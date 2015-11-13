__FILENAME__ = build_counter
#!/usr/bin/env python
#coding=utf=8
import config

import tornado.options
from clint.textui import progress
from macros.macro import REDIS_KEY
from utils import get_redis_client
from models import Photo, Photo_Like

def run():
    redis_client = get_redis_client()
    redis_client.delete(REDIS_KEY['USER_LIKED_COUNT'])
    redis_client.delete(REDIS_KEY['USER_LIKES_COUNT'])
    redis_client.delete(REDIS_KEY['USER_PHOTO_COUNT'])
    photos = Photo().select(['id', 'user_id', 'likes_count']).where('status', '=', 0).findall(limit=1000000)
    for photo in progress.bar(photos):
        current_liked_count = redis_client.hget(REDIS_KEY['USER_LIKED_COUNT'], photo.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_LIKED_COUNT'], photo.user_id, int(current_liked_count) + int(photo.likes_count))

        current_photo_count = redis_client.hget(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id, int(current_photo_count) + 1)

        photo_like = Photo_Like().findall_by_photo_id(photo.id)
        for item in photo_like:
            current_likes_count = redis_client.hget(REDIS_KEY['USER_LIKES_COUNT'], item.user_id) or 0
            redis_client.hset(REDIS_KEY['USER_LIKES_COUNT'], item.user_id, int(current_likes_count) + 1)

if __name__ == '__main__':
    tornado.options.parse_command_line()
    run()

########NEW FILE########
__FILENAME__ = build_db_cache
#!/usr/bin/env python
#coding=utf=8
import config

import json
import tornado.options
from clint.textui import progress
from macros.macro import REDIS_KEY
from utils import get_redis_client
from models import Photo, User

def run():
    redis_client = get_redis_client()
    for table in ('photo', 'user'):
        redis_key = REDIS_KEY['TABLE_ITEMS'].format(table = table)
        if table == 'photo':
            result = Photo().findall_by_status(0, limit = 1000000)
        elif table == 'user':
            result = User().findall(limit = 1000000)

        for item in progress.bar(result):
            redis_client.hset(redis_key, item.id, json.dumps(item.to_dict()))

if __name__ == '__main__':
    tornado.options.parse_command_line()
    run()


########NEW FILE########
__FILENAME__ = gen_invite_key
#!/usr/bin/env python
#coding=utf=8
import config

import tornado.options
import models
from utils import gen_invite_key

def run():
    hash = gen_invite_key()
    models.Invite_Key(
            user_id = 0,
            hash = hash,
            ).save()
    print '/register?invite_key=%s'%hash

if __name__ == '__main__':
    tornado.options.parse_command_line()
    run()


########NEW FILE########
__FILENAME__ = app
#coding=utf-8
from tornado.options import define, options

define('port', default = 9336, type = int, help = 'app listen port')
define('debug', default = True, type = bool, help = 'is debuging?')
define('profile', default = '/tmp/wuditoo.prof', type = str, help = 'profile')
define('photo_save_path', default = 'upload/photos', type = str, help = 'where to put user\'s photos')
define('avatar_save_path', default = 'upload/avatars', type = str, help = 'where to put avatars')
define('www_domain', default = 'lc.wuditoo.com', type = str, help = 'photo domain')
define('photo_domain', default = 'photo.lc.wuditoo.com', type = str, help = 'photo domain')
define('avatar_domain', default = 'avatar.lc.wuditoo.com', type = str, help = 'avatar domain')

options.log_file_prefix = 'log/wuditoo/web.log'
options.log_file_max_size = '50MB'
options.logging = 'debug' if options.debug else 'info'

########NEW FILE########
__FILENAME__ = database
#coding=utf-8
from tornado.options import define, options

define('db_master_url', default = 'mysql://root:123456@127.0.0.1:3306/wuditoo?charset=utf8', help = 'database master config')
define('db_slave_url', default = 'mysql://root:123456@127.0.0.1:3306/wuditoo?charset=utf8', help = 'database slave config')

def get_db_config(): 
    return {
        'master': {
            'url': options.db_master_url,
            'echo': False,
            },
        'slave': {
            'url': options.db_slave_url,
            'echo': False,
            },
    }

########NEW FILE########
__FILENAME__ = redis
#coding=utf-8
from tornado.options import define, options

define('redis_host', default = '127.0.0.1', help = 'master redis\'s host')
define('redis_port', default = 1860, type = int, help = 'master redis\'s port')
define('redis_db', default = 0, type = int, help = 'master redis\'s db')
define('redis_password', default = 'yes', help = 'master redis\'s password')

########NEW FILE########
__FILENAME__ = macro
#coding=utf-8
from collections import OrderedDict

USERS_PER_PAGE = 20

PHOTOS_PER_PAGE = 15

MAX_PAGE = 15

MAX_FOLLOW_NUM = 450

BLOG_POSTS_PER_PAGE = 10

ACTIVITY_PER_PAGE = 20

PASSWORD_SALT = '!QAZ@WSXcde3)Okm9i'

MAX_UPLOAD_SIZE = 10

MAX_AVATAR_SIZE = 2

HOT_PHOTO_INTERVAL = 300

EVENTS = {
    'USER_ACTIVATION': 'user_activation',
    'USER_CREATE': 'user_create',
    'USER_FOLLOW': 'user_follow',
    'USER_UNFOLLOW': 'user_unfollow',
    'PHOTO_LIKE': 'photo_like',
    'PHOTO_UNLIKE': 'photo_unlike',
    'PHOTO_CREATE': 'photo_create',
    'PHOTO_UPLOAD': 'photo_upload',
    'PHOTO_DELETE': 'photo_delete',
    'PHOTO_COMMENT_ADD': 'photo_comment_add',
    'PHOTO_COMMENT_DELETE': 'photo_comment_delete',
    'BLOG_ADD': 'blog.after_insert',
    'BLOG_EDIT': 'blog.after_update',
    'BLOG_DELETE': 'blog_delete',
    'BLOG_COMMENT_ADD': 'blog_comment.after_insert',
}

ACTIVITY_ACTION = {
    'PHOTO_CREATE': 100,
    'PHOTO_LIKE': 101,
    'PHOTO_UNLIKE': 103,
    'PHOTO_COMMENT_ADD': 104,
    'PHOTO_COMMENT_DELETE': 105,
    'PHOTO_DELETE': 106,
    'USER_CREATE': 200,
    'USER_ACTIVATION': 201,
    'USER_FOLLOW': 202,
    'USER_UNFOLLOW': 203,
    'BLOG_ADD': 301,
    'BLOG_EDIT': 302,
    'BLOG_DELETE': 303,
    'BLOG_COMMENT_ADD': 304,
}

AVATAR_SIZE = {
    's': '48x48^',
    'm': '100x100^',
    'l': '160x160^',
}

PHOTO_SIZE = {
    's': '70x70^',
    'm': '215x215^',
    'l': '1200x12000',
}

REDIS_KEY = {
    'USER_PHOTO_COUNT': 'h_usr_pht_cnt',
    'USER_LIKED_COUNT': 'h_usr_lkd_cnt', # 被喜欢的次数
    'USER_LIKES_COUNT': 'h_usr_lks_cnt', # 喜欢的照片的张数
    'TABLE_ITEMS': 'h_tbl_tms:{table}',
    'USER_MESSAGE': 'l_usr_msg:{user_id}',
    'HOT_TAGS': 'set_hot_tags',
}

USER_LEVEL = [0, 10, 100, 500, 1000]
USER_LEVEL_CN = [u'小兔崽', u'功夫兔', u'普京兔', u'流氓兔', u'无敌兔']
USER_LEVEL_PHOTOS_PER_WEEK = [10, 20, 30, 40, 50]

INVITE_NUM = [5, 10, 15, 20, 25]

########NEW FILE########
__FILENAME__ = activity
#coding=utf-8
import time
import logging
from blinker import signal

from helpers import get_photo_url
from macros.macro import EVENTS, ACTIVITY_ACTION
import models

photo_create = signal(EVENTS['PHOTO_CREATE'])
photo_like = signal(EVENTS['PHOTO_LIKE'])
photo_upload = signal(EVENTS['PHOTO_UPLOAD'])
photo_unlike = signal(EVENTS['PHOTO_UNLIKE'])
photo_comment_add = signal(EVENTS['PHOTO_COMMENT_ADD'])
photo_comment_delete = signal(EVENTS['PHOTO_COMMENT_DELETE'])
user_create = signal(EVENTS['USER_CREATE'])
user_follow = signal(EVENTS['USER_FOLLOW'])
user_unfollow = signal(EVENTS['USER_UNFOLLOW'])
blog_add = signal(EVENTS['BLOG_ADD'])
blog_edit = signal(EVENTS['BLOG_EDIT'])
blog_comment_add = signal(EVENTS['BLOG_COMMENT_ADD'])

class Activity(models.base.BaseThing):
    @property
    def text(self):
        user = models.User().find(self.user_id)
        text = ''
        if self.action == ACTIVITY_ACTION['PHOTO_LIKE']:
            photo = models.Photo().find(self.target_id)
            photo_url = get_photo_url(self, photo, 's')
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 喜欢照片 <a href="/photo/{photo_id}"><img src="{photo_url}" /></a>'.format(
                    user = user,
                    photo_id = photo.id,
                    photo_url = photo_url,
                    )
        if self.action == ACTIVITY_ACTION['PHOTO_UNLIKE']:
            photo = models.Photo().find(self.target_id)
            photo_url = get_photo_url(self, photo, 's')
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 不喜欢照片 <a href="/photo/{photo_id}"><img src="{photo_url}" /></a>'.format(
                    user = user,
                    photo_id = photo.id,
                    photo_url = photo_url,
                    )
        elif self.action == ACTIVITY_ACTION['PHOTO_COMMENT_ADD']:
            photo = models.Photo().find(self.context_id)
            photo_url = get_photo_url(self, photo, 's')
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 评论了照片 <a href="/photo/{photo_id}"><img src="{photo_url}" /></a>'.format(
                    user = user,
                    photo_id = photo.id,
                    photo_url = photo_url,
                    )
        elif self.action == ACTIVITY_ACTION['BLOG_COMMENT_ADD']:
            post = models.Blog().find(self.context_id)
            title = u'评论了博文'
            url = '/blog/post/{post.id}'
            if post.status == 1:
                title = u'评论了反馈'
                url = '/feedback'
            text = u'<a href="/user/{user.username}">{user.fullname}</a> {title} <a href="{url}">{post.title}</a> 中的评论'.format(
                    user = user,
                    title = title,
                    post = post,
                    url = url,
                    )
        elif self.action == ACTIVITY_ACTION['USER_FOLLOW']:
            dest_user = models.User().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 关注了 <a href="/user/{user.username}">{dest_user.fullname}</a>'.format(user = user, dest_user = dest_user)
        elif self.action == ACTIVITY_ACTION['USER_UNFOLLOW']:
            dest_user = models.User().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 取消关注了 <a href="/user/{user.username}">{dest_user.fullname}</a>'.format(user = user, dest_user = dest_user)
        elif self.action == ACTIVITY_ACTION['USER_CREATE']:
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 创建了账号'
        elif self.action == ACTIVITY_ACTION['PHOTO_CREATE']:
            photo = models.Photo().find(self.target_id)
            photo_url = get_photo_url(self, photo, 's')
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 发布了照片 <a href="/photo/{photo.id}"><img src="{photo_url}" /></a>'.format(user = user, photo = photo, photo_url = photo_url)
        elif self.action == ACTIVITY_ACTION['BLOG_EDIT']:
            post = models.Blog().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 编辑了博文 <a href="/blog/post/{post.id}">{post.title}</a>'.format(user = user, post = post)
        elif self.action == ACTIVITY_ACTION['BLOG_ADD']:
            post = models.Blog().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 发布了博文 <a href="/blog/post/{post.id}">{post.title}</a>'.format(user = user, post = post)
        elif self.action == ACTIVITY_ACTION['BLOG_DELETE']:
            post = models.Blog().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 删除了博文 <a href="/blog/post/{post.id}">{post.title}</a>'.format(user = user, post = post)
        return text

    @property
    def feed_text(self):
        user = models.User().find(self.user_id)
        text = ''
        if self.action == ACTIVITY_ACTION['PHOTO_CREATE']:
            text = u'{user} 添加了这张照片'.format(user = user.fullname)
        elif self.action == ACTIVITY_ACTION['PHOTO_LIKE']:
            text = u'{user} 喜欢这张照片'.format(user = user.fullname)
        elif self.action == ACTIVITY_ACTION['PHOTO_COMMENT_ADD']:
            text = u'{user} 评论了这张照片'.format(user = user.fullname)
        return text

    def get_feed(self, user_ids, limit = 15, offset = 0):
        return self.where('user_id', 'in', user_ids)\
                   .where('action', 'in', [
                       ACTIVITY_ACTION['PHOTO_CREATE'],
                       ACTIVITY_ACTION['PHOTO_LIKE'],
                       ACTIVITY_ACTION['PHOTO_COMMENT_ADD'],
                       ])\
                   .findall(limit = limit, offset = offset)

    def get_feed_count(self, user_ids):
        return self.where('user_id', 'in', user_ids)\
                   .where('action', 'in', [ACTIVITY_ACTION['PHOTO_CREATE'], ACTIVITY_ACTION['PHOTO_LIKE']])\
                   .count()

    @photo_create.connect
    def _photo_create(photo):
        Activity(
            user_id = photo.user_id,
            action = ACTIVITY_ACTION['PHOTO_CREATE'],
            created = photo.created,
            target_id = photo.id,
            ).save()

    @photo_like.connect
    def _photo_like(photo_like):
        Activity(
            user_id = photo_like.user_id,
            action = ACTIVITY_ACTION['PHOTO_LIKE'],
            created = time.time(),
            target_id = photo_like.photo_id,
            ).save()

    @photo_unlike.connect
    def _photo_unlike(photo_like):
        Activity(
            user_id = photo_like.user_id,
            action = ACTIVITY_ACTION['PHOTO_UNLIKE'],
            created = time.time(),
            target_id = photo_like.photo_id,
            ).save()

    @photo_upload.connect
    def _photo_upload(photo):
        Activity(
            user_id = photo.user_id,
            action = ACTIVITY_ACTION['PHOTO_UPLOAD'],
            created = photo.created,
            target_id = photo.id,
            ).save()

    @user_create.connect
    def _user_create(user, **kwargs):
        Activity(
            user_id = user.id,
            action = ACTIVITY_ACTION['USER_CREATE'],
            created = user.created,
            ).save()

    @user_follow.connect
    def _user_follow(user):
        Activity(
            user_id = user.follower_user_id,
            action = ACTIVITY_ACTION['USER_FOLLOW'],
            target_id = user.followed_user_id,
            created = time.time(),
            ).save()

    @user_unfollow.connect
    def _user_unfollow(user):
        Activity(
            user_id = user.follower_user_id,
            action = ACTIVITY_ACTION['USER_UNFOLLOW'],
            target_id = user.followed_user_id,
            created = time.time(),
            ).save()

    @photo_comment_add.connect
    def _photo_comment_add(photo_comment):
        activity = Activity(
                user_id = photo_comment.user_id,
                action = ACTIVITY_ACTION['PHOTO_COMMENT_ADD'],
                target_id = photo_comment.id,
                created = photo_comment.created,
                context_id = photo_comment.photo_id,
                ).save()

    @blog_add.connect
    def _blog_add(blog):
        activity = Activity(
                user_id = blog.user_id,
                action = ACTIVITY_ACTION['BLOG_ADD'],
                target_id = blog.id,
                created = blog.created,
                ).save()

    @blog_edit.connect
    def _blog_edit(blog):
        action = ACTIVITY_ACTION['BLOG_EDIT'] if blog.status == 0 else ACTIVITY_ACTION['BLOG_DELETE']
        activity = Activity(
                user_id = blog.user_id,
                action = action,
                target_id = blog.id,
                created = time.time(),
                ).save()

    @blog_comment_add.connect
    def _blog_comment_add(comment):
        activity = Activity(
                user_id = comment.user_id,
                action = ACTIVITY_ACTION['BLOG_COMMENT_ADD'],
                target_id = comment.id,
                created = comment.created,
                context_id = comment.blog_id,
                ).save()

########NEW FILE########
__FILENAME__ = base
import logging

import thing
import json
from config.database import get_db_config
from tornado.options import define, options
from macros.macro import REDIS_KEY
from utils import get_redis_client, attr_dict

thing.Thing.db_config(get_db_config())

class BaseThing(thing.Thing):
    def set_attr_by_req(self, arguments, *args):
        for item in args:
            setattr(self, item, arguments.get(item, [''])[0])

    def _after_insert(self):
        if self.table in ('user', 'photo'):
            redis_key = REDIS_KEY['TABLE_ITEMS'].format(table = self.table)
            redis_client = get_redis_client()
            redis_client.hset(redis_key, getattr(self, self._primary_key), json.dumps(self.to_dict()))

    def _after_update(self):
        self._after_insert()

    def _before_find(self, primary_key_value):
        if primary_key_value and self.table in ('user', 'photo'):
            redis_key = REDIS_KEY['TABLE_ITEMS'].format(table = self.table)
            redis_client = get_redis_client()
            result = redis_client.hget(redis_key, primary_key_value)
            return attr_dict(json.loads(result)) if result else None

########NEW FILE########
__FILENAME__ = blog
#coding=utf-8

from blinker import signal
import models
from macros.macro import EVENTS

blog_comment_add = signal(EVENTS['BLOG_COMMENT_ADD'])

class Blog(models.base.BaseThing):

    @property
    def creator(self):
        return models.user.User().find(self.user_id)

    @blog_comment_add.connect
    def _blog_comment_add(comment):
        blog = Blog().find(comment.blog_id)
        blog.comment_count += 1
        blog.save()

########NEW FILE########
__FILENAME__ = blog_comment
#coding=utf-8

import models

class Blog_Comment(models.base.BaseThing):
    @property
    def creator(self):
        return models.user.User().find(self.user_id)

########NEW FILE########
__FILENAME__ = followship
#coding=utf-8
import logging
from blinker import signal

from macros.macro import EVENTS
import models

class FollowShip(models.base.BaseThing):
    def follow(self, user_id, dest_user_id):
        if not self.count_by_follower_user_id_and_followed_user_id(user_id, dest_user_id):
            self.follower_user_id = user_id
            self.followed_user_id = dest_user_id
            self.save()
            signal(EVENTS['USER_FOLLOW']).send(self)
            return self.saved
        return False

    def unfollow(self, user_id, dest_user_id):
        if self.count_by_follower_user_id_and_followed_user_id(user_id, dest_user_id):
            result = self.where('follower_user_id', '=', user_id)\
                         .where('followed_user_id', '=', dest_user_id)\
                         .find()
            delete = result.delete()
            signal(EVENTS['USER_UNFOLLOW']).send(self)
            return delete
        return False

########NEW FILE########
__FILENAME__ = invite_key
#coding=utf-8
import logging
from blinker import signal
import models
from macros.macro import EVENTS, INVITE_NUM
from utils import gen_invite_key

user_create = signal(EVENTS['USER_CREATE'])

class Invite_Key(models.base.BaseThing):
    @user_create.connect
    def _user_create(user, **kwargs):
        invite_key = Invite_Key().find_by_hash(kwargs['invite_key_hash'])
        invite_key.dest_user_id = user.id
        invite_key.used = 1
        invite_key.save()

        for i in range(INVITE_NUM[0]):
            Invite_Key(
                    user_id = user.id,
                    hash = gen_invite_key(),
                    ).save()

    def gen_by_level(self, user, level_current, level_prev):
        delta_key_num = INVITE_NUM[level_current] - INVITE_NUM[level_prev]
        for i in range(delta_key_num):
            Invite_Key(
                    user_id = user.id,
                    hash = gen_invite_key(),
                    ).save()

    @property
    def consumer(self):
        return models.User().find(self.dest_user_id)

########NEW FILE########
__FILENAME__ = notification
#coding=utf-8
import time
import logging
import re
from blinker import signal

from macros.macro import EVENTS, ACTIVITY_ACTION
import models

photo_like = signal(EVENTS['PHOTO_LIKE'])
photo_comment_add = signal(EVENTS['PHOTO_COMMENT_ADD'])
blog_comment_add = signal(EVENTS['BLOG_COMMENT_ADD'])
user_follow = signal(EVENTS['USER_FOLLOW'])

class Notification(models.base.BaseThing):

    def save(self):
        #TODO add notification support
        return False

    @property
    def text(self):
        user = models.User().find(self.operator_id)
        text = ''
        if self.action == ACTIVITY_ACTION['PHOTO_LIKE']:
            photo = models.Photo().find(self.target_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 喜欢照片 <a href="/photo/{photo_id}">{photo_title}</a>'.format(
                    user = user,
                    photo_id = photo.id,
                    photo_title = photo.title or u"无标题",
                    )
        elif self.action == ACTIVITY_ACTION['PHOTO_COMMENT_ADD']:
            photo = models.Photo().find(self.context_id)
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 评论了照片 <a href="/photo/{photo_id}">{photo_title}</a>'.format(
                    user = user,
                    photo_id = photo.id,
                    photo_title = photo.title or u"无标题",
                    )
        elif self.action == ACTIVITY_ACTION['BLOG_COMMENT_ADD']:
            post = models.Blog().find(self.context_id)
            title = u'评论了你在博文'
            url = '/blog/post/{post.id}'
            if post.status == 1:
                title = u'评论了你在反馈'
                url = '/feedback'
            text = u'<a href="/user/{user.username}">{user.fullname}</a> {title} <a href="{url}">{post.title}</a> 中的评论'.format(
                    user = user,
                    title = title,
                    post = post,
                    url = url,
                    )
        elif self.action == ACTIVITY_ACTION['USER_FOLLOW']:
            text = u'<a href="/user/{user.username}">{user.fullname}</a> 关注了你'.format(user = user)

        return text

    @photo_like.connect
    def _photo_like(photo_like):
        receiver_id = models.Photo().find(photo_like.photo_id).user_id
        current_notification = Notification().where('receiver_id', '=', receiver_id)\
                               .where('operator_id', '=', photo_like.user_id)\
                               .where('action', '=', ACTIVITY_ACTION['PHOTO_LIKE'])\
                               .find()
        if not current_notification:
            Notification(
                operator_id = photo_like.user_id,
                receiver_id = receiver_id,
                action = ACTIVITY_ACTION['PHOTO_LIKE'],
                created = time.time(),
                target_id = photo_like.photo_id,
                is_new = 1,
                ).save()
        else:
            current_notification.is_new = 1
            current_notification.created = time.time()
            current_notification.save()

    @photo_comment_add.connect
    def _photo_comment_add(photo_comment):
        receiver_ids = set([models.Photo().find(photo_comment.photo_id).user_id])
        mention_users = re.findall(r'@[^\(]+\((.*?)\)', photo_comment.content)
        if mention_users:
            for username in mention_users:
                user_id = models.User().find_by_username(username).id
            receiver_ids.add(user_id)
        for receiver_id in receiver_ids:
            if photo_comment.user_id != receiver_id:
                Notification(
                    operator_id = photo_comment.user_id,
                    receiver_id = receiver_id,
                    action = ACTIVITY_ACTION['PHOTO_COMMENT_ADD'],
                    created = photo_comment.created,
                    target_id = photo_comment.id,
                    context_id = photo_comment.photo_id,
                    is_new = 1,
                    ).save()

    @user_follow.connect
    def _user_follow(user):
        current_notification = Notification().where('receiver_id', '=', user.followed_user_id)\
                               .where('operator_id', '=', user.follower_user_id)\
                               .where('action', '=', ACTIVITY_ACTION['USER_FOLLOW'])\
                               .find()
        if not current_notification:
            Notification(
                operator_id = user.follower_user_id,
                receiver_id = user.followed_user_id,
                action = ACTIVITY_ACTION['USER_FOLLOW'],
                created = time.time(),
                is_new = 1,
                ).save()
        else:
            current_notification.is_new = 1
            current_notification.created = time.time()
            current_notification.save()

    @blog_comment_add.connect
    def _blog_comment_add(blog_comment):
        receiver_ids = set([models.Blog().find(blog_comment.blog_id).user_id])
        mention_users = re.findall(r'@[^\(]+\((.*?)\)', blog_comment.content)
        if mention_users:
            for username in mention_users:
                user_id = models.User().find_by_username(username).id
            receiver_ids.add(user_id)
        for receiver_id in receiver_ids:
            if blog_comment.user_id != receiver_id:
                Notification(
                    operator_id = blog_comment.user_id,
                    receiver_id = receiver_id,
                    action = ACTIVITY_ACTION['BLOG_COMMENT_ADD'],
                    created = blog_comment.created,
                    target_id = blog_comment.id,
                    context_id = blog_comment.blog_id,
                    is_new = 1,
                    ).save()

########NEW FILE########
__FILENAME__ = photo
#coding=utf-8
import time
import datetime
import logging
from blinker import signal
from formencode import validators

from macros.macro import EVENTS, REDIS_KEY
import models
from utils import get_redis_client, calculate_photo_karma, process_photo_url

photo_like = signal(EVENTS['PHOTO_LIKE'])
photo_unlike = signal(EVENTS['PHOTO_UNLIKE'])
photo_delete = signal(EVENTS['PHOTO_DELETE'])
photo_comment_delete = signal(EVENTS['PHOTO_COMMENT_DELETE'])
photo_comment_add = signal(EVENTS['PHOTO_COMMENT_ADD'])
photo_after_validation = signal('photo.after_validation')

class Photo(models.base.BaseThing):
    _photo_soure_error = {'empty': u'照片地址不能为空', 'badURL': u'链接格式不正确', 'noTLD': u'链接格式不正确'}
    _page_soure_error = {'empty': u'页面址不能为空', 'badURL': u'链接格式不正确', 'noTLD': u'链接格式不正确'}

    title = validators.String(
            not_empty = True,
            strip = True,
            messages = {
                'empty': u'别忘了填写标题哦',
                }
            )

    photo_source = validators.URL(
            strip = True,
            add_http = True,
            not_empty = True,
            messages = _photo_soure_error)

    page_source = validators.URL(
            strip = True,
            add_http = True,
            not_empty = True,
            messages = _page_soure_error)

    @property
    def comments(self):
        return models.Photo_Comment().findall_by_photo_id_and_status(self.id, 0)

    def create(self):
        self.status = 0
        self.created = self.updated = time.time()
        self.karma = calculate_photo_karma(0, self.created)
        self.save()
        if self.saved:
            signal(EVENTS['PHOTO_CREATE']).send(self)
            return self.id

    def delete(self):
        self.status = -1
        self.save()
        signal(EVENTS['PHOTO_DELETE']).send(self)

    def get_hot(self, limit, offset):
        return Photo().order_by('-karma').findall_by_status(0, limit = limit, offset = offset)

    def get_hot_count(self):
        return Photo().count_by_status(0)

    @property
    def creator(self):
        return models.User().find(self.user_id)

    @photo_after_validation.connect
    def _photo_after_validation(photo):
        if not photo.id:
            hashval = process_photo_url(photo.photo_source, photo.user_id)
            if not hashval:
                photo.add_error(photo_source = u'此链接无法被抓取')
            else:
                photo.hash = hashval

    @photo_like.connect
    def _photo_like(photo_like):
        photo = Photo().find(photo_like.photo_id)
        photo.likes_count += 1
        photo.karma = calculate_photo_karma(photo.likes_count, photo.created)
        photo.save()

    @photo_unlike.connect
    def _photo_unlike(photo_like):
        photo = Photo().find(photo_like.photo_id)
        photo.likes_count -= 1
        photo.karma = calculate_photo_karma(photo.likes_count, photo.created)
        photo.save()

    @photo_comment_delete.connect
    def _photo_comment_delete(comment):
        photo = Photo().find(comment.photo_id)
        photo.comments_count -= 1
        photo.save()

    @photo_comment_add.connect
    def _photo_comment_add(comment):
        photo = Photo().find(comment.photo_id)
        photo.comments_count += 1
        photo.save()


########NEW FILE########
__FILENAME__ = photo_comment
#coding=utf-8
import logging
import time
import models
from blinker import signal
from macros.macro import EVENTS

class Photo_Comment(models.base.BaseThing):
    @property
    def creator(self):
        return models.user.User().find(self.user_id)

    def delete(self):
        self.status = -1
        self.save()
        signal(EVENTS['PHOTO_COMMENT_DELETE']).send(self)

    def create(self):
        self.updated = self.created = time.time()
        self.status = 0
        self.save()
        signal(EVENTS['PHOTO_COMMENT_ADD']).send(self)

########NEW FILE########
__FILENAME__ = photo_exif
#coding=utf-8
import logging
from collections import OrderedDict
import models

class Photo_Exif(models.base.BaseThing):
    def get(self, photo_id):
        self.reset()
        meta_dict = OrderedDict()
        meta = self.where('photo_id', '=', photo_id).order_by('id').findall()
        for item in meta:
            meta_dict[item.key] = item.value
        return meta_dict

########NEW FILE########
__FILENAME__ = photo_like
#coding=utf-8
import time
from blinker import signal

from macros.macro import EVENTS
import models

photo_delete = signal(EVENTS['PHOTO_DELETE'])

class Photo_Like(models.base.BaseThing):
    def like(self, user_id, photo_id):
        liked = self.where('user_id', '=', user_id)\
                    .where('photo_id', '=', photo_id)\
                    .find()
        if not liked:
            self.reset()
            self.user_id = user_id
            self.photo_id = photo_id
            self.save()
            signal(EVENTS['PHOTO_LIKE']).send(self)
            return self.saved
        return False

    def unlike(self, user_id, photo_id):
        liked = self.where('user_id', '=', user_id)\
                    .where('photo_id', '=', photo_id)\
                    .find()
        if liked:
            signal(EVENTS['PHOTO_UNLIKE']).send(self)
            self.reset()
            rowcount = self.where('user_id', '=', user_id)\
                .where('photo_id', '=', photo_id)\
                .delete()
            return rowcount
        return False

    @photo_delete.connect
    def _photo_delete(photo):
        Photo_Like().where('photo_id', '=', photo.id).delete()

########NEW FILE########
__FILENAME__ = photo_tag
#coding=utf-8
import logging
import models
from utils import get_redis_client
from macros.macro import REDIS_KEY, EVENTS
from blinker import signal

photo_delete = signal(EVENTS['PHOTO_DELETE'])

class Photo_Tag(models.base.BaseThing):
    @property
    def hot_tags(self):
        redis_key = REDIS_KEY['HOT_TAGS']
        redis_client = get_redis_client()
        if not redis_client.scard(redis_key):
            hot_tags = self.query(
                    '''
                    SELECT tag, count(id) 
                    FROM photo_tag 
                    GROUP BY tag 
                    ORDER BY count(id) DESC
                    LIMIT 100
                    '''
                    ).fetchall()
            for item in hot_tags:
                redis_client.sadd(redis_key, item.tag)
            # expires 1 hour later
            redis_client.expire(redis_key, 3600)
        
        tags = []
        if redis_client.smembers(redis_key):
            length = min(10, redis_client.scard(redis_key))
            for i in range(length):
                tag = redis_client.spop(redis_key)
                tags.append(tag)
            for i in range(length):
                redis_client.sadd(redis_key, tags[i])
        return tags

    @photo_delete.connect
    def _photo_delete(photo):
        Photo_Tag().where('photo_id', '=', photo.id).delete()

########NEW FILE########
__FILENAME__ = profile
#coding=utf-8
import time
import logging
from blinker import signal
import formencode
from formencode import validators

import models
from macros.macro import EVENTS

user_create = signal(EVENTS['USER_CREATE'])

class Profile(models.base.BaseThing):
    _invalid_link = {'badURL': u'链接格式不正确',
                   'noTLD': u'链接格式不正确'}

    link_weibo = validators.URL(
            strip = True,
            add_http = True,
            not_empty = False,
            messages = _invalid_link)

    link_qq = validators.URL(
            strip = True,
            add_http = True,
            not_empty = False,
            messages = _invalid_link)

    link_douban = validators.URL(
            strip = True,
            add_http = True,
            not_empty = False,
            messages = _invalid_link)

    link_flickr = validators.URL(
            strip = True,
            add_http = True,
            not_empty = False,
            messages = _invalid_link)

    link_blog = validators.URL(
            strip = True,
            add_http = True,
            not_empty = False,
            messages = _invalid_link)

    @user_create.connect
    def _user_create(user, **kwargs):
        Profile(
            user_id = user.id,
            link_weibo = '',
            link_qq = '',
            link_douban = '',
            link_flickr = '',
            link_blog = '',
        ).save()

########NEW FILE########
__FILENAME__ = user
#coding=utf-8
import thing
import time
import datetime
import logging
import formencode
from formencode import validators
from blinker import signal

from utils import (hash_password,
                   get_redis_client,
                   cached_property,
                   calculate_user_level)
import models
from macros.macro import (PASSWORD_SALT,
                          EVENTS,
                          REDIS_KEY,
                          USER_LEVEL_CN,
                          USER_LEVEL_PHOTOS_PER_WEEK)

photo_like = signal(EVENTS['PHOTO_LIKE'])
photo_delete = signal(EVENTS['PHOTO_DELETE'])
photo_unlike = signal(EVENTS['PHOTO_UNLIKE'])
photo_create = signal(EVENTS['PHOTO_CREATE'])

class User(models.base.BaseThing):
    email = validators.Email(
            not_empty = True,
            strip = True,
            messages = {'noAt': u'这可不是一个正常的邮箱哦',
                        'empty': u'忘了填邮箱啦'})

    username = formencode.All(
            validators.String(
                 not_empty = True,
                 strip = True,
                 min = 4,
                 max = 24,
                 messages = {
                     'empty': u'用户名总得有一个吧',
                     'tooLong': u'这么长的用户名没有必要吧',
                     'tooShort': u'用户名长度不能少于4'}),
             validators.PlainText(messages = {
                     'invalid': u'用户名只能包含数字，字母和下划线'
                  }))

    fullname = validators.String(
                 not_empty = True,
                 strip = True,
                 max = 12,
                 messages = {
                     'empty': u'总得有个昵称吧',
                     'tooLong': u'这么长的昵称没有必要吧',
                     }
                 )

    password = validators.String(not_empty = True,
                                 messages = {'empty': u'忘记设置密码了'})

    def create(self):
        self.fullname = self.username
        self.created = time.time()

        if self.validate():
            if User().find_by_username(self.username):
                self.errors = {'username': u'此用户名已被占用'}
                return
            if User().find_by_email(self.email):
                self.errors = {'email': u'此Email已被注册'}
                return
            if not self.password_confirm:
                self.errors = {'password_confirm': u'确认密码不能为空'}
                return
            if self.password != self.password_confirm:
                self.errors = {'password': u'两次密码输入不一致'}
                return

            invite_key = models.Invite_Key().find_by_hash(self.invite_key)
            if not invite_key:
                self.errors = {'invite_key': u'该邀请码不存在'}
                return
            if invite_key.used:
                self.errors = {'invite_key': u'该邀请码已被使用'}
                return

            del self.password_confirm
            del self.invite_key
            self.password = hash_password(self.password)
            user_id = self.save()
            signal(EVENTS['USER_CREATE']).send(self, invite_key_hash = invite_key.hash)
            return user_id

    def change_password(self, origin_password, password, password_confirm):
        if not origin_password:
            self.add_error(origin_password = u'当前密码不能为空')
        if not password:
            self.add_error(password = u'新密码不能为空')
        if not password_confirm:
            self.add_error(password_confirm = u'确认密码不能为空')
        
        if password != password_confirm:
            self.add_error(password_confirm = u'两次密码输入不一致')

        if self.errors:
            return False

        if hash_password(origin_password) != self.password:
            self.add_error(origin_password = u'当前密码不正确')
            return False

        self.password = hash_password(password)
        self.save()
        return self.saved

    def is_following(self, dest_user_id):
        return models.FollowShip().count_by_follower_user_id_and_followed_user_id(self.id, dest_user_id)

    def has_liked_photo(self, photo):
        return models.Photo_Like().count_by_user_id_and_photo_id(self.id, photo.id)

    @property
    def is_admin(self):
        return self.id == 1

    @property
    def photo_count(self):
        return get_redis_client().hget(REDIS_KEY['USER_PHOTO_COUNT'], self.id) or 0

    @property
    def liked_count(self):
        return get_redis_client().hget(REDIS_KEY['USER_LIKED_COUNT'], self.id) or 0

    @property
    def likes_count(self):
        return get_redis_client().hget(REDIS_KEY['USER_LIKES_COUNT'], self.id) or 0

    @property
    def following_count(self):
        return models.FollowShip().count_by_follower_user_id(self.id)

    @property
    def follower_count(self):
        return models.FollowShip().count_by_followed_user_id(self.id)

    @property
    def unused_invite_key_count(self):
        return models.Invite_Key().count_by_user_id_and_used(self.id, 0)

    @property
    def profile(self):
        if not getattr(self, '_profile'):
            profile = models.Profile().find_by_user_id(self.id)
            self._profile = profile
        return self._profile

    @property
    def left_upload_count(self):
        if self.is_admin:
            return 100
        init_count = USER_LEVEL_PHOTOS_PER_WEEK[self.level]
        now = datetime.datetime.now()
        dt = now - datetime.timedelta(days = datetime.datetime.weekday(now))
        start_week_timestamp = time.mktime(datetime.datetime.date(dt).timetuple())
        created_count = models.Photo().where('created', '>', start_week_timestamp)\
               .where('status', '=', 0)\
               .where('user_id', '=', self.id)\
               .count()
        return init_count - created_count

    @photo_like.connect
    def _photo_like(photo_like):
        """
        re calculate user level here
        """
        user = models.User().find(models.Photo().find(photo_like.photo_id).user_id)

        redis_client = get_redis_client()
        redis_client.hincrby(REDIS_KEY['USER_LIKED_COUNT'], user.id, 1)

        current_likes_count = redis_client.hget(REDIS_KEY['USER_LIKES_COUNT'], photo_like.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_LIKES_COUNT'], photo_like.user_id, int(current_likes_count) + 1)

        calculated_user_level = calculate_user_level(user)
        if calculated_user_level > user.level:
            redis_key = REDIS_KEY['USER_MESSAGE'].format(user_id = user.id)
            models.Invite_Key().gen_by_level(user, calculated_user_level, user.level)
            msg = u"{0}|恭喜你，成功升级到{1}".format('info', USER_LEVEL_CN[calculated_user_level])
            redis_client.lpush(redis_key, msg)
            user.level = calculated_user_level
            user.save()

    @photo_unlike.connect
    def _photo_unlike(photo_like):
        """
        re calculate user level here
        """
        user = models.User().find(models.Photo().find(photo_like.photo_id).user_id)

        redis_client = get_redis_client()
        redis_client.hincrby(REDIS_KEY['USER_LIKED_COUNT'], user.id, -1)

        current_likes_count = redis_client.hget(REDIS_KEY['USER_LIKES_COUNT'], photo_like.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_LIKES_COUNT'], photo_like.user_id, int(current_likes_count) - 1)

    @photo_create.connect
    def _photo_create(photo):
        redis_client = get_redis_client()
        current_photo_count = redis_client.hget(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id, int(current_photo_count) + 1)

    @photo_delete.connect
    def _photo_delete(photo):
        redis_client = get_redis_client()
        current_photo_count = redis_client.hget(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id) or 0
        redis_client.hset(REDIS_KEY['USER_PHOTO_COUNT'], photo.user_id, int(current_photo_count) - 1)

########NEW FILE########
__FILENAME__ = user_meta
#coding=utf-8
import logging
import uuid
from blinker import signal

import models

class User_Meta(models.base.BaseThing):
    pass

########NEW FILE########
__FILENAME__ = app
#coding=utf-8
import logging
import cProfile as profile
import tornado.ioloop
import tornado.web
import tornado.options
from tornado.options import define, options
import config
tornado.options.parse_command_line()

import helpers
import routes

def create_app():
    settings = {
        'login_url': '/login',
        'static_path': 'src/sites/www/static',
        'template_path': 'src/sites/www/templates',
        'cookie_secret': '16oETzKXQAGaYdkL6gEmGeJJFuYh7EQnp2XdTP1o/Vo=',
        'xsrf_cookies': False,
        'ui_methods': helpers,
        'debug': options.debug,
        #'autoescape': None,
    }
    return tornado.web.Application(routes.handlers, **settings)

def profile_patch():
    def wrapper(old_execute):
        def _(self, transforms, *args, **kwargs):
            if options.profile and self.get_argument('profile', 0):
                self.profiling = True
                self.profiler = profile.Profile()
                result = self.profiler.runcall(old_execute, self, transforms, *args, **kwargs)
                self.profiler.dump_stats(options.profile)
                return result
            else:
                self.profiling = False
                return old_execute(self, transforms, *args, **kwargs)
        return _

    old_execute = tornado.web.RequestHandler._execute
    tornado.web.RequestHandler._execute = wrapper(old_execute)

if __name__ == "__main__":
    profile_patch()
    app = create_app()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


########NEW FILE########
__FILENAME__ = auth
#coding=utf-8
import time
import logging
import tornado
from tornado.options import options
from base import BaseHandler
from utils import set_message, hash_password
import models

class RegisterHandler(BaseHandler):
    def get(self):
        invite_key = self.get_argument('invite_key', '')
        if not invite_key:
            return self.render('error/invite_key_missing.html')
        invite_key_info = models.Invite_Key().find_by_hash(invite_key)

        if not invite_key_info:
            return self.render('error/invite_key_invalid.html')
        if invite_key_info.used:
            return self.render('error/invite_key_used.html')
        return self.render('register.html', invite_key = invite_key)

    def post(self):
        user = models.User(
                username = self.get_argument('username', ''),
                email = self.get_argument('email', ''),
                password = self.get_argument('password', ''),
                password_confirm = self.get_argument('password_confirm', ''),
                invite_key = self.get_argument('invite_key', ''),
                )
        user_id = user.create()

        if not user_id:
            return self.send_error_json(user.errors)

        set_message(self, u'注册成功，有好的摄影作品别忘了来这里分享哦', 'info')
        self.set_secure_cookie('o_O', u'{0}'.format(user_id), domain='.{0}'.format(options.www_domain))
        return self.send_success_json(location = '/')

class LoginHandler(BaseHandler):
    def get(self):
        return self.render('login.html')

    def post(self):
        username = self.get_argument('username', '')
        password = self.get_argument('password', '')
        if not username:
            return self.redirect(u'/login?error={0}'.format(u"用户名不能为空"))
        if not password:
            return self.redirect(u'/login?error={0}'.format(u"密码不能为空"))

        if username.find('@') != -1:
            user = models.User().find_by_email(username)
        else:
            user = models.User().find_by_username(username)

        if user:
            if user.password != hash_password(password):
                return self.redirect(u'/login?error={0}'.format(u"用户名与密码不符"))
        else:
            return self.redirect(u'/login?error={0}'.format(u"该用户不存在"))

        self.set_secure_cookie('o_O', u'{0}'.format(user.id), domain='.{0}'.format(options.www_domain))
        return_url = self.get_argument('return', '/')
        self.redirect(return_url)

class LogoutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie('o_O', domain='.{0}'.format(options.www_domain))
        return self.redirect('/')

########NEW FILE########
__FILENAME__ = base
#coding=utf-8
import logging
from tornado.options import options
import tornado.web
import thing
import models
from macros.macro import PHOTOS_PER_PAGE, USERS_PER_PAGE
from utils import keep_order

class BaseHandler(tornado.web.RequestHandler):

    def send_error_json(self, data):
        return self.write({
            'status': 'error',
            'content': data
            })

    def send_success_json(self, **data):
        return self.write({
            'status': 'ok',
            'content': data
            })

    def get_current_user(self):
        user_id = self.get_secure_cookie('o_O')
        if not user_id:
            return None

        return models.User().find(user_id)

    @property
    def notification_count(self):
        return models.Notification().count_by_receiver_id_and_is_new(self.current_user.id, 1)

    @property
    def is_admin(self):
        return self.current_user and self.current_user.is_admin

    @property
    def is_ajax_request(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

class BasePhotosHandler(BaseHandler):
    def _render(self, kind, photo = None, tag_name = None):
        template_prefix = 'partial/' if self.is_ajax_request else ''
        offset = (int(self.get_argument('page', 1)) - 1) * PHOTOS_PER_PAGE

        if kind == 'hot':
            page_path = '/photos/hot'
            photos_title = u'热门照片'
            photos_type = 'hot'
            photos = (models.Photo().order_by('-karma')
                      .findall_by_status(0, limit = PHOTOS_PER_PAGE, offset = offset))
            total_items = models.Photo().count_by_status(0)
        if kind == 'latest':
            page_path = '/photos/latest'
            photos_title = u'最新照片'
            photos_type = 'latest'
            photos = models.Photo().findall_by_status(0, limit = PHOTOS_PER_PAGE, offset = offset)
            total_items = models.Photo().count_by_status(0)
        elif kind == 'mine_upload':
            page_path = '/mine/photos'
            photos_title = u'我添加的照片'
            photos_type = 'user'
            photos = models.Photo().findall_by_user_id_and_status(
                self.current_user.id, 0, limit = PHOTOS_PER_PAGE, offset = offset)
            total_items = models.Photo().count_by_user_id_and_status(self.current_user.id, 0)
        elif kind == 'mine_likes':
            page_path = '/mine/likes_photos'
            photos_title = u'我喜欢的照片'
            photos_type = 'user'
            photo_ids = models.Photo_Like().findall_by_user_id(
                        self.current_user.id, limit = PHOTOS_PER_PAGE, offset = offset)\
                        .get_field('photo_id')
            photos = []
            for photo_id in photo_ids:
                photos.append(models.Photo().find(photo_id))

            total_items = models.Photo_Like().count_by_user_id(self.current_user.id)
        elif kind == 'tag':
            page_path = u'/tag/{0}'.format(tag_name)
            photos_title = u'带有"{0}"标签的照片'.format(tag_name)
            photos_type = u'tag/{0}'.format(tag_name)
            photo_ids = models.Photo_Tag().findall_by_tag(
                        tag_name, limit = PHOTOS_PER_PAGE, offset = offset)\
                        .get_field('photo_id')
            photos = []
            for photo_id in photo_ids:
                photos.append(models.Photo().find(photo_id))

            total_items = models.Photo_Tag().count_by_tag(tag_name)

        return self.render('{0}photos.html'.format(template_prefix),
                photos_title = photos_title,
                photos_type = photos_type,
                photos = photos,
                total_items = total_items,
                page_path = page_path,
                current_photo = photo,
                )

class BaseUserPhotosHandler(BaseHandler):
    def _render(self, kind, photo = None):
        template_prefix = 'partial/' if self.is_ajax_request else 'user_'
        offset = (int(self.get_argument('page', 1)) - 1) * PHOTOS_PER_PAGE

        fullname = self.user.fullname
        if self.current_user and self.user.id == self.current_user.id:
            fullname = u'我'

        if kind == 'photos':
            page_path = '/user/{0}/photos'.format(self.user.username)
            photos_title = u'{0}的照片'.format(fullname)
            photos_type = 'user'
            photos = models.Photo().findall_by_user_id_and_status(
                self.user.id, 0, limit = PHOTOS_PER_PAGE, offset = offset)
            total_items = models.Photo().count_by_user_id_and_status(self.user.id, 0)

        return self.render('{0}photos.html'.format(template_prefix),
                photos_title = photos_title,
                photos_type = photos_type,
                photos = photos,
                total_items = total_items,
                page_path = page_path,
                current_photo = photo,
                )

class BaseUsersHandler(BaseHandler):
    def _render(self, kind, is_mine = False):
        template_prefix = 'partial/' if self.is_ajax_request else (
                'mine_' if is_mine else 'user_')
        offset = (int(self.get_argument('page', 1)) - 1) * USERS_PER_PAGE

        user = self.user if not is_mine else self.current_user

        if kind == 'following':
            page_path = '/user/{0}/following'.format(user.username) if not is_mine else '/mine/following'
            users_title = u'{0}关注的人'.format(user.fullname if not is_mine else u'我')
            user_ids = models.FollowShip().findall_by_follower_user_id(
                user.id, limit = USERS_PER_PAGE, offset = offset).get_field('followed_user_id')
            users = []
            for user_id in user_ids:
                users.append(models.User().find(user_id))
            total_items = models.FollowShip().count_by_follower_user_id(user.id)

        if kind == 'follower':
            page_path = '/user/{0}/follower'.format(user.username) if not is_mine else '/mine/follower'
            users_title = u'关注{0}的人'.format(user.fullname if not is_mine else u'我')
            user_ids = models.FollowShip().findall_by_followed_user_id(
                user.id, limit = USERS_PER_PAGE, offset = offset).get_field('follower_user_id')
            users = []
            for user_id in user_ids:
                users.append(models.User().find(user_id))
            total_items = models.FollowShip().count_by_followed_user_id(user.id)

        return self.render('{0}users.html'.format(template_prefix),
                users_title = users_title,
                users = users,
                total_items = total_items,
                page_path = page_path,
                )


########NEW FILE########
__FILENAME__ = blog
#coding=utf-8
import tornado
import models
import time
from handlers.base import BaseHandler

class BlogHandler(BaseHandler):
    def get(self, blog_id = 0):
        if not blog_id:
            blog = models.Blog().findall(limit=1).to_list()
            if blog:
                blog = blog[0]
        else:
            blog = models.Blog().find(blog_id)

        blog_comments = None
        if blog:
            blog_comments = models.Blog_Comment().findall_by_blog_id(blog.id)

        blogs = models.Blog().select(['id', 'title']).findall(limit=100)
        return self.render('blog/blog.html', 
                blog = blog,
                blogs = blogs,
                blog_comments = blog_comments,
                )

    @tornado.web.authenticated
    def post(self):
        if not self.current_user.is_admin:
            raise tornado.web.HTTPError(403)

        blog = models.Blog()
        if self.get_argument('id', ''):
            blog.id = self.get_argument('id')
        blog.title = self.get_argument('title')
        blog.content = self.get_argument('content')
        blog.created = blog.updated = time.time()
        blog.user_id = self.current_user.id
        blog.save()
        return self.redirect('/blog/{0}'.format(blog.id))

class BlogCommentAddHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, blog_id):
        if self.get_argument('content', ''):
            models.Blog_Comment(
                user_id = self.current_user.id,
                blog_id = blog_id,
                content = self.get_argument('content'),
                created = time.time(),
                updated = time.time(),
            ).save()
        return self.redirect('/blog/{0}'.format(blog_id))

########NEW FILE########
__FILENAME__ = comment
#coding=utf-8
import logging
import time

from tornado.options import options
import tornado

from base import BaseHandler
import models

class CommentAddHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        photo_id = self.get_argument('photo_id', 0)
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.send_error_json({'message': 'photo not exists'})

        content = self.get_argument('content', '').strip()
        if not content:
            return self.send_error_json({'message': 'empty content'})

        comment = models.Photo_Comment(
                user_id = self.current_user.id,
                photo_id = photo.id,
                content = content,
                )
        comment.create()

        comment_content = self.render_string(
                'partial/comment.html',
                comment = comment,
                photo = photo,
                )

        return self.send_success_json(content = comment_content)

class CommentDeleteHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, comment_id):
        comment = models.Photo_Comment().find(comment_id)
        if comment and comment.status == 0:
            comment.delete()
            return self.send_success_json()
        return self.send_error_json({'message': 'error'})

########NEW FILE########
__FILENAME__ = home
#coding=utf-8
import logging
import time

from tornado.options import options
import tornado.web

from common.macros.macro import PHOTOS_PER_PAGE
from base import BaseHandler, BasePhotosHandler
import models

class HomeHandler(BasePhotosHandler):
    def get(self):
        return self._render('hot')

class AboutHandler(BaseHandler):
    def get(self):
        return self.render('about.html')

########NEW FILE########
__FILENAME__ = photo
#coding=utf-8
import logging
import tornado
import json
from handlers.base import BaseHandler, BasePhotosHandler, BaseUserPhotosHandler
import models
from macros.macro import MAX_UPLOAD_SIZE, PHOTOS_PER_PAGE
from helpers import nl2br
from utils import get_photo_exif, get_photo_width_height, check_photo_permission

class PhotoHandler(BaseHandler):
    def _incr_view_counts(self, photo):
        viewed_photo_ids = self.get_cookie('viewed_photo_ids', '').split(',')
        if str(photo.id) not in (viewed_photo_ids):
            viewed_photo_ids += [photo.id]
            photo.views_count += 1
            photo.save()
            self.set_cookie('viewed_photo_ids', ','.join(map(str, viewed_photo_ids)))

    def get(self, photo_id):
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.render('error/photo_not_exists.html')

        self._incr_view_counts(photo)
        
        return self.render('partial/photo.html',
                           photo = photo,
                           photo_exif = models.Photo_Exif().get(photo_id),
                           photo_tags = models.Photo_Tag().findall_by_photo_id(photo_id),
                           )

    @tornado.web.authenticated
    def post(self):
        photo = models.Photo(
                title = self.get_argument('title', ''),
                content = self.get_argument('content', ''),
                user_id = self.current_user.id,
                page_source = self.get_argument('page_source', ''),
                photo_source = self.get_argument('photo_source', ''),
                )
        photo_id = photo.create()

        if photo_id:
            photo.width, photo.height = get_photo_width_height(self.current_user.id, photo.hash)
            photo.save()

            tags = self.get_argument('tag', '')
            if tags:
                for tag in tags.split(' '):
                    models.Photo_Tag(photo_id = photo_id, tag = tag).save()
            
            if self.get_argument('exif_Model', ''):
                for item in ('Model', 'FocalLength', 'FNumber', 'ExposureTime', 'ISOSpeedRatings', 'Lens'):
                    value = self.get_argument('exif_{0}'.format(item), '')
                    models.Photo_Exif(
                            photo_id = photo_id,
                            key = item,
                            value = value).save()
            else:
                exif = get_photo_exif(photo.hash, self.current_user.id)
                for key, value in exif.items():
                    models.Photo_Exif(
                            photo_id = photo_id,
                            key = key,
                            value = value).save()

            self.send_success_json(location='/photo/{0}/via/mine'.format(photo_id))
        else:
            self.send_error_json(photo.errors)


class PhotoUpdateHandler(BaseHandler):
    @check_photo_permission
    @tornado.web.authenticated
    def post(self, photo_id):
        title = self.get_argument('title', '')
        content = self.get_argument('content', '')
        if title:
            self.photo.title = title
            self.photo.content = content
            self.photo.save()
            return self.send_success_json()
        return self.send_error_json({'message': 'update failed'})

class PhotoLikeHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, photo_id):
        photo = models.Photo().find(photo_id)
        if not photo:
            return self.render('error/photo_not_exists.html')

        if not self.current_user.has_liked_photo(photo):
            models.Photo_Like().like(self.current_user.id, photo_id)
        else:
            models.Photo_Like().unlike(self.current_user.id, photo_id)
        return self.send_success_json()

class PhotoUploadHandler(BaseHandler):
    def get(self):
        template_prefix = 'partial/' if self.is_ajax_request else ''
        return self.render('{0}upload.html'.format(template_prefix))

class HotPhotosHandler(BasePhotosHandler):
    def get(self):
        return self._render('hot')

class LatestPhotosHandler(BasePhotosHandler):
    def get(self):
        return self._render('latest')

class PhotoUserHandler(BaseUserPhotosHandler):
    def get(self, photo_id):
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.render('error/photo_not_exists.html')

        # used in BaseUserPhotosHandler
        self.user = models.User().find(photo.user_id)
        return self._render('photos', photo = photo)

class PhotoMineHandler(BasePhotosHandler):
    def get(self, photo_id):
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.render('error/photo_not_exists.html')
        kind = 'mine_upload' if self.current_user else 'hot'
        return self._render(kind, photo = photo)

class PhotoHotHandler(BasePhotosHandler):
    def get(self, photo_id):
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.render('error/photo_not_exists.html')

        return self._render('hot', photo = photo)

class PhotoTagHandler(BasePhotosHandler):
    def get(self, photo_id, tag_name):
        photo = models.Photo().find(photo_id)
        if not photo or photo.status != 0:
            return self.render('error/photo_not_exists.html')

        return self._render('tag', photo = photo, tag_name = tag_name)

class PhotosTagHandler(BasePhotosHandler):
    def get(self, tag_name):
        return self._render('tag', tag_name = tag_name)

class PhotoTagAddHandler(BaseHandler):
    @check_photo_permission
    @tornado.web.authenticated
    def post(self, photo_id):
        tags = self.get_argument('tag', '').split(' ')
        for tag in tags:
            if tag:
                models.Photo_Tag(
                        photo_id = self.photo.id,
                        tag = tag
                        ).save()

        return self.send_success_json(tags = tags)

class PhotoTagRemoveHandler(BaseHandler):
    @check_photo_permission
    @tornado.web.authenticated
    def post(self, photo_id, tag_id):
        tag = models.Photo_Tag().find(tag_id)
        if tag and tag.photo_id == self.photo.id:
            tag.delete()
            return self.send_success_json()
        return self.send_error_json({'message': 'invalid tag id'})

class PhotoDeleteHandler(BaseHandler):
    @check_photo_permission
    @tornado.web.authenticated
    def post(self, photo_id):
        self.photo.delete()
        return self.send_success_json(location = '/')

########NEW FILE########
__FILENAME__ = user
#coding=utf-8
import tornado
import models
import json
from base import (BaseHandler,
                  BasePhotosHandler,
                  BaseUserPhotosHandler,
                  BaseUsersHandler)
from utils import check_user_exists, process_avatar, hash_password
from helpers import get_avatar_url
from macros.macro import PHOTOS_PER_PAGE, MAX_AVATAR_SIZE, MAX_FOLLOW_NUM, MAX_UPLOAD_SIZE

class UserHandler(BaseUserPhotosHandler):
    @check_user_exists
    def get(self, username):
        return self._render('photos')

class UserPhotosHandler(BaseUserPhotosHandler):
    @check_user_exists
    def get(self, username):
        return self._render('photos')

class UserFollowingHandler(BaseUsersHandler):
    @check_user_exists
    def get(self, username):
        return self._render('following')

class UserFollowerHandler(BaseUsersHandler):
    @check_user_exists
    def get(self, username):
        return self._render('follower')

class MineFollowingHandler(BaseUsersHandler):
    @tornado.web.authenticated
    def get(self):
        return self._render('following', is_mine = True)

class MineFollowerHandler(BaseUsersHandler):
    @tornado.web.authenticated
    def get(self):
        return self._render('follower', is_mine = True)

class UserFollowHandler(BaseHandler):
    @check_user_exists
    @tornado.web.authenticated
    def post(self, username):
        if (not self.current_user.is_following(self.user.id) and 
            self.current_user.following_count < MAX_FOLLOW_NUM):
            models.FollowShip().follow(
                    self.current_user.id, self.user.id)
        else:
            models.FollowShip().unfollow(
                    self.current_user.id, self.user.id)
        return self.send_success_json()

class MinePhotosHandler(BasePhotosHandler):
    @tornado.web.authenticated
    def get(self):
        return self._render('mine_upload')

class MineLikesPhotosHandler(BasePhotosHandler):
    @tornado.web.authenticated
    def get(self):
        return self._render('mine_likes')

class MineInviteHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        invite_keys = models.Invite_Key().findall_by_user_id(self.current_user.id)
        template_prefix = 'partial/' if self.is_ajax_request else 'mine_'
        return self.render('{0}invite_key.html'.format(template_prefix),
                            invite_keys = invite_keys)

class SettingsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        template = 'partial/settings.html' if self.is_ajax_request else 'settings.html'
        return self.render(template, 
                           profile = self.current_user.profile,
                           )

class SettingsProfileHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        fullname = self.get_argument('fullname', '').strip()
        self.current_user.fullname = fullname
        self.current_user.save()
        if not self.current_user.saved:
            return self.send_error_json(self.current_user.errors)

        profile = self.current_user.profile
        profile.camera = self.get_argument('camera', '')
        profile.lens = self.get_argument('lens', '')
        profile.bio = self.get_argument('bio', '')
        profile.save()

        return self.send_success_json()

class SettingsLinkHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        profile = self.current_user.profile
        profile.link_weibo = self.get_argument('link_weibo', '')
        profile.link_qq = self.get_argument('link_qq', '')
        profile.link_douban = self.get_argument('link_douban', '')
        profile.link_flickr = self.get_argument('link_flickr', '')
        profile.link_blog = self.get_argument('link_blog', '')
        profile.save()

        if profile.saved:
            return self.send_success_json()
        return self.send_error_json(profile.errors)

class SettingsAvatarHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        def _send_result(status, content):
            data = {'status': status, 'content': content}
            return self.write("""
                    <script type = 'text/javascript'>
                    parent.avatarUploadDone({0})
                    </script>
                    """.format(json.dumps(data)))

        if not self.request.files:
            return _send_result('error', {'avatar': u'没有选择头像'})
        avatar_info = self.request.files['avatar'][0]
        if avatar_info['content_type'][:5] != 'image':
            return _send_result('error', {'avatar': u'这不是图片哦'})
        if len(avatar_info['body']) > (MAX_AVATAR_SIZE * 1024 * 1024):
            return _send_result('error', {'avatar': u'头像最大不能超过{0}M'.format(MAX_AVATAR_SIZE)})

        hash = process_avatar(avatar_info['body'], self.current_user.id)
        self.current_user.avatar_hash = hash
        self.current_user.save()
        avatar_url = get_avatar_url(self, self.current_user, 's')
        return _send_result('ok', {'avatar_url': avatar_url})

class SettingsPasswordHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        changed = self.current_user.change_password(
                  self.get_argument('origin_password', ''),
                  self.get_argument('password', ''),
                  self.get_argument('password_confirm', ''))
        if changed:
            return self.send_success_json()
        return self.send_error_json(self.current_user.errors)


########NEW FILE########
__FILENAME__ = routes
from handlers import *

handlers = [
    (r"/", HomeHandler),
    (r"/register", RegisterHandler),
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
    (r"/about", AboutHandler),

    (r"/photo/upload", PhotoUploadHandler),
    (r"/photo", PhotoHandler),
    (r"/photo/([0-9]+)/delete", PhotoDeleteHandler),
    (r"/photo/([0-9]+)/tagadd", PhotoTagAddHandler),
    (r"/photo/([0-9]+)/tagremove/([0-9]+)", PhotoTagRemoveHandler),
    (r"/photo/([0-9]+)/update", PhotoUpdateHandler),
    (r"/photo/([0-9]+)/via/user", PhotoUserHandler),
    (r"/photo/([0-9]+)/via/hot", PhotoHotHandler),
    (r"/photo/([0-9]+)/via/mine", PhotoMineHandler),
    (r"/photo/([0-9]+)/via/tag/([^/*]+)", PhotoTagHandler),
    (r"/photo/([0-9]+)", PhotoHandler),
    (r"/photo/([0-9]+)/like", PhotoLikeHandler),
    (r"/photos/hot", HotPhotosHandler),
    (r"/photos/latest", LatestPhotosHandler),
    (r"/tag/([^/*]+)", PhotosTagHandler),

    (r"/user/([a-zA-Z\-\_0-9]+)", UserHandler),
    (r"/user/([a-zA-Z\-\_0-9]+)/photos", UserPhotosHandler),
    (r"/user/([a-zA-Z\-\_0-9]+)/follow", UserFollowHandler),
    (r"/user/([a-zA-Z\-\_0-9]+)/following", UserFollowingHandler),
    (r"/user/([a-zA-Z\-\_0-9]+)/follower", UserFollowerHandler),

    (r"/mine/photos", MinePhotosHandler),
    (r"/mine/likes_photos", MineLikesPhotosHandler),
    (r"/mine/invite", MineInviteHandler),
    (r"/mine/following", MineFollowingHandler),
    (r"/mine/follower", MineFollowerHandler),

    (r"/settings", SettingsHandler),
    (r"/settings/profile", SettingsProfileHandler),
    (r"/settings/link", SettingsLinkHandler),
    (r"/settings/avatar", SettingsAvatarHandler),
    (r"/settings/password", SettingsPasswordHandler),

    (r"/comment/add", CommentAddHandler),
    (r"/comment/([0-9]+)/delete", CommentDeleteHandler),

    (r"/blog", BlogHandler),
    (r"/blog/([0-9]+)", BlogHandler),
    (r"/blog/([0-9]+)/comment", BlogCommentAddHandler),

]

########NEW FILE########
