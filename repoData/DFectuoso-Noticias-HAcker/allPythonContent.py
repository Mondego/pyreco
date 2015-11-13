__FILENAME__ = admin
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import cgi
import keys
import sys

from google.appengine.ext.db import ReferencePropertyResolveError
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache, taskqueue
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote, Notification 
from random import choice

from libs import bitly
sys.path.insert(0, 'libs/tweepy.zip')
import tweepy
import helper


class ReIndexTankHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().fetch(10000)
    base_url = helper.base_url(self) 
    for post in posts:
      taskqueue.add(url='/admin/re-index-tank-task', params={'post_key': str(post.key()), 'base_url': base_url})
    self.response.out.write("ok")

class ReIndexTankTaskHandler(webapp.RequestHandler):
  def post(self):
    post = db.get(self.request.get('post_key'))
    base_url = self.request.get('base_url')
    helper.indextank_document(base_url, post) 

class DeleteNotificationsOfDeletedHandler(webapp.RequestHandler):
  def get(self):
    notifications = Notification.all().fetch(2000)
    for notification in notifications:
      taskqueue.add(url='/admin/delete-notification-of-deleted-comments', params={'notification_key': str(notification.key())})

  def post(self):
    notification = db.get(self.request.get("notification_key"))
    try:
      post = notification.post
      comment = notification.comment
    except ReferencePropertyResolveError:
      logging.info("WE HAVE A NOTIFICATION That failed")
      notification.target_user.remove_notifications_from_memcache()
      notification.delete()

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/admin/re-index-tank', ReIndexTankHandler),
      ('/admin/re-index-tank-task', ReIndexTankTaskHandler),
      ('/admin/delete-notification-of-deleted-comments', DeleteNotificationsOfDeletedHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = appengine_config
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

from gaesessions import SessionMiddleware
from google.appengine.ext.appstats import recording
import keys

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key=keys.cookie_key)
    app = recording.appstats_wsgi_middleware(app)
    return app


########NEW FILE########
__FILENAME__ = crons
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import cgi
import keys
import sys
import urllib

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime
from gaesessions import delete_expired_sessions

from models import User, Post, Comment, Vote
from random import choice

from libs import bitly
sys.path.insert(0, 'libs/tweepy.zip')
import tweepy
import helper


class TopHandler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-karma').fetch(50)
    post = choice(posts)
    post.calculate_karma()
    self.response.out.write("ok")

def sendMessageToTwitter(self, post):
  bitlyApi = bitly.Api(login=keys.bitly_login, apikey=keys.bitly_apikey) 
  auth = tweepy.OAuthHandler(keys.consumer_key, keys.consumer_secret)
  auth.set_access_token(keys.access_token, keys.access_token_secret)
  twitterapi = tweepy.API(auth)
  url =  keys.base_url_custom_url + "/noticia/" + str(post.key())
  if post.nice_url:
    url =  keys.base_url_custom_url + "/noticia/" + str(post.nice_url)

  shortUrl = bitlyApi.shorten(url)
  title = post.title[:115]
  message = title + "... " + shortUrl
  twitterapi.update_status(message)
  return message

class TwitterHandler(webapp.RequestHandler):
  def get(self):
    if hasattr(keys,'consumer_key') and hasattr(keys,'consumer_secret') and hasattr(keys,'access_token') and hasattr(keys,'access_token_secret') and hasattr(keys,'bitly_login') and hasattr(keys,'bitly_apikey') and hasattr(keys,'base_url') and helper.base_url(self) == keys.base_url:
      posts = Post.all().order('-karma').fetch(20)
      for post in posts:
        if not post.twittered:
          post.twittered = True
          post.put()
          out = sendMessageToTwitter(self,post)
          self.response.out.write("Printed:" + out)  
          return
      self.response.out.write("No more message")
    else:
      self.response.out.write("No keys")

class SessionsHandler(webapp.RequestHandler):
  def get(self):
    while not delete_expired_sessions():
      pass
    self.response.out.write("ok")

class SendToKillmetricsHandler(webapp.RequestHandler):
  def get(self):
    killmetrics_key = ''
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
      killmetrics_key = keys.killmetrics_dev
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
      killmetrics_key = keys.killmetrics_prod

    if killmetrics_key == '':
      return

    killmetrics_base_url = "http://www.killmetrics.com/"

    userUID     = urllib.quote(self.request.get("userUID"))
    sessionUID  = urllib.quote(self.request.get("sessionUID"))
    category    = urllib.quote(self.request.get("category"))
    subcategory = urllib.quote(self.request.get("subcategory"))
    verb        = urllib.quote(self.request.get("verb"))
    user_agent  = urllib.quote(self.request.get("user-agent"))

    url = killmetrics_base_url + '/data-point/'+killmetrics_key+'?userUID='+userUID+'&sessionUID='+sessionUID+'&category='+category+'&subcategory='+subcategory+'&verb='+verb+'&user_agent='+user_agent
    result = urlfetch.fetch(url)

  def post(self):
    self.get() 

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/tasks/update_top_karma', TopHandler),
      ('/tasks/send_top_to_twitter', TwitterHandler),
      ('/tasks/cleanup_sessions', SessionsHandler),
      ('/tasks/send_to_killmetrics', SendToKillmetricsHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = CustomFilters
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

register = webapp.template.create_template_register()
def hacetiempo(value):
  value = value.replace("year", "año")
  value = value.replace("week", "semana")
  value = value.replace("day", "dia")
  value = value.replace("hour", "hora")
  value = value.replace("minute", "minuto")
  return value

register.filter(hacetiempo)



########NEW FILE########
__FILENAME__ = APIGitHubHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')



class Handler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_github")
    if json is None:
      users = User.all().filter("github !=", "").fetch(1000)
      github_user_string = [{u.nickname:u.github} for u in users]
      json = simplejson.dumps({'github_users':github_user_string})
      memcache.add("api_github",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)



########NEW FILE########
__FILENAME__ = APIHackerNewsHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_hackernews")
    if json is None:
      users = User.all().filter("hnuser !=", "").fetch(1000)
      hackernews_user_string = [{u.nickname:u.hnuser} for u in users]
      json = simplejson.dumps({'hackernews_users':hackernews_user_string})
      memcache.add("api_hackernews",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)



########NEW FILE########
__FILENAME__ = APITwitterHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    json = memcache.get("api_twitter")
    if json is None:
      users = User.all().filter("twitter !=", "").fetch(1000)
      twitter_user_string = [{u.nickname:u.twitter} for u in users]
      json = simplejson.dumps({'twitter_users':twitter_user_string})
      memcache.add("api_twitter",json,3600)

    if(self.request.get('callback')):
      self.response.headers['Content-Type'] = "application/javascript"
      self.response.out.write(self.request.get('callback')+'(' + json + ')')
    else:
      self.response.headers['Content-Type'] = "application/json"
      self.response.out.write(json)




########NEW FILE########
__FILENAME__ = CommentReplyHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,comment_id):
    session = get_current_session()
    if hasattr(keys, 'comment_key'):
      comment_key = keys.comment_key
    if session.has_key('user'):
      user = session['user']
    try:
      comment = db.get(comment_id)
      self.response.out.write(template.render('templates/comment.html', locals()))
    except db.BadKeyError:
      self.redirect('/')


  def post(self,comment_id):
    session = get_current_session()
    if session.has_key('user'):
      message = helper.sanitizeHtml(self.request.get('message'))
      user = session['user']
      key = self.request.get('comment_key')
      if len(message) > 0 and key == keys.comment_key:
        try:
          parentComment = db.get(comment_id)
          comment = Comment(message=message,user=user,post=parentComment.post, father=parentComment)
          comment.put()
          helper.killmetrics("Comment","Child", "posted", session, "",self)
          comment.post.remove_from_memcache()
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
          Notification.create_notification_for_comment_and_user(comment,parentComment.user)
          self.redirect('/noticia/' + str(parentComment.post.key()))
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/responder/' + comment_id)
    else:
      self.redirect('/login')



########NEW FILE########
__FILENAME__ = EditCommentHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self, comment_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        comment = db.get(helper.parse_post_id(comment_id))
        if comment.can_edit():
          self.response.out.write(template.render('templates/edit-comment.html', locals()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')
    else:
      self.redirect('/')

  def post(self, comment_id):
    session = get_current_session()
    message = helper.sanitizeHtml(self.request.get('message'))

    if session.has_key('user'):
      user = session['user']
      try:
        comment = db.get(helper.parse_post_id(comment_id))
        if comment.can_edit():
          if message is not None:
            comment.message = message
          comment.edited = True
          comment.put()
          self.redirect('/noticia/' + str(comment.post.key()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')  
    else:
      self.redirect('/')



########NEW FILE########
__FILENAME__ = EditPostHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random
import indextank

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        post = db.get(helper.parse_post_id(post_id))
        if post.can_edit():
          self.response.out.write(template.render('templates/edit-post.html', locals()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')
    else:
      self.redirect('/')

  def post(self, post_id):
    session = get_current_session()
    title = helper.sanitizeHtml(self.request.get('title'))
    message = helper.sanitizeHtml(self.request.get('message'))

    if session.has_key('user'):
      user = session['user']
      try:
        post = db.get(helper.parse_post_id(post_id))
        if post.can_edit():
          if len(title) > 0:
            post.title = title
          if post.message is not None and message is not None:
            post.message = message
          post.edited = True
          post.put()
	  
	  #index with indextank
	  helper.indextank_document(helper.base_url(self), post)

	  self.redirect('/noticia/' + str(post.key()))
        else:
          self.redirect('/')
      except db.BadKeyError:
        self.redirect('/')  
    else:
      self.redirect('/')




########NEW FILE########
__FILENAME__ = FAQHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
 
    self.response.out.write(template.render('templates/faq.html', locals()))



########NEW FILE########
__FILENAME__ = GuidelinesHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
 
    self.response.out.write(template.render('templates/guidelines.html', locals()))




########NEW FILE########
__FILENAME__ = LeaderHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']

    users = User.all().order("-karma").fetch(50)
    i = 1
    for u in users:
      u.pos = i
      i = i + 1
    self.response.out.write(template.render('templates/leaders.html', locals()))




########NEW FILE########
__FILENAME__ = LoginHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')


class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('register_error'):
      register_error = session.pop('register_error')
    if session.has_key('login_error'):
      login_error = session.pop('login_error')
    if session.has_key('login_error_nickname'):
      login_error_nickname = session.pop('login_error_nickname')
    if session.has_key('sucess'):
      success = session.pop('success') # creo que hace falta una forma de homologar los mensajes de error/success para que no tenga que estar en todos los templates
                                       # y tampoco se tenga que poner un IF por cada tipo de mensaje

    if session.has_key('user'):
      user = session['user']
      self.redirect('/logout')
    else:
      self.response.out.write(template.render('templates/login.html', locals()))

  def post(self):
    session = get_current_session()
    nickname = helper.sanitizeHtml(self.request.get('nickname'))
    password = helper.sanitizeHtml(self.request.get('password'))
    password = User.slow_hash(password);

    user = User.all().filter('lowercase_nickname =',nickname.lower()).filter('password =',password).fetch(1)
    if len(user) == 1:
      
      helper.killmetrics("Login",nickname, "do", session, "",self)
      random_id = helper.get_session_id(session)
      if session.is_active():
        session.terminate()
      session.regenerate_id()
      session['random_id'] = random_id
      session['user'] = user[0]
      self.redirect('/')
    else:
      session['login_error'] = "Usuario y password incorrectos"
      session['login_error_nickname'] = nickname
      self.redirect('/login')



########NEW FILE########
__FILENAME__ = LogoutHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# User Mgt Handlers
class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    helper.killmetrics("Logout","", "do", session, "",self)
    random_id = helper.get_session_id(session) 
    if session.is_active():
      session.terminate()
    session.regenerate_id()
    session["random_id"] = random_id
    self.redirect('/')


########NEW FILE########
__FILENAME__ = MainHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# Front page
class Handler(webapp.RequestHandler):
  def get(self):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    if (page * perPage) < Post.get_cached_count():
      nextPage = page + 1

    session = get_current_session()
    

    if session.has_key('user'):
      user = session['user']
    #### Killmetrics test
    killmetrics_session_id = helper.get_session_id(session)
    killmetrics_key = ''
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
      killmetrics_key = keys.killmetrics_dev
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
      killmetrics_key = keys.killmetrics_prod
    #### Killmetrics test

    posts = Post.all().order('-karma').fetch(perPage, realPage * perPage)
    prefetch.prefetch_posts_list(posts)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    if helper.is_json(self.request.url):
      posts_json = [p.to_json() for p in posts]
      if(self.request.get('callback')):
        self.response.headers['Content-Type'] = "application/javascript"
        self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
      else:
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(simplejson.dumps({'posts':posts_json}))
    else:
      self.response.out.write(template.render('templates/main.html', locals()))



########NEW FILE########
__FILENAME__ = NewHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    if (page * perPage) < Post.get_cached_count():
      nextPage = page + 1

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    #### Killmetrics test
    killmetrics_session_id = helper.get_session_id(session)
    killmetrics_key = ''
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
      killmetrics_key = keys.killmetrics_dev
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
      killmetrics_key = keys.killmetrics_prod
    #### Killmetrics test


    posts = Post.all().order('-created').fetch(perPage,perPage * realPage)
    prefetch.prefetch_posts_list(posts)
    i = perPage * realPage + 1
    for post in posts:
      post.number = i
      i = i + 1
    if helper.is_json(self.request.url):
      posts_json = [p.to_json() for p in posts]
      if(self.request.get('callback')):
        self.response.headers['Content-Type'] = "application/javascript"
        self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
      else:
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(simplejson.dumps({'posts':posts_json}))
    else:
      self.response.out.write(template.render('templates/main.html', locals()))


########NEW FILE########
__FILENAME__ = NewPasswordHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('forgotten_password_error'):
      forgotten_password_error = session.pop('forgotten_password_error')
    if session.has_key('forgotten_password_ok'):
      forgotten_password_ok = session.pop('forgotten_password_ok')
    
    if session.has_key('user'):
      user = session['user']
      self.redirect('/logout')
    else:
      self.response.out.write(template.render('templates/forgotten-password.html', locals()))

  def post(self):
    session = get_current_session()
    email = helper.sanitizeHtml(self.request.get('email'))
    if len(email) > 1:      
      users = User.all().filter("email =", email).fetch(1)
      if len(users) == 1:
        if session.is_active():
          session.terminate()
        user = users[0]
        Ticket.deactivate_others(user)
        ticket = Ticket(user=user,code=Ticket.create_code(user.password + user.nickname + str(random.random())))
        ticket.put()
        code = ticket.code
        host = self.request.url.replace(self.request.path,'',1)
       
        mail.send_mail(sender="NoticiasHacker <dfectuoso@noticiashacker.com>",
          to=user.nickname + "<"+user.email+">",
          subject="Liga para restablecer password",
          html=template.render('templates/mail/forgotten-password-email.html', locals()),
          body=template.render('templates/mail/forgotten-password-email-plain.html', locals()))
      
        session['forgotten_password_ok'] = "Se ha enviado un correo electrónico a tu bandeja de entrada con las instrucciones"
      else:
        session['forgotten_password_error'] = "El correo electronico <strong>"+ email +"</strong> no existe en nuestra base de datos"
    else:
      session['forgotten_password_error'] = "Debes especificar tu correo electrónico"
     
    self.redirect('/olvide-el-password')



########NEW FILE########
__FILENAME__ = NotificationsInboxAllHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# Notifications
class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      page = helper.sanitizeHtml(self.request.get('pagina'))
      perPage = 10
      page = int(page) if page else 1
      realPage = page - 1
      inboxAll = True
      if realPage > 0:
        prevPage = realPage
      if (page * perPage) < Notification.all().filter("target_user =",user).count():
        nextPage = page + 1
 
      notifications = Notification.all().filter("target_user =",user).order("-created").fetch(perPage,perPage * realPage)
      prefetch.prefetch_refprops(notifications,Notification.post,Notification.comment,Notification.sender_user)
      self.response.out.write(template.render('templates/notifications.html', locals()))
    else:
      self.redirect('/login')



########NEW FILE########
__FILENAME__ = NotificationsInboxHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# Notifications
class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      page = helper.sanitizeHtml(self.request.get('pagina'))
      perPage = 10
      page = int(page) if page else 1
      realPage = page - 1
      inbox = True
      if realPage > 0:
        prevPage = realPage
      if (page * perPage) < Notification.all().filter("target_user =",user).filter("read =",False).count():
        nextPage = page + 1
 
      notifications = Notification.all().filter("target_user =",user).filter("read =",False).order("-created").fetch(perPage,perPage * realPage)
      prefetch.prefetch_refprops(notifications,Notification.post,Notification.comment,Notification.sender_user)
      self.response.out.write(template.render('templates/notifications.html', locals()))
    else:
      self.redirect('/login')


########NEW FILE########
__FILENAME__ = NotificationsMarkAsReadHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,notification_key):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        notification = db.get(helper.sanitizeHtml(notification_key))
        if str(notification.target_user.key()) == str(user.key()):
          notification.read = True
          notification.put()
          user.remove_notifications_from_memcache()
          self.response.out.write('Ok')
        else:
          self.response.out.write('Bad')
      except db.BadKeyError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')



########NEW FILE########
__FILENAME__ = PostHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# News Handlers
class Handler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    #### Killmetrics test
    killmetrics_session_id = helper.get_session_id(session)
    killmetrics_key = ''
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
      killmetrics_key = keys.killmetrics_dev
    if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
      killmetrics_key = keys.killmetrics_prod
    #### Killmetrics test
    if hasattr(keys, 'comment_key'):
      comment_key = keys.comment_key

    try:
      post = Post.all().filter('nice_url =', helper.parse_post_id( post_id ) ).get()
      if  post  == None: #If for some reason the post doesn't have a nice url, we try the id. This is also the case of all old stories
        post = db.get( helper.parse_post_id( post_id ) ) 

      comments = Comment.all().filter("post =", post.key()).order("-karma").fetch(1000)
      comments = helper.order_comment_list_in_memory(comments)
      prefetch.prefetch_comment_list(comments)
      display_post_title = True
      prefetch.prefetch_posts_list([post])
      if helper.is_json(post_id):
        comments_json = [c.to_json() for c in comments if not c.father_ref()] 
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'post':post.to_json(),'comments':comments_json})+')')
        else:
          self.response.headers['Content-Type'] = "application/json"
          self.response.out.write(simplejson.dumps({'post':post.to_json(),'comments':comments_json}))
      else:
        self.response.out.write(template.render('templates/post.html', locals()))
    except db.BadKeyError:
      self.redirect('/')

  # This adds root level comments
  def post(self, post_id):
    session = get_current_session()
    if session.has_key('user'):
      message = helper.sanitizeHtml(self.request.get('message'))
      user = session['user']
      key = self.request.get('comment_key')
      if len(message) > 0 and key == keys.comment_key:
        try:
          post = Post.all().filter('nice_url =', helper.parse_post_id( post_id ) ).get()
          if post  == None: #If for some reason the post doesn't have a nice url, we try the id. This is also the case of all old stories
            post = db.get( helper.parse_post_id( post_id ) ) 

          post.remove_from_memcache()
          comment = Comment(message=message,user=user,post=post)
          comment.put()
          helper.killmetrics("Comment","Root", "posted", session, "",self)
          vote = Vote(user=user, comment=comment, target_user=user)
          vote.put()
          Notification.create_notification_for_comment_and_user(comment,post.user)
          self.redirect('/noticia/' + post_id)
        except db.BadKeyError:
          self.redirect('/')
      else:
        self.redirect('/noticia/' + post_id)
    else:
      self.redirect('/login')




########NEW FILE########
__FILENAME__ = ProfileHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

# User Handlers
class Handler(webapp.RequestHandler):
  def get(self,nickname):
    nickname = helper.parse_post_id(nickname)
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    if session.has_key('profile_saved'):
      profile_saved = session.pop('profile_saved')
    profiledUser = User.all().filter('nickname =',nickname).fetch(1)
    if len(profiledUser) == 1:
      profiledUser = profiledUser[0]
      #TODO fix this horrible way of testing for the user
      if session.has_key('user') and user.key() == profiledUser.key():
        my_profile = True
      if helper.is_json(self.request.url):
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'nickname':profiledUser.nickname, 'karma':profiledUser.karma,'twitter':profiledUser.twitter,'github':profiledUser.github,'hn':profiledUser.hnuser})+')')
        else:
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(simplejson.dumps({'nickname':profiledUser.nickname,'twitter':profiledUser.twitter, 'karma':profiledUser.karma, 'github':profiledUser.github,'hn':profiledUser.hnuser}))
      else:
        self.response.out.write(template.render('templates/profile.html', locals()))
    else:
      self.redirect('/')

  def post(self,nickname):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      profiledUser = User.all().filter('nickname =',nickname).fetch(1)
      if len(profiledUser) == 1:
        profiledUser = profiledUser[0]
      if user.key() == profiledUser.key():
        about = helper.sanitizeHtml(self.request.get('about'))
        hnuser = helper.sanitizeHtml(self.request.get('hnuser'))
        location = helper.sanitizeHtml(self.request.get('location'))
        github = helper.sanitizeHtml(self.request.get('github'))
        twitter = helper.sanitizeHtml(self.request.get('twitter'))
        email = helper.sanitizeHtml(self.request.get('email'))
        url = helper.sanitizeHtml(self.request.get('url'))

        user.about = about
        user.location = location
        user.github = github
        user.hnuser = hnuser
        user.twitter = twitter
        if len(User.all().filter("email",email).fetch(1)) == 0:
          try:
            user.email = email
          except db.BadValueError:
            pass
        try:
          user.url = url
        except db.BadValueError:
          pass
        user.put()
        my_profile = True
        session['profile_saved'] = True 
        self.redirect('/perfil/' + user.nickname)
      else:
        self.redirect('/')
    else:
      self.redirect('/login')


########NEW FILE########
__FILENAME__ = RecoveryHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,code):
    session = get_current_session()
    code = helper.parse_post_id(code)
    if session.has_key('error'):
      error = session['error']
    
    ticket = Ticket.all().filter('code',code).filter('is_active',True).fetch(1)
    if len(ticket) == 1:
      ticket = ticket[0]
      self.response.out.write(template.render('templates/new-password.html', locals()))
    else:
      self.redirect('/')

  def post(self,code):
    session = get_current_session()
    code = helper.parse_post_id(helper.sanitizeHtml(self.request.get('code')))
    password = helper.sanitizeHtml(self.request.get('password'))
    password_confirm = helper.sanitizeHtml(self.request.get('password_confirm'))
    if password != password_confirm :
      session['error'] = "Ocurrió un error al confirmar el password"
      self.redirect('/recovery/'+code)
      return
    ticket = Ticket.all().filter('code',code).filter('is_active',True).fetch(1)
    if len(ticket) == 1:
      ticket = ticket[0]
      user = ticket.user
      user.password = User.slow_hash(password)
      user.put()
      ticket.is_active = False
      ticket.put()
      session['success'] = "Se ha cambiado el password correctamente, ya puedes iniciar sesión con tus nuevas credenciales"
      self.redirect('/login')
    else:
      self.redirect('/')




########NEW FILE########
__FILENAME__ = RegisterHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def post(self):
    session = get_current_session()
    nickname = helper.sanitizeHtml(self.request.get('nickname'))
    password = helper.sanitizeHtml(self.request.get('password'))
    
    if len(nickname) > 1 and len(password) > 1:
      password = User.slow_hash(password);
      already = User.all().filter("lowercase_nickname =",nickname.lower()).fetch(1)
      if len(already) == 0:
        user = User(nickname=nickname, lowercase_nickname=nickname.lower(),password=password, about="")
        user.put()
        helper.killmetrics("Register",nickname, "do", session, "",self)
        random_id = helper.get_session_id(session) 
        if session.is_active():
          session.terminate()
        session.regenerate_id()
        session['random_id'] = random_id
        session['user'] = user
        self.redirect('/')
      else:
        session['register_error'] = "Ya existe alguien con ese nombre de usuario <strong>" + nickname + "</strong>"
        self.redirect('/login')
    else:
      session['register_error'] = "Porfavor escribe un username y un password"
      self.redirect('/login')




########NEW FILE########
__FILENAME__ = RssHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    posts = Post.all().order('-created').fetch(20)
    prefetch.prefetch_posts_list(posts)

    items = []
    for post in posts:
      if len(post.message) == 0:
        rss_poster = '<a href="'+post.url+'">'+post.url+'</a>'
      else:
        rss_poster = post.message
      rss_poster += ' por <a href="'+helper.base_url(self)+'/perfil/'+post.user.nickname+'">'+post.user.nickname+'</a>'

      link = helper.base_url(self)+'/noticia/' + str(post.key())
      if post.nice_url:
        link = helper.base_url(self)+'/noticia/' + str(post.nice_url)

      items.append(PyRSS2Gen.RSSItem(
          title = post.title,
          link = link,
          description = rss_poster,
          guid = PyRSS2Gen.Guid("guid1"),
          pubDate = post.created
      ))

    rss = PyRSS2Gen.RSS2(
            title = "Noticias Hacker",
            link = "http://noticiashacker.com/",
            description = "Noticias Hacker",
            lastBuildDate = datetime.now(),
            items = items
          )
    print 'Content-Type: text/xml'
    self.response.out.write(rss.to_xml('utf-8'))




########NEW FILE########
__FILENAME__ = SubmitNewStoryHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    if session.has_key('post_error'):
      post_error = session.pop('post_error')

    if session.has_key('user'):
      if hasattr(keys, 'comment_key'):
        comment_key = keys.comment_key
      user = session['user']
      #### Killmetrics test
      killmetrics_session_id = helper.get_session_id(session)
      killmetrics_key = ''
      if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_dev') and helper.base_url(self) != keys.base_url:
        killmetrics_key = keys.killmetrics_dev
      if hasattr(keys,'base_url') and hasattr(keys,'killmetrics_prod') and (helper.base_url(self) == keys.base_url or helper.base_url(self) == keys.base_url_custom_url):
        killmetrics_key = keys.killmetrics_prod
      #### Killmetrics test



      get_url = helper.sanitizeHtml(self.request.get('url_bookmarklet'))
      get_title = helper.sanitizeHtml(self.request.get('title_bookmarklet'))
      self.response.out.write(template.render('templates/submit.html', locals()))
    else:
      self.redirect('/login')

  def post(self):
    session = get_current_session()
    url = self.request.get('url')
    title = helper.sanitizeHtml(self.request.get('title'))
    message = helper.sanitizeHtml(self.request.get('message'))
    nice_url = helper.sluglify(title)
    key = self.request.get('comment_key')
 
    if session.has_key('user') and key == keys.comment_key:
      if len(nice_url) > 0:
        user = session['user']
        if len(message) == 0: #is it a post or a message?
          #Check that we don't have the same URL within the last 'check_days'
          since_date = date.today() - timedelta(days=7)
          q = Post.all().filter("created >", since_date).filter("url =", url).count()
          url_exists = q > 0
          q = Post.all().filter("nice_url", nice_url).count()
          nice_url_exist = q > 0
          try:
            if not url_exists:
              if not nice_url_exist:
                post = Post(url=url,title=title,message=message, user=user, nice_url=nice_url)
                post.put()
                helper.killmetrics("Submit","Link", "do", session, "",self)
                vote = Vote(user=user, post=post, target_user=post.user)
                vote.put()
                Post.remove_cached_count_from_memcache()
 	
                #index with indextank
                helper.indextank_document( helper.base_url(self), post)
                
                self.redirect('/noticia/' + str(post.nice_url));
              else:
                session['post_error'] = "Este titulo ha sido usado en una noticia anterior"
                self.redirect('/agregar')
            else:
              session['post_error'] = "Este link ha sido entregado en los ultimo 7 dias"
              self.redirect('/agregar')
          except db.BadValueError:
            session['post_error'] = "El formato del link no es valido"
            self.redirect('/agregar')
        else:
          q = Post.all().filter("nice_url", nice_url).count()
          nice_url_exist = q > 0
          if not nice_url_exist:
            post = Post(title=title,message=message, user=user, nice_url=nice_url)
            post.put()
            helper.killmetrics("Submit","Post", "do", session, "",self)
            post.url = helper.base_url(self) + "/noticia/" + post.nice_url
            post.put()
            Post.remove_cached_count_from_memcache()
            vote = Vote(user=user, post=post, target_user=post.user)
            vote.put()

	    #index with indextank
	    helper.indextank_document( helper.base_url(self), post)
            
	    self.redirect('/noticia/' + post.nice_url);
          else:
            session['post_error'] = "Este titulo ha sido usado en una noticia anterior"
            self.redirect('/agregar')
      else:
        session['post_error'] = "Necesitas agregar un titulo"
        self.redirect('/agregar')
    else:
      self.redirect('/login')

########NEW FILE########
__FILENAME__ = ThreadsHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,nickname):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    perPage = 6
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage
    # this is used to tell the template to include the topic
    threads = True

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    thread_user = User.all().filter('lowercase_nickname =',nickname.lower()).fetch(1)
    if len(thread_user) > 0:
      thread_user = thread_user[0]
      user_comments = Comment.all().filter('user =',thread_user).order('-created').fetch(perPage, realPage * perPage)
      comments = helper.filter_user_comments(user_comments, thread_user)
      if (page * perPage) < Comment.all().filter('user =', thread_user).count():
        nextPage = page + 1
      self.response.out.write(template.render('templates/threads.html', locals()))
    else:
      self.redirect('/')


########NEW FILE########
__FILENAME__ = UpVoteCommentHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self,comment_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        comment = db.get(comment_id)
        if not comment.already_voted():
          vote = Vote(user=user, comment=comment, target_user=comment.user)
          vote.put()
          helper.killmetrics("Vote","Comment", "do", session, "",self)
          comment.remove_from_memcache()
          comment.user.remove_from_memcache()
          self.response.out.write('Ok')
        else:
          self.response.out.write('No')
      except db.BadValueError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')




########NEW FILE########
__FILENAME__ = UpVoteHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')


# vote handlers
class Handler(webapp.RequestHandler):
  def get(self,post_id):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      try:
        post = db.get(post_id)
        if not post.already_voted():
          vote = Vote(user=user, post=post, target_user=post.user)
          vote.put()
          post.remove_from_memcache()
          post.user.remove_from_memcache()
          helper.killmetrics("Vote","News", "do", session, "",self)
          self.response.out.write('Ok')
        else:
          self.response.out.write('No')
      except db.BadValueError:
        self.response.out.write('Bad')
    else:
      self.response.out.write('Bad')




########NEW FILE########
__FILENAME__ = UserPostsHandler
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket


#register the desdetiempo filter to print time since in spanish
template.register_template_library('CustomFilters')

class Handler(webapp.RequestHandler):
  def get(self, user):
    page = helper.sanitizeHtml(self.request.get('pagina'))
    target_user_str= helper.sanitizeHtml(helper.parse_post_id(user))
    perPage = 20
    page = int(page) if page else 1
    realPage = page - 1
    if realPage > 0:
      prevPage = realPage

    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
    target_user = User.all().filter('lowercase_nickname =', target_user_str).fetch(1)
    if len(target_user) > 0:
      posts = Post.all().filter('user =',target_user[0]).order('-created').fetch(perPage,perPage * realPage)
      if (page * perPage) < Post.all().filter('user =',target_user[0]).order('-created').count():
        nextPage = page + 1
      prefetch.prefetch_posts_list(posts)
      i = perPage * realPage + 1
      for post in posts:
        post.number = i
        i = i + 1
      if helper.is_json(self.request.url):
        posts_json = [p.to_json() for p in posts]
        if(self.request.get('callback')):
          self.response.headers['Content-Type'] = "application/javascript"
          self.response.out.write(self.request.get('callback')+'('+simplejson.dumps({'posts':posts_json})+');')
        else:
          self.response.headers['Content-Type'] = "application/json"
          self.response.out.write(simplejson.dumps({'posts':posts_json}))
      else:
        self.response.out.write(template.render('templates/main.html', locals()))
    else:
      self.redirect('/')




########NEW FILE########
__FILENAME__ = helper
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import random
import string
import prefetch
import keys
import indextank
from urlparse import urlparse
from models import User, Post, Comment, Vote 
from django.utils.html import escape
from django.template.defaultfilters import slugify
from google.appengine.api import taskqueue

def sanitizeHtml(value):
  return escape(value)

def is_json(value):
  if value.find('.json') >= 0:
    return True
  else:
    return False

def parse_post_id(value):
  if is_json(value):
    return value.split('.')[0]
  else:
    return value

def add_childs_to_comment(comment):
  """We need to add the childs of each post because we want to render them in the
     same way we render the Post view. So we need to find all the "preprocessed_childs"
     Now, we also want to hold a reference to them to be able to pre_fetch them
  """
  comment.processed_child = []
  total_childs = []
  for child in comment.childs:
    comment.processed_child.append(child)
    total_childs.append(child)
    total_childs.extend(add_childs_to_comment(child))
  return total_childs

def filter_user_comments(all_comments, user):
  """ This function removes comments that belong to a thread
  which had a comment by the same user as a parent """
  res_comments = []
  for user_comment in all_comments: ### Cycle all the comments and find the ones we care
    linked_comment = user_comment
    while(True):
      if Comment.father.get_value_for_datastore(linked_comment) is None:
        if not [c for c in res_comments if c.key() == user_comment.key()]:
          res_comments.append(user_comment) # we care about the ones that are topmost
        break
      if linked_comment.father.user.key() == user.key():
        if not [c for c in res_comments if c.key() == linked_comment.father.key()]:
          res_comments.append(linked_comment.father) # But we also want to append the "father" ones to avoid having pages with 0 comments
        break
      linked_comment = linked_comment.father
  # Add Childs here
  child_list = []
  for comment in res_comments:
    comment.is_top_most = True
    child_list.extend(add_childs_to_comment(comment))
  prefetch.prefetch_comment_list(res_comments + child_list) #Finally we prefetch everything, 1 super call to memcache
  return res_comments

def get_comment_from_list(comment_key,comments):
  return [comment for comment in comments if comment.key() ==  comment_key]

def order_comment_list_in_memory(comments):
  # order childs for display
  for comment in comments:
    comment.processed_child = []
  for comment in comments:
    father_key = Comment.father.get_value_for_datastore(comment)
    if father_key is not None:
      father_comment = get_comment_from_list(father_key,comments)
      if len(father_comment) == 1:
        father_comment[0].processed_child.append(comment)
  return comments

def base_url(self):
  uri = urlparse(self.request.url)
  return uri.scheme +'://'+ uri.netloc

def sluglify(text):
  return slugify(text)

def indextank_document(base_url, post):
  if not keys.indextank_private_key:
    return
  api = indextank.client.ApiClient(keys.indextank_private_key)

  index = api.get_index(keys.indextank_name_key)
  if base_url  == keys.base_url or base_url == keys.base_url_custom_url:
    index = api.get_index(keys.indextank_name_key_prod)

  nhurl = base_url+ "/noticia/" + str(post.nice_url)
  try:
    index.add_document(nhurl, {'text': post.title + ' ' + (post.message or post.url) + ' ' + post.user.nickname,
	'user':post.user.nickname, 'title':post.title, 'message':post.message, 'url': post.url, 'nhurl': nhurl})
  except indextank.client.HttpException:
      pass

def get_session_id(session):
  if session.has_key('random_id'):
    return session['random_id']
  else:
    char_set = string.ascii_uppercase + string.digits
    str = ''.join(random.sample(char_set,20))
    session['random_id'] = str
    return str

def killmetrics(category,subcategory,verb,session,user,r):
  user_agent = str(r.request.headers['User-Agent'])
  sessionUID = get_session_id(session)
  
  taskqueue.add(url='/tasks/send_to_killmetrics', params={'category':category,'subcategory':subcategory,'verb':verb,'userUID': user, 'sessionUID':sessionUID,'user-agent':user_agent})


########NEW FILE########
__FILENAME__ = anyjson
"""
Wraps the best available JSON implementation available in a common interface
"""

__version__ = "0.2.0"
__author__ = "Rune Halvorsen <runefh@gmail.com>"
__homepage__ = "http://bitbucket.org/runeh/anyjson/"
__docformat__ = "restructuredtext"

"""

.. function:: serialize(obj)

    Serialize the object to JSON.

.. function:: deserialize(str)

    Deserialize JSON-encoded object to a Python object.

.. function:: force_implementation(name)

    Load a specific json module. This is useful for testing and not much else

.. attribute:: implementation

    The json implementation object. This is probably not useful to you,
    except to get the name of the implementation in use. The name is
    available through `implementation.name`.
"""

import sys

implementation = None

"""
.. data:: _modules

    List of known json modules, and the names of their serialize/unserialize
    methods, as well as the exception they throw. Exception can be either
    an exception class or a string.
"""
_modules = [("cjson", "encode", "EncodeError", "decode", "DecodeError"),
            ("jsonlib2", "write", "WriteError", "read", "ReadError"),
            ("jsonlib", "write", "WriteError", "read", "ReadError"),
            ("simplejson", "dumps", TypeError, "loads", ValueError),
            ("json", "dumps", TypeError, "loads", ValueError),
            ("django.utils.simplejson", "dumps", TypeError, "loads",
             ValueError)]
_fields = ("modname", "encoder", "encerror", "decoder", "decerror")


class _JsonImplementation(object):
    """Incapsulates a JSON implementation"""

    def __init__(self, modspec):
        modinfo = dict(zip(_fields, modspec))

        # No try block. We want importerror to end up at caller
        module = self._attempt_load(modinfo["modname"])

        self.implementation = modinfo["modname"]
        self._encode = getattr(module, modinfo["encoder"])
        self._decode = getattr(module, modinfo["decoder"])
        self._encode_error = modinfo["encerror"]
        self._decode_error = modinfo["decerror"]

        if isinstance(modinfo["encerror"], basestring):
            self._encode_error = getattr(module, modinfo["encerror"])
        if isinstance(modinfo["decerror"], basestring):
            self._decode_error = getattr(module, modinfo["decerror"])

        self.name = modinfo["modname"]

    def _attempt_load(self, modname):
        """Attempt to load module name modname, returning it on success,
        throwing ImportError if module couldn't be imported"""
        __import__(modname)
        return sys.modules[modname]

    def serialize(self, data):
        """Serialize the datastructure to json. Returns a string. Raises
        TypeError if the object could not be serialized."""
        try:
            return self._encode(data)
        except self._encode_error, exc:
            raise TypeError(*exc.args)

    def deserialize(self, s):
        """deserialize the string to python data types. Raises
        ValueError if the string vould not be parsed."""
        try:
            return self._decode(s)
        except self._decode_error, exc:
            raise ValueError(*exc.args)


def force_implementation(modname):
    """Forces anyjson to use a specific json module if it's available"""
    global implementation
    for name, spec in [(e[0], e) for e in _modules]:
        if name == modname:
            implementation = _JsonImplementation(spec)
            return
    raise ImportError("No module named: %s" % modname)


for modspec in _modules:
    try:
        implementation = _JsonImplementation(modspec)
        break
    except ImportError:
        pass
else:
    raise ImportError("No supported JSON module found")

serialize = lambda value: implementation.serialize(value)
deserialize = lambda value: implementation.deserialize(value)

########NEW FILE########
__FILENAME__ = client

import anyjson
import httplib
import urllib
import urlparse
import base64
import datetime

from indextank.version import VERSION

__USER_AGENT = 'IndexTank-Python/' + VERSION

class ApiClient(object):
    """
    Basic client for an account.
    It needs an API url to be constructed.
    It has methods to manage and access the indexes of the 
    account. The objects returned by these methods implement
    the IndexClient class.
    """
    
    def __init__(self, api_url):
        self.__api_url = api_url.rstrip('/')
    
    def get_index(self, index_name):
        return IndexClient(self.__index_url(index_name))
    
    def create_index(self, index_name):
        index = self.get_index(index_name)
        index.create_index()
        return index
    
    def delete_index(self, index_name):
        self.get_index(index_name).delete_index()
    
    def list_indexes(self):
        _, indexes = _request('GET', self.__indexes_url())
        return [IndexClient(self.__index_url(k), v) for k, v in indexes.iteritems()]
    
    """ Api urls """
    def __indexes_url(self):      return '%s/%s/indexes' % (self.__api_url, 'v1')
    def __index_url(self, name):  return '%s/%s' % (self.__indexes_url(), urllib.quote(name))
    
class IndexClient(object):
    """
    Client for a specific index.
    It allows to inspect the status of the index. 
    It also provides methods for indexing and searching said index.
    """
    
    def __init__(self, index_url, metadata=None):
        self.__index_url = index_url
        self.__metadata = metadata

    def __repr__(self):
        if self.__metadata:
            return 'Index %s\n  index code: %s\n  has started?: %s\n  created on: %s\n  indexed documents: %s' % (self.__index_url, self.__metadata['code'], self.__metadata['started'], self.__metadata['creation_time'], self.__metadata['size'])
        else:
            return 'Index %s\n  <no data available>' % (self.__index_url)


    def exists(self):
        """
        Returns whether an index for the name of this instance
        exists, if it doesn't it can be created by calling
        self.create_index() 
        """
        try:
            self.refresh_metadata()
            return True
        except HttpException, e:
            if e.status == 404:
                return False
            else:
                raise

    def has_started(self):
        """
        Returns whether this index is responsive. Newly created
        indexes can take a little while to get started. 
        If this method returns False most methods in this class
        will raise an HttpException with a status of 503.
        """
        return self.refresh_metadata()['started']
    
    def get_code(self):
        return self._get_metadata()['code']

    def get_size(self):
        return self._get_metadata()['size']
    
    def get_creation_time(self):
        """
        Returns a datetime of when this index was created 
        """
        return _isoparse(self._get_metadata()['creation_time'])
    

    def create_index(self):
        """
        Creates this index. 
        If it already existed a IndexAlreadyExists exception is raised. 
        If the account has reached the limit a TooManyIndexes exception is raised
        """
        try:
            status, _ = _request('PUT', self.__index_url)
            if status == 204:
                raise IndexAlreadyExists('An index for the given name already exists')
        except HttpException, e:
            if e.status == 409:
                raise TooManyIndexes(e.msg)
            raise e
        
    def delete_index(self):
        _request('DELETE', self.__index_url)
    
    def add_documents(self, documents):
        """
        Indexes a batch of documents.
        Arguments:
            documents: a list of dicts with the following format:
                - "docid": string document id
                - "fields": a dict string->string with the fields data
                - "variables": a dict int->double with the document's variables (optional)
                - "categories": a dict string->string with the value for each category for the document (optional)
        
        """
        return _request('PUT', self.__docs_url(), data=documents)

    def add_document(self, docid, fields, variables=None):
        """
        Indexes a document for the given docid and fields.
        Arguments:
            docid: unique document identifier. a str or unicode no longer than 1024 bytes.
            field: map with the document fields
            variables (optional): map integer -> float with values for variables that can
                                  later be used in scoring functions during searches. 
        """
        data = {'docid': docid, 'fields': fields}
        if variables is not None:
            data['variables'] = variables
        _request('PUT', self.__docs_url(), data=data)
        
    def delete_document(self, docid):
        """
        Deletes the given docid from the index if it existed. otherwise, does nothing.
        Arguments:
            docid: unique document identifier
        """
        _request('DELETE', self.__docs_url(), params={'docid': docid})

    def delete_documents(self, docids):
        """
        Deletes the given docids from the index if they existed. otherwise, does nothing.
        Arguments:
            docids: a list of unique document identifiers
        """
        return _request('DELETE', self.__docs_url(), params={'docid': docids})
    
    def update_variables(self, docid, variables):
        """
        Updates the variables of the document for the given docid.
        Arguments:
            docid: unique document identifier
            variables: map integer -> float with values for variables that can
                       later be used in scoring functions during searches. 
        """
        _request('PUT', self.__variables_url(), data={'docid': docid, 'variables': variables})

    def update_categories(self, docid, categories):
        """
        Updates the categories of the document for the given docid.
        Arguments:
            docid: unique document identifier
            categories: map string -> string with values for the categories. 
        """
        _request('PUT', self.__categories_url(), data={'docid': docid, 'categories': categories})
        
    def promote(self, docid, query):
        """
        Makes the given docid the top result of the given query.
        Arguments:
            docid: unique document identifier
            query: the query for which to promote the document 
        """
        _request('PUT', self.__promote_url(), data={'docid': docid, 'query': query})

    def add_function(self, function_index, definition):
        try:
            _request('PUT', self.__function_url(function_index), data={'definition': definition})
        except HttpException, e:
            if e.status == 400:
                raise InvalidDefinition(e.msg)
    
    def delete_function(self, function_index):
        _request('DELETE', self.__function_url(function_index))
    
    def list_functions(self):
        _, functions = _request('GET', self.__functions_url())
        return functions 

    """
    Searches the index
    Arguments:
        query: the query string
        start: result # to start at
        len: number of results to return
        scoring_function: a number specifying the scoring function to use when sorting results for this query
        snippet_fields: a list of field names to retrieve snippets for
        fetch_fields: a list of field names to retrieve content for
        category_filter: a string to list of strings map with the values to filter for the categories (faceting)
        variables: map integer -> float with values for variables that can later be used in scoring function
        docvar_filters: map integer (variable index) -> list of tuples (where each tuple has the two values of a range, allowing -Infinity or Infinity)
        function_filters: map integer (function index) -> list of tuples (where each tuple has the two values of a range, allowing -Infinity or Infinity)
    """
    def search(self, query, start=None, length=None, scoring_function=None, snippet_fields=None, fetch_fields=None, category_filters=None, variables=None, docvar_filters=None, function_filters=None):
        params = { 'q': query }
        if start is not None: params['start'] = start
        if length is not None: params['len'] = length
        if scoring_function is not None: params['function'] = scoring_function
        if snippet_fields is not None: params['snippet'] = reduce(lambda x,y: x + ',' + y, snippet_fields)
        if fetch_fields is not None: params['fetch'] = reduce(lambda x,y: x + ',' + y, fetch_fields)
        if category_filters is not None: params['category_filters'] = anyjson.serialize(category_filters)
        if variables:
            for k, v in variables.items():
                params['var%d' % int(k)] = str(v)

        if docvar_filters:
            for key in docvar_filters.keys():
                value = docvar_filters.get(key)
                total_value = ''
                                    
                for range in value:
                    if len(total_value) != 0:
                        total_value += ','
                    total_value += ("*" if range[0] == None else str(range[0])) + ':' + ("*" if range[1] == None else str(range[1]))
                
                params['filter_docvar' + str(key)] = total_value

        if function_filters:
            for key in function_filters.keys():
                value = function_filters.get(key)
                total_value = ''
                                    
                for range in value:
                    if len(total_value) != 0:
                        total_value += ','
                    total_value += ("*" if range[0] == None else str(range[0])) + ':' + ("*" if range[1] == None else str(range[1]))
                
                params['filter_function' + str(key)] = total_value

        try:
            _, result = _request('GET', self.__search_url(), params=params)
            return result
        except HttpException, e:
            if e.status == 400:
                raise InvalidQuery(e.msg)
            raise

    """ metadata management """
    def _get_metadata(self):
        if self.__metadata is None:
            return self.refresh_metadata()
        return self.__metadata

    def refresh_metadata(self):
        _, self.__metadata = _request('GET', self.__index_url)
        return self.__metadata

    """ Index urls """
    def __docs_url(self):       return '%s/docs' % (self.__index_url)
    def __variables_url(self):  return '%s/docs/variables' % (self.__index_url)
    def __categories_url(self):  return '%s/docs/categories' % (self.__index_url)
    def __promote_url(self):    return '%s/promote' % (self.__index_url)
    def __search_url(self):     return '%s/search' % (self.__index_url)
    def __functions_url(self):  return '%s/functions' % (self.__index_url)
    def __function_url(self,n): return '%s/functions/%s' % (self.__index_url, n)

class InvalidResponseFromServer(Exception):
    pass
class TooManyIndexes(Exception):
    pass
class IndexAlreadyExists(Exception):
    pass
class InvalidQuery(Exception):
    pass
class InvalidDefinition(Exception):
    pass
class Unauthorized(Exception):
    pass

class HttpException(Exception):
    def __init__(self, status, msg):
        self.status = status
        self.msg = msg
        super(HttpException, self).__init__('HTTP %d: %s' % (status, msg))

def _is_ok(status):
    return status / 100 == 2

def _request(method, url, params={}, data={}, headers={}):
    splits = urlparse.urlsplit(url)
    netloc = splits[1]
    netloc_noauth = netloc.split('@')[1]
    scheme = splits[0]
    path = splits[2]
    query = splits[3]
    fragment = splits[4]
    username = ''
    password = netloc.split('@')[0][1:]
    url = urlparse.urlunsplit((scheme, netloc_noauth, path, query, fragment))
    if method in ['GET', 'DELETE']:
        params = urllib.urlencode(params, True)
        if params:
            if '?' not in url:
                url += '?' + params
            else:
                url += '&' + params

    connection = httplib.HTTPConnection(netloc_noauth, 80)
    if username or password:
        credentials = "%s:%s" % (username, password)
        base64_credentials = base64.encodestring(credentials)
        authorization = "Basic %s" % base64_credentials[:-1]
        headers['Authorization'] = authorization

    headers['User-Agent'] = __USER_AGENT
        
    if data:
        body = anyjson.serialize(data)
    else:
        body = ''

    connection.request(method, url, body, headers)
    
    response = connection.getresponse()
    response.body = response.read()
    if _is_ok(response.status):
        if response.body:
            try:
                response.body = anyjson.deserialize(response.body)
            except ValueError, e:
                raise InvalidResponseFromServer('The JSON response could not be parsed: %s.\n%s' % (e, response.body))
            ret = response.status, response.body
        else:
            ret = response.status, None
    elif response.status == 401:
        raise Unauthorized('Authorization required. Use your private api_url.')
    else:
        raise HttpException(response.status, response.body) 
    connection.close()
    return ret

def _isoparse(s):
    try:
        return datetime.datetime(int(s[0:4]),int(s[5:7]),int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19]))
    except:
        return None

########NEW FILE########
__FILENAME__ = indextag
from google.appengine.ext import webapp
from django import template as django_template

import os
DEV = os.environ['SERVER_SOFTWARE'].startswith('Development')

import keys

register = webapp.template.create_template_register()

class StringNode(django_template.Node):
  def __init__(self, string):
    self.string = string
  def render(self, context):
	  return self.string
	
def indexkey(parser, token):
    return StringNode(keys.indextank_public_key)
def indexname(parser, token):
    if DEV:
      return StringNode(keys.indextank_name_key) 
    else:
      return StringNode(keys.indextank_name_key_prod) 

register.tag(indexkey)
register.tag(indexname)

########NEW FILE########
__FILENAME__ = version
VERSION = "1.0.4"

########NEW FILE########
__FILENAME__ = bitly
#!/usr/bin/python2.4
#
# Copyright 2009 Empeeric LTD. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import urllib,urllib2
import urlparse
import string
from django.utils import simplejson
 
BITLY_BASE_URL = "http://api.bit.ly/"
BITLY_API_VERSION = "2.0.1"

VERBS_PARAM = { 
         'shorten':'longUrl',               
         'expand':'shortUrl', 
         'info':'shortUrl',
         'stats':'shortUrl',
         'errors':'',
}

class BitlyError(Exception):
  '''Base class for bitly errors'''
  
  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]

class Api(object):
    """ API class for bit.ly """
    def __init__(self, login, apikey):
        self.login = login
        self.apikey = apikey
        self._urllib = urllib2
        
    def shorten(self,longURLs,params={}):
        """ 
            Takes either:
            A long URL string and returns shortened URL string
            Or a list of long URL strings and returns a list of shortened URL strings.
        """
        want_result_list = True
        if not isinstance(longURLs, list):
            longURLs = [longURLs]
            want_result_list = False
        
        for index,url in enumerate(longURLs):
            if not '://' in url:
                longURLs[index] = "http://" + url
            
        request = self._getURL("shorten",longURLs,params)
        result = self._fetchUrl(request)
        json = simplejson.loads(result)
        self._CheckForError(json)
        
        results = json['results']
        res = [self._extract_short_url(results[url]) for url in longURLs]

        if want_result_list:
            return res
        else:
            return res[0]

    def _extract_short_url(self,item):
        if item['shortKeywordUrl'] == "":
            return item['shortUrl']
        else:
            return item['shortKeywordUrl']

    def expand(self,shortURL,params={}):
        """ Given a bit.ly url or hash, return long source url """
        request = self._getURL("expand",shortURL,params)
        result = self._fetchUrl(request)
        json = simplejson.loads(result)
        self._CheckForError(json)
        return json['results'][string.split(shortURL, '/')[-1]]['longUrl']

    def info(self,shortURL,params={}):
        """ 
        Given a bit.ly url or hash, 
        return information about that page, 
        such as the long source url
        """
        request = self._getURL("info",shortURL,params)
        result = self._fetchUrl(request)
        json = simplejson.loads(result)
        self._CheckForError(json)
        return json['results'][string.split(shortURL, '/')[-1]]

    def stats(self,shortURL,params={}):
        """ Given a bit.ly url or hash, return traffic and referrer data.  """
        request = self._getURL("stats",shortURL,params)
        result = self._fetchUrl(request)
        json = simplejson.loads(result)
        self._CheckForError(json)
        return Stats.NewFromJsonDict(json['results'])

    def errors(self,params={}):
        """ Get a list of bit.ly API error codes. """
        request = self._getURL("errors","",params)
        result = self._fetchUrl(request)
        json = simplejson.loads(result)
        self._CheckForError(json)
        return json['results']
        
    def setUrllib(self, urllib):
        '''Override the default urllib implementation.
    
        Args:
          urllib: an instance that supports the same API as the urllib2 module
        '''
        self._urllib = urllib
    
    def _getURL(self,verb,paramVal,more_params={}): 
        if not isinstance(paramVal, list):
            paramVal = [paramVal]
              
        params = {
                  'version':BITLY_API_VERSION,
                  'format':'json',
                  'login':self.login,
                  'apiKey':self.apikey,
            }

        params.update(more_params)
        params = params.items() 
                
        verbParam = VERBS_PARAM[verb]   
        if verbParam:
            for val in paramVal:
                params.append(( verbParam,val ))
   
        encoded_params = urllib.urlencode(params)
        return "%s%s?%s" % (BITLY_BASE_URL,verb,encoded_params)
       
    def _fetchUrl(self,url):
        '''Fetch a URL
    
        Args:
          url: The URL to retrieve
    
        Returns:
          A string containing the body of the response.
        '''
    
        # Open and return the URL 
        url_data = self._urllib.urlopen(url).read()
        return url_data    

    def _CheckForError(self, data):
        """Raises a BitlyError if bitly returns an error message.
    
        Args:
          data: A python dict created from the bitly json response
        Raises:
          BitlyError wrapping the bitly error message if one exists.
        """
        # bitly errors are relatively unlikely, so it is faster
        # to check first, rather than try and catch the exception
        if 'ERROR' in data or data['statusCode'] == 'ERROR':
            raise BitlyError, data['errorMessage']
        for key in data['results']:
            if type(data['results']) is dict and type(data['results'][key]) is dict:
                if 'statusCode' in data['results'][key] and data['results'][key]['statusCode'] == 'ERROR':
                    raise BitlyError, data['results'][key]['errorMessage'] 
       
class Stats(object):
    '''A class representing the Statistics returned by the bitly api.
    
    The Stats structure exposes the following properties:
    status.user_clicks # read only
    status.clicks # read only
    '''
    
    def __init__(self,user_clicks=None,total_clicks=None):
        self.user_clicks = user_clicks
        self.total_clicks = total_clicks
    
    @staticmethod
    def NewFromJsonDict(data):
        '''Create a new instance based on a JSON dict.
    
        Args:
          data: A JSON dict, as converted from the JSON in the bitly API
        Returns:
          A bitly.Stats instance
        '''
        return Stats(user_clicks=data.get('userClicks', None),
                      total_clicks=data.get('clicks', None))

        
if __name__ == '__main__':
    testURL1="www.yahoo.com"
    testURL2="www.cnn.com"
    a=Api(login="pythonbitly",apikey="R_06871db6b7fd31a4242709acaf1b6648")
    short=a.shorten(testURL1)    
    print "Short URL = %s" % short
    short=a.shorten(testURL1,{'history':1})    
    print "Short URL with history = %s" % short
    urlList=[testURL1,testURL2]
    shortList=a.shorten(urlList)
    print "Short URL list = %s" % shortList
    long=a.expand(short)
    print "Expanded URL = %s" % long
    info=a.info(short)
    print "Info: %s" % info
    stats=a.stats(short)
    print "User clicks %s, total clicks: %s" % (stats.user_clicks,stats.total_clicks)
    errors=a.errors()
    print "Errors: %s" % errors
    testURL3=["www.google.com"]
    short=a.shorten(testURL3) 
    print "Short url in list = %s" % short

########NEW FILE########
__FILENAME__ = PyRSS2Gen
"""PyRSS2Gen - A Python library for generating RSS 2.0 feeds."""

__name__ = "PyRSS2Gen"
__version__ = (1, 0, 0)
__author__ = "Andrew Dalke <dalke@dalkescientific.com>"

_generator_name = __name__ + "-" + ".".join(map(str, __version__))

import datetime

# Could make this the base class; will need to add 'publish'
class WriteXmlMixin:
    def write_xml(self, outfile, encoding = "iso-8859-1"):
        from xml.sax import saxutils
        handler = saxutils.XMLGenerator(outfile, encoding)
        handler.startDocument()
        self.publish(handler)
        handler.endDocument()

    def to_xml(self, encoding = "iso-8859-1"):
        try:
            import cStringIO as StringIO
        except ImportError:
            import StringIO
        f = StringIO.StringIO()
        self.write_xml(f, encoding)
        return f.getvalue()


def _element(handler, name, obj, d = {}):
    if isinstance(obj, basestring) or obj is None:
        # special-case handling to make the API easier
        # to use for the common case.
        handler.startElement(name, d)
        if obj is not None:
            handler.characters(obj)
        handler.endElement(name)
    else:
        # It better know how to emit the correct XML.
        obj.publish(handler)

def _opt_element(handler, name, obj):
    if obj is None:
        return
    _element(handler, name, obj)


def _format_date(dt):
    """convert a datetime into an RFC 822 formatted date

    Input date must be in GMT.
    """
    # Looks like:
    #   Sat, 07 Sep 2002 00:00:01 GMT
    # Can't use strftime because that's locale dependent
    #
    # Isn't there a standard way to do this for Python?  The
    # rfc822 and email.Utils modules assume a timestamp.  The
    # following is based on the rfc822 module.
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
            dt.day,
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month-1],
            dt.year, dt.hour, dt.minute, dt.second)

        
##
# A couple simple wrapper objects for the fields which
# take a simple value other than a string.
class IntElement:
    """implements the 'publish' API for integers

    Takes the tag name and the integer value to publish.
    
    (Could be used for anything which uses str() to be published
    to text for XML.)
    """
    element_attrs = {}
    def __init__(self, name, val):
        self.name = name
        self.val = val
    def publish(self, handler):
        handler.startElement(self.name, self.element_attrs)
        handler.characters(str(self.val))
        handler.endElement(self.name)

class DateElement:
    """implements the 'publish' API for a datetime.datetime

    Takes the tag name and the datetime to publish.

    Converts the datetime to RFC 2822 timestamp (4-digit year).
    """
    def __init__(self, name, dt):
        self.name = name
        self.dt = dt
    def publish(self, handler):
        _element(handler, self.name, _format_date(self.dt))
####

class Category:
    """Publish a category element"""
    def __init__(self, category, domain = None):
        self.category = category
        self.domain = domain
    def publish(self, handler):
        d = {}
        if self.domain is not None:
            d["domain"] = self.domain
        _element(handler, "category", self.category, d)

class Cloud:
    """Publish a cloud"""
    def __init__(self, domain, port, path,
                 registerProcedure, protocol):
        self.domain = domain
        self.port = port
        self.path = path
        self.registerProcedure = registerProcedure
        self.protocol = protocol
    def publish(self, handler):
        _element(handler, "cloud", None, {
            "domain": self.domain,
            "port": str(self.port),
            "path": self.path,
            "registerProcedure": self.registerProcedure,
            "protocol": self.protocol})

class Image:
    """Publish a channel Image"""
    element_attrs = {}
    def __init__(self, url, title, link,
                 width = None, height = None, description = None):
        self.url = url
        self.title = title
        self.link = link
        self.width = width
        self.height = height
        self.description = description
        
    def publish(self, handler):
        handler.startElement("image", self.element_attrs)

        _element(handler, "url", self.url)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)

        width = self.width
        if isinstance(width, int):
            width = IntElement("width", width)
        _opt_element(handler, "width", width)
        
        height = self.height
        if isinstance(height, int):
            height = IntElement("height", height)
        _opt_element(handler, "height", height)

        _opt_element(handler, "description", self.description)

        handler.endElement("image")

class Guid:
    """Publish a guid

    Defaults to being a permalink, which is the assumption if it's
    omitted.  Hence strings are always permalinks.
    """
    def __init__(self, guid, isPermaLink = 1):
        self.guid = guid
        self.isPermaLink = isPermaLink
    def publish(self, handler):
        d = {}
        if self.isPermaLink:
            d["isPermaLink"] = "true"
        else:
            d["isPermaLink"] = "false"
        _element(handler, "guid", self.guid, d)

class TextInput:
    """Publish a textInput

    Apparently this is rarely used.
    """
    element_attrs = {}
    def __init__(self, title, description, name, link):
        self.title = title
        self.description = description
        self.name = name
        self.link = link

    def publish(self, handler):
        handler.startElement("textInput", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "description", self.description)
        _element(handler, "name", self.name)
        _element(handler, "link", self.link)
        handler.endElement("textInput")
        

class Enclosure:
    """Publish an enclosure"""
    def __init__(self, url, length, type):
        self.url = url
        self.length = length
        self.type = type
    def publish(self, handler):
        _element(handler, "enclosure", None,
                 {"url": self.url,
                  "length": str(self.length),
                  "type": self.type,
                  })

class Source:
    """Publish the item's original source, used by aggregators"""
    def __init__(self, name, url):
        self.name = name
        self.url = url
    def publish(self, handler):
        _element(handler, "source", self.name, {"url": self.url})

class SkipHours:
    """Publish the skipHours

    This takes a list of hours, as integers.
    """
    element_attrs = {}
    def __init__(self, hours):
        self.hours = hours
    def publish(self, handler):
        if self.hours:
            handler.startElement("skipHours", self.element_attrs)
            for hour in self.hours:
                _element(handler, "hour", str(hour))
            handler.endElement("skipHours")

class SkipDays:
    """Publish the skipDays

    This takes a list of days as strings.
    """
    element_attrs = {}
    def __init__(self, days):
        self.days = days
    def publish(self, handler):
        if self.days:
            handler.startElement("skipDays", self.element_attrs)
            for day in self.days:
                _element(handler, "day", day)
            handler.endElement("skipDays")

class RSS2(WriteXmlMixin):
    """The main RSS class.

    Stores the channel attributes, with the "category" elements under
    ".categories" and the RSS items under ".items".
    """
    
    rss_attrs = {"version": "2.0"}
    element_attrs = {}
    def __init__(self,
                 title,
                 link,
                 description,

                 language = None,
                 copyright = None,
                 managingEditor = None,
                 webMaster = None,
                 pubDate = None,  # a datetime, *in* *GMT*
                 lastBuildDate = None, # a datetime
                 
                 categories = None, # list of strings or Category
                 generator = _generator_name,
                 docs = "http://blogs.law.harvard.edu/tech/rss",
                 cloud = None,    # a Cloud
                 ttl = None,      # integer number of minutes

                 image = None,     # an Image
                 rating = None,    # a string; I don't know how it's used
                 textInput = None, # a TextInput
                 skipHours = None, # a SkipHours with a list of integers
                 skipDays = None,  # a SkipDays with a list of strings

                 items = None,     # list of RSSItems
                 ):
        self.title = title
        self.link = link
        self.description = description
        self.language = language
        self.copyright = copyright
        self.managingEditor = managingEditor

        self.webMaster = webMaster
        self.pubDate = pubDate
        self.lastBuildDate = lastBuildDate
        
        if categories is None:
            categories = []
        self.categories = categories
        self.generator = generator
        self.docs = docs
        self.cloud = cloud
        self.ttl = ttl
        self.image = image
        self.rating = rating
        self.textInput = textInput
        self.skipHours = skipHours
        self.skipDays = skipDays

        if items is None:
            items = []
        self.items = items

    def publish(self, handler):
        handler.startElement("rss", self.rss_attrs)
        handler.startElement("channel", self.element_attrs)
        _element(handler, "title", self.title)
        _element(handler, "link", self.link)
        _element(handler, "description", self.description)

        self.publish_extensions(handler)
        
        _opt_element(handler, "language", self.language)
        _opt_element(handler, "copyright", self.copyright)
        _opt_element(handler, "managingEditor", self.managingEditor)
        _opt_element(handler, "webMaster", self.webMaster)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        lastBuildDate = self.lastBuildDate
        if isinstance(lastBuildDate, datetime.datetime):
            lastBuildDate = DateElement("lastBuildDate", lastBuildDate)
        _opt_element(handler, "lastBuildDate", lastBuildDate)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)

        _opt_element(handler, "generator", self.generator)
        _opt_element(handler, "docs", self.docs)

        if self.cloud is not None:
            self.cloud.publish(handler)

        ttl = self.ttl
        if isinstance(self.ttl, int):
            ttl = IntElement("ttl", ttl)
        _opt_element(handler, "tt", ttl)

        if self.image is not None:
            self.image.publish(handler)

        _opt_element(handler, "rating", self.rating)
        if self.textInput is not None:
            self.textInput.publish(handler)
        if self.skipHours is not None:
            self.skipHours.publish(handler)
        if self.skipDays is not None:
            self.skipDays.publish(handler)

        for item in self.items:
            item.publish(handler)

        handler.endElement("channel")
        handler.endElement("rss")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the three required fields.
        pass

    
    
class RSSItem(WriteXmlMixin):
    """Publish an RSS Item"""
    element_attrs = {}
    def __init__(self,
                 title = None,  # string
                 link = None,   # url as string
                 description = None, # string
                 author = None,      # email address as string
                 categories = None,  # list of string or Category
                 comments = None,  # url as string
                 enclosure = None, # an Enclosure
                 guid = None,    # a unique string
                 pubDate = None, # a datetime
                 source = None,  # a Source
                 ):
        
        if title is None and description is None:
            raise TypeError(
                "must define at least one of 'title' or 'description'")
        self.title = title
        self.link = link
        self.description = description
        self.author = author
        if categories is None:
            categories = []
        self.categories = categories
        self.comments = comments
        self.enclosure = enclosure
        self.guid = guid
        self.pubDate = pubDate
        self.source = source
        # It sure does get tedious typing these names three times...

    def publish(self, handler):
        handler.startElement("item", self.element_attrs)
        _opt_element(handler, "title", self.title)
        _opt_element(handler, "link", self.link)
        self.publish_extensions(handler)
        _opt_element(handler, "description", self.description)
        _opt_element(handler, "author", self.author)

        for category in self.categories:
            if isinstance(category, basestring):
                category = Category(category)
            category.publish(handler)
        
        _opt_element(handler, "comments", self.comments)
        if self.enclosure is not None:
            self.enclosure.publish(handler)
        _opt_element(handler, "guid", self.guid)

        pubDate = self.pubDate
        if isinstance(pubDate, datetime.datetime):
            pubDate = DateElement("pubDate", pubDate)
        _opt_element(handler, "pubDate", pubDate)

        if self.source is not None:
            self.source.publish(handler)
        
        handler.endElement("item")

    def publish_extensions(self, handler):
        # Derived classes can hook into this to insert
        # output after the title and link elements
        pass

########NEW FILE########
__FILENAME__ = main
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket

from handlers import ( MainHandler, ThreadsHandler, GuidelinesHandler, FAQHandler,
                       NewHandler, UserPostsHandler, SubmitNewStoryHandler, UpVoteHandler,
                       UpVoteCommentHandler, ProfileHandler, PostHandler, EditPostHandler,
                       CommentReplyHandler, EditCommentHandler, NotificationsInboxHandler,
                       NotificationsInboxAllHandler, NotificationsMarkAsReadHandler,
                       LeaderHandler, LoginHandler, LogoutHandler, RegisterHandler, 
                       NewPasswordHandler, RecoveryHandler, RssHandler, APIGitHubHandler,
                       APITwitterHandler, APIHackerNewsHandler )


import os
DEV = os.environ['SERVER_SOFTWARE'].startswith('Development')

# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler.Handler),
      ('/.json', MainHandler.Handler),
      ('/conversaciones/(.+)', ThreadsHandler.Handler),
      ('/directrices', GuidelinesHandler.Handler),
      ('/preguntas-frecuentes', FAQHandler.Handler),
      ('/nuevo', NewHandler.Handler),
      ('/nuevo.json', NewHandler.Handler),
      ('/noticias-usuario/(.+)', UserPostsHandler.Handler),
      ('/agregar', SubmitNewStoryHandler.Handler),
      ('/upvote/(.+)', UpVoteHandler.Handler),
      ('/upvote_comment/(.+)', UpVoteCommentHandler.Handler),
      ('/perfil/(.+)', ProfileHandler.Handler),
      ('/noticia/(.+)', PostHandler.Handler),
      ('/editar-noticia/(.+)', EditPostHandler.Handler),
      ('/responder/(.+)', CommentReplyHandler.Handler),
      ('/editar-comentario/(.+)', EditCommentHandler.Handler),
      ('/inbox', NotificationsInboxHandler.Handler),
      ('/inbox/all', NotificationsInboxAllHandler.Handler),
      ('/inbox/marcar-como-leido/(.+)', NotificationsMarkAsReadHandler.Handler),
      ('/lideres', LeaderHandler.Handler),
      ('/login', LoginHandler.Handler),
      ('/logout', LogoutHandler.Handler),
      ('/register', RegisterHandler.Handler),
      ('/olvide-el-password', NewPasswordHandler.Handler),
      ('/recovery/(.+)?', RecoveryHandler.Handler),
      ('/rss', RssHandler.Handler),
      ('/api/usuarios/github', APIGitHubHandler.Handler),
      ('/api/usuarios/twitter', APITwitterHandler.Handler),
      ('/api/usuarios/hackernews', APIHackerNewsHandler.Handler),
  ], debug=DEV)
  util.run_wsgi_app(application)

webapp.template.register_template_library('indextank.indextag')

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = models
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

# Models
class User(db.Model):
  lowercase_nickname  = db.StringProperty(required=True)
  nickname            = db.StringProperty(required=True)
  password            = db.StringProperty(required=True)
  created             = db.DateTimeProperty(auto_now_add=True)
  about               = db.TextProperty(required=False)
  hnuser              = db.StringProperty(required=False, default="")
  github              = db.StringProperty(required=False, default="")
  location            = db.StringProperty(required=False, default="")
  twitter             = db.StringProperty(required=False, default="")
  email               = db.EmailProperty(required=False)
  url                 = db.LinkProperty(required=False)
  admin               = db.BooleanProperty(default=False)
  karma               = db.IntegerProperty(required=False)

  @staticmethod
  def slow_hash(password, iterations=1000):
    h = hashlib.sha1()
    h.update(unicode(password).encode("utf-8"))
    h.update(keys.salt_key)
    for x in range(iterations):
      h.update(h.digest())
    return h.hexdigest()

  def average_karma(self):
    delta = (datetime.now() - self.created)
    days = delta.days
    votes = self.karma
    if votes is None:
      votes = 0
    if days > 0:
      return votes/float(days)
    else:
      return votes

  def sum_votes(self):
    val = memcache.get("u_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = Vote.all().filter("user !=",self).filter("target_user =",self).count()
      self.karma = val
      self.put()
      memcache.add("u_" + str(self.key()), val, 3600)
      return val

  def remove_from_memcache(self):
    memcache.delete("u_" + str(self.key()))

  def has_notifications(self):
    count_notificationes = memcache.get("user_notification_" + str(self.key()))
    if count_notificationes is not None:
      return count_notificationes > 0 
    else:
      count_notificationes = Notification.all().filter("target_user =",self).filter("read =", False).count()
      memcache.add("user_notification_" + str(self.key()), count_notificationes, 3600)
      return count_notificationes > 0 

  def remove_notifications_from_memcache(self):
    memcache.delete("user_notification_" + str(self.key()))

class Post(db.Model):
  title     = db.StringProperty(required=True)
  url       = db.LinkProperty(required=False)
  nice_url  = db.StringProperty(required=False)
  message   = db.TextProperty()
  user      = db.ReferenceProperty(User, collection_name='posts')
  created   = db.DateTimeProperty(auto_now_add=True)
  karma     = db.FloatProperty()
  edited    = db.BooleanProperty(default=False)
  twittered = db.BooleanProperty(default=False)

  def to_json(self):
    return {
      'id':str(self.key()),
      'title':self.title,
      'message':self.message,
      'created':self.created.strftime("%s"),
      'user':self.user.nickname,
      'comment_count':self.cached_comment_count,
      'url':self.url,	  
      'votes':self.prefetched_sum_votes}

  def url_netloc(self):
    return urlparse(self.url).netloc

  def can_edit(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      if self.user.key() == user.key() or user.admin:
        return True
    return False

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def sum_votes(self):
    val = memcache.get("p_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("p_" + str(self.key()), val, 3600)
      return val

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      # hit memcache for this
      memValue = memcache.get("vp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return memValue == 1
      else:
        vote = Vote.all().filter("user =", user).filter("post =", self).fetch(1)
        memcache.add("vp_" + str(self.key()) + "_" + str(user.key()), len(vote), 3600)
        return len(vote) == 1
    else:
      return False

  def remove_from_memcache(self):
    memcache.delete("pc_" + str(self.key()))
    memcache.delete("p_" + str(self.key()))
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      user.remove_from_memcache()
      memcache.delete("vp_" + str(self.key()) + "_" + str(user.key()))
    self.calculate_karma()

  def calculate_karma(self):
    delta = (datetime.now() - self.created)
    seconds = delta.seconds + delta.days*86400
    hours = seconds / 3600 + 1
    votes = self.sum_votes() 
    gravity = 1.8
    karma = (votes - 1) / pow((hours + 2), gravity)
    self.karma = karma 
    self.put()

  @staticmethod
  def remove_cached_count_from_memcache():
    memcache.delete("Post_count")

  @staticmethod
  def get_cached_count():
    memValue = memcache.get("Post_count")
    if memValue is not None:
      return memValue
    else:
      count = Post.all().count()
      memcache.add("Post_count",count,3600)
      return count

class Comment(db.Model):
  message = db.TextProperty()
  user    = db.ReferenceProperty(User, collection_name='comments')
  post    = db.ReferenceProperty(Post, collection_name='comments')
  father  = db.SelfReferenceProperty(collection_name='childs')
  created = db.DateTimeProperty(auto_now_add=True)
  karma   = db.FloatProperty()
  edited  = db.BooleanProperty(default=False)

  def father_ref(self):
    return Comment.father.get_value_for_datastore(self)

  def to_json(self):
    childs_json = map(lambda u: u.to_json(), self.processed_child)
    return {
      'message':self.message,
      'created':self.created.strftime("%s"),
      'user':self.user.nickname,
      'votes':self.prefetched_sum_votes,
      'comments': childs_json}

  def can_edit(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      if self.user.key() == user.key() or user.admin:
        return True
    return False

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def sum_votes(self):
    val = memcache.get("c_" + str(self.key()))
    if val is not None:
      return val
    else:
      val = self.votes.count()
      memcache.add("c_" + str(self.key()), val, 3600)
      return val

  # This is duplicated code from the pre_fetcher
  # Do not edit if you don't update those functions too
  def already_voted(self):
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      # hit memcache for this
      memValue = memcache.get("cp_" + str(self.key()) + "_" + str(user.key()))
      if memValue is not None:
        return memValue == 1
      else:
        vote = Vote.all().filter("user =", user).filter("comment =", self).fetch(1)
        memcache.add("cp_" + str(self.key()) + "_" + str(user.key()), len(vote), 3600)
        return len(vote) == 1
    else:
      return False

  def remove_from_memcache(self):
    memcache.delete("c_" + str(self.key()))
    session = get_current_session()
    if session.has_key('user'):
      user = session['user']
      user.remove_from_memcache()
      memcache.delete("cp_" + str(self.key()) + "_" + str(user.key()))
    self.calculate_karma()

  def calculate_karma(self):
    delta = (datetime.now() - self.created)
    seconds = delta.seconds + delta.days*86400
    hours = seconds / 3600 + 1
    votes = self.sum_votes() 
    gravity = 1.8
    karma = (votes - 1) / pow((hours + 2), gravity)
    self.karma = karma 
    self.put()

class Vote(db.Model):
  user        = db.ReferenceProperty(User, collection_name='votes')
  target_user = db.ReferenceProperty(User, collection_name='received_votes')
  post        = db.ReferenceProperty(Post, collection_name='votes')
  comment     = db.ReferenceProperty(Comment, collection_name='votes')
  created     = db.DateTimeProperty(auto_now_add=True)

class Notification(db.Model):
  target_user = db.ReferenceProperty(User, collection_name='notifications')
  sender_user = db.ReferenceProperty(User, collection_name='send_notifications')
  post        = db.ReferenceProperty(Post)
  comment     = db.ReferenceProperty(Comment)
  created     = db.DateTimeProperty(auto_now_add=True)
  read        = db.BooleanProperty(default=False)

  @staticmethod
  def create_notification_for_comment_and_user(comment,target_user):
    if comment.user.key() == target_user.key():
      return
    notification = Notification(target_user=target_user,post=comment.post,comment=comment,sender_user=comment.user)
    notification.put()
    target_user.remove_notifications_from_memcache()
    return notification

class Ticket(db.Model):
  user        = db.ReferenceProperty(User, collection_name='tickets')
  is_active   = db.BooleanProperty(default=True)
  code        = db.StringProperty(required=True)
  created     = db.DateTimeProperty(auto_now_add=True)
  
  @staticmethod
  def create_code(seed, iterations=1000):
    h = hashlib.sha1()
    h.update(unicode(seed).encode("utf-8"))
    h.update(keys.salt_key)
    for x in range(iterations):
      h.update(h.digest())
    return h.hexdigest()
  
  @staticmethod
  def deactivate_others(user):
    tickets = Ticket.all().filter('user = ', user.key()).filter('is_active',True)
    for ticket in tickets:
      ticket.is_active = False
      ticket.put()
      
  

########NEW FILE########
__FILENAME__ = prefetch
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from gaesessions import get_current_session
from urlparse import urlparse
from datetime import datetime

from models import User, Post, Comment, Vote 

def prefetch_refprops(entities, *props):
  fields = [(entity, prop) for entity in entities for prop in props]
  ref_keys = [prop.get_value_for_datastore(x) for x, prop in fields]
  ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
  for (entity, prop), ref_key in zip(fields, ref_keys):
    if ref_entities[ref_key]:
      prop.__set__(entity, ref_entities[ref_key])
  return entities

def prefetch_comment_list(comments):
  prefetch_refprops(comments, Comment.user, Comment.post)

  # call all the memcache information
  # starting by the already_voted area
  comment_keys = [str(comment.key()) for comment in comments]
  session = get_current_session()
  if session.has_key('user'):
    user = session['user']
    memcache_voted_keys = ["cp_" + comment_key + "_" + str(user.key()) for comment_key in comment_keys]
    memcache_voted = memcache.get_multi(memcache_voted_keys)
    memcache_to_add = {}
    for comment in comments:
      vote_value = memcache_voted.get("cp_" + str(comment.key()) + "_" +str(user.key()))
      if vote_value is not None:
        comment.prefetched_already_voted = vote_value == 1
      else:
        vote = Vote.all().filter("user =", user).filter("comment =", comment).fetch(1)
        memcache_to_add["cp_" + str(comment.key()) + "_" + str(user.key())] = len(vote)
        comment.prefetched_already_voted = len(vote) == 1
    if memcache_to_add.keys():
      memcache.add_multi(memcache_to_add, 3600)
  else:
    for comment in comments:
      comment.prefetched_already_voted = False
  # now the sum_votes
  memcache_sum_votes_keys = ["c_" + comment_key for comment_key in comment_keys]
  memcache_sum_votes = memcache.get_multi(memcache_sum_votes_keys)
  memcache_to_add = {}
  for comment in comments:
    sum_votes_value = memcache_sum_votes.get("c_" + str(comment.key()))
    if sum_votes_value is not None:
      comment.prefetched_sum_votes = sum_votes_value
    else:
      sum_votes = Vote.all().filter("comment =", comment).count()
      memcache_to_add["c_" + str(comment.key())] = sum_votes
      comment.prefetched_sum_votes =sum_votes
  if memcache_to_add.keys():
    memcache.add_multi(memcache_to_add, 3600)

def prefetch_posts_list(posts):
  prefetch_refprops(posts, Post.user)
  posts_keys = [str(post.key()) for post in posts]

  # get user, if no user, all already_voted = no
  session = get_current_session()
  if session.has_key('user'):
    user = session['user']
    memcache_voted_keys = ["vp_" + post_key + "_" + str(user.key()) for post_key in posts_keys]
    memcache_voted = memcache.get_multi(memcache_voted_keys)
    memcache_to_add = {}
    for post in posts:
      vote_value = memcache_voted.get("vp_" + str(post.key()) + "_" +str(user.key()))
      if vote_value is not None:
        post.prefetched_already_voted = vote_value == 1
      else:
        vote = Vote.all().filter("user =", user).filter("post =", post).fetch(1)
        memcache_to_add["vp_" + str(post.key()) + "_" + str(user.key())] = len(vote)
        post.prefetched_already_voted = len(vote) == 1
    if memcache_to_add.keys():
      memcache.add_multi(memcache_to_add, 3600)
  else:
    for post in posts:
      post.prefetched_already_voted = False
  # now the sum_votes
  memcache_sum_votes_keys = ["p_" + post_key for post_key in posts_keys]
  memcache_sum_votes = memcache.get_multi(memcache_sum_votes_keys)
  memcache_to_add = {}
  for post in posts:
    sum_votes_value = memcache_sum_votes.get("p_" + str(post.key()))
    if sum_votes_value is not None:
      post.prefetched_sum_votes = sum_votes_value
    else:
      sum_votes = Vote.all().filter("post =", post).count()
      memcache_to_add["p_" + str(post.key())] = sum_votes
      post.prefetched_sum_votes = sum_votes
  if memcache_to_add.keys():
    memcache.add_multi(memcache_to_add, 3600)
  # finally we get all the comment count from memcache
  memcache_comment_count_keys = ["pc_" + post_key for post_key in posts_keys]
  memcache_comment_count = memcache.get_multi(memcache_comment_count_keys)
  memcache_to_add = {}
  for post in posts:
    comment_count = memcache_comment_count.get("pc_" + str(post.key()))
    if comment_count is not None:
      post.cached_comment_count = comment_count
    else:
      comment_count = post.comments.count() 
      memcache_to_add["pc_" + str(post.key())] = comment_count
      post.cached_comment_count = comment_count 
  if memcache_to_add.keys():
    memcache.add_multi(memcache_to_add, 3600)

########NEW FILE########
__FILENAME__ = reports
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#Copyright (c) 2011 - Santiago Zavala
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import logging
import hashlib
import keys
import prefetch
import helper
import random

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime, date, timedelta
from gaesessions import get_current_session
from django.utils import simplejson

from libs import PyRSS2Gen
from models import User, Post, Comment, Vote, Notification, Ticket

def w_comma(str):
  if str:
    return str + ","
  else:
    return ","

class UserReportHandler(webapp.RequestHandler):
  def get(self):
    header = "nickname,hnuser,github,twitter,location,url,about,created,comments_count,posts_count,karma,average_karma,\n\r"
    self.response.out.write(header)
    for u in User.all().fetch(1000):
      user_info = w_comma(u.nickname)
      user_info += w_comma(u.hnuser)
      user_info += w_comma(u.github)
      user_info += w_comma(u.twitter)
      user_info += w_comma(u.location)
      user_info += w_comma(u.url)
      user_info += w_comma(u.about)
      user_info += w_comma(str(u.created))
      user_info += w_comma(str(u.comments.count()))
      user_info += w_comma(str(u.posts.count()))
      user_info += w_comma(str(u.karma))
      user_info += w_comma(str(u.average_karma()))
      
      self.response.out.write(user_info + "\n\r")


# App stuff
def main():
  application = webapp.WSGIApplication([
      ('/reports/users', UserReportHandler),
  ], debug=True)
  util.run_wsgi_app(application)



if __name__ == '__main__':
  main()

########NEW FILE########
