__FILENAME__ = ch01_listing_source

import time
import unittest

'''
# <start id="simple-string-calls"/>
$ redis-cli                                 #A
redis 127.0.0.1:6379> set hello world       #D
OK                                          #E
redis 127.0.0.1:6379> get hello             #F
"world"                                     #G
redis 127.0.0.1:6379> del hello             #H
(integer) 1                                 #I
redis 127.0.0.1:6379> get hello             #J
(nil)
redis 127.0.0.1:6379> 
# <end id="simple-string-calls"/>
#A Start the redis-cli client up
#D Set the key 'hello' to the value 'world'
#E If a SET command succeeds, it returns 'OK', which turns into True on the Python side
#F Now get the value stored at the key 'hello'
#G It is still 'world', like we just set it
#H Let's delete the key/value pair
#I If there was a value to delete, DEL returns the number of items that were deleted
#J There is no more value, so trying to fetch the value returns nil, which turns into None on the Python side
#END
'''


'''
# <start id="simple-list-calls"/>
redis 127.0.0.1:6379> rpush list-key item   #A
(integer) 1                                 #A
redis 127.0.0.1:6379> rpush list-key item2  #A
(integer) 2                                 #A
redis 127.0.0.1:6379> rpush list-key item   #A
(integer) 3                                 #A
redis 127.0.0.1:6379> lrange list-key 0 -1  #B
1) "item"                                   #B
2) "item2"                                  #B
3) "item"                                   #B
redis 127.0.0.1:6379> lindex list-key 1     #C
"item2"                                     #C
redis 127.0.0.1:6379> lpop list-key         #D
"item"                                      #D
redis 127.0.0.1:6379> lrange list-key 0 -1  #D
1) "item2"                                  #D
2) "item"                                   #D
redis 127.0.0.1:6379> 
# <end id="simple-list-calls"/>
#A When we push items onto a LIST, the command returns the current length of the list
#B We can fetch the entire list by passing a range of 0 for the start index, and -1 for the last index
#C We can fetch individual items from the list with LINDEX
#D By popping an item from the list, it is no longer available
#END
'''


'''
# <start id="simple-set-calls"/>
redis 127.0.0.1:6379> sadd set-key item     #A
(integer) 1                                 #A
redis 127.0.0.1:6379> sadd set-key item2    #A
(integer) 1                                 #A
redis 127.0.0.1:6379> sadd set-key item3    #A
(integer) 1                                 #A
redis 127.0.0.1:6379> sadd set-key item     #A
(integer) 0                                 #A
redis 127.0.0.1:6379> smembers set-key      #B
1) "item"                                   #B
2) "item2"                                  #B
3) "item3"                                  #B
redis 127.0.0.1:6379> sismember set-key item4   #C
(integer) 0                                     #C
redis 127.0.0.1:6379> sismember set-key item    #C
(integer) 1                                     #C
redis 127.0.0.1:6379> srem set-key item2    #D
(integer) 1                                 #D
redis 127.0.0.1:6379> srem set-key item2    #D
(integer) 0                                 #D
redis 127.0.0.1:6379>  smembers set-key
1) "item"
2) "item3"
redis 127.0.0.1:6379> 
# <end id="simple-set-calls"/>
#A When adding an item to a SET, Redis will return a 1 if the item is new to the set and 0 if it was already in the SET
#B We can fetch all of the items in the SET, which returns them as a sequence of items, which is turned into a Python set from Python
#C We can also ask Redis whether an item is in the SET, which turns into a boolean in Python
#D When we attempt to remove items, our commands return the number of items that were removed
#END
'''


'''
# <start id="simple-hash-calls"/>
redis 127.0.0.1:6379> hset hash-key sub-key1 value1 #A
(integer) 1                                         #A
redis 127.0.0.1:6379> hset hash-key sub-key2 value2 #A
(integer) 1                                         #A
redis 127.0.0.1:6379> hset hash-key sub-key1 value1 #A
(integer) 0                                         #A
redis 127.0.0.1:6379> hgetall hash-key              #B
1) "sub-key1"                                       #B
2) "value1"                                         #B
3) "sub-key2"                                       #B
4) "value2"                                         #B
redis 127.0.0.1:6379> hdel hash-key sub-key2        #C
(integer) 1                                         #C
redis 127.0.0.1:6379> hdel hash-key sub-key2        #C
(integer) 0                                         #C
redis 127.0.0.1:6379> hget hash-key sub-key1        #D
"value1"                                            #D
redis 127.0.0.1:6379> hgetall hash-key
1) "sub-key1"
2) "value1"
# <end id="simple-hash-calls"/>
#A When we add items to a hash, again we get a return value that tells us whether the item is new in the hash
#B We can fetch all of the items in the HASH, which gets translated into a dictionary on the Python side of things
#C When we delete items from the hash, the command returns whether the item was there before we tried to remove it
#D We can also fetch individual fields from hashes
#END
'''


'''
# <start id="simple-zset-calls"/>
redis 127.0.0.1:6379> zadd zset-key 728 member1     #A
(integer) 1                                         #A
redis 127.0.0.1:6379> zadd zset-key 982 member0     #A
(integer) 1                                         #A
redis 127.0.0.1:6379> zadd zset-key 982 member0     #A
(integer) 0                                         #A
redis 127.0.0.1:6379> zrange zset-key 0 -1 withscores   #B
1) "member1"                                            #B
2) "728"                                                #B
3) "member0"                                            #B
4) "982"                                                #B
redis 127.0.0.1:6379> zrangebyscore zset-key 0 800 withscores   #C
1) "member1"                                                    #C
2) "728"                                                        #C
redis 127.0.0.1:6379> zrem zset-key member1     #D
(integer) 1                                     #D
redis 127.0.0.1:6379> zrem zset-key member1     #D
(integer) 0                                     #D
redis 127.0.0.1:6379> zrange zset-key 0 -1 withscores
1) "member0"
2) "982"
# <end id="simple-zset-calls"/>
#A When we add items to a ZSET, the the command returns the number of new items
#B We can fetch all of the items in the ZSET, which are ordered by the scores, and scores are turned into floats in Python
#C We can also fetch a subsequence of items based on their scores
#D When we remove items, we again find the number of items that were removed
#END
'''

# <start id="upvote-code"/>
ONE_WEEK_IN_SECONDS = 7 * 86400                     #A
VOTE_SCORE = 432                                    #A

def article_vote(conn, user, article):
    cutoff = time.time() - ONE_WEEK_IN_SECONDS      #B
    if conn.zscore('time:', article) < cutoff:      #C
        return

    article_id = article.partition(':')[-1]         #D
    if conn.sadd('voted:' + article_id, user):      #E
        conn.zincrby('score:', article, VOTE_SCORE) #E
        conn.hincrby(article, 'votes', 1)           #E
# <end id="upvote-code"/>
#A Prepare our constants
#B Calculate the cutoff time for voting
#C Check to see if the article can still be voted on (we could use the article HASH here, but scores are returned as floats so we don't have to cast it)
#D Get the id portion from the article:id identifier
#E If the user hasn't voted for this article before, increment the article score and vote count (note that our HINCRBY and ZINCRBY calls should be in a Redis transaction, but we don't introduce them until chapter 3 and 4, so ignore that for now)
#END

# <start id="post-article-code"/>
def post_article(conn, user, title, link):
    article_id = str(conn.incr('article:'))     #A

    voted = 'voted:' + article_id
    conn.sadd(voted, user)                      #B
    conn.expire(voted, ONE_WEEK_IN_SECONDS)     #B

    now = time.time()
    article = 'article:' + article_id
    conn.hmset(article, {                       #C
        'title': title,                         #C
        'link': link,                           #C
        'poster': user,                         #C
        'time': now,                            #C
        'votes': 1,                             #C
    })                                          #C

    conn.zadd('score:', article, now + VOTE_SCORE)  #D
    conn.zadd('time:', article, now)                #D

    return article_id
# <end id="post-article-code"/>
#A Generate a new article id
#B Start with the posting user having voted for the article, and set the article voting information to automatically expire in a week (we discuss expiration in chapter 3)
#C Create the article hash
#D Add the article to the time and score ordered zsets
#END

# <start id="fetch-articles-code"/>
ARTICLES_PER_PAGE = 25

def get_articles(conn, page, order='score:'):
    start = (page-1) * ARTICLES_PER_PAGE            #A
    end = start + ARTICLES_PER_PAGE - 1             #A

    ids = conn.zrevrange(order, start, end)         #B
    articles = []
    for id in ids:                                  #C
        article_data = conn.hgetall(id)             #C
        article_data['id'] = id                     #C
        articles.append(article_data)               #C

    return articles
# <end id="fetch-articles-code"/>
#A Set up the start and end indexes for fetching the articles
#B Fetch the article ids
#C Get the article information from the list of article ids
#END

# <start id="add-remove-groups"/>
def add_remove_groups(conn, article_id, to_add=[], to_remove=[]):
    article = 'article:' + article_id           #A
    for group in to_add:
        conn.sadd('group:' + group, article)    #B
    for group in to_remove:
        conn.srem('group:' + group, article)    #C
# <end id="add-remove-groups"/>
#A Construct the article information like we did in post_article
#B Add the article to groups that it should be a part of
#C Remove the article from groups that it should be removed from
#END

# <start id="fetch-articles-group"/>
def get_group_articles(conn, group, page, order='score:'):
    key = order + group                                     #A
    if not conn.exists(key):                                #B
        conn.zinterstore(key,                               #C
            ['group:' + group, order],                      #C
            aggregate='max',                                #C
        )
        conn.expire(key, 60)                                #D
    return get_articles(conn, page, key)                    #E
# <end id="fetch-articles-group"/>
#A Create a key for each group and each sort order
#B If we haven't sorted these articles recently, we should sort them
#C Actually sort the articles in the group based on score or recency
#D Tell Redis to automatically expire the ZSET in 60 seconds
#E Call our earlier get_articles() function to handle pagination and article data fetching
#END

#--------------- Below this line are helpers to test the code ----------------

class TestCh01(unittest.TestCase):
    def setUp(self):
        import redis
        self.conn = redis.Redis(db=15)

    def tearDown(self):
        del self.conn
        print
        print

    def test_article_functionality(self):
        conn = self.conn
        import pprint

        article_id = str(post_article(conn, 'username', 'A title', 'http://www.google.com'))
        print "We posted a new article with id:", article_id
        print
        self.assertTrue(article_id)

        print "Its HASH looks like:"
        r = conn.hgetall('article:' + article_id)
        print r
        print
        self.assertTrue(r)

        article_vote(conn, 'other_user', 'article:' + article_id)
        print "We voted for the article, it now has votes:",
        v = conn.hget('article:' + article_id, 'votes')
        print v
        print
        self.assertTrue(v > 1)

        print "The currently highest-scoring articles are:"
        articles = get_articles(conn, 1)
        pprint.pprint(articles)
        print

        self.assertTrue(len(articles) >= 1)

        add_remove_groups(conn, article_id, ['new-group'])
        print "We added the article to a new group, other articles include:"
        articles = get_group_articles(conn, 'new-group', 1)
        pprint.pprint(articles)
        print
        self.assertTrue(len(articles) >= 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch02_listing_source

import json
import threading
import time
import unittest
import urlparse
import uuid

QUIT = False

# <start id="_1311_14471_8266"/>
def check_token(conn, token):
    return conn.hget('login:', token)   #A
# <end id="_1311_14471_8266"/>
#A Fetch and return the given user, if available
#END

# <start id="_1311_14471_8265"/>
def update_token(conn, token, user, item=None):
    timestamp = time.time()                             #A
    conn.hset('login:', token, user)                    #B
    conn.zadd('recent:', token, timestamp)              #C
    if item:
        conn.zadd('viewed:' + token, item, timestamp)   #D
        conn.zremrangebyrank('viewed:' + token, 0, -26) #E
# <end id="_1311_14471_8265"/>
#A Get the timestamp
#B Keep a mapping from the token to the logged-in user
#C Record when the token was last seen
#D Record that the user viewed the item
#E Remove old items, keeping the most recent 25
#END

# <start id="_1311_14471_8270"/>
QUIT = False
LIMIT = 10000000

def clean_sessions(conn):
    while not QUIT:
        size = conn.zcard('recent:')                    #A
        if size <= LIMIT:                               #B
            time.sleep(1)                               #B
            continue

        end_index = min(size - LIMIT, 100)              #C
        tokens = conn.zrange('recent:', 0, end_index-1) #C

        session_keys = []                               #D
        for token in tokens:                            #D
            session_keys.append('viewed:' + token)      #D

        conn.delete(*session_keys)                      #E
        conn.hdel('login:', *tokens)                    #E
        conn.zrem('recent:', *tokens)                   #E
# <end id="_1311_14471_8270"/>
#A Find out how many tokens are known
#B We are still under our limit, sleep and try again
#C Fetch the token ids that should be removed
#D Prepare the key names for the tokens to delete
#E Remove the oldest tokens
#END

# <start id="_1311_14471_8279"/>
def add_to_cart(conn, session, item, count):
    if count <= 0:
        conn.hrem('cart:' + session, item)          #A
    else:
        conn.hset('cart:' + session, item, count)   #B
# <end id="_1311_14471_8279"/>
#A Remove the item from the cart
#B Add the item to the cart
#END

# <start id="_1311_14471_8271"/>
def clean_full_sessions(conn):
    while not QUIT:
        size = conn.zcard('recent:')
        if size <= LIMIT:
            time.sleep(1)
            continue

        end_index = min(size - LIMIT, 100)
        sessions = conn.zrange('recent:', 0, end_index-1)

        session_keys = []
        for sess in sessions:
            session_keys.append('viewed:' + sess)
            session_keys.append('cart:' + sess)                    #A

        conn.delete(*session_keys)
        conn.hdel('login:', *sessions)
        conn.zrem('recent:', *sessions)
# <end id="_1311_14471_8271"/>
#A The required added line to delete the shopping cart for old sessions
#END

# <start id="_1311_14471_8291"/>
def cache_request(conn, request, callback):
    if not can_cache(conn, request):                #A
        return callback(request)                    #A

    page_key = 'cache:' + hash_request(request)     #B
    content = conn.get(page_key)                    #C

    if not content:
        content = callback(request)                 #D
        conn.setex(page_key, content, 300)          #E

    return content                                  #F
# <end id="_1311_14471_8291"/>
#A If we cannot cache the request, immediately call the callback
#B Convert the request into a simple string key for later lookups
#C Fetch the cached content if we can, and it is available
#D Generate the content if we can't cache the page, or if it wasn't cached
#E Cache the newly generated content if we can cache it
#F Return the content
#END

# <start id="_1311_14471_8287"/>
def schedule_row_cache(conn, row_id, delay):
    conn.zadd('delay:', row_id, delay)           #A
    conn.zadd('schedule:', row_id, time.time())  #B
# <end id="_1311_14471_8287"/>
#A Set the delay for the item first
#B Schedule the item to be cached now
#END


# <start id="_1311_14471_8292"/>
def cache_rows(conn):
    while not QUIT:
        next = conn.zrange('schedule:', 0, 0, withscores=True)  #A
        now = time.time()
        if not next or next[0][1] > now:
            time.sleep(.05)                                     #B
            continue

        row_id = next[0][0]
        delay = conn.zscore('delay:', row_id)                   #C
        if delay <= 0:
            conn.zrem('delay:', row_id)                         #D
            conn.zrem('schedule:', row_id)                      #D
            conn.delete('inv:' + row_id)                        #D
            continue

        row = Inventory.get(row_id)                             #E
        conn.zadd('schedule:', row_id, now + delay)             #F
        conn.set('inv:' + row_id, json.dumps(row.to_dict()))    #F
# <end id="_1311_14471_8292"/>
#A Find the next row that should be cached (if any), including the timestamp, as a list of tuples with zero or one items
#B No rows can be cached now, so wait 50 milliseconds and try again
#C Get the delay before the next schedule
#D The item shouldn't be cached anymore, remove it from the cache
#E Get the database row
#F Update the schedule and set the cache value
#END

# <start id="_1311_14471_8298"/>
def update_token(conn, token, user, item=None):
    timestamp = time.time()
    conn.hset('login:', token, user)
    conn.zadd('recent:', token, timestamp)
    if item:
        conn.zadd('viewed:' + token, item, timestamp)
        conn.zremrangebyrank('viewed:' + token, 0, -26)
        conn.zincrby('viewed:', item, -1)                   #A
# <end id="_1311_14471_8298"/>
#A The line we need to add to update_token()
#END

# <start id="_1311_14471_8288"/>
def rescale_viewed(conn):
    while not QUIT:
        conn.zremrangebyrank('viewed:', 0, -20001)      #A
        conn.zinterstore('viewed:', {'viewed:': .5})    #B
        time.sleep(300)                                 #C
# <end id="_1311_14471_8288"/>
#A Remove any item not in the top 20,000 viewed items
#B Rescale all counts to be 1/2 of what they were before
#C Do it again in 5 minutes
#END

# <start id="_1311_14471_8289"/>
def can_cache(conn, request):
    item_id = extract_item_id(request)          #A
    if not item_id or is_dynamic(request):      #B
        return False
    rank = conn.zrank('viewed:', item_id)       #C
    return rank is not None and rank < 10000    #D
# <end id="_1311_14471_8289"/>
#A Get the item id for the page, if any
#B Check whether the page can be statically cached, and whether this is an item page
#C Get the rank of the item
#D Return whether the item has a high enough view count to be cached
#END


#--------------- Below this line are helpers to test the code ----------------

def extract_item_id(request):
    parsed = urlparse.urlparse(request)
    query = urlparse.parse_qs(parsed.query)
    return (query.get('item') or [None])[0]

def is_dynamic(request):
    parsed = urlparse.urlparse(request)
    query = urlparse.parse_qs(parsed.query)
    return '_' in query

def hash_request(request):
    return str(hash(request))

class Inventory(object):
    def __init__(self, id):
        self.id = id

    @classmethod
    def get(cls, id):
        return Inventory(id)

    def to_dict(self):
        return {'id':self.id, 'data':'data to cache...', 'cached':time.time()}

class TestCh02(unittest.TestCase):
    def setUp(self):
        import redis
        self.conn = redis.Redis(db=15)

    def tearDown(self):
        del self.conn
        global QUIT, LIMIT
        QUIT = False
        LIMIT = 10000000
        print
        print

    def test_login_cookies(self):
        conn = self.conn
        global LIMIT, QUIT
        token = str(uuid.uuid4())

        update_token(conn, token, 'username', 'itemX')
        print "We just logged-in/updated token:", token
        print "For user:", 'username'
        print

        print "What username do we get when we look-up that token?"
        r = check_token(conn, token)
        print r
        print
        self.assertTrue(r)


        print "Let's drop the maximum number of cookies to 0 to clean them out"
        print "We will start a thread to do the cleaning, while we stop it later"

        LIMIT = 0
        t = threading.Thread(target=clean_sessions, args=(conn,))
        t.setDaemon(1) # to make sure it dies if we ctrl+C quit
        t.start()
        time.sleep(1)
        QUIT = True
        time.sleep(2)
        if t.isAlive():
            raise Exception("The clean sessions thread is still alive?!?")

        s = conn.hlen('login:')
        print "The current number of sessions still available is:", s
        self.assertFalse(s)

    def test_shoppping_cart_cookies(self):
        conn = self.conn
        global LIMIT, QUIT
        token = str(uuid.uuid4())

        print "We'll refresh our session..."
        update_token(conn, token, 'username', 'itemX')
        print "And add an item to the shopping cart"
        add_to_cart(conn, token, "itemY", 3)
        r = conn.hgetall('cart:' + token)
        print "Our shopping cart currently has:", r
        print

        self.assertTrue(len(r) >= 1)

        print "Let's clean out our sessions and carts"
        LIMIT = 0
        t = threading.Thread(target=clean_full_sessions, args=(conn,))
        t.setDaemon(1) # to make sure it dies if we ctrl+C quit
        t.start()
        time.sleep(1)
        QUIT = True
        time.sleep(2)
        if t.isAlive():
            raise Exception("The clean sessions thread is still alive?!?")

        r = conn.hgetall('cart:' + token)
        print "Our shopping cart now contains:", r

        self.assertFalse(r)

    def test_cache_request(self):
        conn = self.conn
        token = str(uuid.uuid4())

        def callback(request):
            return "content for " + request

        update_token(conn, token, 'username', 'itemX')
        url = 'http://test.com/?item=itemX'
        print "We are going to cache a simple request against", url
        result = cache_request(conn, url, callback)
        print "We got initial content:", repr(result)
        print

        self.assertTrue(result)

        print "To test that we've cached the request, we'll pass a bad callback"
        result2 = cache_request(conn, url, None)
        print "We ended up getting the same response!", repr(result2)

        self.assertEquals(result, result2)

        self.assertFalse(can_cache(conn, 'http://test.com/'))
        self.assertFalse(can_cache(conn, 'http://test.com/?item=itemX&_=1234536'))

    def test_cache_rows(self):
        import pprint
        conn = self.conn
        global QUIT
        
        print "First, let's schedule caching of itemX every 5 seconds"
        schedule_row_cache(conn, 'itemX', 5)
        print "Our schedule looks like:"
        s = conn.zrange('schedule:', 0, -1, withscores=True)
        pprint.pprint(s)
        self.assertTrue(s)

        print "We'll start a caching thread that will cache the data..."
        t = threading.Thread(target=cache_rows, args=(conn,))
        t.setDaemon(1)
        t.start()

        time.sleep(1)
        print "Our cached data looks like:"
        r = conn.get('inv:itemX')
        print repr(r)
        self.assertTrue(r)
        print
        print "We'll check again in 5 seconds..."
        time.sleep(5)
        print "Notice that the data has changed..."
        r2 = conn.get('inv:itemX')
        print repr(r2)
        print
        self.assertTrue(r2)
        self.assertTrue(r != r2)

        print "Let's force un-caching"
        schedule_row_cache(conn, 'itemX', -1)
        time.sleep(1)
        r = conn.get('inv:itemX')
        print "The cache was cleared?", not r
        print
        self.assertFalse(r)

        QUIT = True
        time.sleep(2)
        if t.isAlive():
            raise Exception("The database caching thread is still alive?!?")

    # We aren't going to bother with the top 10k requests are cached, as
    # we already tested it as part of the cached requests test.

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch03_listing_source

import time
import unittest

import redis

ONE_WEEK_IN_SECONDS = 7 * 86400
VOTE_SCORE = 432
ARTICLES_PER_PAGE = 25

'''
# <start id="string-calls-1"/>
>>> conn = redis.Redis()
>>> conn.get('key')             #A
>>> conn.incr('key')            #B
1                               #B
>>> conn.incr('key', 15)        #B
16                              #B
>>> conn.decr('key', 5)         #C
11                              #C
>>> conn.get('key')             #D
'11'                            #D
>>> conn.set('key', '13')       #E
True                            #E
>>> conn.incr('key')            #E
14                              #E
# <end id="string-calls-1"/>
#A When we fetch a key that does not exist, we get the None value, which is not displayed in the interactive console
#B We can increment keys that don't exist, and we can pass an optional value to increment by more than 1
#C Like incrementing, decrementing takes an optional argument for the amount to decrement by
#D When we fetch the key it acts like a string
#E And when we set the key, we can set it as a string, but still manipulate it like an integer
#END
'''


'''
# <start id="string-calls-2"/>
>>> conn.append('new-string-key', 'hello ')     #A
6L                                              #B
>>> conn.append('new-string-key', 'world!')
12L                                             #B
>>> conn.substr('new-string-key', 3, 7)         #C
'lo wo'                                         #D
>>> conn.setrange('new-string-key', 0, 'H')     #E
12                                              #F
>>> conn.setrange('new-string-key', 6, 'W')
12
>>> conn.get('new-string-key')                  #G
'Hello World!'                                  #H
>>> conn.setrange('new-string-key', 11, ', how are you?')   #I
25
>>> conn.get('new-string-key')
'Hello World, how are you?'                     #J
>>> conn.setbit('another-key', 2, 1)            #K
0                                               #L
>>> conn.setbit('another-key', 7, 1)            #M
0                                               #M
>>> conn.get('another-key')                     #M
'!'                                             #N
# <end id="string-calls-2"/>
#A Let's append the string 'hello ' to the previously non-existent key 'new-string-key'
#B When appending a value, Redis returns the length of the string so far
#C Redis uses 0-indexing, and when accessing ranges, is inclusive of the endpoints by default
#D The string 'lo wo' is from the middle of 'hello world!'
#E Let's set a couple string ranges
#F When setting a range inside a string, Redis also returns the total length of the string
#G Let's see what we have now!
#H Yep, we capitalized our 'H' and 'W'
#I With setrange we can replace anywhere inside the string, and we can make the string longer
#J We replaced the exclamation point and added more to the end of the string
#K If you write to a bit beyond the size of the string, it is filled with nulls
#L Setting bits also returns the value of the bit before it was set
#M If you are going to try to interpret the bits stored in Redis, remember that offsets into bits are from the highest-order to the lowest-order
#N We set bits 2 and 7 to 1, which gave us '!', or character 33
#END
'''

'''
# <start id="list-calls-1"/>
>>> conn.rpush('list-key', 'last')          #A
1L                                          #A
>>> conn.lpush('list-key', 'first')         #B
2L
>>> conn.rpush('list-key', 'new last')
3L
>>> conn.lrange('list-key', 0, -1)          #C
['first', 'last', 'new last']               #C
>>> conn.lpop('list-key')                   #D
'first'                                     #D
>>> conn.lpop('list-key')                   #D
'last'                                      #D
>>> conn.lrange('list-key', 0, -1)
['new last']
>>> conn.rpush('list-key', 'a', 'b', 'c')   #E
4L
>>> conn.lrange('list-key', 0, -1)
['new last', 'a', 'b', 'c']
>>> conn.ltrim('list-key', 2, -1)           #F
True                                        #F
>>> conn.lrange('list-key', 0, -1)          #F
['b', 'c']                                  #F
# <end id="list-calls-1"/>
#A When we push items onto the list, it returns the length of the list after the push has completed
#B We can easily push on both ends of the list
#C Semantically, the left end of the list is the beginning, and the right end of the list is the end
#D Popping off the left items repeatedly will return items from left to right
#E We can push multiple items at the same time
#F We can trim any number of items from the start, end, or both
#END
'''

'''
# <start id="list-calls-2"/>
>>> conn.rpush('list', 'item1')             #A
1                                           #A
>>> conn.rpush('list', 'item2')             #A
2                                           #A
>>> conn.rpush('list2', 'item3')            #A
1                                           #A
>>> conn.brpoplpush('list2', 'list', 1)     #B
'item3'                                     #B
>>> conn.brpoplpush('list2', 'list', 1)     #C
>>> conn.lrange('list', 0, -1)              #D
['item3', 'item1', 'item2']                 #D
>>> conn.brpoplpush('list', 'list2', 1)
'item2'
>>> conn.blpop(['list', 'list2'], 1)        #E
('list', 'item3')                           #E
>>> conn.blpop(['list', 'list2'], 1)        #E
('list', 'item1')                           #E
>>> conn.blpop(['list', 'list2'], 1)        #E
('list2', 'item2')                          #E
>>> conn.blpop(['list', 'list2'], 1)        #E
>>>
# <end id="list-calls-2"/>
#A Let's add some items to a couple lists to start
#B Let's move an item from one list to the other, leaving it
#C When a list is empty, the blocking pop will stall for the timeout, and return None (which is not displayed in the interactive console)
#D We popped the rightmost item from 'list2' and pushed it to the left of 'list'
#E Blocking left-popping items from these will check lists for items in the order that they are passed, until they are empty
#END
'''

# <start id="exercise-update-token"/>
def update_token(conn, token, user, item=None):
    timestamp = time.time()
    conn.hset('login:', token, user)
    conn.zadd('recent:', token, timestamp)
    if item:
        key = 'viewed:' + token
        conn.lrem(key, item)                    #A
        conn.rpush(key, item)                   #B
        conn.ltrim(key, -25, -1)                #C
    conn.zincrby('viewed:', item, -1)
# <end id="exercise-update-token"/>
#A Remove the item from the list if it was there
#B Push the item to the right side of the LIST so that ZRANGE and LRANGE have the same result
#C Trim the LIST to only include the most recent 25 items
#END


'''
# <start id="set-calls-1"/>
>>> conn.sadd('set-key', 'a', 'b', 'c')         #A
3                                               #A
>>> conn.srem('set-key', 'c', 'd')              #B
True                                            #B
>>> conn.srem('set-key', 'c', 'd')              #B
False                                           #B
>>> conn.scard('set-key')                       #C
2                                               #C
>>> conn.smembers('set-key')                    #D
set(['a', 'b'])                                 #D
>>> conn.smove('set-key', 'set-key2', 'a')      #E
True                                            #E
>>> conn.smove('set-key', 'set-key2', 'c')      #F
False                                           #F
>>> conn.smembers('set-key2')                   #F
set(['a'])                                      #F
# <end id="set-calls-1"/>
#A Adding items to the SET returns the number of items that weren't already in the SET
#B Removing items from the SET returns whether an item was removed - note that the client is buggy in that respect, as Redis itself returns the total number of items removed
#C We can get the number of items in the SET
#D We can also fetch the whole SET
#E We can easily move items from one SET to another SET
#F When an item doesn't exist in the first set during a SMOVE, it isn't added to the destination SET
#END
'''


'''
# <start id="set-calls-2"/>
>>> conn.sadd('skey1', 'a', 'b', 'c', 'd')  #A
4                                           #A
>>> conn.sadd('skey2', 'c', 'd', 'e', 'f')  #A
4                                           #A
>>> conn.sdiff('skey1', 'skey2')            #B
set(['a', 'b'])                             #B
>>> conn.sinter('skey1', 'skey2')           #C
set(['c', 'd'])                             #C
>>> conn.sunion('skey1', 'skey2')           #D
set(['a', 'c', 'b', 'e', 'd', 'f'])         #D
# <end id="set-calls-2"/>
#A First we'll add a few items to a couple SETs
#B We can calculate the result of removing all of the items in the second set from the first SET
#C We can also find out which items exist in both SETs
#D And we can find out all of the items that are in either of the SETs
#END
'''

'''
# <start id="hash-calls-1"/>
>>> conn.hmset('hash-key', {'k1':'v1', 'k2':'v2', 'k3':'v3'})   #A
True                                                            #A
>>> conn.hmget('hash-key', ['k2', 'k3'])                        #B
['v2', 'v3']                                                    #B
>>> conn.hlen('hash-key')                                       #C
3                                                               #C
>>> conn.hdel('hash-key', 'k1', 'k3')                           #D
True                                                            #D
# <end id="hash-calls-1"/>
#A We can add multiple items to the hash in one call
#B We can fetch a subset of the values in a single call
#C The HLEN command is typically used for debugging very large HASHes
#D The HDEL command handles multiple arguments without needing an HMDEL counterpart and returns True if any fields were removed
#END
'''

'''
# <start id="hash-calls-2"/>
>>> conn.hmset('hash-key2', {'short':'hello', 'long':1000*'1'}) #A
True                                                            #A
>>> conn.hkeys('hash-key2')                                     #A
['long', 'short']                                               #A
>>> conn.hexists('hash-key2', 'num')                            #B
False                                                           #B
>>> conn.hincrby('hash-key2', 'num')                            #C
1L                                                              #C
>>> conn.hexists('hash-key2', 'num')                            #C
True                                                            #C
# <end id="hash-calls-2"/>
#A Fetching keys can be useful to keep from needing to transfer large values when you are looking into HASHes
#B We can also check the existence of specific keys
#C Incrementing a previously non-existent key in a hash behaves just like on strings, Redis operates as though the value had been 0
#END
'''

'''
# <start id="zset-calls-1"/>
>>> conn.zadd('zset-key', 'a', 3, 'b', 2, 'c', 1)   #A
3                                                   #A
>>> conn.zcard('zset-key')                          #B
3                                                   #B
>>> conn.zincrby('zset-key', 'c', 3)                #C
4.0                                                 #C
>>> conn.zscore('zset-key', 'b')                    #D
2.0                                                 #D
>>> conn.zrank('zset-key', 'c')                     #E
2                                                   #E
>>> conn.zcount('zset-key', 0, 3)                   #F
2L                                                  #F
>>> conn.zrem('zset-key', 'b')                      #G
True                                                #G
>>> conn.zrange('zset-key', 0, -1, withscores=True) #H
[('a', 3.0), ('c', 4.0)]                            #H
# <end id="zset-calls-1"/>
#A Adding members to ZSETs in Python has the arguments reversed compared to standard Redis, so as to not confuse users compared to HASHes
#B Knowing how large a ZSET is can tell you in some cases if it is necessary to trim your ZSET
#C We can also increment members like we can with STRING and HASH values
#D Fetching scores of individual members can be useful if you have been keeping counters or toplists
#E By fetching the 0-indexed position of a member, we can then later use ZRANGE to fetch a range of the values easily
#F Counting the number of items with a given range of scores can be quite useful for some tasks
#G Removing members is as easy as adding them
#H For debugging, we usually fetch the entire ZSET with this ZRANGE call, but real use-cases will usually fetch items a relatively small group at a time
#END
'''

'''
# <start id="zset-calls-2"/>
>>> conn.zadd('zset-1', 'a', 1, 'b', 2, 'c', 3)                         #A
3                                                                       #A
>>> conn.zadd('zset-2', 'b', 4, 'c', 1, 'd', 0)                         #A
3                                                                       #A
>>> conn.zinterstore('zset-i', ['zset-1', 'zset-2'])                    #B
2L                                                                      #B
>>> conn.zrange('zset-i', 0, -1, withscores=True)                       #B
[('c', 4.0), ('b', 6.0)]                                                #B
>>> conn.zunionstore('zset-u', ['zset-1', 'zset-2'], aggregate='min')   #C
4L                                                                      #C
>>> conn.zrange('zset-u', 0, -1, withscores=True)                       #C
[('d', 0.0), ('a', 1.0), ('c', 1.0), ('b', 2.0)]                        #C
>>> conn.sadd('set-1', 'a', 'd')                                        #D
2                                                                       #D
>>> conn.zunionstore('zset-u2', ['zset-1', 'zset-2', 'set-1'])          #D
4L                                                                      #D
>>> conn.zrange('zset-u2', 0, -1, withscores=True)                      #D
[('d', 1.0), ('a', 2.0), ('c', 4.0), ('b', 6.0)]                        #D
# <end id="zset-calls-2"/>
#A We'll start out by creating a couple ZSETs
#B When performing ZINTERSTORE or ZUNIONSTORE, our default aggregate is sum, so scores of items that are in multiple ZSETs are added
#C It is easy to provide different aggregates, though we are limited to sum, min, and max
#D You can also pass SETs as inputs to ZINTERSTORE and ZUNIONSTORE, they behave as though they were ZSETs with all scores equal to 1
#END
'''

def publisher(n):
    time.sleep(1)
    for i in xrange(n):
        conn.publish('channel', i)
        time.sleep(1)

def run_pubsub():
    threading.Thread(target=publisher, args=(3,)).start()
    pubsub = conn.pubsub()
    pubsub.subscribe(['channel'])
    count = 0
    for item in pubsub.listen():
        print item
        count += 1
        if count == 4:
            pubsub.unsubscribe()
        if count == 5:
            break

'''
# <start id="pubsub-calls-1"/>
>>> def publisher(n):
...     time.sleep(1)                                                   #A
...     for i in xrange(n):
...         conn.publish('channel', i)                                  #B
...         time.sleep(1)                                               #B
...
>>> def run_pubsub():
...     threading.Thread(target=publisher, args=(3,)).start()
...     pubsub = conn.pubsub()
...     pubsub.subscribe(['channel'])
...     count = 0
...     for item in pubsub.listen():
...         print item
...         count += 1
...         if count == 4:
...             pubsub.unsubscribe()
...         if count == 5:
...             break
... 

>>> def run_pubsub():
...     threading.Thread(target=publisher, args=(3,)).start()           #D
...     pubsub = conn.pubsub()                                          #E
...     pubsub.subscribe(['channel'])                                   #E
...     count = 0
...     for item in pubsub.listen():                                    #F
...         print item                                                  #G
...         count += 1                                                  #H
...         if count == 4:                                              #H
...             pubsub.unsubscribe()                                    #H
...         if count == 5:                                              #L
...             break                                                   #L
...
>>> run_pubsub()                                                        #C
{'pattern': None, 'type': 'subscribe', 'channel': 'channel', 'data': 1L}#I
{'pattern': None, 'type': 'message', 'channel': 'channel', 'data': '0'} #J
{'pattern': None, 'type': 'message', 'channel': 'channel', 'data': '1'} #J
{'pattern': None, 'type': 'message', 'channel': 'channel', 'data': '2'} #J
{'pattern': None, 'type': 'unsubscribe', 'channel': 'channel', 'data':  #K
0L}                                                                     #K
# <end id="pubsub-calls-1"/>
#A We sleep initially in the function to let the SUBSCRIBEr connect and start listening for messages
#B After publishing, we will pause for a moment so that we can see this happen over time
#D Let's start the publisher thread to send 3 messages
#E We'll set up the pubsub object and subscribe to a channel
#F We can listen to subscription messages by iterating over the result of pubsub.listen()
#G We'll print every message that we receive
#H We will stop listening for new messages after the subscribe message and 3 real messages by unsubscribing
#L When we receive the unsubscribe message, we need to stop receiving messages
#C Actually run the functions to see them work
#I When subscribing, we receive a message on the listen channel
#J These are the structures that are produced as items when we iterate over pubsub.listen()
#K When we unsubscribe, we receive a message telling us which channels we have unsubscribed from and the number of channels we are still subscribed to
#END
'''


'''
# <start id="sort-calls"/>
>>> conn.rpush('sort-input', 23, 15, 110, 7)                    #A
4                                                               #A
>>> conn.sort('sort-input')                                     #B
['7', '15', '23', '110']                                        #B
>>> conn.sort('sort-input', alpha=True)                         #C
['110', '15', '23', '7']                                        #C
>>> conn.hset('d-7', 'field', 5)                                #D
1L                                                              #D
>>> conn.hset('d-15', 'field', 1)                               #D
1L                                                              #D
>>> conn.hset('d-23', 'field', 9)                               #D
1L                                                              #D
>>> conn.hset('d-110', 'field', 3)                              #D
1L                                                              #D
>>> conn.sort('sort-input', by='d-*->field')                    #E
['15', '110', '7', '23']                                        #E
>>> conn.sort('sort-input', by='d-*->field', get='d-*->field')  #F
['1', '3', '5', '9']                                            #F
# <end id="sort-calls"/>
#A Start by adding some items to a LIST
#B We can sort the items numerically
#C And we can sort the items alphabetically
#D We are just adding some additional data for SORTing and fetching
#E We can sort our data by fields of HASHes
#F And we can even fetch that data and return it instead of or in addition to our input data
#END
'''

'''
# <start id="simple-pipeline-notrans"/>
>>> def notrans():
...     print conn.incr('notrans:')                     #A
...     time.sleep(.1)                                  #B
...     conn.incr('notrans:', -1)                       #C
...
>>> if 1:
...     for i in xrange(3):                             #D
...         threading.Thread(target=notrans).start()    #D
...     time.sleep(.5)                                  #E
...
1                                                       #F
2                                                       #F
3                                                       #F
# <end id="simple-pipeline-notrans"/>
#A Increment the 'notrans:' counter and print the result
#B Wait for 100 milliseconds
#C Decrement the 'notrans:' counter
#D Start three threads to execute the non-transactional increment/sleep/decrement
#E Wait half a second for everything to be done
#F Because there is no transaction, each of the threaded commands can interleave freely, causing the counter to steadily grow in this case
#END
'''

'''
# <start id="simple-pipeline-trans"/>
>>> def trans():
...     pipeline = conn.pipeline()                      #A
...     pipeline.incr('trans:')                         #B
...     time.sleep(.1)                                  #C
...     pipeline.incr('trans:', -1)                     #D
...     print pipeline.execute()[0]                     #E
...
>>> if 1:
...     for i in xrange(3):                             #F
...         threading.Thread(target=trans).start()      #F
...     time.sleep(.5)                                  #G
...
1                                                       #H
1                                                       #H
1                                                       #H
# <end id="simple-pipeline-trans"/>
#A Create a transactional pipeline
#B Queue up the 'trans:' counter increment
#C Wait for 100 milliseconds
#D Queue up the 'trans:' counter decrement
#E Execute both commands and print the result of the increment operation
#F Start three of the transactional increment/sleep/decrement calls
#G Wait half a second for everything to be done
#H Because each increment/sleep/decrement pair is executed inside a transaction, no other commands can be interleaved, which gets us a result of 1 for all of our results
#END
'''

# <start id="exercise-fix-article-vote"/>
def article_vote(conn, user, article):
    cutoff = time.time() - ONE_WEEK_IN_SECONDS
    posted = conn.zscore('time:', article)                      #A
    if posted < cutoff:
        return

    article_id = article.partition(':')[-1]
    pipeline = conn.pipeline()
    pipeline.sadd('voted:' + article_id, user)
    pipeline.expire('voted:' + article_id, int(posted-cutoff))  #B
    if pipeline.execute()[0]:
        pipeline.zincrby('score:', article, VOTE_SCORE)         #C
        pipeline.hincrby(article, 'votes', 1)                   #C
        pipeline.execute()                                      #C
# <end id="exercise-fix-article-vote"/>
#A If the article should expire bewteen our ZSCORE and our SADD, we need to use the posted time to properly expire it
#B Set the expiration time if we shouldn't have actually added the vote to the SET
#C We could lose our connection between the SADD/EXPIRE and ZINCRBY/HINCRBY, so the vote may not count, but that is better than it partially counting by failing between the ZINCRBY/HINCRBY calls
#END

# Technically, the above article_vote() version still has some issues, which
# are addressed in the following, which uses features/functionality not
# introduced until chapter 4.

def article_vote(conn, user, article):
    cutoff = time.time() - ONE_WEEK_IN_SECONDS
    posted = conn.zscore('time:', article)
    article_id = article.partition(':')[-1]
    voted = 'voted:' + article_id

    pipeline = conn.pipeline()
    while posted > cutoff:
        try:
            pipeline.watch(voted)
            if not pipeline.sismember(voted, user):
                pipeline.multi()
                pipeline.sadd(voted, user)
                pipeline.expire(voted, int(posted-cutoff))
                pipeline.zincrby('score:', article, VOTE_SCORE)
                pipeline.hincrby(article, 'votes', 1)
                pipeline.execute()
            else:
                pipeline.unwatch()
            return
        except redis.exceptions.WatchError:
            cutoff = time.time() - ONE_WEEK_IN_SECONDS

# <start id="exercise-fix-get_articles"/>
def get_articles(conn, page, order='score:'):
    start = max(page-1, 0) * ARTICLES_PER_PAGE
    end = start + ARTICLES_PER_PAGE - 1

    ids = conn.zrevrangebyscore(order, start, end)

    pipeline = conn.pipeline()
    map(pipeline.hgetall, ids)                              #A

    articles = []
    for id, article_data in zip(ids, pipeline.execute()):   #B
        article_data['id'] = id
        articles.append(article_data)

    return articles
# <end id="exercise-fix-get_articles"/>
#A Prepare the HGETALL calls on the pipeline
#B Execute the pipeline and add ids to the article
#END

'''
# <start id="other-calls-1"/>
>>> conn.set('key', 'value')                    #A
True                                            #A
>>> conn.get('key')                             #A
'value'                                         #A
>>> conn.expire('key', 2)                       #B
True                                            #B
>>> time.sleep(2)                               #B
>>> conn.get('key')                             #B
>>> conn.set('key', 'value2')
True
>>> conn.expire('key', 100); conn.ttl('key')    #C
True                                            #C
100                                             #C
# <end id="other-calls-1"/>
#A We are starting with a very simple STRING value
#B If we set a key to expire in the future, and we wait long enough for the key to expire, when we try to fetch the key, it has already been deleted
#C We can also easily find out how long it will be before a key will expire
#END
'''

# <start id="exercise-no-recent-zset"/>
THIRTY_DAYS = 30*86400
def check_token(conn, token):
    return conn.get('login:' + token)       #A

def update_token(conn, token, user, item=None):
    conn.setex('login:' + token, user, THIRTY_DAYS) #B
    key = 'viewed:' + token
    if item:
        conn.lrem(key, item)
        conn.rpush(key, item)
        conn.ltrim(key, -25, -1)
    conn.expire(key, THIRTY_DAYS)                   #C
    conn.zincrby('viewed:', item, -1)

def add_to_cart(conn, session, item, count):
    key = 'cart:' + session
    if count <= 0:
        conn.hrem(key, item)
    else:
        conn.hset(key, item, count)
    conn.expire(key, THIRTY_DAYS)               #D
# <end id="exercise-no-recent-zset"/>
#A We are going to store the login token as a string value so we can EXPIRE it
#B Set the value of the the login token and the token's expiration time with one call
#C We can't manipulate LISTs and set their expiration at the same time, so we must do it later
#D We also can't manipulate HASHes and set their expiration times, so we again do it later
#END

########NEW FILE########
__FILENAME__ = ch04_listing_source

import os
import time
import unittest
import uuid

import redis

'''
# <start id="persistence-options"/>
save 60 1000                        #A
stop-writes-on-bgsave-error no      #A
rdbcompression yes                  #A
dbfilename dump.rdb                 #A

appendonly no                       #B
appendfsync everysec                #B
no-appendfsync-on-rewrite no        #B
auto-aof-rewrite-percentage 100     #B
auto-aof-rewrite-min-size 64mb      #B

dir ./                              #C
# <end id="persistence-options"/>
#A Snapshotting persistence options
#B Append-only file persistence options
#C Shared option, where to store the snapshot or append-only file
#END
'''

# <start id="process-logs-progress"/>
def process_logs(conn, path, callback):                     #K
    current_file, offset = conn.mget(                       #A
        'progress:file', 'progress:position')               #A

    pipe = conn.pipeline()

    def update_progress():                                  #H
        pipe.mset({                                         #I
            'progress:file': fname,                         #I
            'progress:position': offset                     #I
        })
        pipe.execute()                                      #J

    for fname in sorted(os.listdir(path)):                  #B
        if fname < current_file:                            #C
            continue

        inp = open(os.path.join(path, fname), 'rb')
        if fname == current_file:                           #D
            inp.seek(int(offset, 10))                       #D
        else:
            offset = 0

        current_file = None

        for lno, line in enumerate(inp):                    #L
            callback(pipe, line)                            #E
            offset += int(offset) + len(line)               #F

            if not (lno+1) % 1000:                          #G
                update_progress()                           #G
        update_progress()                                   #G

        inp.close()
# <end id="process-logs-progress"/>
#A Get the current progress
#B Iterate over the logfiles in sorted order
#C Skip over files that are before the current file
#D If we are continuing a file, skip over the parts that we've already processed
#E Handle the log line
#F Update our information about the offset into the file
#G Write our progress back to Redis every 1000 lines, or when we are done with a file
#H This closure is meant primarily to reduce the number of duplicated lines later
#I We want to update our file and line number offsets into the logfile
#J This will execute any outstanding log updates, as well as to actually write our file and line number updates to Redis
#K Our function will be provided with a callback that will take a connection and a log line, calling methods on the pipeline as necessary
#L The enumerate function iterates over a sequence (in this case lines from a file), and produces pairs consisting of a numeric sequence starting from 0, and the original data
#END

# <start id="wait-for-sync"/>
def wait_for_sync(mconn, sconn):
    identifier = str(uuid.uuid4())
    mconn.zadd('sync:wait', identifier, time.time())        #A

    while not sconn.info()['master_link_status'] != 'up':   #B
        time.sleep(.001)

    while not sconn.zscore('sync:wait', identifier):        #C
        time.sleep(.001)

    deadline = time.time() + 1.01                           #D
    while time.time() < deadline:                           #D
        if sconn.info()['aof_pending_bio_fsync'] == 0:      #E
            break                                           #E
        time.sleep(.001)

    mconn.zrem('sync:wait', identifier)                     #F
    mconn.zremrangebyscore('sync:wait', 0, time.time()-900) #F
# <end id="wait-for-sync"/>
#A Add the token to the master
#B Wait for the slave to sync (if necessary)
#C Wait for the slave to receive the data change
#D Wait up to 1 second
#E Check to see if the data is known to be on disk
#F Clean up our status and clean out older entries that may have been left there
#END

'''
# <start id="master-failover"/>
user@vpn-master ~:$ ssh root@machine-b.vpn                          #A
Last login: Wed Mar 28 15:21:06 2012 from ...                       #A
root@machine-b ~:$ redis-cli                                        #B
redis 127.0.0.1:6379> SAVE                                          #C
OK                                                                  #C
redis 127.0.0.1:6379> QUIT                                          #C
root@machine-b ~:$ scp \\                                           #D
> /var/local/redis/dump.rdb machine-c.vpn:/var/local/redis/         #D
dump.rdb                      100%   525MB  8.1MB/s   01:05         #D
root@machine-b ~:$ ssh machine-c.vpn                                #E
Last login: Tue Mar 27 12:42:31 2012 from ...                       #E
root@machine-c ~:$ sudo /etc/init.d/redis-server start              #E
Starting Redis server...                                            #E
root@machine-c ~:$ exit
root@machine-b ~:$ redis-cli                                        #F
redis 127.0.0.1:6379> SLAVEOF machine-c.vpn 6379                    #F
OK                                                                  #F
redis 127.0.0.1:6379> QUIT
root@machine-b ~:$ exit
user@vpn-master ~:$
# <end id="master-failover"/>
#A Connect to machine B on our vpn network
#B Start up the command line redis client to do a few simple operations
#C Start a SAVE, and when it is done, QUIT so that we can continue
#D Copy the snapshot over to the new master, machine C
#E Connect to the new master and start Redis
#F Tell machine B's Redis that it should use C as the new master
#END
'''

# <start id="_1313_14472_8342"/>
def list_item(conn, itemid, sellerid, price):
    inventory = "inventory:%s"%sellerid
    item = "%s.%s"%(itemid, sellerid)
    end = time.time() + 5
    pipe = conn.pipeline()

    while time.time() < end:
        try:
            pipe.watch(inventory)                    #A
            if not pipe.sismember(inventory, itemid):#B
                pipe.unwatch()                       #E
                return None

            pipe.multi()                             #C
            pipe.zadd("market:", item, price)        #C
            pipe.srem(inventory, itemid)             #C
            pipe.execute()                           #F
            return True
        except redis.exceptions.WatchError:          #D
            pass                                     #D
    return False
# <end id="_1313_14472_8342"/>
#A Watch for changes to the users's inventory
#B Verify that the user still has the item to be listed
#E If the item is not in the user's inventory, stop watching the inventory key and return
#C Actually list the item
#F If execute returns without a WatchError being raised, then the transaction is complete and the inventory key is no longer watched
#D The user's inventory was changed, retry
#END

# <start id="_1313_14472_8353"/>
def purchase_item(conn, buyerid, itemid, sellerid, lprice):
    buyer = "users:%s"%buyerid
    seller = "users:%s"%sellerid
    item = "%s.%s"%(itemid, sellerid)
    inventory = "inventory:%s"%buyerid
    end = time.time() + 10
    pipe = conn.pipeline()

    while time.time() < end:
        try:
            pipe.watch("market:", buyer)                #A

            price = pipe.zscore("market:", item)        #B
            funds = int(pipe.hget(buyer, "funds"))      #B
            if price != lprice or price > funds:        #B
                pipe.unwatch()                          #B
                return None

            pipe.multi()                                #C
            pipe.hincrby(seller, "funds", int(price))   #C
            pipe.hincrby(buyer, "funds", int(-price))   #C
            pipe.sadd(inventory, itemid)                #C
            pipe.zrem("market:", item)                  #C
            pipe.execute()                              #C
            return True
        except redis.exceptions.WatchError:             #D
            pass                                        #D

    return False
# <end id="_1313_14472_8353"/>
#A Watch for changes to the market and to the buyer's account information
#B Check for a sold/repriced item or insufficient funds
#C Transfer funds from the buyer to the seller, and transfer the item to the buyer
#D Retry if the buyer's account or the market changed
#END


# <start id="update-token"/>
def update_token(conn, token, user, item=None):
    timestamp = time.time()                             #A
    conn.hset('login:', token, user)                    #B
    conn.zadd('recent:', token, timestamp)              #C
    if item:
        conn.zadd('viewed:' + token, item, timestamp)   #D
        conn.zremrangebyrank('viewed:' + token, 0, -26) #E
        conn.zincrby('viewed:', item, -1)               #F
# <end id="update-token"/>
#A Get the timestamp
#B Keep a mapping from the token to the logged-in user
#C Record when the token was last seen
#D Record that the user viewed the item
#E Remove old items, keeping the most recent 25
#F Update the number of times the given item had been viewed
#END

# <start id="update-token-pipeline"/>
def update_token_pipeline(conn, token, user, item=None):
    timestamp = time.time()
    pipe = conn.pipeline(False)                         #A
    pipe.hset('login:', token, user)
    pipe.zadd('recent:', token, timestamp)
    if item:
        pipe.zadd('viewed:' + token, item, timestamp)
        pipe.zremrangebyrank('viewed:' + token, 0, -26)
        pipe.zincrby('viewed:', item, -1)
    pipe.execute()                                      #B
# <end id="update-token-pipeline"/>
#A Set up the pipeline
#B Execute the commands in the pipeline
#END

# <start id="simple-pipeline-benchmark-code"/>
def benchmark_update_token(conn, duration):
    for function in (update_token, update_token_pipeline):      #A
        count = 0                                               #B
        start = time.time()                                     #B
        end = start + duration                                  #B
        while time.time() < end:
            count += 1
            function(conn, 'token', 'user', 'item')             #C
        delta = time.time() - start                             #D
        print function.__name__, count, delta, count / delta    #E
# <end id="simple-pipeline-benchmark-code"/>
#A Execute both the update_token() and the update_token_pipeline() functions
#B Set up our counters and our ending conditions
#C Call one of the two functions
#D Calculate the duration
#E Print information about the results
#END

'''
# <start id="redis-benchmark"/>
$ redis-benchmark  -c 1 -q                               #A
PING (inline): 34246.57 requests per second
PING: 34843.21 requests per second
MSET (10 keys): 24213.08 requests per second
SET: 32467.53 requests per second
GET: 33112.59 requests per second
INCR: 32679.74 requests per second
LPUSH: 33333.33 requests per second
LPOP: 33670.04 requests per second
SADD: 33222.59 requests per second
SPOP: 34482.76 requests per second
LPUSH (again, in order to bench LRANGE): 33222.59 requests per second
LRANGE (first 100 elements): 22988.51 requests per second
LRANGE (first 300 elements): 13888.89 requests per second
LRANGE (first 450 elements): 11061.95 requests per second
LRANGE (first 600 elements): 9041.59 requests per second
# <end id="redis-benchmark"/>
#A We run with the '-q' option to get simple output, and '-c 1' to use a single client
#END
'''

#--------------- Below this line are helpers to test the code ----------------

class TestCh04(unittest.TestCase):
    def setUp(self):
        import redis
        self.conn = redis.Redis(db=15)
        self.conn.flushdb()

    def tearDown(self):
        self.conn.flushdb()
        del self.conn
        print
        print

    # We can't test process_logs, as that would require writing to disk, which
    # we don't want to do.

    # We also can't test wait_for_sync, as we can't guarantee that there are
    # multiple Redis servers running with the proper configuration

    def test_list_item(self):
        import pprint
        conn = self.conn

        print "We need to set up just enough state so that a user can list an item"
        seller = 'userX'
        item = 'itemX'
        conn.sadd('inventory:' + seller, item)
        i = conn.smembers('inventory:' + seller)
        print "The user's inventory has:", i
        self.assertTrue(i)
        print

        print "Listing the item..."
        l = list_item(conn, item, seller, 10)
        print "Listing the item succeeded?", l
        self.assertTrue(l)
        r = conn.zrange('market:', 0, -1, withscores=True)
        print "The market contains:"
        pprint.pprint(r)
        self.assertTrue(r)
        self.assertTrue(any(x[0] == 'itemX.userX' for x in r))

    def test_purchase_item(self):
        self.test_list_item()
        conn = self.conn
        
        print "We need to set up just enough state so a user can buy an item"
        buyer = 'userY'
        conn.hset('users:userY', 'funds', 125)
        r = conn.hgetall('users:userY')
        print "The user has some money:", r
        self.assertTrue(r)
        self.assertTrue(r.get('funds'))
        print

        print "Let's purchase an item"
        p = purchase_item(conn, 'userY', 'itemX', 'userX', 10)
        print "Purchasing an item succeeded?", p
        self.assertTrue(p)
        r = conn.hgetall('users:userY')
        print "Their money is now:", r
        self.assertTrue(r)
        i = conn.smembers('inventory:' + buyer)
        print "Their inventory is now:", i
        self.assertTrue(i)
        self.assertTrue('itemX' in i)
        self.assertEquals(conn.zscore('market:', 'itemX.userX'), None)

    def test_benchmark_update_token(self):
        benchmark_update_token(self.conn, 5)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch05_listing_source

import bisect
import contextlib
import csv
from datetime import datetime
import functools
import json
import logging
import random
import threading
import time
import unittest
import uuid

import redis

QUIT = False
SAMPLE_COUNT = 100

config_connection = None

# <start id="recent_log"/>
SEVERITY = {                                                    #A
    logging.DEBUG: 'debug',                                     #A
    logging.INFO: 'info',                                       #A
    logging.WARNING: 'warning',                                 #A
    logging.ERROR: 'error',                                     #A
    logging.CRITICAL: 'critical',                               #A
}                                                               #A
SEVERITY.update((name, name) for name in SEVERITY.values())     #A

def log_recent(conn, name, message, severity=logging.INFO, pipe=None):
    severity = str(SEVERITY.get(severity, severity)).lower()    #B
    destination = 'recent:%s:%s'%(name, severity)               #C
    message = time.asctime() + ' ' + message                    #D
    pipe = pipe or conn.pipeline()                              #E
    pipe.lpush(destination, message)                            #F
    pipe.ltrim(destination, 0, 99)                              #G
    pipe.execute()                                              #H
# <end id="recent_log"/>
#A Set up a mapping that should help turn most logging severity levels into something consistent
#B Actually try to turn a logging level into a simple string
#C Create the key that messages will be written to
#D Add the current time so that we know when the message was sent
#E Set up a pipeline so we only need 1 round trip
#F Add the message to the beginning of the log list
#G Trim the log list to only include the most recent 100 messages
#H Execute the two commands
#END

# <start id="common_log"/>
def log_common(conn, name, message, severity=logging.INFO, timeout=5):
    severity = str(SEVERITY.get(severity, severity)).lower()    #A
    destination = 'common:%s:%s'%(name, severity)               #B
    start_key = destination + ':start'                          #C
    pipe = conn.pipeline()
    end = time.time() + timeout
    while time.time() < end:
        try:
            pipe.watch(start_key)                               #D
            now = datetime.utcnow().timetuple()                 #E
            hour_start = datetime(*now[:4]).isoformat()         #F

            existing = pipe.get(start_key)
            pipe.multi()                                        #H
            if existing and existing < hour_start:              #G
                pipe.rename(destination, destination + ':last') #I
                pipe.rename(start_key, destination + ':pstart') #I
                pipe.set(start_key, hour_start)                 #J

            pipe.zincrby(destination, message)                  #K
            log_recent(pipe, name, message, severity, pipe)     #L
            return
        except redis.exceptions.WatchError:
            continue                                            #M
# <end id="common_log"/>
#A Handle the logging level
#B Set up the destination key for keeping recent logs
#C Keep a record of the start of the hour for this set of messages
#D We are going to watch the start of the hour key for changes that only happen at the beginning of the hour
#E Get the current time
#F Find the current start hour
#G If the current list of common logs is for a previous hour
#H Set up the transaction
#I Move the old common log information to the archive
#J Update the start of the current hour for the common logs
#K Actually increment our common counter
#L Call the log_recent() function to record these there, and rely on its call to execute()
#M If we got a watch error from someone else archiving, try again
#END

# <start id="update_counter"/>
PRECISION = [1, 5, 60, 300, 3600, 18000, 86400]         #A

def update_counter(conn, name, count=1, now=None):
    now = now or time.time()                            #B
    pipe = conn.pipeline()                              #C
    for prec in PRECISION:                              #D
        pnow = int(now / prec) * prec                   #E
        hash = '%s:%s'%(prec, name)                     #F
        pipe.zadd('known:', hash, 0)                    #G
        pipe.hincrby('count:' + hash, pnow, count)      #H
    pipe.execute()
# <end id="update_counter"/>
#A The precision of the counters in seconds: 1 second, 5 seconds, 1 minute, 5 minutes, 1 hour, 5 hours, 1 day - adjust as necessary
#B Get the current time to know when is the proper time to add to
#C Create a transactional pipeline so that later cleanup can work correctly
#D Add entries for all precisions that we record
#E Get the start of the current time slice
#F Create the named hash where this data will be stored
#G Record a reference to the counters into a ZSET with the score 0 so we can clean up after ourselves
#H Update the counter for the given name and time precision
#END

# <start id="get_counter"/>
def get_counter(conn, name, precision):
    hash = '%s:%s'%(precision, name)                #A
    data = conn.hgetall('count:' + hash)            #B
    to_return = []                                  #C
    for key, value in data.iteritems():             #C
        to_return.append((int(key), int(value)))    #C
    to_return.sort()                                #D
    return to_return
# <end id="get_counter"/>
#A Get the name of the key where we will be storing counter data
#B Fetch the counter data from Redis
#C Convert the counter data into something more expected
#D Sort our data so that older samples are first
#END

# <start id="clean_counters"/>
def clean_counters(conn):
    pipe = conn.pipeline(True)
    passes = 0                                                  #A
    while not QUIT:                                             #C
        start = time.time()                                     #D
        index = 0                                               #E
        while index < conn.zcard('known:'):                     #E
            hash = conn.zrange('known:', index, index)          #F
            index += 1
            if not hash:
                break
            hash = hash[0]
            prec = int(hash.partition(':')[0])                  #G
            bprec = int(prec // 60) or 1                        #H
            if passes % bprec:                                  #I
                continue

            hkey = 'count:' + hash
            cutoff = time.time() - SAMPLE_COUNT * prec          #J
            samples = map(int, conn.hkeys(hkey))                #K
            samples.sort()                                      #L
            remove = bisect.bisect_right(samples, cutoff)       #L

            if remove:                                          #M
                conn.hdel(hkey, *samples[:remove])              #M
                if remove == len(samples):                      #N
                    try:
                        pipe.watch(hkey)                        #O
                        if not pipe.hlen(hkey):                 #P
                            pipe.multi()                        #P
                            pipe.zrem('known:', hash)           #P
                            pipe.execute()                      #P
                            index -= 1                          #B
                        else:
                            pipe.unwatch()                      #Q
                    except redis.exceptions.WatchError:         #R
                        pass                                    #R

        passes += 1                                             #S
        duration = min(int(time.time() - start) + 1, 60)        #S
        time.sleep(max(60 - duration, 1))                       #T
# <end id="clean_counters"/>
#A Keep a record of the number of passes so that we can balance cleaning out per-second vs. per-day counters
#C Keep cleaning out counters until we are told to stop
#D Get the start time of the pass to calculate the total duration
#E Incrementally iterate over all known counters
#F Get the next counter to check
#G Get the precision of the counter
#H We are going to be taking a pass every 60 seconds or so, so we are going to try to clean out counters at roughly the rate that they are written to
#I Try the next counter if we aren't supposed to check this one on this pass (for example, we have taken 3 passes, but the counter has a precision of 5 minutes)
#J Find the cutoff time for the earliest sample that we should keep, given the precision and number of samples that we want to keep
#K Fetch the times of the samples, and convert the strings to integers
#L Determine the number of samples that should be deleted
#M Remove the samples as necessary
#N We have a reason to potentially remove the counter from the list of known counters ZSET
#O Watch the counter hash for changes
#P Verify that the counter hash is empty, and if so, remove it from the known counters
#B If we deleted a counter, then we can use the same index next pass
#Q The hash is not empty, keep it in the list of known counters
#R Someone else changed the counter hash by adding counters, which means that it has data, so we will leave the counter in the list of known counters
#S Update our passes and duration variables for the next pass, as an attempt to clean out counters as often as they are seeing updates
#T Sleep the remainder of the 60 seconds, or at least 1 second, just to offer a bit of a rest
#END

# <start id="update_stats"/>
def update_stats(conn, context, type, value, timeout=5):
    destination = 'stats:%s:%s'%(context, type)                 #A
    start_key = destination + ':start'                          #B
    pipe = conn.pipeline(True)
    end = time.time() + timeout
    while time.time() < end:
        try:
            pipe.watch(start_key)                               #B
            now = datetime.utcnow().timetuple()                 #B
            hour_start = datetime(*now[:4]).isoformat()         #B

            existing = pipe.get(start_key)
            pipe.multi()
            if existing and existing < hour_start:
                pipe.rename(destination, destination + ':last') #B
                pipe.rename(start_key, destination + ':pstart') #B
                pipe.set(start_key, hour_start)                 #B

            tkey1 = str(uuid.uuid4())
            tkey2 = str(uuid.uuid4())
            pipe.zadd(tkey1, 'min', value)                      #C
            pipe.zadd(tkey2, 'max', value)                      #C
            pipe.zunionstore(destination,                       #D
                [destination, tkey1], aggregate='min')          #D
            pipe.zunionstore(destination,                       #D
                [destination, tkey2], aggregate='max')          #D

            pipe.delete(tkey1, tkey2)                           #E
            pipe.zincrby(destination, 'count')                  #F
            pipe.zincrby(destination, 'sum', value)             #F
            pipe.zincrby(destination, 'sumsq', value*value)     #F

            return pipe.execute()[-3:]                          #G
        except redis.exceptions.WatchError:
            continue                                            #H
# <end id="update_stats"/>
#A Set up the destination statistics key
#B Handle the current hour/last hour like in common_log()
#C Add the value to the temporary keys
#D Union the temporary keys with the destination stats key with the appropriate min/max aggregate
#E Clean up the temporary keys
#F Update the count, sum, and sum of squares members of the zset
#G Return the base counter info so that the caller can do something interesting if necessary
#H If the hour just turned over and the stats have already been shuffled over, try again
#END

# <start id="get_stats"/>
def get_stats(conn, context, type):
    key = 'stats:%s:%s'%(context, type)                                 #A
    data = dict(conn.zrange(key, 0, -1, withscores=True))               #B
    data['average'] = data['sum'] / data['count']                       #C
    numerator = data['sumsq'] - data['sum'] ** 2 / data['count']        #D
    data['stddev'] = (numerator / (data['count'] - 1 or 1)) ** .5       #E
    return data
# <end id="get_stats"/>
#A Set up the key that we are fetching our statistics from
#B Fetch our basic statistics and package them as a dictionary
#C Calculate the average
#D Prepare the first part of the calculation of standard deviation
#E Finish our calculation of standard deviation
#END


# <start id="access_time_context_manager"/>
@contextlib.contextmanager                                              #A
def access_time(conn, context):
    start = time.time()                                                 #B
    yield                                                               #C

    delta = time.time() - start                                         #D
    stats = update_stats(conn, context, 'AccessTime', delta)            #E
    average = stats[1] / stats[0]                                       #F

    pipe = conn.pipeline(True)
    pipe.zadd('slowest:AccessTime', context, average)                   #G
    pipe.zremrangebyrank('slowest:AccessTime', 0, -101)                 #H
    pipe.execute()
# <end id="access_time_context_manager"/>
#A Make this Python generator into a context manager
#B Record the start time
#C Let the block of code that we are wrapping run
#D Calculate the time that the block took to execute
#E Update the stats for this context
#F Calculate the average
#G Add the average to a ZSET that holds the slowest access times
#H Keep the slowest 100 items in the AccessTime ZSET
#END

# <start id="access_time_use"/>
def process_view(conn, callback):               #A
    with access_time(conn, request.path):       #B
        return callback()                       #C
# <end id="access_time_use"/>
#A This example web view takes the Redis connection as well as a callback to generate the content
#B This is how you would use the access time context manager to wrap a block of code
#C This is executed when the 'yield' statement is hit from within the context manager
#END

# <start id="_1314_14473_9188"/>
def ip_to_score(ip_address):
    score = 0
    for v in ip_address.split('.'):
        score = score * 256 + int(v, 10)
    return score
# <end id="_1314_14473_9188"/>
#END

# <start id="_1314_14473_9191"/>
def import_ips_to_redis(conn, filename):                #A
    csv_file = csv.reader(open(filename, 'rb'))
    for count, row in enumerate(csv_file):
        start_ip = row[0] if row else ''                #B
        if 'i' in start_ip.lower():
            continue
        if '.' in start_ip:                             #B
            start_ip = ip_to_score(start_ip)            #B
        elif start_ip.isdigit():                        #B
            start_ip = int(start_ip, 10)                #B
        else:
            continue                                    #C

        city_id = row[2] + '_' + str(count)             #D
        conn.zadd('ip2cityid:', city_id, start_ip)      #E
# <end id="_1314_14473_9191"/>
#A Should be run with the location of the GeoLiteCity-Blocks.csv file
#B Convert the IP address to a score as necessary
#C Header row or malformed entry
#D Construct the unique city id
#E Add the IP address score and City ID
#END

# <start id="_1314_14473_9194"/>
def import_cities_to_redis(conn, filename):         #A
    for row in csv.reader(open(filename, 'rb')):
        if len(row) < 4 or not row[0].isdigit():
            continue
        row = [i.decode('latin-1') for i in row]
        city_id = row[0]                            #B
        country = row[1]                            #B
        region = row[2]                             #B
        city = row[3]                               #B
        conn.hset('cityid2city:', city_id,          #C
            json.dumps([city, region, country]))    #C
# <end id="_1314_14473_9194"/>
#A Should be run with the location of the GeoLiteCity-Location.csv file
#B Prepare the information for adding to the hash
#C Actually add the city information to Redis
#END

# <start id="_1314_14473_9197"/>
def find_city_by_ip(conn, ip_address):
    if isinstance(ip_address, str):                        #A
        ip_address = ip_to_score(ip_address)               #A

    city_id = conn.zrevrangebyscore(                       #B
        'ip2cityid:', ip_address, 0, start=0, num=1)       #B

    if not city_id:
        return None

    city_id = city_id[0].partition('_')[0]                 #C
    return json.loads(conn.hget('cityid2city:', city_id))  #D
# <end id="_1314_14473_9197"/>
#A Convert the IP address to a score for zrevrangebyscore
#B Find the uique city ID
#C Convert the unique city ID to the common city ID
#D Fetch the city information from the hash
#END

# <start id="is_under_maintenance"/>
LAST_CHECKED = None
IS_UNDER_MAINTENANCE = False

def is_under_maintenance(conn):
    global LAST_CHECKED, IS_UNDER_MAINTENANCE   #A

    if LAST_CHECKED < time.time() - 1:          #B
        LAST_CHECKED = time.time()              #C
        IS_UNDER_MAINTENANCE = bool(            #D
            conn.get('is-under-maintenance'))   #D

    return IS_UNDER_MAINTENANCE                 #E
# <end id="is_under_maintenance"/>
#A Set the two variables as globals so we can write to them later
#B Check to see if it has been at least 1 second since we last checked
#C Update the last checked time
#D Find out whether the system is under maintenance
#E Return whether the system is under maintenance
#END

# <start id="set_config"/>
def set_config(conn, type, component, config):
    conn.set(
        'config:%s:%s'%(type, component),
        json.dumps(config))
# <end id="set_config"/>
#END

# <start id="get_config"/>
CONFIGS = {}
CHECKED = {}

def get_config(conn, type, component, wait=1):
    key = 'config:%s:%s'%(type, component)

    if CHECKED.get(key) < time.time() - wait:           #A
        CHECKED[key] = time.time()                      #B
        config = json.loads(conn.get(key) or '{}')      #C
        config = dict((str(k), config[k]) for k in config)#G
        old_config = CONFIGS.get(key)                   #D

        if config != old_config:                        #E
            CONFIGS[key] = config                       #F

    return CONFIGS.get(key)
# <end id="get_config"/>
#A Check to see if we should update the configuration information about this component
#B We can, so update the last time we checked this connection
#C Fetch the configuration for this component
#G Convert potentially unicode keyword arguments into string keyword arguments
#D Get the old configuration for this component
#E If the configurations are different
#F Update the configuration
#END

# <start id="redis_connection"/>
REDIS_CONNECTIONS = {}

def redis_connection(component, wait=1):                        #A
    key = 'config:redis:' + component                           #B
    def wrapper(function):                                      #C
        @functools.wraps(function)                              #D
        def call(*args, **kwargs):                              #E
            old_config = CONFIGS.get(key, object())             #F
            _config = get_config(                               #G
                config_connection, 'redis', component, wait)    #G

            config = {}
            for k, v in _config.iteritems():                    #L
                config[k.encode('utf-8')] = v                   #L

            if config != old_config:                            #H
                REDIS_CONNECTIONS[key] = redis.Redis(**config)  #H

            return function(                                    #I
                REDIS_CONNECTIONS.get(key), *args, **kwargs)    #I
        return call                                             #J
    return wrapper                                              #K
# <end id="redis_connection"/>
#A We pass the name of the application component to the decorator
#B We cache the configuration key because we will be fetching it every time the function is called
#C Our wrapper takes a function that it wraps with another function
#D Copy some useful metadata from the original function to the configuration handler
#E Create the actual function that will be managing connection information
#F Fetch the old configuration, if any
#G Get the new configuration, if any
#L Make the configuration usable for creating a Redis connection
#H If the new and old configuration do not match, create a new connection
#I Call and return the result of our wrapped function, remembering to pass the connection and the other matched arguments
#J Return the fully wrapped function
#K Return a function that can wrap our Redis function
#END

'''
# <start id="recent_log_decorator"/>
@redis_connection('logs')                   #A
def log_recent(conn, app, message):         #B
    'the old log_recent() code'

log_recent('main', 'User 235 logged in')    #C
# <end id="recent_log_decorator"/>
#A The redis_connection() decorator is very easy to use
#B The function definition doesn't change
#C You no longer need to worry about passing the log server connection when calling log_recent()
#END
'''

#--------------- Below this line are helpers to test the code ----------------

class request:
    pass

# a faster version with pipelines for actual testing
def import_ips_to_redis(conn, filename):
    csv_file = csv.reader(open(filename, 'rb'))
    pipe = conn.pipeline(False)
    for count, row in enumerate(csv_file):
        start_ip = row[0] if row else ''
        if 'i' in start_ip.lower():
            continue
        if '.' in start_ip:
            start_ip = ip_to_score(start_ip)
        elif start_ip.isdigit():
            start_ip = int(start_ip, 10)
        else:
            continue

        city_id = row[2] + '_' + str(count)
        pipe.zadd('ip2cityid:', city_id, start_ip)
        if not (count+1) % 1000:
            pipe.execute()
    pipe.execute()

def import_cities_to_redis(conn, filename):
    pipe = conn.pipeline(False)
    for count, row in enumerate(csv.reader(open(filename, 'rb'))):
        if len(row) < 4 or not row[0].isdigit():
            continue
        row = [i.decode('latin-1') for i in row]
        city_id = row[0]
        country = row[1]
        region = row[2]
        city = row[3]
        pipe.hset('cityid2city:', city_id,
            json.dumps([city, region, country]))
        if not (count+1) % 1000:
            pipe.execute()
    pipe.execute()

class TestCh05(unittest.TestCase):
    def setUp(self):
        global config_connection
        import redis
        self.conn = config_connection = redis.Redis(db=15)
        self.conn.flushdb()

    def tearDown(self):
        self.conn.flushdb()
        del self.conn
        global config_connection, QUIT, SAMPLE_COUNT
        config_connection = None
        QUIT = False
        SAMPLE_COUNT = 100
        print
        print

    def test_log_recent(self):
        import pprint
        conn = self.conn

        print "Let's write a few logs to the recent log"
        for msg in xrange(5):
            log_recent(conn, 'test', 'this is message %s'%msg)
        recent = conn.lrange('recent:test:info', 0, -1)
        print "The current recent message log has this many messages:", len(recent)
        print "Those messages include:"
        pprint.pprint(recent[:10])
        self.assertTrue(len(recent) >= 5)

    def test_log_common(self):
        import pprint
        conn = self.conn

        print "Let's write some items to the common log"
        for count in xrange(1, 6):
            for i in xrange(count):
                log_common(conn, 'test', "message-%s"%count)
        common = conn.zrevrange('common:test:info', 0, -1, withscores=True)
        print "The current number of common messages is:", len(common)
        print "Those common messages are:"
        pprint.pprint(common)
        self.assertTrue(len(common) >= 5)

    def test_counters(self):
        import pprint
        global QUIT, SAMPLE_COUNT
        conn = self.conn

        print "Let's update some counters for now and a little in the future"
        now = time.time()
        for delta in xrange(10):
            update_counter(conn, 'test', count=random.randrange(1,5), now=now+delta)
        counter = get_counter(conn, 'test', 1)
        print "We have some per-second counters:", len(counter)
        self.assertTrue(len(counter) >= 10)
        counter = get_counter(conn, 'test', 5)
        print "We have some per-5-second counters:", len(counter)
        print "These counters include:"
        pprint.pprint(counter[:10])
        self.assertTrue(len(counter) >= 2)
        print

        tt = time.time
        def new_tt():
            return tt() + 2*86400
        time.time = new_tt

        print "Let's clean out some counters by setting our sample count to 0"
        SAMPLE_COUNT = 0
        t = threading.Thread(target=clean_counters, args=(conn,))
        t.setDaemon(1) # to make sure it dies if we ctrl+C quit
        t.start()
        time.sleep(1)
        QUIT = True
        time.time = tt
        counter = get_counter(conn, 'test', 86400)
        print "Did we clean out all of the counters?", not counter
        self.assertFalse(counter)

    def test_stats(self):
        import pprint
        conn = self.conn

        print "Let's add some data for our statistics!"
        for i in xrange(5):
            r = update_stats(conn, 'temp', 'example', random.randrange(5, 15))
        print "We have some aggregate statistics:", r
        rr = get_stats(conn, 'temp', 'example')
        print "Which we can also fetch manually:"
        pprint.pprint(rr)
        self.assertTrue(rr['count'] >= 5)

    def test_access_time(self):
        import pprint
        conn = self.conn

        print "Let's calculate some access times..."
        for i in xrange(10):
            with access_time(conn, "req-%s"%i):
                time.sleep(.5 + random.random())
        print "The slowest access times are:"
        atimes = conn.zrevrange('slowest:AccessTime', 0, -1, withscores=True)
        pprint.pprint(atimes[:10])
        self.assertTrue(len(atimes) >= 10)
        print

        def cb():
            time.sleep(1 + random.random())

        print "Let's use the callback version..."
        for i in xrange(5):
            request.path = 'cbreq-%s'%i
            process_view(conn, cb)
        print "The slowest access times are:"
        atimes = conn.zrevrange('slowest:AccessTime', 0, -1, withscores=True)
        pprint.pprint(atimes[:10])
        self.assertTrue(len(atimes) >= 10)

    def test_ip_lookup(self):
        conn = self.conn

        try:
            open('GeoLiteCity-Blocks.csv', 'rb')
            open('GeoLiteCity-Location.csv', 'rb')
        except:
            print "********"
            print "You do not have the GeoLiteCity database available, aborting test"
            print "Please have the following two files in the current path:"
            print "GeoLiteCity-Blocks.csv"
            print "GeoLiteCity-Location.csv"
            print "********"
            return

        print "Importing IP addresses to Redis... (this may take a while)"
        import_ips_to_redis(conn, 'GeoLiteCity-Blocks.csv')
        ranges = conn.zcard('ip2cityid:')
        print "Loaded ranges into Redis:", ranges
        self.assertTrue(ranges > 1000)
        print

        print "Importing Location lookups to Redis... (this may take a while)"
        import_cities_to_redis(conn, 'GeoLiteCity-Location.csv')
        cities = conn.hlen('cityid2city:')
        print "Loaded city lookups into Redis:", cities
        self.assertTrue(cities > 1000)
        print

        print "Let's lookup some locations!"
        rr = random.randrange
        for i in xrange(5):
            print find_city_by_ip(conn, '%s.%s.%s.%s'%(rr(1,255), rr(256), rr(256), rr(256)))

    def test_is_under_maintenance(self):
        print "Are we under maintenance (we shouldn't be)?", is_under_maintenance(self.conn)
        self.conn.set('is-under-maintenance', 'yes')
        print "We cached this, so it should be the same:", is_under_maintenance(self.conn)
        time.sleep(1)
        print "But after a sleep, it should change:", is_under_maintenance(self.conn)
        print "Cleaning up..."
        self.conn.delete('is-under-maintenance')
        time.sleep(1)
        print "Should be False again:", is_under_maintenance(self.conn)

    def test_config(self):
        print "Let's set a config and then get a connection from that config..."
        set_config(self.conn, 'redis', 'test', {'db':15})
        @redis_connection('test')
        def test(conn2):
            return bool(conn2.info())
        print "We can run commands from the configured connection:", test()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch06_listing_source

import bisect
from collections import defaultdict, deque
import json
import math
import os
import time
import unittest
import uuid
import zlib

import redis

QUIT = False
pipe = inv = item = market = buyer = seller = inventory = None

# <start id="_1314_14473_8380"/>
def add_update_contact(conn, user, contact):
    ac_list = 'recent:' + user
    pipeline = conn.pipeline(True)     #A
    pipeline.lrem(ac_list, contact)    #B
    pipeline.lpush(ac_list, contact)   #C
    pipeline.ltrim(ac_list, 0, 99)     #D
    pipeline.execute()                 #E
# <end id="_1314_14473_8380"/>
#A Set up the atomic operation
#B Remove the contact from the list if it exists
#C Push the item onto the front of the list
#D Remove anything beyond the 100th item
#E Actually execute everything
#END

# <start id="_1314_14473_8383"/>
def remove_contact(conn, user, contact):
    conn.lrem('recent:' + user, contact)
# <end id="_1314_14473_8383"/>
#END

# <start id="_1314_14473_8386"/>
def fetch_autocomplete_list(conn, user, prefix):
    candidates = conn.lrange('recent:' + user, 0, -1) #A
    matches = []
    for candidate in candidates:                      #B
        if candidate.lower().startswith(prefix):      #B
            matches.append(candidate)                 #C
    return matches                                    #D
# <end id="_1314_14473_8386"/>
#A Fetch the autocomplete list
#B Check each candidate
#C We found a match
#D Return all of the matches
#END

# <start id="_1314_14473_8396"/>
valid_characters = '`abcdefghijklmnopqrstuvwxyz{'             #A

def find_prefix_range(prefix):
    posn = bisect.bisect_left(valid_characters, prefix[-1:])  #B
    suffix = valid_characters[(posn or 1) - 1]                #C
    return prefix[:-1] + suffix + '{', prefix + '{'           #D
# <end id="_1314_14473_8396"/>
#A Set up our list of characters that we know about
#B Find the position of prefix character in our list of characters
#C Find the predecessor character
#D Return the range
#END

# <start id="_1314_14473_8399"/>
def autocomplete_on_prefix(conn, guild, prefix):
    start, end = find_prefix_range(prefix)                 #A
    identifier = str(uuid.uuid4())                         #A
    start += identifier                                    #A
    end += identifier                                      #A
    zset_name = 'members:' + guild

    conn.zadd(zset_name, start, 0, end, 0)                 #B
    pipeline = conn.pipeline(True)
    while 1:
        try:
            pipeline.watch(zset_name)
            sindex = pipeline.zrank(zset_name, start)      #C
            eindex = pipeline.zrank(zset_name, end)        #C
            erange = min(sindex + 9, eindex - 2)           #C
            pipeline.multi()
            pipeline.zrem(zset_name, start, end)           #D
            pipeline.zrange(zset_name, sindex, erange)     #D
            items = pipeline.execute()[-1]                 #D
            break
        except redis.exceptions.WatchError:                #E
            continue                                       #E

    return [item for item in items if '{' not in item]     #F
# <end id="_1314_14473_8399"/>
#A Find the start/end range for the prefix
#B Add the start/end range items to the ZSET
#C Find the ranks of our end points
#D Get the values inside our range, and clean up
#E Retry if someone modified our autocomplete zset
#F Remove start/end entries if an autocomplete was in progress
#END

# <start id="_1314_14473_8403"/>
def join_guild(conn, guild, user):
    conn.zadd('members:' + guild, user, 0)

def leave_guild(conn, guild, user):
    conn.zrem('members:' + guild, user)
# <end id="_1314_14473_8403"/>
#END

# <start id="_1314_14473_8431"/>
def list_item(conn, itemid, sellerid, price):
    #...
            pipe.watch(inv)                             #A
            if not pipe.sismember(inv, itemid):         #B
                pipe.unwatch()                          #B
                return None

            pipe.multi()                                #C
            pipe.zadd("market:", item, price)           #C
            pipe.srem(inv, itemid)                      #C
            pipe.execute()                              #C
            return True
    #...
# <end id="_1314_14473_8431"/>
#A Watch for changes to the users's inventory
#B Verify that the user still has the item to be listed
#C Actually list the item
#END

# <start id="_1314_14473_8435"/>
def purchase_item(conn, buyerid, itemid, sellerid, lprice):
    #...
            pipe.watch("market:", buyer)                #A

            price = pipe.zscore("market:", item)        #B
            funds = int(pipe.hget(buyer, 'funds'))      #B
            if price != lprice or price > funds:        #B
                pipe.unwatch()                          #B
                return None

            pipe.multi()                                #C
            pipe.hincrby(seller, 'funds', int(price))   #C
            pipe.hincrby(buyerid, 'funds', int(-price)) #C
            pipe.sadd(inventory, itemid)                #C
            pipe.zrem("market:", item)                  #C
            pipe.execute()                              #C
            return True

    #...
# <end id="_1314_14473_8435"/>
#A Watch for changes to the market and the buyer's account information
#B Check for a sold/repriced item or insufficient funds
#C Transfer funds from the buyer to the seller, and transfer the item to the buyer
#END

# <start id="_1314_14473_8641"/>
def acquire_lock(conn, lockname, acquire_timeout=10):
    identifier = str(uuid.uuid4())                      #A

    end = time.time() + acquire_timeout
    while time.time() < end:
        if conn.setnx('lock:' + lockname, identifier):  #B
            return identifier

        time.sleep(.001)

    return False
# <end id="_1314_14473_8641"/>
#A A 128-bit random identifier
#B Get the lock
#END

# <start id="_1314_14473_8645"/>
def purchase_item_with_lock(conn, buyerid, itemid, sellerid):
    buyer = "users:%s"%buyerid
    seller = "users:%s"%sellerid
    item = "%s.%s"%(itemid, sellerid)
    inventory = "inventory:%s"%buyerid
    end = time.time() + 30

    locked = acquire_lock(conn, market)                #A
    if not locked:
        return False

    pipe = conn.pipeline(True)
    try:
        while time.time() < end:
            try:
                pipe.zscore("market:", item)           #B
                pipe.hget(buyer, 'funds')              #B
                price, funds = pipe.execute()          #B
                if price is None or price > funds:     #B
                    pipe.unwatch()                     #B
                    return None                        #B

                pipe.hincrby(seller, 'funds', int(price))  #C
                pipe.hincrby(buyer, 'funds', int(-price))  #C
                pipe.sadd(inventory, itemid)               #C
                pipe.zrem("market:", item)                 #C
                pipe.execute()                             #C
                return True
            except redis.exceptions.WatchError:
                pass
    finally:
        release_lock(conn, market, locked)             #D
# <end id="_1314_14473_8645"/>
#A Get the lock
#B Check for a sold item or insufficient funds
#C Transfer funds from the buyer to the seller, and transfer the item to the buyer
#D Release the lock
#END

# <start id="_1314_14473_8650"/>
def release_lock(conn, lockname, identifier):
    pipe = conn.pipeline(True)
    lockname = 'lock:' + lockname

    while True:
        try:
            pipe.watch(lockname)                  #A
            if pipe.get(lockname) == identifier:  #A
                pipe.multi()                      #B
                pipe.delete(lockname)             #B
                pipe.execute()                    #B
                return True                       #B

            pipe.unwatch()
            break

        except redis.exceptions.WatchError:       #C
            pass                                  #C

    return False                                  #D
# <end id="_1314_14473_8650"/>
#A Check and verify that we still have the lock
#B Release the lock
#C Someone else did something with the lock, retry
#D We lost the lock
#END

# <start id="_1314_14473_8790"/>
def acquire_lock_with_timeout(
    conn, lockname, acquire_timeout=10, lock_timeout=10):
    identifier = str(uuid.uuid4())                      #A
    lockname = 'lock:' + lockname
    lock_timeout = int(math.ceil(lock_timeout))         #D

    end = time.time() + acquire_timeout
    while time.time() < end:
        if conn.setnx(lockname, identifier):            #B
            conn.expire(lockname, lock_timeout)         #B
            return identifier
        elif not conn.ttl(lockname):                    #C
            conn.expire(lockname, lock_timeout)         #C

        time.sleep(.001)

    return False
# <end id="_1314_14473_8790"/>
#A A 128-bit random identifier
#B Get the lock and set the expiration
#C Check and update the expiration time as necessary
#D Only pass integers to our EXPIRE calls
#END

# <start id="_1314_14473_8986"/>
def acquire_semaphore(conn, semname, limit, timeout=10):
    identifier = str(uuid.uuid4())                             #A
    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zremrangebyscore(semname, '-inf', now - timeout)  #B
    pipeline.zadd(semname, identifier, now)                    #C
    pipeline.zrank(semname, identifier)                        #D
    if pipeline.execute()[-1] < limit:                         #D
        return identifier

    conn.zrem(semname, identifier)                             #E
    return None
# <end id="_1314_14473_8986"/>
#A A 128-bit random identifier
#B Time out old semaphore holders
#C Try to acquire the semaphore
#D Check to see if we have it
#E We failed to get the semaphore, discard our identifier
#END

# <start id="_1314_14473_8990"/>
def release_semaphore(conn, semname, identifier):
    return conn.zrem(semname, identifier)                      #A
# <end id="_1314_14473_8990"/>
#A Returns True if the semaphore was properly released, False if it had timed out
#END

# <start id="_1314_14473_9004"/>
def acquire_fair_semaphore(conn, semname, limit, timeout=10):
    identifier = str(uuid.uuid4())                             #A
    czset = semname + ':owner'
    ctr = semname + ':counter'

    now = time.time()
    pipeline = conn.pipeline(True)
    pipeline.zremrangebyscore(semname, '-inf', now - timeout)  #B
    pipeline.zinterstore(czset, {czset: 1, semname: 0})        #B

    pipeline.incr(ctr)                                         #C
    counter = pipeline.execute()[-1]                           #C

    pipeline.zadd(semname, identifier, now)                    #D
    pipeline.zadd(czset, identifier, counter)                  #D

    pipeline.zrank(czset, identifier)                          #E
    if pipeline.execute()[-1] < limit:                         #E
        return identifier                                      #F

    pipeline.zrem(semname, identifier)                         #G
    pipeline.zrem(czset, identifier)                           #G
    pipeline.execute()
    return None
# <end id="_1314_14473_9004"/>
#A A 128-bit random identifier
#B Time out old entries
#C Get the counter
#D Try to acquire the semaphore
#E Check the rank to determine if we got the semaphore
#F We got the semaphore
#G We didn't get the semaphore, clean out the bad data
#END

# <start id="_1314_14473_9014"/>
def release_fair_semaphore(conn, semname, identifier):
    pipeline = conn.pipeline(True)
    pipeline.zrem(semname, identifier)
    pipeline.zrem(semname + ':owner', identifier)
    return pipeline.execute()[0]                               #A
# <end id="_1314_14473_9014"/>
#A Returns True if the semaphore was properly released, False if it had timed out
#END

# <start id="_1314_14473_9022"/>
def refresh_fair_semaphore(conn, semname, identifier):
    if conn.zadd(semname, identifier, time.time()):            #A
        release_fair_semaphore(conn, semname, identifier)      #B
        return False                                           #B
    return True                                                #C
# <end id="_1314_14473_9022"/>
#A Update our semaphore
#B We lost our semaphore, report back
#C We still have our semaphore
#END

# <start id="_1314_14473_9031"/>
def acquire_semaphore_with_lock(conn, semname, limit, timeout=10):
    identifier = acquire_lock(conn, semname, acquire_timeout=.01)
    if identifier:
        try:
            return acquire_fair_semaphore(conn, semname, limit, timeout)
        finally:
            release_lock(conn, semname, identifier)
# <end id="_1314_14473_9031"/>
#END

# <start id="_1314_14473_9056"/>
def send_sold_email_via_queue(conn, seller, item, price, buyer):
    data = {
        'seller_id': seller,                    #A
        'item_id': item,                        #A
        'price': price,                         #A
        'buyer_id': buyer,                      #A
        'time': time.time()                     #A
    }
    conn.rpush('queue:email', json.dumps(data)) #B
# <end id="_1314_14473_9056"/>
#A Prepare the item
#B Push the item onto the queue
#END

# <start id="_1314_14473_9060"/>
def process_sold_email_queue(conn):
    while not QUIT:
        packed = conn.blpop(['queue:email'], 30)                  #A
        if not packed:                                            #B
            continue                                              #B

        to_send = json.loads(packed[1])                           #C
        try:
            fetch_data_and_send_sold_email(to_send)               #D
        except EmailSendError as err:
            log_error("Failed to send sold email", err, to_send)
        else:
            log_success("Sent sold email", to_send)
# <end id="_1314_14473_9060"/>
#A Try to get a message to send
#B No message to send, try again
#C Load the packed email information
#D Send the email using our pre-written emailing function
#END

# <start id="_1314_14473_9066"/>
def worker_watch_queue(conn, queue, callbacks):
    while not QUIT:
        packed = conn.blpop([queue], 30)                    #A
        if not packed:                                      #B
            continue                                        #B

        name, args = json.loads(packed[1])                  #C
        if name not in callbacks:                           #D
            log_error("Unknown callback %s"%name)           #D
            continue                                        #D
        callbacks[name](*args)                              #E
# <end id="_1314_14473_9066"/>
#A Try to get an item from the queue
#B There is nothing to work on, try again
#C Unpack the work item
#D The function is unknown, log the error and try again
#E Execute the task
#END

# <start id="_1314_14473_9074"/>
def worker_watch_queues(conn, queues, callbacks):   #A
    while not QUIT:
        packed = conn.blpop(queues, 30)             #B
        if not packed:
            continue

        name, args = json.loads(packed[1])
        if name not in callbacks:
            log_error("Unknown callback %s"%name)
            continue
        callbacks[name](*args)
# <end id="_1314_14473_9074"/>
#A The first changed line to add priority support
#B The second changed line to add priority support
#END

# <start id="_1314_14473_9094"/>
def execute_later(conn, queue, name, args, delay=0):
    identifier = str(uuid.uuid4())                          #A
    item = json.dumps([identifier, queue, name, args])      #B
    if delay > 0:
        conn.zadd('delayed:', item, time.time() + delay)    #C
    else:
        conn.rpush('queue:' + queue, item)                  #D
    return identifier                                       #E
# <end id="_1314_14473_9094"/>
#A Generate a unique identifier
#B Prepare the item for the queue
#C Delay the item
#D Execute the item immediately
#E Return the identifier
#END

# <start id="_1314_14473_9099"/>
def poll_queue(conn):
    while not QUIT:
        item = conn.zrange('delayed:', 0, 0, withscores=True)   #A
        if not item or item[0][1] > time.time():                #B
            time.sleep(.01)                                     #B
            continue                                            #B

        item = item[0][0]                                       #C
        identifier, queue, function, args = json.loads(item)    #C

        locked = acquire_lock(conn, identifier)                 #D
        if not locked:                                          #E
            continue                                            #E

        if conn.zrem('delayed:', item):                         #F
            conn.rpush('queue:' + queue, item)                  #F

        release_lock(conn, identifier, locked)                  #G
# <end id="_1314_14473_9099"/>
#A Get the first item in the queue
#B No item or the item is still to be execued in the future
#C Unpack the item so that we know where it should go
#D Get the lock for the item
#E We couldn't get the lock, so skip it and try again
#F Move the item to the proper list queue
#G Release the lock
#END

# <start id="_1314_14473_9124"/>
def create_chat(conn, sender, recipients, message, chat_id=None):
    chat_id = chat_id or str(conn.incr('ids:chat:'))      #A

    recipients.append(sender)                             #E
    recipientsd = dict((r, 0) for r in recipients)        #E

    pipeline = conn.pipeline(True)
    pipeline.zadd('chat:' + chat_id, **recipientsd)       #B
    for rec in recipients:                                #C
        pipeline.zadd('seen:' + rec, chat_id, 0)          #C
    pipeline.execute()

    return send_message(conn, chat_id, sender, message)   #D
# <end id="_1314_14473_9124"/>
#A Get a new chat id
#E Set up a dictionary of users to scores to add to the chat ZSET
#B Create the set with the list of people participating
#C Initialize the seen zsets
#D Send the message
#END

# <start id="_1314_14473_9127"/>
def send_message(conn, chat_id, sender, message):
    identifier = acquire_lock(conn, 'chat:' + chat_id)
    if not identifier:
        raise Exception("Couldn't get the lock")
    try:
        mid = conn.incr('ids:' + chat_id)                #A
        ts = time.time()                                 #A
        packed = json.dumps({                            #A
            'id': mid,                                   #A
            'ts': ts,                                    #A
            'sender': sender,                            #A
            'message': message,                          #A
        })                                               #A

        conn.zadd('msgs:' + chat_id, packed, mid)        #B
    finally:
        release_lock(conn, 'chat:' + chat_id, identifier)
    return chat_id
# <end id="_1314_14473_9127"/>
#A Prepare the message
#B Send the message to the chat
#END

# <start id="_1314_14473_9132"/>
def fetch_pending_messages(conn, recipient):
    seen = conn.zrange('seen:' + recipient, 0, -1, withscores=True) #A

    pipeline = conn.pipeline(True)

    for chat_id, seen_id in seen:                               #B
        pipeline.zrangebyscore(                                 #B
            'msgs:' + chat_id, seen_id+1, 'inf')                #B
    chat_info = zip(seen, pipeline.execute())                   #C

    for i, ((chat_id, seen_id), messages) in enumerate(chat_info):
        if not messages:
            continue
        messages[:] = map(json.loads, messages)
        seen_id = messages[-1]['id']                            #D
        conn.zadd('chat:' + chat_id, recipient, seen_id)        #D

        min_id = conn.zrange(                                   #E
            'chat:' + chat_id, 0, 0, withscores=True)           #E

        pipeline.zadd('seen:' + recipient, chat_id, seen_id)    #F
        if min_id:
            pipeline.zremrangebyscore(                          #G
                'msgs:' + chat_id, 0, min_id[0][1])             #G
        chat_info[i] = (chat_id, messages)
    pipeline.execute()

    return chat_info
# <end id="_1314_14473_9132"/>
#A Get the last message ids received
#B Fetch all new messages
#C Prepare information about the data to be returned
#D Update the 'chat' ZSET with the most recently received message
#E Discover messages that have been seen by all users
#F Update the 'seen' ZSET
#G Clean out messages that have been seen by all users
#END

# <start id="_1314_14473_9135"/>
def join_chat(conn, chat_id, user):
    message_id = int(conn.get('ids:' + chat_id))                #A

    pipeline = conn.pipeline(True)
    pipeline.zadd('chat:' + chat_id, user, message_id)          #B
    pipeline.zadd('seen:' + user, chat_id, message_id)          #C
    pipeline.execute()
# <end id="_1314_14473_9135"/>
#A Get the most recent message id for the chat
#B Add the user to the chat member list
#C Add the chat to the users's seen list
#END

# <start id="_1314_14473_9136"/>
def leave_chat(conn, chat_id, user):
    pipeline = conn.pipeline(True)
    pipeline.zrem('chat:' + chat_id, user)                      #A
    pipeline.zrem('seen:' + user, chat_id)                      #A
    pipeline.zcard('chat:' + chat_id)                           #B

    if not pipeline.execute()[-1]:
        pipeline.delete('msgs:' + chat_id)                      #C
        pipeline.delete('ids:' + chat_id)                       #C
        pipeline.execute()
    else:
        oldest = conn.zrange(                                   #D
            'chat:' + chat_id, 0, 0, withscores=True)           #D
        conn.zremrangebyscore('chat:' + chat_id, 0, oldest)     #E
# <end id="_1314_14473_9136"/>
#A Remove the user from the chat
#B Find the number of remaining group members
#C Delete the chat
#D Find the oldest message seen by all users
#E Delete old messages from the chat
#END

# <start id="_1314_15044_3669"/>
aggregates = defaultdict(lambda: defaultdict(int))      #A

def daily_country_aggregate(conn, line):
    if line:
        line = line.split()
        ip = line[0]                                    #B
        day = line[1]                                   #B
        country = find_city_by_ip_local(ip)[2]          #C
        aggregates[day][country] += 1                   #D
        return

    for day, aggregate in aggregates.items():           #E
        conn.zadd('daily:country:' + day, **aggregate)  #E
        del aggregates[day]                             #E
# <end id="_1314_15044_3669"/>
#A Prepare the local aggregate dictionary
#B Extract the information from our log lines
#C Find the country from the IP address
#D Increment our local aggregate
#E The day file is done, write our aggregate to Redis
#END

# <start id="_1314_14473_9209"/>
def copy_logs_to_redis(conn, path, channel, count=10,
                       limit=2**30, quit_when_done=True):
    bytes_in_redis = 0
    waiting = deque()
    create_chat(conn, 'source', map(str, range(count)), '', channel) #I
    count = str(count)
    for logfile in sorted(os.listdir(path)):               #A
        full_path = os.path.join(path, logfile)

        fsize = os.stat(full_path).st_size
        while bytes_in_redis + fsize > limit:              #B
            cleaned = _clean(conn, channel, waiting, count)#B
            if cleaned:                                    #B
                bytes_in_redis -= cleaned                  #B
            else:                                          #B
                time.sleep(.25)                            #B

        with open(full_path, 'rb') as inp:                 #C
            block = ' '                                    #C
            while block:                                   #C
                block = inp.read(2**17)                    #C
                conn.append(channel+logfile, block)        #C

        send_message(conn, channel, 'source', logfile)     #D

        bytes_in_redis += fsize                            #E
        waiting.append((logfile, fsize))                   #E

    if quit_when_done:                                     #F
        send_message(conn, channel, 'source', ':done')     #F

    while waiting:                                         #G
        cleaned = _clean(conn, channel, waiting, count)    #G
        if cleaned:                                        #G
            bytes_in_redis -= cleaned                      #G
        else:                                              #G
            time.sleep(.25)                                #G

def _clean(conn, channel, waiting, count):                 #H
    if not waiting:                                        #H
        return 0                                           #H
    w0 = waiting[0][0]                                     #H
    if conn.get(channel + w0 + ':done') == count:          #H
        conn.delete(channel + w0, channel + w0 + ':done')  #H
        return waiting.popleft()[1]                        #H
    return 0                                               #H
# <end id="_1314_14473_9209"/>
#I Create the chat that will be used to send messages to clients
#A Iterate over all of the logfiles
#B Clean out finished files if we need more room
#C Upload the file to Redis
#D Notify the listeners that the file is ready
#E Update our local information about Redis' memory use
#F We are out of files, so signal that it is done
#G Clean up the files when we are done
#H How we actually perform the cleanup from Redis
#END

# <start id="_1314_14473_9213"/>
def process_logs_from_redis(conn, id, callback):
    while 1:
        fdata = fetch_pending_messages(conn, id)                    #A

        for ch, mdata in fdata:
            for message in mdata:
                logfile = message['message']

                if logfile == ':done':                                #B
                    return                                            #B
                elif not logfile:
                    continue

                block_reader = readblocks                             #C
                if logfile.endswith('.gz'):                           #C
                    block_reader = readblocks_gz                      #C

                for line in readlines(conn, ch+logfile, block_reader):#D
                    callback(conn, line)                              #E
                callback(conn, None)                                  #F

                conn.incr(ch + logfile + ':done')                     #G

        if not fdata:
            time.sleep(.1)
# <end id="_1314_14473_9213"/>
#A Fetch the list of files
#B No more logfiles
#C Choose a block reader
#D Iterate over the lines
#E Pass each line to the callback
#F Force a flush of our aggregate caches
#G Report that we are finished with the log
#END

# <start id="_1314_14473_9221"/>
def readlines(conn, key, rblocks):
    out = ''
    for block in rblocks(conn, key):
        out += block
        posn = out.rfind('\n')                      #A
        if posn >= 0:                               #B
            for line in out[:posn].split('\n'):     #C
                yield line + '\n'                   #D
            out = out[posn+1:]                      #E
        if not block:                               #F
            yield out
            break
# <end id="_1314_14473_9221"/>
#A Find the rightmost linebreak if any - rfind() returns -1 on failure
#B We found a line break
#C Split on all of the line breaks
#D Yield each line
#E Keep track of the trailing data
#F We are out of data
#END

# <start id="_1314_14473_9225"/>
def readblocks(conn, key, blocksize=2**17):
    lb = blocksize
    pos = 0
    while lb == blocksize:                                  #A
        block = conn.substr(key, pos, pos + blocksize - 1)  #B
        yield block                                         #C
        lb = len(block)                                     #C
        pos += lb                                           #C
    yield ''
# <end id="_1314_14473_9225"/>
#A Keep going while we got as much as we expected
#B Fetch the block
#C Prepare for the next pass
#END

# <start id="_1314_14473_9229"/>
def readblocks_gz(conn, key):
    inp = ''
    decoder = None
    for block in readblocks(conn, key, 2**17):                  #A
        if not decoder:
            inp += block
            try:
                if inp[:3] != "\x1f\x8b\x08":                #B
                    raise IOError("invalid gzip data")          #B
                i = 10                                          #B
                flag = ord(inp[3])                              #B
                if flag & 4:                                    #B
                    i += 2 + ord(inp[i]) + 256*ord(inp[i+1])    #B
                if flag & 8:                                    #B
                    i = inp.index('\0', i) + 1                  #B
                if flag & 16:                                   #B
                    i = inp.index('\0', i) + 1                  #B
                if flag & 2:                                    #B
                    i += 2                                      #B

                if i > len(inp):                                #C
                    raise IndexError("not enough data")         #C
            except (IndexError, ValueError):                    #C
                continue                                        #C

            else:
                block = inp[i:]                                 #D
                inp = None                                      #D
                decoder = zlib.decompressobj(-zlib.MAX_WBITS)   #D
                if not block:
                    continue

        if not block:                                           #E
            yield decoder.flush()                               #E
            break

        yield decoder.decompress(block)                         #F
# <end id="_1314_14473_9229"/>
#A Read the raw data from Redis
#B Parse the header information so that we can get the compressed data
#C We haven't read the full header yet
#D We found the header, prepare the decompressor
#E We are out of data, yield the last chunk
#F Yield a decompressed block
#END

class TestCh06(unittest.TestCase):
    def setUp(self):
        import redis
        self.conn = redis.Redis(db=15)

    def tearDown(self):
        del self.conn
        print
        print

    def test_add_update_contact(self):
        import pprint
        conn = self.conn
        conn.delete('recent:user')

        print "Let's add a few contacts..."
        for i in xrange(10):
            add_update_contact(conn, 'user', 'contact-%i-%i'%(i//3, i))
        print "Current recently contacted contacts"
        contacts = conn.lrange('recent:user', 0, -1)
        pprint.pprint(contacts)
        self.assertTrue(len(contacts) >= 10)
        print

        print "Let's pull one of the older ones up to the front"
        add_update_contact(conn, 'user', 'contact-1-4')
        contacts = conn.lrange('recent:user', 0, 2)
        print "New top-3 contacts:"
        pprint.pprint(contacts)
        self.assertEquals(contacts[0], 'contact-1-4')
        print

        print "Let's remove a contact..."
        print remove_contact(conn, 'user', 'contact-2-6')
        contacts = conn.lrange('recent:user', 0, -1)
        print "New contacts:"
        pprint.pprint(contacts)
        self.assertTrue(len(contacts) >= 9)
        print

        print "And let's finally autocomplete on "
        all = conn.lrange('recent:user', 0, -1)
        contacts = fetch_autocomplete_list(conn, 'user', 'c')
        self.assertTrue(all == contacts)
        equiv = [c for c in all if c.startswith('contact-2-')]
        contacts = fetch_autocomplete_list(conn, 'user', 'contact-2-')
        equiv.sort()
        contacts.sort()
        self.assertEquals(equiv, contacts)
        conn.delete('recent:user')

    def test_address_book_autocomplete(self):
        self.conn.delete('members:test')
        print "the start/end range of 'abc' is:", find_prefix_range('abc')
        print

        print "Let's add a few people to the guild"
        for name in ['jeff', 'jenny', 'jack', 'jennifer']:
            join_guild(self.conn, 'test', name)
        print
        print "now let's try to find users with names starting with 'je':"
        r = autocomplete_on_prefix(self.conn, 'test', 'je')
        print r
        self.assertTrue(len(r) == 3)
        print "jeff just left to join a different guild..."
        leave_guild(self.conn, 'test', 'jeff')
        r = autocomplete_on_prefix(self.conn, 'test', 'je')
        print r
        self.assertTrue(len(r) == 2)
        self.conn.delete('members:test')

    def test_distributed_locking(self):
        self.conn.delete('lock:testlock')
        print "Getting an initial lock..."
        self.assertTrue(acquire_lock_with_timeout(self.conn, 'testlock', 1, 1))
        print "Got it!"
        print "Trying to get it again without releasing the first one..."
        self.assertFalse(acquire_lock_with_timeout(self.conn, 'testlock', .01, 1))
        print "Failed to get it!"
        print
        print "Waiting for the lock to timeout..."
        time.sleep(2)
        print "Getting the lock again..."
        r = acquire_lock_with_timeout(self.conn, 'testlock', 1, 1)
        self.assertTrue(r)
        print "Got it!"
        print "Releasing the lock..."
        self.assertTrue(release_lock(self.conn, 'testlock', r))
        print "Released it..."
        print
        print "Acquiring it again..."
        self.assertTrue(acquire_lock_with_timeout(self.conn, 'testlock', 1, 1))
        print "Got it!"
        self.conn.delete('lock:testlock')

    def test_counting_semaphore(self):
        self.conn.delete('testsem', 'testsem:owner', 'testsem:counter')
        print "Getting 3 initial semaphores with a limit of 3..."
        for i in xrange(3):
            self.assertTrue(acquire_fair_semaphore(self.conn, 'testsem', 3, 1))
        print "Done!"
        print "Getting one more that should fail..."
        self.assertFalse(acquire_fair_semaphore(self.conn, 'testsem', 3, 1))
        print "Couldn't get it!"
        print
        print "Lets's wait for some of them to time out"
        time.sleep(2)
        print "Can we get one?"
        r = acquire_fair_semaphore(self.conn, 'testsem', 3, 1)
        self.assertTrue(r)
        print "Got one!"
        print "Let's release it..."
        self.assertTrue(release_fair_semaphore(self.conn, 'testsem', r))
        print "Released!"
        print
        print "And let's make sure we can get 3 more!"
        for i in xrange(3):
            self.assertTrue(acquire_fair_semaphore(self.conn, 'testsem', 3, 1))
        print "We got them!"
        self.conn.delete('testsem', 'testsem:owner', 'testsem:counter')

    def test_delayed_tasks(self):
        import threading
        self.conn.delete('queue:tqueue', 'delayed:')
        print "Let's start some regular and delayed tasks..."
        for delay in [0, .5, 0, 1.5]:
            self.assertTrue(execute_later(self.conn, 'tqueue', 'testfn', [], delay))
        r = self.conn.llen('queue:tqueue')
        print "How many non-delayed tasks are there (should be 2)?", r
        self.assertEquals(r, 2)
        print
        print "Let's start up a thread to bring those delayed tasks back..."
        t = threading.Thread(target=poll_queue, args=(self.conn,))
        t.setDaemon(1)
        t.start()
        print "Started."
        print "Let's wait for those tasks to be prepared..."
        time.sleep(2)
        global QUIT
        QUIT = True
        t.join()
        r = self.conn.llen('queue:tqueue')
        print "Waiting is over, how many tasks do we have (should be 4)?", r
        self.assertEquals(r, 4)
        self.conn.delete('queue:tqueue', 'delayed:')

    def test_multi_recipient_messaging(self):
        self.conn.delete('ids:chat:', 'msgs:1', 'ids:1', 'seen:joe', 'seen:jeff', 'seen:jenny')

        print "Let's create a new chat session with some recipients..."
        chat_id = create_chat(self.conn, 'joe', ['jeff', 'jenny'], 'message 1')
        print "Now let's send a few messages..."
        for i in xrange(2, 5):
            send_message(self.conn, chat_id, 'joe', 'message %s'%i)
        print
        print "And let's get the messages that are waiting for jeff and jenny..."
        r1 = fetch_pending_messages(self.conn, 'jeff')
        r2 = fetch_pending_messages(self.conn, 'jenny')
        print "They are the same?", r1==r2
        self.assertEquals(r1, r2)
        print "Those messages are:"
        import pprint
        pprint.pprint(r1)
        self.conn.delete('ids:chat:', 'msgs:1', 'ids:1', 'seen:joe', 'seen:jeff', 'seen:jenny')

    def test_file_distribution(self):
        import gzip, shutil, tempfile, threading
        self.conn.delete('test:temp-1.txt', 'test:temp-2.txt', 'test:temp-3.txt', 'msgs:test:', 'seen:0', 'seen:source', 'ids:test:', 'chat:test:')

        dire = tempfile.mkdtemp()
        try:
            print "Creating some temporary 'log' files..."
            with open(dire + '/temp-1.txt', 'wb') as f:
                f.write('one line\n')
            with open(dire + '/temp-2.txt', 'wb') as f:
                f.write(10000 * 'many lines\n')
            out = gzip.GzipFile(dire + '/temp-3.txt.gz', mode='wb')
            for i in xrange(100000):
                out.write('random line %s\n'%(os.urandom(16).encode('hex'),))
            out.close()
            size = os.stat(dire + '/temp-3.txt.gz').st_size
            print "Done."
            print
            print "Starting up a thread to copy logs to redis..."
            t = threading.Thread(target=copy_logs_to_redis, args=(self.conn, dire, 'test:', 1, size))
            t.setDaemon(1)
            t.start()

            print "Let's pause to let some logs get copied to Redis..."
            time.sleep(.25)
            print
            print "Okay, the logs should be ready. Let's process them!"

            index = [0]
            counts = [0, 0, 0]
            def callback(conn, line):
                if line is None:
                    print "Finished with a file %s, linecount: %s"%(index[0], counts[index[0]])
                    index[0] += 1
                elif line or line.endswith('\n'):
                    counts[index[0]] += 1

            print "Files should have 1, 10000, and 100000 lines"
            process_logs_from_redis(self.conn, '0', callback)
            self.assertEquals(counts, [1, 10000, 100000])

            print
            print "Let's wait for the copy thread to finish cleaning up..."
            t.join()
            print "Done cleaning out Redis!"

        finally:
            print "Time to clean up files..."
            shutil.rmtree(dire)
            print "Cleaned out files!"
        self.conn.delete('test:temp-1.txt', 'test:temp-2.txt', 'test:temp-3.txt', 'msgs:test:', 'seen:0', 'seen:source', 'ids:test:', 'chat:test:')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch07_listing_source

import math
import re
import unittest
import uuid

import redis

AVERAGE_PER_1K = {}

# <start id="tokenize-and-index"/>
STOP_WORDS = set('''able about across after all almost also am among
an and any are as at be because been but by can cannot could dear did
do does either else ever every for from get got had has have he her
hers him his how however if in into is it its just least let like
likely may me might most must my neither no nor not of off often on
only or other our own rather said say says she should since so some
than that the their them then there these they this tis to too twas us
wants was we were what when where which while who whom why will with
would yet you your'''.split())                                          #A

WORDS_RE = re.compile("[a-z']{2,}")                                     #B

def tokenize(content):
    words = set()                                                       #C
    for match in WORDS_RE.finditer(content.lower()):                    #D
        word = match.group().strip("'")                                 #E
        if len(word) >= 2:                                              #F
            words.add(word)                                             #F
    return words - STOP_WORDS                                           #G

def index_document(conn, docid, content):
    words = tokenize(content)                                           #H

    pipeline = conn.pipeline(True)
    for word in words:                                                  #I
        pipeline.sadd('idx:' + word, docid)                             #I
    return len(pipeline.execute())                                      #J
# <end id="tokenize-and-index"/>
#A We pre-declare our known stop words, these were fetched from http://www.textfixer.com/resources/
#B A regular expression that extracts words as we defined them
#C Our Python set of words that we have found in the document content
#D Iterate over all of the words in the content
#E Strip any leading or trailing single-quote characters
#F Keep any words that are still at least 2 characters long
#G Return the set of words that remain that are also not stop words
#H Get the tokenized words for the content
#I Add the documents to the appropriate inverted index entries
#J Return the number of unique non-stop words that were added for the document
#END

# <start id="_1314_14473_9158"/>
def _set_common(conn, method, names, ttl=30, execute=True):
    id = str(uuid.uuid4())                                  #A
    pipeline = conn.pipeline(True) if execute else conn     #B
    names = ['idx:' + name for name in names]               #C
    getattr(pipeline, method)('idx:' + id, *names)          #D
    pipeline.expire('idx:' + id, ttl)                       #E
    if execute:
        pipeline.execute()                                  #F
    return id                                               #G

def intersect(conn, items, ttl=30, _execute=True):          #H
    return _set_common(conn, 'sinterstore', items, ttl, _execute) #H

def union(conn, items, ttl=30, _execute=True):                    #I
    return _set_common(conn, 'sunionstore', items, ttl, _execute) #I

def difference(conn, items, ttl=30, _execute=True):               #J
    return _set_common(conn, 'sdiffstore', items, ttl, _execute)  #J
# <end id="_1314_14473_9158"/>
#A Create a new temporary identifier
#B Set up a transactional pipeline so that we have consistent results for each individual call
#C Add the 'idx:' prefix to our terms
#D Set up the call for one of the operations
#E Instruct Redis to expire the SET in the future
#F Actually execute the operation
#G Return the id for the caller to process the results
#H Helper function to perform SET intersections
#I Helper function to perform SET unions
#J Helper function to perform SET differences
#END

# <start id="parse-query"/>
QUERY_RE = re.compile("[+-]?[a-z']{2,}")                #A

def parse(query):
    unwanted = set()                                    #B
    all = []                                            #C
    current = set()                                     #D
    for match in QUERY_RE.finditer(query.lower()):      #E
        word = match.group()                            #F
        prefix = word[:1]                               #F
        if prefix in '+-':                              #F
            word = word[1:]                             #F
        else:                                           #F
            prefix = None                               #F

        word = word.strip("'")                          #G
        if len(word) < 2 or word in STOP_WORDS:         #G
            continue                                    #G

        if prefix == '-':                               #H
            unwanted.add(word)                          #H
            continue                                    #H

        if current and not prefix:                      #I
            all.append(list(current))                   #I
            current = set()                             #I
        current.add(word)                               #J

    if current:                                         #K
        all.append(list(current))                       #K

    return all, list(unwanted)                          #L
# <end id="parse-query"/>
#A Our regular expression for finding wanted, unwanted, and synonym words
#B A unique set of unwanted words
#C Our final result of words that we are looking to intersect
#D The current unique set of words to consider as synonyms
#E Iterate over all words in the search query
#F Discover +/- prefixes, if any
#G Strip any leading or trailing single quotes, and skip anything that is a stop word
#H If the word is unwanted, add it to the unwanted set
#I Set up a new synonym set if we have no synonym prefix and we already have words
#J Add the current word to the current set
#K Add any remaining words to the final intersection
#END

# <start id="search-query"/>
def parse_and_search(conn, query, ttl=30):
    all, unwanted = parse(query)                                    #A
    if not all:                                                     #B
        return None                                                 #B

    to_intersect = []
    for syn in all:                                                 #D
        if len(syn) > 1:                                            #E
            to_intersect.append(union(conn, syn, ttl=ttl))          #E
        else:                                                       #F
            to_intersect.append(syn[0])                             #F

    if len(to_intersect) > 1:                                       #G
        intersect_result = intersect(conn, to_intersect, ttl=ttl)   #G
    else:                                                           #H
        intersect_result = to_intersect[0]                          #H

    if unwanted:                                                    #I
        unwanted.insert(0, intersect_result)                        #I
        return difference(conn, unwanted, ttl=ttl)                  #I

    return intersect_result                                         #J
# <end id="search-query"/>
#A Parse the query
#B If there are no words in the query that are not stop words, we don't have a result
#D Iterate over each list of synonyms
#E If the synonym list is more than one word long, then perform the union operation
#F Otherwise use the individual word directly
#G If we have more than one word/result to intersect, intersect them
#H Otherwise use the individual word/result directly
#I If we have any unwanted words, remove them from our earlier result and return it
#J Otherwise return the intersection result
#END


# <start id="sorted-searches"/>
def search_and_sort(conn, query, id=None, ttl=300, sort="-updated", #A
                    start=0, num=20):                               #A
    desc = sort.startswith('-')                                     #B
    sort = sort.lstrip('-')                                         #B
    by = "kb:doc:*->" + sort                                        #B
    alpha = sort not in ('updated', 'id', 'created')                #I

    if id and not conn.expire(id, ttl):     #C
        id = None                           #C

    if not id:                                      #D
        id = parse_and_search(conn, query, ttl=ttl) #D

    pipeline = conn.pipeline(True)
    pipeline.scard('idx:' + id)                                     #E
    pipeline.sort('idx:' + id, by=by, alpha=alpha,                  #F
        desc=desc, start=start, num=num)                            #F
    results = pipeline.execute()

    return results[0], results[1], id                               #G
# <end id="sorted-searches"/>
#A We will optionally take an previous result id, a way to sort the results, and options for paginating over the results
#B Determine which attribute to sort by, and whether to sort ascending or descending
#I We need to tell Redis whether we are sorting by a number or alphabetically
#C If there was a previous result, try to update its expiration time if it still exists
#D Perform the search if we didn't have a past search id, or if our results expired
#E Fetch the total number of results
#F Sort the result list by the proper column and fetch only those results we want
#G Return the number of items in the results, the results we wanted, and the id of the results so that we can fetch them again later
#END

# <start id="zset_scored_composite"/>
def search_and_zsort(conn, query, id=None, ttl=300, update=1, vote=0,   #A
                    start=0, num=20, desc=True):                        #A

    if id and not conn.expire(id, ttl):     #B
        id = None                           #B

    if not id:                                      #C
        id = parse_and_search(conn, query, ttl=ttl) #C

        scored_search = {
            id: 0,                                  #I
            'sort:update': update,                  #D
            'sort:votes': vote                      #D
        }
        id = zintersect(conn, scored_search, ttl)   #E

    pipeline = conn.pipeline(True)
    pipeline.zcard('idx:' + id)                                     #F
    if desc:                                                        #G
        pipeline.zrevrange('idx:' + id, start, start + num - 1)     #G
    else:                                                           #G
        pipeline.zrange('idx:' + id, start, start + num - 1)        #G
    results = pipeline.execute()

    return results[0], results[1], id                               #H
# <end id="zset_scored_composite"/>
#A Like before, we'll optionally take a previous result id for pagination if the result is still available
#B We will refresh the search result's TTL if possible
#C If our search result expired, or if this is the first time we've searched, perform the standard SET search
#I We use the 'id' key for the intersection, but we don't want it to count towards weights
#D Set up the scoring adjustments for balancing update time and votes. Remember: votes can be adjusted to 1, 10, 100, or higher depending on the sorting result desired.
#E Intersect using our helper function that we define in listing 7.7
#F Fetch the size of the result ZSET
#G Handle fetching a "page" of results
#H Return the results and the id for pagination
#END


# <start id="zset_helpers"/>
def _zset_common(conn, method, scores, ttl=30, **kw):
    id = str(uuid.uuid4())                                  #A
    execute = kw.pop('_execute', True)                      #J
    pipeline = conn.pipeline(True) if execute else conn     #B
    for key in scores.keys():                               #C
        scores['idx:' + key] = scores.pop(key)              #C
    getattr(pipeline, method)('idx:' + id, scores, **kw)    #D
    pipeline.expire('idx:' + id, ttl)                       #E
    if execute:                                             #F
        pipeline.execute()                                  #F
    return id                                               #G

def zintersect(conn, items, ttl=30, **kw):                              #H
    return _zset_common(conn, 'zinterstore', dict(items), ttl, **kw)    #H

def zunion(conn, items, ttl=30, **kw):                                  #I
    return _zset_common(conn, 'zunionstore', dict(items), ttl, **kw)    #I
# <end id="zset_helpers"/>
#A Create a new temporary identifier
#B Set up a transactional pipeline so that we have consistent results for each individual call
#C Add the 'idx:' prefix to our inputs
#D Set up the call for one of the operations
#E Instruct Redis to expire the ZSET in the future
#F Actually execute the operation, unless explicitly instructed not to by the caller
#G Return the id for the caller to process the results
#H Helper function to perform ZSET intersections
#I Helper function to perform ZSET unions
#J Allow the passing of an argument to determine whether we should defer pipeline execution
#END


# <start id="string-to-score"/>
def string_to_score(string, ignore_case=False):
    if ignore_case:                         #A
        string = string.lower()             #A

    pieces = map(ord, string[:6])           #B
    while len(pieces) < 6:                  #C
        pieces.append(-1)                   #C

    score = 0
    for piece in pieces:                    #D
        score = score * 257 + piece + 1     #D

    return score * 2 + (len(string) > 6)    #E
# <end id="string-to-score"/>
#A We can handle optional case-insensitive indexes easily, so we will
#B Convert the first 6 characters of the string into their numeric values, null being 0, tab being 9, capital A being 65, etc.
#C For strings that aren't at least 6 characters long, we will add place-holder values to represent that the string was short
#D For each value in the converted string values, we add it to the score, taking into consideration that a null is different from a place holder
#E Because we have an extra bit, we can also signify whether the string is exactly 6 characters or more, allowing us to differentiate 'robber' and 'robbers', though not 'robbers' and 'robbery'
#END

def to_char_map(set):
    out = {}
    for pos, val in enumerate(sorted(set)):
        out[val] = pos-1
    return out

LOWER = to_char_map(set([-1]) | set(xrange(ord('a'), ord('z')+1)))
ALPHA = to_char_map(set(LOWER) | set(xrange(ord('A'), ord('Z')+1)))
LOWER_NUMERIC = to_char_map(set(LOWER) | set(xrange(ord('0'), ord('9')+1)))
ALPHA_NUMERIC = to_char_map(set(LOWER_NUMERIC) | set(ALPHA))

def string_to_score_generic(string, mapping):
    length = int(52 / math.log(len(mapping), 2))    #A

    pieces = map(ord, string[:length])              #B
    while len(pieces) < length:                     #C
        pieces.append(-1)                           #C

    score = 0
    for piece in pieces:                            #D
        value = mapping[piece]                      #D
        score = score * len(mapping) + value + 1    #D

    return score * 2 + (len(string) > length)       #E



# <start id="zadd-string"/>
def zadd_string(conn, name, *args, **kwargs):
    pieces = list(args)                         #A
    for piece in kwargs.iteritems():            #A
        pieces.extend(piece)                    #A

    for i, v in enumerate(pieces):
        if i & 1:                               #B
            pieces[i] = string_to_score(v)      #B

    return conn.zadd(name, *pieces)             #C
# <end id="zadd-string"/>
#A Combine both types of arguments passed for later modification
#B Convert string scores to integer scores
#C Call the existing ZADD method
#END

# <start id="ecpm_helpers"/>
def cpc_to_ecpm(views, clicks, cpc):
    return 1000. * cpc * clicks / views

def cpa_to_ecpm(views, actions, cpa):
    return 1000. * cpa * actions / views #A
# <end id="ecpm_helpers"/>
#A Because click through rate is (clicks/views), and action rate is (actions/clicks), when we multiply them together we get (actions/views)
#END

# <start id="index_ad"/>
TO_ECPM = {
    'cpc': cpc_to_ecpm,
    'cpa': cpa_to_ecpm,
    'cpm': lambda *args:args[-1],
}

def index_ad(conn, id, locations, content, type, value):
    pipeline = conn.pipeline(True)                          #A

    for location in locations:
        pipeline.sadd('idx:req:'+location, id)              #B

    words = tokenize(content)
    for word in tokenize(content):                          #H
        pipeline.zadd('idx:' + word, id, 0)                 #H

    rvalue = TO_ECPM[type](                                 #C
        1000, AVERAGE_PER_1K.get(type, 1), value)           #C
    pipeline.hset('type:', id, type)                        #D
    pipeline.zadd('idx:ad:value:', id, rvalue)              #E
    pipeline.zadd('ad:base_value:', id, value)              #F
    pipeline.sadd('terms:' + id, *list(words))              #G
    pipeline.execute()
# <end id="index_ad"/>
#A Set up the pipeline so that we only need a single round-trip to perform the full index operation
#B Add the ad id to all of the relevant location SETs for targeting
#H Index the words for the ad
#C We will keep a dictionary that stores the average number of clicks or actions per 1000 views on our network, for estimating the performance of new ads
#D Record what type of ad this is
#E Add the ad's eCPM to a ZSET of all ads
#F Add the ad's base value to a ZST of all ads
#G Keep a record of the words that could be targeted for the ad
#END

# <start id="target_ad"/>
def target_ads(conn, locations, content):
    pipeline = conn.pipeline(True)
    matched_ads, base_ecpm = match_location(pipeline, locations)    #A
    words, targeted_ads = finish_scoring(                           #B
        pipeline, matched_ads, base_ecpm, content)                  #B

    pipeline.incr('ads:served:')                                    #C
    pipeline.zrevrange('idx:' + targeted_ads, 0, 0)                 #D
    target_id, targeted_ad = pipeline.execute()[-2:]

    if not targeted_ad:                                             #E
        return None, None                                           #E

    ad_id = targeted_ad[0]
    record_targeting_result(conn, target_id, ad_id, words)          #F

    return target_id, ad_id                                         #G
# <end id="target_ad"/>
#A Find all ads that fit the location targeting parameter, and their eCPMs
#B Finish any bonus scoring based on matching the content
#C Get an id that can be used for reporting and recording of this particular ad target
#D Fetch the top-eCPM ad id
#E If there were no ads that matched the location targeting, return nothing
#F Record the results of our targeting efforts as part of our learning process
#G Return the target id and the ad id to the caller
#END

# <start id="location_target"/>
def match_location(pipe, locations):
    required = ['req:' + loc for loc in locations]                  #A
    matched_ads = union(pipe, required, ttl=300, _execute=False)    #B
    return matched_ads, zintersect(pipe,                            #C
        {matched_ads: 0, 'ad:value:': 1}, _execute=False)  #C
# <end id="location_target"/>
#A Calculate the SET key names for all of the provided locations
#B Calculate the SET of matched ads that are valid for this location
#C Return the matched ads SET id, as well as the id of the ZSET that includes the base eCPM of all of the matched ads
#END

# <start id="finish_scoring"/>
def finish_scoring(pipe, matched, base, content):
    bonus_ecpm = {}
    words = tokenize(content)                                   #A
    for word in words:
        word_bonus = zintersect(                                #B
            pipe, {matched: 0, word: 1}, _execute=False)        #B
        bonus_ecpm[word_bonus] = 1                              #B

    if bonus_ecpm:
        minimum = zunion(                                       #C
            pipe, bonus_ecpm, aggregate='MIN', _execute=False)  #C
        maximum = zunion(                                       #C
            pipe, bonus_ecpm, aggregate='MAX', _execute=False)  #C

        return words, zunion(                                       #D
            pipe, {base:1, minimum:.5, maximum:.5}, _execute=False) #D
    return words, base                                          #E
# <end id="finish_scoring"/>
#A Tokenize the content for matching against ads
#B Find the ads that are location-targeted, which also have one of the words in the content
#C Find the minimum and maximum eCPM bonuses for each ad
#D Compute the total of the base + half of the minimum eCPM bonus + half of the maximum eCPM bonus
#E If there were no words in the content to match against, return just the known eCPM
#END

# <start id="record_targeting"/>
def record_targeting_result(conn, target_id, ad_id, words):
    pipeline = conn.pipeline(True)

    terms = conn.smembers('terms:' + ad_id)                 #A
    matched = list(words & terms)                           #A
    if matched:
        matched_key = 'terms:matched:%s' % target_id
        pipeline.sadd(matched_key, *matched)                #B
        pipeline.expire(matched_key, 900)                   #B

    type = conn.hget('type:', ad_id)                        #C
    pipeline.incr('type:%s:views:' % type)                  #C
    for word in matched:                                    #D
        pipeline.zincrby('views:%s' % ad_id, word)          #D
    pipeline.zincrby('views:%s' % ad_id, '')                #D

    if not pipeline.execute()[-1] % 100:                    #E
        update_cpms(conn, ad_id)                            #E

# <end id="record_targeting"/>
#A Find the words in the content that matched with the words in the ad
#B If any words in the ad matched the content, record that information and keep it for 15 minutes
#C Keep a per-type count of the number of views that each ad received
#D Record view information for each word in the ad, as well as the ad itself
#E Every 100th time that the ad was shown, update the ad's eCPM
#END

# <start id="record_click"/>
def record_click(conn, target_id, ad_id, action=False):
    pipeline = conn.pipeline(True)
    click_key = 'clicks:%s'%ad_id

    match_key = 'terms:matched:%s'%target_id

    type = conn.hget('type:', ad_id)
    if type == 'cpa':                       #A
        pipeline.expire(match_key, 900)     #A
        if action:
            click_key = 'actions:%s' % ad_id  #B

    if action and type == 'cpa':
        pipeline.incr('type:cpa:actions:' % type) #C
    else:
        pipeline.incr('type:%s:clicks:' % type)   #C

    matched = list(conn.smembers(match_key))#D
    matched.append('')                      #D
    for word in matched:                    #D
        pipeline.zincrby(click_key, word)   #D
    pipeline.execute()

    update_cpms(conn, ad_id)                #E
# <end id="record_click"/>
#A If the ad was a CPA ad, refresh the expiration time of the matched terms if it is still available
#B Record actions instead of clicks
#C Keep a global count of clicks/actions for ads based on the ad type
#D Record clicks (or actions) for the ad and for all words that had been targeted in the ad
#E Update the eCPM for all words that were seen in the ad
#END

# <start id="update_cpms"/>
def update_cpms(conn, ad_id):
    pipeline = conn.pipeline(True)
    pipeline.hget('type:', ad_id)               #A
    pipeline.zscore('ad:base_value:', ad_id)    #A
    pipeline.smembers('terms:' + ad_id)         #A
    type, base_value, words = pipeline.execute()#A

    which = 'clicks'                                        #B
    if type == 'cpa':                                       #B
        which = 'actions'                                   #B

    pipeline.get('type:%s:views:' % type)                   #C
    pipeline.get('type:%s:%s' % (type, which))              #C
    type_views, type_clicks = pipeline.execute()            #C
    AVERAGE_PER_1K[type] = (                                        #D
        1000. * int(type_clicks or '1') / int(type_views or '1'))   #D

    if type == 'cpm':   #E
        return          #E

    view_key = 'views:%s' % ad_id
    click_key = '%s:%s' % (which, ad_id)

    to_ecpm = TO_ECPM[type]

    pipeline.zscore(view_key, '')                                   #G
    pipeline.zscore(click_key, '')                                  #G
    ad_views, ad_clicks = pipeline.execute()                        #G
    if (ad_clicks or 0) < 1:                                        #N
        ad_ecpm = conn.zscore('idx:ad:value:', ad_id)               #N
    else:
        ad_ecpm = to_ecpm(ad_views or 1, ad_clicks or 0, base_value)#H
        pipeline.zadd('idx:ad:value:', ad_id, ad_ecpm)              #H

    for word in words:
        pipeline.zscore(view_key, word)                             #I
        pipeline.zscore(click_key, word)                            #I
        views, clicks = pipeline.execute()[-2:]                     #I

        if (clicks or 0) < 1:                                       #J
            continue                                                #J

        word_ecpm = to_ecpm(views or 1, clicks or 0, base_value)    #K
        bonus = word_ecpm - ad_ecpm                                 #L
        pipeline.zadd('idx:' + word, ad_id, bonus)                  #M
    pipeline.execute()
# <end id="update_cpms"/>
#A Fetch the type and value of the ad, as well as all of the words in the ad
#B Determine whether the eCPM of the ad should be based on clicks or actions
#C Fetch the current number of views and clicks/actions for the given ad type
#D Write back to our global dictionary the click-through rate or action rate for the ad
#E If we are processing a CPM ad, then we don't update any of the eCPMs, as they are already updated
#N Use the existing eCPM if the ad hasn't received any clicks yet
#G Fetch the per-ad view and click/action scores and
#H Calculate the ad's eCPM and update the ad's value
#I Fetch the view and click/action scores for the word
#J Don't update eCPMs when the ad has not received any clicks
#K Calculate the word's eCPM
#L Calculate the word's bonus
#M Write the word's bonus back to the per-word per-ad ZSET
#END


# <start id="slow_job_search"/>
def add_job(conn, job_id, required_skills):
    conn.sadd('job:' + job_id, *required_skills)        #A

def is_qualified(conn, job_id, candidate_skills):
    temp = str(uuid.uuid4())
    pipeline = conn.pipeline(True)
    pipeline.sadd(temp, *candidate_skills)              #B
    pipeline.expire(temp, 5)                            #B
    pipeline.sdiff('job:' + job_id, temp)               #C
    return not pipeline.execute()[-1]                   #D
# <end id="slow_job_search"/>
#A Add all required job skills to the job's SET
#B Add the candidate's skills to a temporary SET with an expiration time
#C Calculate the SET of skills that the job requires that the user doesn't have
#D Return True if there are no skills that the candidate does not have
#END

# <start id="job_search_index"/>
def index_job(conn, job_id, skills):
    pipeline = conn.pipeline(True)
    for skill in skills:
        pipeline.sadd('idx:skill:' + skill, job_id)             #A
    pipeline.zadd('idx:jobs:req', job_id, len(set(skills)))     #B
    pipeline.execute()
# <end id="job_search_index"/>
#A Add the job id to all appropriate skill SETs
#B Add the total required skill count to the required skills ZSET
#END

# <start id="job_search_results"/>
def find_jobs(conn, candidate_skills):
    skills = {}                                                 #A
    for skill in set(candidate_skills):                         #A
        skills['skill:' + skill] = 1                            #A

    job_scores = zunion(conn, skills)                           #B
    final_result = zintersect(                                  #C
        conn, {job_scores:-1, 'jobs:req':1})                    #C

    return conn.zrangebyscore('idx:' + final_result, 0, 0)      #D
# <end id="job_search_results"/>
#A Set up the dictionary for scoring the jobs
#B Calculate the scores for each of the jobs
#C Calculate how many more skills the job requires than the candidate has
#D Return the jobs that the candidate has the skills for
#END

# 0 is beginner, 1 is intermediate, 2 is expert
SKILL_LEVEL_LIMIT = 2

def index_job_levels(conn, job_id, skill_levels):
    total_skills = len(set(skill for skill, level in skill_levels))
    pipeline = conn.pipeline(True)
    for skill, level in skill_levels:
        level = min(level, SKILL_LEVEL_LIMIT)
        for wlevel in xrange(level, SKILL_LEVEL_LIMIT+1):
            pipeline.sadd('idx:skill:%s:%s'%(skill,wlevel), job_id)
    pipeline.zadd('idx:jobs:req', job_id, total_skills)
    pipeline.execute()

def search_job_levels(conn, skill_levels):
    skills = {}
    for skill, level in skill_levels:
        level = min(level, SKILL_LEVEL_LIMIT)
        for wlevel in xrange(level, SKILL_LEVEL_LIMIT+1):
            skills['skill:%s:%s'%(skill,wlevel)] = 1

    job_scores = zunion(conn, skills)
    final_result = zintersect(conn, {job_scores:-1, 'jobs:req':1})

    return conn.zrangebyscore('idx:' + final_result, 0, 0)


def index_job_years(conn, job_id, skill_years):
    total_skills = len(set(skill for skill, level in skill_years))
    pipeline = conn.pipeline(True)
    for skill, years in skill_years:
        pipeline.zadd(
            'idx:skill:%s:years'%skill, job_id, max(years, 0))
    pipeline.sadd('idx:jobs:all', job_id)
    pipeline.zadd('idx:jobs:req', job_id, total_skills)


def search_job_years(conn, skill_years):
    skill_years = dict(skill_years)
    pipeline = conn.pipeline(True)

    union = []
    for skill, years in skill_years.iteritems():
        sub_result = zintersect(pipeline,
            {'jobs:all':-years, 'skill:%s:years'%skill:1}, _execute=False)
        pipeline.zremrangebyscore('idx:' + sub_result, '(0', 'inf')
        union.append(
            zintersect(pipeline, {'jobs:all':1, sub_result:0}), _execute=False)

    job_scores = zunion(pipeline, dict((key, 1) for key in union), _execute=False)
    final_result = zintersect(pipeline, {job_scores:-1, 'jobs:req':1}, _execute=False)

    pipeline.zrange('idx:' + final_result, 0, 0)
    return pipeline.execute()[-1]

class TestCh07(unittest.TestCase):
    content = 'this is some random content, look at how it is indexed.'
    def setUp(self):
        self.conn = redis.Redis(db=15)
        self.conn.flushdb()
    def tearDown(self):
        self.conn.flushdb()

    def test_index_document(self):
        print "We're tokenizing some content..."
        tokens = tokenize(self.content)
        print "Those tokens are:", tokens
        self.assertTrue(tokens)

        print "And now we are indexing that content..."
        r = index_document(self.conn, 'test', self.content)
        self.assertEquals(r, len(tokens))
        for t in tokens:
            self.assertEquals(self.conn.smembers('idx:' + t), set(['test']))

    def test_set_operations(self):
        index_document(self.conn, 'test', self.content)

        r = intersect(self.conn, ['content', 'indexed'])
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = intersect(self.conn, ['content', 'ignored'])
        self.assertEquals(self.conn.smembers('idx:' + r), set())

        r = union(self.conn, ['content', 'ignored'])
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = difference(self.conn, ['content', 'ignored'])
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = difference(self.conn, ['content', 'indexed'])
        self.assertEquals(self.conn.smembers('idx:' + r), set())

    def test_parse_query(self):
        query = 'test query without stopwords'
        self.assertEquals(parse(query), ([[x] for x in query.split()], []))

        query = 'test +query without -stopwords'
        self.assertEquals(parse(query), ([['test', 'query'], ['without']], ['stopwords']))

    def test_parse_and_search(self):
        print "And now we are testing search..."
        index_document(self.conn, 'test', self.content)

        r = parse_and_search(self.conn, 'content')
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = parse_and_search(self.conn, 'content indexed random')
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = parse_and_search(self.conn, 'content +indexed random')
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = parse_and_search(self.conn, 'content indexed +random')
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        r = parse_and_search(self.conn, 'content indexed -random')
        self.assertEquals(self.conn.smembers('idx:' + r), set())

        r = parse_and_search(self.conn, 'content indexed +random')
        self.assertEquals(self.conn.smembers('idx:' + r), set(['test']))

        print "Which passed!"

    def test_search_with_sort(self):
        print "And now let's test searching with sorting..."

        index_document(self.conn, 'test', self.content)
        index_document(self.conn, 'test2', self.content)
        self.conn.hmset('kb:doc:test', {'updated': 12345, 'id': 10})
        self.conn.hmset('kb:doc:test2', {'updated': 54321, 'id': 1})

        r = search_and_sort(self.conn, "content")
        self.assertEquals(r[1], ['test2', 'test'])

        r = search_and_sort(self.conn, "content", sort='-id')
        self.assertEquals(r[1], ['test', 'test2'])
        print "Which passed!"

    def test_search_with_zsort(self):
        print "And now let's test searching with sorting via zset..."

        index_document(self.conn, 'test', self.content)
        index_document(self.conn, 'test2', self.content)
        self.conn.zadd('idx:sort:update', 'test', 12345, 'test2', 54321)
        self.conn.zadd('idx:sort:votes', 'test', 10, 'test2', 1)

        r = search_and_zsort(self.conn, "content", desc=False)
        self.assertEquals(r[1], ['test', 'test2'])

        r = search_and_zsort(self.conn, "content", update=0, vote=1, desc=False)
        self.assertEquals(r[1], ['test2', 'test'])
        print "Which passed!"

    def test_string_to_score(self):
        words = 'these are some words that will be sorted'.split()
        pairs = [(word, string_to_score(word)) for word in words]
        pairs2 = list(pairs)
        pairs.sort()
        pairs2.sort(key=lambda x:x[1])
        self.assertEquals(pairs, pairs2)

        words = 'these are some words that will be sorted'.split()
        pairs = [(word, string_to_score_generic(word, LOWER)) for word in words]
        pairs2 = list(pairs)
        pairs.sort()
        pairs2.sort(key=lambda x:x[1])
        self.assertEquals(pairs, pairs2)

        zadd_string(self.conn, 'key', 'test', 'value', test2='other')
        self.assertTrue(self.conn.zscore('key', 'test'), string_to_score('value'))
        self.assertTrue(self.conn.zscore('key', 'test2'), string_to_score('other'))

    def test_index_and_target_ads(self):
        index_ad(self.conn, '1', ['USA', 'CA'], self.content, 'cpc', .25)
        index_ad(self.conn, '2', ['USA', 'VA'], self.content + ' wooooo', 'cpc', .125)

        for i in xrange(100):
            ro = target_ads(self.conn, ['USA'], self.content)
        self.assertEquals(ro[1], '1')

        r = target_ads(self.conn, ['VA'], 'wooooo')
        self.assertEquals(r[1], '2')

        self.assertEquals(self.conn.zrange('idx:ad:value:', 0, -1, withscores=True), [('2', 0.125), ('1', 0.25)])
        self.assertEquals(self.conn.zrange('ad:base_value:', 0, -1, withscores=True), [('2', 0.125), ('1', 0.25)])

        record_click(self.conn, ro[0], ro[1])

        self.assertEquals(self.conn.zrange('idx:ad:value:', 0, -1, withscores=True), [('2', 0.125), ('1', 2.5)])
        self.assertEquals(self.conn.zrange('ad:base_value:', 0, -1, withscores=True), [('2', 0.125), ('1', 0.25)])

    def test_is_qualified_for_job(self):
        add_job(self.conn, 'test', ['q1', 'q2', 'q3'])
        self.assertTrue(is_qualified(self.conn, 'test', ['q1', 'q3', 'q2']))
        self.assertFalse(is_qualified(self.conn, 'test', ['q1', 'q2']))

    def test_index_and_find_jobs(self):
        index_job(self.conn, 'test1', ['q1', 'q2', 'q3'])
        index_job(self.conn, 'test2', ['q1', 'q3', 'q4'])
        index_job(self.conn, 'test3', ['q1', 'q3', 'q5'])

        self.assertEquals(find_jobs(self.conn, ['q1']), [])
        self.assertEquals(find_jobs(self.conn, ['q1', 'q3', 'q4']), ['test2'])
        self.assertEquals(find_jobs(self.conn, ['q1', 'q3', 'q5']), ['test3'])
        self.assertEquals(find_jobs(self.conn, ['q1', 'q2', 'q3', 'q4', 'q5']), ['test1', 'test2', 'test3'])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch08_listing_source

import BaseHTTPServer
import cgi
import functools
import json
import math
import random
import socket
import SocketServer
import time
import threading
import unittest
import uuid
import urlparse

import redis

def acquire_lock_with_timeout(
    conn, lockname, acquire_timeout=10, lock_timeout=10):
    identifier = str(uuid.uuid4())                      #A
    lockname = 'lock:' + lockname
    lock_timeout = int(math.ceil(lock_timeout))         #D

    end = time.time() + acquire_timeout
    while time.time() < end:
        if conn.setnx(lockname, identifier):            #B
            conn.expire(lockname, lock_timeout)         #B
            return identifier
        elif not conn.ttl(lockname):                    #C
            conn.expire(lockname, lock_timeout)         #C

        time.sleep(.001)

    return False

def release_lock(conn, lockname, identifier):
    pipe = conn.pipeline(True)
    lockname = 'lock:' + lockname

    while True:
        try:
            pipe.watch(lockname)                  #A
            if pipe.get(lockname) == identifier:  #A
                pipe.multi()                      #B
                pipe.delete(lockname)             #B
                pipe.execute()                    #B
                return True                       #B

            pipe.unwatch()
            break

        except redis.exceptions.WatchError:       #C
            pass                                  #C

    return False                                  #D

CONFIGS = {}
CHECKED = {}

def get_config(conn, type, component, wait=1):
    key = 'config:%s:%s'%(type, component)

    if CHECKED.get(key) < time.time() - wait:           #A
        CHECKED[key] = time.time()                      #B
        config = json.loads(conn.get(key) or '{}')      #C
        old_config = CONFIGS.get(key)                   #D

        if config != old_config:                        #E
            CONFIGS[key] = config                       #F

    return CONFIGS.get(key)

REDIS_CONNECTIONS = {}

def redis_connection(component, wait=1):                        #A
    key = 'config:redis:' + component                           #B
    def wrapper(function):                                      #C
        @functools.wraps(function)                              #D
        def call(*args, **kwargs):                              #E
            old_config = CONFIGS.get(key, object())             #F
            _config = get_config(                               #G
                config_connection, 'redis', component, wait)    #G

            config = {}
            for k, v in _config.iteritems():                    #L
                config[k.encode('utf-8')] = v                   #L

            if config != old_config:                            #H
                REDIS_CONNECTIONS[key] = redis.Redis(**config)  #H

            return function(                                    #I
                REDIS_CONNECTIONS.get(key), *args, **kwargs)    #I
        return call                                             #J
    return wrapper                                              #K

def execute_later(conn, queue, name, args):
    # this is just for testing purposes
    assert conn is args[0]
    t = threading.Thread(target=globals()[name], args=tuple(args))
    t.setDaemon(1)
    t.start()

# <start id="create-twitter-user"/>
def create_user(conn, login, name):
    llogin = login.lower()
    lock = acquire_lock_with_timeout(conn, 'user:' + llogin, 1) #A
    if not lock:                            #B
        return None                         #B

    if conn.hget('users:', llogin):         #C
        return None                         #C

    id = conn.incr('user:id:')              #D
    pipeline = conn.pipeline(True)
    pipeline.hset('users:', llogin, id)     #E
    pipeline.hmset('user:%s'%id, {          #F
        'login': login,                     #F
        'id': id,                           #F
        'name': name,                       #F
        'followers': 0,                     #F
        'following': 0,                     #F
        'posts': 0,                         #F
        'signup': time.time(),              #F
    })
    pipeline.execute()
    release_lock(conn, 'user:' + llogin, lock)  #G
    return id                               #H
# <end id="create-twitter-user"/>
#A Try to acquire the lock for the lowercased version of the login name. This function is defined in chapter 6
#B If we couldn't get the lock, then someone else already has the same login name
#C We also store a HASH of lowercased login names to user ids, so if there is already a login name that maps to an ID, we know and won't give it to a second person
#D Each user is given a unique id, generated by incrementing a counter
#E Add the lowercased login name to the HASH that maps from login names to user ids
#F Add the user information to the user's HASH
#G Release the lock over the login name
#H Return the id of the user
#END

# <start id="create-twitter-status"/>
def create_status(conn, uid, message, **data):
    pipeline = conn.pipeline(True)
    pipeline.hget('user:%s'%uid, 'login')   #A
    pipeline.incr('status:id:')             #B
    login, id = pipeline.execute()

    if not login:                           #C
        return None                         #C

    data.update({
        'message': message,                 #D
        'posted': time.time(),              #D
        'id': id,                           #D
        'uid': uid,                         #D
        'login': login,                     #D
    })
    pipeline.hmset('status:%s'%id, data)    #D
    pipeline.hincrby('user:%s'%uid, 'posts')#E
    pipeline.execute()
    return id                               #F
# <end id="create-twitter-status"/>
#A Get the user's login name from their user id
#B Create a new id for the status message
#C Verify that we have a proper user account before posting
#D Prepare and set the data for the status message
#E Record the fact that a status message has been posted
#F Return the id of the newly created status message
#END

# <start id="fetch-page"/>
def get_status_messages(conn, uid, timeline='home:', page=1, count=30):#A
    statuses = conn.zrevrange(                                  #B
        '%s%s'%(timeline, uid), (page-1)*count, page*count-1)   #B

    pipeline = conn.pipeline(True)
    for id in statuses:                                         #C
        pipeline.hgetall('status:%s'%id)                        #C

    return filter(None, pipeline.execute())                     #D
# <end id="fetch-page"/>
#A We will take an optional 'timeline' argument, as well as page size and status message counts
#B Fetch the most recent status ids in the timeline
#C Actually fetch the status messages themselves
#D Filter will remove any 'missing' status messages that had been previously deleted
#END

# <start id="follow-user"/>
HOME_TIMELINE_SIZE = 1000
def follow_user(conn, uid, other_uid):
    fkey1 = 'following:%s'%uid          #A
    fkey2 = 'followers:%s'%other_uid    #A

    if conn.zscore(fkey1, other_uid):   #B
        return None                     #B

    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zadd(fkey1, other_uid, now)    #C
    pipeline.zadd(fkey2, uid, now)          #C
    pipeline.zcard(fkey1)                           #D
    pipeline.zcard(fkey2)                           #D
    pipeline.zrevrange('profile:%s'%other_uid,      #E
        0, HOME_TIMELINE_SIZE-1, withscores=True)   #E
    following, followers, status_and_score = pipeline.execute()[-3:]

    pipeline.hset('user:%s'%uid, 'following', following)        #F
    pipeline.hset('user:%s'%other_uid, 'followers', followers)  #F
    if status_and_score:
        pipeline.zadd('home:%s'%uid, **dict(status_and_score))  #G
    pipeline.zremrangebyrank('home:%s'%uid, 0, -HOME_TIMELINE_SIZE-1)#G

    pipeline.execute()
    return True                         #H
# <end id="follow-user"/>
#A Cache the following and followers key names
#B If the other_uid is already being followed, return
#C Add the uids to the proper following and followers ZSETs
#D Find the size of the following and followers ZSETs
#E Fetch the most recent HOME_TIMELINE_SIZE status messages from the newly followed user's profile timeline
#F Update the known size of the following and followers ZSETs in each user's HASH
#G Update the home timeline of the following user, keeping only the most recent 1000 status messages
#H Return that the user was correctly followed
#END

# <start id="unfollow-user"/>
def unfollow_user(conn, uid, other_uid):
    fkey1 = 'following:%s'%uid          #A
    fkey2 = 'followers:%s'%other_uid    #A

    if not conn.zscore(fkey1, other_uid):   #B
        return None                         #B

    pipeline = conn.pipeline(True)
    pipeline.zrem(fkey1, other_uid)                 #C
    pipeline.zrem(fkey2, uid)                       #C
    pipeline.zcard(fkey1)                           #D
    pipeline.zcard(fkey2)                           #D
    pipeline.zrevrange('profile:%s'%other_uid,      #E
        0, HOME_TIMELINE_SIZE-1)                    #E
    following, followers, statuses = pipeline.execute()[-3:]

    pipeline.hset('user:%s'%uid, 'following', following)        #F
    pipeline.hset('user:%s'%other_uid, 'followers', followers)  #F
    if statuses:
        pipeline.zrem('home:%s'%uid, *statuses)                 #G

    pipeline.execute()
    return True                         #H
# <end id="unfollow-user"/>
#A Cache the following and followers key names
#B If the other_uid is not being followed, return
#C Remove the uids the proper following and followers ZSETs
#D Find the size of the following and followers ZSETs
#E Fetch the most recent HOME_TIMELINE_SIZE status messages from the user that we stopped following
#F Update the known size of the following and followers ZSETs in each user's HASH
#G Update the home timeline, removing any status messages from the previously followed user
#H Return that the unfollow executed successfully
#END

# <start id="exercise-refilling-timelines"/>
REFILL_USERS_STEP = 50
def refill_timeline(conn, incoming, timeline, start=0):
    if not start and conn.zcard(timeline) >= 750:               #A
        return                                                  #A

    users = conn.zrangebyscore(incoming, start, 'inf',          #B
        start=0, num=REFILL_USERS_STEP, withscores=True)        #B

    pipeline = conn.pipeline(False)
    for uid, start in users:
        pipeline.zrevrange('profile:%s'%uid,                    #C
            0, HOME_TIMELINE_SIZE-1, withscores=True)           #C

    messages = []
    for results in pipeline.execute():
        messages.extend(results)                            #D

    messages.sort(key=lambda x:-x[1])                       #E
    del messages[HOME_TIMELINE_SIZE:]                       #E

    pipeline = conn.pipeline(True)
    if messages:
        pipeline.zadd(timeline, **dict(messages))           #F
    pipeline.zremrangebyrank(                               #G
        timeline, 0, -HOME_TIMELINE_SIZE-1)                 #G
    pipeline.execute()

    if len(users) >= REFILL_USERS_STEP:
        execute_later(conn, 'default', 'refill_timeline',       #H
            [conn, incoming, timeline, start])                  #H
# <end id="exercise-refilling-timelines"/>
#A If the timeline is 3/4 of the way full already, don't bother refilling it
#B Fetch a group of users that should contribute to this timeline
#C Fetch the most recent status messages from the users followed
#D Group all of the fetched status messages together
#E Sort all of the status messages by how recently they were posted, and keep the most recent 1000
#F Add all of the fetched status messages to the user's home timeline
#G Remove any messages that are older than the most recent 1000
#H If there are still more users left to fetch from, keep going
#END

# <start id="exercise-follow-user-list"/>
def follow_user_list(conn, uid, other_uid, list_id):
    fkey1 = 'list:in:%s'%list_id            #A
    fkey2 = 'list:out:%s'%other_uid         #A
    timeline = 'list:statuses:%s'%list_id   #A

    if conn.zscore(fkey1, other_uid):   #B
        return None                     #B

    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zadd(fkey1, other_uid, now)        #C
    pipeline.zadd(fkey2, list_id, now)          #C
    pipeline.zcard(fkey1)                       #D
    pipeline.zrevrange('profile:%s'%other_uid,      #E
        0, HOME_TIMELINE_SIZE-1, withscores=True)   #E
    following, status_and_score = pipeline.execute()[-2:]

    pipeline.hset('list:%s'%list_id, 'following', following)    #F
    pipeline.zadd(timeline, **dict(status_and_score))           #G
    pipeline.zremrangebyrank(timeline, 0, -HOME_TIMELINE_SIZE-1)#G

    pipeline.execute()
    return True                         #H
# <end id="exercise-follow-user"/>
#A Cache the key names
#B If the other_uid is already being followed by the list, return
#C Add the uids to the proper ZSETs
#D Find the size of the list ZSET
#E Fetch the most recent status messages from the user's profile timeline
#F Update the known size of the list ZSETs in the list information HASH
#G Update the list of status messages
#H Return that adding the user to the list completed successfully
#END

# <start id="exercise-unfollow-user-list"/>
def unfollow_user_list(conn, uid, other_uid, list_id):
    fkey1 = 'list:in:%s'%list_id            #A
    fkey2 = 'list:out:%s'%other_uid         #A
    timeline = 'list:statuses:%s'%list_id   #A

    if not conn.zscore(fkey1, other_uid):   #B
        return None                         #B

    pipeline = conn.pipeline(True)
    pipeline.zrem(fkey1, other_uid)                 #C
    pipeline.zrem(fkey2, list_id)                   #C
    pipeline.zcard(fkey1)                           #D
    pipeline.zrevrange('profile:%s'%other_uid,      #E
        0, HOME_TIMELINE_SIZE-1)                    #E
    following, statuses = pipeline.execute()[-2:]

    pipeline.hset('list:%s'%list_id, 'following', following)    #F
    if statuses:
        pipeline.zrem(timeline, *statuses)                      #G
        refill_timeline(fkey1, timeline)                        #H

    pipeline.execute()
    return True                         #I
# <end id="exercise-unfollow-user-list"/>
#A Cache the key names
#B If the other_uid is not being followed by the list, return
#C Remove the uids from the proper ZSETs
#D Find the size of the list ZSET
#E Fetch the most recent status messages from the user that we stopped following
#F Update the known size of the list ZSETs in the list information HASH
#G Update the list timeline, removing any status messages from the previously followed user
#H Start refilling the list timeline
#I Return that the unfollow executed successfully
#END

# <start id="exercise-create-user-list"/>
def create_user_list(conn, uid, name):
    pipeline = conn.pipeline(True)
    pipeline.hget('user:%s'%uid, 'login')   #A
    pipeline.incr('list:id:')               #B
    login, id = pipeline.execute()

    if not login:               #C
        return None             #C

    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zadd('lists:%s'%uid, **{id: now})  #D
    pipeline.hmset('list:%s'%id, {              #E
        'name': name,                           #E
        'id': id,                               #E
        'uid': uid,                             #E
        'login': login,                         #E
        'following': 0,                         #E
        'created': now,                         #E
    })
    pipeline.execute()

    return id           #F
# <end id="exercise-create-user-list"/>
#A Fetch the login name of the user who is creating the list
#B Generate a new list id
#C If the user doesn't exist, return
#D Add the new list to a ZSET of lists that the user has created
#E Create the list information HASH
#F Return the new list id
#END

# <start id="post-message"/>
def post_status(conn, uid, message, **data):
    id = create_status(conn, uid, message, **data)  #A
    if not id:              #B
        return None         #B

    posted = conn.hget('status:%s'%id, 'posted')    #C
    if not posted:                                  #D
        return None                                 #D

    post = {str(id): float(posted)}
    conn.zadd('profile:%s'%uid, **post)             #E

    syndicate_status(conn, uid, post)       #F
    return id
# <end id="post-message"/>
#A Create a status message using the earlier function
#B If the creation failed, return
#C Get the time that the message was posted
#D If the post wasn't found, return
#E Add the status message to the user's profile timeline
#F Actually push the status message out to the followers of the user
#END

# <start id="syndicate-message"/>
POSTS_PER_PASS = 1000           #A
def syndicate_status(conn, uid, post, start=0):
    followers = conn.zrangebyscore('followers:%s'%uid, start, 'inf',#B
        start=0, num=POSTS_PER_PASS, withscores=True)   #B

    pipeline = conn.pipeline(False)
    for follower, start in followers:                    #E
        pipeline.zadd('home:%s'%follower, **post)        #C
        pipeline.zremrangebyrank(                        #C
            'home:%s'%follower, 0, -HOME_TIMELINE_SIZE-1)#C
    pipeline.execute()

    if len(followers) >= POSTS_PER_PASS:                    #D
        execute_later(conn, 'default', 'syndicate_status',  #D
            [conn, uid, post, start])                       #D
# <end id="syndicate-message"/>
#A Only send to 1000 users per pass
#B Fetch the next group of 1000 followers, starting at the last person to be updated last time
#E Iterating through the followers results will update the 'start' variable, which we can later pass on to subsequent syndicate_status() calls
#C Add the status to the home timelines of all of the fetched followers, and trim the home timelines so they don't get too big
#D If at least 1000 followers had received an update, execute the remaining updates in a task
#END

# <start id="syndicate-message-list"/>
def syndicate_status_list(conn, uid, post, start=0, on_lists=False):
    key = 'followers:%s'%uid            #A
    base = 'home:%s'                    #A
    if on_lists:                        #A
        key = 'list:out:%s'%uid         #A
        base = 'list:statuses:%s'       #A
    followers = conn.zrangebyscore(key, start, 'inf',   #B
        start=0, num=POSTS_PER_PASS, withscores=True)   #B

    pipeline = conn.pipeline(False)
    for follower, start in followers:                   #C
        pipeline.zadd(base%follower, **post)            #C
        pipeline.zremrangebyrank(                       #C
            base%follower, 0, -HOME_TIMELINE_SIZE-1)    #C
    pipeline.execute()

    if len(followers) >= POSTS_PER_PASS:                    #D
        execute_later(conn, 'default', 'syndicate_status',  #D
            [conn, uid, post, start, on_lists])             #D

    elif not on_lists:
        execute_later(conn, 'default', 'syndicate_status',  #E
            [conn, uid, post, 0, True])                     #E
# <end id="syndicate-message-list"/>
#A Use keys for home timelines or list timelines, depending on how far along we are
#B Fetch the next group of 1000 followers or lists, starting at the last user or list to be updated last time
#C Add the status to the home timelines of all of the fetched followers, and trim the home timelines so they don't get too big
#D If at least 1000 followers had received an update, execute the remaining updates in a task
#E Start executing over lists if we haven't executed over lists yet, but we are done with home timelines
#END

# <start id="delete-message"/>
def delete_status(conn, uid, status_id):
    key = 'status:%s'%status_id
    lock = acquire_lock_with_timeout(conn, key, 1)  #A
    if not lock:                #B
        return None             #B

    if conn.hget(key, 'uid') != str(uid):   #C
        return None                         #C

    pipeline = conn.pipeline(True)
    pipeline.delete(key)                            #D
    pipeline.zrem('profile:%s'%uid, status_id)      #E
    pipeline.zrem('home:%s'%uid, status_id)         #F
    pipeline.hincrby('user:%s'%uid, 'posts', -1)    #G
    pipeline.execute()

    release_lock(conn, key, lock)
    return True
# <end id="delete-message"/>
#A Acquire a lock around the status object to ensure that no one else is trying to delete it when we are
#B If we didn't get the lock, return
#C If the user doesn't match the user stored in the status message, return
#D Delete the status message
#E Remove the status message id from the user's profile timeline
#F Remove the status message id from the user's home timeline
#G Reduce the number of posted messages in the user information HASH
#END

# <start id="exercise-clean-out-timelines"/>
def clean_timelines(conn, uid, status_id, start=0, on_lists=False):
    key = 'followers:%s'%uid            #A
    base = 'home:%s'                    #A
    if on_lists:                        #A
        key = 'list:out:%s'%uid         #A
        base = 'list:statuses:%s'       #A
    followers = conn.zrangebyscore(key, start, 'inf',   #B
        start=0, num=POSTS_PER_PASS, withscores=True)   #B

    pipeline = conn.pipeline(False)
    for follower, start in followers:                    #C
        pipeline.zrem(base%follower, status_id)          #C
    pipeline.execute()

    if len(followers) >= POSTS_PER_PASS:                    #D
        execute_later(conn, 'default', 'clean_timelines' ,  #D
            [conn, uid, status_id, start, on_lists])        #D

    elif not on_lists:
        execute_later(conn, 'default', 'clean_timelines',   #E
            [conn, uid, status_id, 0, True])                #E
# <end id="exercise-clean-out-timelines"/>
#A Use keys for home timelines or list timelines, depending on how far along we are
#B Fetch the next group of 1000 followers or lists, starting at the last user or list to be updated last time
#C Remove the status from the home timelines of all of the fetched followers
#D If at least 1000 followers had received an update, execute the remaining updates in a task
#E Start executing over lists if we haven't executed over lists yet, but we are done with home timelines
#END

# <start id="streaming-http-server"/>
class StreamingAPIServer(               #A
    SocketServer.ThreadingMixIn,        #B
    BaseHTTPServer.HTTPServer):         #B

    daemon_threads = True               #C

class StreamingAPIRequestHandler(               #D
    BaseHTTPServer.BaseHTTPRequestHandler):     #E

    def do_GET(self):                                       #F
        parse_identifier(self)                              #G
        if self.path != '/statuses/sample.json':            #H
            return self.send_error(404)                     #H

        process_filters(self)                               #I

    def do_POST(self):                                      #J
        parse_identifier(self)                              #K
        if self.path != '/statuses/filter.json':            #L
            return self.send_error(404)                     #L

        process_filters(self)                               #M
# <end id="streaming-http-server"/>
#A Create a new class called 'StreamingAPIServer'
#B This new class should have the ability to create new threads with each request, and should be a HTTPServer
#C Tell the internals of the threading server to shut down all client request threads if the main server thread dies
#D Create a new class called 'StreamingAPIRequestHandler'
#E This new class should be able to handle HTTP requests
#F Create a method that is called do_GET(), which will be executed on GET requests performed against this server
#G Call a helper function that handles the fetching of an identifier for the client
#H If the request is not a 'sample' or 'firehose' streaming GET request, return a '404 not found' error
#I Otherwise, call a helper function that actually handles the filtering
#J Create a method that is called do_POST(), which will be executed on POST requests performed against this server
#K Call a helper function that handles the fetching of an identifier for the client
#L If the request is not a user, keyword, or location filter, return a '404 not found' error
#M Otherwise, call a helper function that actually handles the filtering
#END

# <start id="get-identifier"/>
def parse_identifier(handler):
    handler.identifier = None       #A
    handler.query = {}              #A
    if '?' in handler.path:         #B
        handler.path, _, query = handler.path.partition('?')    #C
        handler.query = urlparse.parse_qs(query)                #D
        identifier = handler.query.get('identifier') or [None]  #E
        handler.identifier = identifier[0]                      #F
# <end id="get-identifier"/>
#A Set the identifier and query arguments to be palceholder values
#B If there were query arguments as part of the request, process them
#C Extract the query portion from the path, and update the path
#D Parse the query
#E Fetch the list of query arguments with the name 'identifier'
#F Use the first identifier passed
#END

# <start id="stream-to-client"/>
FILTERS = ('track', 'filter', 'location')                   #A
def process_filters(handler):
    id = handler.identifier
    if not id:                                              #B
        return handler.send_error(401, "identifier missing")#B

    method = handler.path.rsplit('/')[-1].split('.')[0]     #C
    name = None
    args = None
    if method == 'filter':                                  #D
        data = cgi.FieldStorage(                                #E
            fp=handler.rfile,                                   #E
            headers=handler.headers,                            #E
            environ={'REQUEST_METHOD':'POST',                   #E
                     'CONTENT_TYPE':handler.headers['Content-Type'],#E
        })

        for name in data:                               #F
            if name in FILTERS:                         #F
                args = data.getfirst(name).lower().split(',')   #F
                break                                   #F

        if not args:                                            #G
            return handler.send_error(401, "no filter provided")#G
    else:
        args = handler.query                                #M

    handler.send_response(200)                              #H
    handler.send_header('Transfer-Encoding', 'chunked')     #H
    handler.end_headers()

    quit = [False]                                          #N
    for item in filter_content(id, method, name, args, quit):   #I
        try:
            handler.wfile.write('%X\r\n%s\r\n'%(len(item), item))   #J
        except socket.error:                                    #K
            quit[0] = True                                      #K
    if not quit[0]:
        handler.wfile.write('0\r\n\r\n')                        #L
# <end id="stream-to-client"/>
#A Keep a listing of filters that need arguments
#B Return an error if an identifier was not provided by the client
#C Fetch the method, should be one of 'sample' or 'filter'
#D If this is a filtering method, we need to fetch the arguments
#E Parse the POST request to discover the type and arguments to the filter
#F Fetch any of the filters provided by the client request
#G If there were no filters specified, return an error
#M For sample requests, pass the query arguments as the 'args'
#H Finally return a response to the client, informing them that they will be receiving a streaming response
#N Use a Python list as a holder for a pass-by-reference variable, which will allow us to tell the content filter to stop receiving messages
#I Iterate over the results of the filter
#J Send the pre-encoded response to the client using the chunked encoding
#K If sending to the client caused an error, then we need to tell the subscriber to unsubscribe and shut down
#L Send the "end of chunks" message to the client if we haven't already disconnected
#END

_create_status = create_status
# <start id="create-message-streaming"/>
def create_status(conn, uid, message, **data):
    pipeline = conn.pipeline(True)
    pipeline.hget('user:%s'%uid, 'login')
    pipeline.incr('status:id:')
    login, id = pipeline.execute()

    if not login:
        return None

    data.update({
        'message': message,
        'posted': time.time(),
        'id': id,
        'uid': uid,
        'login': login,
    })
    pipeline.hmset('status:%s'%id, data)
    pipeline.hincrby('user:%s'%uid, 'posts')
    pipeline.publish('streaming:status:', json.dumps(data)) #A
    pipeline.execute()
    return id
# <end id="create-message-streaming"/>
#A The added line to send a message to streaming filters
#END

_delete_status = delete_status
# <start id="delete-message-streaming"/>
def delete_status(conn, uid, status_id):
    key = 'status:%s'%status_id
    lock = acquire_lock_with_timeout(conn, key, 1)
    if not lock:
        return None

    if conn.hget(key, 'uid') != str(uid):
        return None

    pipeline = conn.pipeline(True)
    status = conn.hgetall(key)                                  #A
    status['deleted'] = True                                    #B
    pipeline.publish('streaming:status:', json.dumps(status))   #C
    pipeline.delete(key)
    pipeline.zrem('profile:%s'%uid, status_id)
    pipeline.zrem('home:%s'%uid, status_id)
    pipeline.hincrby('user:%s'%uid, 'posts', -1)
    pipeline.execute()

    release_lock(conn, key, lock)
    return True
# <end id="delete-message-streaming"/>
#A Fetch the status message so that streaming filters can perform the same filters to determine whether the deletion should be passed to the client
#B Mark the status message as deleted
#C Publish the deleted status message to the stream
#END

# <start id="message-subscription"/>
@redis_connection('social-network')                         #A
def filter_content(conn, id, method, name, args, quit):
    match = create_filters(id, method, name, args)          #B

    pubsub = conn.pubsub()                      #C
    pubsub.subscribe(['streaming:status:'])     #C

    for item in pubsub.listen():                #D
        message = item['data']                  #E
        decoded = json.loads(message)           #E

        if match(decoded):                      #F
            if decoded.get('deleted'):                      #G
                yield json.dumps({                          #G
                    'id': decoded['id'], 'deleted': True})  #G
            else:
                yield message                   #H

        if quit[0]:                             #I
            break                               #I

    pubsub.reset()                              #J
# <end id="message-subscription"/>
#A Use our automatic connection decorator from chapter 5
#B Create the filter that will determine whether a message should be sent to the client
#C Prepare the subscription
#D Receive messages from the subscription
#E Get the status message information from the subscription structure
#F Check if the status message matched the filter
#G For deleted messages, send a special 'deleted' placeholder for the message
#H For matched status messages that are not deleted, send the message itself
#I If the web server no longer has a connection to the client, stop filtering messages
#J Reset the Redis connection to ensure that the Redis server clears its outgoing buffers if this wasn't fast enough
#END

# <start id="create-filters"/>
def create_filters(id, method, name, args):
    if method == 'sample':                      #A
        return SampleFilter(id, args)           #A
    elif name == 'track':                       #B
        return TrackFilter(args)                #B
    elif name == 'follow':                      #B
        return FollowFilter(args)               #B
    elif name == 'location':                    #B
        return LocationFilter(args)             #B
    raise Exception("Unknown filter")           #C
# <end id="create-filters"/>
#A For the 'sample' method, we don't need to worry about names, just the arguments
#B For the 'filter' method, we actually worry about which of the filters we want to apply, so return the specific filters for them
#C If no filter matches, then raise an exception
#END

# <start id="sample-filter"/>
def SampleFilter(id, args):                             #A
    percent = int(args.get('percent', ['10'])[0], 10)   #B
    ids = range(100)                                    #C
    shuffler = random.Random(id)                        #C
    shuffler.shuffle(ids)                               #C
    keep = set(ids[:max(percent, 1)])                   #D

    def check(status):                                  #E
        return (status['id'] % 100) in keep             #F
    return check
# <end id="sample-filter"/>
#A We are defining a filter class called "SampleFilter", which are created by passing 'id' and 'args' parameters
#B The 'args' parameter is actually a dictionary, based on the parameters passed as part of the GET request
#C We use the 'id' parameter to randomly choose a subset of ids, the count of which is determined by the 'percent' argument passed
#D We will use a Python set to allow us to quickly determine whether a status message matches our criteria
#E If we create a specially named method called '__call__' on an instance, it will be called if the instance is used like a function
#F To filter status messages, we fetch the status id, find its value modulo 100, and return whether it is in the status ids that we want to accept
#END

# <start id="track-filter"/>
def TrackFilter(list_of_strings):
    groups = []                                 #A
    for group in list_of_strings:               #A
        group = set(group.lower().split())      #A
        if group:
            groups.append(group)                #B

    def check(status):
        message_words = set(status['message'].lower().split())  #C
        for group in groups:                                #D
            if len(group & message_words) == len(group):    #E
                return True                                 #E
        return False
    return check
# <end id="track-filter"/>
#A The filter should have been provided with a list of word groups, and the filter matches if a message has all of the words in any of the groups
#B We will only keep groups that have at least 1 word
#C We are going to split words in the message on whitespace
#D Then we are going to iterate over all of the groups
#E If all of the words in any of the groups match, we will accept the message with this filter
#END

# <start id="follow-filter"/>
def FollowFilter(names):
    names = set()                                   #A
    for name in names:                              #B
        names.add('@' + name.lower().lstrip('@'))   #B

    def check(status):
        message_words = set(status['message'].lower().split())  #C
        message_words.add('@' + status['login'].lower())        #C

        return message_words & names                            #D
    return check
# <end id="follow-filter"/>
#A We are going to try to match login names against posters and messages
#B Make all of the names consistently stored as '@username'
#C Construct a set of words from the message and the poster's name
#D Consider the message a match if any of the usernames provided match any of the whitespace-separated words in the message
#END

# <start id="location-filter"/>
def LocationFilter(list_of_boxes):
    boxes = []                                                  #A
    for start in xrange(0, len(list_of_boxes)-3, 4):            #A
        boxes.append(map(float, list_of_boxes[start:start+4]))  #A

    def check(self, status):
        location = status.get('location')           #B
        if not location:                            #C
            return False                            #C

        lat, lon = map(float, location.split(','))  #D
        for box in self.boxes:                      #E
            if (box[1] <= lat <= box[3] and         #F
                box[0] <= lon <= box[2]):           #F
                return True                         #F
        return False
    return check
# <end id="location-filter"/>
#A We are going to create a set of boxes that define the regions that should return messages
#B Try to fetch 'location' data from a status message
#C If the message has no location information, then it can't be inside the boxes
#D Otherwise, extract the latitude and longitude of the location
#E To match one of the boxes, we need to iterate over all boxes
#F If the message status location is within the required latitude and longitude range, then the status message matches the filter
#END

_filter_content = filter_content
def filter_content(identifier, method, name, args, quit):
    print "got:", identifier, method, name, args
    for i in xrange(10):
        yield json.dumps({'id':i})
        if quit[0]:
            break
        time.sleep(.1)
'''
# <start id="start-http-server"/>
if __name__ == '__main__':                  #A
    server = StreamingAPIServer(                        #B
        ('localhost', 8080), StreamingAPIRequestHandler)#B
    print 'Starting server, use <Ctrl-C> to stop'       #C
    server.serve_forever()                  #D
# <end id="start-http-server"/>
#A Run the below block of code if this module is being run from the command line
#B Create an insteance of the streaming API server listening on localhost port 8080, and use the StreamingAPIRequestHandler to process requests
#C Print an informational line
#D Run the server until someone kills it
#END
'''

class TestCh08(unittest.TestCase):
    def setUp(self):
        self.conn = redis.Redis(db=15)
        self.conn.flushdb()
    def tearDown(self):
        self.conn.flushdb()

    def test_create_user_and_status(self):
        self.assertEquals(create_user(self.conn, 'TestUser', 'Test User'), 1)
        self.assertEquals(create_user(self.conn, 'TestUser', 'Test User2'), None)

        self.assertEquals(create_status(self.conn, 1, "This is a new status message"), 1)
        self.assertEquals(self.conn.hget('user:1', 'posts'), '1')

    def test_follow_unfollow_user(self):
        self.assertEquals(create_user(self.conn, 'TestUser', 'Test User'), 1)
        self.assertEquals(create_user(self.conn, 'TestUser2', 'Test User2'), 2)
        
        self.assertTrue(follow_user(self.conn, 1, 2))
        self.assertEquals(self.conn.zcard('followers:2'), 1)
        self.assertEquals(self.conn.zcard('followers:1'), 0)
        self.assertEquals(self.conn.zcard('following:1'), 1)
        self.assertEquals(self.conn.zcard('following:2'), 0)
        self.assertEquals(self.conn.hget('user:1', 'following'), '1')
        self.assertEquals(self.conn.hget('user:2', 'following'), '0')
        self.assertEquals(self.conn.hget('user:1', 'followers'), '0')
        self.assertEquals(self.conn.hget('user:2', 'followers'), '1')

        self.assertEquals(unfollow_user(self.conn, 2, 1), None)
        self.assertEquals(unfollow_user(self.conn, 1, 2), True)
        self.assertEquals(self.conn.zcard('followers:2'), 0)
        self.assertEquals(self.conn.zcard('followers:1'), 0)
        self.assertEquals(self.conn.zcard('following:1'), 0)
        self.assertEquals(self.conn.zcard('following:2'), 0)
        self.assertEquals(self.conn.hget('user:1', 'following'), '0')
        self.assertEquals(self.conn.hget('user:2', 'following'), '0')
        self.assertEquals(self.conn.hget('user:1', 'followers'), '0')
        self.assertEquals(self.conn.hget('user:2', 'followers'), '0')
        
    def test_syndicate_status(self):
        self.assertEquals(create_user(self.conn, 'TestUser', 'Test User'), 1)
        self.assertEquals(create_user(self.conn, 'TestUser2', 'Test User2'), 2)
        self.assertTrue(follow_user(self.conn, 1, 2))
        self.assertEquals(self.conn.zcard('followers:2'), 1)
        self.assertEquals(self.conn.hget('user:1', 'following'), '1')
        self.assertEquals(post_status(self.conn, 2, 'this is some message content'), 1)
        self.assertEquals(len(get_status_messages(self.conn, 1)), 1)

        for i in xrange(3, 11):
            self.assertEquals(create_user(self.conn, 'TestUser%s'%i, 'Test User%s'%i), i)
            follow_user(self.conn, i, 2)

        global POSTS_PER_PASS
        POSTS_PER_PASS = 5
        
        self.assertEquals(post_status(self.conn, 2, 'this is some other message content'), 2)
        time.sleep(.1)
        self.assertEquals(len(get_status_messages(self.conn, 9)), 2)

        self.assertTrue(unfollow_user(self.conn, 1, 2))
        self.assertEquals(len(get_status_messages(self.conn, 1)), 0)

    def test_refill_timeline(self):
        self.assertEquals(create_user(self.conn, 'TestUser', 'Test User'), 1)
        self.assertEquals(create_user(self.conn, 'TestUser2', 'Test User2'), 2)
        self.assertEquals(create_user(self.conn, 'TestUser3', 'Test User3'), 3)
        
        self.assertTrue(follow_user(self.conn, 1, 2))
        self.assertTrue(follow_user(self.conn, 1, 3))

        global HOME_TIMELINE_SIZE
        HOME_TIMELINE_SIZE = 5
        
        for i in xrange(10):
            self.assertTrue(post_status(self.conn, 2, 'message'))
            self.assertTrue(post_status(self.conn, 3, 'message'))
            time.sleep(.05)

        self.assertEquals(len(get_status_messages(self.conn, 1)), 5)
        self.assertTrue(unfollow_user(self.conn, 1, 2))
        self.assertTrue(len(get_status_messages(self.conn, 1)) < 5)

        refill_timeline(self.conn, 'following:1', 'home:1')
        messages = get_status_messages(self.conn, 1)
        self.assertEquals(len(messages), 5)
        for msg in messages:
            self.assertEquals(msg['uid'], '3')
        
        delete_status(self.conn, '3', messages[-1]['id'])
        self.assertEquals(len(get_status_messages(self.conn, 1)), 4)
        self.assertEquals(self.conn.zcard('home:1'), 5)
        clean_timelines(self.conn, '3', messages[-1]['id'])
        self.assertEquals(self.conn.zcard('home:1'), 4)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch09_listing_source

import binascii
import bisect
from datetime import date, timedelta
from collections import defaultdict
import math
import time
import unittest
import uuid

import redis

def readblocks(conn, key, blocksize=2**17):
    lb = blocksize
    pos = 0
    while lb == blocksize:                                  #A
        block = conn.substr(key, pos, pos + blocksize - 1)  #B
        yield block                                         #C
        lb = len(block)                                     #C
        pos += lb                                           #C
    yield ''

'''
# <start id="ziplist-configuration-options"/>
list-max-ziplist-entries 512    #A
list-max-ziplist-value 64       #A

hash-max-ziplist-entries 512    #B
hash-max-ziplist-value 64       #B

zset-max-ziplist-entries 128    #C
zset-max-ziplist-value 64       #C
# <end id="ziplist-configuration-options"/>
#A Limits for ziplist use with LISTs
#B Limits for ziplist use with HASHes (previous versions of Redis used a different name and encoding for this)
#C Limits for ziplist use with ZSETs
#END
'''

'''
# <start id="ziplist-test"/>
>>> conn.rpush('test', 'a', 'b', 'c', 'd')  #A
4                                           #A
>>> conn.debug_object('test')                                       #B
{'encoding': 'ziplist', 'refcount': 1, 'lru_seconds_idle': 20,      #C
'lru': 274841, 'at': '0xb6c9f120', 'serializedlength': 24,          #C
'type': 'Value'}                                                    #C
>>> conn.rpush('test', 'e', 'f', 'g', 'h')  #D
8                                           #D
>>> conn.debug_object('test')
{'encoding': 'ziplist', 'refcount': 1, 'lru_seconds_idle': 0,   #E
'lru': 274846, 'at': '0xb6c9f120', 'serializedlength': 36,      #E
'type': 'Value'}
>>> conn.rpush('test', 65*'a')          #F
9
>>> conn.debug_object('test')
{'encoding': 'linkedlist', 'refcount': 1, 'lru_seconds_idle': 10,   #F
'lru': 274851, 'at': '0xb6c9f120', 'serializedlength': 30,          #G
'type': 'Value'}
>>> conn.rpop('test')                                               #H
'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
>>> conn.debug_object('test')
{'encoding': 'linkedlist', 'refcount': 1, 'lru_seconds_idle': 0,    #H
'lru': 274853, 'at': '0xb6c9f120', 'serializedlength': 17,
'type': 'Value'}
# <end id="ziplist-test"/>
#A Let's start by pushing 4 items onto a LIST
#B We can discover information about a particular object with the 'debug object' command
#C The information we are looking for is the 'encoding' information, which tells us that this is a ziplist, which is using 24 bytes of memory
#D Let's push 4 more items onto the LIST
#E We still have a ziplist, and its size grew to 36 bytes (which is exactly 2 bytes overhead, 1 byte data, for each of the 4 items we just pushed)
#F When we push an item bigger than what was allowed for the encoding, the LIST gets converted from the ziplist encoding to a standard linked list
#G While the serialized length went down, for non-ziplist encodings (except for the special encoding for SETs), this number doesn't represent the amount of actual memory used by the structure
#H After a ziplist is converted to a regular structure, it doesn't get re-encoded as a ziplist if the structure later meets the criteria
#END
'''

'''
# <start id="intset-configuration-option"/>
set-max-intset-entries 512      #A
# <end id="intset-configuration-option"/>
#A Limits for intset use with SETs
#END
'''

'''
# <start id="intset-test"/>
>>> conn.sadd('set-object', *range(500))    #A
500
>>> conn.debug_object('set-object')         #A
{'encoding': 'intset', 'refcount': 1, 'lru_seconds_idle': 0,    #A
'lru': 283116, 'at': '0xb6d1a1c0', 'serializedlength': 1010,
'type': 'Value'}
>>> conn.sadd('set-object', *range(500, 1000))  #B
500
>>> conn.debug_object('set-object')             #B
{'encoding': 'hashtable', 'refcount': 1, 'lru_seconds_idle': 0, #B
'lru': 283118, 'at': '0xb6d1a1c0', 'serializedlength': 2874,
'type': 'Value'}
# <end id="intset-test"/>
#A Let's add 500 items to the set and see that it is still encoded as an intset
#B But when we push it over our configured 512 item limit, the intset is translated into a hash table representation
#END
'''

# <start id="rpoplpush-benchmark"/>
def long_ziplist_performance(conn, key, length, passes, psize): #A
    conn.delete(key)                    #B
    conn.rpush(key, *range(length))     #C
    pipeline = conn.pipeline(False)     #D

    t = time.time()                     #E
    for p in xrange(passes):            #F
        for pi in xrange(psize):        #G
            pipeline.rpoplpush(key, key)#H
        pipeline.execute()              #I

    return (passes * psize) / (time.time() - t or .001) #J
# <end id="rpoplpush-benchmark"/>
#A We are going to parameterize everything so that we can measure performance in a variety of ways
#B Start by deleting the named key to ensure that we only benchmark exactly what we intend to
#C Initialize the LIST by pushing our desired count of numbers onto the right end
#D Prepare a pipeline so that we are less affected by network round-trip times
#E Start the timer
#F We will perform a number of pipeline executions provided by 'passes'
#G Each pipeline execution will include 'psize' actual calls to RPOPLPUSH
#H Each call will result in popping the rightmost item from the LIST, pushing to the left end of the same LIST
#I Execute the 'psize' calls to RPOPLPUSH
#J Calculate the number of calls per second that are performed
#END

'''
# <start id="rpoplpush-performance"/>
>>> long_ziplist_performance(conn, 'list', 1, 1000, 100)        #A
52093.558416505381                                              #A
>>> long_ziplist_performance(conn, 'list', 100, 1000, 100)      #A
51501.154762768667                                              #A
>>> long_ziplist_performance(conn, 'list', 1000, 1000, 100)     #A
49732.490843316067                                              #A
>>> long_ziplist_performance(conn, 'list', 5000, 1000, 100)     #B
43424.056529592635                                              #B
>>> long_ziplist_performance(conn, 'list', 10000, 1000, 100)    #B
36727.062573334966                                              #B
>>> long_ziplist_performance(conn, 'list', 50000, 1000, 100)    #C
16695.140684975777                                              #C
>>> long_ziplist_performance(conn, 'list', 100000, 500, 100)    #D
553.10821080054586                                              #D
# <end id="rpoplpush-performance"/>
#A With lists encoded as ziplists at 1000 entries or smaller, Redis is still able to perform around 50,000 operations per second or better
#B But as lists encoded as ziplists grow to 5000 or more, performance starts to drop off as memory copy costs start reducing performance
#C Once we hit 50,000 entries in a ziplist, performance has dropped significantly
#D And once we hit 100,000 entries, ziplists are effectively unusable
#END
'''

def long_ziplist_index(conn, key, length, passes, psize): #A
    conn.delete(key)                    #B
    conn.rpush(key, *range(length))     #C
    length >>= 1
    pipeline = conn.pipeline(False)     #D
    t = time.time()                     #E
    for p in xrange(passes):            #F
        for pi in xrange(psize):        #G
            pipeline.lindex(key, length)#H
        pipeline.execute()              #I
    return (passes * psize) / (time.time() - t or .001) #J

def long_intset_performance(conn, key, length, passes, psize): #A
    conn.delete(key)                    #B
    conn.sadd(key, *range(1000000, 1000000+length))     #C
    cur = 1000000-1
    pipeline = conn.pipeline(False)     #D
    t = time.time()                     #E
    for p in xrange(passes):            #F
        for pi in xrange(psize):        #G
            pipeline.spop(key)#H
            pipeline.sadd(key, cur)
            cur -= 1
        pipeline.execute()              #I
    return (passes * psize) / (time.time() - t or .001) #J


# <start id="calculate-shard-key"/>
def shard_key(base, key, total_elements, shard_size):   #A
    if isinstance(key, (int, long)) or key.isdigit():   #B
        shard_id = int(str(key), 10) // shard_size      #C
    else:
        shards = 2 * total_elements // shard_size       #D
        shard_id = binascii.crc32(key) % shards         #E
    return "%s:%s"%(base, shard_id)                     #F
# <end id="calculate-shard-key"/>
#A We will call the shard_key() function with a base HASH name, along with the key to be stored in the sharded HASH, the total number of expected elements, and the desired shard size
#B If the value is an integer or a string that looks like an integer, we will use it directly to calculate the shard id
#C For integers, we assume they are sequentially assigned ids, so we can choose a shard id based on the upper 'bits' of the numeric id itself. We also use an explicit base here (necessitating the str() call) so that a key of '010' turns into 10, and not 8
#D For non-integer keys, we first calculate the total number of shards desired, based on an expected total number of elements and desired shard size
#E When we know the number of shards we want, we hash the key and find its value modulo the number of shards we want
#F Finally, we combine the base key with the shard id we calculated to determine the shard key
#END

# <start id="sharded-hset-hget"/>
def shard_hset(conn, base, key, value, total_elements, shard_size):
    shard = shard_key(base, key, total_elements, shard_size)    #A
    return conn.hset(shard, key, value)                         #B

def shard_hget(conn, base, key, total_elements, shard_size):
    shard = shard_key(base, key, total_elements, shard_size)    #C
    return conn.hget(shard, key)                                #D
# <end id="sharded-hset-hget"/>
#A Calculate the shard to store our value in
#B Set the value in the shard
#C Calculate the shard to fetch our value from
#D Get the value in the shard
#END

'''
# <start id="sharded-ip-lookup"/>
TOTAL_SIZE = 320000                                             #A
SHARD_SIZE = 1024                                               #A

def import_cities_to_redis(conn, filename):
    for row in csv.reader(open(filename)):
        ...
        shard_hset(conn, 'cityid2city:', city_id,               #B
            json.dumps([city, region, country]),                #B
            TOTAL_SIZE, SHARD_SIZE)                             #B

def find_city_by_ip(conn, ip_address):
    ...
    data = shard_hget(conn, 'cityid2city:', city_id,            #C
        TOTAL_SIZE, SHARD_SIZE)                                 #C
    return json.loads(data)
# <end id="sharded-ip-lookup"/>
#A We set the arguments for the sharded calls as global constants to ensure that we always pass the same information
#B To set the data, we need to pass the TOTAL_SIZE and SHARD_SIZE information, though in this case TOTAL_SIZE is unused because our ids are numeric
#C To fetch the data, we need to use the same information for TOTAL_SIZE and SHARD_SIZE for general sharded keys
#END
'''

# <start id="sharded-sadd"/>
def shard_sadd(conn, base, member, total_elements, shard_size):
    shard = shard_key(base,
        'x'+str(member), total_elements, shard_size)            #A
    return conn.sadd(shard, member)                             #B
# <end id="sharded-sadd"/>
#A Shard the member into one of the sharded SETs, remember to turn it into a string because it isn't a sequential id
#B Actually add the member to the shard
#END

# <start id="unique-visitor-count"/>
SHARD_SIZE = 512                        #B

def count_visit(conn, session_id):
    today = date.today()                                #C
    key = 'unique:%s'%today.isoformat()                 #C
    expected = get_expected(conn, key, today)           #D
 
    id = int(session_id.replace('-', '')[:15], 16)      #E
    if shard_sadd(conn, key, id, expected, SHARD_SIZE): #F
        conn.incr(key)                                  #G
# <end id="unique-visitor-count"/>
#B And we stick with a typical shard size for the intset encoding for SETs
#C Get today's date and generate the key for the unique count
#D Fetch or calculate the expected number of unique views today
#E Calculate the 56 bit id for this 128 bit UUID
#F Add the id to the sharded SET
#G If the id wasn't in the sharded SET, then we increment our uniqie view count
#END

# <start id="expected-viewer-count"/>
DAILY_EXPECTED = 1000000                                #I
EXPECTED = {}                                           #A

def get_expected(conn, key, today):
    if key in EXPECTED:                                 #B
        return EXPECTED[key]                            #B
 
    exkey = key + ':expected'
    expected = conn.get(exkey)                          #C
 
    if not expected:
        yesterday = (today - timedelta(days=1)).isoformat() #D
        expected = conn.get('unique:%s'%yesterday)          #D
        expected = int(expected or DAILY_EXPECTED)          #D
 
        expected = 2**int(math.ceil(math.log(expected*1.5, 2))) #E
        if not conn.setnx(exkey, expected):                 #F
            expected = conn.get(exkey)                      #G
 
    EXPECTED[key] = int(expected)                       #H
    return EXPECTED[key]                                #H
# <end id="expected-viewer-count"/>
#I We start with an initial expected number of daily visits that may be a little high
#A Keep a local copy of any calculated expected counts
#B If we have already calculated or seen the expected number of views for today, use that number
#C If someone else has already calculated the expected number of views for today, use that number
#D Fetch the unique count for yesterday, or if not available, use our default 1 million
#E Add 50% to yesterday's count, and round up to the next even power of 2, under the assumption that view count today should be at least 50% better than yesterday
#F Save our calculated expected number of views back to Redis for other calls if possible
#G If someone else stored the expected count for today before us, use their count instead
#H Keep a local copy of today's expected number of hits, and return it back to the caller
#END

# <start id="location-tables"/>
COUNTRIES = '''
ABW AFG AGO AIA ALA ALB AND ARE ARG ARM ASM ATA ATF ATG AUS AUT AZE BDI
BEL BEN BES BFA BGD BGR BHR BHS BIH BLM BLR BLZ BMU BOL BRA BRB BRN BTN
BVT BWA CAF CAN CCK CHE CHL CHN CIV CMR COD COG COK COL COM CPV CRI CUB
CUW CXR CYM CYP CZE DEU DJI DMA DNK DOM DZA ECU EGY ERI ESH ESP EST ETH
FIN FJI FLK FRA FRO FSM GAB GBR GEO GGY GHA GIB GIN GLP GMB GNB GNQ GRC
GRD GRL GTM GUF GUM GUY HKG HMD HND HRV HTI HUN IDN IMN IND IOT IRL IRN
IRQ ISL ISR ITA JAM JEY JOR JPN KAZ KEN KGZ KHM KIR KNA KOR KWT LAO LBN
LBR LBY LCA LIE LKA LSO LTU LUX LVA MAC MAF MAR MCO MDA MDG MDV MEX MHL
MKD MLI MLT MMR MNE MNG MNP MOZ MRT MSR MTQ MUS MWI MYS MYT NAM NCL NER
NFK NGA NIC NIU NLD NOR NPL NRU NZL OMN PAK PAN PCN PER PHL PLW PNG POL
PRI PRK PRT PRY PSE PYF QAT REU ROU RUS RWA SAU SDN SEN SGP SGS SHN SJM
SLB SLE SLV SMR SOM SPM SRB SSD STP SUR SVK SVN SWE SWZ SXM SYC SYR TCA
TCD TGO THA TJK TKL TKM TLS TON TTO TUN TUR TUV TWN TZA UGA UKR UMI URY
USA UZB VAT VCT VEN VGB VIR VNM VUT WLF WSM YEM ZAF ZMB ZWE'''.split()#A

STATES = {
    'CAN':'''AB BC MB NB NL NS NT NU ON PE QC SK YT'''.split(),       #B
    'USA':'''AA AE AK AL AP AR AS AZ CA CO CT DC DE FL FM GA GU HI IA ID
IL IN KS KY LA MA MD ME MH MI MN MO MP MS MT NC ND NE NH NJ NM NV NY OH
OK OR PA PR PW RI SC SD TN TX UT VA VI VT WA WI WV WY'''.split(),     #C
}
# <end id="location-tables"/>
#A A table of ISO 3 country codes. Calling 'split()' will split the string on whitespace, turning the string into a list of country codes
#B Province/territory information for Canada
#C State information for the United States
#END

# <start id="location-to-code"/>
def get_code(country, state):
    cindex = bisect.bisect_left(COUNTRIES, country)             #A
    if cindex > len(COUNTRIES) or COUNTRIES[cindex] != country: #B
        cindex = -1                                             #B
    cindex += 1                                                 #C

    sindex = -1
    if state and country in STATES:
        states = STATES[country]                                #D
        sindex = bisect.bisect_left(states, state)              #E
        if sindex > len(states) or states[sindex] != state:     #F
            sindex = -1                                         #F
    sindex += 1                                                 #G

    return chr(cindex) + chr(sindex)                            #H
# <end id="location-to-code"/>
#A Find the offset for the country
#B If the country isn't found, then set its index to be -1
#C Because uninitialized data in Redis will return as nulls, we want 'not found' to be 0, and the first country to be 1
#D Pull the state information for the country, if it is available
#E Find the offset for the state
#F Handle not-found states like we did with countries
#G Keep not-found states at 0, and found states > 0
#H The chr() function will turn an integer value of 0..255 into the ascii character with that same value
#END

# <start id="set-location-information"/>
USERS_PER_SHARD = 2**20                                     #A

def set_location(conn, user_id, country, state):
    code = get_code(country, state)                         #B
    
    shard_id, position = divmod(user_id, USERS_PER_SHARD)   #C
    offset = position * 2                                   #D

    pipe = conn.pipeline(False)
    pipe.setrange('location:%s'%shard_id, offset, code)     #E

    tkey = str(uuid.uuid4())                                #F
    pipe.zadd(tkey, 'max', user_id)                         #F
    pipe.zunionstore('location:max',                        #F
        [tkey, 'location:max'], aggregate='max')            #F
    pipe.delete(tkey)                                       #F

    pipe.execute()
# <end id="set-location-information"/>
#A Set the size of each shard
#B Get the location code to store for the user
#C Find the shard id and position of the user in the specific shard
#D Calculate the offset of the user's data
#E Set the value in the proper sharded location table
#F Update a ZSET that stores the maximum user id seen so far
#END

# <start id="aggregate-population"/>
def aggregate_location(conn):
    countries = defaultdict(int)                                #A
    states = defaultdict(lambda:defaultdict(int))               #A

    max_id = int(conn.zscore('location:max', 'max'))            #B
    max_block = max_id // USERS_PER_SHARD                       #B

    for shard_id in xrange(max_block + 1):                      #C
        for block in readblocks(conn, 'location:%s'%shard_id):  #D
            for offset in xrange(0, len(block)-1, 2):           #E
                code = block[offset:offset+2]
                update_aggregates(countries, states, [code])    #F

    return countries, states
# <end id="aggregate-population"/>
#A Initialize two special structures that will allow us to quickly update existing and missing counters quickly
#B Fetch the maximum user id known, and use that to calculate the maximum shard id that we need to visit
#C Sequentially check every shard
#D ... reading each block
#E Extract each code from the block and look up the original location information (like USA, CA for someone who lives in California)
#F Update our aggregates
#END

# <start id="code-to-location"/>
def update_aggregates(countries, states, codes):
    for code in codes:
        if len(code) != 2:                              #A
            continue                                    #A

        country = ord(code[0]) - 1                      #B
        state = ord(code[1]) - 1                        #B
        
        if country < 0 or country >= len(COUNTRIES):    #C
            continue                                    #C

        country = COUNTRIES[country]                    #D
        countries[country] += 1                         #E

        if country not in STATES:                       #F
            continue                                    #F
        if state < 0 or state >= STATES[country]:       #F
            continue                                    #F

        state = STATES[country][state]                  #G
        states[country][state] += 1                     #H
# <end id="code-to-location"/>
#A Only look up codes that could be valid
#B Calculate the actual offset of the country and state in the lookup tables
#C If the country is out of the range of valid countries, continue to the next code
#D Fetch the ISO-3 country code
#E Count this user in the decoded country
#F If we don't have state information or if the state is out of the range of valid states for the country, continue to the next code
#G Fetch the state name from the code
#H Increment the count for the state
#END

# <start id="aggregate-limited"/>
def aggregate_location_list(conn, user_ids):
    pipe = conn.pipeline(False)                                 #A
    countries = defaultdict(int)                                #B
    states = defaultdict(lambda: defaultdict(int))              #B

    for i, user_id in enumerate(user_ids):
        shard_id, position = divmod(user_id, USERS_PER_SHARD)   #C
        offset = position * 2                                   #C

        pipe.substr('location:%s'%shard_id, offset, offset+1)   #D

        if (i+1) % 1000 == 0:                                   #E
            update_aggregates(countries, states, pipe.execute())#E

    update_aggregates(countries, states, pipe.execute())        #F

    return countries, states                                    #G
# <end id="aggregate-limited"/>
#A Set up the pipeline so that we aren't making too many round-trips to Redis
#B Set up our base aggregates as we did before
#C Calculate the shard id and offset into the shard for this user's location
#D Send another pipelined command to fetch the location information for the user
#E Every 1000 requests, we will actually update the aggregates using the helper function we defined before
#F Handle the last hunk of users that we might have missed before
#G Return the aggregates
#END

class TestCh09(unittest.TestCase):
    def setUp(self):
        self.conn = redis.Redis(db=15)
        self.conn.flushdb()
    def tearDown(self):
        self.conn.flushdb()

    def test_long_ziplist_performance(self):
        long_ziplist_performance(self.conn, 'test', 5, 10, 10)
        self.assertEquals(self.conn.llen('test'), 5)

    def test_shard_key(self):
        base = 'test'
        self.assertEquals(shard_key(base, 1, 2, 2), 'test:0')
        self.assertEquals(shard_key(base, '1', 2, 2), 'test:0')
        self.assertEquals(shard_key(base, 125, 1000, 100), 'test:1')
        self.assertEquals(shard_key(base, '125', 1000, 100), 'test:1')

        for i in xrange(50):
            self.assertTrue(0 <= int(shard_key(base, 'hello:%s'%i, 1000, 100).partition(':')[-1]) < 20)
            self.assertTrue(0 <= int(shard_key(base, i, 1000, 100).partition(':')[-1]) < 10)

    def test_sharded_hash(self):
        for i in xrange(50):
            shard_hset(self.conn, 'test', 'keyname:%s'%i, i, 1000, 100)
            self.assertEquals(shard_hget(self.conn, 'test', 'keyname:%s'%i, 1000, 100), str(i))
            shard_hset(self.conn, 'test2', i, i, 1000, 100)
            self.assertEquals(shard_hget(self.conn, 'test2', i, 1000, 100), str(i))

    def test_sharded_sadd(self):
        for i in xrange(50):
            shard_sadd(self.conn, 'testx', i, 50, 50)
        self.assertEquals(self.conn.scard('testx:0') + self.conn.scard('testx:1'), 50)

    def test_unique_visitors(self):
        global DAILY_EXPECTED
        DAILY_EXPECTED = 10000
        
        for i in xrange(179):
            count_visit(self.conn, str(uuid.uuid4()))
        self.assertEquals(self.conn.get('unique:%s'%(date.today().isoformat())), '179')

        self.conn.flushdb()
        self.conn.set('unique:%s'%((date.today() - timedelta(days=1)).isoformat()), 1000)
        for i in xrange(183):
            count_visit(self.conn, str(uuid.uuid4()))
        self.assertEquals(self.conn.get('unique:%s'%(date.today().isoformat())), '183')

    def test_user_location(self):
        i = 0
        for country in COUNTRIES:
            if country in STATES:
                for state in STATES[country]:
                    set_location(self.conn, i, country, state)
                    i += 1
            else:
                set_location(self.conn, i, country, '')
                i += 1
        
        _countries, _states = aggregate_location(self.conn)
        countries, states = aggregate_location_list(self.conn, range(i+1))
        
        self.assertEquals(_countries, countries)
        self.assertEquals(_states, states)

        for c in countries:
            if c in STATES:
                self.assertEquals(len(STATES[c]), countries[c])
                for s in STATES[c]:
                    self.assertEquals(states[c][s], 1)
            else:
                self.assertEquals(countries[c], 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch10_listing_source

import binascii
from collections import defaultdict
from datetime import date
from decimal import Decimal
import functools
import json
from Queue import Empty, Queue
import threading
import time
import unittest
import uuid

import redis

CONFIGS = {}
CHECKED = {}

def get_config(conn, type, component, wait=1):
    key = 'config:%s:%s'%(type, component)

    if CHECKED.get(key) < time.time() - wait:           #A
        CHECKED[key] = time.time()                      #B
        config = json.loads(conn.get(key) or '{}')      #C
        config = dict((str(k), config[k]) for k in config)
        old_config = CONFIGS.get(key)                   #D

        if config != old_config:                        #E
            CONFIGS[key] = config                       #F

    return CONFIGS.get(key)

REDIS_CONNECTIONS = {}
config_connection = None

def redis_connection(component, wait=1):                        #A
    key = 'config:redis:' + component                           #B
    def wrapper(function):                                      #C
        @functools.wraps(function)                              #D
        def call(*args, **kwargs):                              #E
            old_config = CONFIGS.get(key, object())             #F
            _config = get_config(                               #G
                config_connection, 'redis', component, wait)    #G

            config = {}
            for k, v in _config.iteritems():                    #L
                config[k.encode('utf-8')] = v                   #L

            if config != old_config:                            #H
                REDIS_CONNECTIONS[key] = redis.Redis(**config)  #H

            return function(                                    #I
                REDIS_CONNECTIONS.get(key), *args, **kwargs)    #I
        return call                                             #J
    return wrapper                                              #K

def index_document(conn, docid, words, scores):
    pipeline = conn.pipeline(True)
    for word in words:                                                  #I
        pipeline.sadd('idx:' + word, docid)                             #I
    pipeline.hmset('kb:doc:%s'%docid, scores)
    return len(pipeline.execute())                                      #J

def parse_and_search(conn, query, ttl):
    id = str(uuid.uuid4())
    conn.sinterstore('idx:' + id,
        ['idx:'+key for key in query])
    conn.expire('idx:' + id, ttl)
    return id

def search_and_sort(conn, query, id=None, ttl=300, sort="-updated", #A
                    start=0, num=20):                               #A
    desc = sort.startswith('-')                                     #B
    sort = sort.lstrip('-')                                         #B
    by = "kb:doc:*->" + sort                                        #B
    alpha = sort not in ('updated', 'id', 'created')                #I

    if id and not conn.expire(id, ttl):     #C
        id = None                           #C

    if not id:                                      #D
        id = parse_and_search(conn, query, ttl=ttl) #D

    pipeline = conn.pipeline(True)
    pipeline.scard('idx:' + id)                                     #E
    pipeline.sort('idx:' + id, by=by, alpha=alpha,                  #F
        desc=desc, start=start, num=num)                            #F
    results = pipeline.execute()

    return results[0], results[1], id                               #G

def zintersect(conn, keys, ttl):
    id = str(uuid.uuid4())
    conn.zinterstore('idx:' + id,
        dict(('idx:'+k, v) for k,v in keys.iteritems()))
    conn.expire('idx:' + id, ttl)
    return id

def search_and_zsort(conn, query, id=None, ttl=300, update=1, vote=0,   #A
                    start=0, num=20, desc=True):                        #A

    if id and not conn.expire(id, ttl):     #B
        id = None                           #B

    if not id:                                      #C
        id = parse_and_search(conn, query, ttl=ttl) #C

        scored_search = {                           #D
            id: 0,                                  #D
            'sort:update': update,                  #D
            'sort:votes': vote                      #D
        }
        id = zintersect(conn, scored_search, ttl)   #E

    pipeline = conn.pipeline(True)
    pipeline.zcard('idx:' + id)                                     #F
    if desc:                                                        #G
        pipeline.zrevrange('idx:' + id, start, start + num - 1)     #G
    else:                                                           #G
        pipeline.zrange('idx:' + id, start, start + num - 1)        #G
    results = pipeline.execute()

    return results[0], results[1], id                               #H

def execute_later(conn, queue, name, args):
    t = threading.Thread(target=globals()[name], args=tuple(args))
    t.setDaemon(1)
    t.start()

HOME_TIMELINE_SIZE = 1000
POSTS_PER_PASS = 1000

def shard_key(base, key, total_elements, shard_size):   #A
    if isinstance(key, (int, long)) or key.isdigit():   #B
        shard_id = int(str(key), 10) // shard_size      #C
    else:
        shards = 2 * total_elements // shard_size       #D
        shard_id = binascii.crc32(key) % shards         #E
    return "%s:%s"%(base, shard_id)                     #F

def shard_sadd(conn, base, member, total_elements, shard_size):
    shard = shard_key(base,
        'x'+str(member), total_elements, shard_size)            #A
    return conn.sadd(shard, member)                             #B

SHARD_SIZE = 512
EXPECTED = defaultdict(lambda: 1000000)

# <start id="get-connection"/>
def get_redis_connection(component, wait=1):
    key = 'config:redis:' + component
    old_config = CONFIGS.get(key, object())             #A
    config = get_config(                                #B
        config_connection, 'redis', component, wait)    #B

    if config != old_config:                            #C
        REDIS_CONNECTIONS[key] = redis.Redis(**config)  #C

    return REDIS_CONNECTIONS.get(key)                   #D
# <end id="get-connection"/>
#A Fetch the old configuration, if any
#B Get the new configuration, if any
#C If the new and old configuration do not match, create a new connection
#D Return the desired connection object
#END

# <start id="get-sharded-connection"/>
def get_sharded_connection(component, key, shard_count, wait=1):
    shard = shard_key(component, 'x'+str(key), shard_count, 2)  #A
    return get_redis_connection(shard, wait)                    #B
# <end id="get-sharded-connection"/>
#A Calculate the shard id of the form: &lt;component&gt;:&lt;shard&gt;
#B Return the connection
#END


# <start id="no-decorator-example"/>
def log_recent(conn, app, message):
    'the old log_recent() code'

log_recent = redis_connection('logs')(log_recent)   #A
# <end id="no-decorator-example"/>
#A This performs the equivalent decoration, but requires repeating the 'log_recent' function name 3 times
#END

# <start id="shard-aware-decorator"/>
def sharded_connection(component, shard_count, wait=1):         #A
    def wrapper(function):                                      #B
        @functools.wraps(function)                              #C
        def call(key, *args, **kwargs):                         #D
            conn = get_sharded_connection(                      #E
                component, key, shard_count, wait)              #E
            return function(conn, key, *args, **kwargs)         #F
        return call                                             #G
    return wrapper                                              #H
# <end id="shard-aware-decorator"/>
#A Our decorator is going to take a component name, as well as the number of shards desired
#B We are then going to create a wrapper that will actually decorate the function
#C Copy some useful metadata from the original function to the configuration handler
#D Create the function that will calculate a shard id for keys, and set up the connection manager
#E Fetch the sharded connection
#F Actually call the function, passing the connection and existing arguments
#G Return the fully wrapped function
#H Return a function that can wrap functions that need a sharded connection
#END

# <start id="sharded-count-unique"/>
@sharded_connection('unique', 16)                       #A
def count_visit(conn, session_id):
    today = date.today()
    key = 'unique:%s'%today.isoformat()
    conn2, expected = get_expected(key, today)          #B

    id = int(session_id.replace('-', '')[:15], 16)
    if shard_sadd(conn, key, id, expected, SHARD_SIZE):
        conn2.incr(key)                                 #C

@redis_connection('unique')                             #D
def get_expected(conn, key, today):
    'all of the same function body as before, except the last line'
    return conn, EXPECTED[key]                          #E
# <end id="sharded-count-unique"/>
#A We are going to shard this to 16 different machines, which will automatically shard to multiple keys on each machine
#B Our changed call to get_expected()
#C Use the returned non-sharded connection to increment our unique counts
#D Use a non-sharded connection to get_expected()
#E Also return the non-sharded connection so that count_visit() can increment our unique count as necessary
#END

# <start id="search-with-values"/>
def search_get_values(conn, query, id=None, ttl=300, sort="-updated", #A
                      start=0, num=20):                               #A
    count, docids, id = search_and_sort(                            #B
        conn, query, id, ttl, sort, 0, start+num)                   #B

    key = "kb:doc:%s"
    sort = sort.lstrip('-')

    pipe = conn.pipeline(False)
    for docid in docids:                                            #C
        pipe.hget(key%docid, sort)                                  #C
    sort_column = pipe.execute()                                    #C

    data_pairs = zip(docids, sort_column)                           #D
    return count, data_pairs, id                                    #E
# <end id="search-with-values"/>
#A We need to take all of the same parameters to pass on to search_and_sort()
#B First get the results of a search and sort
#C Fetch the data that the results were sorted by
#D Pair up the document ids with the data that it was sorted by
#E Return the count, data, and cache id of the results
#END

# <start id="search-on-shards"/>
def get_shard_results(component, shards, query, ids=None, ttl=300,  #A
                  sort="-updated", start=0, num=20, wait=1):        #A

    count = 0       #B
    data = []       #B
    ids = ids or shards * [None]       #C
    for shard in xrange(shards):
        conn = get_redis_connection('%s:%s'%(component, shard), wait)#D
        c, d, i = search_get_values(                        #E
            conn, query, ids[shard], ttl, sort, start, num) #E

        count += c          #F
        data.extend(d)      #F
        ids[shard] = i      #F

    return count, data, ids     #G
# <end id="search-on-shards"/>
#A In order to know what servers to connect to, we are going to assume that all of our shard information is kept in the standard configuration location
#B Prepare structures to hold all of our fetched data
#C Use cached results if we have any, otherwise start over
#D Get or create a connection to the desired shard
#E Fetch the search results and their sort values
#F Combine this shard's results with all of the other results
#G Return the raw results from all of the shards
#END

def get_values_thread(component, shard, wait, rqueue, *args, **kwargs):
    conn = get_redis_connection('%s:%s'%(component, shard), wait)
    count, results, id = search_get_values(conn, *args, **kwargs)
    rqueue.put((shard, count, results, id))

def get_shard_results_thread(component, shards, query, ids=None, ttl=300,
                  sort="-updated", start=0, num=20, wait=1, timeout=.5):

    ids = ids or shards * [None]
    rqueue = Queue()

    for shard in xrange(shards):
        t = threading.Thread(target=get_values_thread, args=(
            component, shard, wait, rqueue, query, ids[shard],
            ttl, sort, start, num))
        t.setDaemon(1)
        t.start()

    received = 0
    count = 0
    data = []
    deadline = time.time() + timeout
    while received < shards and time.time() < deadline:
        try:
            sh, c, r, i = rqueue.get(timeout=max(deadline-time.time(), .001))
        except Empty:
            break
        else:
            count += c
            data.extend(r)
            ids[sh] = i

    return count, data, ids

# <start id="merge-sharded-results"/>
def to_numeric_key(data):
    try:
        return Decimal(data[1] or '0')      #A
    except:
        return Decimal('0')                 #A

def to_string_key(data):
    return data[1] or ''                    #B

def search_shards(component, shards, query, ids=None, ttl=300,      #C
                  sort="-updated", start=0, num=20, wait=1):        #C

    count, data, ids = get_shard_results(                           #D
        component, shards, query, ids, ttl, sort, start, num, wait) #D

    reversed = sort.startswith('-')                     #E
    sort = sort.strip('-')                              #E
    key = to_numeric_key                                #E
    if sort not in ('updated', 'id', 'created'):        #E
        key = to_string_key                             #E

    data.sort(key=key, reverse=reversed)               #F

    results = []
    for docid, score in data[start:start+num]:          #G
        results.append(docid)                           #G

    return count, results, ids                          #H
# <end id="merge-sharded-results"/>
#A We are going to use the 'Decimal' numeric type here because it transparently handles both integers and floats reasonably, defaulting to 0 if the value wasn't numeric or was missing
#B Always return a string, even if there was no value stored
#C We need to take all of the sharding and searching arguments, mostly to pass on to lower-level functions, but we use the sort and search offsets
#D Fetch the results of the unsorted sharded search
#E Prepare all of our sorting options
#F Actually sort our results based on the sort parameter
#G Fetch just the page of results that we want
#H Return the results, including the sequence of cache ids for each shard
#END

# <start id="zset-search-with-values"/>
def search_get_zset_values(conn, query, id=None, ttl=300, update=1, #A
                    vote=0, start=0, num=20, desc=True):            #A

    count, r, id = search_and_zsort(                                #B
        conn, query, id, ttl, update, vote, 0, 1, desc)             #B

    if desc:                                                        #C
        data = conn.zrevrange(id, 0, start + num - 1, withscores=True)#C
    else:                                                           #C
        data = conn.zrange(id, 0, start + num - 1, withscores=True) #C

    return count, data, id                                          #D
# <end id="zset-search-with-values"/>
#A We need to accept all of the standard arguments for search_and_zsort()
#B Call the underlying search_and_zsort() function to get the cached result id and total number of results
#C Fetch all of the results we need, including their scores
#D Return the count, results with scores, and the cache id
#END

# <start id="search-shards-zset"/>
def search_shards_zset(component, shards, query, ids=None, ttl=300,   #A
                update=1, vote=0, start=0, num=20, desc=True, wait=1):#A

    count = 0                       #B
    data = []                       #B
    ids = ids or shards * [None]    #C
    for shard in xrange(shards):
        conn = get_redis_connection('%s:%s'%(component, shard), wait) #D
        c, d, i = search_get_zset_values(conn, query, ids[shard],     #E
            ttl, update, vote, start, num, desc)                      #E

        count += c      #F
        data.extend(d)  #F
        ids[shard] = i  #F

    def key(result):        #G
        return result[1]    #G

    data.sort(key=key, reversed=desc)   #H
    results = []
    for docid, score in data[start:start+num]:  #I
        results.append(docid)                   #I

    return count, results, ids                  #J
# <end id="search-shards-zset"/>
#A We need to take all of the sharding arguments along with all of the search arguments
#B Prepare structures for data to be returned
#C Use cached results if any, otherwise start from scratch
#D Fetch or create a connection to each shard
#E Perform the search on a shard and fetch the scores
#F Merge the results together
#G Prepare the simple sort helper to only return information about the score
#H Sort all of the results together
#I Extract the document ids from the results, removing the scores
#J Return the search results to the caller
#END

# <start id="sharded-api-base"/>
class KeyShardedConnection(object):
    def __init__(self, component, shards):          #A
        self.component = component                  #A
        self.shards = shards                        #A
    def __getitem__(self, key):                     #B
        return get_sharded_connection(              #C
            self.component, key, self.shards)       #C
# <end id="sharded-api-base"/>
#A The object is initialized with the component name and number of shards
#B When an item is fetched from the object, this method is called with the item that was requested
#C Use the passed key along with the previously-known component and shards to fetch the sharded connection
#END

# <start id="sharded-api-example"/>
sharded_timelines = KeyShardedConnection('timelines', 8)    #A

def follow_user(conn, uid, other_uid):
    fkey1 = 'following:%s'%uid
    fkey2 = 'followers:%s'%other_uid

    if conn.zscore(fkey1, other_uid):
        print "already followed", uid, other_uid
        return None

    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zadd(fkey1, other_uid, now)
    pipeline.zadd(fkey2, uid, now)
    pipeline.zcard(fkey1)
    pipeline.zcard(fkey2)
    following, followers = pipeline.execute()[-2:]
    pipeline.hset('user:%s'%uid, 'following', following)
    pipeline.hset('user:%s'%other_uid, 'followers', followers)
    pipeline.execute()

    pkey = 'profile:%s'%other_uid
    status_and_score = sharded_timelines[pkey].zrevrange(   #B
        pkey, 0, HOME_TIMELINE_SIZE-1, withscores=True)     #B

    if status_and_score:
        hkey = 'home:%s'%uid
        pipe = sharded_timelines[hkey].pipeline(True)       #C
        pipe.zadd(hkey, **dict(status_and_score))           #D
        pipe.zremrangebyrank(hkey, 0, -HOME_TIMELINE_SIZE-1)#D
        pipe.execute()                                      #E

    return True
# <end id="sharded-api-example"/>
#A Create a connection that knows about the sharding information for a given component with a number of shards
#B Fetch the recent status messages from the profile timeline of the now-followed user
#C Get a connection based on the shard key provided, and fetch a pipeline from that
#D Add the statuses to the home timeline ZSET on the shard, then trim it
#E Execute the transaction
#END


# <start id="key-data-sharded-api"/>
class KeyDataShardedConnection(object):
    def __init__(self, component, shards):          #A
        self.component = component                  #A
        self.shards = shards                        #A
    def __getitem__(self, ids):                     #B
        id1, id2 = map(int, ids)                    #C
        if id2 < id1:                               #D
            id1, id2 = id2, id1                     #D
        key = "%s:%s"%(id1, id2)                    #E
        return get_sharded_connection(              #F
            self.component, key, self.shards)       #F
# <end id="key-data-sharded-api"/>
#A The object is initialized with the component name and number of shards
#B When the pair of ids are passed as part of the dictionary lookup, this method is called
#C Unpack the pair of ids, and ensure that they are integers
#D If the second is less than the first, swap them so that the first id is less than or equal to the second
#E Construct a key based on the two ids
#F Use the computed key along with the previously-known component and shards to fetch the sharded connection
#END

_follow_user = follow_user
# <start id="sharded-api-example2"/>
sharded_timelines = KeyShardedConnection('timelines', 8)        #A
sharded_followers = KeyDataShardedConnection('followers', 16)   #A

def follow_user(conn, uid, other_uid):
    fkey1 = 'following:%s'%uid
    fkey2 = 'followers:%s'%other_uid

    sconn = sharded_followers[uid, other_uid]           #B
    if sconn.zscore(fkey1, other_uid):                  #C
        return None

    now = time.time()
    spipe = sconn.pipeline(True)
    spipe.zadd(fkey1, other_uid, now)                   #D
    spipe.zadd(fkey2, uid, now)                         #D
    following, followers = spipe.execute()

    pipeline = conn.pipeline(True)
    pipeline.hincrby('user:%s'%uid, 'following', int(following))      #E
    pipeline.hincrby('user:%s'%other_uid, 'followers', int(followers))#E
    pipeline.execute()

    pkey = 'profile:%s'%other_uid
    status_and_score = sharded_timelines[pkey].zrevrange(
        pkey, 0, HOME_TIMELINE_SIZE-1, withscores=True)

    if status_and_score:
        hkey = 'home:%s'%uid
        pipe = sharded_timelines[hkey].pipeline(True)
        pipe.zadd(hkey, **dict(status_and_score))
        pipe.zremrangebyrank(hkey, 0, -HOME_TIMELINE_SIZE-1)
        pipe.execute()

    return True
# <end id="sharded-api-example2"/>
#A Create a connection that knows about the sharding information for a given component with a number of shards
#B Fetch the connection object for the uid,other_uid pair
#C Check to see if other_uid is already followed
#D Add the follower/following information to the ZSETs
#E Update the follower and following information for both users
#END

# <start id="sharded-zrangebyscore"/>
def sharded_zrangebyscore(component, shards, key, min, max, num):   #A
    data = []
    for shard in xrange(shards):
        conn = get_redis_connection("%s:%s"%(component, shard))     #B
        data.extend(conn.zrangebyscore(                             #C
            key, min, max, start=0, num=num, withscores=True))      #C

    def key(pair):                      #D
        return pair[1], pair[0]         #D
    data.sort(key=key)                  #D

    return data[:num]                   #E
# <end id="sharded-zrangebyscore"/>
#A We need to take arguments for the component and number of shards, and we are going to limit the arguments to be passed on to only those that will ensure correct behavior in sharded situations
#B Fetch the sharded connection for the current shard
#C Get the data from Redis for this shard
#D Sort the data based on score then by member
#E Return only the number of items requested
#END

# <start id="sharded-syndicate-posts"/>
def syndicate_status(uid, post, start=0, on_lists=False):
    root = 'followers'
    key = 'followers:%s'%uid
    base = 'home:%s'
    if on_lists:
        root = 'list:out'
        key = 'list:out:%s'%uid
        base = 'list:statuses:%s'

    followers = sharded_zrangebyscore(root,                         #A
        sharded_followers.shards, key, start, 'inf', POSTS_PER_PASS)#A

    to_send = defaultdict(list)                             #B
    for follower, start in followers:
        timeline = base % follower                          #C
        shard = shard_key('timelines',                      #D
            timeline, sharded_timelines.shards, 2)          #D
        to_send[shard].append(timeline)                     #E

    for timelines in to_send.itervalues():
        pipe = sharded_timelines[timelines[0]].pipeline(False)  #F
        for timeline in timelines:
            pipe.zadd(timeline, **post)                 #G
            pipe.zremrangebyrank(                       #G
                timeline, 0, -HOME_TIMELINE_SIZE-1)     #G
        pipe.execute()

    conn = redis.Redis()
    if len(followers) >= POSTS_PER_PASS:
        execute_later(conn, 'default', 'syndicate_status',
            [uid, post, start, on_lists])

    elif not on_lists:
        execute_later(conn, 'default', 'syndicate_status',
            [uid, post, 0, True])
# <end id="sharded-syndicate-posts"/>
#A Fetch the next group of followers using the sharded ZRANGEBYSCORE call
#B Prepare a structure that will group profile information on a per-shard basis
#C Calculate the key for the timeline
#D Find the shard where this timeline would go
#E Add the timeline key to the rest of the timelines on the same shard
#F Get a connection to the server for the group of timelines, and create a pipeline
#G Add the post to the timeline, and remove any posts that are too old
#END

def _fake_shards_for(conn, component, count, actual):
    assert actual <= 4
    for i in xrange(count):
        m = i % actual
        conn.set('config:redis:%s:%i'%(component, i), json.dumps({'db':14 - m}))

class TestCh10(unittest.TestCase):
    def _flush(self):
        self.conn.flushdb()
        redis.Redis(db=14).flushdb()
        redis.Redis(db=13).flushdb()
        redis.Redis(db=12).flushdb()
        redis.Redis(db=11).flushdb()
        
    def setUp(self):
        self.conn = redis.Redis(db=15)
        self._flush()
        global config_connection
        config_connection = self.conn
        self.conn.set('config:redis:test', json.dumps({'db':15}))

    def tearDown(self):
        self._flush()

    def test_get_sharded_connections(self):
        _fake_shards_for(self.conn, 'shard', 2, 2)

        for i in xrange(10):
            get_sharded_connection('shard', i, 2).sadd('foo', i)

        s0 = redis.Redis(db=14).scard('foo')
        s1 = redis.Redis(db=13).scard('foo')
        self.assertTrue(s0 < 10)
        self.assertTrue(s1 < 10)
        self.assertEquals(s0 + s1, 10)

    def test_count_visit(self):
        shards = {'db':13}, {'db':14}
        self.conn.set('config:redis:unique', json.dumps({'db':15}))
        for i in xrange(16):
            self.conn.set('config:redis:unique:%s'%i, json.dumps(shards[i&1]))
    
        for i in xrange(100):
            count_visit(str(uuid.uuid4()))
        base = 'unique:%s'%date.today().isoformat()
        total = 0
        for c in shards:
            conn = redis.Redis(**c)
            keys = conn.keys(base + ':*')
            for k in keys:
                cnt = conn.scard(k)
                total += cnt
                self.assertTrue(cnt < k)
        self.assertEquals(total, 100)
        self.assertEquals(self.conn.get(base), '100')

    def test_sharded_search(self):
        _fake_shards_for(self.conn, 'search', 2, 2)
        
        docs = 'hello world how are you doing'.split(), 'this world is doing fine'.split()
        for i in xrange(50):
            c = get_sharded_connection('search', i, 2)
            index_document(c, i, docs[i&1], {'updated':time.time() + i, 'id':i, 'created':time.time() + i})
            r = search_and_sort(c, docs[i&1], sort='-id')
            self.assertEquals(r[1][0], str(i))

        total = 0
        for shard in (0,1):
            count = search_get_values(get_redis_connection('search:%s'%shard),['this', 'world'], num=50)[0]
            total += count
            self.assertTrue(count < 50)
            self.assertTrue(count > 0)
        
        self.assertEquals(total, 25)
        
        count, r, id = get_shard_results('search', 2, ['world', 'doing'], num=50)
        self.assertEquals(count, 50)
        self.assertEquals(count, len(r))
        
        self.assertEquals(get_shard_results('search', 2, ['this', 'doing'], num=50)[0], 25)

        count, r, id = get_shard_results_thread('search', 2, ['this', 'doing'], num=50)
        self.assertEquals(count, 25)
        self.assertEquals(count, len(r))
        r.sort(key=lambda x:x[1], reverse=True)
        r = list(zip(*r)[0])
        
        count, r2, id = search_shards('search', 2, ['this', 'doing'])
        self.assertEquals(count, 25)
        self.assertEquals(len(r2), 20)
        self.assertEquals(r2, r[:20])
        
    def test_sharded_follow_user(self):
        _fake_shards_for(self.conn, 'timelines', 8, 4)

        sharded_timelines['profile:1'].zadd('profile:1', 1, time.time())
        for u2 in xrange(2, 11):
            sharded_timelines['profile:%i'%u2].zadd('profile:%i'%u2, u2, time.time() + u2)
            _follow_user(self.conn, 1, u2)
            _follow_user(self.conn, u2, 1)
        
        self.assertEquals(self.conn.zcard('followers:1'), 9)
        self.assertEquals(self.conn.zcard('following:1'), 9)
        self.assertEquals(sharded_timelines['home:1'].zcard('home:1'), 9)
        
        for db in xrange(14, 10, -1):
            self.assertTrue(len(redis.Redis(db=db).keys()) > 0)
        for u2 in xrange(2, 11):
            self.assertEquals(self.conn.zcard('followers:%i'%u2), 1)
            self.assertEquals(self.conn.zcard('following:%i'%u2), 1)
            self.assertEquals(sharded_timelines['home:%i'%u2].zcard('home:%i'%u2), 1)

    def test_sharded_follow_user_and_syndicate_status(self):
        _fake_shards_for(self.conn, 'timelines', 8, 4)
        _fake_shards_for(self.conn, 'followers', 4, 4)
        sharded_followers.shards = 4
    
        sharded_timelines['profile:1'].zadd('profile:1', 1, time.time())
        for u2 in xrange(2, 11):
            sharded_timelines['profile:%i'%u2].zadd('profile:%i'%u2, u2, time.time() + u2)
            follow_user(self.conn, 1, u2)
            follow_user(self.conn, u2, 1)
        
        allkeys = defaultdict(int)
        for db in xrange(14, 10, -1):
            c = redis.Redis(db=db)
            for k in c.keys():
                allkeys[k] += c.zcard(k)

        for k, v in allkeys.iteritems():
            part, _, owner = k.partition(':')
            if part in ('following', 'followers', 'home'):
                self.assertEquals(v, 9 if owner == '1' else 1)
            elif part == 'profile':
                self.assertEquals(v, 1)

        self.assertEquals(len(sharded_zrangebyscore('followers', 4, 'followers:1', '0', 'inf', 100)), 9)
        syndicate_status(1, {'11':time.time()})
        self.assertEquals(len(sharded_zrangebyscore('timelines', 4, 'home:2', '0', 'inf', 100)), 2)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ch11_listing_source

import bisect
import math
import threading
import time
import unittest
import uuid

import redis

# <start id="script-load"/>
def script_load(script):
    sha = [None]                #A
    def call(conn, keys=[], args=[], force_eval=False):   #B
        if not force_eval:
            if not sha[0]:   #C
                sha[0] = conn.execute_command(              #D
                    "SCRIPT", "LOAD", script, parse="LOAD") #D
    
            try:
                return conn.execute_command(                    #E
                    "EVALSHA", sha[0], len(keys), *(keys+args)) #E
        
            except redis.exceptions.ResponseError as msg:
                if not msg.args[0].startswith("NOSCRIPT"):      #F
                    raise                                       #F
        
        return conn.execute_command(                    #G
            "EVAL", script, len(keys), *(keys+args))    #G
    
    return call             #H
# <end id="script-load"/>
#A Store the cached SHA1 hash of the result of SCRIPT LOAD in a list so we can change it later from within the call() function
#B When calling the "loaded script", you must provide the connection, the set of keys that the script will manipulate, and any other arguments to the function
#C We will only try loading the script if we don't already have a cached SHA1 hash
#D Load the script if we don't already have the SHA1 hash cached
#E Execute the command from the cached SHA1
#F If the error was unrelated to a missing script, re-raise the exception
#G If we received a script-related error, or if we need to force-execute the script, directly execute the script, which will automatically cache the script on the server (with the same SHA1 that we've already cached) when done
#H Return the function that automatically loads and executes scripts when called
#END

'''
# <start id="show-script-load"/>
>>> ret_1 = script_load("return 1")     #A
>>> ret_1(conn)                         #B
1L                                      #C
# <end id="show-script-load"/>
#A Most uses will load the script and store a reference to the returned function
#B You can then call the function by passing the connection object and any desired arguments
#C Results will be returned and converted into appropriate Python types, when possible
#END
'''


# <start id="ch08-post-status"/>
def create_status(conn, uid, message, **data):
    pipeline = conn.pipeline(True)
    pipeline.hget('user:%s' % uid, 'login') #A
    pipeline.incr('status:id:')             #B
    login, id = pipeline.execute()

    if not login:                           #C
        return None                         #C

    data.update({
        'message': message,                 #D
        'posted': time.time(),              #D
        'id': id,                           #D
        'uid': uid,                         #D
        'login': login,                     #D
    })
    pipeline.hmset('status:%s' % id, data)  #D
    pipeline.hincrby('user:%s' % uid, 'posts')#E
    pipeline.execute()
    return id                               #F
# <end id="ch08-post-status"/>
#A Get the user's login name from their user id
#B Create a new id for the status message
#C Verify that we have a proper user account before posting
#D Prepare and set the data for the status message
#E Record the fact that a status message has been posted
#F Return the id of the newly created status message
#END

_create_status = create_status
# <start id="post-status-lua"/>
def create_status(conn, uid, message, **data):          #H
    args = [                                            #I
        'message', message,                             #I
        'posted', time.time(),                          #I
        'uid', uid,                                     #I
    ]
    for key, value in data.iteritems():                 #I
        args.append(key)                                #I
        args.append(value)                              #I

    return create_status_lua(                           #J
        conn, ['user:%s' % uid, 'status:id:'], args)    #J

create_status_lua = script_load('''
local login = redis.call('hget', KEYS[1], 'login')      --A
if not login then                                       --B
    return false                                        --B
end
local id = redis.call('incr', KEYS[2])                  --C
local key = string.format('status:%s', id)              --D

redis.call('hmset', key,                                --E
    'login', login,                                     --E
    'id', id,                                           --E
    unpack(ARGV))                                       --E
redis.call('hincrby', KEYS[1], 'posts', 1)              --F

return id                                               --G
''')
# <end id="post-status-lua"/>
#A Fetch the user's login name from their id, remember that tables in Lua are 1-indexed, not 0-indexed like Python and most other languages
#B If there is no login, return that no login was found
#C Get a new id for the status message
#D Prepare the destination key for the status message
#E Set the data for the status message
#F Increment the post count of the user
#G Return the id of the status message
#H Take all of the arguments as before
#I Prepare the arguments/attributes to be set on the status message
#J Call the script
#END

# <start id="old-lock"/>
def acquire_lock_with_timeout(
    conn, lockname, acquire_timeout=10, lock_timeout=10):
    identifier = str(uuid.uuid4())                      #A
    lockname = 'lock:' + lockname
    lock_timeout = int(math.ceil(lock_timeout))         #D
    
    end = time.time() + acquire_timeout
    while time.time() < end:
        if conn.setnx(lockname, identifier):            #B
            conn.expire(lockname, lock_timeout)         #B
            return identifier
        elif not conn.ttl(lockname):                    #C
            conn.expire(lockname, lock_timeout)         #C
    
        time.sleep(.001)
    
    return False
# <end id="old-lock"/>
#A A 128-bit random identifier
#B Get the lock and set the expiration
#C Check and update the expiration time as necessary
#D Only pass integers to our EXPIRE calls
#END

_acquire_lock_with_timeout = acquire_lock_with_timeout

# <start id="lock-in-lua"/>
def acquire_lock_with_timeout(
    conn, lockname, acquire_timeout=10, lock_timeout=10):
    identifier = str(uuid.uuid4())                      
    lockname = 'lock:' + lockname
    lock_timeout = int(math.ceil(lock_timeout))      
    
    acquired = False
    end = time.time() + acquire_timeout
    while time.time() < end and not acquired:
        acquired = acquire_lock_with_timeout_lua(                   #A
            conn, [lockname], [lock_timeout, identifier]) == 'OK'   #A
    
        time.sleep(.001 * (not acquired))
    
    return acquired and identifier

acquire_lock_with_timeout_lua = script_load('''
if redis.call('exists', KEYS[1]) == 0 then              --B
    return redis.call('setex', KEYS[1], unpack(ARGV))   --C
end
''')
# <end id="lock-in-lua"/>
#A Actually acquire the lock, checking to verify that the Lua call completed successfully
#B If the lock doesn't already exist, again remembering that tables use 1-based indexing
#C Set the key with the provided expiration and identifier
#END

def release_lock(conn, lockname, identifier):
    pipe = conn.pipeline(True)
    lockname = 'lock:' + lockname
    
    while True:
        try:
            pipe.watch(lockname)                  #A
            if pipe.get(lockname) == identifier:  #A
                pipe.multi()                      #B
                pipe.delete(lockname)             #B
                pipe.execute()                    #B
                return True                       #B
    
            pipe.unwatch()
            break
    
        except redis.exceptions.WatchError:       #C
            pass                                  #C
    
    return False                                  #D

_release_lock = release_lock

# <start id="release-lock-in-lua"/>
def release_lock(conn, lockname, identifier):
    lockname = 'lock:' + lockname
    return release_lock_lua(conn, [lockname], [identifier]) #A

release_lock_lua = script_load('''
if redis.call('get', KEYS[1]) == ARGV[1] then               --B
    return redis.call('del', KEYS[1]) or true               --C
end
''')
# <end id="release-lock-in-lua"/>
#A Call the Lua function that releases the lock
#B Make sure that the lock matches
#C Delete the lock and ensure that we return true
#END

# <start id="old-acquire-semaphore"/>
def acquire_semaphore(conn, semname, limit, timeout=10):
    identifier = str(uuid.uuid4())                             #A
    now = time.time()

    pipeline = conn.pipeline(True)
    pipeline.zremrangebyscore(semname, '-inf', now - timeout)  #B
    pipeline.zadd(semname, identifier, now)                    #C
    pipeline.zrank(semname, identifier)                        #D
    if pipeline.execute()[-1] < limit:                         #D
        return identifier

    conn.zrem(semname, identifier)                             #E
    return None
# <end id="old-acquire-semaphore"/>
#A A 128-bit random identifier
#B Time out old semaphore holders
#C Try to acquire the semaphore
#D Check to see if we have it
#E We failed to get the semaphore, discard our identifier
#END

_acquire_semaphore = acquire_semaphore

# <start id="acquire-semaphore-lua"/>
def acquire_semaphore(conn, semname, limit, timeout=10):
    now = time.time()                                           #A
    return acquire_semaphore_lua(conn, [semname],               #B
        [now-timeout, limit, now, str(uuid.uuid4())])           #B

acquire_semaphore_lua = script_load('''
redis.call('zremrangebyscore', KEYS[1], '-inf', ARGV[1])        --C

if redis.call('zcard', KEYS[1]) < tonumber(ARGV[2]) then        --D
    redis.call('zadd', KEYS[1], ARGV[3], ARGV[4])               --E
    return ARGV[4]
end
''')
# <end id="acquire-semaphore-lua"/>
#A Get the current timestamp for handling timeouts
#B Pass all of the required arguments into the Lua function to actually acquire the semaphore
#C Clean out all of the expired semaphores
#D If we have not yet hit our semaphore limit, then acquire the semaphore
#E Add the timestamp the timeout ZSET
#END

def release_semaphore(conn, semname, identifier):
    return conn.zrem(semname, identifier)

# <start id="refresh-semaphore-lua"/>
def refresh_semaphore(conn, semname, identifier):
    return refresh_semaphore_lua(conn, [semname],
        [identifier, time.time()]) != None          #A

refresh_semaphore_lua = script_load('''
if redis.call('zscore', KEYS[1], ARGV[1]) then                   --B
    return redis.call('zadd', KEYS[1], ARGV[2], ARGV[1]) or true --B
end
''')
# <end id="refresh-semaphore-lua"/>
#A If Lua had returned "nil" from the call (the semaphore wasn't refreshed), Python will return None instead
#B If the semaphore is still valid, then we update the semaphore's timestamp
#END

valid_characters = '`abcdefghijklmnopqrstuvwxyz{'             #A

def find_prefix_range(prefix):
    posn = bisect.bisect_left(valid_characters, prefix[-1:])  #B
    suffix = valid_characters[(posn or 1) - 1]                #C
    return prefix[:-1] + suffix + '{', prefix + '{'           #D

# <start id="old-autocomplete-code"/>
def autocomplete_on_prefix(conn, guild, prefix):
    start, end = find_prefix_range(prefix)                 #A
    identifier = str(uuid.uuid4())                         #A
    start += identifier                                    #A
    end += identifier                                      #A
    zset_name = 'members:' + guild

    conn.zadd(zset_name, start, 0, end, 0)                 #B
    pipeline = conn.pipeline(True)
    while 1:
        try:
            pipeline.watch(zset_name)
            sindex = pipeline.zrank(zset_name, start)      #C
            eindex = pipeline.zrank(zset_name, end)        #C
            erange = min(sindex + 9, eindex - 2)           #C
            pipeline.multi()
            pipeline.zrem(zset_name, start, end)           #D
            pipeline.zrange(zset_name, sindex, erange)     #D
            items = pipeline.execute()[-1]                 #D
            break
        except redis.exceptions.WatchError:                #E
            continue                                       #E

    return [item for item in items if '{' not in item]     #F
# <end id="old-autocomplete-code"/>
#A Find the start/end range for the prefix
#B Add the start/end range items to the ZSET
#C Find the ranks of our end points
#D Get the values inside our range, and clean up
#E Retry if someone modified our autocomplete zset
#F Remove start/end entries if an autocomplete was in progress
#END

_autocomplete_on_prefix = autocomplete_on_prefix
# <start id="autocomplete-on-prefix-lua"/>
def autocomplete_on_prefix(conn, guild, prefix):
    start, end = find_prefix_range(prefix)                  #A
    identifier = str(uuid.uuid4())                          #A
    
    items = autocomplete_on_prefix_lua(conn,                #B
        ['members:' + guild],                               #B
        [start+identifier, end+identifier])                 #B
    
    return [item for item in items if '{' not in item]      #C

autocomplete_on_prefix_lua = script_load('''
redis.call('zadd', KEYS[1], 0, ARGV[1], 0, ARGV[2])             --D
local sindex = redis.call('zrank', KEYS[1], ARGV[1])            --E
local eindex = redis.call('zrank', KEYS[1], ARGV[2])            --E
eindex = math.min(sindex + 9, eindex - 2)                       --F

redis.call('zrem', KEYS[1], unpack(ARGV))                       --G
return redis.call('zrange', KEYS[1], sindex, eindex)            --H
''')
# <end id="autocomplete-on-prefix-lua"/>
#A Get the range and identifier
#B Fetch the data from Redis with the Lua script
#C Filter out any items that we don't want
#D Add our place-holder endpoints to the ZSET
#E Find the endpoint positions in the ZSET
#F Calculate the proper range of values to fetch
#G Remove the place-holder endpoints
#H Fetch and return our results
#END

# <start id="ch06-purchase-item-with-lock"/>
def purchase_item_with_lock(conn, buyerid, itemid, sellerid):
    buyer = "users:%s" % buyerid
    seller = "users:%s" % sellerid
    item = "%s.%s" % (itemid, sellerid)
    inventory = "inventory:%s" % buyerid
    end = time.time() + 30

    locked = acquire_lock(conn, 'market:')             #A
    if not locked:
        return False

    pipe = conn.pipeline(True)
    try:
        while time.time() < end:
            try:
                pipe.watch(buyer)
                pipe.zscore("market:", item)           #B
                pipe.hget(buyer, 'funds')              #B
                price, funds = pipe.execute()          #B
                if price is None or price > funds:     #B
                    pipe.unwatch()                     #B
                    return None                        #B

                pipe.hincrby(seller, int(price))       #C
                pipe.hincrby(buyerid, int(-price))     #C
                pipe.sadd(inventory, itemid)           #C
                pipe.zrem("market:", item)             #C
                pipe.execute()                         #C
                return True
            except redis.exceptions.WatchError:
                pass
    finally:
        release_lock(conn, 'market:', locked)          #D
# <end id="ch06-purchase-item-with-lock"/>
#A Get the lock
#B Check for a sold item or insufficient funds
#C Transfer funds from the buyer to the seller, and transfer the item to the buyer
#D Release the lock
#END

# <start id="purchase-item-lua"/>
def purchase_item(conn, buyerid, itemid, sellerid):
    buyer = "users:%s" % buyerid                        #A
    seller = "users:%s" % sellerid                      #A
    item = "%s.%s"%(itemid, sellerid)                   #A
    inventory = "inventory:%s" % buyerid                #A

    return purchase_item_lua(conn,
        ['market:', buyer, seller, inventory], [item, itemid])

purchase_item_lua = script_load('''
local price = tonumber(redis.call('zscore', KEYS[1], ARGV[1]))  --B
local funds = tonumber(redis.call('hget', KEYS[2], 'funds'))    --B

if price and funds and funds >= price then                      --C
    redis.call('hincrby', KEYS[3], 'funds', price)              --C
    redis.call('hincrby', KEYS[2], 'funds', -price)             --C
    redis.call('sadd', KEYS[4], ARGV[2])                        --C
    redis.call('zrem', KEYS[1], ARGV[1])                        --C
    return true                                                 --D
end
''')
# <end id="purchase-item-lua"/>
#A Prepare all of the keys and arguments for the Lua script
#B Get the item price and the buyer's available funds
#C If the item is still available and the buyer has enough money, transfer the item
#D Signify that the purchase completed successfully
#END

def list_item(conn, itemid, sellerid, price):
    inv = "inventory:%s" % sellerid
    item = "%s.%s" % (itemid, sellerid)
    return list_item_lua(conn, [inv, 'market:'], [itemid, item, price])

list_item_lua = script_load('''
if redis.call('sismember', KEYS[1], ARGV[1]) ~= 0 then
    redis.call('zadd', KEYS[2], ARGV[2], ARGV[3])
    redis.call('srem', KEYS[1], ARGV[1])
    return true
end
''')

# <start id="sharded-list-push"/>
def sharded_push_helper(conn, key, *items, **kwargs):
    items = list(items)                                 #A
    total = 0
    while items:                                        #B
        pushed = sharded_push_lua(conn,                 #C
            [key+':', key+':first', key+':last'],       #C
            [kwargs['cmd']] + items[:64])               #D
        total += pushed                                 #E
        del items[:pushed]                              #F
    return total                                        #G

def sharded_lpush(conn, key, *items):
    return sharded_push_helper(conn, key, *items, cmd='lpush')#H

def sharded_rpush(conn, key, *items):
    return sharded_push_helper(conn, key, *items, cmd='rpush')#H

sharded_push_lua = script_load('''
local max = tonumber(redis.call(                            --I
    'config', 'get', 'list-max-ziplist-entries')[2])        --I
if #ARGV < 2 or max < 2 then return 0 end                   --J

local skey = ARGV[1] == 'lpush' and KEYS[2] or KEYS[3]      --K
local shard = redis.call('get', skey) or '0'                --K

while 1 do
    local current = tonumber(redis.call('llen', KEYS[1]..shard))    --L
    local topush = math.min(#ARGV - 1, max - current - 1)           --M
    if topush > 0 then                                              --N
        redis.call(ARGV[1], KEYS[1]..shard, unpack(ARGV, 2, topush+1))--N
        return topush                                                 --N
    end
    shard = redis.call(ARGV[1] == 'lpush' and 'decr' or 'incr', skey) --O
end
''')
# <end id="sharded-list-push"/>
#A Convert our sequence of items into a list
#B While we still have items to push
#C Push items onto the sharded list by calling the Lua script
#D Note that we only push up to 64 items at a time here, you may want to adjust this up or down, depending on your maximum list ziplist size
#E Count the number of items that we pushed
#F Remove the items that we've already pushed
#G Return the total number of items pushed
#H Make a call to the sharded_push_helper function with a special argument that tells it to use lpush or rpush
#I Determine the maximum size of a LIST shard
#J If there is nothing to push, or if our max ziplist LIST entries is too small, return 0
#K Find out whether we are pushing onto the left or right end of the LIST, and get the correct end shard
#L Get the current length of that shard
#M Calculate how many of our current number of items we can push onto the current LIST shard without going over the limit, saving one entry for later blocking pop purposes
#N If we can push some items, then push as many items as we can
#O Otherwise generate a new shard, and try again
#END

def sharded_llen(conn, key):
    return sharded_llen_lua(conn, [key+':', key+':first', key+':last'])

sharded_llen_lua = script_load('''
local shardsize = tonumber(redis.call(
    'config', 'get', 'list-max-ziplist-entries')[2])

local first = tonumber(redis.call('get', KEYS[2]) or '0')
local last = tonumber(redis.call('get', KEYS[3]) or '0')

local total = 0
total = total + tonumber(redis.call('llen', KEYS[1]..first))
if first ~= last then
    total = total + (last - first - 1) * (shardsize-1)
    total = total + tonumber(redis.call('llen', KEYS[1]..last))
end

return total
''')

# <start id="sharded-list-pop-lua"/>
def sharded_lpop(conn, key):
    return sharded_list_pop_lua(
        conn, [key+':', key+':first', key+':last'], ['lpop'])

def sharded_rpop(conn, key):
    return sharded_list_pop_lua(
        conn, [key+':', key+':first', key+':last'], ['rpop'])

sharded_list_pop_lua = script_load('''
local skey = ARGV[1] == 'lpop' and KEYS[2] or KEYS[3]           --A
local okey = ARGV[1] ~= 'lpop' and KEYS[2] or KEYS[3]           --B
local shard = redis.call('get', skey) or '0'                    --C

local ret = redis.call(ARGV[1], KEYS[1]..shard)                 --D
if not ret or redis.call('llen', KEYS[1]..shard) == '0' then    --E
    local oshard = redis.call('get', okey) or '0'               --F

    if shard == oshard then                                     --G
        return ret                                              --G
    end

    local cmd = ARGV[1] == 'lpop' and 'incr' or 'decr'          --H
    shard = redis.call(cmd, skey)                               --I
    if not ret then
        ret = redis.call(ARGV[1], KEYS[1]..shard)               --J
    end
end
return ret
''')
# <end id="sharded-list-pop-lua"/>
#A Get the key for the end we will be popping from
#B Get the key for the end we won't be popping from
#C Get the shard id that we will be popping from
#D Pop from the shard
#E If we didn't get anything because the shard was empty, or we have just made the shard empty, we should clean up our shard endpoint
#F Get the shard id for the end we didn't pop from
#G If both ends of the sharded LIST are the same, then the list is now empty and we are done
#H Determine whether to increment or decrement the shard id, based on whether we were popping off the left or right end
#I Adjust our shard endpoint
#J If we didn't get a value before, try again on the new shard
#END

# <start id="sharded-blocking-list-pop"/>
DUMMY = str(uuid.uuid4())                                           #A

def sharded_bpop_helper(conn, key, timeout, pop, bpop, endp, push): #B
    pipe = conn.pipeline(False)                                     #C
    timeout = max(timeout, 0) or 2**64                              #C
    end = time.time() + timeout                                     #C
    
    while time.time() < end:
        result = pop(conn, key)                                     #D
        if result not in (None, DUMMY):                             #D
            return result                                           #D
    
        shard = conn.get(key + endp) or '0'                         #E
        sharded_bpop_helper_lua(pipe, [key + ':', key + endp],      #F
            [shard, push, DUMMY], force_eval=True)                  #L
        getattr(pipe, bpop)(key + ':' + shard, 1)                   #G
    
        result = (pipe.execute()[-1] or [None])[-1]                 #H
        if result not in (None, DUMMY):                             #H
            return result                                           #H

def sharded_blpop(conn, key, timeout=0):                              #I
    return sharded_bpop_helper(                                       #I
        conn, key, timeout, sharded_lpop, 'blpop', ':first', 'lpush') #I

def sharded_brpop(conn, key, timeout=0):                              #I
    return sharded_bpop_helper(                                       #I
        conn, key, timeout, sharded_rpop, 'brpop', ':last', 'rpush')  #I

sharded_bpop_helper_lua = script_load('''
local shard = redis.call('get', KEYS[2]) or '0'                     --J
if shard ~= ARGV[1] then                                            --K
    redis.call(ARGV[2], KEYS[1]..ARGV[1], ARGV[3])                  --K
end
''')
# <end id="sharded-blocking-list-pop"/>
#A Our defined dummy value, which you can change to be something that you shouldn't expect to see in your sharded LISTs
#B We are going to define a helper function that will actually perform the pop operations for both types of blocking pop operations
#C Prepare the pipeline and timeout information
#D Try to perform a non-blocking pop, returning the value it it isn't missing or the dummy value
#E Get the shard that we think we need to pop from
#F Run the Lua helper, which will handle pushing a dummy value if we are popping from the wrong shard
#L We use force_eval here to ensure an EVAL call instead of an EVALSHA, because we can't afford to perform a potentially failing EVALSHA inside a pipeline
#G Try to block on popping the item from the LIST, using the proper 'blpop' or 'brpop' command passed in
#H If we got an item, then we are done, otherwise retry
#I These functions prepare the actual call to the underlying blocking pop operations
#J Get the actual shard for the end we want to pop from
#K If we were going to try to pop from the wrong shard, push an extra value
#END

class TestCh11(unittest.TestCase):
    def setUp(self):
        self.conn = redis.Redis(db=15)
        self.conn.flushdb()
    def tearDown(self):
        self.conn.flushdb()

    def test_load_script(self):
        self.assertEquals(script_load("return 1")(self.conn), 1)

    def test_create_status(self):
        self.conn.hset('user:1', 'login', 'test')
        sid = _create_status(self.conn, 1, 'hello')
        sid2 = create_status(self.conn, 1, 'hello')
        
        self.assertEquals(self.conn.hget('user:1', 'posts'), '2')
        data = self.conn.hgetall('status:%s'%sid)
        data2 = self.conn.hgetall('status:%s'%sid2)
        data.pop('posted'); data.pop('id')
        data2.pop('posted'); data2.pop('id')
        self.assertEquals(data, data2)

    def test_locking(self):
        identifier = acquire_lock_with_timeout(self.conn, 'test', 1, 5)
        self.assertTrue(identifier)
        self.assertFalse(acquire_lock_with_timeout(self.conn, 'test', 1, 5))
        release_lock(self.conn, 'test', identifier)
        self.assertTrue(acquire_lock_with_timeout(self.conn, 'test', 1, 5))
    
    def test_semaphore(self):
        ids = []
        for i in xrange(5):
            ids.append(acquire_semaphore(self.conn, 'test', 5, timeout=1))
        self.assertTrue(None not in ids)
        self.assertFalse(acquire_semaphore(self.conn, 'test', 5, timeout=1))
        time.sleep(.01)
        id = acquire_semaphore(self.conn, 'test', 5, timeout=0)
        self.assertTrue(id)
        self.assertFalse(refresh_semaphore(self.conn, 'test', ids[-1]))
        self.assertFalse(release_semaphore(self.conn, 'test', ids[-1]))

        self.assertTrue(refresh_semaphore(self.conn, 'test', id))
        self.assertTrue(release_semaphore(self.conn, 'test', id))
        self.assertFalse(release_semaphore(self.conn, 'test', id))

    def test_autocomplet_on_prefix(self):
        for word in 'these are some words that we will be autocompleting on'.split():
            self.conn.zadd('members:test', word, 0)
        
        self.assertEquals(autocomplete_on_prefix(self.conn, 'test', 'th'), ['that', 'these'])
        self.assertEquals(autocomplete_on_prefix(self.conn, 'test', 'w'), ['we', 'will', 'words'])
        self.assertEquals(autocomplete_on_prefix(self.conn, 'test', 'autocompleting'), ['autocompleting'])

    def test_marketplace(self):
        self.conn.sadd('inventory:1', '1')
        self.conn.hset('users:2', 'funds', 5)
        self.assertFalse(list_item(self.conn, 2, 1, 10))
        self.assertTrue(list_item(self.conn, 1, 1, 10))
        self.assertFalse(purchase_item(self.conn, 2, '1', 1))
        self.conn.zadd('market:', '1.1', 4)
        self.assertTrue(purchase_item(self.conn, 2, '1', 1))

    def test_sharded_list(self):
        self.assertEquals(sharded_lpush(self.conn, 'lst', *range(100)), 100)
        self.assertEquals(sharded_llen(self.conn, 'lst'), 100)

        self.assertEquals(sharded_lpush(self.conn, 'lst2', *range(1000)), 1000)
        self.assertEquals(sharded_llen(self.conn, 'lst2'), 1000)
        self.assertEquals(sharded_rpush(self.conn, 'lst2', *range(-1, -1001, -1)), 1000)
        self.assertEquals(sharded_llen(self.conn, 'lst2'), 2000)

        self.assertEquals(sharded_lpop(self.conn, 'lst2'), '999')
        self.assertEquals(sharded_rpop(self.conn, 'lst2'), '-1000')
        
        for i in xrange(999):
            r = sharded_lpop(self.conn, 'lst2')
        self.assertEquals(r, '0')

        results = []
        def pop_some(conn, fcn, lst, count, timeout):
            for i in xrange(count):
                results.append(sharded_blpop(conn, lst, timeout))
        
        t = threading.Thread(target=pop_some, args=(self.conn, sharded_blpop, 'lst3', 10, 1))
        t.setDaemon(1)
        t.start()
        
        self.assertEquals(sharded_rpush(self.conn, 'lst3', *range(4)), 4)
        time.sleep(2)
        self.assertEquals(sharded_rpush(self.conn, 'lst3', *range(4, 8)), 4)
        time.sleep(2)
        self.assertEquals(results, ['0', '1', '2', '3', None, '4', '5', '6', '7', None])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = chA_listing_source

'''
# <start id="linux-redis-install"/>
~:$ wget -q http://redis.googlecode.com/files/redis-2.6.2.tar.gz  #A
~:$ tar -xzf redis-2.6.2.tar.gz                            #B
~:$ cd redis-2.6.2/
~/redis-2.6.2:$ make                                    #C
cd src && make all                                          #D
[trimmed]                                                   #D
make[1]: Leaving directory `~/redis-2.6.2/src'          #D
~/redis-2.6.2:$ sudo make install                       #E
cd src && make install                                      #F
[trimmed]                                                   #F
make[1]: Leaving directory `~/redis-2.6.2/src'          #F
~/redis-2.6.2:$ redis-server redis.conf                             #G
[13792] 26 Aug 17:53:16.523 * Max number of open files set to 10032 #H
[trimmed]                                                           #H
[13792] 26 Aug 17:53:16.529 * The server is now ready to accept     #H
connections on port 6379                                            #H
# <end id="linux-redis-install"/>
#A Download the most recent version of Redis 2.6 (we use some features of Redis 2.6 in other chapters, but you can use the most recent version you are comfortable with by finding the download link: http://redis.io/download )
#B Extract the source code
#C Compile Redis
#D Watch compilation messages go by, you shouldn't see any errors
#E Install Redis
#F Watch installation messages go by, you shouldn't see any errors
#G Start Redis server
#H See the confirmation that Redis has started
#END
'''

'''
# <start id="linux-python-install"/>
~:$ wget -q http://peak.telecommunity.com/dist/ez_setup.py          #A
~:$ sudo python ez_setup.py                                         #B
Downloading http://pypi.python.org/packages/2.7/s/setuptools/...    #B
[trimmed]                                                           #B
Finished processing dependencies for setuptools==0.6c11             #B
~:$ sudo python -m easy_install redis hiredis                       #C
Searching for redis                                                 #D
[trimmed]                                                           #D
Finished processing dependencies for redis                          #D
Searching for hiredis                                               #E
[trimmed]                                                           #E
Finished processing dependencies for hiredis                        #E
~:$
# <end id="linux-python-install"/>
#A Download the setuptools ez_setup module
#B Run the ez_setup module to download and install setuptools
#C Run setuptools' easy_install package to install the redis and hiredis packages
#D The redis package offers a somewhat standard interface to Redis from Python
#E The hiredis package is a C accelerator library for the Python Redis library
#END
'''

'''
# <start id="mac-redis-install"/>
~:$ curl -O http://rudix.googlecode.com/hg/Ports/rudix/rudix.py     #A
[trimmed]
~:$ sudo python rudix.py install rudix                              #B
Downloading rudix.googlecode.com/files/rudix-12.6-0.pkg             #C
[trimmed]                                                           #C
installer: The install was successful.                              #C
All done                                                            #C
~:$ sudo rudix install redis                                        #D
Downloading rudix.googlecode.com/files/redis-2.4.15-0.pkg           #E
[trimmed]                                                           #E
installer: The install was successful.                              #E
All done                                                            #E
~:$ redis-server                                                    #F
[699] 13 Jul 21:18:09 # Warning: no config file specified, using the#G
default config. In order to specify a config file use 'redis-server #G
/path/to/redis.conf'                                                #G
[699] 13 Jul 21:18:09 * Server started, Redis version 2.4.15        #G
[699] 13 Jul 21:18:09 * The server is now ready to accept connections#G
on port 6379                                                        #G
[699] 13 Jul 21:18:09 - 0 clients connected (0 slaves), 922304 bytes#G
in use                                                              #G
# <end id="mac-redis-install"/>
#A Download the bootstrap script that installs Rudix
#B Tell Rudix to install itself
#C Rudix is downloading and installing itself
#D Tell Rudix to install Redis
#E Rudix is downloading and installing Redis - note that we use some features from Redis 2.6, which is not yet available from Rudix
#F Start the Redis server
#G Redis started, and is running with the default configuration
#END
'''

'''
# <start id="mac-python-install"/>
~:$ sudo rudix install pip                              #A
Downloading rudix.googlecode.com/files/pip-1.1-1.pkg    #B
[trimmed]                                               #B
installer: The install was successful.                  #B
All done                                                #B
~:$ sudo pip install redis                              #C
Downloading/unpacking redis                             #D
[trimmed]                                               #D
Cleaning up...                                          #D
~:$
# <end id="mac-python-install"/>
#A Because we have Rudix installed, we can install a Python package manager called pip
#B Rudix is installing pip
#C We can now use pip to install the Python Redis client library
#D Pip is installing the Redis client library for Python
#END
'''

'''
# <start id="windows-python-install"/>
C:\Users\josiah>c:\python27\python                                      #A
Python 2.7.3 (default, Apr 10 2012, 23:31:26) [MSC v.1500 32 bit...
Type "help", "copyright", "credits" or "license" for more information.
>>> from urllib import urlopen                                          #B
>>> data = urlopen('http://peak.telecommunity.com/dist/ez_setup.py')    #C
>>> open('ez_setup.py', 'wb').write(data.read())                        #D
>>> exit()                                                              #E

C:\Users\josiah>c:\python27\python ez_setup.py                          #F
Downloading http://pypi.python.org/packages/2.7/s/setuptools/...        #G
[trimmed]                                                               #G
Finished processing dependencies for setuptools==0.6c11                 #G

C:\Users\josiah>c:\python27\python -m easy_install redis                #H
Searching for redis                                                     #H
[trimmed]                                                               #H
Finished processing dependencies for redis                              #H
C:\Users\josiah>
# <end id="windows-python-install"/>
#A Start Python by itself in interactive mode
#B Import the urlopen factory function from the urllib module
#C Fetch a module that will help us install other packages
#D Write the downloaded module to a file on disk
#E Quit the Python interpreter by running the builtin exit() function
#F Run the ez_setup helper module
#G The ez_setup helper downloads and installs setuptools, which will make it easy to download and install the Redis client library
#H Use setuptools' easy_install module to download and install Redis
#END
'''


'''
# <start id="hello-redis-appendix"/>
~:$ python                                          #A
Python 2.6.5 (r265:79063, Apr 16 2010, 13:09:56) 
[GCC 4.4.3] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import redis                                    #B
>>> conn = redis.Redis()                            #C
>>> conn.set('hello', 'world')                      #D
True                                                #D
>>> conn.get('hello')                               #E
'world'                                             #E
# <end id="hello-redis-appendix"/>
#A Start Python so that we can verify everything is up and running correctly
#B Import the redis library, it will automatically use the hiredis C accelerator library if it is available
#C Create a connection to Redis
#D Set a value and see that it was set
#E Get the value we just set
#END
'''

########NEW FILE########
