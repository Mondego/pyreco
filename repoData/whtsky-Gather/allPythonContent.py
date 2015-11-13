__FILENAME__ = fabfile
from fabric.api import *

env.hosts = ['whtsky@pbb.whouz.com']


def update():
    with cd('~/PBB'):
        run('git pull origin master')
        run('./bin/pip install -r requirements.txt')


########NEW FILE########
__FILENAME__ = account
# coding=utf-8

import time
import hashlib
import tornado.web
import tornado.locale
from bson.objectid import ObjectId
from . import BaseHandler
from .utils import username_validator, email_validator


class SignupHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect(self.get_argument('next', '/'))
        self.render('account/signup.html')

    def post(self):
        self.recaptcha_validate()
        username = self.get_argument('username', None)
        email = self.get_argument('email', '').lower()
        password = self.get_argument('password', None)
        password2 = self.get_argument('password2', None)
        if not (username and email and password and password2):
            self.flash('Please fill the required field')
        if password != password2:
            self.flash("Password doesn't match")
        if username and not username_validator.match(username):
            self.flash('Username is invalid')
        if email and not email_validator.match(email):
            self.flash('Not a valid email address')
        if username and \
           self.db.members.find_one({'name_lower': username.lower()}):
            self.flash('This username is already registered')
        if email and self.db.members.find_one({'email': email}):
            self.flash('This email is already registered')
        if self.messages:
            self.render('account/signup.html')
            return
        password = hashlib.sha1(password + username.lower()).hexdigest()
        role = 1
        if not self.db.members.count():
            role = 5
        self.db.members.insert({
            'name': username,
            'name_lower': username.lower(),
            'password': password,
            'email': email,
            'website': '',
            'description': '',
            'created': time.time(),
            'language': self.settings['default_locale'],
            'role': role,  # TODO:send mail.
            'like': [],  # topics
            'follow': [],  # users
            'favorite': []  # nodes

        })
        self.set_secure_cookie('user', password, expires_days=30)
        self.redirect(self.get_argument('next', '/'))


class SigninHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect(self.get_argument('next', '/'))
        self.render('account/signin.html')

    def post(self):
        username = self.get_argument('username', '').lower()
        password = self.get_argument('password', None)
        if not (username and password):
            self.flash('Please fill the required field')
        password = hashlib.sha1(password + username).hexdigest()
        member = self.db.members.find_one({'name_lower': username,
                                           'password': password})
        if not member:
            self.flash('Invalid account or password')
            self.render('account/signin.html')
            return
        self.set_secure_cookie('user', password, expires_days=30)
        self.redirect(self.get_argument('next', '/'))


class SignoutHandler(BaseHandler):
    def get(self):
        user_name = self.get_argument('user', None)
        if user_name != self.current_user['name']:
            raise tornado.web.HTTPError(403)
        self.clear_cookie('user')
        self.redirect(self.get_argument('next', '/'))


class SettingsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('account/settings.html', locales=self.application.locales)

    @tornado.web.authenticated
    def post(self):
        website = self.get_argument('website', '')
        description = self.get_argument('description', '')
        pushover = self.get_argument('pushover', '')
        language = self.get_argument('language')
        if len(description) > 1500:
            self.flash("The description is too long")
        self.db.members.update({'_id': self.current_user['_id']}, {'$set': {
            'website': website,
            'description': description,
            'language': language,
            'pushover': pushover
        }})
        self.flash('Saved successfully', type='success')
        self.redirect('/account/settings')


class ChangePasswordHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        old_password = self.get_argument('old_password', None)
        new_password = self.get_argument('new_password', None)
        if not (old_password and new_password):
            self.flash('Please fill the required field')
        key = old_password + self.current_user['name'].lower()
        password = hashlib.sha1(key).hexdigest()
        if password != self.current_user['password']:
            self.flash('Invalid password')
        if self.messages:
            self.redirect('/account/settings')
            return
        key = new_password + self.current_user['name'].lower()
        password = str(hashlib.sha1(key).hexdigest())
        self.db.members.update({'_id': self.current_user['_id']},
                               {'$set': {'password': password}})
        self.set_secure_cookie('user', password, expires_days=30)
        self.flash('Saved successfully', type='success')
        self.redirect('/account/settings')


class NotificationsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        p = int(self.get_argument('p', 1))
        notis = self.db.notifications.find({
            'to': self.current_user['name_lower']
        }, sort=[('created', -1)])
        notis_count = notis.count()
        per_page = self.settings['notifications_per_page']
        notis = notis[(p - 1) * per_page:p * per_page]
        self.render('account/notifications.html', notis=notis,
                    notis_count=notis_count, p=p)


class NotificationsClearHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.db.notifications.remove({'to': self.current_user['name_lower']})
        self.redirect('/')


class NotificationsRemoveHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        self.db.notifications.remove({'_id': ObjectId(id)})
        self.redirect(self.get_argument('next', '/account/notifications'))


handlers = [
    (r'/account/signup', SignupHandler),
    (r'/account/signin', SigninHandler),
    (r'/account/signout', SignoutHandler),
    (r'/account/settings', SettingsHandler),
    (r'/account/password', ChangePasswordHandler),
    (r'/account/notifications', NotificationsHandler),
    (r'/account/notifications/clear', NotificationsClearHandler),
    (r'/account/notifications/(\w+)/remove', NotificationsRemoveHandler),
]

########NEW FILE########
__FILENAME__ = api
import re
import tornado.web
import tornado.escape

from . import BaseHandler

html_re = re.compile('(<.*?>)')


class NewNotificationsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        notifications = []
        notis = self.db.notifications.find({
            'to': self.current_user['name_lower'],
            'read': False
        }, sort=[('created', -1)])
        for noti in notis:
            member = self.get_member(noti['from'])
            topic = self.get_topic(noti['topic'])
            content = html_re.sub('', noti['content'])
            content = tornado.escape.xhtml_unescape(content)
            avatar = self.get_avatar_img(member, size=128)
            notifications.append({
                'id': str(noti['_id']),
                'avatar': avatar,
                'title': '%s mentioned you at %s' %
                (member['name'], topic['title']),
                'content': content,
                'url': '/topic/%s' % topic['_id']
            })

        if not notifications:
            return

        # Turn to json.
        self.write({
            "notifications": notifications,
            "id": notifications[0]['id']
        })
        # https://github.com/facebook/tornado/blob/master/tornado/web.py#L501


class TopicAsJSONHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, topic_id):
        d = dict(**self.get_topic(topic_id))
        d['_id'] = str(d['_id'])
        replies = self.db.replies.find({'topic': topic_id},
                                            sort=[('index', 1)])
        d['replies_count'] = str(replies.count())

        self.write(d) # isinstance(d, dict) == True


handlers = [
    (r'/api/notifications/new', NewNotificationsHandler),
    (r'/api/topic/(\w+)', TopicAsJSONHandler),
]

########NEW FILE########
__FILENAME__ = dashboard
# coding=utf-8

from bson.objectid import ObjectId
from . import BaseHandler as _BaseHandler


class BaseHandler(_BaseHandler):
    def prepare(self):
        self.check_role(role_min=3)
        super(BaseHandler, self).prepare()


class LinkHandler(BaseHandler):
    def get(self):
        self.render('dashboard/link.html')

    def post(self):
        name = self.get_argument('name', None)
        link = self.get_argument('link', None)
        title = self.get_argument('title', '')
        priority = int(self.get_argument('priority', 1))
        if not (name and link and priority):
            self.flash('Please fill the required field')
        if link and self.db.links.find_one({'link': link.lower()}):
            self.flash('This link has been registered')
        if self.messages:
            self.redirect('/dashboard/link')
        self.db.links.insert({
            'name': name,
            'link': link,
            'title': title,
            'priority': priority,
        })
        self.redirect('/dashboard/link')


class RemoveLinkHandler(BaseHandler):
    def get(self, link_id):
        self.db.links.remove(ObjectId(link_id))
        self.redirect('/dashboard/link')


handlers = [
    (r'/dashboard/link', LinkHandler),
    (r'/dashboard/link/(\w+)/remove', RemoveLinkHandler),
]

########NEW FILE########
__FILENAME__ = member
# coding=utf-8

import tornado.web
from . import BaseHandler


class MemberListHandler(BaseHandler):
    def get(self):
        per_page = self.settings['members_per_page']
        members = self.db.members.find(sort=[('created', -1)])
        count = members.count()
        p = int(self.get_argument('p', 1))
        members = members[(p - 1) * per_page:p * per_page]
        self.render('member/list.html', per_page=per_page, members=members,
                    count=count, p=p)


class MemberPageHandler(BaseHandler):
    def get(self, name):
        member = self.get_member(name)
        topics = self.db.topics.find({'author': member['name']},
                                     sort=[('last_reply_time', -1)])
        topics = topics[:self.settings['topics_per_page']]
        replies = self.db.replies.find({'author': member['name']},
                                       sort=[('created', -1)])
        replies = replies[:self.settings['replies_per_page']]
        if member['like']:
            member['like'] = member['like'][:self.settings['topics_per_page']]
            liked_topics = [self.get_topic(x) for x in member['like']]
        else:
            liked_topics = []
        self.render('member/member.html', member=member, topics=topics,
                    replies=replies, liked_topics=liked_topics)


class MemberTopicsHandler(BaseHandler):
    def get(self, name):
        member = self.get_member(name)
        topics = self.db.topics.find(
            {'author': member['name']},
            sort=[('last_reply_time', -1)]
        )
        topics_count = topics.count()
        p = int(self.get_argument('p', 1))
        topics = topics[(p - 1) * self.settings['topics_per_page']:
                        p*self.settings['topics_per_page']]
        self.render('member/topics.html', member=member,
                    topics=topics, topics_count=topics_count, p=p)


class ChangeRoleHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, name):
        role = int(self.get_argument('role', 100))
        if self.current_user['role'] < 3:
            self.check_role(role_min=role + 1)
        name = name.lower()
        self.db.members.update({'name_lower': name},
                               {'$set': {'role': role}})
        self.redirect('/member/' + name)


handlers = [
    (r'/member', MemberListHandler),
    (r'/member/(\w+)', MemberPageHandler),
    (r'/member/(\w+)/topics', MemberTopicsHandler),
    (r'/member/(\w+)/role', ChangeRoleHandler),
]

########NEW FILE########
__FILENAME__ = node
 # coding=utf-8

import tornado.web
from . import BaseHandler


class NodeListHandler(BaseHandler):
    def get(self):
        nodes = self.db.nodes.find()
        self.render('node/list.html', nodes=nodes)


class NodeHandler(BaseHandler):
    def get(self, node_name):
        node = self.get_node(node_name)
        topics = self.db.topics.find({'node': node['name']},
                                     sort=[('last_reply_time', -1)])
        topics_count = topics.count()
        p = int(self.get_argument('p', 1))
        self.render('node/node.html', node=node, topics=topics,
                    topics_count=topics_count, p=p)


class AddHandler(BaseHandler):
    def get(self):
        self.check_role()
        self.render('node/add.html')

    def post(self):
        self.check_role()
        name = self.get_argument('name', None)
        title = self.get_argument('title', None)
        if not title:
            title = name
        if not (name and title):
            self.flash('Please fill the required field')
        if self.db.nodes.find_one({'name_lower': name.lower()}):
            self.flash('This node name is already registered')
        if self.db.nodes.find_one({'title': title}):
            self.flash('This node title is already registered')
        if self.messages:
            self.render('node/add.html')
            return

        description = self.get_argument('description', '')
        html = self.get_argument('html', '')
        self.db.nodes.insert({
            'name': name,
            'name_lower': name.lower(),
            'title': title,
            'description': description,
            'html': html,
        })
        self.redirect(self.get_argument('next', '/node/' + name))


class EditHandler(BaseHandler):
    def get(self, node_name):
        self.check_role()
        node = self.get_node(node_name)
        self.render('node/edit.html', node=node)

    def post(self, node_name):
        self.check_role()
        node = self.get_node(node_name)
        name = self.get_argument('name', None)
        title = self.get_argument('title', name)
        if not name:
            self.flash('Please fill the required field')
        if name != node['name'] and \
                self.db.nodes.find_one({'name_lower': name.lower()}):
                self.flash('This node name is already registered')
        if title != node['title'] and \
                self.db.nodes.find_one({'title': title}):
            self.flash('This node title is already registered')
        if self.messages:
            self.render('node/edit.html', node=node)
            return

        self.db.topics.update({'node': node['name']},
                              {'$set': {'node': name}}, multi=True)
        node['name'] = name
        node['name_lower'] = name.lower()
        node['title'] = title
        node['description'] = self.get_argument('description', '')
        node['description'] = self.get_argument('description', '')
        node['html'] = self.get_argument('html', '')
        self.db.nodes.save(node)

        self.flash('Saved successfully', type='success')
        self.redirect(self.get_argument('next', '/node/' + node['name']))


class RemoveHandler(BaseHandler):
    def get(self, node_name):
        self.check_role()
        node = self.get_node(node_name)
        self.render('node/remove.html', node=node)

    def post(self, node_name):
        self.check_role()
        from_node = self.get_node(node_name)
        node_name = self.get_argument('node')
        to_node = self.get_node(node_name)
        members = self.db.members.find({'favorite': from_node['name']})
        for member in members:
            member['favorite'].remove(from_node['name'])
            self.db.members.save(member)

        self.db.nodes.remove(from_node)
        self.db.topics.update({'node': from_node['name']},
                              {'$set': {'node': to_node['name']}}, multi=True)
        self.flash('Removed successfully', type='success')
        self.redirect('/')


class NodeSidebar(tornado.web.UIModule):
    def render(self, node):
        return self.render_string("node/modules/sidebar.html", node=node)


class FeedHandler(BaseHandler):
    def get(self, node_name):
        node = self.get_node(node_name)
        topics = self.db.topics.find({'node': node['name']},
                                     sort=[('modified', -1)])
        self.render('feed.xml', topics=topics)


handlers = [
    (r'/node', NodeListHandler),
    (r'/node/add', AddHandler),
    (r'/node/([%A-Za-z0-9.-]+)', NodeHandler),
    (r'/node/([%A-Za-z0-9.-]+)/edit', EditHandler),
    (r'/node/([%A-Za-z0-9.-]+)/remove', RemoveHandler),
    (r'/node/([%A-Za-z0-9.-]+)/feed', FeedHandler),
]

ui_modules = {
    'node_sitebar': NodeSidebar,
}

########NEW FILE########
__FILENAME__ = others
# coding=utf-8

from . import BaseHandler


class UserAgentHandler(BaseHandler):
    def get(self):
        ua = self.request.headers.get("User-Agent", "Unknow")
        source = self.get_source()
        if not source:
            source = 'Desktop'
        self.render('others/ua.html', ua=ua, source=source)


class FeedHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "text/xml")
        topics = self.db.topics.find(sort=[('modified', -1)])
        self.render('feed.xml', topics=topics)

handlers = [
    (r'/ua', UserAgentHandler),
    (r'/feed', FeedHandler),
]

########NEW FILE########
__FILENAME__ = recaptcha
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Hsiaoming Yang
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#    * Neither the name of the author nor the names of its contributors
#      may be used to endorse or promote products derived from this
#      software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import urllib


class RecaptchaMixin(object):
    """RecaptchaMixin

    You must define some options for this mixin. All information
    can be found at http://www.google.com/recaptcha

    A basic example::

        from tornado.options import define
        from tornado.web import RequestHandler, asynchronous
        define('recaptcha_key', 'key')
        define('recaptcha_secret', 'secret')
        define('recaptcha_theme', 'clean')

        class SignupHandler(RequestHandler, RecaptchaMixin):
            def get(self):
                self.write('<form method="post" action="">')
                self.write(self.xsrf_form_html())
                self.write(self.recaptcha_render())
                self.write('<button type="submit">Submit</button>')
                self.write('</form>')

            @asynchronous
            def post(self):
                self.recaptcha_validate(self._on_validate)

            def _on_validate(self, response):
                if response:
                    self.write('success')
                    self.finish()
                    return
                self.write('failed')
                self.finish()
    """

    RECAPTCHA_VERIFY_URL = "http://www.google.com/recaptcha/api/verify"

    def recaptcha_render(self):
        if not self.settings['use_recaptcha']:
            return ''
        token = self._recaptcha_token()
        html = (
            '<div id="recaptcha_div"></div>'
            '<script type="text/javascript" '
            'src="https://www.google.com/recaptcha/api/js/recaptcha_ajax.js">'
            '</script><script type="text/javascript">'
            'Recaptcha.create("%(key)s", "recaptcha_div", '
            '{theme: "%(theme)s",callback:Recaptcha.focus_response_field});'
            '</script>'
        )
        return html % token

    def recaptcha_validate(self):
        if not self.settings['use_recaptcha']:
            return
        token = self._recaptcha_token()
        challenge = self.get_argument('recaptcha_challenge_field', None)
        response = self.get_argument('recaptcha_response_field', None)
        post_args = {
            'privatekey': token['secret'],
            'remoteip': self.request.remote_ip,
            'challenge': challenge,
            'response': response
        }
        body = urllib.urlopen(self.RECAPTCHA_VERIFY_URL,
                              urllib.urlencode(post_args)).read()
        verify, message = body.split()
        if verify != 'true':
            self.flash('Are you human?')
            self.redirect('/')

    def _recaptcha_token(self):
        token = dict(
            key=self.settings['recaptcha_key'],
            secret=self.settings['recaptcha_secret'],
            theme=self.settings['recaptcha_theme'],
        )
        return token

########NEW FILE########
__FILENAME__ = sentry
from tornado.web import HTTPError
from tornado.web import RequestHandler as _RequestHandler

from raven.contrib.tornado import SentryMixin as _SentryMixin


class RequestHandler(_SentryMixin, _RequestHandler):
    def log_exception(self, typ, value, tb):
        if isinstance(value, HTTPError) and value.status_code in [403, 404]:
            _RequestHandler.log_exception(self, typ, value, tb)
        else:
            _SentryMixin.log_exception(self, typ, value, tb)

    def get_sentry_user_info(self):
        user = self.current_user
        data = user or {}
        return {
            'sentry.interfaces.User': {
                "name": user.get("name", ""),
                "email": user.get("email", "")
            }
        }

    def get_sentry_data_from_request(self):
        """
        Extracts the data required for 'sentry.interfaces.Http' from the
        current request being handled by the request handler

        :param return: A dictionary.
        """
        data = super(RequestHandler, self).get_sentry_data_from_request()
        data['sentry.interfaces.Http']['ip'] = self.request.remote_ip
        return data

########NEW FILE########
__FILENAME__ = topic
# coding=utf-8

import time
import logging
import tornado.web

from . import BaseHandler
from bson.objectid import ObjectId
from .utils import make_content


class TopicListHandler(BaseHandler):
    def get(self):
        topics = self.db.topics.find(sort=[('last_reply_time', -1)])
        topics_count = topics.count()
        p = int(self.get_argument('p', 1))
        self.render(
            'topic/list.html', topics=topics,
            topics_count=topics_count, p=p
        )


class TopicHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        if self.current_user:
            self.db.notifications.update({
                'topic': ObjectId(topic_id),
                'to': self.current_user['name_lower']
            }, {'$set': {'read': True}}, multi=True)
            if 'read' in topic:
                self.db.topics.update(
                    {'_id': ObjectId(topic_id)},
                    {'$addToSet': {'read': self.current_user['name_lower']}}
                )
            else:
                self.db.topics.update(
                    {'_id': ObjectId(topic_id)},
                    {'$set': {'read': [self.current_user['name_lower']]}}
                )
        replies = self.db.replies.find({'topic': topic_id},
                                       sort=[('index', 1)])
        replies_count = replies.count()
        p = int(self.get_argument('p', 1))
        if p < 1:
            p = 1

        self.render('topic/topic.html', topic=topic,
                    replies=replies, replies_count=replies_count,
                    p=p)


class CreateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        node_name = self.get_argument("node", "")
        self.render('topic/create.html', node_name=node_name)

    @tornado.web.authenticated
    def post(self):
        node = self.get_argument("node", '')
        title = self.get_argument('title', '')
        content = self.get_argument('content', '')
        if not (node and title and content):
            self.flash('Please fill the required field')
        if len(title) > 100:
            self.flash("The title is too long")
        if len(content) > 20000:
            self.flash("The content is too long")
        if not self.get_node(node):
            raise tornado.web.HTTPError(403)
        if self.messages:
            self.render('topic/create.html', node_name=node)
            return
        topic = self.db.topics.find_one({
            'title': title,
            'content': content,
            'author': self.current_user['name']
        })
        if topic:
            self.redirect('/topic/%s' % topic['_id'])
            return
        time_now = time.time()
        content_html = make_content(content)
        data = {
            'title': title,
            'content': content,
            'content_html': content_html,
            'author': self.current_user['name'],
            'node': node,
            'created': time_now,
            'modified': time_now,
            'last_reply_time': time_now,
            'index': 0,
        }
        source = self.get_source()
        if source:
            data['source'] = source
        topic_id = self.db.topics.insert(data)
        self.send_notification(content_html, topic_id)
        self.redirect('/topic/%s' % topic_id)


class ReplyHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, topic_id):
        content = self.get_argument('content', None)
        if not content:
            self.flash('Please fill the required field')
        elif len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.redirect('/topic/%s' % topic_id)
            return
        reply = self.db.replies.find_one({
            'topic': topic_id,
            'content': content,
            'author': self.current_user['name']
        })
        if reply:
            self.redirect('/topic/%s' % topic_id)
            return
        index = self.db.topics.find_and_modify({'_id': ObjectId(topic_id)},
                                               update={'$inc': {'index': 1}})['index'] + 1
        time_now = time.time()
        content_html = make_content(content)
        self.send_notification(content_html, topic_id)
        source = self.get_source()
        data = {
            'content': content,
            'content_html': content_html,
            'author': self.current_user['name'],
            'topic': topic_id,
            'created': time_now,
            'modified': time_now,
            'index': index,
        }
        if source:
            data['source'] = source
        self.db.replies.insert(data)
        self.db.topics.update({'_id': ObjectId(topic_id)},
                              {'$set': {'last_reply_time': time_now,
                                        'last_reply_by':
                                        self.current_user['name'],
                                        'read': [self.current_user['name_lower']]}})
        reply_nums = self.db.replies.find({'topic': topic_id}).count()
        last_page = self.get_page_num(reply_nums,
                                      self.settings['replies_per_page'])
        self.redirect('/topic/%s?p=%s' % (topic_id, last_page))


class RemoveHandler(BaseHandler):
    def post(self, topic_id):
        self.check_role(owner_name=self.current_user['name'])
        topic_id = ObjectId(topic_id)
        topic = self.get_topic(topic_id)
        self.captureMessage(
            "%s removed a topic" % self.current_user["name"],
            data={
                "level": logging.INFO
            },
            extra={
                "topic": topic
            }
        )
        self.db.histories.remove({"target_id": topic_id})
        self.db.topics.remove({'_id': topic_id})
        self.db.replies.remove({'topic': topic_id})
        self.db.notifications.remove({'topic': ObjectId(topic_id)})
        self.flash('Removed successfully', type='success')


class EditHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        self.check_role(owner_name=topic['author'])
        node = self.get_node(topic['node'])
        self.render('topic/edit.html', topic=topic,
                    node=node)

    def post(self, topic_id):
        topic = self.get_topic(topic_id)
        self.check_role(owner_name=topic['author'])
        title = self.get_argument('title', '')
        content = self.get_argument('content', '')
        if not (title and content):
            self.flash('Please fill the required field')
        if len(title) > 100:
            self.flash("The title is too long")
        if len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.render('topic/edit.html', topic=topic)
            return
        if content == topic['content'] and title == topic['title']:
            self.redirect('/topic/%s' % topic_id)
            return
        if title != topic['title']:
            self.save_history(topic_id, topic['title'], title, type="title")
            topic['title'] = title
        if content != topic['content']:
            self.save_history(topic_id, topic['content'], content)
            topic['content'] = content
            content = make_content(content)
            self.db.notifications.update({'content': topic['content_html'],
                                          'topic': ObjectId(topic_id)},
                                         {'$set': {'content': content}})
            topic['content_html'] = content
        topic['modified'] = time.time()
        self.db.topics.save(topic)
        self.flash('Saved successfully', type='success')
        self.redirect('/topic/%s' % topic_id)


class MoveHandler(BaseHandler):
    def get(self, topic_id):
        topic = self.get_topic(topic_id)
        self.render('topic/move.html', topic=topic)

    def post(self, topic_id):
        node_name = self.get_argument('node', '')
        import logging
        logging.info(node_name)
        node = self.get_node(node_name.lower())
        self.db.topics.update({'_id': ObjectId(topic_id)},
                              {'$set': {'node': node['name']}})
        self.flash('Moved successfully', type='success')
        self.redirect('/topic/%s' % topic_id)


class EditReplyHandler(BaseHandler):
    def get(self, reply_id):
        reply = self.db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.check_role(owner_name=reply['author'])
        self.render('topic/edit_reply.html', reply=reply)

    def post(self, reply_id):
        reply = self.db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.check_role(owner_name=reply['author'])
        content = self.get_argument('content', '')
        if not content:
            self.flash('Please fill the required field')
        elif len(content) > 20000:
            self.flash("The content is too long")
        if self.messages:
            self.render('topic/edit_reply.html', reply=reply)
            return
        if content == reply['content']:
            self.redirect(self.get_argument('next', '/'))
            return
        self.save_history(reply_id, reply['content'], content)
        reply['modified'] = time.time()
        reply['content'] = content
        content = make_content(content)
        self.db.notifications.update({'content': reply['content_html']},
                                     {'$set': {'content': content}})
        reply['content_html'] = content
        self.db.replies.save(reply)
        self.flash('Saved successfully', type='success')
        self.redirect(self.get_argument('next', '/'))


class RemoveReplyHandler(BaseHandler):
    def post(self, reply_id):
        self.check_role(owner_name=self.current_user['name'])
        reply_id = ObjectId(reply_id)
        reply = self.db.replies.find_one({'_id': reply_id})
        if not reply:
            raise tornado.web.HTTPError(404)
        self.db.notifications.remove({
            'from': reply['author'].lower(),
            'content': reply['content_html'],
        }, multi=True)
        topic = self.get_topic(reply['topic'])
        self.captureMessage(
            "%s removed a reply" % self.current_user["name"],
            data={
                "level": logging.INFO
            },
            extra={
                "reply": reply,
                "topic": topic
            }
        )
        self.db.histories.remove({"target_id": reply_id})
        self.db.replies.remove({'_id': reply_id})
        self.flash('Removed successfully', type='success')


class HistoryHandler(BaseHandler):
    def get(self, id):
        self.check_role(role_min=5)
        id = ObjectId(id)
        histories = self.db.histories.find(
            {"target_id": id},
            sort=[('created', 1)]
        )
        self.render("topic/history.html", histories=histories)


class TopicList(tornado.web.UIModule):
    def render(self, topics):
        return self.render_string("topic/modules/list.html", topics=topics)


class Paginator(tornado.web.UIModule):
    def render(self, p, perpage, count, base_url):
        return self.render_string("topic/modules/paginator.html", p=p,
                                  perpage=perpage, count=count, base_url=base_url)


handlers = [
    (r'/', TopicListHandler),
    (r'/topic', TopicListHandler),
    (r'/topic/create', CreateHandler),
    (r'/topic/(\w+)', TopicHandler),
    (r'/topic/(\w+)/edit', EditHandler),
    (r'/topic/(\w+)/reply', ReplyHandler),
    (r'/topic/(\w+)/remove', RemoveHandler),
    (r'/topic/(\w+)/move', MoveHandler),
    (r'/reply/(\w+)/edit', EditReplyHandler),
    (r'/reply/(\w+)/remove', RemoveReplyHandler),
    (r'/history/(\w+)/', HistoryHandler)
]

ui_modules = {
    'topic_list': TopicList,
    'paginator': Paginator,
}

########NEW FILE########
__FILENAME__ = utils
import re
import requests
import settings

from tornado.escape import xhtml_escape, _unicode, _URL_RE
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer

username_validator = re.compile(r'^[a-zA-Z0-9]+$')
email_validator = re.compile(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)

_CODE_RE = re.compile(r'```(\w+)(.+?)```', re.S)
_MENTION_RE = re.compile(r'((?:^|\W)@\w+)')
_FLOOR_RE = re.compile(r'((?:^|\W)#\d+)')
_TOPIC_RE = re.compile(r'((?:^|\W)t[a-z0-9]{24})')
_EMAIL_RE = re.compile(r'([A-Za-z0-9-+.]+@[A-Za-z0-9-.]+)(\s|$)')

formatter = HtmlFormatter()


def make_content(text, extra_params='rel="nofollow"'):
    """https://github.com/facebook/tornado/blob/master/tornado/escape.py#L238
    """
    if extra_params:
        extra_params = " " + extra_params.strip()

    def make_link(m):
        url = m.group(1)
        proto = m.group(2)

        href = m.group(1)
        if not proto:
            href = "http://" + href   # no proto specified, use http

        params = extra_params

        if '.' in href:
            name_extension = href.split('.')[-1].lower()
            if name_extension in ('jpg', 'png', 'git', 'jpeg'):
                return u'<img src="%s" />' % href

        return u'<a href="%s"%s>%s</a>' % (href, params, url)

    def cover_email(m):
        data = {'mail': m.group(1),
                'end': m.group(2)}
        return u'<a href="mailto:%(mail)s">%(mail)s</a>%(end)s' % data

    def convert_mention(m):
        data = {}
        data['begin'], data['user'] = m.group(1).split('@')
        t = u'%(begin)s<a href="/member/%(user)s" class="mention">' \
            u'@%(user)s</a>'
        return t % data

    def convert_floor(m):
        data = {}
        data['begin'], data['floor'] = m.group(1).split('#')
        t = u'%(begin)s<a href="#reply%(floor)s"' \
            ' class="mention mention_floor">#%(floor)s</a>'
        return t % data

    def convert_topic(m):
        data = {}
        data['begin'], data['topic_link'] = m.group(1).split('t')
        data['topic_link_short'] = data['topic_link'][:6]
        t = u"""%(begin)s<a href="%(topic_link)s"
            class="mention mention_topic"
            _id=%(topic_link)s>t%(topic_link_short)s</a>"""
        return t % data

    def highligt(m):
        try:
            name = m.group(1)
            lexer = get_lexer_by_name(name)
        except ValueError:
            lexer = TextLexer()
        text = m.group(2).replace('&quot;', '"').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        return highlight(text, lexer, formatter)

    text = _unicode(xhtml_escape(text)).replace(' ', '&nbsp;')
    text = _CODE_RE.sub(highligt, text).replace('\n', '<br />')
    text = _EMAIL_RE.sub(cover_email, text)
    text = _MENTION_RE.sub(convert_mention, text)
    text = _FLOOR_RE.sub(convert_floor, text)
    text = _TOPIC_RE.sub(convert_topic, text)
    return _URL_RE.sub(make_link, text)


def send_notify(user, message, url):
    if settings.pushover_token:
        return requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": settings.pushover_token,
                "user": user,
                "message": message,
                "url": url
            },
            headers={
                "Content-type": "application/x-www-form-urlencoded"
            }
        ).json()

########NEW FILE########
__FILENAME__ = init_db
# coding=utf-8

import settings
import pymongo

db = pymongo.Connection(host=settings.mongodb_host,
                        port=settings.mongodb_port)[settings.database_name]
db.members.create_index([('created', -1)])
db.topics.create_index([('last_reply_time', -1), ('node', 1)])
db.replies.create_index([('topic', 1), ('index', 1)])
db.notifications.create_index([('to', 1), ('created', 1)])
db.links.create_index([('priority', -1)])
db.histories.create_index([('target_id', 1), ('created', 1)])

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# coding=utf-8

import os
import tornado.httpserver
import tornado.ioloop
import tornado.locale
import tornado.options
import tornado.web
import urls

from tornado.options import define, options
from sentry_client import AsyncSentryClient
from init_db import db

ROOT = os.path.abspath(os.path.dirname(__file__))

define('port', default=8888, help='run on the given port', type=int)
define('settings', default=os.path.join(ROOT, 'settings.py'),
       help='path to the settings file.', type=str)


class Application(tornado.web.Application):
    def __init__(self):
        settings = {'template_path': os.path.join(ROOT, "templates"),
                    'role': {1: 'Member',
                             2: 'Admin',
                             3: 'SuperAdmin',
                             5: 'Owner'}}
        execfile(options.settings, {}, settings)

        settings['host'] = settings['forum_url'].split('/')[2]

        if 'static_path' not in settings:
            settings['static_path'] = os.path.join(ROOT, "static")

        super(Application, self).__init__(urls.handlers,
                                          ui_modules=urls.ui_modules, login_url='/account/signin',
                                          xsrf_cookies=True,
                                          **settings)

        self.db = db

        tornado.locale.load_translations(os.path.join(ROOT, "locale"))
        tornado.locale.set_default_locale(settings['default_locale'])
        supported_locales = list(tornado.locale.get_supported_locales())
        supported_locales.sort()
        locales = []
        for locale in supported_locales:
            locale = (locale, tornado.locale.LOCALE_NAMES[locale]['name'])
            locales.append(locale)
        self.locales = tuple(locales)
        
        self.sentry_client = AsyncSentryClient(settings['sentry_dsn'])


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sentry_client
import base64
import zlib

from raven.utils.json import json, BetterJSONEncoder
from raven.contrib.tornado import AsyncSentryClient as _Client
from bson.objectid import ObjectId

class PBBJSONEncoder(BetterJSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(PBBJSONEncoder, self).default(obj)


class AsyncSentryClient(_Client):
    def encode(self, data):
        """
        Serializes ``data`` into a raw string.
        """
        s = json.dumps(data, cls=PBBJSONEncoder).encode('utf8')
        return base64.b64encode(zlib.compress(s))

########NEW FILE########
__FILENAME__ = settings
# coding=utf-8

mongodb_host = '127.0.0.1'
mongodb_port = 27017
database_name = 'forum'


forum_title = 'site_name'
forum_url = 'http://xxx.com/'
sentry_dsn = ''
# forum_url MUST ends with '/'
# static_path = ''
# static_url_prefix = 'http://assets.xxx.com'

default_locale = 'zh_CN'
notifications_per_page = 10
members_per_page = 100
topics_per_page = 20
replies_per_page = topics_per_page

pushover_token = ""
gravatar_base_url = 'http://cn.gravatar.com/avatar/'
google_analytics = ''
cookie_secret = 'hey reset me!'

use_recaptcha = False  # If you use it,set to True
recaptcha_key = ''
recaptcha_secret = ''
recaptcha_theme = 'clean'

gzip = False
debug = True

########NEW FILE########
__FILENAME__ = tools
#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function
import time
import settings
from handlers.utils import username_validator
import hashlib

import pymongo

db = pymongo.Connection(host=settings.mongodb_host,
                        port=settings.mongodb_port)[settings.database_name]
db.members.create_index([('created', -1)])
db.topics.create_index([('last_reply_time', -1), ('node', 1)])
db.replies.create_index([('topic', 1), ('index', 1)])
db.notifications.create_index([('to', 1), ('created', 1)])
db.links.create_index([('priority', -1)])


if __name__ == '__main__':

    username = email = ''

    while True:
        username = raw_input('username:')
        if not username_validator.match(username):
            print("Invalid username")
            continue
        if not db.members.find_one({'name_lower': username.lower()}):
            break
        else:
            print("This username is already registered")

    while True:
        email = raw_input('email:').lower()
        if not db.members.find_one({'email': email}):
            break
        print("This email is already registered")

    password = raw_input('password:')
    password = hashlib.sha1(password + username.lower()).hexdigest()

    db.members.insert({
                      'name': username,
                      'name_lower': username.lower(),
                      'password': password,
                      'email': email,
                      'website': '',
                      'description': '',
                      'created': time.time(),
                      'role': 3,
                      'language': settings.default_locale,
                      'like': [],  # topics
                      'follow': [],  # users
                      'favorite': []  # nodes
                      })

########NEW FILE########
__FILENAME__ = urls
from handlers import account, member, node, topic, dashboard, others, api

__all__ = ['handlers', 'ui_modules']

handlers = []
handlers.extend(account.handlers)
handlers.extend(member.handlers)
handlers.extend(node.handlers)
handlers.extend(topic.handlers)
handlers.extend(dashboard.handlers)
handlers.extend(others.handlers)
handlers.extend(api.handlers)

ui_modules = {}
ui_modules.update(**node.ui_modules)
ui_modules.update(**topic.ui_modules)

########NEW FILE########
