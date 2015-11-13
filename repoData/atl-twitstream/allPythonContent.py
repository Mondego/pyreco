__FILENAME__ = fixreplies
#!/usr/bin/env python

import textwrap
import getpass
import re
import sys
import htmlentitydefs
from optparse import OptionGroup
try:
    import json as simplejson
except ImportError:
    import simplejson

import twitter
import twitstream

USAGE = """%prog [options] [user] <filter1> [<filter2> ...]

Grabs the users that are members of all of the filter sets.
The Streaming API 'follow' method gets each of the named users'
public status messages and the replies to each of them.

Note that there can be a heavy API load at the start, roughly
the number of pages times the number of predicates, so be 
careful of API limits!"""

def GetFavorites(api, 
                 user=None,
                 page=None):
    if user:
        url = 'http://twitter.com/favorites/%s.json' % user
    elif not user and not api._username:
        raise twitter.TwitterError("User must be specified if API is not authenticated.")
    else:
        url = 'http://twitter.com/favorites.json'
    parameters = {}
    if page:
        parameters['page'] = page
    json = api._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    api._CheckForTwitterError(data)
    return [twitter.Status.NewFromJsonDict(x) for x in data]


def GetFollowerIds(api, user_id=None, screen_name=None):
    '''Fetch an array of numeric IDs for every user the specified user is followed by. If called with no arguments,
     the results are follower IDs for the authenticated user.  Note that it is unlikely that there is ever a good reason
     to use both of the kwargs.

     Args:
       user_id: Optional.  Specfies the ID of the user for whom to return the followers list.
       screen_name:  Optional.  Specfies the screen name of the user for whom to return the followers list.

    '''
    url = 'http://twitter.com/followers/ids.json'
    parameters = {}
    if user_id:
        parameters['user_id'] = user_id
    if screen_name:
        parameters['screen_name'] = screen_name
    json = api._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    api._CheckForTwitterError(data)
    return data

def GetFriendIds(api, user_id=None, screen_name=None):
    '''Fetch an array of numeric IDs for every user the specified user is followed by. If called with no arguments,
     the results are follower IDs for the authenticated user.  Note that it is unlikely that there is ever a good reason
     to use both of the kwargs.

     Args:
       user_id: Optional.  Specfies the ID of the user for whom to return the followers list.
       screen_name:  Optional.  Specfies the screen name of the user for whom to return the followers list.

    '''
    url = 'http://twitter.com/friends/ids.json'
    parameters = {}
    if user_id:
        parameters['user_id'] = user_id
    elif screen_name:
        parameters['screen_name'] = screen_name
    else:
        raise twitter.TwitterError("One of user_id or screen_name must be specified.")
    json = api._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    api._CheckForTwitterError(data)
    return data

status_wrap = textwrap.TextWrapper(initial_indent='    ', subsequent_indent='    ')

class Formatter(object):
    
    url_pat = re.compile(r'\b(http://\S+[^\s\.\,\?\)\]\>])', re.IGNORECASE)
    ent_pat = re.compile("&#?\w+;")
    user_pat = re.compile(r'(@\w+)')
    wrap = textwrap.TextWrapper(initial_indent='    ', subsequent_indent='    ')
    
    def __init__(self, friends=[]):
        self.friend_pat = re.compile('(@%s)\\b' % "|@".join(friends), re.IGNORECASE)
        self.friends = friends
    
    def __call__(self, status):
        st = twitter.Status.NewFromJsonDict(status)
        if not st.user:
            if options.debug:
                print >> sys.stderr, status
            return
        if st.user.screen_name in self.friends:
            print '\033[94m\033[1m' + st.user.screen_name + '\033[0m:'
        else:
            print '\033[95m' + st.user.screen_name + ':\033[0m'            
        mess = self.ent_pat.sub(self.unescape, st.text)
        mess = self.wrap.fill(mess)
        mess = self.friend_pat.sub(self.bold, mess)
        mess = self.url_pat.sub(self.underline, mess)
        print mess + '\n'
    
    @staticmethod
    def bold(m):
        return '\033[1m' + m.group(1) + '\033[0m'
    
    @staticmethod    
    def underline(m):
        return '\033[4m' + m.group(1) + '\033[0m'
    
    @staticmethod
    def inverse(m):
        return '\033[7m' + m.group(1) + '\033[0m'
    
    @staticmethod
    def unescape(m):
        "http://effbot.org/zone/re-sub.htm#unescape-html"
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    

class Growler(object):
    def __init__(self, user=None, follow_usernames=[]):
        from Growl import GrowlNotifier, Image
        image = self.Image.imageFromPath('./twitter.bmp')
        self.growl = self.GrowlNotifier(applicationName="twitstream", 
            notifications=['Status', 'Self', 'Friend', 'Reply', 'Direct'],
            applicationIcon=image)
        self.growl.register()
        self.user = user
        self.follow_usernames = set(follow_usernames)
        
    def __call__(self, status):
        if 'user' not in status:
            if options.debug:
                print >> sys.stderr, status
            return
        if status['user']['screen_name'] == self.user:
            status_type = "Self"
        elif status['user']['screen_name'] in self.follow_usernames:
            status_type = "Friend"
        elif status['in_reply_to_status_id']:
            status_type = "Reply"
        else:
            status_type = "Status"
        self.growl.notify(status_type,
            "%s (%s)" % (status['user']['name'], status['user']['screen_name']),
            status['text'])

def filter_dict_with_set(a, b):
    if not a:
        return b
    else:
        c = a.copy()
        for y in a:
            if y not in b:
                del c[y]
        return c

if __name__ == '__main__':
    parser = twitstream.parser
    parser.add_option('-g', '--pages', help="Number of pages to check (default: 3)", type='int', default=3)
    parser.add_option('-m', '--maximum', help="Maximum number of users to track (default/max: 400)", type='int', default=400)
    parser.add_option('--growl', help="Send notifications to Growl (Mac only)", action='store_true', dest='growl')
    group = OptionGroup(parser, "filters",
                        "Combining more than one of the user filters takes the "
                        "intersection of the predicates.")
    group.add_option('--friends', help="Limit to friends", action="store_true", dest='friends')
    group.add_option('--followers', help="Limit to followers", action="store_true", dest='followers')
    group.add_option('--favorites', help="Limit to recent favorites", action="store_true", dest='favorites')
    group.add_option('--mention', help="Limit to those who mention the user", action='store_true', dest='mention')
    group.add_option('--chat', help="Limit to those to whom the user replies", action='store_true', dest='chat')
    group.add_option('--exclude', help="Manually exclude a comma-delimited user list")
    parser.add_option_group(group)
    parser.usage = USAGE
    (options, args) = parser.parse_args()
    
    if not(options.friends or options.followers or options.favorites or options.mention or options.chat):
        raise StandardError("Require at least one filter to be named")
    
    twitstream.ensure_credentials(options)
    
    a = twitter.Api(username=options.username, password=options.password)
    
    if len(args) > 0:
        user = args[0]
    else:
        user = options.username
    
    follow = dict()
    if options.favorites:
        friends = dict()
        for p in range(options.pages):
            ss = GetFavorites(a, user=user, page=p+1)
            for s in ss:
                friends[str(s.user.id)] = str(s.user.screen_name)
        follow = filter_dict_with_set(follow, friends)
        if options.debug: print "after filtering favorites:", follow
    
    if options.mention:
        friends = dict()
        for p in range(options.pages):
            ss = a.GetReplies(page=p+1)
            for s in ss:
                friends[str(s.user.id)] = str(s.user.screen_name)
        follow = filter_dict_with_set(follow, friends)
        if options.debug: print "after filtering mentions:", follow
    
    if options.chat:
        friends = dict()
        for p in range(options.pages):
            ss = a.GetUserTimeline(screen_name=user, page=p+1, count=100)
            for s in ss:
                if s.in_reply_to_user_id:
                    friends[str(s.in_reply_to_user_id)] = str(s.in_reply_to_screen_name)
        follow = filter_dict_with_set(follow, friends)
        if options.debug: print "after filtering chatters:", follow
    
    if options.friends:
        friends = set(map(str, GetFriendIds(a, screen_name=user)))
        if not follow:
            friends = dict(map(lambda x:(x,''), friends))
        follow = filter_dict_with_set(follow, friends)
        if options.debug: print "after filtering friends:", follow
    
    if options.followers:
        friends = set(map(str, GetFollowerIds(a, screen_name=user)))
        if not follow:
            friends = dict(map(lambda x:(x,''), friends))
        follow = filter_dict_with_set(follow, friends)
        if options.debug: print "after filtering followers:", follow
    
    if options.exclude:
        ss = options.exclude.split(',')
        invdict = dict(map(lambda x:(x[1],x[0]), follow.items()))
        for s in ss:
            if s in invdict:
                del invdict[s]
        follow = dict(map(lambda x:(x[1],x[0]), invdict.items()))
        if options.debug: print "after filtering excludes:", follow
    
    options.maximum = min(400, options.maximum)
    if len(follow) > options.maximum:
        print "found %d, discarding %d..." % (len(follow), len(follow) - options.maximum)
        follow = dict(follow.items()[:options.maximum])
    follow_ids = follow.keys()
    follow_usernames = filter(None, follow.values())
    
    print "Following %d users..." % len(follow)
    if follow_usernames:
        print status_wrap.fill(", ".join(follow_usernames))
    print
    
    if options.growl:
        prettyprint = Growler(user, follow_usernames)
    else:
        prettyprint = Formatter(follow_usernames)
    
    stream = twitstream.follow(options.username, options.password, prettyprint, follow_ids, engine=options.engine)
    
    stream.run()

########NEW FILE########
__FILENAME__ = spritz
#!/usr/bin/env python

# The key module provided here:
import twitstream

# Provide documentation:
USAGE = """%prog [options] 

Show a real-time subset of all twitter statuses."""

# Define a function/callable called on every status:
def callback(status):
    print "%s:\t%s\n" % (status.get('user', {}).get('screen_name'), status.get('text'))

if __name__ == '__main__':
    # Inherit the built in parser and use it to get credentials:
    parser = twitstream.parser
    parser.usage = USAGE
    (options, args) = parser.parse_args()
    twitstream.ensure_credentials(options)
    
    # Call a specific API method in the twitstream module: 
    stream = twitstream.spritzer(options.username, options.password, callback, 
                                 debug=options.debug, engine=options.engine)
    
    # Loop forever on the streaming call:
    stream.run()

########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python

import types
import re
import math
import sys
from collections import defaultdict
from urlparse import urlparse

import twitstream

USAGE = """stats.py [options] <key>

Extract statistics from the spritzer stream until interrupted.
Potential keys are: %s"""

link_re = re.compile(">([^<]+)</a>")
url_re = re.compile(r'\b(http://\S+[^\s\.\,\?\)\]\>])', re.IGNORECASE)

def linked(string):
    m = link_re.search(string)
    if m:
        return m.groups()[0]
    else:
        return string

def sec_to_hours(offset):
    if offset == None:
        return -24.
    else:
        return offset/3600.

def urls(string):
    g = url_re.search(string)
    if g:
        return g.groups()
    else:
        return []

def first_url_domain(array):
    if array:
        return urlparse(array[0])[1]
    else:
        return None

def log_spacing(integer):
    m = math.sqrt(10)
    if integer == 0:
        return 0
    return m ** math.floor(math.log(integer, m))

def linear_chunk(interval):
    def linear(x):
        return interval * math.floor(x/interval)
    return linear

class Counter(object):
    def __init__(self, field):
        self.field = field
        self.path = self.FIELDS[field]
        self.counter = defaultdict(int)
    
    def __call__(self, status):
        key = status
        if 'user' not in key:
            if options.debug:
                print >> sys.stderr, status
            return
        for elem in self.path:
            if isinstance(elem, types.FunctionType) or isinstance(elem, types.BuiltinFunctionType):
                key = elem(key)
            else:
                key = key[elem]
        self.counter[key] += 1
        print >> sys.stderr, ".",
        sys.stderr.flush()
    
    def top(self, count):
        print
        if self.field in self.UNORDERED:
            hist = sorted(self.counter.items(), key=lambda x: x[1], reverse=True)
            for val in hist[:count]:
                print "%6d:\t%s" % (val[1], val[0])
        else:
            hist = sorted(self.counter.items(), key=lambda x: x[0])
            if self.field in self.FLOATKEYS:
                for val in hist:
                    print "%+02.2f:\t%d" % val
            else:
                for val in hist:
                    print "%6d:\t%d" % val
    
    FIELDS = {'source':     ('source', linked),
              'client':     ('source', linked),
              'user':       ('user', 'screen_name'),
              'timezone':   ('user', 'time_zone'),
              'utcoffset':  ('user', 'utc_offset', sec_to_hours),
              'followers':  ('user', 'followers_count', log_spacing),
              'friends':    ('user', 'friends_count', log_spacing),
              'favourites': ('user', 'favourites_count', log_spacing),
              'favorites':  ('user', 'favourites_count', log_spacing),
              'statuses':   ('user', 'statuses_count', log_spacing),
              'length':     ('text', len, linear_chunk(10)),
              'counturls':  ('text', urls, len),
              'urldomains': ('text', urls, first_url_domain),
              }
    
    UNORDERED = set(('source', 'client', 'user', 'timezone', 'urldomains'))
    FLOATKEYS = set(('utcoffset',))

if __name__ == '__main__':
    parser = twitstream.parser
    parser.usage = USAGE % ", ".join(Counter.FIELDS)
    parser.add_option('-m', '--maximum', type='int', default=10,
        help="Maximum number of results to print (for non-numerical values) (default: 10, -1 for all)")
    (options, args) = parser.parse_args()
    
    if len(args) == 1 and args[0] in Counter.FIELDS:
        field = args[0]
    else:
        raise NotImplementedError("Requires exactly one argument from:\n%s" % ", ".join(Counter.FIELDS.keys()))
    
    twitstream.ensure_credentials(options)            
    count = Counter(field)
    
    stream = twitstream.spritzer(options.username, options.password, count, 
                                 debug=options.debug, engine=options.engine)
    
    try:
        stream.run()
    except: 
        stream.cleanup()
        count.top(options.maximum)
        print "=" * 40
        print " Total: %d" % sum(count.counter.values())
    


########NEW FILE########
__FILENAME__ = textori
#!/usr/bin/env python

# With the deepest affection for the original:
# http://twistori.com/

import textwrap
import getpass
import re
import sys
import htmlentitydefs

import twitter
import twitstream

USAGE = """%prog [options] [[keyword1] keyword2 ...]

Pretty-prints status messages that match one of the keywords.

Inspired by http://twistori.com/"""


class Formatter(object):
    
    url_pat = re.compile(r'\b(http://\S+[^\s\.\,\?\)\]\>])', re.IGNORECASE)
    ent_pat = re.compile("&#?\w+;")
    wrap = textwrap.TextWrapper(initial_indent='    ', subsequent_indent='    ')
    
    def __init__(self, keywords=[]):
        self.kw_pat = re.compile('\\b(%s)\\b' % "|".join(keywords), re.IGNORECASE)
    
    def __call__(self, status):
        st = twitter.Status.NewFromJsonDict(status)
        if not st.user:
            if options.debug:
                print >> sys.stderr, status
            return
        print '\033[94m' + st.user.screen_name + ':\033[0m'
        mess = self.ent_pat.sub(self.unescape, st.text)
        mess = self.wrap.fill(mess)
        mess = self.kw_pat.sub(self.bold, mess)
        mess = self.url_pat.sub(self.underline, mess)
        print mess
     
    @staticmethod
    def bold(m):
        return '\033[1m' + m.group(1) + '\033[0m'
    
    @staticmethod    
    def underline(m):
        return '\033[4m' + m.group(1) + '\033[0m'
    
    @staticmethod
    def unescape(m):
        "http://effbot.org/zone/re-sub.htm#unescape-html"
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    

if __name__ == '__main__':
    twitstream.parser.usage = USAGE
    (options, args) = twitstream.parser.parse_args()
    twitstream.ensure_credentials(options)
    
    if len(args) < 1:
        args = ['love', 'hate', 'think', 'believe', 'feel', 'wish']
    
    prettyprint = Formatter(args)
    
    stream = twitstream.track(options.username, options.password, prettyprint, args, options.debug, engine=options.engine)
    
    stream.run()

########NEW FILE########
__FILENAME__ = twitstream-test
#!/usr/bin/env python

import twitstream

(options, args) = twitstream.parser.parse_args()
    
if len(args) < 1:
    twitstream.parser.error("requires one method argument")
else:
    method = args[0]
    if method not in twitstream.GETMETHODS and method not in twitstream.POSTPARAMS:
        raise NotImplementedError("Unknown method: %s" % method)

twitstream.ensure_credentials(options)

stream = twitstream.twitstream(method, options.username, options.password, twitstream.DEFAULTACTION, 
            defaultdata=args[1:], debug=options.debug, engine=options.engine)

stream.run()

########NEW FILE########
__FILENAME__ = warehouse
#!/usr/bin/env python

import sys
import twitstream
from urlparse import urlunsplit, urlsplit
from binascii import unhexlify, hexlify


# Provide documentation:
USAGE = """%prog [options] [dburl]

Store a real-time subset of all twitter statuses in MongoDB or CouchDB.
The optional dburl is constructed as:
  [mongo|couch]://host:port/path

MongoDB offers up to two levels of path (database/collection), while
CouchDB uses one. The default behavior is to try CouchDB first, falling
back to MongoDB on localhost, with a path of "test" (or "test/test")."""

class Mongo(object):
    from pymongo.connection import Connection
    from pymongo.objectid import ObjectId
    def __init__(self, location=None, port=None, path=''):
        if not port:
            port = None
        self.conn = self.Connection(host=location, port=port)
        (pathdb, foo, pathcoll) = path.partition('/')
        if not pathdb:
            pathdb = 'test'
        if not pathcoll:
            pathcoll = pathdb
        self.data = self.conn[pathdb][pathcoll]
    
    def status_id(self, num):
        """Derive an ObjectID from the status id."""
        return self.ObjectId(unhexlify('74776974' + ("%x" % num).zfill(16)))
    
    def remove(self, num):
        self.data.remove(self.status_id(num))
    
    def twitsafe(self, status):
        """Change Longs to hex strings to work around MongoDB's assumption
        of 32-bit ints."""
        status['_id'] = self.status_id(status.get('id'))
        if status.get('id'):
            status['id'] = ('%x' % status['id']).zfill(16)
        if status.get('in_reply_to_status_id'):
            status['in_reply_to_status_id'] = ('%x' % status['in_reply_to_status_id']).zfill(16)
        return status
    
    def store(self, num, status):
        self.data.save(status)

class Couch(object):
    from couchdb.client import Server
    def __init__(self, location=None, port=None, path=''):
        lp = list([location or 'localhost', port or 5984])
        lp[1] = str(lp[1])
        dburl = urlunsplit(('http', ':'.join(lp), '', '', ''))
        self.conn = self.Server(dburl)
        if not path:
            path = 'test'
        if path not in self.conn:
            self.data = self.conn.create(path)
        else:
            self.data = self.conn[path]
    
    def status_id(self, num):
        return ("%x" % num).zfill(16)
    
    def remove(self, num):
        del self.data[self.status_id(num)]
    
    def twitsafe(self, status):
        return status
    
    def store(self, num, status):
        self.data[self.status_id(num)] = status


KNOWN = {'mongo': Mongo,
         'couch': Couch}


class Warehouse(object):
    def __init__(self, dburl=''):
        if not dburl:
            try:
                import couchdb
                dburl = 'couch://'
                del couchdb
            except ImportError:
                import pymongo
                dburl = 'mongo://'
                del pymongo
        (self.scheme, self.location, self.port, self.path) = self.urlparse(dburl)
        self.db = KNOWN[self.scheme](self.location, self.port, self.path)
    
    def __call__(self, status):
        if status.get('delete'):
            try:
                self.db.remove(status.get('delete').get('status').get('id'))
                print >> sys.stderr, "-",
            except Exception:
                print >> sys.stderr, ",",
            sys.stderr.flush()
        elif status.get('user'):
            idnum = status.get('id')
            self.db.twitsafe(status)
            try:
                self.db.store(idnum, status)
                print >> sys.stderr, ".",
            except Exception:
                print >> sys.stderr, ";",
            sys.stderr.flush()
        else:
            print >> sys.stderr, '\n' + status
            
    def urlparse(self, url):
        (scheme, foo, rem, bar, baz) = urlsplit(url)
        rem = rem.lstrip('/')
        (locport, foo, path) = rem.partition('/')
        (location, foo, port) = locport.partition(':')
        if not port: port = 0
        return (scheme, location, int(port), path)

if __name__ == '__main__':
    # Inherit the built in parser and use it to get credentials:
    parser = twitstream.parser
    parser.usage = USAGE
    (options, args) = parser.parse_args()
    twitstream.ensure_credentials(options)
    if args:
        dburl = args[0]
    else:
        dburl = ''
    
    callback = Warehouse(dburl)
    
    # Call a specific API method in the twitstream module: 
    stream = twitstream.spritzer(options.username, options.password, callback,
                                 debug=options.debug, engine=options.engine)
    
    # Loop forever on the streaming call:
    try:
        stream.run()
    finally:
        stream.cleanup()
    

########NEW FILE########
__FILENAME__ = twitasync
import asynchat
import asyncore
import socket
import base64
import urllib
import sys
from urlparse import urlparse

from tlslite.api import *

try:
    import json
except ImportError:
    import simplejson as json

USERAGENT = "twitstream.py (http://www.github.com/atl/twitstream), using asynchat"


class TwitterStreamGET(asynchat.async_chat):
    def __init__(self, user, pword, url, action, debug=False, preprocessor=json.loads):
        asynchat.async_chat.__init__(self)
        self.authkey = base64.b64encode("%s:%s" % (user, pword))
        self.preprocessor = preprocessor
        self.url = url
        self.host = urlparse(url)[1]
        try:
            proxy = urlparse(urllib.getproxies()['https'])[1].split(':')
            proxy[1] = int(proxy[1]) or 80
            self.proxy = tuple(proxy)
        except:
            self.proxy = None
        self.inbuf = ""
        self.action = action
        self.debug = debug
        self.set_terminator("\r\n")
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.proxy:
            self.connect( self.proxy )
        else:
            self.connect( (self.host, 443) )
        
    
    @property
    def request(self):
        request  = 'GET %s HTTP/1.0\r\n' % self.url
        request += 'Authorization: Basic %s\r\n' % self.authkey
        request += 'Accept: application/json\r\n'
        request += 'User-Agent: %s\r\n' % USERAGENT
        request += '\r\n'
        return request
    
    def collect_incoming_data(self, data):
        self.inbuf += data
    
    def found_terminator(self):
        if self.inbuf.startswith("HTTP/1") and not self.inbuf.endswith("200 OK"):
            print >> sys.stderr, self.inbuf
        elif self.inbuf.startswith('{'):
            if self.preprocessor:
                a = self.preprocessor(self.inbuf)
            else:
                a = self.inbuf
            self.action(a)
        if self.debug:
            print >> sys.stderr, self.inbuf
        self.inbuf = ""
    
    def handle_connect(self):
        if self.debug:
            print >> sys.stderr, self.request
        self.socket = TLSConnection(self.socket)
        self.socket.handshakeClientCert()
        self.push(self.request)
    
    def handle_close(self):
        self.close()
    
    @staticmethod
    def run():
        asyncore.loop()
    
    def cleanup(self):
        print >> sys.stderr, self.inbuf
        self.close()

class TwitterStreamPOST(TwitterStreamGET):
    def __init__(self, user, pword, url, action, data=tuple(), debug=False, preprocessor=json.loads):
        TwitterStreamGET.__init__(self, user, pword, url, action, debug, preprocessor)
        self.data = data
    
    @property
    def request(self):
        data = urllib.urlencode(self.data)
        request  = 'POST %s HTTP/1.0\r\n' % self.url
        request += 'Authorization: Basic %s\r\n' % self.authkey
        request += 'Accept: application/json\r\n'
        request += 'User-Agent: %s\r\n' % USERAGENT
        request += 'Content-Type: application/x-www-form-urlencoded\r\n'
        request += 'Content-Length: %d\r\n' % len(data)
        request += '\r\n'
        request += '%s' % data
        return request
    
########NEW FILE########
__FILENAME__ = twitcurl
import pycurl
import sys
from urllib import urlencode, getproxies
try:
    # I'm told that simplejson is faster than 2.6's json
    import simplejson as json
except ImportError:
    import json


USERAGENT = "twitstream.py (http://www.github.com/atl/twitstream), using PycURL"

class TwitterStreamGET(object):
    def __init__(self, user, pword, url, action, debug=False, preprocessor=json.loads):
        self.debug = debug
        self.userpass = "%s:%s" % (user, pword)
        self.preprocessor = preprocessor
        self.url = url
        try:
            self.proxy = getproxies()['https']
        except:
            self.proxy = ''
        self.contents = ""
        self.action = action
        self._request = None
    
    @property
    def request(self):
        self._request = pycurl.Curl()
        self._request.setopt(self._request.URL, self.url)
        self._request.setopt(self._request.USERPWD, self.userpass)
        if self.proxy:
            self._request.setopt(self._request.PROXY, self.proxy)
        self._request.setopt(self._request.WRITEFUNCTION, self.body_callback)
        self._request.setopt(self._request.FTP_SSL, pycurl.FTPSSL_ALL)
        return self._request
    
    def body_callback(self, buf):
        self.contents += buf
        q = self.contents.split('\r\n')
        for s in q[:-1]:
            if s.startswith('{'):
                if self.preprocessor:
                    a = self.preprocessor(s)
                else:
                    a = s
                self.action(a)
        self.contents = q[-1]
    
    def run(self, request=None):
        if request:
            self._request = request
        else:
            self.request
        self._request.perform()
    
    def cleanup(self):
        print >> sys.stderr, self.contents
        self._request.close()

class TwitterStreamPOST(TwitterStreamGET):
    def __init__(self, user, pword, url, action, data=tuple(), debug=False, preprocessor=json.loads):
        TwitterStreamGET.__init__(self, user, pword, url, action, debug, preprocessor)
        self.data = data
    
    @property
    def request(self):
        self._request = pycurl.Curl()
        self._request.setopt(self._request.URL, self.url)
        self._request.setopt(self._request.USERPWD, self.userpass)
        if self.proxy:
            self._request.setopt(self._request.PROXY, self.proxy)
        self._request.setopt(self._request.WRITEFUNCTION, self.body_callback)
        self._request.setopt(self._request.POST, 1)
        self._request.setopt(self._request.POSTFIELDS, urlencode(self.data))
        return self._request
    


########NEW FILE########
__FILENAME__ = twittornado
import socket
import base64
import urllib
import sys
from urlparse import urlparse
from tornado import iostream, ioloop
try:
    import json
except ImportError:
    import simplejson as json
import ssl

# Yes, this is very strongly based upon the twitasync approach.
# There was little call to change my approach on a first pass,
# and the IOStream interface is very similar to asyncore/asynchat.

USERAGENT = "twitstream.py (http://www.github.com/atl/twitstream), using tornado.iostream"

class TwitterStreamGET(object):
    def __init__(self, user, pword, url, action, debug=False, preprocessor=json.loads):
        self.authkey = base64.b64encode("%s:%s" % (user, pword))
        self.preprocessor = preprocessor
        self.url = url
        self.host = urlparse(url)[1]
        try:
            proxy = urlparse(urllib.getproxies()['https'])[1].split(':')
            proxy[1] = int(proxy[1]) or 443
            self.proxy = tuple(proxy)
        except:
            self.proxy = None
        self.action = action
        self.debug = debug
        self.terminator = "\r\n"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = None
        if self.proxy:
            self.connect( self.proxy )
        else:
            self.connect( (self.host, 443) )
    
    @property
    def request(self):
        request  = 'GET %s HTTP/1.0\r\n' % self.url
        request += 'Authorization: Basic %s\r\n' % self.authkey
        request += 'Accept: application/json\r\n'
        request += 'User-Agent: %s\r\n' % USERAGENT
        request += '\r\n'
        return request
    
    def connect(self, host):
        self.sock.connect(host)
        self.sock = ssl.wrap_socket(self.sock, do_handshake_on_connect=False)
        self.stream = iostream.SSLIOStream(self.sock)
    
    def found_terminator(self, data):
        if data.startswith("HTTP/1") and not data.endswith("200 OK\r\n"):
            print >> sys.stderr, data
        if data.startswith('{'):
            if self.preprocessor:
                a = self.preprocessor(data)
            else:
                a = data
            self.action(a)
        if self.debug:
            print >> sys.stderr, data
        self.stream.read_until(self.terminator, self.found_terminator)
        
    def run(self):
        self.stream.write(self.request)
        self.stream.read_until(self.terminator, self.found_terminator)
        ioloop.IOLoop.instance().start()
    
    def cleanup(self):
        self.stream.close()

class TwitterStreamPOST(TwitterStreamGET):
    def __init__(self, user, pword, url, action, data=tuple(), debug=False, preprocessor=json.loads):
        TwitterStreamGET.__init__(self, user, pword, url, action, debug, preprocessor)
        self.data = data
    
    @property
    def request(self):
        data = urllib.urlencode(self.data)
        request  = 'POST %s HTTP/1.0\r\n' % self.url
        request += 'Authorization: Basic %s\r\n' % self.authkey
        request += 'Accept: application/json\r\n'
        request += 'User-Agent: %s\r\n' % USERAGENT
        request += 'Content-Type: application/x-www-form-urlencoded\r\n'
        request += 'Content-Length: %d\r\n' % len(data)
        request += '\r\n'
        request += '%s' % data
        return request

########NEW FILE########
