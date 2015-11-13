__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


import re
import urllib

from django import newforms as forms
from buzzengine.api import models
from google.appengine.api import taskqueue


class NewCommentForm(forms.Form):
    article_url   = forms.URLField(required=True,   widget=forms.HiddenInput)
    article_title = forms.CharField(required=False, widget=forms.HiddenInput)

    author_name  = forms.CharField(required=True,  label="Name")
    author_email = forms.EmailField(required=True, label="Email")
    author_url   = forms.URLField(required=False,  label="URL")
    author_ip    = forms.CharField(required=False)
    
    comment = forms.CharField(required=True, widget=forms.Textarea(attrs={'cols': 30, 'rows': 3}))

    def save(self):
        data = self.clean_data
        
        article_url = data.get('article_url')
        article_title = data.get('article_title') or data.get('article_url')

        article = models.Article.get_or_insert(article_url, url=article_url, title=article_title)
        if article.title != article_title:
            article.title = article_title
            article.put()

        author_email = data.get('author_email')
        author_name  = data.get('author_name') 
        author_url   = data.get('author_url')  
        author_ip    = data.get('author_ip')
        author_key   = (author_email or '') + author_name

        author = models.Author.get_or_insert(author_key, name=author_name)
        has_changes = False
        
        if author.url != author_url and author_url:
            author.url = author_url
            has_changes = True

        if author_email and author_email != author.email:
            author.email = author_email
            has_changes = True

        if has_changes:
            author.put()

        comment = models.Comment(parent=article, comment=data.get('comment'), author=author, article=article, author_ip=author_ip)
        comment.put()

        params = urllib.urlencode({'article_url': article_url, 'comment_id': comment.key().id()})
        taskqueue.add(url="/api/notify/?" + params, method="GET")

        self._author  = author
        self._article = article
        self._comment = comment

        return comment
        
    @property
    def output(self):
        return {
            'article': {
                'url': self._article.url,
                'title': self._article.title,
            },
            'author': {
                'email': self._author.email,
                'name':  self._author.name,
                'url':  self._author.url,
            },
            'comment': self._comment.comment,
        }

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "alex@magnolialabs.com"

import re
from django.conf import settings
from buzzengine.api.models import Author


class TrackingMiddleware:
    def process_request(self, request):
        authorhash = request.GET.get('author') or request.COOKIES.get('author') 
        if authorhash:
            request.author = Author.get_by_hash(authorhash)
        else:
            request.author = None


class HttpControlMiddleware(object):

    def _do_process_request(self, request):
        if hasattr(request, 'ROOT_DOMAIN') and hasattr(request, 'API_DOMAIN'):
            return

        url     = request.REQUEST.get('article_url') or request.META.get('HTTP_REFERER')
        rorigin = request.REQUEST.get('origin')
        host    = None
        origin  = None

        if url:
            origin = re.findall('^(https?://[^/]+)', url)
            origin = origin[0] if origin else None
        elif rorigin and re.match('^https?://[^/]+$', rorigin):
            origin = rorigin

        host = request.META['SERVER_NAME']
        if str(request.META.get('SERVER_PORT')) != str(80):
            host += ":" + request.META['SERVER_PORT']

        request.API_DOMAIN  = host
        request.ROOT_DOMAIN = origin
        

    def process_request(self, request):
        self._do_process_request(request)


    def process_response(self, request, response):
        # for some weird reason, ROOT_DOMAIN sometimes is not set,
        # although process_request should always be called before
        # process_response

        self._do_process_request(request)        
        origin = request.ROOT_DOMAIN if hasattr(request, 'ROOT_DOMAIN') else None

        if origin:
            response['Access-Control-Allow-Origin'] = origin or "*"
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Headers'] = 'Content-Type, *'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Max-Age'] = '111111'

        return response

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


import random
import hashlib

from django.conf import settings
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext import db


CACHE_EXP_SECS = 60 * 60 * 24 * 7 * 4 # 4 weeks


class Article(db.Model):
    url = db.LinkProperty(required=True)
    title = db.StringProperty(required=False)

    created_at = db.DateTimeProperty(auto_now_add=True)

    def __unicode__(self):
        return str(self.url)


class Author(db.Model):
    name       = db.StringProperty(required=True)
    email      = db.EmailProperty(required=False)
    url        = db.StringProperty(required=False)    
    email_hash = db.StringProperty(required=False)
    created_at = db.DateTimeProperty(auto_now_add=True)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.email or "no email specified")

    def put(self):
        email = self.email and self.email.strip()
        name  = self.name.strip()

        md5 = hashlib.md5()    
        md5.update(email or name)

        email_hash = md5.hexdigest()
        self.email_hash = email_hash

        obj = super(Author, self).put()
        memcache.delete(self.email_hash, namespace="authors")
        return obj

    def get_email_hash(self):
        if not self.email_hash:
            self.put()
        return self.email_hash

    @property
    def gravatar_url(self):        
        return "http://www.gravatar.com/avatar/" + self.get_email_hash() + ".jpg?s=80&d=mm"

    @classmethod
    def get_by_hash(self, email_hash):
        author = memcache.get(email_hash, namespace="authors")
        if not author:
            author = Author.gql("WHERE email_hash = :1", email_hash)[:1]            
            author = author[0] if author else None
            memcache.set(email_hash, author, time=CACHE_EXP_SECS, namespace='authors')
        return author


class Comment(db.Model):
    article   = db.ReferenceProperty(Article, required=True)
    author    = db.ReferenceProperty(Author,  required=True)
    comment   = db.TextProperty(required=True)
    author_ip = db.StringProperty(required=False)

    created_at = db.DateTimeProperty(auto_now_add=True)
    updated_at = db.DateTimeProperty(auto_now=True)    

    def delete(self, *args, **kwargs):
        # invalidates cache
        memcache.delete(self.article.url, namespace='comments')
        return super(Comment, self).delete(*args, **kwargs)

    def put(self, *args, **kwargs):
        obj = super(Comment, self).put(*args, **kwargs)
        # invalidates cache
        memcache.delete(self.article.url, namespace='comments')
        return obj

    @classmethod
    def get_comments(self, article_url):
        comments = memcache.get(article_url, namespace="comments")

        if not comments:
            article = Article.get_by_key_name(article_url)
            if article:
                comments = Comment.gql("WHERE article = :1", article)
                comments = [ {'id': c.key().id(), 'comment': c.comment, 'created_at': c.created_at, "author": { "name": c.author.name, 'url': c.author.url, 'email': c.author.email, 'gravatar_url': c.author.gravatar_url }} for c in comments ]
            else:
                comments = []

            memcache.set(article_url, comments, time=CACHE_EXP_SECS, namespace='comments')

        return comments

########NEW FILE########
__FILENAME__ = tasks
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


from google.appengine.api import mail
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, Http404
from django.conf import settings
from buzzengine.api import models


def notify(request):
    comment_id = request.REQUEST.get('comment_id')
    article_url = request.REQUEST.get('article_url')

    article = models.Article.get_by_key_name(article_url)
    if not article: raise Http404

    comment_id = int(comment_id)
    comment = models.Comment.get_by_id(comment_id, parent=article)
    if not comment: raise Http404        

    author = comment.author

    tpl = get_template("api/email_notification.txt")
    ctx = Context({'author': author, 'article_url': article_url, 'comment': comment, 'API_DOMAIN': request.API_DOMAIN})
    txt = tpl.render(ctx)

    mail.send_mail(
        sender=settings.EMAIL_SENDER,
        to=settings.ADMIN_EMAIL,
        subject=author.name + " commented on your blog",
        body=txt)

    return HttpResponse("Mail sent!")

########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


from django.conf.urls.defaults import *
from buzzengine.api import views 
from buzzengine.api import tasks

urlpatterns = patterns('',
    (r'^hello/$', views.say_hello),
    (r'^comments/$', views.comments),
    (r'^notify/$', tasks.notify),
    (r'^test/page.html$', views.test_page),
    (r'^export/$', views.export_xml),
)

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


import hashlib
import re

from datetime import datetime, timedelta
from django.utils import simplejson as json

from google.appengine.api import mail
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.conf import settings
from buzzengine.api.forms import NewCommentForm
from buzzengine.api import models


def comments(request):
    url = request.REQUEST.get('article_url') or request.META.get('HTTP_REFERER')
    if not url:
        raise Http404

    if url.rfind('#') > 0:
        url = url[:url.rfind('#')]

    if not url:        
        resp = HttpResponse(json.dumps({'article_url': ['This field is required.']}, indent=4), mimetype='text/plain')
        resp.status_code = 400
        return resp

    if request.method == 'POST':
        return _comment_create(request, url)
    else:
        return _comment_list(request, url)


def _comment_create(request, article_url):
    data = request.POST
    data = dict([ (k,data[k]) for k in data.keys() ])

    data['article_url'] = article_url
    data['author_ip']   = _discover_user_ip(request)

    is_json = not request.META['HTTP_ACCEPT'].find("html")

    form = NewCommentForm(data)
    if not form.is_valid():
        if is_json:
            resp = HttpResponse(json.dumps(form.errors, indent=4), mimetype='text/plain')
            resp.status_code = 400
            return resp
        else:
            return _comment_list(request, article_url, form=form)

    new_comment = form.save()
    if is_json:
        response = HttpResponse("OK", mimetype='text/plain')

    return _comment_list(request, article_url=article_url, author=new_comment.author)


def _comment_list(request, article_url, form=None, author=None):

    comments = models.Comment.get_comments(article_url)

    is_json = not request.META['HTTP_ACCEPT'].find("html")
    if is_json:
        comments = [ {'comment': c['comment'], "author": { "name": c['author']['name'], 'url': c['author']['url'], 'gravatar_url': c['author']['gravatar_url'] }} for c in comments ]
        return HttpResponse(json.dumps(comments, indent=4), mimetype="text/plain")

    data = request.POST
    data = dict([ (k,data[k]) for k in data.keys() ])
    data['article_url'] = article_url
    data['comment']     = None

    author = author or request.author
    if author and not (data.get('author_name') or data.get('author_email') or data.get('author_url')):
        data['author_name']  = author.name
        data['author_email'] = author.email
        data['author_url']   = author.url

    comments.sort(lambda a,b: cmp(a['created_at'], b['created_at']))

    form = form or NewCommentForm(initial=data)
    return render_to_response("api/comments.html", {'comments': comments, 'form': form, 'API_DOMAIN': request.API_DOMAIN, 'current_author': author})


def _discover_user_ip(request):
    # discover IP of user
    ip = request.META['REMOTE_ADDR']
    if ip == '127.0.0.1':
        try:
            ip = request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
        except:
            pass
    return ip

def say_hello(request):    
    return HttpResponse("TheBuzzEngine greeted with %s, says hello!" % request.method, mimetype="text/html")

def test_page(request):
    return render_to_response("api/test_page.html", { 'API_DOMAIN': request.API_DOMAIN })


def crossdomain_xml(request):
    return HttpResponseRedirect("/static/local-policy.xml")

def export_xml(request):
    articles = models.Article.all()
    output = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dsq="http://www.disqus.com/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:wp="http://wordpress.org/export/1.0/" >
  <channel>
"""
    for article in articles:
        output += "   <item>\n"
        output += """
      <title>%s</title>
      <link>%s</link>
      <dsq:thread_identifier>%s</dsq:thread_identifier>
      <wp:post_date_gmt>%s</wp:post_date_gmt>
      <wp:comment_status>open</wp:comment_status>
""" % (article.title or article.url, article.url or '', article.url or '', article.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        comments = models.Comment.get_comments(article.url)
        for comment in comments:
            output += "      <wp:comment>\n"
            output += """
        <wp:comment_id>%s</wp:comment_id>
        <wp:comment_author>%s</wp:comment_author>
        <wp:comment_author_email>%s</wp:comment_author_email>
        <wp:comment_author_url>%s</wp:comment_author_url>
        <wp:comment_date_gmt>%s</wp:comment_date_gmt>
        <wp:comment_content><![CDATA[%s]]></wp:comment_content>
        <wp:comment_approved>1</wp:comment_approved>
        <wp:comment_parent>0</wp:comment_parent>""" % (

                comment['id'],
                comment['author'].get('name') or '',
                comment['author'].get('email') or '',
                comment['author'].get('url') or '',
                comment['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                comment['comment'],
                
            )
            output += "      </wp:comment>\n"

        output += "   </item>\n"

    output += """  </channel>
</rss>"""

    return HttpResponse(output, mimetype="text/plain")

        


########NEW FILE########
__FILENAME__ = email_handler
import logging, email
from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app

class LogSenderHandler(InboundMailHandler):
    def receive(self, mail_message):
        logging.info("Received a message from: " + mail_message.sender)

application = webapp.WSGIApplication([LogSenderHandler.mapping()], debug=True)

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


from django.conf import settings
from google.appengine.api import users
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response


def requires_admin(view):
    def f(request, *args, **kwargs):
        user = users.get_current_user()
        uri = "http://" + request.API_DOMAIN + request.get_full_path()

        if not user:
            return HttpResponseRedirect(users.create_login_url(uri))

        if not users.is_current_user_admin():
            resp = render_to_response("frontend/admin/login_required.html", {'login_url': users.create_login_url(uri), 'user': user})
            resp.status_code = 403
            return resp

        request.user = user
        return view(request, *args, **kwargs)

    return f


########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "alex@magnolialabs.com"


from google.appengine.ext.db import djangoforms as forms
#from django import newforms as forms
from buzzengine.api.models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ['author_ip', 'article', 'author']
########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


from django.conf.urls.defaults import *
from buzzengine.frontend import views


urlpatterns = patterns('',
    (r'^$', views.homepage),
    (r'^admin/edit/$', views.edit_comment),
)

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


import hashlib
import re

from urllib import quote
from datetime import datetime, timedelta
from django.utils import simplejson as json

from google.appengine.api import users
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from buzzengine.api import models
from buzzengine.frontend.decorators import requires_admin
from buzzengine.frontend.forms import CommentForm


def homepage(request):
    return render_to_response("frontend/homepage.html", {'API_DOMAIN': request.API_DOMAIN})


@requires_admin
def edit_comment(request):
    comment = _get_item(request)
    form = CommentForm(instance=comment)

    if request.method == "POST":
        if request.POST.get('delete'):
            comment.delete()

            article_url = request.REQUEST.get('article_url')
            if article_url.find('#') == -1:
                article_url += '#comments'

            return HttpResponseRedirect(article_url) 
        else:
            form = CommentForm(request.POST, instance=comment)
            if form.is_valid():
                form.save()
                return _render(request, "frontend/admin/edit.html", {"form": form, "comment": comment, 'message': 'Message saved!'})

    return _render(request, "frontend/admin/edit.html", {"form": form, "comment": comment})


def _get_item(request):
    comment_id = request.REQUEST.get('comment_id')
    article_url = request.REQUEST.get('article_url')

    article = models.Article.get_by_key_name(article_url)
    if not article: raise Http404

    comment_id = int(comment_id)
    comment = models.Comment.get_by_id(comment_id, parent=article)
    if not comment: raise Http404        

    return comment
    

def _render(request, tpl_name, kwargs):
    kwargs['user'] = request.user
    kwargs['logout_url'] = users.create_logout_url("/")
    return render_to_response(tpl_name, kwargs)
########NEW FILE########
__FILENAME__ = handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


import logging
import os,sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'buzzengine.settings'

# Google App Engine imports.
from google.appengine.ext.webapp import util

# Force Django to reload its settings.
from django.conf import settings
settings._target = None

import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def log_exception(*args, **kwds):
   logging.exception('Exception in request:')

# Log errors.
django.dispatch.dispatcher.connect(
   log_exception, django.core.signals.got_request_exception)

# Unregister the rollback event handler.
django.dispatch.dispatcher.disconnect(
    django.db._rollback_on_exception,
    django.core.signals.got_request_exception)

def main():
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()

    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
import os

# when a new comment happens, 
# this email address receives an alert
ADMIN_EMAIL  = "contact@alexn.org"

# FROM header of new message notifications.  Unfortunately it must be
# an approved sender ... like the emails of admins you approve for the
# GAE Application Instance.
#
# Some details here:
#   http://code.google.com/appengine/docs/python/mail/sendingmail.html
#
EMAIL_SENDER = "TheBuzzEngine <messages@thebuzzengine.com>"


## Web framework specific stuff ...

DEBUG = False
ROOT_PATH = os.path.dirname(__file__)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'buzzengine.api.middleware.TrackingMiddleware',
    'buzzengine.api.middleware.HttpControlMiddleware',
)
INSTALLED_APPS = (
    'buzzengine.api',
    'buzzengine.frontend',
)
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)
ROOT_URLCONF = 'buzzengine.urls'



########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Alexandru Nedelcu"
__email__     = "contact@alexn.org"


from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^api/', include('buzzengine.api.urls')),
    (r'', include('buzzengine.frontend.urls')),
)



########NEW FILE########
