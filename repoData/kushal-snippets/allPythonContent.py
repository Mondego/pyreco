__FILENAME__ = dateutil
import datetime

class Eastern_tzinfo(datetime.tzinfo):
    """Implementation of the Eastern timezone.
    
    Adapted from http://code.google.com/appengine/docs/python/datastore/typesandpropertyclasses.html
    """
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5) + self.dst(dt)

    def _FirstSunday(self, dt):
        """First Sunday on or after dt."""
        return dt + datetime.timedelta(days=(6-dt.weekday()))

    def dst(self, dt):
        # 2 am on the second Sunday in March
        dst_start = self._FirstSunday(datetime.datetime(dt.year, 3, 8, 2))
        # 1 am on the first Sunday in November
        dst_end = self._FirstSunday(datetime.datetime(dt.year, 11, 1, 1))

        if dst_start <= dt.replace(tzinfo=None) < dst_end:
            return datetime.timedelta(hours=1)
        else:
            return datetime.timedelta(hours=0)
        
    def tzname(self, dt):
        if self.dst(dt) == datetime.timedelta(hours=0):
            return "EST"
        else:
            return "EDT"
        
        
def date_for_new_snippet():
    """Return next Monday, unless it is Monday (0) or Tuesday (1)"""
    today = datetime.datetime.now(Eastern_tzinfo()).date()
    if (today.weekday() < 2):
        aligned = today - datetime.timedelta(days=today.weekday())
    else:
        aligned = today + datetime.timedelta(days=(7 - today.weekday()))
    return aligned


def date_for_retrieval():
    """Always return the most recent Monday."""
    today = datetime.datetime.now(Eastern_tzinfo()).date()
    return today - datetime.timedelta(days=today.weekday())

########NEW FILE########
__FILENAME__ = emails
import logging

from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from dateutil import *
from model import *

REMINDER = """
Hey nerd,

The kids want to know what you're up to. Don't leave 'em hanging.
"""

class ReminderEmail(webapp.RequestHandler):
    def get(self):
        all_users = User.all().filter("enabled =", True).fetch(500)
        for user in all_users:
            # TODO: Check if one has already been submitted for this period.
            taskqueue.add(url='/onereminder', params={'email': user.email})


class OneReminderEmail(webapp.RequestHandler):
    def post(self):
        mail.send_mail(sender="snippets <snippets@fssnippets.appspotmail.com>",
                       to=self.request.get('email'),
                       subject="Snippet time!",
                       body=REMINDER)

    def get(self):
        post(self)

class DigestEmail(webapp.RequestHandler):
    def get(self):
        all_users = User.all().filter("enabled =", True).fetch(500)
        for user in all_users:
            taskqueue.add(url='/onedigest', params={'email': user.email})
            

class OneDigestEmail(webapp.RequestHandler):
    def __send_mail(self, recipient, body):
        mail.send_mail(sender="snippets <snippets@fssnippets.appspotmail.com>",
                       to=recipient,
                       subject="Snippet delivery!",
                       body=body)

    def __snippet_to_text(self, snippet):
        divider = '-' * 30
        return '%s\n%s\n%s' % (snippet.user.pretty_name(), divider, snippet.text)

    def get(self):
        post(self)

    def post(self):
        user = user_from_email(self.request.get('email'))
        d = date_for_retrieval()
        all_snippets = Snippet.all().filter("date =", d).fetch(500)
        all_users = User.all().fetch(500)
        following = compute_following(user, all_users)
        logging.info(all_snippets)
        body = '\n\n\n'.join([self.__snippet_to_text(s) for s in all_snippets if s.user.email in following])
        if body:
            self.__send_mail(user.email, 'https://fssnippets.appspot.com\n\n' + body)
        else:
            logging.info(user.email + ' not following anybody.')

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#
import os

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from emails import *
from model import *

import functools
import urllib

def authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # TODO: handle post requests separately
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return None
        return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(webapp.RequestHandler):
    def get_user(self):
        '''Returns the user object on authenticated requests'''
        user = users.get_current_user()
        assert user

        userObj = User.all().filter("email =", user.email()).fetch(1)
        if not userObj:
            userObj = User(email=user.email())
            userObj.put()
        else:
            userObj = userObj[0]
        return userObj
    
    def render(self, template_name, template_values):
        #self.response.headers['Content-Type'] = 'text/html'
        path = os.path.join(os.path.dirname(__file__), 'templates/%s.html' % template_name)
        self.response.out.write(template.render(path, template_values))
        

class UserHandler(BaseHandler):
    """Show a given user's snippets."""

    @authenticated
    def get(self, email):
        user = self.get_user()
        email = urllib.unquote_plus(email)
        desired_user = user_from_email(email)
        snippets = desired_user.snippet_set
        snippets = sorted(snippets, key=lambda s: s.date, reverse=True)
        following = email in user.following 
        tags = [(t, t in user.tags_following) for t in desired_user.tags]
         
        template_values = {
                           'current_user' : user,
                           'user': desired_user,
                           'snippets': snippets,
                           'following': following,
                           'tags': tags
                           }
        self.render('user', template_values)


class FollowHandler(BaseHandler):
    """Follow a user or tag."""
    @authenticated
    def get(self):
        user = self.get_user()
        desired_tag = self.request.get('tag')
        desired_user = self.request.get('user')
        continue_url = self.request.get('continue')
        
        if desired_tag and (desired_tag not in user.tags_following):
            user.tags_following.append(desired_tag)
            user.put()
        if desired_user and (desired_user not in user.following):
            user.following.append(desired_user)
            user.put()
            
        self.redirect(continue_url)


class UnfollowHandler(BaseHandler):
    """Unfollow a user or tag."""
    @authenticated
    def get(self):
        user = self.get_user()
        desired_tag = self.request.get('tag')
        desired_user = self.request.get('user')
        continue_url = self.request.get('continue')
        
        if desired_tag and (desired_tag in user.tags_following):
            user.tags_following.remove(desired_tag)
            user.put()
        if desired_user and (desired_user in user.following):
            user.following.remove(desired_user)
            user.put()
            
        self.redirect(continue_url)
        

class TagHandler(BaseHandler):
    """View this week's snippets in a given tag."""
    @authenticated
    def get(self, tag):
        user = self.get_user()
        d = date_for_retrieval()
        all_snippets = Snippet.all().filter("date =", d).fetch(500)
        if (tag != 'all'):
            all_snippets = [s for s in all_snippets if tag in s.user.tags]
        following = tag in user.tags_following

        template_values = {
                           'current_user' : user,
                           'snippets': all_snippets,
                           'following': following,
                           'tag': tag
                           }
        self.render('tag', template_values)

    
class MainHandler(BaseHandler):
    """Show list of all users and acting user's settings."""

    @authenticated
    def get(self):
        user = self.get_user()
        # Update enabled state if requested
        set_enabled = self.request.get('setenabled')
        if set_enabled == '1':
            user.enabled = True
            user.put()
        elif set_enabled == '0':
            user.enabled = False
            user.put()

        # Update tags if sent
        tags = self.request.get('tags')
        if tags:
            user.tags = [s.strip() for s in tags.split(',')]
            user.put()
            
        # Fetch user list and display
        raw_users = User.all().order('email').fetch(500)
        following = compute_following(user, raw_users)
        all_users = [(u, u.email in following) for u in raw_users]
        all_tags = set()
        for u in raw_users:
            all_tags.update(u.tags)
        all_tags = [(t, t in user.tags_following) for t in all_tags]
        
        template_values = {
                           'current_user' : user,
                           'all_users': all_users,
                           'all_tags': all_tags                           
                           }
        self.render('index', template_values)


def main():
    application = webapp.WSGIApplication(
                                         [('/', MainHandler),
                                          ('/user/(.*)', UserHandler),
                                          ('/tag/(.*)', TagHandler),
                                          ('/follow', FollowHandler),
                                          ('/unfollow', UnfollowHandler),
                                          ('/reminderemail', ReminderEmail),
                                          ('/digestemail', DigestEmail),
                                          ('/onereminder', OneReminderEmail),
                                          ('/onedigest', OneDigestEmail)],
                                          debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = model
import logging

from google.appengine.api import users
from google.appengine.ext import db

class User(db.Model):
    # Just store email address, because GAFYD seems to be buggy (omits domain in stored email or something...)
    email = db.StringProperty()
    following = db.StringListProperty()
    enabled = db.BooleanProperty(default=True)
    tags = db.StringListProperty()
    tags_following = db.StringListProperty()
    
    def pretty_name(self):
        return self.email.split('@')[0]
    
class Snippet(db.Model):
    user = db.ReferenceProperty(User)
    text = db.TextProperty()
    date = db.DateProperty()
    
def compute_following(current_user, users):
    """Return set of email addresses being followed by this user."""
    email_set = set(current_user.following)
    tag_set = set(current_user.tags_following)
    following = set()
    for u in users:
        if ((u.email in email_set) or
            (len(tag_set.intersection(u.tags)) > 0)):
            following.add(u.email)
    return following            
    
def user_from_email(email):
    return User.all().filter("email =", email).fetch(1)[0]
    
def create_or_replace_snippet(user, text, date):
    # Delete existing (yeah, yeah, should be a transaction)
    for existing in Snippet.all().filter("date =", date).filter("user =", user).fetch(10):
        existing.delete()
    
    # Write new
    snippet = Snippet(text=text, user=user, date=date)
    snippet.put()
       
########NEW FILE########
__FILENAME__ = receive_email
import datetime
import email
import logging
import re

from google.appengine.ext import webapp
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp import util

from dateutil import date_for_new_snippet
from model import user_from_email, create_or_replace_snippet

class ReceiveEmail(InboundMailHandler):
    """Receive a snippet email and create or replace snippet for this week."""

    def receive(self, message):
        user = user_from_email(email.utils.parseaddr(message.sender)[1])
        for content_type, body in message.bodies('text/plain'):
            # http://stackoverflow.com/questions/4021392/how-do-you-decode-a-binary-encoded-mail-message-in-python
            if body.encoding == '8bit':
                body.encoding = '7bit'
            content = body.decode()

            sig_pattern = re.compile(r'^\-\-\s*$', re.MULTILINE)
            split_email = re.split(sig_pattern, content)
            content = split_email[0]

            reply_pattern = re.compile(r'^On.*at.*snippets', re.MULTILINE)
            split_email = re.split(reply_pattern, content)
            content = split_email[0]

            create_or_replace_snippet(user, content, date_for_new_snippet())


def main():
    application = webapp.WSGIApplication([ReceiveEmail.mapping()], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()



########NEW FILE########
