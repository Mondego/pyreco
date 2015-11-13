__FILENAME__ = block
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(answer):
    def f(x):
        print answer
    return f

twitter.Twitter(sys.argv[1], sys.argv[2]).block(sys.argv[3]).addCallback(
    cb("worked")).addErrback(cb("didn't work")).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = dms
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry from %s: %s" % (msg.sender_screen_name, msg.text)

twitter.Twitter(sys.argv[1], sys.argv[2]).direct_messages(gotEntry).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = feed
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor
from twisted.python import log

from twittytwister import twitter

def cb(entry):
    print entry.text

twitter.TwitterFeed(sys.argv[1], sys.argv[2]).spritzer(cb).addErrback(log.err)

reactor.run()

########NEW FILE########
__FILENAME__ = follow-rt
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor
from twisted.python import log

from twittytwister import twitter

def cb(entry):
    print entry.text

u, p, follows = sys.argv[1], sys.argv[2], sys.argv[3:]

twitter.TwitterFeed(u, p).follow(cb, set(follows)).addErrback(log.err)

reactor.run()

########NEW FILE########
__FILENAME__ = follow
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(answer):
    def f(x):
        print answer
    return f

twitter.Twitter(sys.argv[1], sys.argv[2]).follow(sys.argv[3]).addCallback(
    cb("worked")).addErrback(cb("didn't work")).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = friends
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry from %s: %s" % (msg.user.screen_name, msg.text)

twitter.Twitter(sys.argv[1], sys.argv[2]).friends(gotEntry).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = friends_ids
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
Copyright (c) 2009  Eduardo Habkost <ehabkost@raisama.net>

"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotId(data):
    print "Friend ID: %s" % (data)

def error(e):
    print "ERROR: ",e

twitter.Twitter(sys.argv[1], sys.argv[2]).friends_ids(gotId, sys.argv[3]).addErrback(error).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = leave
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(answer):
    def f(x):
        print answer
    return f

twitter.Twitter(sys.argv[1], sys.argv[2]).leave(sys.argv[3]).addCallback(
    cb("worked")).addErrback(cb("didn't work")).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = list-followers-oauth
#!/usr/bin/env python
"""

Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def gotUser(user):
    print "User:  %s (%s)" % (user.name, user.screen_name)

un=None
if len(sys.argv) > 5:
    un=sys.argv[5]

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

twitter.Twitter(consumer=consumer, token=token).list_followers(gotUser, un).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = list-followers
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotUser(user):
    print "User:  %s (%s)" % (user.name, user.screen_name)

un=None
if len(sys.argv) > 3:
    un=sys.argv[3]

twitter.Twitter(sys.argv[1], sys.argv[2]).list_followers(gotUser, un).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = list-friends-oauth
#!/usr/bin/env python
"""

Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def gotUser(user):
    print "User:  %s (%s)" % (user.name, user.screen_name)

un=None
if len(sys.argv) > 5:
    un=sys.argv[5]

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

twitter.Twitter(consumer=consumer, token=token).list_friends(gotUser, un).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = list-friends
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotUser(user):
    print "User:  %s (%s)" % (user.name, user.screen_name)

def gotPage(next, prev):
    print "end of page: next:%s prev:%s" % (next, prev)

def error(e):
    print "ERROR: %s" % (e)
    reactor.stop()

un=None
if len(sys.argv) > 3:
    un=sys.argv[3]

params={}
if len(sys.argv) > 4:
    params = {'cursor':sys.argv[4]}

twitter.Twitter(sys.argv[1], sys.argv[2]).list_friends(gotUser, un, params, page_delegate=gotPage).addCallbacks(
    lambda x: reactor.stop(), error)

reactor.run()

########NEW FILE########
__FILENAME__ = list_members
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
Copyright (c) 2009  Bogdano Arendartchuk <debogdano@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry from %s" % repr(msg.screen_name)

twitter.Twitter(sys.argv[1], sys.argv[2]).list_members(gotEntry, sys.argv[3],
        sys.argv[4]).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = list_timeline
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
Copyright (c) 2009  Bogdano Arendartchuk <debogdano@gmail.com>
"""

import sys

from twisted.internet import reactor, defer

from twittytwister import twitter

fetchCount = 0

@defer.deferredGenerator
def getSome(tw, list_user, list_name):
    global fetchCount
    fetchCount = 0

    def gotEntry(msg):
        global fetchCount
        fetchCount += 1
        sys.stdout.write(msg.text.encode("utf8") + "\n")

    page = 1
    while True:
        fetchCount = 0
        sys.stderr.write("Fetching page %d for %s/%s\n" % (page, list_user,
            list_name))
        d = tw.list_timeline(gotEntry, list_user, list_name,
                {'count': '200', 'page': str(page)})
        page += 1
        wfd = defer.waitForDeferred(d)
        yield wfd
        wfd.getResult()

        if fetchCount == 0:
            reactor.stop()

user = sys.argv[1]
list_user = sys.argv[3]
list_name = sys.argv[4]

tw = twitter.Twitter(sys.argv[1], sys.argv[2])

defer.maybeDeferred(getSome, tw, list_user, list_name)

reactor.run()

########NEW FILE########
__FILENAME__ = public_timeline
#!/usr/bin/env python
"""

Copyright (c) 2009  tsing <tsing@jianqing.org>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry from %s: %s" % (msg.author.name, msg.title)

twitter.Twitter(sys.argv[1], sys.argv[2]).public_timeline(gotEntry).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = replies
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry from %s: %s" % (msg.author.name, msg.title)

twitter.Twitter(sys.argv[1], sys.argv[2]).replies(gotEntry).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotEntry(msg):
    print "Got a entry: ", msg.title

twitter.Twitter().search(sys.argv[1], gotEntry).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = show-user-oauth
#!/usr/bin/env python
"""

Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def gotUser(u):
    print "Got a user: %s" % u

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

twitter.Twitter(consumer=consumer, token=token).show_user(sys.argv[5]).addCallback(
    gotUser).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = show-user
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def gotUser(u):
    print "Got a user: %s" % u

twitter.Twitter(sys.argv[1], sys.argv[2]).show_user(sys.argv[3]).addCallback(
    gotUser).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = track-proxy
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor
from twisted.python import log

from twittytwister import twitter

def cb(entry):
    print entry.text

u, p, terms = sys.argv[1], sys.argv[2], sys.argv[3:]

proxy_host = "my_proxy_host"
proxy_port = 80  # 80 is the default
proxy_username = "username"
proxy_password = "secret"

twitter.TwitterFeed(u, p, proxy_host=proxy_host, proxy_port=proxy_port,
        proxy_username=proxy_username, proxy_password=proxy_password
        ).track(cb, set(terms)).addErrback(log.err)

reactor.run()

########NEW FILE########
__FILENAME__ = track
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor
from twisted.python import log

from twittytwister import twitter

def cb(entry):
    print entry.text

u, p, terms = sys.argv[1], sys.argv[2], sys.argv[3:]

twitter.TwitterFeed(u, p).track(cb, set(terms)).addErrback(log.err)

reactor.run()

########NEW FILE########
__FILENAME__ = unblock
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(answer):
    def f(x):
        print answer
    return f

twitter.Twitter(sys.argv[1], sys.argv[2]).unblock(sys.argv[3]).addCallback(
    cb("worked")).addErrback(cb("didn't work")).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = update-oauth
#!/usr/bin/env python
"""
Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def cb(x):
    print "Posted id", x

def eb(e):
    print e

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

twitter.Twitter(consumer=consumer, token=token).update(' '.join(sys.argv[5:])
    ).addCallback(cb).addErrback(eb).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = update-with-client-name
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(x):
    print "Posted id", x

def eb(e):
    print e

#set client info
#beware that if you want to use your own client name you should
#talk about it in the twitter development mailing list so they can
#add it, or else it will show up as being 'from web'
info = twitter.TwitterClientInfo('TweetDeck', '1.0', 'http://tweetdeck.com/')
twitter.Twitter(sys.argv[1], sys.argv[2], client_info = info).update(' '.join(sys.argv[3:])
    ).addCallback(cb).addErrback(eb).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(x):
    print "Posted id", x

def eb(e):
    print e

twitter.Twitter(sys.argv[1], sys.argv[2]).update(' '.join(sys.argv[3:])
    ).addCallback(cb).addErrback(eb).addBoth(lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = update_profile_image-oauth
#!/usr/bin/env python
"""
Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def cb(x):
    print "Avatar updated"

def eb(e):
    print e

def both(x):
    avatar.close()
    reactor.stop()


consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])
avatar = open(sys.argv[5], 'r')


twitter.Twitter(consumer=consumer, token=token).update_profile_image('avatar.jpg', avatar.read()).addCallback(cb).addErrback(eb).addBoth(both)

reactor.run()

########NEW FILE########
__FILENAME__ = user_stream
#!/usr/bin/env python
#
# Copyright (c) 2012  Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Print Tweets on a user's timeline in real time.

This connects to the Twitter User Stream API endpoint with the given OAuth
credentials and prints out all Tweets of the associated user and of the
accounts the user follows. This is equivalent to the user's time line.

The arguments, in order, are: consumer key, consumer secret, access token key,
access token secret.
"""

import sys

from twisted.internet import reactor
from twisted.python import log

from oauth import oauth

from twittytwister import twitter

def cb(entry):
    print '%s: %s' % (entry.user.screen_name.encode('utf-8'),
                      entry.text.encode('utf-8'))

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

feed = twitter.TwitterFeed(consumer=consumer, token=token)
d = feed.user(cb, {'with': 'followings'})

# Exit when the connection was closed or an exception was raised.
d.addCallback(lambda protocol: protocol.deferred)
d.addErrback(log.err)
d.addBoth(lambda _: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = user_stream_monitor
#!/usr/bin/env python
#
# Copyright (c) 2012  Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Print Tweets on a user's timeline in real time.

This connects to the Twitter User Stream API endpoint with the given OAuth
credentials and prints out all Tweets of the associated user and of the
accounts the user follows. This is equivalent to the user's time line.

The arguments, in order, are: consumer key, consumer secret, access token key,
access token secret.

This is mostly the same as the C{user_stream.py} example, except that this
uses L{twittytwisted.streaming.TwitterMonitor}. It will reconnect in the
face of disconnections or explicit reconnects to change the API request
parameters (e.g. changing the track keywords).
"""

import sys

from twisted.internet import reactor

from oauth import oauth

from twittytwister import twitter

def cb(entry):
    print '%s: %s' % (entry.user.screen_name.encode('utf-8'),
                      entry.text.encode('utf-8'))

def change(monitor):
    monitor.args = {}
    monitor.connect(forceReconnect=True)

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

feed = twitter.TwitterFeed(consumer=consumer, token=token)
monitor = twitter.TwitterMonitor(feed.user, cb, {'with': 'followings'})

monitor.startService()
reactor.callLater(30, change, monitor)

reactor.run()

########NEW FILE########
__FILENAME__ = user_timeline-oauth
#!/usr/bin/env python
"""

Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter
import oauth

def gotEntry(msg):
    print "%s" % (msg.text)

consumer = oauth.OAuthConsumer(sys.argv[1], sys.argv[2])
token = oauth.OAuthToken(sys.argv[3], sys.argv[4])

user = None
if len(sys.argv) > 5:
    user = sys.argv[5]

twitter.Twitter(consumer=consumer, token=token).user_timeline(gotEntry, user).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = user_timeline
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor, defer

from twittytwister import twitter

fetchCount = 0

@defer.deferredGenerator
def getSome(tw, user):
    global fetchCount
    fetchCount = 0

    def gotEntry(msg):
        global fetchCount
        fetchCount += 1
        sys.stdout.write(msg.text.encode("utf8") + "\n")

    page = 1
    while True:
        fetchCount = 0
        sys.stderr.write("Fetching page %d for %s\n" % (page, user))
        d = tw.user_timeline(gotEntry, user, {'count': '200', 'page': str(page)})
        page += 1
        wfd = defer.waitForDeferred(d)
        yield wfd
        wfd.getResult()

        if fetchCount == 0:
            reactor.stop()

user = sys.argv[1]
if len(sys.argv) > 3:
    user = sys.argv[3]

tw = twitter.Twitter(sys.argv[1], sys.argv[2])

defer.maybeDeferred(getSome, tw, user)

reactor.run()

########NEW FILE########
__FILENAME__ = verify_creds
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys

from twisted.internet import reactor

from twittytwister import twitter

def cb(answer):
    def f(x):
        print answer
    return f

twitter.Twitter(sys.argv[1], sys.argv[2]).verify_credentials().addCallback(
    cb("worked")).addErrback(cb("didn't work")).addBoth(
    lambda x: reactor.stop())

reactor.run()

########NEW FILE########
__FILENAME__ = txml_test
#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

from __future__ import with_statement

import sys
sys.path.append("twittytwister")
sys.path.append("../twittytwister")

from twisted.trial import unittest as twunit
import unittest

import txml

class XMLParserTest(twunit.TestCase):

    def parse_test(self, filename, parser):
        with open("../test/" + filename) as f:
            parser.write(f.read())

    def testParsingEntry(self):
        ts=self
        def gotEntry(e):
            if e.id == 'tag:search.twitter.com,2005:1043835074':
                ts.assertEquals('2008-12-07T19:50:01Z', e.published)
                ts.assertEquals('PlanetAmerica (PlanetAmerica)', e.author.name)
                ts.assertEquals('http://twitter.com/PlanetAmerica',
                    e.author.uri)
                ts.assertEquals(
                    'http://twitter.com/PlanetAmerica/statuses/1043835074',
                    e.alternate)
                ts.assertEquals(
                    'http://s3.amazonaws.com/twitter_production/'
                    'profile_images/66422442/PA_PeaceOnEarth_normal.JPG',
                    e.image)
                ts.assertEquals(
                    '@americac2c getting ready to go out to run errands...'
                    ' If I can just stop tweeting...'
                    ' TWITTER IS LIKE CRACK!', e.title)
                ts.assertEquals(
                    '&lt;a href="http://twitter.com/americac2c"&gt;'
                    '@americac2c&lt;/a&gt; getting ready to go out '
                    'to run errands... If I can just stop tweeting... '
                    '&lt;b&gt;TWITTER&lt;/b&gt; IS LIKE CRACK!',
                     e.content)
        self.parse_test('search.atom', txml.Feed(gotEntry))

    def testNewParsingEntry(self):
        ts=self
        def gotEntry(e):
            if e.id == 'tag:search.twitter.com,2005:1229915194':
                ts.assertEquals('&lt;a href="http://www.twhirl.org/"&gt;twhirl&lt;/a&gt;',
                                e.twitter_source)
        self.parse_test('new-search.atom', txml.Feed(gotEntry))

    def testParsingUser(self):
        ts=self
        def gotUser(u):
            if u.id == '16957618':
                ts.assertEquals('16957618', u.id)
                ts.assertEquals('Greg Yaitanes', u.name)
                ts.assertEquals('GregYaitanes', u.screen_name)
                ts.assertEquals('LA or NYC', u.location)
                ts.assertEquals(
                    'twitter investor, advisor and i direct things',
                    u.description)
                ts.assertEquals('http://s3.amazonaws.com/twitter_production/'
                    'profile_images/62795863/gybiopic_normal.jpg',
                    u.profile_image_url)
                ts.assertEquals('http://www.imdb.com/name/nm0944981/', u.url)
                ts.assertEquals('true', u.protected)
                ts.assertEquals('36', u.followers_count)
        self.parse_test('friends.xml', txml.Users(gotUser))

    def testParsingDirectMessages(self):
        ts=self
        def gotDirectMessage(dm):
            ts.assertEquals('45010464', dm.id)
            ts.assertEquals('24113688', dm.sender_id)
            ts.assertEquals('some stuff', dm.text)
            ts.assertEquals('14117412', dm.recipient_id)
            ts.assertEquals('Fri Dec 12 17:50:50 +0000 2008', dm.created_at)
            ts.assertEquals('somesender', dm.sender_screen_name)
            ts.assertEquals('dlsspy', dm.recipient_screen_name)

            ts.assertEquals('24113688', dm.sender.id)
            ts.assertEquals('Some Sender', dm.sender.name)
            ts.assertEquals('somesender', dm.sender.screen_name)
            ts.assertEquals('Some Place', dm.sender.location)
            ts.assertEquals('I do stuff.', dm.sender.description)
            ts.assertEquals('http://www.spy.net/obama-hornz.jpg',
                dm.sender.profile_image_url)
            ts.assertEquals('http://www.spy.net/', dm.sender.url)
            ts.assertEquals('false', dm.sender.protected)
            ts.assertEquals('76', dm.sender.followers_count)

            ts.assertEquals('14117412', dm.recipient.id)
            ts.assertEquals('Dustin Sallings', dm.recipient.name)
            ts.assertEquals('dlsspy', dm.recipient.screen_name)
            ts.assertEquals('Santa Clara, CA', dm.recipient.location)
            ts.assertEquals('Probably writing code.', dm.recipient.description)
            ts.assertEquals('http://s3.amazonaws.com/twitter_production/'
                'profile_images/57455325/IMG_0596_2_normal.JPG',
                dm.recipient.profile_image_url)
            ts.assertEquals('http://bleu.west.spy.net/~dustin/',
                dm.recipient.url)
            ts.assertEquals('false', dm.recipient.protected)
            ts.assertEquals('198', dm.recipient.followers_count)
        self.parse_test('dm.xml', txml.Direct(gotDirectMessage))

    def testParsingStatusList(self):
        ts=self
        def gotStatusItem(s):
            if s.id == '1054780802':
                ts.assertEquals('1054780802', s.id)
                ts.assertEquals('Sat Dec 13 04:10:57 +0000 2008', s.created_at)
                ts.assertEquals('Getting Jekyll ready for something '
                    'special next week.', s.text)
                ts.assertEquals('false', s.truncated)
                ts.assertEquals('', s.in_reply_to_status_id)
                ts.assertEquals('', s.in_reply_to_user_id)
                ts.assertEquals('false', s.favorited)
                ts.assertEquals('', s.in_reply_to_screen_name)
                ts.assertEquals('5502392', s.user.id)
                ts.assertEquals('Tom Preston-Werner', s.user.name)
                ts.assertEquals('mojombo', s.user.screen_name)
                ts.assertEquals('iPhone: 37.813461,-122.416519',
                    s.user.location)
                ts.assertEquals('powerset ftw!', s.user.description)
                ts.assertEquals('http://s3.amazonaws.com/twitter_production/'
                    'profile_images/21599172/tom_prestonwerner_normal.jpg',
                    s.user.profile_image_url)
                ts.assertEquals('http://rubyisawesome.com', s.user.url)
                ts.assertEquals('false', s.user.protected)
                ts.assertEquals('516', s.user.followers_count)

        self.parse_test('status_list.xml', txml.Statuses(gotStatusItem))

    def testParsingUser(self):
        ts = self
        def gotUser(u):
            ts.assertEquals('14117412', u.id)
            ts.assertEquals('Dustin Sallings', u.name)
            ts.assertEquals('dlsspy', u.screen_name)
            ts.assertEquals('Santa Clara, CA', u.location)
            ts.assertEquals('Probably writing code.', u.description)
            ts.assertEquals('http://s3.amazonaws.com/twitter_production/'
                'profile_images/57455325/IMG_0596_2_normal.JPG',
                u.profile_image_url)
            ts.assertEquals('http://bleu.west.spy.net/~dustin/', u.url)
            ts.assertEquals('false', u.protected)
            ts.assertEquals('201', u.followers_count)
            ts.assertEquals('9ae4e8', u.profile_background_color)
            ts.assertEquals('000000', u.profile_text_color)
            ts.assertEquals('0000ff', u.profile_link_color)
            ts.assertEquals('e0ff92', u.profile_sidebar_fill_color)
            ts.assertEquals('87bc44', u.profile_sidebar_border_color)
            ts.assertEquals('54', u.friends_count)
            ts.assertEquals('Mon Mar 10 20:57:07 +0000 2008', u.created_at)
            ts.assertEquals('37', u.favourites_count)
            ts.assertEquals('-28800', u.utc_offset)
            # ts.assertEquals('Pacific Time (US & Canada)', u.time_zone)
            ts.assertEquals('false', u.following)
            ts.assertEquals('false', u.notifications)
            ts.assertEquals('1583', u.statuses_count)
            ts.assertEquals('Sun Dec 14 07:24:26 +0000 2008',
                u.status.created_at)
            ts.assertEquals('1056508954', u.status.id)
            ts.assertEquals('Never before have so many people with so '
                'little to say said so much to so few. '
                'http://despair.com/blogging.html', u.status.text)
            # ts.assertEquals(
            #     '<a href="http://github.com/dustin/twitterspy">TwitterSpy< a>',
            #     u.status.source)
            ts.assertEquals('false', u.status.truncated)
            ts.assertEquals('', u.status.in_reply_to_status_id)
            ts.assertEquals('', u.status.in_reply_to_user_id)
            ts.assertEquals('false', u.status.favorited)
            ts.assertEquals('', u.status.in_reply_to_screen_name)

        self.parse_test('user.xml', txml.Users(gotUser))

    def testStatusUpdateParse(self):
        with open("../test/update.xml") as f:
            id = txml.parseUpdateResponse(f.read())
            self.assertEquals('1045518625', id)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = streaming
# -*- test-case-name: twittytwister.test.test_streaming -*-
#
# Copyright (c) 2010-2012 Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Twitter Streaming API.

@see: U{http://dev.twitter.com/pages/streaming_api}.
"""

import simplejson as json

from twisted.internet import defer
from twisted.protocols.basic import LineReceiver
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss

class LengthDelimitedStream(LineReceiver):
    """
    Length-delimited datagram decoder protocol.

    Datagrams are prefixed by a line with a decimal length in ASCII. Lines are
    delimited by C{\r\n} and maybe empty, for keep-alive purposes.
    """

    def __init__(self):
        self._rawBuffer = None
        self._rawBufferLength = None
        self._expectedLength = None


    def lineReceived(self, line):
        """
        Called when a line is received.

        We expect a length in bytes or an empty line for keep-alive. If
        we got a length, switch to raw mode to receive that amount of bytes.
        """
        if line and line.isdigit():
            self._expectedLength = int(line)
            self._rawBuffer = []
            self._rawBufferLength = 0
            self.setRawMode()
        else:
            self.keepAliveReceived()


    def rawDataReceived(self, data):
        """
        Called when raw data is received.

        Fill the raw buffer C{_rawBuffer} until we have received at least
        C{_expectedLength} bytes. Call C{datagramReceived} with the received
        byte string of the expected size. Then switch back to line mode with
        the remainder of the buffer.
        """
        self._rawBuffer.append(data)
        self._rawBufferLength += len(data)

        if self._rawBufferLength >= self._expectedLength:
            receivedData = ''.join(self._rawBuffer)
            expectedData = receivedData[:self._expectedLength]
            extraData = receivedData[self._expectedLength:]

            self._rawBuffer = None
            self._rawBufferLength = None
            self._expectedLength = None

            self.datagramReceived(expectedData)
            self.setLineMode(extraData)


    def datagramReceived(self, data):
        """
        Called when a datagram is received.
        """
        raise NotImplementedError()


    def keepAliveReceived(self):
        """
        Called when a empty line as keep-alive is received.

        This can be overridden for logging purposes.
        """



class TwitterObject(object):
    """
    A Twitter object.
    """
    raw = None
    SIMPLE_PROPS = None
    COMPLEX_PROPS = None
    LIST_PROPS = None

    @classmethod
    def fromDict(cls, data):
        """
        Fill this objects attributes from a dict for known properties.
        """
        obj = cls()
        obj.raw = data
        for name, value in data.iteritems():
            if cls.SIMPLE_PROPS and name in cls.SIMPLE_PROPS:
                setattr(obj, name, value)
            elif cls.COMPLEX_PROPS and name in cls.COMPLEX_PROPS:
                value = cls.COMPLEX_PROPS[name].fromDict(value)
                setattr(obj, name, value)
            elif cls.LIST_PROPS and name in cls.LIST_PROPS:
                value = [cls.LIST_PROPS[name].fromDict(item)
                         for item in value]
                setattr(obj, name, value)

        return obj


    def __repr__(self):
        bodyParts = []
        for name in dir(self):
            if self.SIMPLE_PROPS and name in self.SIMPLE_PROPS:
                if hasattr(self, name):
                    bodyParts.append("%s=%s" % (name,
                                                repr(getattr(self, name))))

            elif self.COMPLEX_PROPS and name in self.COMPLEX_PROPS:
                if hasattr(self, name):
                    bodyParts.append("%s=%s" % (name,
                                                repr(getattr(self, name))))
            elif self.LIST_PROPS and name in self.LIST_PROPS:
                if hasattr(self, name):
                    items = getattr(self, name)

                    itemBodyParts = []
                    for item in items:
                        itemBodyParts.append(repr(item))

                    itemBody = ',\n'.join(itemBodyParts)
                    lines = itemBody.splitlines()
                    itemBody = '\n    '.join(lines)

                    if itemBody:
                        itemBody = '\n    %s\n' % (itemBody,)

                    bodyParts.append("%s=[%s]" % (name, itemBody))

        body = ',\n'.join(bodyParts)
        lines = body.splitlines()
        body = '\n    '.join(lines)

        result = "%s(\n    %s\n)" % (self.__class__.__name__, body)
        return result



class Indices(TwitterObject):
    """
    Indices for tweet entities.
    """
    start = None
    end = None

    @classmethod
    def fromDict(cls, data):
        obj = cls()
        obj.raw = data
        try:
            obj.start, obj.end = data
        except (TypeError, ValueError):
            log.err()
        return obj

    def __repr__(self):
        return "%s(start=%s, end=%s)" % (self.__class__.__name__,
                                         self.start, self.end)



class Size(TwitterObject):
    """
    Size of a media object.
    """
    SIMPLE_PROPS = set(['w', 'h', 'resize'])



class Sizes(TwitterObject):
    """
    Available sizes for a media object.
    """
    COMPLEX_PROPS = {'large': Size,
                     'medium': Size,
                     'small': Size,
                     'thumb': Size}



class Media(TwitterObject):
    """
    Media entity.
    """
    SIMPLE_PROPS = set(['id', 'media_url', 'media_url_https', 'url',
                        'display_url', 'expanded_url', 'type'])
    COMPLEX_PROPS = {'indices': Indices, 'sizes': Sizes}



class URL(TwitterObject):
    """
    URL entity.
    """
    SIMPLE_PROPS = set(['url', 'display_url', 'expanded_url'])
    COMPLEX_PROPS = {'indices': Indices}



class UserMention(TwitterObject):
    SIMPLE_PROPS = set(['id', 'screen_name', 'name'])
    COMPLEX_PROPS = {'indices': Indices}



class HashTag(TwitterObject):
    SIMPLE_PROPS = set(['text'])
    COMPLEX_PROPS = {'indices': Indices}



class Entities(TwitterObject):
    """
    Tweet entities.
    """
    LIST_PROPS = {'media': Media, 'urls': URL,
                  'user_mentions': UserMention, 'hashtags': HashTag}



class Status(TwitterObject):
    """
    Twitter Status.
    """
    SIMPLE_PROPS = set(['created_at', 'id', 'text', 'source', 'truncated',
        'in_reply_to_status_id', 'in_reply_to_screen_name',
        'in_reply_to_user_id', 'favorited', 'user_id', 'geo'])
    COMPLEX_PROPS = {'entities': Entities}

# circular reference:
Status.COMPLEX_PROPS['retweeted_status'] = Status



class User(TwitterObject):
    """
    Twitter User.
    """
    SIMPLE_PROPS = set(['id', 'name', 'screen_name', 'location', 'description',
        'profile_image_url', 'url', 'protected', 'followers_count',
        'profile_background_color', 'profile_text_color', 'profile_link_color',
        'profile_sidebar_fill_color', 'profile_sidebar_border_color',
        'friends_count', 'created_at', 'favourites_count', 'utc_offset',
        'time_zone', 'following', 'notifications', 'statuses_count',
        'profile_background_image_url', 'profile_background_tile', 'verified',
        'geo_enabled'])
    COMPLEX_PROPS = {'status': Status}

# circular reference:
Status.COMPLEX_PROPS['user'] = User



class TwitterStream(LengthDelimitedStream, TimeoutMixin):
    """
    Twitter Stream.

    This protocol decodes an JSON encoded stream of Twitter statuses and
    associated datastructures, where each datagram is length-delimited.

    L{TimeoutMixin} is used to disconnect the stream in case Twitter stops
    sending data, including the keep-alives that usually result in traffic
    at least every 30 seconds. If not passed using C{timeoutPeriod}, the
    timeout period is set to 60 seconds.
    """

    def __init__(self, callback, timeoutPeriod=60):
        LengthDelimitedStream.__init__(self)
        self.setTimeout(timeoutPeriod)
        self.callback = callback
        self.deferred = defer.Deferred()


    def dataReceived(self, data):
        """
        Called when data is received.

        This overrides the default implementation from LineReceiver to
        reset the connection timeout.
        """
        self.resetTimeout()
        LengthDelimitedStream.dataReceived(self, data)


    def datagramReceived(self, data):
        """
        Decode the JSON-encoded datagram and call the callback.
        """
        try:
            obj = json.loads(data)
        except ValueError, e:
            log.err(e, 'Invalid JSON in stream: %r' % data)
            return

        if u'text' in obj:
            obj = Status.fromDict(obj)
        else:
            log.msg('Unsupported object %r' % obj)
            return

        self.callback(obj)


    def connectionLost(self, reason):
        """
        Called when the body is complete or the connection was lost.

        @note: As the body length is usually not known at the beginning of the
        response we expect a L{PotentialDataLoss} when Twitter closes the
        stream, instead of L{ResponseDone}. Other exceptions are treated
        as error conditions.
        """
        self.setTimeout(None)
        if reason.check(ResponseDone, PotentialDataLoss):
            self.deferred.callback(None)
        else:
            self.deferred.errback(reason)


    def timeoutConnection(self):
        """
        Called when the connection times out.

        This protocol is used to process the HTTP response body. Its transport
        is really a proxy, that does not provide C{loseConnection}. Instead it
        has C{stopProducing}, which will result in the real transport being
        closed when called.
        """
        self.transport.stopProducing()

########NEW FILE########
__FILENAME__ = test_streaming
# Copyright (c) 2010-2012 Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Tests for L{twittytwister.streaming}.
"""

from twisted.internet import task
from twisted.python import failure
from twisted.test import proto_helpers
from twisted.trial import unittest
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss

from twittytwister import streaming

class StreamTester(streaming.LengthDelimitedStream):
    """
    Test helper that stores all received datagrams in sequence.
    """
    def __init__(self):
        streaming.LengthDelimitedStream.__init__(self)
        self.datagrams = []
        self.keepAlives = 0


    def datagramReceived(self, data):
        self.datagrams.append(data)


    def keepAliveReceived(self):
        self.keepAlives += 1



class LengthDelimitedStreamTest(unittest.TestCase):
    """
    Tests for L{LengthDelimitedStream}.
    """

    def setUp(self):
        transport = proto_helpers.StringTransport()
        self.protocol = StreamTester()
        self.protocol.makeConnection(transport)


    def test_receiveDatagram(self):
        """
        A datagram is a length, CRLF and a sequence of bytes of given length.
        """
        self.protocol.dataReceived("""4\r\ntest""")
        self.assertEquals(['test'], self.protocol.datagrams)
        self.assertEquals(0, self.protocol.keepAlives)


    def test_receiveTwoDatagrams(self):
        """
        Two encoded datagrams should result in two calls to datagramReceived.
        """
        self.protocol.dataReceived("""4\r\ntest5\r\ntest2""")
        self.assertEquals(['test', 'test2'], self.protocol.datagrams)
        self.assertEquals(0, self.protocol.keepAlives)


    def test_receiveKeepAlive(self):
        """
        Datagrams may have empty keep-alive lines in between.
        """
        self.protocol.dataReceived("""4\r\ntest\r\n5\r\ntest2""")
        self.assertEquals(['test', 'test2'], self.protocol.datagrams)
        self.assertEquals(1, self.protocol.keepAlives)


    def test_notImplemented(self):
        self.protocol = streaming.LengthDelimitedStream()
        self.assertRaises(NotImplementedError, self.protocol.dataReceived,
                                               """4\r\ntest""")



class TwitterObjectTest(unittest.TestCase):
    """
    Tests for L{streaming.TwitterObject} and subclasses.
    """

    def setUp(self):
        self.data = [
            {
                'contributors': None,
                'coordinates': None,
                'created_at': 'Mon Dec 06 11:46:33 +0000 2010',
                'entities': {'hashtags': [], 'urls': [], 'user_mentions': []},
                'favorited': False,
                'geo': None,
                'id': 11748322888908800,
                'id_str': '11748322888908800',
                'in_reply_to_screen_name': None,
                'in_reply_to_status_id': None,
                'in_reply_to_status_id_str': None,
                'in_reply_to_user_id': None,
                'in_reply_to_user_id_str': None,
                'place': None,
                'retweet_count': None,
                'retweeted': False,
                'source': 'web',
                'text': 'Test #1',
                'truncated': False,
                'user': {
                    'contributors_enabled': False,
                    'created_at': 'Mon Aug 31 13:36:20 +0000 2009',
                    'description': None,
                    'favourites_count': 0,
                    'follow_request_sent': None,
                    'followers_count': 1,
                    'following': None,
                    'friends_count': 0,
                    'geo_enabled': False,
                    'id': 70393696,
                    'id_str': '70393696',
                    'lang': 'en',
                    'listed_count': 0,
                    'location': None,
                    'name': 'ikDisplay',
                    'notifications': None,
                    'profile_background_color': 'C0DEED',
                    'profile_background_image_url': 'http://s.twimg.com/a/1290538325/images/themes/theme1/bg.png',
                    'profile_background_tile': False,
                    'profile_image_url': 'http://a2.twimg.com/profile_images/494331594/ikTag_normal.png',
                    'profile_link_color': '0084B4',
                    'profile_sidebar_border_color': 'C0DEED',
                    'profile_sidebar_fill_color': 'DDEEF6',
                    'profile_text_color': '333333',
                    'profile_use_background_image': True,
                    'protected': False,
                    'screen_name': 'ikdisplay',
                    'show_all_inline_media': False,
                    'statuses_count': 23,
                    'time_zone': None,
                    'url': None,
                    'utc_offset': None,
                    'verified': False}},
            {
                "text": "#Photos on Twitter: taking flight http://t.co/qbJx26r",
                "entities": {
                    "media": [
                        {
                            "id": 76360760611180544,
                            "id_str": "76360760611180544",
                            "media_url": "http://p.twimg.com/AQ9JtQsCEAA7dEN.jpg",
                            "media_url_https": "https://p.twimg.com/AQ9JtQsCEAA7dEN.jpg",
                            "url": "http://t.co/qbJx26r",
                            "display_url": "pic.twitter.com/qbJx26r",
                            "expanded_url": "http://twitter.com/twitter/status/76360760606986241/photo/1",
                            "sizes": {
                                "large": {
                                    "w": 700,
                                    "resize": "fit",
                                    "h": 466
                                },
                                "medium": {
                                    "w": 600,
                                    "resize": "fit",
                                    "h": 399
                                },
                                "small": {
                                    "w": 340,
                                    "resize": "fit",
                                    "h": 226
                                },
                                "thumb": {
                                    "w": 150,
                                    "resize": "crop",
                                    "h": 150
                                }
                            },
                            "type": "photo",
                            "indices": [
                                34,
                                53
                            ]
                        }
                    ],
                    "urls": [],
                    "user_mentions": [],
                    "hashtags": []
                }
            }
        ]


    def test_fromDictBasic(self):
        """
        A tweet is a Status with a user attribute holding a User.
        """

        status = streaming.Status.fromDict(self.data[0])
        self.assertEquals(u'Test #1', status.text)
        self.assertEquals(70393696, status.user.id)
        self.assertEquals(u'ikdisplay', status.user.screen_name)


    def test_fromDictEntitiesMediaBasic(self):
        """
        Media entities are parsed, simple properties are available.
        """

        status = streaming.Status.fromDict(self.data[1])
        self.assertTrue(hasattr(status.entities, 'media'))
        self.assertTrue(hasattr(status.entities, 'urls'))
        self.assertTrue(hasattr(status.entities, 'user_mentions'))
        self.assertTrue(hasattr(status.entities, 'hashtags'))
        self.assertEqual(1, len(status.entities.media))
        mediaItem = status.entities.media[0]
        self.assertEqual(76360760611180544, mediaItem.id)
        self.assertEqual('http://p.twimg.com/AQ9JtQsCEAA7dEN.jpg',
                         mediaItem.media_url)


    def test_fromDictEntitiesMediaIndices(self):
        """
        Media entities are parsed, simple properties are available.
        """

        status = streaming.Status.fromDict(self.data[1])
        mediaItem = status.entities.media[0]
        self.assertEquals(34, mediaItem.indices.start)
        self.assertEquals(53, mediaItem.indices.end)


    def test_fromDictEntitiesMediaSizes(self):
        """
        Media sizes are extracted.
        """

        status = streaming.Status.fromDict(self.data[1])
        mediaItem = status.entities.media[0]
        self.assertEquals(700, mediaItem.sizes.large.w)
        self.assertEquals(466, mediaItem.sizes.large.h)
        self.assertEquals('fit', mediaItem.sizes.large.resize)


    def test_fromDictEntitiesURL(self):
        """
        URL entities are extracted.
        """
        data = {
            "urls": [
                {
                    "url": "http://t.co/0JG5Mcq",
                    "display_url": u"blog.twitter.com/2011/05/twitte\xe2",
                    "expanded_url": "http://blog.twitter.com/2011/05/twitter-for-mac-update.html",
                    "indices": [
                        84,
                        103
                    ]
                }
            ],
        }
        entities = streaming.Entities.fromDict(data)
        self.assertEquals('http://t.co/0JG5Mcq', entities.urls[0].url)


    def test_fromDictEntitiesUserMention(self):
        """
        User mention entities are extracted.
        """
        data = {
            "user_mentions": [
                {
                    "id": 22548447,
                    "id_str": "22548447",
                    "screen_name": "rno",
                    "name": "Arnaud Meunier",
                    "indices": [
                        0,
                        4
                    ]
                }
            ],
        }
        entities = streaming.Entities.fromDict(data)
        user_mention = entities.user_mentions[0]
        self.assertEquals(22548447, user_mention.id)
        self.assertEquals('rno', user_mention.screen_name)
        self.assertEquals('Arnaud Meunier', user_mention.name)
        self.assertEquals(0, user_mention.indices.start)
        self.assertEquals(4, user_mention.indices.end)


    def test_fromDictEntitiesHashTag(self):
        """
        Hash tag entities are extracted.
        """
        data = {
            "hashtags": [
                {
                    "text": "devnestSF",
                    "indices": [
                        6,
                        16
                    ]
                }
            ]
        }
        entities = streaming.Entities.fromDict(data)
        hashTag = entities.hashtags[0]
        self.assertEquals('devnestSF', hashTag.text)
        self.assertEquals(6, hashTag.indices.start)
        self.assertEquals(16, hashTag.indices.end)


    def test_repr(self):
        data = {
                'created_at': 'Mon Dec 06 11:46:33 +0000 2010',
                'entities': {'hashtags': [], 'urls': [], 'user_mentions': []},
                'id': 11748322888908800,
                'text': 'Test #1',
                'user': {
                    'id': 70393696,
                    'screen_name': 'ikdisplay',
                    }
                }
        status = streaming.Status.fromDict(data)
        result = repr(status)
        expected = """Status(
    created_at='Mon Dec 06 11:46:33 +0000 2010',
    entities=Entities(
        hashtags=[],
        urls=[],
        user_mentions=[]
    ),
    id=11748322888908800,
    text='Test #1',
    user=User(
        id=70393696,
        screen_name='ikdisplay'
    )
)"""
        self.assertEqual(expected, result)


    def test_reprIndices(self):
        data = [6, 16]
        indices = streaming.Indices.fromDict(data)
        result = repr(indices)
        expected = """Indices(start=6, end=16)"""
        self.assertEqual(expected, result)


    def test_reprEntities(self):
        data = {
            "urls": [
                {
                    "url": "http://t.co/0JG5Mcq",
                    "display_url": u"blog.twitter.com/2011/05/twitte\xe2",
                    "expanded_url": "http://blog.twitter.com/2011/05/twitter-for-mac-update.html",
                    "indices": [
                        84,
                        103
                    ]
                }
            ],
        }
        entities = streaming.Entities.fromDict(data)
        result = repr(entities)
        expected = """Entities(
    urls=[
        URL(
            display_url=u'blog.twitter.com/2011/05/twitte\\xe2',
            expanded_url='http://blog.twitter.com/2011/05/twitter-for-mac-update.html',
            indices=Indices(start=84, end=103),
            url='http://t.co/0JG5Mcq'
        )
    ]
)"""
        self.assertEqual(expected, result)


class TestableTwitterStream(streaming.TwitterStream):

    def __init__(self, _clock, *args, **kwargs):
        self._clock = _clock
        streaming.TwitterStream.__init__(self, *args, **kwargs)


    def callLater(self, *args, **kwargs):
        return self._clock.callLater(*args, **kwargs)



class TwitterStreamTest(unittest.TestCase):
    """
    Tests for L{streaming.TwitterStream}.
    """

    def setUp(self):
        self.objects = []
        self.transport = proto_helpers.StringTransport()
        self.clock = task.Clock()
        self.protocol = TestableTwitterStream(self.clock, self.objects.append)
        self.protocol.makeConnection(self.transport)


    def tearDown(self):
        self.protocol.setTimeout(None)


    def test_status(self):
        """
        Status objects become L{streaming.Status} objects passed to callback.
        """
        data = """{"text": "Test status"}\n\r"""
        self.protocol.datagramReceived(data)
        self.assertEquals(1, len(self.objects))
        self.assertIsInstance(self.objects[-1], streaming.Status)


    def test_unknownObject(self):
        """
        Unknown objects are ignored.
        """
        data = """{"something": "Some Value"}\n\r"""
        self.protocol.datagramReceived(data)
        self.assertEquals(0, len(self.objects))


    def test_badJSON(self):
        """
        Datagrams with invalid JSON are logged and ignored.
        """
        data = """blah\n\r"""
        self.protocol.datagramReceived(data)
        self.assertEquals(0, len(self.objects))
        loggedErrors = self.flushLoggedErrors(ValueError)
        self.assertEquals(1, len(loggedErrors))


    def test_closedResponseDone(self):
        """
        When the connection is done, the deferred is fired.
        """
        self.protocol.connectionLost(failure.Failure(ResponseDone()))
        return self.protocol.deferred


    def test_closedPotentialDataLoss(self):
        """
        When the connection is done, the deferred is fired.
        """
        self.protocol.connectionLost(failure.Failure(PotentialDataLoss()))
        return self.protocol.deferred


    def test_closedOther(self):
        """
        When the connection is done, the deferred is fired.
        """
        self.protocol.connectionLost(failure.Failure(Exception()))
        self.assertFailure(self.protocol.deferred, Exception)


    def test_closedNoTimeout(self):
        """
        When the connection is done, there is no timeout.
        """
        self.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.assertEquals(None, self.protocol.timeOut)
        return self.protocol.deferred


    def test_timeout(self):
        """
        When the timeout is reached, the transport should stop producing.

        A real transport would call connectionLost, but we don't need to test
        that here.
        """
        self.clock.advance(59)
        self.assertEquals('producing', self.transport.producerState)
        self.clock.advance(1)
        self.assertEquals('stopped', self.transport.producerState)


    def test_timeoutPostponedOnData(self):
        """
        When the timeout is reached, the transport stops producing.

        A real transport would call connectionLost, but we don't need to test
        that here.
        """
        self.clock.advance(20)
        data = """{"text": "Test status"}\n\r"""
        self.protocol.dataReceived(data)
        self.clock.advance(40)
        self.assertEquals('producing', self.transport.producerState,
                          "Unexpected timeout")
        self.clock.advance(20)
        self.assertEquals('stopped', self.transport.producerState)

########NEW FILE########
__FILENAME__ = test_twitter
# Copyright (c) 2010-2012  Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Tests for L{twittytwister.twitter}.
"""

from twisted.internet import defer, task
from twisted.internet.error import ConnectError
from twisted.python import failure
from twisted.trial import unittest
from twisted.web import error as http_error
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss

from twittytwister import twitter, streaming

DELAY_INITIAL = twitter.TwitterMonitor.backOffs[None]['initial']

class TwitterFeedTest(unittest.TestCase):
    """
    Tests for L{twitter.TwitterFeed):
    """

    def setUp(self):
        self.feed = twitter.TwitterFeed()
        self.calls = []


    def _rtfeed(self, url, delegate, args):
        self.calls.append((url, delegate, args))


    def test_user(self):
        """
        C{user} opens a Twitter User Stream.
        """
        self.patch(self.feed, '_rtfeed', self._rtfeed)
        self.feed.user(None)
        self.assertEqual(1, len(self.calls))
        url, delegate, args = self.calls[-1]
        self.assertEqual('https://userstream.twitter.com/1.1/user.json', url)
        self.assertIdentical(None, delegate)
        self.assertIdentical(None, args)


    def test_userArgs(self):
        """
        The second argument to C{user} is a dict passed on as arguments.
        """
        self.patch(self.feed, '_rtfeed', self._rtfeed)
        self.feed.user(None, {'replies': 'all'})
        url, delegate, args = self.calls[-1]
        self.assertEqual({'replies': 'all'}, args)


    def test_site(self):
        """
        C{site} opens a Twitter Site Stream.
        """
        self.patch(self.feed, '_rtfeed', self._rtfeed)
        self.feed.site(None, {'follow': '6253282'})
        self.assertEqual(1, len(self.calls))
        url, delegate, args = self.calls[-1]
        self.assertEqual('https://sitestream.twitter.com/1.1/site.json', url)
        self.assertIdentical(None, delegate)
        self.assertEqual({'follow': '6253282'}, args)



class FakeTwitterProtocol(object):
    """
    A testing Protocol that behaves like TwitterProtocol.
    """

    def __init__(self):
        self.deferred = defer.Deferred()
        self.transport = self
        self.stopCalled = False


    def stopProducing(self):
        """
        Record that this protocol was asked to stop producing.
        """
        self.stopCalled = True


    def connectionLost(self, reason):
        """
        Lose the connection with reason.
        """
        if reason.check(ResponseDone, PotentialDataLoss):
            self.deferred.callback(None)
        else:
            self.deferred.errback(reason)



class FakeTwitterAPI(object):
    """
    Fake TwitterAPI that provides a filter method for testing.
    """

    protocol = None
    deferred = None

    def __init__(self):
        self.filterCalls = []
        self.delegate = None


    def filter(self, delegate, args=None):
        """
        Returns the deferred, which can be fired in tests at will.
        """
        self.delegate = delegate
        self.filterCalls.append(args)
        self.deferred = defer.Deferred()
        return self.deferred


    def connected(self):
        """
        Connect using FakeTwitterProtocol and callback our deferred.
        """
        self.protocol = FakeTwitterProtocol()
        self.deferred.callback(self.protocol)


    def connectFail(self, reason):
        """
        Fail the connection attempt.
        """
        self.deferred.errback(reason)



class TwitterMonitorTest(unittest.TestCase):
    """
    Tests for L{twitter.TwitterMonitor}.
    """

    def setUp(self):
        """
        Called at the beginning of each test.

        Set up a L{twitter.TwitterMonitor} with testable API, a clock to
        test delayed calls and make the test class the delegate.
        """
        self.entries = []
        self.clock = task.Clock()
        self.api = FakeTwitterAPI()
        self.monitor = twitter.TwitterMonitor(self.api.filter,
                                              delegate=None,
                                              reactor=self.clock)
        self.monitor.noisy = True
        self.connects = None


    def tearDown(self):
        self.assertEquals(0, len(self.clock.calls))


    def onEntry(self, entry):
        self.entries.append(entry)


    def setUpState(self, state):
        """
        Set up the monitor to a given state, to simplify tests.
        """
        # Initial state is 'stopped'.
        if state == 'stopped':
            return

        # Starting the service with no delegate results in state 'idle'.
        self.monitor.startService()
        if state == 'idle':
            return

        # Setting up a delegate causes transition to state 'connecting'.
        if not self.monitor.delegate:
            self.monitor.delegate = self.onEntry
            self.monitor.connect()
        self.clock.advance(0)
        if state == 'connecting':
            return

        # If we want to reach aborting, force a reconnect while connecting.
        if state == 'aborting':
            self.monitor.connect(forceReconnect=True)
            return

        # Connecting the API causes a transition to state 'connected'
        self.api.connected()
        if state == 'connected':
            return

        # Forcing a reconnect while connected drops the connection
        self.monitor.connect(forceReconnect=True)
        if state == 'disconnecting':
            return

        # Actually lose the connection
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        if state == 'disconnected':
            return

        # When disconnected, the next state is usually 'waiting'
        if state == 'waiting':
            return


    def setFilters(self, *args, **kwargs):
        """
        Wraps L{twitter.TwitterMonitor.setFilters} to track connects.
        """
        self.patch(self.monitor, 'connect', self.connect)
        self.monitor.setFilters(*args, **kwargs)


    def connect(self, forceReconnect=False):
        """
        Called on each connection attempt via the L{setFilters}.
        """
        self.connects = forceReconnect


    def test_init(self):
        """
        Set up monitor without passing a custom reactor.
        """
        self.monitor = twitter.TwitterMonitor(self.api,
                                              delegate=self.onEntry)


    def test_initialStateStopped(self):
        """
        When the service has not been started, the state is 'stopped'.
        """
        self.setUpState('stopped')

        self.assertEqual(0, len(self.api.filterCalls))


    def test_unknownState(self):
        """
        Cannot transition to an unknown state.
        """
        self.assertRaises(ValueError, self.monitor._toState, "unknown")


    def test_startServiceNoDelegate(self):
        """
        When the service is started without delegate, go to 'idle'.
        """
        self.monitor.startService()
        self.clock.advance(0)
        self.assertEqual(0, len(self.api.filterCalls))


    def test_startServiceWithDelegate(self):
        """
        When the service is started with filters, initiate connection.
        """
        self.monitor.delegate = self.onEntry
        self.monitor.startService()
        self.clock.advance(0)
        self.assertEqual(1, len(self.api.filterCalls))


    def test_stopServiceConnected(self):
        """
        Stopping the service while waiting to reconnect should abort.
        """
        self.setUpState('connected')

        # Stop the service.
        self.monitor.stopService()

        # Actually lose the connection
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))

        # No reconnect should be attempted.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(1, len(self.api.filterCalls))


    def test_stopServiceWaiting(self):
        """
        Stopping the service while waiting to reconnect should abort.
        """
        self.setUpState('waiting')

        # Stop the service.
        self.monitor.stopService()

        # No reconnect should be attempted.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(1, len(self.api.filterCalls))


    def test_stopServiceWaitingAndStarting(self):
        """
        Stopping and starting service while waiting, should cause 1 connect.
        """
        self.setUpState('waiting')

        # Stop the service.
        self.monitor.stopService()

        # Start the service before the initial reconnect delay expires
        self.clock.advance(DELAY_INITIAL - 1)
        self.monitor.startService()
        self.clock.advance(0)
        self.assertEqual(2, len(self.api.filterCalls))

        # After the initial reconnect delay, don't connect again!
        self.clock.advance(1)
        self.assertEqual(2, len(self.api.filterCalls), 'Extra connect')


    def test_stopServiceAfterReconnect(self):
        """
        Stopping the service after waiting is fine.
        """
        self.setUpState('waiting')

        # No reconnect should be attempted.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(2, len(self.api.filterCalls))

        # Stop the service.
        self.monitor.stopService()
        self.clock.advance(0)


    def test_connectStopped(self):
        """
        Attempting to connect while the service is not running should fail.

        The initial state is stopped, so don't connect.
        """
        self.setUpState('stopped')

        self.assertRaises(twitter.Error, self.monitor.connect)

        self.clock.advance(0)
        self.assertEqual(0, len(self.api.filterCalls))


    def test_connectIdle(self):
        """
        Attempting to connect while idle should succeed.
        """
        self.setUpState('idle')

        self.monitor.delegate = self.onEntry
        self.monitor.connect()
        self.clock.advance(0)

        self.assertEqual(1, len(self.api.filterCalls))


    def test_connectIdleNoDelegate(self):
        """
        Don't connect without delegate.
        """
        self.setUpState('idle')

        # Unset the delegate
        self.monitor.delegate = None

        # Try to connect.
        self.assertRaises(twitter.Error, self.monitor.connect)

        self.clock.advance(0)
        self.assertEqual(0, len(self.api.filterCalls), 'Extra connect')


    def test_connectConnecting(self):
        """
        Don't connect while connecting.
        """
        self.setUpState('connecting')

        # Try to connect.
        self.assertRaises(twitter.Error, self.monitor.connect)

        self.clock.advance(0)
        self.assertEqual(1, len(self.api.filterCalls), 'Extra connect')


    def test_connectConnectingReconnect(self):
        """
        Don't connect while connecting.
        """
        self.setUpState('connecting')

        # Try to connect.
        self.monitor.connect(forceReconnect=True)

        # As we haven't connected yet, we cannot drop the connection yet,
        # and no reconnect should have taken place.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(1, len(self.api.filterCalls))

        # The initial connection is now established.
        self.api.connected()

        # A disconnect occurs right away.
        self.clock.advance(0)
        self.assertTrue(self.api.protocol.stopCalled)
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.clock.advance(0)

        # Now the reconnect occurs, wait for delayed calls.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(2, len(self.api.filterCalls))


    def test_connectConnected(self):
        """
        Don't connect while connecting.
        """
        self.setUpState('connected')

        # Try to connect.
        self.assertRaises(twitter.Error, self.monitor.connect)
        self.clock.advance(0)
        self.assertEqual(1, len(self.api.filterCalls), 'Extra connect')


    def test_connectConnectedReconnect(self):
        """
        Reconnect while connected.
        """
        self.setUpState('connected')

        # Try to connect.
        self.monitor.connect(forceReconnect=True)

        # As we haven't connected yet, we cannot drop the connection yet,
        # and no reconnect should have taken place.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(1, len(self.api.filterCalls))

        # A disconnect occurs right away.
        self.clock.advance(0)
        self.assertTrue(self.api.protocol.stopCalled)
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.clock.advance(0)

        # Now the reconnect occurs, wait for delayed calls.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(2, len(self.api.filterCalls))


    def test_connectDisconnected(self):
        """
        Connect immediately if disconnected.
        """
        self.setUpState('disconnected')

        # Try to connect.
        self.monitor.connect()
        self.clock.advance(0)
        self.assertEqual(2, len(self.api.filterCalls), 'Missing connect')

        # Now the reconnect occurs, wait for delayed calls.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(2, len(self.api.filterCalls), 'Extra connect')


    def test_connectDisconnectedNoDelegate(self):
        """
        Don't connect without delegate if disconnected.
        """
        self.setUpState('disconnected')

        # Unset the delegate
        self.monitor.delegate = None

        # Try to connect.
        self.assertRaises(twitter.Error, self.monitor.connect)

        # Now a reconnect should not occur, wait for erroneous delayed calls.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(1, len(self.api.filterCalls), 'Extra connect')


    def test_connectDisconnectedReconnectImmediately(self):
        """
        Reconnect immediately upon disconnect, if delay is 0.
        """
        import copy
        self.monitor.backOffs = copy.deepcopy(self.monitor.backOffs)
        self.monitor.backOffs[None]['initial'] = 0
        self.setUpState('disconnected')

        self.assertEqual(2, len(self.api.filterCalls), 'Missing connect')


    def test_connectAborting(self):
        """
        Don't connect while aborting.
        """
        self.setUpState('aborting')

        # Try to connect.
        self.assertRaises(twitter.Error, self.monitor.connect)

        self.clock.advance(0)
        self.assertEqual(1, len(self.api.filterCalls), 'Extra connect')


    def test_connectDisconnecting(self):
        """
        Don't connect while disconnecting.
        """
        self.setUpState('disconnecting')

        # The stream is being disconnected, cannot connect explicitly
        self.assertRaises(twitter.Error, self.monitor.connect)

        self.clock.advance(0)
        self.assertEqual(1, len(self.api.filterCalls), 'Extra connect')

        # Lose the connection.
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.clock.advance(0)

        # Now the reconnect occurs, wait for delayed calls.
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(2, len(self.api.filterCalls))


    def test_connectConnectError(self):
        """
        Connect errors cause reconnects after a delay with back-offs.
        """
        self.setUpState('connecting')

        callCount = 1
        for delay in (0.25, 0.5, 1, 2, 4, 8, 16, 16):
            # Fail the connection attempt with a ConnectError
            self.api.connectFail(ConnectError())
            self.clock.advance(0)

            # The error is logged
            self.assertEquals(1, len(self.flushLoggedErrors(ConnectError)))

            # A reconnect is done after the delay
            self.clock.advance(delay)
            callCount += 1
            self.assertEqual(callCount, len(self.api.filterCalls))


    def test_connectHTTPError(self):
        """
        HTTP errors cause reconnects after a delay with back-offs.
        """
        self.setUpState('connecting')

        callCount = 1
        for delay in (10, 20, 40, 80, 160, 240, 240):
            # Fail the connection attempt with a ConnectError
            self.api.connectFail(http_error.Error(401))
            self.clock.advance(0)

            # The error is logged
            self.assertEquals(1, len(self.flushLoggedErrors(http_error.Error)))

            # A reconnect is done after the delay
            self.clock.advance(delay)
            callCount += 1
            self.assertEqual(callCount, len(self.api.filterCalls))


    def test_connectUnknownError(self):
        """
        Unknown errors while connecting are logged, transition to idle state.
        """
        self.setUpState('connecting')

        class UnknownError(Exception):
            pass

        callCount = 1
        for delay in (10, 20, 40, 80, 160, 240, 240):
            # Fail the connection attempt with a ConnectError
            self.api.connectFail(UnknownError())
            self.clock.advance(0)

            # The error is logged
            self.assertEquals(1, len(self.flushLoggedErrors(UnknownError)))

            # A reconnect is done after the delay
            self.clock.advance(delay)
            callCount += 1
            self.assertEqual(callCount, len(self.api.filterCalls))


    def test_connectionLostDone(self):
        """
        When the connection is closed while connected, attempt reconnect.
        """
        self.setUpState('connected')

        # Connection closed by other party.
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.clock.advance(0)

        # A reconnect is attempted, but not before the back off delay.
        self.assertEqual(1, len(self.api.filterCalls))
        self.clock.advance(1)
        self.assertEqual(1, len(self.api.filterCalls))
        self.clock.advance(DELAY_INITIAL - 1)
        self.assertEqual(2, len(self.api.filterCalls))


    def test_connectionLostDoneAfterError(self):
        """
        Reconnect with initial interval after succesful reconnect.
        """
        self.setUpState('connecting')

        # First connect fails.
        self.api.connectFail(ConnectError())
        self.flushLoggedErrors(ConnectError)

        # A reconnect is attempted
        self.clock.advance(0.25)
        self.assertEqual(2, len(self.api.filterCalls))

        # Reconnect succeeds.
        self.api.connected()

        # Connection closed by other party.
        self.api.protocol.connectionLost(failure.Failure(ResponseDone()))
        self.clock.advance(0)

        # A reconnect is attempted, but not before the back off delay.
        self.assertEqual(2, len(self.api.filterCalls))
        self.clock.advance(DELAY_INITIAL)
        self.assertEqual(3, len(self.api.filterCalls))

        # Second reconnect fails.
        self.api.connectFail(ConnectError())
        self.flushLoggedErrors(ConnectError)

        # A reconnect is attempted, but not before the same back off delay.
        self.assertEqual(3, len(self.api.filterCalls))
        self.clock.advance(0.25)
        self.assertEqual(4, len(self.api.filterCalls))


    def test_connectionLostFailure(self):
        """
        When the connection is closed with an error, attempt reconnect.
        """
        self.setUpState('connected')

        class Error(Exception):
            pass

        # Connection closed by other party.
        self.api.protocol.connectionLost(failure.Failure(Error()))
        self.clock.advance(0)

        # A reconnect is attempted, but not before the back off delay.
        self.assertEqual(1, len(self.api.filterCalls))
        self.clock.advance(1)
        self.assertEqual(1, len(self.api.filterCalls))
        self.clock.advance(self.monitor.backOffs['other']['initial'] - 1)
        self.assertEqual(2, len(self.api.filterCalls))

        self.assertEqual(1, len(self.flushLoggedErrors(Error)))


    def test_onEntry(self):
        """
        Received entries are passed to the delegate.
        """
        self.setUpState('connected')
        self.clock.advance(0)

        status = streaming.Status.fromDict({'text': u'Hello!'})
        self.api.delegate(status)
        self.assertEqual([status], self.entries)


    def test_onEntryNoDelegate(self):
        """
        If there is no (longer) a delegate, silently drop the entry.
        """
        self.setUpState('connected')
        self.clock.advance(0)

        self.monitor.delegate = None

        status = streaming.Status.fromDict({'text': u'Hello!'})
        self.api.delegate(status)


    def test_onEntryError(self):
        """
        If the delegate's onEntry raises an exception, log it and go on.
        """
        class Error(Exception):
            pass

        def onEntry(entry):
            raise Error()

        self.monitor.delegate = onEntry
        self.setUpState('connected')
        self.clock.advance(0)

        status = streaming.Status.fromDict({'text': u'Hello!'})
        self.api.delegate(status)

        self.assertEqual(1, len(self.flushLoggedErrors(Error)))

########NEW FILE########
__FILENAME__ = twitter
# -*- test-case-name: twittytwister.test.test_streaming -*-
#
# Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
# Copyright (c) 2009  Kevin Dunglas <dunglas@gmail.com>
# Copyright (c) 2010-2012  Ralph Meijer <ralphm@ik.nu>
# See LICENSE.txt for details

"""
Twisted Twitter interface.
"""

import base64
import urllib
import mimetypes
import mimetools
import logging

from oauth import oauth

from twisted.application import service
from twisted.internet import defer, reactor, endpoints
from twisted.internet import error as ierror
from twisted.python import failure, log
from twisted.web import client, error, http_headers

from twittytwister import streaming, txml

SIGNATURE_METHOD = oauth.OAuthSignatureMethod_HMAC_SHA1()

BASE_URL="https://api.twitter.com/1"
SEARCH_URL="http://search.twitter.com/search.atom"


logger = logging.getLogger('twittytwister.twitter')


##### ugly hack to work around a bug on HTTPDownloader on Twisted 8.2.0 (fixed on 9.0.0)
def install_twisted_fix():
    orig_method = client.HTTPDownloader.gotHeaders
    def gotHeaders(self, headers):
        client.HTTPClientFactory.gotHeaders(self, headers)
        orig_method(self, headers)
    client.HTTPDownloader.gotHeaders = gotHeaders

def buggy_twisted():
    o = client.HTTPDownloader('http://dummy-url/foo', None)
    client.HTTPDownloader.gotHeaders(o, {})
    if o.response_headers is None:
        return True
    return False

if buggy_twisted():
    install_twisted_fix()

##### end of hack


class TwitterClientInfo:
    def __init__ (self, name, version = None, url = None):
        self.name = name
        self.version = version
        self.url = url

    def get_headers (self):
        headers = [
                ('X-Twitter-Client',self.name),
                ('X-Twitter-Client-Version',self.version),
                ('X-Twitter-Client-URL',self.url),
                ]
        return dict(filter(lambda x: x[1] != None, headers))

    def get_source (self):
        return self.name


def __downloadPage(factory, *args, **kwargs):
    """Start a HTTP download, returning a HTTPDownloader object"""

    # The Twisted API is weird:
    # 1) web.client.downloadPage() doesn't give us the HTTP headers
    # 2) there is no method that simply accepts a URL and gives you back
    #    a HTTPDownloader object

    #TODO: convert getPage() usage to something similar, too

    downloader = factory(*args, **kwargs)
    if downloader.scheme == 'https':
        from twisted.internet import ssl
        contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(downloader.host, downloader.port,
                           downloader, contextFactory)
    else:
        reactor.connectTCP(downloader.host, downloader.port,
                           downloader)
    return downloader

def downloadPage(url, file, timeout=0, **kwargs):
    c = __downloadPage(client.HTTPDownloader, url, file, **kwargs)
    # HTTPDownloader doesn't have the 'timeout' keyword parameter on
    # Twisted 8.2.0, so set it directly:
    if timeout:
        c.timeout = timeout
    return c

def getPage(url, *args, **kwargs):
    return __downloadPage(client.HTTPClientFactory, url, *args, **kwargs)

class Twitter(object):

    agent="twitty twister"

    def __init__(self, user=None, passwd=None,
        base_url=BASE_URL, search_url=SEARCH_URL,
                 consumer=None, token=None, signature_method=SIGNATURE_METHOD,client_info = None, timeout=0):

        self.base_url = base_url
        self.search_url = search_url

        self.use_auth = False
        self.use_oauth = False
        self.client_info = None
        self.timeout = timeout

        # rate-limit info:
        self.rate_limit_limit = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

        if user and passwd:
            self.use_auth = True
            self.username = user
            self.password = passwd

        if consumer and token:
            self.use_auth = True
            self.use_oauth = True
            self.consumer = consumer
            self.token = token
            self.signature_method = signature_method

        if client_info != None:
            self.client_info = client_info


    def __makeOAuthHeader(self, method, url, parameters={}, headers={}):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
            token=self.token, http_method=method, http_url=url, parameters=parameters)
        oauth_request.sign_request(self.signature_method, self.consumer, self.token)

        headers.update(oauth_request.to_header())
        return headers

    def __makeAuthHeader(self, headers={}):
        authorization = base64.encodestring('%s:%s'
            % (self.username, self.password))[:-1]
        headers['Authorization'] = "Basic %s" % authorization
        return headers

    def _makeAuthHeader(self, method, url, parameters={}, headers={}):
        if self.use_oauth:
            return self.__makeOAuthHeader(method, url, parameters, headers)
        else:
            return self.__makeAuthHeader(headers)

    def makeAuthHeader(self, method, url, parameters={}, headers={}):
        if self.use_auth:
            return self._makeAuthHeader(method, url, parameters, headers)
        else:
            return headers

    def _urlencode(self, h):
        rv = []
        for k,v in h.iteritems():
            rv.append('%s=%s' %
                (urllib.quote(k.encode("utf-8")),
                urllib.quote(v.encode("utf-8"))))
        return '&'.join(rv)

    def __encodeMultipart(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
        boundary = mimetools.choose_boundary()
        crlf = '\r\n'

        l = []
        for k, v in fields:
            l.append('--' + boundary)
            l.append('Content-Disposition: form-data; name="%s"' % k)
            l.append('')
            l.append(v)
        for (k, f, v) in files:
            l.append('--' + boundary)
            l.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (k, f))
            l.append('Content-Type: %s' % self.__getContentType(f))
            l.append('')
            l.append(v)
        l.append('--' + boundary + '--')
        l.append('')
        body = crlf.join(l)

        return boundary, body

    def gotHeaders(self, headers):
        logger.debug("hdrs: %r", headers)
        if headers is None:
            return

        def ratelimit_header(name):
            hdr = 'x-ratelimit-%s' % (name)
            field = 'rate_limit_%s' % (name)
            r = headers.get(hdr)
            if r is not None and len(r) > 0 and r[0]:
                v = int(r[0])
                setattr(self, field, v)
            else:
                return None

        ratelimit_header('limit')
        ratelimit_header('remaining')
        ratelimit_header('reset')

        logger.debug('hdrs end')


    def __getContentType(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    def __clientDefer(self, c):
        """Return a deferred for a HTTP client, after handling incoming headers"""
        def handle_headers(r):
            self.gotHeaders(c.response_headers)
            return r

        return c.deferred.addBoth(handle_headers)

    def __postMultipart(self, path, fields=(), files=()):
        url = self.base_url + path

        (boundary, body) = self.__encodeMultipart(fields, files)
        headers = {'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
            'Content-Length': str(len(body))
            }

        self._makeAuthHeader('POST', url, headers=headers)

        c = getPage(url, method='POST',
            agent=self.agent,
            postdata=body, headers=headers, timeout=self.timeout)
        return self.__clientDefer(c)

    #TODO: deprecate __post()?
    def __post(self, path, args={}):
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}

        url = self.base_url + path

        self._makeAuthHeader('POST', url, args, headers)

        if self.client_info != None:
            headers.update(self.client_info.get_headers())
            args['source'] = self.client_info.get_source()

        c = getPage(url, method='POST',
            agent=self.agent,
            postdata=self._urlencode(args), headers=headers, timeout=self.timeout)
        return self.__clientDefer(c)

    def __doDownloadPage(self, *args, **kwargs):
        """Works like client.downloadPage(), but handle incoming headers
        """
        logger.debug("download page: %r, %r", args, kwargs)

        return self.__clientDefer(downloadPage(*args, **kwargs))

    def __postPage(self, path, parser, args={}):
        url = self.base_url + path
        headers = self.makeAuthHeader('POST', url, args)

        if self.client_info != None:
            headers.update(self.client_info.get_headers())
            args['source'] = self.client_info.get_source()

        return self.__doDownloadPage(url, parser, method='POST',
            agent=self.agent,
            postdata=self._urlencode(args), headers=headers, timeout=self.timeout)

    def __downloadPage(self, path, parser, params=None):
        url = self.base_url + path

        headers = self.makeAuthHeader('GET', url, params)
        if params:
            url += '?' + self._urlencode(params)

        return self.__doDownloadPage(url, parser,
            agent=self.agent, headers=headers, timeout=self.timeout)

    def __get(self, path, delegate, params, parser_factory=txml.Feed, extra_args=None):
        parser = parser_factory(delegate, extra_args)
        return self.__downloadPage(path, parser, params)

    def verify_credentials(self, delegate=None):
        "Verify a user's credentials."
        parser = txml.Users(delegate)
        return self.__downloadPage('/account/verify_credentials.xml', parser)

    def __parsed_post(self, hdef, parser):
        deferred = defer.Deferred()
        hdef.addErrback(lambda e: deferred.errback(e))
        hdef.addCallback(lambda p: deferred.callback(parser(p)))
        return deferred

    def update(self, status, source=None, params={}):
        "Update your status.  Returns the ID of the new post."
        params = params.copy()
        params['status'] = status
        if source:
            params['source'] = source
        return self.__parsed_post(self.__post('/statuses/update.xml', params),
            txml.parseUpdateResponse)

    def retweet(self, id, delegate):
        """Retweet a post

        Returns the retweet status info back to the given delegate
        """
        parser = txml.Statuses(delegate)
        return self.__postPage('/statuses/retweet/%s.xml' % (id), parser)

    def friends(self, delegate, params={}, extra_args=None):
        """Get updates from friends.

        Calls the delgate once for each status object received."""
        return self.__get('/statuses/friends_timeline.xml', delegate, params,
            txml.Statuses, extra_args=extra_args)

    def home_timeline(self, delegate, params={}, extra_args=None):
        """Get updates from friends.

        Calls the delgate once for each status object received."""
        return self.__get('/statuses/home_timeline.xml', delegate, params,
            txml.Statuses, extra_args=extra_args)

    def mentions(self, delegate, params={}, extra_args=None):
        return self.__get('/statuses/mentions.xml', delegate, params,
            txml.Statuses, extra_args=extra_args)

    def user_timeline(self, delegate, user=None, params={}, extra_args=None):
        """Get the most recent updates for a user.

        If no user is specified, the statuses for the authenticating user are
        returned.

        See search for example of how results are returned."""
        if user:
            params['id'] = user
        return self.__get('/statuses/user_timeline.xml', delegate, params,
                          txml.Statuses, extra_args=extra_args)

    def list_timeline(self, delegate, user, list_name, params={},
            extra_args=None):
        return self.__get('/%s/lists/%s/statuses.xml' % (user, list_name),
                delegate, params, txml.Statuses, extra_args=extra_args)

    def public_timeline(self, delegate, params={}, extra_args=None):
        "Get the most recent public timeline."

        return self.__get('/statuses/public_timeline.atom', delegate, params,
                          extra_args=extra_args)

    def direct_messages(self, delegate, params={}, extra_args=None):
        """Get direct messages for the authenticating user.

        Search results are returned one message at a time a DirectMessage
        objects"""
        return self.__get('/direct_messages.xml', delegate, params,
                          txml.Direct, extra_args=extra_args)

    def send_direct_message(self, text, user=None, delegate=None, screen_name=None, user_id=None, params={}):
        """Send a direct message
        """
        params = params.copy()
        if user is not None:
            params['user'] = user
        if user_id is not None:
            params['user_id'] = user_id
        if screen_name is not None:
            params['screen_name'] = screen_name
        params['text'] = text
        parser = txml.Direct(delegate)
        return self.__postPage('/direct_messages/new.xml', parser, params)

    def replies(self, delegate, params={}, extra_args=None):
        """Get the most recent replies for the authenticating user.

        See search for example of how results are returned."""
        return self.__get('/statuses/replies.atom', delegate, params,
                          extra_args=extra_args)

    def follow(self, user):
        """Follow the given user.

        Returns no useful data."""
        return self.__post('/friendships/create/%s.xml' % user)

    def leave(self, user):
        """Stop following the given user.

        Returns no useful data."""
        return self.__post('/friendships/destroy/%s.xml' % user)

    def follow_user(self, user, delegate):
        """Follow the given user.

        Returns the user info back to the given delegate
        """
        parser = txml.Users(delegate)
        return self.__postPage('/friendships/create/%s.xml' % (user), parser)

    def unfollow_user(self, user, delegate):
        """Unfollow the given user.

        Returns the user info back to the given delegate
        """
        parser = txml.Users(delegate)
        return self.__postPage('/friendships/destroy/%s.xml' % (user), parser)

    def __paging_get(self, url, delegate, params, pager, page_delegate=None):
        def end_page(p):
            if page_delegate:
                page_delegate(p.next_cursor, p.previous_cursor)

        parser = pager.pagingParser(delegate, page_delegate=end_page)
        return self.__downloadPage(url, parser, params)

    def __nopaging_get(self, url, delegate, params, pager):
        parser = pager.noPagingParser(delegate)
        return self.__downloadPage(url, parser, params)

    def __get_maybe_paging(self, url, delegate, params, pager, extra_args=None, page_delegate=None):
        if extra_args is None:
            eargs = ()
        else:
            eargs = (extra_args,)

        def do_delegate(i):
            delegate(i, *eargs)

        if params.has_key('cursor'):
            return self.__paging_get(url, delegate, params, pager, page_delegate)
        else:
            return self.__nopaging_get(url, delegate, params, pager)


    def list_friends(self, delegate, user=None, params={}, extra_args=None, page_delegate=None):
        """Get the list of friends for a user.

        Calls the delegate with each user object found."""
        if user:
            url = '/statuses/friends/' + user + '.xml'
        else:
            url = '/statuses/friends.xml'

        return self.__get_maybe_paging(url, delegate, params, txml.PagedUserList, extra_args, page_delegate)

    def list_followers(self, delegate, user=None, params={}, extra_args=None, page_delegate=None):
        """Get the list of followers for a user.

        Calls the delegate with each user object found."""
        if user:
            url = '/statuses/followers/' + user + '.xml'
        else:
            url = '/statuses/followers.xml'

        return self.__get_maybe_paging(url, delegate, params, txml.PagedUserList, extra_args, page_delegate)

    def friends_ids(self, delegate, user, params={}, extra_args=None, page_delegate=None):
        return self.__get_maybe_paging('/friends/ids/%s.xml' % (user), delegate, params, txml.PagedIDList, extra_args, page_delegate)

    def followers_ids(self, delegate, user, params={}, extra_args=None, page_delegate=None):
        return self.__get_maybe_paging('/followers/ids/%s.xml' % (user), delegate, params, txml.PagedIDList, extra_args, page_delegate)

    def list_members(self, delegate, user, list_name, params={}, extra_args=None, page_delegate=None):
        return self.__get_maybe_paging('/%s/%s/members.xml' % (user, list_name), delegate, params, txml.PagedUserList, extra_args, page_delegate=page_delegate)

    def show_user(self, user):
        """Get the info for a specific user.

        Returns a delegate that will receive the user in a callback."""

        url = '/users/show/%s.xml' % (user)
        d = defer.Deferred()

        self.__downloadPage(url, txml.Users(lambda u: d.callback(u))) \
            .addErrback(lambda e: d.errback(e))

        return d

    def search(self, query, delegate, args=None, extra_args=None):
        """Perform a search query.

        Results are given one at a time to the delegate.  An example delegate
        may look like this:

        def exampleDelegate(entry):
            print entry.title"""
        if args is None:
            args = {}
        args['q'] = query
        return self.__doDownloadPage(self.search_url + '?' + self._urlencode(args),
            txml.Feed(delegate, extra_args), agent=self.agent)

    def block(self, user):
        """Block the given user.

        Returns no useful data."""
        return self.__post('/blocks/create/%s.xml' % user)

    def unblock(self, user):
        """Unblock the given user.

        Returns no useful data."""
        return self.__post('/blocks/destroy/%s.xml' % user)

    def update_profile_image(self, filename, image):
        """Update the profile image of an authenticated user.
        The image parameter must be raw data.

        Returns no useful data."""

        return self.__postMultipart('/account/update_profile_image.xml',
                                    files=(('image', filename, image),))



class TwitterFeed(Twitter):
    """
    Realtime feed handling class.

    Results are given one at a time to the delegate. An example delegate
    may look like this::

        def exampleDelegate(entry):
            print entry.text

    Several methods take an optional C{args} parameter with a dictionary
    of request arguments that are passed along in the request. See
    U{https://dev.twitter.com/docs/streaming-apis/parameters} for a
    description of the parameters and for which methods they apply.

    @cvar protocol: The protocol class to instantiate and deliver the response
        body to. Defaults to L{streaming.TwitterStream}.
    """

    protocol = streaming.TwitterStream

    def __init__(self, *args, **kwargs):
        self.proxy_username = None
        if "proxy_host" in kwargs:
            port = 80
            if "proxy_port" in kwargs:
                port = kwargs["proxy_port"] 
                del kwargs["proxy_port"]
            if "proxy_username" in kwargs:
                self.proxy_username = kwargs["proxy_username"] 
                del kwargs["proxy_username"]
            if "proxy_password" in kwargs:
                self.proxy_password = kwargs["proxy_password"] 
                del kwargs["proxy_password"]

            endpoint = endpoints.TCP4ClientEndpoint(reactor, kwargs["proxy_host"], port)
            self.agent = client.ProxyAgent(endpoint)
            del kwargs["proxy_host"]
        else:
            self.agent = client.Agent(reactor)

        Twitter.__init__(self, *args, **kwargs)


    def _rtfeed(self, url, delegate, args):
        def cb(response):
            if response.code == 200:
                protocol = self.protocol(delegate)
                response.deliverBody(protocol)
                return protocol
            else:
                raise error.Error(response.code, response.phrase)

        args = args or {}
        args['delimited'] = 'length'
        url += '?' + self._urlencode(args)
        authHeaders = self._makeAuthHeader("GET", url, args)
        rawHeaders = dict([(name, [value])
                           for name, value
                           in authHeaders.iteritems()])
        headers = http_headers.Headers(rawHeaders)
        print 'Fetching', url
        d = self.agent.request('GET', url, headers, None)
        d.addCallback(cb)
        return d

    def _makeAuthHeader(self, method, url, args):
        items = {}
        if self.proxy_username != None:
            proxyAuth = base64.b64encode('%s:%s' % (self.proxy_username, self.proxy_password))
            items['Proxy-Authorization'] = 'Basic ' + proxyAuth.strip()

        items.update(Twitter._makeAuthHeader(self, method, url, args))
        return items

    def sample(self, delegate, args=None):
        """
        Returns a random sample of all public statuses.

        The actual access level determines the portion of the firehose.
        """
        return self._rtfeed(
            'https://stream.twitter.com/1.1/statuses/sample.json',
            delegate,
            args)


    def spritzer(self, delegate, args=None):
        """
        Get the spritzer feed.

        The API method 'spritzer' is deprecated. This method is provided for
        backwards compatibility. Use L{sample} instead.
        """
        return self.sample(delegate, args)


    def gardenhose(self, delegate, args=None):
        """
        Get the gardenhose feed.

        The API method 'gardenhose' is deprecated. This method is provided for
        backwards compatibility. Use L{sample} instead.
        """
        return self.sample(delegate, args=None)


    def firehose(self, delegate, args=None):
        """
        Returns all public statuses.
        """
        return self._rtfeed(
            'https://stream.twitter.com/1.1/statuses/firehose.json',
            delegate,
            args)


    def filter(self, delegate, args=None):
        """
        Returns public statuses that match one or more filter predicates.
        """
        return self._rtfeed(
            'https://stream.twitter.com/1.1/statuses/filter.json',
            delegate,
            args)


    def follow(self, delegate, follow):
        """
        Returns public statuses from or in reply to a set of users.

        Note that the old API method 'follow' is deprecated. This method
        is backwards compatible and provides a shorthand to L{filter}. The
        actual allowed number of user IDs depends on the access level of the
        used account.
        """
        return self.filter(delegate, {'follow': ','.join(follow)})


    def birddog(self, delegate, follow):
        """
        Follow up to 200,000 users in realtime.

        The API method `birddog` is deprecated. This method is provided for
        backwards compatibility. Use L{follow} or L{filter} instead.
        """
        return self.follow(delegate, follow)


    def shadow(self, delegate, follow):
        """
        Follow up to 2,000 users in realtime.

        The API method `birddog` is deprecated. This method is provided for
        backwards compatibility. Use L{follow} or L{filter} instead.
        """
        return self.follow(delegate, follow, 'shadow')


    def track(self, delegate, terms):
        """
        Returns public statuses matching a set of keywords.

        Note that the old API method 'track' is deprecated. This method is
        backwards compatible and provides a shorthand to L{filter}. The actual
        allowed number of keywords in C{terms} depends on the access level of
        the used account.
        """
        return self.filter(delegate, {'track': ','.join(terms)})


    def user(self, delegate, args=None):
        """
        Return all statuses of the connecting user.

        This uses the User Stream API endpoint. Without arguments it returns
        all statuses of the user itself, in real-time.

        Depending on the arguments, it can also send the statuses of the
        accounts the user follows and/or all replies to accounts the user
        follows. On top of that, it takes the same arguments as L{filter} to
        also track certain keywords, follow additional accounts or filter by
        location.
        """
        return self._rtfeed(
            'https://userstream.twitter.com/1.1/user.json',
            delegate,
            args)


    def site(self, delegate, args):
        """
        Return all statuses of the specified users.

        This uses the Site Stream API endpoint. The users to follow are
        specified using the (mandatory) C{'follow'} argument in C{args}.
        Without additional arguments it returns all statuses of the specified
        users, in real-time.

        Depending on the arguments, it can also send the statuses of the
        accounts the users follow and/or all replies to accounts the users
        follow.
        """
        return self._rtfeed(
            'https://sitestream.twitter.com/1.1/site.json',
            delegate,
            args)



class Error(Exception):
    """
    Base error raised by L{TwitterMonitor.connect}.
    """



class ConnectError(Error):
    """
    Error raised while attempting to initiate a new connection.
    """



class NoConsumerError(Error):
    """
    The monitor has no consumer.
    """



class TwitterMonitor(service.Service):
    """
    Reconnecting Twitter monitor service.

    This service attempts to keep a connection by reconnecting if a connection
    is dropped or when explicitly requested through L{connect}. Be sure that
    the API parameters provided in L{args} have all required parameters before
    starting the service.

    @cvar noisy: Whether or not to log informational messages about
        reconnects.
    type noisy: C{bool}

    @type api: The Twitter API endpoint that is used to initiate connections.

    @ivar args: Arguments to the Streaming API request.
    @type args: C{dict}

    @ivar delegate: The consumer of incoming Twitter entries.

    @ivar protocol: Current protocol instance parsing incoming Twitter
        entries.
    @type protocol: L{TwitterStream}

    @ivar _delay: Current delay, in seconds.
    @type _delay: C{float}

    @ivar _state: Current state.

    @ivar _errorState: Current error state. One of C{None}, C{'http'},
        C{'connect'}, C{'other'}.

    @ivar _reconnectDelayedCall: Current pending reconnect call.
    @type _reconnectDelayedCall: {twitter.internet.base.DelayedCall}

    @cvar backOffs: Configuration of back-off strategies for the various
        error states (see L{_errorState}). The value is a dictionary with
        keys C{'initial'}, C{'max'} and {'factor'} to represent the initial
        and maximum backoff delay (both in seconds), and the multiplication
        factor on each attempt, respectively. The key C{'errorTypes'} key
        holds a set of exceptions to match failures against.
    @type backOffs: C{dict}

    """
    noisy = False

    protocol = None

    _delay = None
    _state = None
    _errorState = None
    _reconnectDelayedCall = None

    backOffs = {
            # Back-off settings from clean disconnects
            None: {
                'initial': 5,
                'max': float('inf'), # No limit,
                'factor': 1, # No increase
                },
            # Back-off settings for HTTP errors
            'http': {
                'errorTypes': (error.Error,),
                'initial': 10,
                'max': 240,
                'factor': 2,
                },
            # Back-off settings for network level connect errors
            'network': {
                'errorTypes': (ierror.ConnectError,
                               ierror.TimeoutError,
                               ierror.ConnectionClosed,
                               ierror.DNSLookupError,
                               ),
                'initial': 0.25,
                'max': 16,
                'factor': 2,
                },
            # Back-off settings for other, non-specific errors.
            'other': {
                'initial': 10,
                'max': 240,
                'factor': 2,
                },
            }

    def __init__(self, api, delegate, args=None, reactor=None):
        """
        Initialize the monitor.

        This sets the initial state to C{'stopped'}.

        @param api: The Twitter API endpoint that is used to initiate
            connections. E.g. L{twittytwister.twitter.TwitterFeed.filter}.

        @param delegate: The consumer of received Twitter entries.
            This callable will be called with a L{Status} instances as they
            are received.

        @param args: Initial arguments to the API.
        @type args: C{dict}
        """
        self.api = api
        self.delegate = delegate
        self.args = args
        if reactor is None:
            from twisted.internet import reactor
        self.reactor = reactor
        self._state = 'stopped'


    def startService(self):
        """
        Start the service.

        This causes a transition to the C{'idle'} state, and then calls
        L{connect} to attempt an initial conection.
        """
        service.Service.startService(self)
        self._toState('idle')

        try:
            self.connect()
        except NoConsumerError:
            pass


    def stopService(self):
        """
        Stop the service.

        This causes a transition to the C{'stopped'} state.
        """
        service.Service.stopService(self)
        self._toState('stopped')


    def connect(self, forceReconnect=False):
        """
        Check current conditions and initiate connection if possible.

        This is called to check preconditions for starting a new connection,
        and initating the connection itself.

        If the service is not running, this will do nothing.

        @param forceReconnect: Drop an existing connection to reconnnect.
        @type forceReconnect: C{False}

        @raises L{ConnectError}: When a connection (attempt) is already in
            progress, unless C{forceReconnect} is set.

        @raises L{NoConsumerError}: When there is no consumer for incoming
        tweets. No further connection attempts will be made, unless L{connect}
        is called again.
        """
        if self._state == 'stopped':
            raise Error("This service is not running. Not connecting.")
        if self._state == 'connected':
            if forceReconnect:
                self._toState('disconnecting')
                return True
            else:
                raise ConnectError("Already connected.")
        elif self._state == 'aborting':
            raise ConnectError("Aborting connection in progress.")
        elif self._state == 'disconnecting':
            raise ConnectError("Disconnect in progress.")
        elif self._state == 'connecting':
            if forceReconnect:
                self._toState('aborting')
                return True
            else:
                raise ConnectError("Connect in progress.")

        if self.delegate is None:
            if self._state != 'idle':
                self._toState('idle')
            raise NoConsumerError()

        if self._state == 'waiting':
            if self._reconnectDelayedCall.called:
                self._reconnectDelayedCall = None
                pass
            else:
                self._reconnectDelayedCall.reset(0)
                return True

        self._toState('connecting')
        return True


    def loseConnection(self):
        """
        Forcibly close the current connection.
        """
        if self.protocol:
            self.protocol.transport.stopProducing()


    def makeConnection(self, protocol):
        """
        Called when the connection has been established.

        This method is called when an HTTP 200 response has been received,
        with the protocol that decodes the individual Twitter stream elements.
        That protocol will call the consumer for all Twitter entries received.

        The protocol, stored in L{protocol}, has a deferred that fires when
        the connection is closed, causing a transition to the
        C{'disconnected'} state.

        @param protocol: The Twitter stream protocol.
        @type protocol: L{TwitterStream}
        """
        self._errorState = None

        def cb(result):
            self.protocol = None
            if self._state == 'stopped':
                # Don't transition to any other state. We are stopped.
                pass
            else:
                if isinstance(result, failure.Failure):
                    reason = result
                else:
                    reason = None
                self._toState('disconnected', reason)

        self.protocol = protocol
        d = protocol.deferred
        d.addBoth(cb)


    def _reconnect(self, errorState):
        """
        Attempt to reconnect.

        If the current back-off delay is 0, L{connect} is called. Otherwise,
        it will cause a transition to the C{'waiting'} state, ultimately
        causing a call to L{connect} when the delay expires.
        """
        def connect():
            if self.noisy:
                log.msg("Reconnecting now.")
            self.connect()

        backOff = self.backOffs[errorState]

        if self._errorState != errorState or self._delay is None:
            self._errorState = errorState
            self._delay = backOff['initial']
        else:
            self._delay = min(backOff['max'], self._delay * backOff['factor'])

        if self._delay == 0:
            connect()
        else:
            self._reconnectDelayedCall = self.reactor.callLater(self._delay,
                                                                connect)
            self._toState('waiting')


    def _toState(self, state, *args, **kwargs):
        """
        Transition to the next state.

        @param state: Name of the next state.
        """
        try:
            method = getattr(self, '_state_%s' % state)
        except AttributeError:
            raise ValueError("No such state %r" % state)

        log.msg("%s: to state %r" % (self.__class__.__name__, state))
        self._state = state
        method(*args, **kwargs)


    def _state_stopped(self):
        """
        The service is not running.

        This is the initial state, and the state after L{stopService} was
        called. To get out of this state, call L{startService}. If there is a
        current connection, we disconnect.
        """
        if self._reconnectDelayedCall:
            self._reconnectDelayedCall.cancel()
            self._reconnectDelayedCall = None
        self.loseConnection()


    def _state_idle(self):
        """
        Idle state.

        In this state no connection attempts are made, and there are no
        automatic transitions from here: the service is at rest.

        Besides being the initial state when the service starts, it is reached
        when preconditions for connecting to Twitter have not been met (e.g.
        when is no consumer).

        This state can be left by calling by a new connection attempt
        though L{connect} or L{setFilters}, or by stopping the service.
        """
        if self._reconnectDelayedCall:
            self._reconnectDelayedCall.cancel()
            self._reconnectDelayedCall = None


    def _state_connecting(self):
        """
        A connection is being started.

        A succesful attempt results in the state C{'connected'} when the
        first response from Twitter has been received. Transitioning
        to the state C{'aborting'} will cause an immediate disconnect instead,
        by transitioning to C{'disconnecting'}.

        Errors will cause a transition to the C{'error'} state.
        """

        def responseReceived(protocol):
            self.makeConnection(protocol)
            if self._state == 'aborting':
                self._toState('disconnecting')
            else:
                self._toState('connected')

        def trapError(failure):
            self._toState('error', failure)

        def onEntry(entry):
            if self.delegate:
                try:
                    self.delegate(entry)
                except:
                    log.err()
            else:
                pass

        d = self.api(onEntry, self.args)
        d.addCallback(responseReceived)
        d.addErrback(trapError)


    def _state_connected(self):
        """
        A response was received over the new connection.

        The protocol passed to this state has a deferred that will fire
        when the connection has been dropped, which then causes a transition
        to the C{'disconnected'} state.
        """
        pass


    def _state_disconnecting(self):
        """
        A disconnect is in progress.
        """
        self.loseConnection()


    def _state_disconnected(self, reason):
        """
        The connection has been dropped.

        If there was a failure, A reconnect will be attempted.
        """
        if reason:
            self._toState('error', reason)
        else:
            self._reconnect(None)


    def _state_aborting(self):
        """
        The current connection attempt will be aborted.

        Unfortunately, there is no interface to drop the underlying
        TCP connection, so we have to wait until we are connected, or
        the connecting fails, until we can disconnect.
        """
        pass


    def _state_waiting(self):
        """
        Waiting for reconnect.

        Wait for L{delay} seconds until attempting a new connect.
        """
        if self.noisy:
            log.msg("Reconnecting in %0.2f seconds" % (self._delay,))


    def _state_error(self, reason):
        """
        The connection attempt resulted in an error.

        Attempt a reconnect with a back-off algorithm.
        """
        log.err(reason)

        def matchException(failure):
            for errorState, backOff in self.backOffs.iteritems():
                if 'errorTypes' not in backOff:
                    continue
                if failure.check(*backOff['errorTypes']):
                    return errorState

            return 'other'

        errorState = matchException(reason)
        self._reconnect(errorState)

# vim: set expandtab:

########NEW FILE########
__FILENAME__ = txml
from twisted.internet import error
from twisted.web import sux, microdom

import logging
logger = logging.getLogger('twittytwister.txml')

class NoopParser(object):
    def __init__(self, n):
        self.name = n
        self.done = False
    def gotTagStart(self, name, attrs):
        pass
    def gotTagEnd(self, name, data):
        self.done = (name == self.name)
    def value(self):
        # don't store anything on the object after parsing this
        return None

class BaseXMLHandler(object):

    def __init__(self, n, handler_dict={}, enter_unknown=False):
        self.done = False
        self.current_ob = None
        self.tag_name = n
        self.before_delegates = {}
        self.after_delegates = {}
        self.handler_dict = handler_dict
        self.enter_unknown = enter_unknown

        for p in self.handler_dict:
            self.__dict__[self.cleanup(p)] = None

    def setBeforeDelegate(self, name, fn):
        self.before_delegates[name] = fn

    def setAfterDelegate(self, name, fn):
        self.after_delegates[name] = fn

    def setDelegate(self, name, before=None, after=None):
        if before:
            self.setBeforeDelegate(name, before)
        if after:
            self.setAfterDelegate(name, after)

    def setPredefDelegate(self, type, before=None, after=None):
        self.setDelegate(type.MY_TAG, before, after)

    def setSubDelegates(self, namelist, before=None, after=None):
        """Set a delegate for a sub-sub-item, according to a list of names"""
        if len(namelist) > 1:
            def set_sub(i):
                i.setSubDelegates(namelist[1:], before, after)
            self.setBeforeDelegate(namelist[0], set_sub)
        elif len(namelist) == 1:
            self.setDelegate(namelist[0], before, after)

    def objectStarted(self, name, o):
        if name in self.before_delegates:
            self.before_delegates[name](o)

    def objectFinished(self, name, o):
        if name in self.after_delegates:
            self.after_delegates[name](o)

    def gotTagStart(self, name, attrs):
        if self.current_ob:
            self.current_ob.gotTagStart(name, attrs)
        elif name in self.handler_dict:
            self.current_ob = self.handler_dict[name](name)
            self.objectStarted(name, self.current_ob)
        elif not self.enter_unknown:
            logger.warning("Got unknown tag %s in %s", name, self.__class__)
            self.current_ob = NoopParser(name)

    def gotTagEnd(self, name, data):
        if self.current_ob:
            self.current_ob.gotTagEnd(name, data)
            if self.current_ob.done:
                v = self.current_ob.value()
                if v is not None:
                    self.__dict__[self.cleanup(name)] = v
                    self.objectFinished(name, v)
                self.current_ob = None
        elif name == self.tag_name:
            self.done = True
            del self.current_ob
            self.gotFinalData(data)

    def gotFinalData(self, data):
        pass

    def value(self):
        # by default, the resulting value is the handler object itself,
        # but XMLStringHandler overwrites this
        return self

    def cleanup(self, n):
        return n.replace(':', '_')

    def __repr__(self):
        return "{%s %s}" % (self.tag_name, self.__dict__)

class XMLStringHandler(BaseXMLHandler):
    """XML data handler for simple string fields"""
    def gotFinalData(self, data):
        self.data = data

    def value(self):
        return self.data


class PredefinedXMLHandler(BaseXMLHandler):
    MY_TAG = ''
    SIMPLE_PROPS = []
    COMPLEX_PROPS = []

    # if set to True, contents inside unknown tags
    # will be parsed as if the unknown tags weren't
    # around it.
    ENTER_UNKNOWN = False

    def __init__(self, n):
        handler_dict = dict([(p.MY_TAG,p) for p in self.COMPLEX_PROPS])
        handler_dict.update([(p,XMLStringHandler) for p in self.SIMPLE_PROPS])
        super(PredefinedXMLHandler, self).__init__(n, handler_dict, self.ENTER_UNKNOWN)

class Author(PredefinedXMLHandler):
    MY_TAG = 'author'
    SIMPLE_PROPS = [ 'name', 'uri' ]

class Entry(PredefinedXMLHandler):
    MY_TAG = 'entry'
    SIMPLE_PROPS = ['id', 'published', 'title', 'content', 'link', 'updated',
                    'twitter:source', 'twitter:lang']
    COMPLEX_PROPS = [Author]

    def gotTagStart(self, name, attrs):
        super(Entry, self).gotTagStart(name, attrs)
        if name == 'link':
            self.__dict__[attrs['rel']] = attrs['href']

    def gotTagEnd(self, name, data):
        super(Entry, self).gotTagEnd(name, data)
        if name == 'link':
            del self.link

class Status(PredefinedXMLHandler):
    MY_TAG = 'status'
    SIMPLE_PROPS = ['created_at', 'id', 'text', 'source', 'truncated',
        'in_reply_to_status_id', 'in_reply_to_screen_name',
        'in_reply_to_user_id', 'favorited', 'user_id', 'geo']
    COMPLEX_PROPS = []

class RetweetedStatus(Status):
    MY_TAG = 'retweeted_status'

# circular reference:
Status.COMPLEX_PROPS.append(RetweetedStatus)


class User(PredefinedXMLHandler):
    MY_TAG = 'user'
    SIMPLE_PROPS = ['id', 'name', 'screen_name', 'location', 'description',
        'profile_image_url', 'url', 'protected', 'followers_count',
        'profile_background_color', 'profile_text_color', 'profile_link_color',
        'profile_sidebar_fill_color', 'profile_sidebar_border_color',
        'friends_count', 'created_at', 'favourites_count', 'utc_offset',
        'time_zone', 'following', 'notifications', 'statuses_count',
        'profile_background_image_url', 'profile_background_tile', 'verified',
        'geo_enabled']
    COMPLEX_PROPS = [Status]

# circular reference:
Status.COMPLEX_PROPS.append(User)


class SenderUser(User):
    MY_TAG = 'sender'

class RecipientUser(User):
    MY_TAG = 'recipient'

class DirectMessage(PredefinedXMLHandler):
    MY_TAG = 'direct_message'
    SIMPLE_PROPS = ['id', 'sender_id', 'text', 'recipient_id', 'created_at',
        'sender_screen_name', 'recipient_screen_name']
    COMPLEX_PROPS = [SenderUser, RecipientUser]


### simple object list handlers:

class SimpleListHandler(BaseXMLHandler):
    """Class for simple handlers that work with just a single type of element"""
    ITEM_TYPE = Entry
    ITEM_TAG = None

    @classmethod
    def item_tag(klass):
        tag = klass.ITEM_TAG
        if tag is None:
            tag = klass.ITEM_TYPE.MY_TAG
        return tag

    def __init__(self, n):
        type = self.ITEM_TYPE
        tag = self.item_tag()
        super(SimpleListHandler, self).__init__(n,
                 handler_dict={tag:type}, enter_unknown=True)

class EntryList(SimpleListHandler):
    MY_TAG = 'feed'
    ITEM_TYPE = Entry

class UserList(SimpleListHandler):
    MY_TAG = 'users'
    ITEM_TYPE = User

class DirectMessageList(SimpleListHandler):
    MY_TAG = 'direct-messages'
    ITEM_TYPE = DirectMessage

class StatusList(SimpleListHandler):
    MY_TAG = 'statuses'
    ITEM_TYPE = Status

class IDList(SimpleListHandler):
    MY_TAG = 'ids'
    ITEM_TYPE = XMLStringHandler
    ITEM_TAG = 'id'


class ListPage(PredefinedXMLHandler):
    """Base class for the classes of paging items"""
    SIMPLE_PROPS = ['next_cursor', 'previous_cursor']

class UserListPage(ListPage):
    MY_TAG = 'users_list'
    COMPLEX_PROPS = [UserList]

class IDListPage(ListPage):
    MY_TAG = 'id_list'
    COMPLEX_PROPS = [IDList]


def topLevelXMLHandler(toplevel_type):
    """Used to create a BaseXMLHandler object that just handles a single type of tag"""
    return BaseXMLHandler(None,
                          handler_dict={toplevel_type.MY_TAG:toplevel_type},
                          enter_unknown=True)


class Parser(sux.XMLParser):

    """A file-like thingy that parses a friendfeed feed with SUX."""
    def __init__(self, handler):
        self.connectionMade()
        self.data=[]
        self.handler=handler

    def write(self, b):
        self.dataReceived(b)
    def close(self):
        self.connectionLost(error.ConnectionDone())
    def open(self):
        pass
    def read(self):
        return None

    # XML Callbacks
    def gotTagStart(self, name, attrs):
        self.data=[]
        self.handler.gotTagStart(name, attrs)

    def gotTagEnd(self, name):
        self.handler.gotTagEnd(name, ''.join(self.data).decode('utf8'))

    def gotText(self, data):
        self.data.append(data)

    def gotEntityReference(self, data):
        e = {'quot': '"', 'lt': '&lt;', 'gt': '&gt;', 'amp': '&amp;'}
        if e.has_key(data):
            self.data.append(e[data])
        elif data[0] == '#':
            self.data.append('&' + data + ';')
        else:
            logger.error("Unhandled entity reference: %s\n" % (data))


def listParser(list_type, delegate, extra_args=None):
    toplevel_type = list_type.ITEM_TYPE

    if extra_args:
        args = (extra_args,)
    else:
        args = ()

    def do_delegate(e):
        delegate(e, *args)

    handler = list_type(None)
    handler.setPredefDelegate(toplevel_type, after=do_delegate)
    return Parser(handler)

def simpleListFactory(list_type):
    """Used for simple parsers that support only one type of object"""
    def create(delegate, extra_args=None):
        """Create a Parser object for the specific tag type, on the fly"""
        return listParser(list_type, delegate, extra_args)
    return create



Feed     = simpleListFactory(EntryList)

Users    = simpleListFactory(UserList)

Direct   = simpleListFactory(DirectMessageList)

Statuses = simpleListFactory(StatusList)

HoseFeed = simpleListFactory(StatusList)


class Pager:
    """Able to create parsers that support paging, and parsers that don't"""
    def __init__(self, page_type, list_type):
        self.page_type = page_type
        self.list_type = list_type

    def pagingParser(self, delegate, page_delegate):
        item_tag = self.list_type.item_tag()
        root_handler = topLevelXMLHandler(self.page_type)
        root_handler.setPredefDelegate(self.page_type, after=page_delegate)
        root_handler.setSubDelegates([self.page_type.MY_TAG, self.list_type.MY_TAG, item_tag], after=delegate)
        return Parser(root_handler)

    def noPagingParser(self, delegate):
        item_tag = self.list_type.item_tag()
        root_handler = topLevelXMLHandler(self.list_type)
        root_handler.setSubDelegates([self.list_type.MY_TAG, item_tag], after=delegate)
        return Parser(root_handler)


PagedUserList = Pager(UserListPage, UserList)
PagedIDList = Pager(IDListPage, IDList)


def parseXML(xml):
    return microdom.parseXMLString(xml)

def parseUpdateResponse(xml):
    return parseXML(xml).getElementsByTagName("id")[0].firstChild().data

# vim: set expandtab:

########NEW FILE########
