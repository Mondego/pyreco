__FILENAME__ = ds_import
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.db.models.loading import get_model
from django.forms.models import model_to_dict

import sys 
reload(sys) 
sys.setdefaultencoding('utf-8') 

import json
import urllib
import urllib2
import duoshuo
import ast

DUOSHUO_SHORT_NAME = getattr(settings, "DUOSHUO_SHORT_NAME", None)
DUOSHUO_SECRET = getattr(settings, "DUOSHUO_SECRET", None)


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not args:
            raise CommandError('Tell me what\'s data you want synchronization (user/thread/comment)')
        if not DUOSHUO_SHORT_NAME or not DUOSHUO_SECRET:
            raise CommandError('Before you can sync you need to set DUOSHUO_SHORT_NAME and DUOSHUO_SECRET')
        else:
            api = duoshuo.DuoshuoAPI(short_name=DUOSHUO_SHORT_NAME, secret=DUOSHUO_SECRET)
            data = {
                'secret' : DUOSHUO_SECRET,
                'short_name' : DUOSHUO_SHORT_NAME,
            }
        if args[0] == 'user':
            api_url = '%s://%s.duoshuo.com/api/users/import.json' % (api.uri_schema, DUOSHUO_SHORT_NAME)
            users = User.objects.all()
            users_data = {}
            for user in users:
                avatar = user.get_profile().avatar and user.get_profile().avatar or ''

                data['users[%s][user_key]'% user.id] = user.id
                data['users[%s][name]'% user.id] = user.username
                data['users[%s][email]'% user.id] = user.email
                data['users[%s][avatar]'% user.id] = avatar


            data = urllib.urlencode(data)
            response = urllib2.urlopen(api_url, data).read()

            print '%d %s is success import to Duoshuo' % (len(users), len(users) > 1 and 'users' or 'user')

        elif args[0] == 'comment':
            # api_url = '%s://%s.duoshuo.com/api/posts/import.json' , (api.uri_schema, DUOSHUO_SHORT_NAME) 
            
            # try:
            #     threads = ast.literal_eval(open('duoshuo/threads.json', 'r').read())
            # except IOError:
            #     threads = ''

            # comments = Comment.objects.all()
            # for comment in comments:
            #     data['posts[%s][post_key]'% comment.id] = comment.id
            #     data['posts[%s][author_key]'% comment.id] = comment.user_id
            #     data['posts[%s][author_name]'% comment.id] = comment.user_name
            #     data['posts[%s][author_email]'% comment.id] = comment.user_email
            #     data['posts[%s][created_at]'% comment.id] = comment.user_email
            #     data['posts[%s][message]'% comment.id] = comment.comment
            #     data['posts[%s][flags]'% comment.id] = 'import'
            #     try:
            #         threads['%s_%s_%s' % (comment.content_type.app_label,comment.content_type.model,comment.content_object.id)]
            #     except:
            #         pass
            #     else:
            #         data['posts[%s][thread_id]'% comment.id] = thread_id

            # print '%d %s was success sync;' % (len(comments), len(comments) > 1 and 'comments' or 'comment')

            raise CommandError('Sorry, now just import user')

        elif args[0] == 'thread':
            # api_url = '%s://%s.duoshuo.com/api/threads/import.json' % (api.uri_schema, DUOSHUO_SHORT_NAME)

            # current_site = Site.objects.get_current()
            # if current_site.domain == 'example.com':
            #     raise CommandError('I need to know your domain name, it should not be example.com')
            # else:
            #     print "\033[0;32;40mAll threads will be import to %s, use Ctrl-D/Ctrl+C to break if this domain name is not correct.\033[0m" % current_site.domain

            # _s = raw_input('Please input the thread model name such as `threads.thread`:')
            # if len(_s.split('.')) != 2:
            #     raise CommandError('Model name is invalid.')
            # else:
            #     print "\033[0;32;40mStart  import thread from %s:\033[0m" % _s
            #     app_label, model_name = [s.lower() for s in _s.split('.')]

            # thread_model = get_model(app_label, model_name)
            # if not thread_model:
            #     raise CommandError('Cant\'t find model: %s.' % _s)

            # try:
            #     thread_model.get_absolute_url
            # except AttributeError:
            #     raise CommandError('Please define a get_absolute_url() method.')

            # thread_schema = {'title': '', 'content': ''}
            # thread_schema['title'] = raw_input('Enter thread title filed name: ')
            # thread_schema['content'] = raw_input('Enter thread content filed name: ')

            # threads = thread_model.objects.all()
            # for thread in threads:
            #     data['threads[%s][thread_key]'% thread.id] = '%s_%s_%s' % (app_label, model_name, str(thread.id))
            #     data['threads[%s][url]'% thread.id] = 'http://%s%s' % (current_site.domain, thread.get_absolute_url())
            #     try:
            #         data['threads[%s][title]'% thread.id] = thread.__getattribute__(thread_schema['title'])
            #     except:
            #         pass

            #     try:
            #         data['threads[%s][content]'% thread.id] = thread.__getattribute__(thread_schema['content'])
            #     except:
            #         pass

            # data = urllib.urlencode(data)
            # response = json.loads(urllib2.urlopen(api_url, data).read())

            # _f = open('duoshuo/threads.json', 'w')
            # _f.write(unicode(response['response']))
            # _f.close()

            # print '%d %s was success sync;' % (len(threads), len(threads) > 1 and 'threads' or 'thread')

            raise CommandError('Sorry, now just import user')
        else:
            raise CommandError('Tell me what\'s data you want synchronization (user/thread/comment)')

    # def _comment_to_threads(self, comment):
    #     thread = comment.
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User

	

########NEW FILE########
__FILENAME__ = duoshuo_tags
# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.template import Library, Node

DUOSHUO_SHORT_NAME = getattr(settings, "DUOSHUO_SHORT_NAME", None)
DUOSHUO_SECRET = getattr(settings, "DUOSHUO_SECRET", None)

register = Library()

class DuoshuoCommentsNode(Node):
    def __init__(self, short_name=DUOSHUO_SHORT_NAME):
        self.short_name = short_name

    def render(self, context):
        code = '''<!-- Duoshuo Comment BEGIN -->
        <div class="ds-thread"></div>
        <script type="text/javascript">
        var duoshuoQuery = {short_name:"%s"};
        (function() {
            var ds = document.createElement('script');
            ds.type = 'text/javascript';ds.async = true;
            ds.src = 'http://static.duoshuo.com/embed.js';
            ds.charset = 'UTF-8';
            (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(ds);
        })();
        </script>
        <!-- Duoshuo Comment END -->''' % self.short_name
        return code
    
def duoshuo_comments(parser, token):
    short_name = token.contents.split()   
    if DUOSHUO_SHORT_NAME:
        return DuoshuoCommentsNode(DUOSHUO_SHORT_NAME)
    elif len(short_name) == 2:
        return DuoshuoCommentsNode(short_name[1])
    else:
        raise template.TemplateSyntaxError, "duoshuo_comments tag takes SHORT_NAME as exactly one argument"
duoshuo_comments = register.tag(duoshuo_comments)

# 生成remote_auth，使用JWT后弃用
# @register.filter
# def remote_auth(value):
#     user = value
#     duoshuo_query = ds_remote_auth(user.id, user.username, user.email)
#     code = '''
#     <script>
#     duoshuoQuery['remote_auth'] = '%s';
#     </script>
#     ''' % duoshuo_query
#     return code
# remote_auth.is_safe = True

########NEW FILE########
__FILENAME__ = tests
# -*- coding:utf-8 -*-
#!/usr/bin/env python

"""
多说API测试文件。作为通用的Python程序，没有使用Django的TestCase
"""
import os
import unittest
try:
    import json
    _parse_json = lambda s: json.loads(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
    except ImportError:
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)

os.sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duoshuo

import utils


class DuoshuoAPITest(unittest.TestCase):
    DUOSHUO_SHORT_NAME = 'official'
    DUOSHUO_SECRET = 'a'*32
    API = duoshuo.DuoshuoAPI(short_name=DUOSHUO_SHORT_NAME, secret=DUOSHUO_SECRET)

    def test_host(self):
        api = self.API
        host = api.host
        self.assertEqual(host, 'api.duoshuo.com')

    def test_get_url(self):
        redirect_uri = 'example.com'
        api = self.API
        url = utils.get_url(api, redirect_uri=redirect_uri)
        self.assertEqual(url,
            'http://%s/oauth2/authorize?client_id=%s&redirect_uri=%s&response_type=code' % 
            (api.host, self.DUOSHUO_SHORT_NAME, redirect_uri)
        )

    def test_user_api(self):
        api = self.API
        response = api.users.profile(user_id=1)
        user_id = response['response']['user_id']

        self.assertEqual(int(user_id), 1)

    # 以下测试要是short_name和secret正确设置

    # def test_log_api(self):
    #     api = self.API
    #     response = api.log.list()
    #     code = response['code']
    #     self.assertEqual(int(code), 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 Duoshuo

import binascii
import base64
import hashlib
import hmac
import time
import urllib
import urllib2
import urlparse
import json
import jwt

try:
    from django.conf import settings
except ValueError, ImportError:
    settings = {}
    settings.DUOSHUO_SECRET = None
    settings.DUOSHUO_SHORT_NAME = None

"""
实现Remote Auth后可以在评论框显示本地身份(已停用，由set_duoshuo_token代替)
Use:
    views.py: sig = remote_auth(key=request.user.id, name=request.user.username, email=request.user.email)
    template/xxx.html: duoshuoQuery['remote_auth'] = {{ sig }}
"""
def remote_auth(user_id, name, email, url=None, avatar=None, DUOSHUO_SECRET=None):
    data = json.dumps({
        'key': user_id,
        'name': name,
        'email': email,
        'url': url,
        'avatar': avatar,
    })
    message = base64.b64encode(data)
    timestamp = int(time.time())
    sig = hmac.HMAC(settings.DUOSHUO_SECRET, '%s %s' % (message, timestamp), hashlib.sha1).hexdigest()
    duoshuo_query = '%s %s %s' % (message, sig, timestamp)
    return duoshuo_query

"""
在评论框显示本地身份
Use:
    from utils import set_duoshuo_token
    response = HttpResponse()
    return set_duoshuo_token(request, response)

"""
def set_duoshuo_token(request, response):
    if (request.user.id):
        token = {
            'short_name': settings.DUOSHUO_SHORT_NAME,
            'user_key': request.user.id,
            'name': request.user.username,
        }
        signed_token = jwt.encode(token, settings.DUOSHUO_SECRET)
        response.set_cookie('duoshuo_token', signed_token)
    return response

def sync_article(article):
    userprofile = request.user.get_profile()
    if userprofile.duoshuo_id:
        author_id = userprofile.duoshuo_id
    else:
        author_id = 0

    api_url = 'http://api.duoshuo.com/threads/sync.json'
    #TODO: get article url from urls.py
    url_hash = hashlib.md5(article.url).hexdigest()
    data = urllib.urlencode({
        'short_name' : DUOSHUO_SHORT_NAME,
        'thread_key' : article.id,
        'url' : article.url,
        'url_hash' : url_hash,
        'author_key' : author_id
    })
    
    response = json.loads(urllib2.urlopen(api_url, data).read())['response']
    return response


def get_url(api, redirect_uri=None):
    if not redirect_uri:
        raise ValueError('Missing required argument: redirect_uri')
    else:
        params = {'client_id': api.short_name, 'redirect_uri': redirect_uri, 'response_type': 'code'}
        return '%s://%s/oauth2/%s?%s' % (api.uri_schema, api.host, 'authorize', \
            urllib.urlencode(sorted(params.items())))

def sync_comment(posts):
    api_url = 'http://56we.duoshuo.com/api/import/comments.json'
    data = urllib.urlencode({
       'data' : posts,
    })
    response = json.loads(urllib2.urlopen(api_url, data).read())
########NEW FILE########
