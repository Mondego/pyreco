__FILENAME__ = album
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Album(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Album>'

    def get(self, id):
        return self._get('/v2/album/%s' % id)

    def new(self, title, desc='', order='desc', privacy='public'):
        return self._post('/v2/albums',
                          title=title, desc=desc,
                          order=order, privacy=privacy)

    def update(self, id, title='', desc='', order='desc', privacy='public'):
        return self._put('/v2/album/%s' % id,
                         title=title, desc=desc,
                         order=order, privacy=privacy)

    def delete(self, id):
        return self._delete('/v2/album/%s' % id)

    def list(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/album/user_created/%s' % user_id,
                         start=start, count=count)

    def liked_list(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/album/user_liked/%s' % user_id,
                         start=start, count=count)

    def photos(self, id, start=DEFAULT_START, count=DEFAULT_COUNT, order='', sortby='time'):
        return self._get('/v2/album/%s/photos' % id,
                         start=start, count=count, order=order, sortby=sortby)

    def like(self, id):
        return self._post('/v2/album/%s/like' % id)

    def unlike(self, id):
        return self._delete('/v2/album/%s/like' % id)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

from pyoauth2 import AccessToken

from .error import DoubanAPIError, DoubanOAuthError

DEFAULT_START = 0
DEFAULT_COUNT = 20


def check_execption(func):
    def _check(*arg, **kws):
        resp = func(*arg, **kws)
        if resp.status >= 400:
            raise DoubanAPIError(resp)
        body = resp.body
        if body:
            return resp.parsed
        return body
    return _check


class DoubanAPIBase(object):

    def __init__(self, access_token):
        self.access_token = access_token
        if not isinstance(self.access_token, AccessToken):
            raise DoubanOAuthError(401, 'UNAUTHORIZED')

    def __repr__(self):
        return '<DoubanAPI Base>'

    @check_execption
    def _get(self, url, **opts):
        return self.access_token.get(url, **opts)

    @check_execption
    def _post(self, url, **opts):
        return self.access_token.post(url, **opts)

    @check_execption
    def _put(self, url, **opts):
        return self.access_token.put(url, **opts)

    @check_execption
    def _patch(self, url, **opts):
        return self.access_token.patch(url, **opts)

    @check_execption
    def _delete(self, url, **opts):
        return self.access_token.delete(url, **opts)

########NEW FILE########
__FILENAME__ = book
# -*- coding: utf-8 -*-

from .subject import Subject


class Book(Subject):

    target = 'book'

    def __repr__(self):
        return '<DoubanAPI Book>'

    def isbn(self, isbn_id):
        return self._get('/v2/book/isbn/%s' % isbn_id)

########NEW FILE########
__FILENAME__ = comment
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Comment(DoubanAPIBase):

    def __init__(self, access_token, target):
        self.access_token = access_token
        self.target = target

    def __repr__(self):
        return '<DoubanAPI Comment>'

    def list(self, target_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/%s/%s/comments' % (self.target, target_id),
                         start=start, count=count)

    def new(self, target_id, content):
        return self._post('/v2/%s/%s/comments' % (self.target, target_id),
                          content=content)

    def get(self, target_id, id):
        return self._get('/v2/%s/%s/comment/%s' % (self.target, target_id, id))

    def delete(self, target_id, id):
        return self._delete('/v2/%s/%s/comment/%s' % (self.target, target_id, id))

########NEW FILE########
__FILENAME__ = discussion
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT
from .comment import Comment


class Discussion(DoubanAPIBase):

    target = 'discussion'

    def __repr__(self):
        return '<DoubanAPI Discussion>'

    def get(self, id):
        return self._get('/v2/discussion/%s' % id)

    def new(self, target, target_id, title, content):
        return self._post('/v2/%s/%s/discussions' % (target, target_id),
                          title=title, content=content)

    def list(self, target, target_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/%s/%s/discussions' % (target, target_id),
                         start=start, count=count)

    def update(self, id, title, content):
        return self._put('/v2/discussion/%s' % id,
                         title=title, content=content)

    def delete(self, id):
        return self._delete('/v2/discussion/%s' % id)

    def comments(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return Comment(self.access_token, self.target).list(id, start=start, count=count)

    @property
    def comment(self):
        return Comment(self.access_token, self.target)

########NEW FILE########
__FILENAME__ = doumail
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Doumail(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Doumail>'

    def get(self, id):
        return self._get('/v2/doumail/%s' % id)

    def inbox(self, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/doumail/inbox', start=start, count=count)

    def outbox(self, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/doumail/outbox', start=start, count=count)

    def unread(self, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/doumail/inbox/unread', start=start, count=count)

    def read(self, id):
        return self._put('/v2/doumail/%s' % id, key='key')

    def reads(self, ids):
        if isinstance(ids, (list, tuple)):
            ids = ','.join(ids)
        return self._put('/v2/doumail/read', ids=ids)

    def delete(self, id):
        return self._delete('/v2/doumail/%s' % id)

    def deletes(self, ids):
        if isinstance(ids, (tuple, list)):
            ids = ','.join(ids)
        return self._post('/v2/doumail/delete', ids=ids)

    def new(self, title, content, receiver_id, captcha_token=None, captcha_string=None):
        return self._post('/v2/doumails',
                          title=title, content=content, receiver_id=receiver_id,
                          captcha_toke=captcha_token, captcha_string=captcha_string)

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-


class DoubanBaseError(Exception):
    def __str__(self):
        return "***%s (%s)*** %s" % (self.status, self.reason, self.msg)


class DoubanOAuthError(DoubanBaseError):
    def __init__(self, status, reason, msg={}):
        self.status = status
        self.reason = reason
        self.msg = {}


class DoubanAPIError(DoubanBaseError):

    def __init__(self, resp):
        self.status = resp.status
        self.reason = resp.reason
        self.msg = resp.parsed

########NEW FILE########
__FILENAME__ = event
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Event(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Event>'

    def get(self, id):
        return self._get('/v2/event/%s' % id)

    def list(self, loc, day_type=None, type=None, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/list',
                         loc=loc, day_type=day_type, type=type, start=start, count=count)

    def search(self, q, loc, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/search', q=q, loc=loc)

    def join(self, id, participate_date=''):
        data = dict(participate_date=participate_date) if participate_date else {}
        return self._post('/v2/event/%s/participants' % id, **data)

    def quit(self, id, participate_date=''):
        data = dict(participate_date=participate_date) if participate_date else {}
        return self._delete('/v2/event/%s/participants' % id, **data)

    def wish(self, id):
        return self._post('/v2/event/%s/wishers' % id)

    def unwish(self, id):
        return self._delete('/v2/event/%s/wishers' % id)

    def participants(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/%s/participants' % id,
                         start=start, count=count)

    def wishers(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/%s/wishers' % id,
                         start=start, count=count)

    def owned(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/user_created/%s' % user_id,
                         start=start, count=count)

    def participated(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/user_participated/%s' % user_id,
                         start=start, count=count)

    def wished(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/event/user_wished/%s' % user_id,
                         start=start, count=count)

########NEW FILE########
__FILENAME__ = guess
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Guess(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Guess>'

########NEW FILE########
__FILENAME__ = miniblog
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_COUNT


class Miniblog(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Miniblog>'

    def get(self, id):
        return self._get('/shuo/v2/statuses/%s' % id)

    def new(self, text, image=None):
        files = dict(image=image) if image else dict()
        return self._post('/shuo/v2/statuses/', text=text, files=files)

    def rec(self, title='', url='', desc='', image=''):
        return self._post('/shuo/v2/statuses/',
                          rec_title=title, rec_url=url,
                          rec_desc=desc, rec_image=image)

    def delete(self, id):
        return self._delete('/shuo/v2/statuses/%s' % id)

    def home_timeline(self, count=DEFAULT_COUNT, since_id=None, until_id=None, category=None):
        return self._get('/shuo/v2/statuses/home_timeline',
                         count=count, since_id=since_id,
                         until_id=until_id, category=category)

    def user_timeline(self, user_id, since_id=None, until_id=None):
        return self._get('/shuo/v2/statuses/user_timeline/%s' % user_id,
                         since_id=since_id, until_id=until_id)

    def like(self, id):
        return self._post('/shuo/v2/statuses/%s/like' % id)

    def unlike(self, id):
        return self._delete('/shuo/v2/statuses/%s/like' % id)

    def likers(self, id):
        return self._get('/shuo/v2/statuses/%s/like' % id)

    def reshare(self, id):
        return self._post('/shuo/v2/statuses/%s/reshare' % id)

    def unreshare(self, id):
        return self._delete('/shuo/v2/statuses/%s/reshare' % id)

    def reshareders(self, id):
        return self._get('/shuo/v2/statuses/%s/reshare' % id)

    def comments(self, id):
        return self._get('/shuo/v2/statuses/%s/comments' % id)

    @property
    def comment(self):
        return MiniblogComment(self.access_token)


class MiniblogComment(DoubanAPIBase):

    def new(self, miniblog_id, text):
        return self._post('/shuo/v2/statuses/%s/comments' % miniblog_id, text=text)

    def get(self, id):
        return self._get('/shuo/v2/statuses/comment/%s' % id)

    def delete(self, id):
        return self._delete('/shuo/v2/statuses/comment/%s' % id)

########NEW FILE########
__FILENAME__ = movie
# -*- coding: utf-8 -*-

from .subject import Subject


class Movie(Subject):

    target = 'movie'

    def __repr__(self):
        return '<DoubanAPI Movie>'

    def celebrity(self, celebrity_id):
        return self._get('/v2/movie/celebrity/%s' % celebrity_id)

    def imdb(self, imdb_id):
        return self._get('/v2/movie/imdb/%s' % imdb_id)

########NEW FILE########
__FILENAME__ = music
# -*- coding: utf-8 -*-

from .subject import Subject


class Music(Subject):

    target = 'music'

    def __repr__(self):
        return '<DoubanAPI Music>'

########NEW FILE########
__FILENAME__ = note
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT
from .comment import Comment


class Note(DoubanAPIBase):

    target = 'note'

    def __repr__(self):
        return '<DoubanAPI Note>'

    def new(self, title, content, privacy='public', can_reply='true'):
        return self._post('/v2/notes',
                          title=title, content=content,
                          privacy=privacy, can_reply=can_reply)

    def get(self, id, format='text'):
        return self._get('/v2/note/%s' % id, format=format)

    def update(self, id, title, content, privacy='public', can_reply='true'):
        return self._put('/v2/note/%s' % id,
                         title=title, content=content,
                         privacy=privacy, can_reply=can_reply)

    def upload_photo(self, id, pid, image, content, layout=None, desc=None):
        kwargs = {
            'pids': 'p_%s' % pid,
            'content': content,
            'layout_%s' % pid: layout,
            'desc_%s' % pid: desc
        }
        files = {
            'image_%s' % pid: image
        }
        return self._post('/v2/note/%s' % id, files=files, **kwargs)

    def delete(self, id):
        return self._delete('/v2/note/%s' % id)

    def like(self, id):
        return self._post('/v2/note/%s/like' % id)

    def unlike(self, id):
        return self._delete('/v2/note/%s/like' % id)

    def list(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/note/user_created/%s' % user_id,
                         start=start, count=count)

    def liked_list(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/note/user_liked/%s' % user_id,
                         start=start, count=count)

    def comments(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return Comment(self.access_token, self.target).list(id, start=start, count=count)

    @property
    def comment(self):
        return Comment(self.access_token, self.target)

########NEW FILE########
__FILENAME__ = online
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class Online(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI Online>'

    def get(self, id):
        return self._get('/v2/online/%s' % id)

    def new(self, title, desc, begin_time, end_time,
            related_url='', cascade_invite='false', tags=''):
        return self._post('/v2/onlines',
                          title=title, desc=desc, tags=tags,
                          begin_time=begin_time, end_time=end_time,
                          related_url=related_url, cascade_invite=cascade_invite)

    def update(self, id, title, desc, begin_time, end_time,
               related_url='', cascade_invite='false', tags=''):
        return self._put('/v2/online/%s' % id,
                         title=title, desc=desc, tags=tags,
                         begin_time=begin_time, end_time=end_time,
                         related_url=related_url, cascade_invite=cascade_invite)

    def delete(self, id):
        return self._delete('/v2/online/%s' % id)

    def join(self, id):
        return self._post('/v2/online/%s/participants' % id)

    def quit(self, id):
        return self._delete('/v2/online/%s/participants' % id)

    def photos(self, id, start=DEFAULT_START, count=DEFAULT_COUNT, order='', sortby='time'):
        return self._get('/v2/online/%s/photos' % id,
                         start=start, count=count, order=order, sortby=sortby)

    def upload(self, id, image, desc=''):
        return self._post('/v2/online/%s/photos' % id,
                          desc=desc, files={'image': image})

    def like(self, id):
        return self._post('/v2/online/%s/like' % id)

    def unlike(self, id):
        return self._delete('/v2/online/%s/like' % id)

    def participants(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/online/%s/participants' % id,
                         start=start, count=count)

    def discussions(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/online/%s/discussions' % id,
                         start=start, count=count)

    @property
    def discussion(self):
        return OnlineDiscussion(self.access_token)

    def list(self, cate='day', start=DEFAULT_START, count=DEFAULT_COUNT):
        # cate: day, week, latest
        return self._get('/v2/onlines', cate=cate, start=start, count=count)

    def created(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/online/user_created/%s' % user_id,
                         start=start, count=count)

    def joined(self, user_id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/online/user_participated/%s' % user_id,
                         start=start, count=count)


class OnlineDiscussion(DoubanAPIBase):

    def new(self, target_id, title, content):
        return self._post('/v2/online/%s/discussions' % target_id,
                          title=title, content=content)

########NEW FILE########
__FILENAME__ = photo
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT
from .comment import Comment


class Photo(DoubanAPIBase):

    target = 'photo'

    def __repr__(self):
        return '<DoubanAPI Photo>'

    def get(self, id):
        return self._get('/v2/photo/%s' % id)

    def new(self, album_id, image, desc=''):
        return self._post('/v2/album/%s' % album_id,
                          desc=desc, files={'image': image})

    def update(self, id, desc):
        return self._put('/v2/photo/%s' % id, desc=desc)

    def delete(self, id):
        return self._delete('/v2/photo/%s' % id)

    def like(self, id):
        return self._post('/v2/photo/%s/like' % id)

    def unlike(self, id):
        return self._delete('/v2/photo/%s/like' % id)

    def comments(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        return Comment(self.access_token, self.target).list(id, start=start, count=count)

    @property
    def comment(self):
        return Comment(self.access_token, self.target)

########NEW FILE########
__FILENAME__ = review
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase


class Review(DoubanAPIBase):

    def __init__(self, access_token, target):
        self.access_token = access_token
        self.target = target

    def new(self, target_id, title, content, rating=''):
        data = {self.target: target_id,
                'title': title,
                'content': content,
                'rating': rating, }
        return self._post('/v2/%s/reviews' % self.target, **data)

    def update(self, id, title, content, rating=''):
        data = {self.target: id,
                'title': title,
                'content': content,
                'rating': rating, }
        return self._put('/v2/%s/review/%s' % (self.target, id), **data)

    def delete(self, id):
        return self._delete('/v2/%s/review/%s' % (self.target, id))

########NEW FILE########
__FILENAME__ = subject
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT
from .review import Review


class Subject(DoubanAPIBase):

    target = None

    def get(self, id):
        return self._get('/v2/%s/%s' % (self.target, id))

    def search(self, q='', tag='', start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/%s/search' % self.target,
                         q=q, tag=tag, start=start, count=count)

    def tags(self, id):
        return self._get('/v2/%s/%s/tags' % (self.target, id))

    def tagged_list(self, id):
        return self._get('/v2/%s/user_tags/%s' % (self.target, id))

    @property
    def review(self):
        return Review(self.access_token, self.target)

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf-8 -*-

from .base import DoubanAPIBase, DEFAULT_START, DEFAULT_COUNT


class User(DoubanAPIBase):

    def __repr__(self):
        return '<DoubanAPI User>'

    def get(self, id):
        return self._get('/v2/user/%s' % id)

    @property
    def me(self):
        return self.get('~me')

    def search(self, q, start=DEFAULT_START, count=DEFAULT_COUNT):
        return self._get('/v2/user', q=q, start=start, count=count)

    def follow(self, id):
        return self._post('/shuo/v2/friendships/create', user_id=id)

    def unfollow(self, id):
        return self._post('/shuo/v2/friendships/destroy', user_id=id)

    def following(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        page = start / count
        return self._get('/shuo/v2/users/%s/following' % id, page=page, count=count)

    def followers(self, id, start=DEFAULT_START, count=DEFAULT_COUNT):
        page = start / count
        return self._get('/shuo/v2/users/%s/followers' % id, page=page, count=count)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

from pyoauth2 import Client, AccessToken
from .api import DoubanAPI


class DoubanClient(DoubanAPI):

    API_HOST = 'https://api.douban.com'
    AUTH_HOST = 'https://www.douban.com'
    TOKEN_URL = AUTH_HOST + '/service/auth2/token'
    AUTHORIZE_URL = AUTH_HOST + '/service/auth2/auth'

    def __init__(self, key, secret, redirect='', scope=''):
        self.redirect_uri = redirect
        self.scope = scope
        self.client = Client(key, secret,
                             site=self.API_HOST,
                             authorize_url=self.AUTHORIZE_URL,
                             token_url=self.TOKEN_URL)
        self.access_token = None

    def __repr__(self):
        return '<DoubanClient OAuth2>'

    @property
    def authorize_url(self):
        return self.client.auth_code.authorize_url(redirect_uri=self.redirect_uri, scope=self.scope)

    def auth_with_code(self, code):
        self.access_token = self.client.auth_code.get_token(code, redirect_uri=self.redirect_uri)

    def auth_with_token(self, token):
        self.access_token = AccessToken(self.client, token)

    def auth_with_password(self, username, password, **opt):
        self.access_token = self.client.password.get_token(username=username, password=password,
                                                           redirect_uri=self.redirect_uri, **opt)

    @property
    def token_code(self):
        return self.access_token and self.access_token.token

    @property
    def refresh_token_code(self):
        return getattr(self.access_token, 'refresh_token', None)

    def refresh_token(self, refresh_token):
        access_token = AccessToken(self.client, token='', refresh_token=refresh_token)
        self.access_token = access_token.refresh()

########NEW FILE########
__FILENAME__ = auth_with_code
from six.moves import input
from douban_client import DoubanClient

KEY = ''
SECRET = ''
CALLBACK = ''

SCOPE = 'douban_basic_common,community_basic_user'
client = DoubanClient(KEY, SECRET, CALLBACK, SCOPE)

print client.authorize_url
code = input('Enter the verification code:')

client.auth_with_code(code)
print client.user.me

########NEW FILE########
__FILENAME__ = auth_with_password
#encoding:utf-8

"""
auth with password

注意：auth_with_password 需要先申请 xAuth 权限

关于 xAuth 权限申请可咨询: api-master[at]douban.com
或者到 http://www.douban.com/group/dbapi/ 寻求帮助

"""

from douban_client import DoubanClient

KEY = ''
SECRET = ''
CALLBACK = ''
SCOPE = 'douban_basic_common,community_basic_user'

client = DoubanClient(KEY, SECRET, CALLBACK, SCOPE)
client.auth_with_password('user_email', 'user_password')

print client.user.me

########NEW FILE########
__FILENAME__ = auth_with_token
from douban_client import DoubanClient

KEY = ''
SECRET = ''
CALLBACK = ''
TOKEN = 'your token'

SCOPE = 'douban_basic_common,community_basic_user'
client = DoubanClient(KEY, SECRET, CALLBACK, SCOPE)

client.auth_with_token(TOKEN)
print client.user.me

########NEW FILE########
__FILENAME__ = framework
# -*- coding: utf-8 -*-

import os
import sys

from six import print_
from six.moves import input, reduce


TEST_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, ROOT_DIR)

from unittest import main, TestCase
from douban_client import DoubanClient
from douban_client.api.error import DoubanAPIError

try:
    from local_config import KEY, SECRET, CALLBACK, SCOPE, TOKEN
except ImportError:
    KEY = ''
    SECRET = ''
    CALLBACK = ''

    SCOPE_MAP = { 'basic': ['douban_basic_common', 'community_basic_user'], }
    SCOPE = ','.join(reduce(lambda x, y: x + y, SCOPE_MAP.values()))
    TOKEN = ''

def get_client():
    client = DoubanClient(KEY, SECRET, CALLBACK, SCOPE)

    token = TOKEN

    if token:
        client.auth_with_token(token)
    else:
        print_('Go to the following link in your browser:')
        print_(client.authorize_url)

        code = input('Enter the verification code and hit ENTER when you\'re done:')
        client.auth_with_code(code)
        print_('token code:', client.token_code)
        print_('refresh token code:', client.refresh_token_code)
    return client

client = get_client()

class DoubanClientTestBase(TestCase):
    def setUp(self):
        pass

    @property
    def client(self):
        return client

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-

import os
import sys

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, ROOT_DIR)

from unittest import main, TestSuite, findTestCases

def get_test_module_names():
    file_names = os.listdir(os.curdir)
    for fn in file_names:
        if fn.startswith('test') and fn.endswith('.py'):
            yield 'tests.' + fn[:-3]

def suite():
    alltests = TestSuite()

    for module_name in get_test_module_names():
        module = __import__(module_name, fromlist=[module_name])
        alltests.addTest(findTestCases(module))

    return alltests


if __name__ == '__main__':
    main(defaultTest='suite')

########NEW FILE########
__FILENAME__ = test_api_album
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiAlbum(DoubanClientTestBase):
    def setUp(self):
        super(TestApiAlbum, self).setUp()
        self.user_id = '40774605'
        self.album_id = '50201880'

    def test_get_album(self):
        ret = self.client.album.get(self.album_id)
        
        self.assertEqual(self.album_id, ret['id'])
        self.assertTrue('liked' in ret)

    def test_new_album(self):
        ret = self.client.album.new('test', desc='ddddddddddddd')
        
        self.assertTrue('id' in ret)
        self.assertTrue('privacy' in ret)
        self.assertTrue('size' in ret)
        self.assertTrue('author' in ret)

    def test_update_album(self):
        new_title = uuid4().hex
        self.client.album.update(self.album_id, new_title, 'new_desc')
        ret = self.client.album.get(self.album_id)
        self.assertEqual(new_title, ret['title'])

    def test_delete_album(self):
        aid = self.client.album.new('test', desc='abcdefg')['id']
        ret = self.client.album.delete(aid)

        self.assertEqual({}, ret)

    def test_album_list_by_user(self):
        ret = self.client.album.list(self.user_id)
        
        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('albums' in ret)
        self.assertTrue(isinstance(ret['albums'], list))

    def test_liked_album(self):
        ret = self.client.album.liked_list(self.user_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('albums' in ret)
        self.assertTrue(isinstance(ret['albums'], list))

    def test_get_photos(self):
        ret = self.client.album.photos(self.album_id)

        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('photos' in ret)
        self.assertTrue(isinstance(ret['photos'], list))

    def test_like_album(self):
        ret = self.client.album.like(self.album_id)

        self.assertEqual({}, ret)

    def test_unlike_album(self):
        ret = self.client.album.unlike(self.album_id)

        self.assertEqual({}, ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_book
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiBook(DoubanClientTestBase):
    def setUp(self):
        super(TestApiBook, self).setUp()
        self.user_id = '40774605'
        self.book_id = '1126080'
        self.review_id = '1084441'
        self.isbn = '9787540457297'

    def test_get_book(self):
        ret = self.client.book.get(self.book_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('author' in ret)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)

    def test_get_book_by_isbn(self):
        ret= self.client.book.isbn(self.isbn)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('author' in ret)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)

    def test_search_book(self):
        ret = self.client.book.search('坦白')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['books'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    # def test_book_reviews(self):
    #     ret = self.client.book.reviews(self.book_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertTrue(isinstance(ret['reviews'], list))
    #     self.assertTrue('start' in ret)
    #     self.assertTrue('count' in ret)
    #     self.assertTrue('total' in ret)

    def test_book_tags(self):
        ret = self.client.book.tags(self.book_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_get_book_tagged_list(self):
        ret = self.client.book.tagged_list('40774605')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_new_update_delete_review(self):

        # new
        title = content = uuid4().hex
        content = content * 10
        ret = self.client.book.review.new(self.book_id, title, content)

        self.assertTrue(isinstance(ret, dict))
        self.assertEqual(content, ret['content'])
        self.assertTrue('author' in ret)

        review_id = ret['id']

        # update
        content = content * 2
        ret = self.client.book.review.update(review_id, title, content)
        self.assertEqual(content, ret['content'])

        # delete
        ret = self.client.book.review.delete(review_id)
        self.assertEqual('OK', ret)


    # def test_get_book_review(self):
    #     ret = self.client.book.review.get(self.review_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertEqual(ret['id'], self.review_id)
    #     self.assertTrue('rating' in ret)
    #     self.assertTrue('author' in ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_discussion
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiDiscussion(DoubanClientTestBase):
    def setUp(self):
        super(TestApiDiscussion, self).setUp()
        self.user_id = '40774605'
        self.discussion_id = '48752833'
        self.target = 'online'
        self.target_id = '10903196'
        self.comment_id = '12939812'
        
        tmp = uuid4().hex

        self.title = tmp
        self.content = tmp
        self.comment_content = uuid4().hex
        self.comment_update_content = uuid4().hex

    def _add_discussion(self):
        return self.client.discussion.new(self.target, self.target_id, self.title, self.content)


    def test_get_discussion(self):
        ret = self.client.discussion.get(self.discussion_id)

        self.assertEqual(self.discussion_id, ret['id'])
        self.assertTrue('author' in ret)
        self.assertTrue('content' in ret)

    def test_update_discussion(self):
        content = title = uuid4().hex
        ret = self.client.discussion.update(self.discussion_id, title, content)

        self.assertTrue(title, ret['title'])
        self.assertTrue(content, ret['content'])

    def test_new_discussion(self):
        ret = self._add_discussion()

        self.assertTrue(self.title, ret['title'])
        self.assertTrue(self.content, ret['content'])
        self.assertTrue(self.target in ret['alt'])
        self.assertTrue(self.target_id in ret['alt'])

    def test_delete_discussion(self):
        dis = self._add_discussion()
        ret = self.client.discussion.delete(dis['id'])

        self.assertEqual({}, ret)

    def test_discussion_list(self):
        ret = self.client.discussion.list(self.target, self.target_id)

        self.assertTrue(isinstance(ret['discussions'], list))

    def test_discussion_comments(self):
        ret = self.client.discussion.comments(self.discussion_id)

        self.assertTrue(isinstance(ret['comments'], list))

    def test_get_discussion_comment(self):
        ret = self.client.discussion.comment.get(self.discussion_id, self.comment_id)

        self.assertEqual(self.comment_id, ret['id'])
        self.assertTrue('content' in ret)

    def test_new_delete_discussion_comment(self):
        # new
        ret = self.client.discussion.comment.new(self.discussion_id, self.comment_content)
        
        self.assertTrue('id' in ret)
        self.assertTrue('content' in ret)

        # delete
        comment_id = ret['id']
        ret = self.client.discussion.comment.delete(self.discussion_id, comment_id)

        self.assertEqual({}, ret)
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_doumail
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, DoubanAPIError, main

class TestApiDoumail(DoubanClientTestBase):
    def setUp(self):
        super(TestApiDoumail, self).setUp()
        self.user_id = '51789002'
        self.doumail_id = '263891152'
        self.doumail_ids = ['265897597', '265897596', '265897595']

    def _new_doumail(self):
        title = content = uuid4().hex
        try:
            ret = self.client.doumail.new(title, content, self.user_id)
        except DoubanAPIError as e:
            ret = None
        return ret

    def test_get_doumail(self):
        ret = self.client.doumail.get(self.doumail_id)

        self.assertEqual(self.doumail_id, ret['id'])
        self.assertEqual(self.user_id, ret['receiver']['id'])

    def test_doumail_inbox(self):
        ret = self.client.doumail.inbox()

        self.assertTrue('start' in ret)
        self.assertTrue(isinstance(ret['mails'], list))

    def test_doumail_outbox(self):
        ret = self.client.doumail.outbox()

        self.assertTrue('start' in ret)
        self.assertTrue(isinstance(ret['mails'], list))

    def test_doumail_unread(self):
        ret = self.client.doumail.unread()

        self.assertTrue('start' in ret)
        self.assertTrue(isinstance(ret['mails'], list))

    def test_new_doumail(self):
        ret = self._new_doumail()

        self.assertEqual({}, ret)

    def test_read_doumail(self):
        ret = self.client.doumail.read(self.doumail_id)

        self.assertEqual('R', ret['status'])

    def test_reads_doumail(self):
        ret = self.client.doumail.reads(self.doumail_ids)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['mails'], list))

    def test_delete_doumail(self):
        doumail = self.client.doumail.inbox()
        doumail_id = doumail['mails'][0]['id']
        ret = self.client.doumail.delete(doumail_id)

        self.assertEqual({}, ret)

    def test_deletes_doumail(self):
        doumail = self.client.doumail.inbox()
        doumail_ids = [m['id'] for m in doumail['mails']][:2]
        ret = self.client.doumail.deletes(ids=doumail_ids)

        self.assertEqual({}, ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_error
# -*- coding: utf-8 -*-

from framework import DoubanClientTestBase, DoubanAPIError, main

class TestApiError(DoubanClientTestBase):
    pass


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_event
# -*- coding: utf-8 -*-

from uuid import uuid4
from datetime import datetime
from framework import DoubanClientTestBase, main

class TestApiEvent(DoubanClientTestBase):
    
    def setUp(self):
        self.event_id = '17087697'
        self.user_id = '40774605'
        self.loc = '108288'
        self.participate_date = datetime.now().strftime('%Y-%m-%d')

    def test_get_event(self):
        ret = self.client.event.get(self.event_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertEqual(self.event_id, ret['id'])
        self.assertTrue('loc_id' in ret)
        self.assertTrue('loc_name' in ret)

    def test_get_event_participants(self):
        ret = self.client.event.participants(self.event_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['users'], list))
        self.assertTrue('total' in ret)

    def test_get_event_wishers(self):
        ret = self.client.event.wishers(self.event_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['users'], list))
        self.assertTrue('total' in ret)

    def test_get_user_owned_events(self):
        ret = self.client.event.owned(self.user_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['events'], list))

    def test_get_user_participated_events(self):
        ret = self.client.event.participated(self.user_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['events'], list))

    def test_get_user_wished_events(self):
        ret = self.client.event.wished(self.user_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['events'], list))

    def test_event_list(self):
        ret = self.client.event.list(self.loc)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['events'], list))

    def test_search_event(self):
        ret = self.client.event.search('北京', self.loc)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['events'], list))

    def test_join_event(self):
        ret = self.client.event.join(self.event_id)

        self.assertEqual({}, ret)

    def test_quit_event(self):
        ret = self.client.event.quit(self.event_id)
        
        self.assertEqual({}, ret)

    def test_wish_event(self):
        ret = self.client.event.wish(self.event_id)

        self.assertEqual({}, ret)

    def test_unwish_event(self):
        ret = self.client.event.unwish(self.event_id)

        self.assertEqual({}, ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_guess
# -*- coding: utf-8 -*-

from framework import DoubanClientTestBase, main

class TestApiGuess(DoubanClientTestBase):
    def setUp(self):
        super(TestApiGuess, self).setUp()
        self.user_id = '40774605'

    # def test_guess_notes(self):
    #     ret = self.client.guess.notes(self.user_id)

    #     self.assertTrue(ret.has_key('start'))
    #     self.assertTrue(ret.has_key('count'))
    #     self.assertTrue(ret.has_key('notes'))
    #     self.assertTrue(isinstance(ret['notes'], list))

    # def test_guess_albums(self):
    #     ret = self.client.guess.albums(self.user_id)

    #     self.assertTrue(ret.has_key('start'))
    #     self.assertTrue(ret.has_key('count'))
    #     self.assertTrue(ret.has_key('albums'))
    #     self.assertTrue(isinstance(ret['albums'], list))

    # def test_guess_onlines(self):
    #     ret = self.client.guess.onlines(self.user_id)

    #     self.assertTrue(ret.has_key('start'))
    #     self.assertTrue(ret.has_key('count'))
    #     self.assertTrue(ret.has_key('onlines'))
    #     self.assertTrue(isinstance(ret['onlines'], list))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_miniblog
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, DoubanAPIError, main


class TestApiMiniblog(DoubanClientTestBase):

    def setUp(self):
        super(TestApiMiniblog, self).setUp()
        self.user_id = '40774605'
        self.miniblog_id = '999242853'
        self.comment = uuid4().hex
        self.comment_id = '140907103'
        self.rec_title = 'rec from douban-client'
        self.rec_url = 'https://github.com/douban/douban-client'
        self.rec_desc = 'Python client library for Douban APIs (OAuth 2.0) '
        self.rec_image = 'http://img3.douban.com/view/photo/photo/public/p1850826843.jpg'

    def _gen_text(self):
        return 'test miniblog %s by douban-client'% uuid4().hex

    def _new_miniblog(self, upload=False):
        image = upload and open('douban.png', 'rb')
        ret = self.client.miniblog.new(self._gen_text(), image=image)
        if image:
            image.close()
        return ret

    def test_get_miniblog(self):
        ret = self.client.miniblog.get(self.miniblog_id)
        self.assertTrue(isinstance(ret, dict))

    def test_home_timeline(self):
        ret = self.client.miniblog.home_timeline()
        self.assertTrue(isinstance(ret, list))

    def test_user_timeline(self):
        ret = self.client.miniblog.user_timeline(self.user_id)
        self.assertTrue(isinstance(ret, list))
        self.assertTrue(all([self.user_id == r['user']['id'] for r in ret]))

    def test_new_miniblog(self):
        ret = self._new_miniblog()
        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('id' in ret)

    def test_new_miniblog_with_image(self):
        ret = self._new_miniblog(upload=True)
        self.assertTrue('id' in ret)

    def test_delete_miniblog(self):
        mb = self._new_miniblog()
        mid = mb['id']
        self.client.miniblog.delete(mid)
        func = self.client.miniblog.get
        self.assertRaises(DoubanAPIError, func, mid)

    def test_like_unlike_likers_miniblog(self):
        mb = self._new_miniblog()
        mid = mb['id']
        ret = self.client.miniblog.like(mid)
        self.assertTrue(ret['liked'])

        ret = self.client.miniblog.unlike(mid)
        self.assertFalse(ret['liked'])
        ret = self.client.miniblog.likers(mid)
        self.assertTrue(isinstance(ret, list))

    def test_reshare_unreshare_resharers_miniblog(self):
        mid = self.miniblog_id
        # reshare
        self.client.miniblog.reshare(mid)
        ret = self.client.miniblog.get(mid)
        reshared_count = ret['reshared_count']
        self.assertTrue(reshared_count > 0)

        # unreshare
        # 这个豆瓣广播还没有实现接口
        # self.client.miniblog.unreshare(mid)
        # ret = self.client.miniblog.get(mid)
        #
        #self.assertEqual(reshared_count-1, ret['reshared_count'])

        # reshareders
        ret = self.client.miniblog.reshareders(mid)
        self.assertTrue(isinstance(ret, list))

    def test_get_miniblog_comments(self):
        ret = self.client.miniblog.comments(self.miniblog_id)
        self.assertTrue(isinstance(ret, list))
        self.assertTrue(all(['user' in r for r in ret]))

    def test_new_delete_miniblog_comment(self):
        # new
        ret = self.client.miniblog.comment.new(self.miniblog_id, self.comment)
        self.assertEqual(self.comment, ret['text'])
        # delete
        comment_id = ret['id']
        ret = self.client.miniblog.comment.delete(comment_id)
        self.assertEqual(self.comment, ret['text'])

    def test_get_miniblog_comment(self):
        ret = self.client.miniblog.comment.get(self.comment_id)
        self.assertEqual('456', ret['text'])

    def test_miniblog_rec(self):
        ret = self.client.miniblog.rec(title=self.rec_title, url=self.rec_url,
                desc=self.rec_desc, image=self.rec_image)
        self.assertTrue('title' in ret)
        self.assertEqual(len(ret['attachments']), 1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_movie
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiMovie(DoubanClientTestBase):
    def setUp(self):
        super(TestApiMovie, self).setUp()
        self.user_id = '40774605'
        self.movie_id = '1296357'
        self.review_id = '5565362'
        self.imdb = 'tt1345836'
        self.celebrity_id = '1053585'

    def test_get_movie(self):
        ret = self.client.movie.get(self.movie_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('author' in ret)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)

    def test_get_celebrity(self):
        ret = self.client.movie.celebrity(self.celebrity_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('name' in ret)
        self.assertTrue('avatars' in ret)
        self.assertTrue('works'in ret)

    def test_get_movie_by_imdb(self):
        ret= self.client.movie.imdb(self.imdb)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('author' in ret)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)

    def test_search_movie(self):
        ret = self.client.movie.search('蝙蝠侠')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['subjects'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    # def test_movie_reviews(self):
    #     ret = self.client.movie.reviews(self.movie_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertTrue(isinstance(ret['reviews'], list))
    #     self.assertTrue('start' in ret)
    #     self.assertTrue('count' in ret)
    #     self.assertTrue('total' in ret)

    def test_movie_tags(self):
        ret = self.client.movie.tags(self.movie_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_get_movie_tagged_list(self):
        ret = self.client.movie.tagged_list('40774605')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_new_update_delete_review(self):

        # new
        title = content = uuid4().hex
        content = content * 10
        ret = self.client.movie.review.new(self.movie_id, title, content)

        self.assertTrue(isinstance(ret, dict))
        self.assertEqual(content, ret['content'])
        self.assertTrue('author' in ret)

        review_id = ret['id']

        # update
        content = content * 2
        ret = self.client.movie.review.update(review_id, title, content)
        self.assertEqual(content, ret['content'])

        # delete
        ret = self.client.movie.review.delete(review_id)
        self.assertEqual('OK', ret)


    # def test_get_movie_review(self):
    #     ret = self.client.movie.review.get(self.review_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertEqual(ret['id'], self.review_id)
    #     self.assertTrue('rating' in ret)
    #     self.assertTrue('author' in ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_music
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiMusic(DoubanClientTestBase):
    def setUp(self):
        super(TestApiMusic, self).setUp()
        self.user_id = '40774605'
        self.music_id = '1419262'
        self.review_id = '5572975'

    def test_get_music(self):
        ret = self.client.music.get(self.music_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('author' in ret)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)

    def test_search_music(self):
        ret = self.client.music.search('坦白')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['musics'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    # def test_music_reviews(self):
    #     ret = self.client.music.reviews(self.music_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertTrue(isinstance(ret['reviews'], list))
    #     self.assertTrue('start' in ret)
    #     self.assertTrue('count' in ret)
    #     self.assertTrue('total' in ret)

    def test_music_tags(self):
        ret = self.client.music.tags(self.music_id)

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_get_music_tagged_list(self):
        ret = self.client.music.tagged_list('40774605')

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue(isinstance(ret['tags'], list))
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_new_update_delete_review(self):

        # new
        title = content = uuid4().hex
        content = content * 10
        ret = self.client.music.review.new(self.music_id, title, content)

        self.assertTrue(isinstance(ret, dict))
        self.assertEqual(content, ret['content'])
        self.assertTrue('author' in ret)

        review_id = ret['id']

        # update
        content = content * 2
        ret = self.client.music.review.update(review_id, title, content)
        self.assertEqual(content, ret['content'])

        # delete
        ret = self.client.music.review.delete(review_id)
        self.assertEqual('OK', ret)


    # def test_get_music_review(self):
    #     ret = self.client.music.review.get(self.review_id)

    #     self.assertTrue(isinstance(ret, dict))
    #     self.assertEqual(ret['id'], self.review_id)
    #     self.assertTrue('rating' in ret)
    #     self.assertTrue('author' in ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_note
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main


class TestApiNote(DoubanClientTestBase):
    def setUp(self):
        super(TestApiNote, self).setUp()
        self.user_id = '64129916'
        self.note_id = '321263424'
        self.comment_id = '36366425'
        self.comment_content = uuid4().hex
        self.title = 'test note title'
        self.content = 'test note content'
        self.update_content = 'test note was updated'

    def _new_note(self):
        return self.client.note.new(self.title, self.content)

    def test_get_note_list(self):
        ret = self.client.note.list(self.user_id)

        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('notes' in ret)
        self.assertTrue(isinstance(ret['notes'], list))

    def test_get_note(self):
        ret = self.client.note.get(self.note_id)

        self.assertEqual(ret['id'], self.note_id)
        self.assertTrue('title' in ret)
        self.assertTrue('summary' in ret)
        self.assertTrue('content' in ret)

    def test_new_note(self):
        ret = self._new_note()
        self.assertEqual(ret['title'], self.title)
        self.assertTrue('content' in ret)

    def test_update_note(self):
        ret = self._new_note()
        self.assertTrue('id' in ret)
        note_id = ret.get('id')
        self.assertTrue(note_id)
        ret = self.client.note.update(note_id, self.title, self.update_content)

        # TODO
        # 这个地方很奇怪，更新成功，但是应该返回结果类型是 unicode，说好的 JSON 呢
        # self.assertEqual(ret['title'], self.title)
        # self.assertEqual(ret['content'], self.update_content)

        self.assertTrue(self.update_content in ret)

    def test_upload_note_photo(self):
        note = self._new_note()
        self.assertTrue('id' in note)
        note_id = note.get('id')
        self.assertTrue(note_id)

        pid = 1
        content = self.update_content
        layout = 'L'
        desc = 'desc for image%s' % pid
        with open('douban.png', 'rb') as image:
            ret = self.client.note.upload_photo(note_id, pid, image, content, layout, desc)
            self.assertTrue('content' in ret)

    def test_delete_note(self):
        note = self._new_note()
        ret = self.client.note.delete(note['id'])
        self.assertEqual(ret, {})

    def test_get_liked(self):
        ret = self.client.note.liked_list(self.user_id)
        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('notes' in ret)
        self.assertTrue(isinstance(ret['notes'], list))

    def test_like(self):
        ret = self.client.note.like(self.note_id)
        self.assertEqual(ret, {})

    def test_unlike(self):
        ret = self.client.note.unlike(self.note_id)
        self.assertEqual(ret, {})

    def test_note_comments(self):
        ret = self.client.note.comments(self.note_id)
        self.assertTrue(isinstance(ret['comments'], list))

    def test_get_note_comment(self):
        ret = self.client.note.comment.get(self.note_id, self.comment_id)
        self.assertEqual(self.comment_id, ret['id'])
        self.assertTrue('content' in ret)

    def test_new_delete_note_comment(self):
        # new
        ret = self.client.note.comment.new(self.note_id, self.comment_content)
        self.assertTrue('id' in ret)
        self.assertTrue('content' in ret)
        # delete
        comment_id = ret['id']
        ret = self.client.note.comment.delete(self.note_id, comment_id)
        self.assertEqual({}, ret)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_online
# -*- coding: utf-8 -*-

from uuid import uuid4
from datetime import datetime, timedelta
from framework import DoubanClientTestBase, main

t2s = lambda t: t.strftime('%Y-%m-%d %H:%M')
now = datetime.now()
begin_time = t2s(now)
end_time  = t2s(now + timedelta(days=1))

class TestApiOnline(DoubanClientTestBase):
    def setUp(self):
        super(TestApiOnline, self).setUp()
        self.user_id = '40774605'
        self.online_id = '11182611'
        self._title = 'api douban-client test'
        self._desc = 'api test, desc abcdefg hijklmn opq rst uvw xyz, now you see, i can create online.'
        self.discussion_title = uuid4().hex
        self.discussion_content = uuid4().hex


    def _add_online(self):
        return self.client.online.new(self._title, self._desc, begin_time, end_time)


    def test_get_online(self):
        ret = self.client.online.get(self.online_id)

        self.assertEqual(self.online_id, ret['id'])
        self.assertEqual('http://www.douban.com/online/%s/'%self.online_id, ret['alt'])

    def test_new_online(self):
        ret = self._add_online()

        self.assertEqual(self._title, ret['title'])
        self.assertEqual(self._desc, ret['desc'])

    def test_update_online(self):
        online = self._add_online()
        new_title = self._title + 'new'
        new_desc = self._desc + 'new'
        ret = self.client.online.update(online['id'], new_title, new_desc, begin_time, end_time)

        self.assertEqual(new_title, ret['title'])
        self.assertEqual(new_desc, ret['desc'])

    def test_delete_online(self):
        online = self._add_online()
        ret = self.client.online.delete(online['id'])

        self.assertEqual({}, ret)

    def test_join_online(self):
        ret = self.client.online.join(self.online_id)

        self.assertEqual({}, ret)

    def test_quit_online(self):
        ret = self.client.online.quit(self.online_id)

        self.assertEqual({}, ret)

    def test_like_online(self):
        ret = self.client.online.like(self.online_id)

        self.assertEqual({}, ret)

    def test_unlike_online(self):
        ret = self.client.online.unlike(self.online_id)

        self.assertEqual({}, ret)

    def test_get_online_participants(self):
        ret = self.client.online.participants(self.online_id)

        self.assertTrue('total' in ret)
        self.assertTrue(isinstance(ret['users'], list))

    def test_get_online_discussions(self):
        ret = self.client.online.discussions(self.online_id)

        self.assertTrue(isinstance(ret['discussions'], list))

    def test_online_list(self):
        ret = self.client.online.list(cate='day')

        self.assertTrue('total' in ret)
        self.assertTrue(isinstance(ret['onlines'], list))

    def test_new_online_discussion(self):
        online_id = 10903196
        ret = self.client.online.discussion.new(online_id, self.discussion_title, self.discussion_content)

        self.assertTrue(self.discussion_title, ret['title'])
        self.assertTrue(self.discussion_content, ret['content'])

    def test_created_onlines(self):
        ret = self.client.online.created(self.user_id)

        self.assertTrue('total' in ret)
        self.assertTrue(isinstance(ret['onlines'], list))

    def test_joined_onlines(self):
        ret = self.client.online.joined(self.user_id)

        self.assertTrue('total' in ret)
        self.assertTrue(isinstance(ret['onlines'], list))



if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_photo
# -*- coding: utf-8 -*-

from uuid import uuid4
from framework import DoubanClientTestBase, main

class TestApiPhoto(DoubanClientTestBase):
    def setUp(self):
        super(TestApiPhoto, self).setUp()
        self.user_id = '40774605'
        self.album_id = '50201880'
        self.photo_id = '1692008281'
        self.comment_id = '113934719'
        self.comment_content = uuid4().hex

    def _add_photo(self):
        with open('douban.png', 'rb') as image:
            return self.client.photo.new(self.album_id, image)

    def test_get_photo(self):
        ret = self.client.photo.get(self.photo_id)

        self.assertEqual(self.photo_id, ret['id'])

    def test_new_photo(self):
        ret = self._add_photo()

        self.assertEqual(self.album_id, ret['album_id'])
        self.assertTrue('id' in ret)
        self.assertTrue('desc' in ret)
        self.assertTrue('alt' in ret)

    def test_delete_photo(self):
        photo = self._add_photo()
        ret = self.client.photo.delete(photo['id'])

        self.assertEqual({}, ret)

    def test_update_photo(self):
        desc = 'hmm'
        ret = self.client.photo.update(self.photo_id, desc)
        self.assertTrue(desc.startswith(ret['desc']))

    def test_like_photo(self):
        ret = self.client.photo.like(self.photo_id)
        self.assertEqual({}, ret)

    def test_unlike_photo(self):
        ret = self.client.photo.unlike(self.photo_id)
        self.assertEqual({}, ret)

    def test_photo_comments(self):
        ret = self.client.photo.comments(self.photo_id)

        self.assertTrue(isinstance(ret['comments'], list))

    def test_get_photo_comment(self):
        ret = self.client.photo.comment.get(self.photo_id, self.comment_id)

        self.assertEqual(self.comment_id, ret['id'])
        self.assertTrue('content' in ret)

    def test_new_delete_photo_comment(self):
        # new
        ret = self.client.photo.comment.new(self.photo_id, self.comment_content)
        
        self.assertTrue('id' in ret)
        self.assertTrue('content' in ret)

        # delete
        comment_id = ret['id']
        ret = self.client.photo.comment.delete(self.photo_id, comment_id)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_api_user
# -*- coding: utf-8 -*-

from framework import DoubanClientTestBase, main

class TestApiUser(DoubanClientTestBase):

    def setUp(self):
        super(TestApiUser, self).setUp()
        self.user_id = '70920446'

    def test_get_user(self):
        ret = self.client.user.get('liluoliluo')
        self.assertEqual(ret['uid'], 'liluoliluo')

    def test_get_me(self):
        ret = self.client.user.me
        self.assertTrue('id' in ret)

    def test_search(self):
        q = '落'
        ret = self.client.user.search(q)

        self.assertTrue('start' in ret)
        self.assertTrue('count' in ret)
        self.assertTrue('total' in ret)

    def test_follow(self):
        ret = self.client.user.follow(self.user_id)

        self.assertTrue(ret['following'])

    def test_unfollow(self):
        self.client.user.follow(self.user_id)
        ret = self.client.user.unfollow(self.user_id)

        self.assertFalse(ret['following'])

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('uid' in ret)

    def test_followers(self):
        ret = self.client.user.followers(self.user_id)

        self.assertTrue(isinstance(ret, list))
        self.assertTrue(all(['uid' in r for r in ret]))

    # def test_following_followers_of(self):
    #     ret = self.client.user.following_followers_of('51789002')


    # def test_suggestions(self):
    #     ret = self.client.user.suggestions(self.user_id)

    #     self.assertTrue(isinstance(ret, list))
    #     self.assertTrue(all(['uid' in r for r in ret]))



if __name__ == '__main__':
    main()

########NEW FILE########
