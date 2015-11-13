__FILENAME__ = commands
import itertools
import random
import sys

if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    import simplejson as json
else:
    import json

from os.path import exists
from sys import argv

import hipchat.config
import hipchat.room
import hipchat.user

class NoConfigException(Exception): pass

def init_sys_cfg():
    if exists('hipchat.cfg'):
        hipchat.config.init_cfg('hipchat.cfg')
    elif exists('~/.hipchat.cfg'):
        hipchat.config.init_cfg('~/.hipchat.cfg')
    elif exists('/etc/hipchat.cfg'):
        hipchat.config.init_cfg('/etc/hipchat.cfg')
    else:
        raise NoConfigException

class ArgsException(Exception): pass


def list_users():
    include_deleted = 0
    if len(argv) > 1:
        include_deleted = argv[1]
    init_sys_cfg()
    print json.dumps(map(hipchat.user.User.get_json,
        hipchat.user.User.list(include_deleted=include_deleted)))


def add_user():
    try:
        dont_care, email, name, title, is_admin, password, timezone = argv
    except ValueError:
        raise ArgsException("%s <email> <name> <title> <is_admin> <password> <timezone>" % argv[0])
    init_sys_cfg()
    print hipchat.user.User.create(email=email,
                                   name=name,
                                   title=title,
                                   is_group_admin=is_admin,
                                   password=password,
                                   timezone=timezone)


def disable_user():
    try:
        dont_care, email = argv
    except ValueError:
        raise ArgsException("%s <email>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   password="".join([x('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890:"<\',.>;|\\+=-_~`!@#$%%^&*(){}1234567890[]') for x in itertools.repeat(random.choice, 20)])) #i'm sure there's a better way to do this, but too lazy to do research


def enable_user():
    try:
        dont_care, email, password = argv
    except ValueError:
        raise ArgsException("%s <email> <password>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   password=password)


def show_user():
    try:
        dont_care, email = argv
    except ValueError:
        raise ArgsException("%s <email>" % argv[0])
    init_sys_cfg()
    print hipchat.user.User.show(user_id=email)


def set_user_password():
    try:
        dont_care, email, password = argv
    except ValueError:
        raise ArgsException("%s <email> <password>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   password=password)


def set_user_name():
    try:
        dont_care, email, name = argv
    except ValueError:
        raise ArgsException("%s <email> <name>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   name=name)


def set_user_admin():
    try:
        dont_care, email, is_admin = argv
    except ValueError:
        raise ArgsException("%s <email> <is_admin>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   is_group_admin=is_admin)


def set_user_timezone():
    try:
        dont_care, email, timezone = argv
    except ValueError:
        raise ArgsException("%s <email> <timezone>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   timezone=timezone)


def set_user_title():
    try:
        dont_care, email, title = argv
    except ValueError:
        raise ArgsException("%s <email> <title>" % argv[0])
    init_sys_cfg()
    user_id = hipchat.user.User.show(user_id=email).user_id
    print hipchat.user.User.update(user_id=user_id,
                                   title=title)


def del_user():
    try:
        dont_care, email = argv
    except ValueError:
        raise ArgsException("%s <email>" % argv[0])
    init_sys_cfg()
    print hipchat.user.User.delete(user_id=email)


def undel_user():
    try:
        dont_care, email = argv
    except ValueError:
        raise ArgsException("%s <email>" % argv[0])
    init_sys_cfg()
    print hipchat.user.User.undelete(user_id=email)

########NEW FILE########
__FILENAME__ = config
from configobj import ConfigObj

token = 0
proxy_server = 0
proxy_type = 0

def init_cfg(config_fname):
    cfg = ConfigObj(config_fname)
    global token, proxy_type, proxy_server
    token = cfg['token']
    proxy_server = cfg.get('proxy_server', 0)
    proxy_type = cfg.get('proxy_type', 0)

########NEW FILE########
__FILENAME__ = connection
import sys

from urllib import urlencode
from urllib2 import urlopen, Request

if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    import simplejson as json
else:
    import json

import hipchat.config

def partial(func, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = keywords.copy()
        newkeywords.update(fkeywords)
        return func(*(args + fargs), **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc


def call_hipchat(cls, ReturnType, url, data=True, **kw):
    auth = [('format', 'json'), ('auth_token', hipchat.config.token)]
    if not data:
        auth.extend(kw.items())
    req = Request(url=url + '?%s' % urlencode(auth))
    if data:
        req.add_data(urlencode(kw.items()))
    if hipchat.config.proxy_server and hipchat.config.proxy_type:
        req.set_proxy(hipchat.config.proxy_server, hipchat.config.proxy_type)
    return ReturnType(json.load(urlopen(req)))


class HipChatObject(object):
    def __init__(self, jsono):
        self.jsono = jsono
        for k, v in jsono[self.sort].iteritems():
            setattr(self, k, v)

    def __str__(self):
        return json.dumps(self.jsono)

    def get_json(self):
        return self.jsono

########NEW FILE########
__FILENAME__ = room
from hipchat.connection import partial, call_hipchat, HipChatObject

class Room(HipChatObject):
    sort = 'room'


class Message(HipChatObject):
    sort = 'message'


class MessageSentStatus(HipChatObject):
    sort = 'status'
    def __init__(self, jsono):
        self.jsono = jsono
        self.status = jsono.get('status')


Room.history = \
    classmethod(partial(call_hipchat, 
                        ReturnType=lambda x: map(Message, map(lambda y: {'message': y}, x['messages'])), 
                        url="https://api.hipchat.com/v1/rooms/history", 
                        data=False))
Room.list = \
    classmethod(partial(call_hipchat, 
                        ReturnType=lambda x: map(Room, map(lambda y: {'room': y}, x['rooms'])), 
                        url="https://api.hipchat.com/v1/rooms/list", 
                        data=False))
Room.message = classmethod(partial(call_hipchat, ReturnType=MessageSentStatus, url="https://api.hipchat.com/v1/rooms/message", data=True))
Room.show = classmethod(partial(call_hipchat, Room, url="https://api.hipchat.com/v1/rooms/show", data=False))

########NEW FILE########
__FILENAME__ = user
from hipchat.connection import partial, call_hipchat, HipChatObject

class UserDeleteStatus(HipChatObject):
    sort = 'delete'
    def __init__(self, jsono):
        self.jsono = jsono
        self.deleted = jsono.get('deleted')


class User(HipChatObject):
    sort = 'user'


User.create = classmethod(partial(call_hipchat, User, url="https://api.hipchat.com/v1/users/create", data=True))
User.delete = \
    classmethod(partial(call_hipchat, 
                        ReturnType=UserDeleteStatus, 
                        url="https://api.hipchat.com/v1/users/delete", 
                        data=True))
User.undelete = \
    classmethod(partial(call_hipchat, 
                        ReturnType=UserDeleteStatus, 
                        url="https://api.hipchat.com/v1/users/undelete", 
                        data=True))
User.list = \
    classmethod(partial(call_hipchat, 
                        ReturnType=lambda x: map(User, map(lambda y: {'user': y}, x['users'])), 
                        url="https://api.hipchat.com/v1/users/list", 
                        data=False))
User.show = classmethod(partial(call_hipchat, User, url="https://api.hipchat.com/v1/users/show", data=False))
User.update = classmethod(partial(call_hipchat, User, url="https://api.hipchat.com/v1/users/update", data=True))

########NEW FILE########
