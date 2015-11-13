__FILENAME__ = auth
# -*- coding: utf-8 -*-

import requests
from requests.compat import urlencode, urlparse

# import urllib2

import time

try:
    import json
except:
    # Python 2.6 support
    import simplejson as json

try:
    import oauth2 as oauth
    has_oauth = True
except:
    has_oauth = False

try:
    import httplib2
    has_httplib2 = True
except:
    has_httplib2 = False

from .googlereader import GoogleReader
from .url import ReaderUrl

def toUnicode(obj, encoding='utf-8'):
    return obj
    # if isinstance(obj, basestring):
    #     if not isinstance(obj, unicode):
    #         obj = unicode(obj, encoding)
    # return obj

class AuthenticationMethod(object):
    """
    Defines an interface for authentication methods, must have a get method
    make this abstract?
    1. auth on setup
    2. need to have GET method
    """
    def __init__(self):
        self.client = "libgreader" #@todo: is this needed?

    def getParameters(self, extraargs=None):
        parameters = {'ck':time.time(), 'client':self.client}
        if extraargs:
            parameters.update(extraargs)
        return urlencode(parameters)

    def postParameters(self, post=None):
        return post

class ClientAuthMethod(AuthenticationMethod):
    """
    Auth type which requires a valid Google Reader username and password
    """
    CLIENT_URL = 'https://www.google.com/accounts/ClientLogin'

    def __init__(self, username, password):
        super(ClientAuthMethod, self).__init__()
        self.username   = username
        self.password   = password
        self.auth_token = self._getAuth()
        self.token      = self._getToken()

    def postParameters(self, post=None):
        post.update({'T': self.token})
        return super(ClientAuthMethod, self).postParameters(post)

    def get(self, url, parameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        getString = self.getParameters(parameters)
        headers = {'Authorization':'GoogleLogin auth=%s' % self.auth_token}
        req = requests.get(url + "?" + getString, headers=headers)
        return req.text

    def post(self, url, postParameters=None, urlParameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        if urlParameters:
            url = url + "?" + self.getParameters(urlParameters)
        headers = {'Authorization':'GoogleLogin auth=%s' % self.auth_token,
                    'Content-Type': 'application/x-www-form-urlencoded'
                    }
        postString = self.postParameters(postParameters)
        req = requests.post(url, data=postString, headers=headers)
        return req.text

    def _getAuth(self):
        """
        Main step in authorizing with Reader.
        Sends request to Google ClientAuthMethod URL which returns an Auth token.

        Returns Auth token or raises IOError on error.
        """
        parameters = {
            'service'     : 'reader',
            'Email'       : self.username,
            'Passwd'      : self.password,
            'accountType' : 'GOOGLE'}
        req = requests.post(ClientAuthMethod.CLIENT_URL, data=parameters)
        if req.status_code != 200:
            raise IOError("Error getting the Auth token, have you entered a"
                    "correct username and password?")
        data = req.text
        #Strip newline and non token text.
        token_dict = dict(x.split('=') for x in data.split('\n') if x)
        return token_dict["Auth"]

    def _getToken(self):
        """
        Second step in authorizing with Reader.
        Sends authorized request to Reader token URL and returns a token value.

        Returns token or raises IOError on error.
        """
        headers = {'Authorization':'GoogleLogin auth=%s' % self.auth_token}
        req = requests.get(ReaderUrl.API_URL + 'token', headers=headers)
        if req.status_code != 200:
            raise IOError("Error getting the Reader token.")
        return req.content

class OAuthMethod(AuthenticationMethod):
    """
    Loose wrapper around OAuth2 lib. Kinda awkward.
    """
    GOOGLE_URL        = 'https://www.google.com/accounts/'
    REQUEST_TOKEN_URL = (GOOGLE_URL + 'OAuthGetRequestToken?scope=%s' %
                         ReaderUrl.READER_BASE_URL)
    AUTHORIZE_URL     = GOOGLE_URL + 'OAuthAuthorizeToken'
    ACCESS_TOKEN_URL  = GOOGLE_URL + 'OAuthGetAccessToken'

    def __init__(self, consumer_key, consumer_secret):
        if not has_oauth:
            raise ImportError("No module named oauth2")
        super(OAuthMethod, self).__init__()
        self.oauth_key         = consumer_key
        self.oauth_secret      = consumer_secret
        self.consumer          = oauth.Consumer(self.oauth_key, self.oauth_secret)
        self.authorized_client = None
        self.token_key         = None
        self.token_secret      = None
        self.callback          = None
        self.username          = "OAuth"

    def setCallback(self, callback_url):
        self.callback = '&oauth_callback=%s' % callback_url

    def setRequestToken(self):
        # Step 1: Get a request token. This is a temporary token that is used for
        # having the user authorize an access token and to sign the request to obtain
        # said access token.
        client = oauth.Client(self.consumer)
        if not self.callback:
            resp, content = client.request(OAuthMethod.REQUEST_TOKEN_URL)
        else:
            resp, content = client.request(OAuthMethod.REQUEST_TOKEN_URL + self.callback)
        if int(resp['status']) != 200:
            raise IOError("Error setting Request Token")
        token_dict = dict(urlparse.parse_qsl(content))
        self.token_key = token_dict['oauth_token']
        self.token_secret = token_dict['oauth_token_secret']

    def setAndGetRequestToken(self):
        self.setRequestToken()
        return (self.token_key, self.token_secret)

    def buildAuthUrl(self, token_key=None):
        if not token_key:
            token_key = self.token_key
        #return auth url for user to click or redirect to
        return "%s?oauth_token=%s" % (OAuthMethod.AUTHORIZE_URL, token_key)

    def setAccessToken(self):
        self.setAccessTokenFromCallback(self.token_key, self.token_secret, None)

    def setAccessTokenFromCallback(self, token_key, token_secret, verifier):
        token = oauth.Token(token_key, token_secret)
        #step 2 depends on callback
        if verifier:
            token.set_verifier(verifier)
        client = oauth.Client(self.consumer, token)

        resp, content = client.request(OAuthMethod.ACCESS_TOKEN_URL, "POST")
        if int(resp['status']) != 200:
            raise IOError("Error setting Access Token")
        access_token = dict(urlparse.parse_qsl(content))

        #created Authorized client using access tokens
        self.authFromAccessToken(access_token['oauth_token'],
                                 access_token['oauth_token_secret'])

    def authFromAccessToken(self, oauth_token, oauth_token_secret):
        self.token_key         = oauth_token
        self.token_secret      = oauth_token_secret
        token                  = oauth.Token(oauth_token,oauth_token_secret)
        self.authorized_client = oauth.Client(self.consumer, token)

    def getAccessToken(self):
        return (self.token_key, self.token_secret)

    def get(self, url, parameters=None):
        if self.authorized_client:
            getString = self.getParameters(parameters)
            #can't pass in urllib2 Request object here?
            resp, content = self.authorized_client.request(url + "?" + getString)
            return toUnicode(content)
        else:
            raise IOError("No authorized client available.")

    def post(self, url, postParameters=None, urlParameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        if self.authorized_client:
            if urlParameters:
                getString = self.getParameters(urlParameters)
                req = urllib2.Request(url + "?" + getString)
            else:
                req = urllib2.Request(url)
            postString = self.postParameters(postParameters)
            resp,content = self.authorized_client.request(req, method="POST", body=postString)
            return toUnicode(content)
        else:
            raise IOError("No authorized client available.")

class OAuth2Method(AuthenticationMethod):
    '''
    Google OAuth2 base method.
    '''
    GOOGLE_URL = 'https://accounts.google.com'
    AUTHORIZATION_URL = GOOGLE_URL + '/o/oauth2/auth'
    ACCESS_TOKEN_URL = GOOGLE_URL + '/o/oauth2/token'
    SCOPE = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.google.com/reader/api/',
    ]

    def __init__(self, client_id, client_secret):
        super(OAuth2Method, self).__init__()
        self.client_id         = client_id
        self.client_secret     = client_secret
        self.authorized_client = None
        self.code              = None
        self.access_token      = None
        self.action_token      = None
        self.redirect_uri      = None
        self.username          = "OAuth2"

    def setRedirectUri(self, redirect_uri):
        self.redirect_uri = redirect_uri

    def buildAuthUrl(self):
        args = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPE),
            'response_type': 'code',
        }
        return self.AUTHORIZATION_URL + '?' + urlencode(args)

    def setActionToken(self):
        '''
        Get action to prevent XSRF attacks
        http://code.google.com/p/google-reader-api/wiki/ActionToken

        TODO: mask token expiring? handle regenerating?
        '''
        self.action_token = self.get(ReaderUrl.ACTION_TOKEN_URL)

    def setAccessToken(self):
        params = {
            'grant_type': 'authorization_code',  # request auth code
            'code': self.code,                   # server response code
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        request = requests.post(self.ACCESS_TOKEN_URL, data=params,
                                headers=headers)

        if request.status_code != 200:
            raise IOError('Error getting Access Token')

        response = request.json()
        if 'access_token' not in response:
            raise IOError('Error getting Access Token')
        else:
            self.authFromAccessToken(response['access_token'])

    def authFromAccessToken(self, access_token):
        self.access_token = access_token

    def get(self, url, parameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        if not self.access_token:
            raise IOError("No authorized client available.")
        if parameters is None:
            parameters = {}
        parameters.update({'access_token': self.access_token, 'alt': 'json'})
        request = requests.get(url + '?' + self.getParameters(parameters))
        if request.status_code != 200:
            return None
        else:
            return toUnicode(request.text)

    def post(self, url, postParameters=None, urlParameters=None):
        """
        Convenience method for requesting to google with proper cookies/params.
        """
        if not self.access_token:
            raise IOError("No authorized client available.")
        if not self.action_token:
            raise IOError("Need to generate action token.")
        if urlParameters is None:
            urlParameters = {}
        headers = {'Authorization': 'Bearer ' + self.access_token,
                   'Content-Type': 'application/x-www-form-urlencoded'}
        postParameters.update({'T':self.action_token})
        request = requests.post(url + '?' + self.getParameters(urlParameters),
                                data=postParameters, headers=headers)
        if request.status_code != 200:
            return None
        else:
            return toUnicode(request.text)

class GAPDecoratorAuthMethod(AuthenticationMethod):
    """
    An adapter to work with Google API for Python OAuth2 wrapper.
    Especially useful when deploying to Google AppEngine.
    """
    def __init__(self, credentials):
        """
        Initialize auth method with existing credentials.
        Args:
            credentials: OAuth2 credentials obtained via GAP OAuth2 library.
        """
        if not has_httplib2:
            raise ImportError("No module named httplib2")
        super(GAPDecoratorAuthMethod, self).__init__()
        self._http = None
        self._credentials = credentials
        self._action_token = None

    def _setupHttp(self):
        """
        Setup an HTTP session authorized by OAuth2.
        """
        if self._http == None:
            http = httplib2.Http()
            self._http = self._credentials.authorize(http)

    def get(self, url, parameters=None):
        """
        Implement libgreader's interface for authenticated GET request
        """
        if self._http == None:
            self._setupHttp()
        uri = url + "?" + self.getParameters(parameters)
        response, content = self._http.request(uri, "GET")
        return content

    def post(self, url, postParameters=None, urlParameters=None):
        """
        Implement libgreader's interface for authenticated POST request
        """
        if self._action_token == None:
            self._action_token = self.get(ReaderUrl.ACTION_TOKEN_URL)

        if self._http == None:
            self._setupHttp()
        uri = url + "?" + self.getParameters(urlParameters)
        postParameters.update({'T':self._action_token})
        body = self.postParameters(postParameters)
        response, content = self._http.request(uri, "POST", body=body)
        return content

########NEW FILE########
__FILENAME__ = googlereader
# -*- coding: utf-8 -*-

import time

try:
    import json
except:
    import simplejson as json

from .url import ReaderUrl
from .items import SpecialFeed, Item, Category, Feed

class GoogleReader(object):
    """
    Class for using the unofficial Google Reader API and working with
    the data it returns.

    Requires valid google username and password.
    """
    def __repr__(self):
        return "<Google Reader object: %s>" % self.auth.username

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<Google Reader object: %s>" % self.auth.username

    def __init__(self, auth):
        self.auth           = auth
        self.feeds          = []
        self.categories     = []
        self.feedsById      = {}
        self.categoriesById = {}
        self.specialFeeds   = {}
        self.orphanFeeds    = []
        self.userId         = None
        self.addTagBacklog  = {}
        self.inItemTagTransaction   = False

    def toJSON(self):
        """
        TODO: build a json object to return via ajax
        """
        pass

    def getFeeds(self):
        """
        @Deprecated, see getSubscriptionList
        """
        return self.feeds

    def getSubscriptionList(self):
        """
        Returns a list of Feed objects containing all of a users subscriptions
        or None if buildSubscriptionList has not been called, to get the Feeds
        """
        return self.feeds

    def getCategories(self):
        """
        Returns a list of all the categories or None if buildSubscriptionList
        has not been called, to get the Feeds
        """
        return self.categories

    def makeSpecialFeeds(self):
        for type in ReaderUrl.SPECIAL_FEEDS:
            self.specialFeeds[type] = SpecialFeed(self, type)

    def getSpecialFeed(self, type):
        return self.specialFeeds[type]

    def buildSubscriptionList(self):
        """
        Hits Google Reader for a users's alphabetically ordered list of feeds.

        Returns true if succesful.
        """
        self._clearLists()
        unreadById = {}

        if not self.userId:
            self.getUserInfo()

        unreadJson = self.httpGet(ReaderUrl.UNREAD_COUNT_URL, { 'output': 'json', })
        unreadCounts = json.loads(unreadJson, strict=False)['unreadcounts']
        for unread in unreadCounts:
            unreadById[unread['id']] = unread['count']

        feedsJson = self.httpGet(ReaderUrl.SUBSCRIPTION_LIST_URL, { 'output': 'json', })
        subscriptions = json.loads(feedsJson, strict=False)['subscriptions']

        for sub in subscriptions:
            categories = []
            if 'categories' in sub:
                for hCategory in sub['categories']:
                    cId = hCategory['id']
                    if not cId in self.categoriesById:
                        category = Category(self, hCategory['label'], cId)
                        self._addCategory(category)
                    categories.append(self.categoriesById[cId])

            try:
                feed = self.getFeed(sub['id'])
                if not feed:
                    raise
                if not feed.title:
                    feed.title = sub['title']
                for category in categories:
                    feed.addCategory(category)
                feed.unread = unreadById.get(sub['id'], 0)
            except:
                feed = Feed(self,
                            sub['title'],
                            sub['id'],
                            sub.get('htmlUrl', None),
                            unreadById.get(sub['id'], 0),
                            categories)
            if not categories:
                self.orphanFeeds.append(feed)
            self._addFeed(feed)

        specialUnreads = [id for id in unreadById
                            if id.find('user/%s/state/com.google/' % self.userId) != -1]
        for type in self.specialFeeds:
            feed = self.specialFeeds[type]
            feed.unread = 0
            for id in specialUnreads:
                if id.endswith('/%s' % type):
                    feed.unread = unreadById.get(id, 0)
                    break

        return True

    def _getFeedContent(self, url, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        A list of items (from a feed, a category or from URLs made with SPECIAL_ITEMS_URL)

        Returns a dict with
         :param id: (str, feed's id)
         :param continuation: (str, to be used to fetch more items)
         :param items:  array of dits with :
            - update (update timestamp)
            - author (str, username)
            - title (str, page title)
            - id (str)
            - content (dict with content and direction)
            - categories (list of categories including states or ones provided by the feed owner)
        """
        parameters = {}
        if excludeRead:
            parameters['xt'] = 'user/-/state/com.google/read'
        if continuation:
            parameters['c'] = continuation
        parameters['n'] = loadLimit
        if since:
            parameters['ot'] = since
        if until:
            parameters['nt'] = until
        contentJson = self.httpGet(url, parameters)
        return json.loads(contentJson, strict=False)

    def itemsToObjects(self, parent, items):
        objects = []
        for item in items:
            objects.append(Item(self, item, parent))
        return objects

    def getFeedContent(self, feed, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Return items for a particular feed
        """
        return self._getFeedContent(feed.fetchUrl, excludeRead, continuation, loadLimit, since, until)

    def getCategoryContent(self, category, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Return items for a particular category
        """
        return self._getFeedContent(category.fetchUrl, excludeRead, continuation, loadLimit, since, until)

    def _modifyItemTag(self, item_id, action, tag):
        """ wrapper around actual HTTP POST string for modify tags """
        return self.httpPost(ReaderUrl.EDIT_TAG_URL,
                             {'i': item_id, action: tag, 'ac': 'edit-tags'})

    def removeItemTag(self, item, tag):
        """
        Remove a tag to an individal item.

        tag string must be in form "user/-/label/[tag]"
        """
        return self._modifyItemTag(item.id, 'r', tag)

    def beginAddItemTagTransaction(self):
        if self.inItemTagTransaction:
            raise Exception("Already in addItemTag transaction")
        self.addTagBacklog = {}
        self.inItemTagTransaction = True

    def addItemTag(self, item, tag):
        """
        Add a tag to an individal item.

        tag string must be in form "user/-/label/[tag]"
        """
        if self.inItemTagTransaction:
            # XXX: what if item's parent is not a feed?
            if not tag in self.addTagBacklog:
                self.addTagBacklog[tag] = []                
            self.addTagBacklog[tag].append({'i': item.id, 's': item.parent.id})
            return "OK"
        else:
            return self._modifyItemTag(item.id, 'a', tag)

    
    def commitAddItemTagTransaction(self):
        if self.inItemTagTransaction:
            for tag in self.addTagBacklog:
                itemIds = [item['i'] for item in self.addTagBacklog[tag]]
                feedIds = [item['s'] for item in self.addTagBacklog[tag]]
                self.httpPost(ReaderUrl.EDIT_TAG_URL,
                    {'i': itemIds, 'a': tag, 'ac': 'edit-tags', 's': feedIds})
            self.addTagBacklog = {}
            self.inItemTagTransaction = False
            return True
        else:
            raise Exception("Not in addItemTag transaction")

    def markFeedAsRead(self, feed):
        return self.httpPost(
            ReaderUrl.MARK_ALL_READ_URL,
            {'s': feed.id, })

    def subscribe(self, feedUrl):
        """
        Adds a feed to the top-level subscription list

        Ubscribing seems idempotent, you can subscribe multiple times
        without error

        returns True or throws HTTPError
        """
        response = self.httpPost(
            ReaderUrl.SUBSCRIPTION_EDIT_URL,
            {'ac':'subscribe', 's': feedUrl})
        # FIXME - need better return API
        if response and 'OK' in response:
            return True
        else:
            return False

    def unsubscribe(self, feedUrl):
        """
        Removes a feed url from the top-level subscription list

        Unsubscribing seems idempotent, you can unsubscribe multiple times
        without error

        returns True or throws HTTPError
        """
        response = self.httpPost(
            ReaderUrl.SUBSCRIPTION_EDIT_URL,
            {'ac':'unsubscribe', 's': feedUrl})
        # FIXME - need better return API
        if response and 'OK' in response:
            return True
        else:
            return False

    def getUserInfo(self):
        """
        Returns a dictionary of user info that google stores.
        """
        userJson = self.httpGet(ReaderUrl.USER_INFO_URL)
        result = json.loads(userJson, strict=False)
        self.userId = result['userId']
        return result

    def getUserSignupDate(self):
        """
        Returns the human readable date of when the user signed up for google reader.
        """
        userinfo = self.getUserInfo()
        timestamp = int(float(userinfo["signupTimeSec"]))
        return time.strftime("%m/%d/%Y %H:%M", time.gmtime(timestamp))

    def httpGet(self, url, parameters=None):
        """
        Wrapper around AuthenticationMethod get()
        """
        return self.auth.get(url, parameters)

    def httpPost(self, url, post_parameters=None):
        """
        Wrapper around AuthenticationMethod post()
        """
        return self.auth.post(url, post_parameters)

    def _addFeed(self, feed):
        if feed.id not in self.feedsById:
            self.feedsById[feed.id] = feed
            self.feeds.append(feed)

    def _addCategory (self, category):
        if category.id not in self.categoriesById:
            self.categoriesById[category.id] = category
            self.categories.append(category)

    def getFeed(self, id):
        return self.feedsById.get(id, None)

    def getCategory(self, id):
        return self.categoriesById.get(id, None)

    def _clearLists(self):
        """
        Clear all list before sync : feeds and categories
        """
        self.feedsById      = {}
        self.feeds          = []
        self.categoriesById = {}
        self.categories     = []
        self.orphanFeeds    = []

########NEW FILE########
__FILENAME__ = items
# -*- coding: utf-8 -*-

from requests.compat import quote

from .url import ReaderUrl

class ItemsContainer(object):
    """
    A base class used for all classes aimed to have items (Categories and Feeds)
    """
    def __init__(self):
        self.items          = []
        self.itemsById      = {}
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        self.lastUpdated    = None
        self.unread         = 0
        self.continuation   = None

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Get content from google reader with specified parameters.
        Must be overladed in inherited clases
        """
        return None

    def loadItems(self, excludeRead=False, loadLimit=20, since=None, until=None):
        """
        Load items and call itemsLoadedDone to transform data in objects
        """
        self.clearItems()
        self.loadtLoadOk    = False
        self.lastLoadLength = 0
        self._itemsLoadedDone(self._getContent(excludeRead, None, loadLimit, since, until))

    def loadMoreItems(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        """
        Load more items using the continuation parameters of previously loaded items.
        """
        self.lastLoadOk     = False
        self.lastLoadLength = 0
        if not continuation and not self.continuation:
            return
        self._itemsLoadedDone(self._getContent(excludeRead, continuation or self.continuation, loadLimit, since, until))

    def _itemsLoadedDone(self, data):
        """
        Called when all items are loaded
        """
        if data is None:
            return
        self.continuation   = data.get('continuation', None)
        self.lastUpdated    = data.get('updated', None)
        self.lastLoadLength = len(data.get('items', []))
        self.googleReader.itemsToObjects(self, data.get('items', []))
        self.lastLoadOk = True

    def _addItem(self, item):
        self.items.append(item)
        self.itemsById[item.id] = item

    def getItem(self, id):
        return self.itemsById[id]

    def clearItems(self):
        self.items        = []
        self.itemsById    = {}
        self.continuation = None

    def getItems(self):
        return self.items

    def countItems(self, excludeRead=False):
        if excludeRead:
            sum([1 for item in self.items if item.isUnread()])
        else:
            return len(self.items)

    def markItemRead(self, item, read):
        if read and item.isUnread():
            self.unread -= 1
        elif not read and item.isRead():
            self.unread += 1

    def markAllRead(self):
        self.unread = 0
        for item in self.items:
            item.read = True
            item.canUnread = False
        result = self.googleReader.markFeedAsRead(self)
        return result.upper() == 'OK'

    def countUnread(self):
        self.unread = self.countItems(excludeRead=True)

class Category(ItemsContainer):
    """
    Class for representing a category
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<%s (%d), %s>" % (self.label, self.unread, self.id)

    def __init__(self, googleReader, label, id):
        """
         :param label: (str)
         :param id: (str)
        """
        super(Category, self).__init__()
        self.googleReader = googleReader

        self.label = label
        self.id    = id

        self.feeds  = []

        self.fetchUrl = ReaderUrl.CATEGORY_URL + Category.urlQuote(self.label)

    def _addFeed(self, feed):
        if not feed in self.feeds:
            self.feeds.append(feed)
            try:
                self.unread += feed.unread
            except:
                pass

    def getFeeds(self):
        return self.feeds

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        return self.googleReader.getCategoryContent(self, excludeRead, continuation, loadLimit, since, until)

    def countUnread(self):
        self.unread = sum([feed.unread for feed in self.feeds])

    def toArray(self):
        pass

    def toJSON(self):
        pass

    @staticmethod
    def urlQuote(string):
        """ Quote a string for being used in a HTTP URL """
        return quote(string.encode("utf-8"))

class BaseFeed(ItemsContainer):
    """
    Class for representing a special feed.
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "<%s, %s>" % (self.title, self.id)

    def __init__(self, googleReader, title, id, unread, categories=[]):
        """
         :param title: (str, name of the feed)
         :param id: (str, id for google reader)
         :param unread: (int, number of unread items, 0 by default)
         :param categories: (list) - list of all categories a feed belongs to, can be empty
        """
        super(BaseFeed, self).__init__()

        self.googleReader = googleReader

        self.id    = id
        self.title = title
        self.unread = unread

        self.categories = []
        for category in categories:
            self.addCategory(category)

        self.continuation = None

    def addCategory(self, category):
        if not category in self.categories:
            self.categories.append(category)
            category._addFeed(self)

    def getCategories(self):
        return self.categories

    def _getContent(self, excludeRead=False, continuation=None, loadLimit=20, since=None, until=None):
        return self.googleReader.getFeedContent(self, excludeRead, continuation, loadLimit, since, until)

    def markItemRead(self, item, read):
        super(BaseFeed, self).markItemRead(item, read)
        for category in self.categories:
            category.countUnread()

    def markAllRead(self):
        self.unread = 0
        for category in self.categories:
            category.countUnread()
        return super(BaseFeed, self).markAllRead()

    def toArray(self):
        pass

    def toJSON(self):
        pass

class SpecialFeed(BaseFeed):
    """
    Class for representing specials feeds (starred, shared, friends...)
    """
    def __init__(self, googleReader, type):
        """
        type is one of ReaderUrl.SPECIAL_FEEDS
        """
        super(SpecialFeed, self).__init__(
            googleReader,
            title      = type,
            id         = ReaderUrl.SPECIAL_FEEDS_PART_URL+type,
            unread     = 0,
            categories = [],
        )
        self.type = type

        self.fetchUrl = ReaderUrl.CONTENT_BASE_URL + Category.urlQuote(self.id)

class Feed(BaseFeed):
    """
    Class for representing a normal feed.
    """

    def __init__(self, googleReader, title, id, siteUrl=None, unread=0, categories=[]):
        """
        :param title: str name of the feed
        :param id: str, id for google reader
        :param siteUrl: str, can be empty
        :param unread: int, number of unread items, 0 by default
        :param categories: (list) - list of all categories a feed belongs to, can be empty
        """
        super(Feed, self).__init__(googleReader, title, id, unread, categories)

        self.feedUrl = self.id.lstrip('feed/')
        self.siteUrl = siteUrl

        self.fetchUrl = ReaderUrl.FEED_URL + Category.urlQuote(self.id)

class Item(object):
    """
    Class for representing an individual item (an entry of a feed)
    """
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return '<"%s" by %s, %s>' % (self.title, self.author, self.id)

    def __init__(self, googleReader, item, parent):
        """
        :param item: An item loaded from json
        :param parent: the object (Feed of Category) containing the Item
        """
        self.googleReader = googleReader
        self.parent = parent

        self.data   = item # save original data for accessing other fields
        self.id     = item['id']
        self.title  = item.get('title', '(no title)')
        self.author = item.get('author', None)
        self.content = item.get('content', item.get('summary', {})).get('content', '')
        self.origin  = { 'title': '', 'url': ''}
        if 'crawlTimeMsec' in item:
            self.time = int(item['crawlTimeMsec']) // 1000
        else:
            self.time = None

        # check original url
        self.url    = None
        for alternate in item.get('alternate', []):
            if alternate.get('type', '') == 'text/html':
                self.url = alternate['href']
                break

        # check status
        self.read    = False
        self.starred = False
        self.shared  = False
        for category in item.get('categories', []):
            if category.endswith('/state/com.google/read'):
                self.read = True
            elif category.endswith('/state/com.google/starred'):
                self.starred = True
            elif category in ('user/-/state/com.google/broadcast',
                              'user/%s/state/com.google/broadcast' % self.googleReader.userId):
                self.shared = True

        self.canUnread = item.get('isReadStateLocked', 'false') != 'true'

        # keep feed, can be used when item is fetched from a special feed, then it's the original one
        try:
            f = item['origin']
            self.origin = {
                'title': f.get('title', ''),
                'url': f.get('htmlUrl', ''),
            }
            self.feed = self.googleReader.getFeed(f['streamId'])
            if not self.feed:
                raise
            if not self.feed.title and 'title' in f:
                self.feed.title = f['title']
        except:
            try:
                self.feed = Feed(self, f.get('title', ''), f['streamId'], f.get('htmlUrl', None), 0, [])
                try:
                    self.googleReader._addFeed(self.feed)
                except:
                    pass
            except:
                self.feed = None

        self.parent._addItem(self)

    def isUnread(self):
        return not self.read

    def isRead(self):
        return self.read

    def markRead(self, read=True):
        self.parent.markItemRead(self, read)
        self.read = read
        if read:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_READ)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_READ)
        return result.upper() == 'OK'

    def markUnread(self, unread=True):
        return self.markRead(not unread)

    def isShared(self):
        return self.shared

    def markShared(self, shared=True):
        self.shared = shared
        if shared:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_SHARED)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_SHARED)
        return result.upper() == 'OK'

    def share(self):
        return self.markShared()

    def unShare(self):
        return self.markShared(False)

    def isStarred(self):
        return self.starred

    def markStarred(self, starred=True):
        self.starred = starred
        if starred:
            result = self.googleReader.addItemTag(self, ReaderUrl.TAG_STARRED)
        else:
            result = self.googleReader.removeItemTag(self, ReaderUrl.TAG_STARRED)
        return result.upper() == 'OK'

    def star(self):
        return self.markStarred()

    def unStar(self):
        return self.markStarred(False)

########NEW FILE########
__FILENAME__ = url
# -*- coding: utf-8 -*-

class ReaderUrl(object):
    READER_BASE_URL        = 'https://www.google.com/reader/api'
    API_URL                = READER_BASE_URL + '/0/'

    ACTION_TOKEN_URL       = API_URL + 'token'
    USER_INFO_URL          = API_URL + 'user-info'

    SUBSCRIPTION_LIST_URL  = API_URL + 'subscription/list'
    SUBSCRIPTION_EDIT_URL  = API_URL + 'subscription/edit'
    UNREAD_COUNT_URL       = API_URL + 'unread-count'

    CONTENT_PART_URL       = 'stream/contents/'
    CONTENT_BASE_URL       = API_URL + CONTENT_PART_URL
    SPECIAL_FEEDS_PART_URL = 'user/-/state/com.google/'

    READING_LIST           = 'reading-list'
    READ_LIST              = 'read'
    KEPTUNREAD_LIST        = 'kept-unread'
    STARRED_LIST           = 'starred'
    SHARED_LIST            = 'broadcast'
    NOTES_LIST             = 'created'
    FRIENDS_LIST           = 'broadcast-friends'
    SPECIAL_FEEDS          = (READING_LIST, READ_LIST, KEPTUNREAD_LIST,
                              STARRED_LIST, SHARED_LIST, FRIENDS_LIST,
                              NOTES_LIST,)

    FEED_URL               = CONTENT_BASE_URL
    CATEGORY_URL           = CONTENT_BASE_URL + 'user/-/label/'

    EDIT_TAG_URL           = API_URL + 'edit-tag'
    TAG_READ               = 'user/-/state/com.google/read'
    TAG_STARRED            = 'user/-/state/com.google/starred'
    TAG_SHARED             = 'user/-/state/com.google/broadcast'

    MARK_ALL_READ_URL      = API_URL + 'mark-all-as-read'

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuthMethod in libgreader.
"""

#ClientAuthMethod
#User account I created for testing
# username  = 'libgreadertest@gmail.com'
# password  = 'libgreadertestlibgreadertest'
# firstname = 'Foo'

#OAuth2
# requires API access tokens from google 
# available at https://code.google.com/apis/console/
# -goto "API Access" and generate a new client id for web applications
try:
    from .local_config import *
except Exception:
    pass

########NEW FILE########
__FILENAME__ = test_auth
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for oauth and ClientAuthMethod in libgreader.

"""

try:
    import unittest2 as unittest
except:
    import unittest

from libgreader import GoogleReader, OAuthMethod, OAuth2Method, ClientAuthMethod, Feed
import requests
import re

from .config import *

class TestClientAuthMethod(unittest.TestCase):
    def test_ClientAuthMethod_login(self):
        ca = ClientAuthMethod(username,password)
        self.assertNotEqual(ca, None)

    def test_reader(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        self.assertNotEqual(reader, None)

    def test_bad_user_details(self):
        self.assertRaises(IOError, ClientAuthMethod, 'asdsa', '')

    def test_reader_user_info(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])


#automated approval of oauth url
#returns mechanize Response of the last "You have accepted" page
def automated_oauth_approval(url):
    #general process is:
    # 1. assume user isn't logged in, so get redirected to google accounts
    # login page. login using test account credentials
    # 2. redirected back to oauth approval page. br.submit() should choose the
    # first submit on that page, which is the "Accept" button
    br = mechanize.Browser()
    br.open(url)
    br.select_form(nr=0)
    br["Email"] = username
    br["Passwd"] = password
    response1 = br.submit()
    br.select_form(nr=0)
    req2 = br.click(type="submit", nr=0)
    response2 = br.open(req2)
    return response2

@unittest.skip('deprecated')
class TestOAuth(unittest.TestCase):
    def test_oauth_login(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        self.assertNotEqual(auth, None)

    def test_getting_request_token(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        token, token_secret = auth.setAndGetRequestToken()
        url = auth.buildAuthUrl()
        response = automated_oauth_approval(url)
        self.assertNotEqual(-1,response.get_data().find('You have successfully granted'))

    def test_full_auth_process_without_callback(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        auth.setRequestToken()
        auth_url = auth.buildAuthUrl()
        response = automated_oauth_approval(auth_url)
        auth.setAccessToken()
        reader = GoogleReader(auth)

        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])

    def test_full_auth_process_with_callback(self):
        auth = OAuthMethod(oauth_key, oauth_secret)
        #must be a working callback url for testing
        auth.setCallback("http://www.asktherelic.com")
        token, token_secret = auth.setAndGetRequestToken()
        auth_url = auth.buildAuthUrl()

        #callback section
        #get response, which is a redirect to the callback url
        response = automated_oauth_approval(auth_url)
        query_string = urlparse.urlparse(response.geturl()).query
        #grab the verifier token from the callback url query string
        token_verifier = urlparse.parse_qs(query_string)['oauth_verifier'][0]

        auth.setAccessTokenFromCallback(token, token_secret, token_verifier)
        reader = GoogleReader(auth)

        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])


#automate getting the approval token
def mechanize_oauth2_approval(url):
    """
    general process is:
    1. assume user isn't logged in, so get redirected to google accounts
    login page. login using account credentials
    But, if the user has already granted access, the user is auto redirected without
    having to confirm again.
    2. redirected back to oauth approval page. br.submit() should choose the
    first submit on that page, which is the "Accept" button
    3. mechanize follows the redirect, and should throw 40X exception and
    we return the token
    """
    br = mechanize.Browser()
    br.open(url)
    br.select_form(nr=0)
    br["Email"] = username
    br["Passwd"] = password
    try:
        response1 = br.submit()
        br.select_form(nr=0)
        response2 = br.submit()
    except Exception as e:
        #watch for 40X exception on trying to load redirect page
        pass
    callback_url = br.geturl()
    # split off the token in hackish fashion
    return callback_url.split('code=')[1]

def automated_oauth2_approval(url):
    """
    general process is:
    1. assume user isn't logged in, so get redirected to google accounts
    login page. login using account credentials
    2. get redirected to oauth approval screen
    3. authorize oauth app
    """
    auth_url = url
    headers = {'Referer': auth_url}

    s = requests.Session()
    r1 = s.get(auth_url)
    post_data = dict((x[0],x[1]) for x in re.findall('name="(.*?)".*?value="(.*?)"', str(r1.content), re.MULTILINE))
    post_data['Email'] = username
    post_data['Passwd'] = password
    post_data['timeStmp'] = ''
    post_data['secTok'] = ''
    post_data['signIn'] = 'Sign in'
    post_data['GALX'] = s.cookies['GALX']

    r2 = s.post('https://accounts.google.com/ServiceLoginAuth', data=post_data, headers=headers, allow_redirects=False)

    #requests is fucking up the url encoding and double encoding ampersands
    scope_url = r2.headers['location'].replace('amp%3B','')

    # now get auth screen
    r3 = s.get(scope_url)

    # unless we have already authed!
    if 'asktherelic' in r3.url:
        code = r3.url.split('=')[1]
        return code

    post_data = dict((x[0],x[1]) for x in re.findall('name="(.*?)".*?value="(.*?)"', str(r3.content)))
    post_data['submit_access'] = 'true'
    post_data['_utf8'] = '&#9731'

    # again, fucked encoding for amp;
    action_url = re.findall('action="(.*?)"', str(r3.content))[0].replace('amp;','')

    r4 = s.post(action_url, data=post_data, headers=headers, allow_redirects=False)
    code = r4.headers['Location'].split('=')[1]

    s.close()

    return code

@unittest.skipIf("client_id" not in globals(), 'OAuth2 config not setup')
class TestOAuth2(unittest.TestCase):
    def test_full_auth_and_access_userdata(self):
        auth = OAuth2Method(client_id, client_secret)
        auth.setRedirectUri(redirect_url)
        url = auth.buildAuthUrl()
        token = automated_oauth2_approval(url)
        auth.code = token
        auth.setAccessToken()

        reader = GoogleReader(auth)
        info = reader.getUserInfo()
        self.assertEqual(dict, type(info))
        self.assertEqual(firstname, info['userName'])

    def test_oauth_subscribe(self):
        auth = OAuth2Method(client_id, client_secret)
        auth.setRedirectUri(redirect_url)
        url = auth.buildAuthUrl()
        token = automated_oauth2_approval(url)
        auth.code = token
        auth.setAccessToken()
        auth.setActionToken()

        reader = GoogleReader(auth)

        slashdot = 'feed/http://rss.slashdot.org/Slashdot/slashdot'
        #unsubscribe always return true; revert feedlist state
        self.assertTrue(reader.unsubscribe(slashdot))
        # now subscribe
        self.assertTrue(reader.subscribe(slashdot))
        # wait for server to update
        import time
        time.sleep(1)
        reader.buildSubscriptionList()
        # test subscribe successful
        self.assertIn(slashdot, [x.id for x in reader.getSubscriptionList()])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_special_feeds
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
libG(oogle)Reader
Copyright (C) 2010  Matt Behrens <askedrelic@gmail.com> http://asktherelic.com

Python library for working with the unofficial Google Reader API.

Unit tests for feeds.
"""

try:
    import unittest2 as unittest
except:
    import unittest

from libgreader import GoogleReader, OAuthMethod, ClientAuthMethod, Feed, ItemsContainer, Item, BaseFeed, SpecialFeed, ReaderUrl
import re
import time

from .config import *

class TestSpecialFeeds(unittest.TestCase):
    def test_reading_list_exists(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        reader.makeSpecialFeeds()
        feeds = reader.getFeedContent(reader.getSpecialFeed(ReaderUrl.READING_LIST))

        self.assertEqual(dict, type(feeds))

        list_match = re.search('reading list in Google Reader', feeds['title'])
        self.assertTrue(list_match)

    def test_marking_read(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        feed_item = container.items[0]
        self.assertTrue(feed_item.markRead())
        self.assertTrue(feed_item.isRead())

    def test_loading_item_count(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems(loadLimit=5)

        self.assertEqual(5, len(container.items))
        self.assertEqual(5, container.countItems())

    def test_subscribe_unsubscribe(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        
        slashdot = 'feed/http://rss.slashdot.org/Slashdot/slashdot'

        #unsubscribe always return true; revert feedlist state
        self.assertTrue(reader.unsubscribe(slashdot))

        # now subscribe
        self.assertTrue(reader.subscribe(slashdot))

        # wait for server to update
        time.sleep(1)
        reader.buildSubscriptionList()

        # test subscribe successful
        self.assertIn(slashdot, [x.id for x in reader.getSubscriptionList()])

    def test_add_remove_single_feed_tag(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        tag_name = 'test-single-tag'
        feed_1 = container.items[0]

        # assert tag doesn't exist yet
        self.assertFalse(any([tag_name in x for x in feed_1.data['categories']]))

        # add tag
        reader.addItemTag(feed_1, 'user/-/label/' + tag_name)

        #reload now
        container.clearItems()
        container.loadItems()
        feed_2 = container.items[0]

        # assert tag is in new
        self.assertTrue(any([tag_name in x for x in feed_2.data['categories']]))

        # remove tag
        reader.removeItemTag(feed_2, 'user/-/label/' + tag_name)

        #reload now
        container.clearItems()
        container.loadItems()
        feed_3 = container.items[0]

        # assert tag is removed
        self.assertFalse(any([tag_name in x for x in feed_3.data['categories']]))

    def test_transaction_add_feed_tags(self):
        ca = ClientAuthMethod(username,password)
        reader = GoogleReader(ca)
        container = SpecialFeed(reader, ReaderUrl.READING_LIST)
        container.loadItems()

        tags = ['test-transaction%s' % x for x in range(5)]
        feed_1 = container.items[0]

        reader.beginAddItemTagTransaction()
        for tag in tags:
            reader.addItemTag(feed_1, 'user/-/label/' + tag)
        reader.commitAddItemTagTransaction()

        #reload now
        container.clearItems()
        container.loadItems()
        feed_2 = container.items[0]

        # figure out if all tags were returned
        tags_exist = [any(map(lambda tag: tag in x, tags)) for x in feed_2.data['categories']]
        tag_exist_count = sum([1 for x in tags_exist if x])
        self.assertEqual(5, tag_exist_count)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
