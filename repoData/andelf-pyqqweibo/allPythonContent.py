__FILENAME__ = example-auth
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  FileName    : example-auth.py
#  Author      : Feather.et.ELF <andelf@gmail.com>
#  Created     : Fri Apr 08 15:35:36 2011 by Feather.et.ELF
#  Copyright   : andelf <andelf@gmail.com> (c) 2011
#  Description : example to show how to do authentication
#  Time-stamp: <2011-06-04 11:37:50 andelf>


from __future__ import unicode_literals
import sys
sys.path.insert(0, '..')
import webbrowser
from qqweibo import API, JSONParser
from qqweibo import OAuth2_0_Handler as AuthHandler
import secret

# for py3k
try:
    input = raw_input
except:
    pass


API_KEY = secret.apiKey
API_SECRET = secret.apiSecret
CALLBACK_URL = secret.callbackUrl

auth = AuthHandler(API_KEY, API_SECRET, CALLBACK_URL)


## use get_authorization_url if you haven't got a token
url = auth.get_authorization_url()
print ('Opening {:s} in your browser...'.format(url))
webbrowser.open_new(url)
verifier = input('Your CODE: ').strip()

token = auth.get_access_token(verifier)

print token
# = Save Token =


# now you have a workable api
api = API(auth, parser=JSONParser())
# or use `api = API(auth)`
print ("User Infomation:")
I = api.user.info()                     # or api.me()
data = I['data']
print (("Name: {name}\nNick: {nick}\nLocation {location}\n"
        "Email: {email}\n").format(**data))

########NEW FILE########
__FILENAME__ = example-timeline
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  FileName    : example-timeline.py
#  Author      : Feather.et.ELF <fledna@qq.com>
#  Created     : Fri Apr 08 15:37:46 2011 by Feather.et.ELF
#  Copyright   : andelf <andelf@gmail.com> (c) 2011
#  Description : example file to show how to get timeline
#  Time-stamp: <2011-06-04 11:38:17 andelf>


from __future__ import unicode_literals
import sys
sys.path.insert(0, "..")
import webbrowser

from qqweibo import OAuthHandler, API


API_KEY = 'your key'
API_SECRET = 'your secret'

if API_KEY.startswith('your'):
    print ('You must fill API_KEY and API_SECRET!')
    webbrowser.open("http://open.t.qq.com/apps_index.php")
    raise RuntimeError('You must set API_KEY and API_SECRET')

auth = OAuthHandler(API_KEY, API_SECRET)

token = YOUR TOKEN HERE (so called consumer)
tokenSecret = YOUR TOKEN_SECRET HERE (so called token)

auth.setToken(token, tokenSecret)

api = API(auth)

"""
Avaliable API:
Do to refer api.doc.rst
api.timeline.broadcast
api.timeline.home
api.timeline.mentions
api.timeline.public
api.timeline.special
api.timeline.topic
api.timeline.user
"""

def dumpTweet(t):
    try:
        print ("{0.nick}({0.name}) => {0.origtext} [{0.from_}]".format(t))
        if t.source:
            print ("!Orig: {0.source.origtext}".format(t))
    except UnicodeEncodeError:
        # NOTE: this is a very common error under win32
        print ("Error: Some tweets or usernames may be outside "
               "your system encoding")


for t in api.timeline.home():
    dumpTweet(t)

for retid in api.timeline.homeids():
    t = api.tweet.show(retid.id)
    # or the magic t = retid.as_tweet()
    dumpTweet(t)
    print ("Warning: it may use up your request quota.")
    break

for t in api.timeline.users(names=['andelf', 'karenmo']):
    dumpTweet(t)

########NEW FILE########
__FILENAME__ = example-tweet
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  FileName    : example-tweet.py
#  Author      : Feather.et.ELF <andelf@gmail.com>
#  Created     : Fri Apr 08 15:44:25 2011 by Feather.et.ELF
#  Copyright   : andelf <andelf@gmail.com> (c) 2011
#  Description : example to show how to post or del
#  Time-stamp: <2011-06-04 11:38:34 andelf>


from __future__ import unicode_literals
import sys
sys.path.insert(0, "..")
import webbrowser

from qqweibo import OAuthHandler, API, ModelParser


API_KEY = 'your key'
API_SECRET = 'your secret'


if API_KEY.startswith('your'):
    print ('You must fill API_KEY and API_SECRET!')
    webbrowser.open("http://open.t.qq.com/apps_index.php")
    raise RuntimeError('You must set API_KEY and API_SECRET')

auth = OAuthHandler(API_KEY, API_SECRET)

token = 'your token'
tokenSecret = 'yourr tokenSecret'

auth.setToken(token, tokenSecret)

# this time we use ModelParser()
api = API(auth, parser=ModelParser())


"""
Avaliable API:
Do to refer api.doc.rst
api.tweet.add
api.tweet.addmusic
api.tweet.addpic
api.tweet.addvideo
api.tweet.comment
api.tweet.delete
api.tweet.getvideoinfo
api.tweet.reply
"""

# you must use unicode object here
sent = []
ret = api.tweet.add('测试发帖....本帖来自 #pyqqweibo#.', clientip='127.0.0.1')
print (ret)
sent.append(ret.id)

tw = api.tweet.show(ret.id)
print ('id={0.id} nick={0.nick} text={0.text}'.format(tw))

ret = tw.reply('测试自回复')           # 作为对话显示
sent.append(ret.id)

ret = tw.retweet('测试自转发')
sent.append(ret.id)

ret = tw.comment('测试评论')
sent.append(ret.id)

for id in sent:
    print ("Uncomment to delete")
    #api.tweet.delete(id)
    # or api.tweet.show(id).delete()

########NEW FILE########
__FILENAME__ = example-user
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  FileName    : example-user.py
#  Author      : Feather.et.ELF <andelf@gmail.com>
#  Created     : Fri Apr 08 16:53:09 2011 by Feather.et.ELF
#  Copyright   : andelf <andelf@gmail.com> (c) 2011
#  Description : example to show how to use user api
#  Time-stamp: <2011-06-04 11:39:06 andelf>


import sys
sys.path.insert(0, "..")
import webbrowser

from qqweibo import API
from qqweibo import OAuth2_0_Handler as AuthHandler

API_KEY = 'your key'
API_SECRET = 'your secret'

if API_KEY.startswith('your'):
    print ('You must fill API_KEY and API_SECRET!')
    webbrowser.open("http://open.t.qq.com/apps_index.php")
    raise RuntimeError('You must set API_KEY and API_SECRET')

CALLBACK_URL = 'http://fledna.duapp.com/query'

auth = AuthHandler(API_KEY, API_SECRET, CALLBACK_URL)


token = YOUR TOKEN HERE
tokenSecret = YOUR TOKEN_SECRET HERE

auth.setToken(token, tokenSecret)

# this time we use ModelParser()
api = API(auth)  # ModelParser is the default option


"""
Avaliable API:
Do to refer api.doc.rst
api.user.info
api.user.otherinfo
api.user.update
api.user.updatehead
api.user.userinfo
"""

me = api.user.info()

print (("Name: {0.name}\nNick: {0.nick}\nLocation {0.location}\n"
        "Email: {0.email}\nIntro: {0.introduction}").format(me))

print (me.self)                           # is this user myself?

me.introduction = 'modify from pyqqweibo!!!'
me.update()                             # update infomation

me = api.user.info()
print (me.introduction)

api.user.updatehead('/path/to/your/head/img.fmt')

ret = api.user.otherinfo('NBA')

print (ret.verifyinfo)

for t in ret.timeline(reqnum=3):
    print (t.text)

########NEW FILE########
__FILENAME__ = secret.sample
apiKey = 'yours'
apiSecret = 'yours'
callbackUrl = 'http://fledna.duapp.com/query'
openid = 'yours'
accessToken = 'yours'

########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-11-09 10:18:18 wangshuyu>

import os
import mimetypes

from qqweibo.binder import bind_api
from qqweibo.error import QWeiboError
from qqweibo.parsers import ModelParser
from qqweibo.utils import convert_to_utf8_bytes, mulitpart_urlencode


class API(object):
    """Weibo API"""
    # TODO: remove unsupported params
    def __init__(self, auth_handler=None, retry_count=0,
                 host='open.t.qq.com', api_root='/api', cache=None,
                 secure=False, retry_delay=0, retry_errors=None,
                 source=None, parser=None, log=None):
        self.auth = auth_handler
        self.host = host
        self.api_root = api_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()
        self.log = log

        self._build_api_path()
    ## 时间线 ##

    """ 1.Statuses/home_timeline 主页时间线 """
    # BUG: type, contenttype, accesslevel is useless
    _statuses_home_timeline = bind_api(
        path = '/statuses/home_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime',
                         'type', 'contenttype'],
    )

    """ 2.Statuses/public_timeline 广播大厅时间线"""
    _statuses_public_timeline = bind_api(
        path = '/statuses/public_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pos'],
    )

    """ 3.Statuses/user_timeline 其他用户发表时间线"""
    _statuses_user_timeline = bind_api(
        path = '/statuses/user_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['name', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
    )

    """ 4.Statuses/mentions_timeline @提到我的时间线 """
    _statuses_mentions_timeline = bind_api(
        path = '/statuses/mentions_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid',
                         'type', 'contenttype', 'accesslevel'],
    )

    """ 5.Statuses/ht_timeline 话题时间线 """
    _statuses_ht_timeline = bind_api(
        path = '/statuses/ht_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['httext', 'reqnum', 'pageflag', 'pageinfo'],
    )

    """ 6.Statuses/broadcast_timeline 我发表时间线 """
    _statuses_broadcast_timeline = bind_api(
        path = '/statuses/broadcast_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
    )

    """ 7.Statuses/special_timeline 特别收听的人发表时间线 """
    _statuses_special_timeline = bind_api(
        path = '/statuses/special_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime'],
    )

    """ 8.Statuses/area_timeline 地区发表时间线 """
    # required: country, province, city
    _statuses_area_timeline = bind_api(
        path = '/statuses/area_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['country', 'province', 'city', 'reqnum', 'pos'],
    )

    """ 9.Statuses/home_timeline_ids 主页时间线索引 """
    _statuses_home_timeline_ids = bind_api(
        path = '/statuses/home_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'type',
                         'contenttype'],
    )

    """ 10.Statuses/user_timeline_ids 其他用户发表时间线索引 """
    # required: name
    _statuses_user_timeline_ids = bind_api(
        path = '/statuses/user_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['name', 'reqnum', 'pageflag', 'pagetime', 'type',
                         'contenttype'],
    )

    """ 11.Statuses/broadcast_timeline_ids 我发表时间线索引 """
    _statuses_broadcast_timeline_ids = bind_api(
        path = '/statuses/broadcast_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid', 'type',
                         'contenttype'],
    )

    """ 12.Statuses/mentions_timeline_ids 用户提及时间线索引 """
    _statuses_mentions_timeline_ids = bind_api(
        path = '/statuses/mentions_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid', 'type',
                         'contenttype'],
    )

    """ 13.Statuses/users_timeline 多用户发表时间线 """
    _statuses_users_timeline = bind_api(
        path = '/statuses/users_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['names', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
    )

    """ 14.Statuses/users_timeline_ids 多用户发表时间线索引 """
    _statuses_users_timeline_ids = bind_api(
        path = '/statuses/users_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['names', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
    )

    """ 15.statuses/ht_timeline_ext 话题时间线 """
    _statuses_ht_timeline_ext = bind_api(
        path = '/statuses/ht_timeline_ext',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['httext', 'reqnum', 'tweetid', 'time', 'pageflag',
                         'flag', 'accesslevel', 'type', 'contenttype'],
    )

    """ 16.statuses/home_timeline_vip 拉取vip用户发表微博消息接口 """
    _statuses_home_timeline_vip = bind_api(
        path = '/statuses/home_timeline_vip',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'lastid', 'pagetime', 'pageflag',],

    )

    _statuses_get_micro_album = bind_api(
        path = '/statuses/get_micro_album',
        payload_type = 'json', payload_list = True,
        allowed_param = ['reqnum', 'name'],
    )

    _statuses_sub_re_list = bind_api(
        path = '/statuses/sub_re_list',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['rootid', 'type', 'reqnum'],
    )

    """ 名单接口 """
    _list_add_to_list = bind_api(
        path = '/add_to_list',
        method = 'POST',
        payload_type = 'json',
        allowed_param = ['listid', 'names'],
    )
    ## TODO: finish list api

    ## 微博相关 ##
    """ 1.t/show 获取一条微博数据 """
    _t_show = bind_api(
        path = '/t/show',
        payload_type = 'tweet',
        allowed_param = ['id'],

    )

    """ 2.t/add 发表一条微博 """
    _t_add = bind_api(
        path = '/t/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['content', 'longitude', 'latitude', 'clientip'],

    )

    """ 3.t/del 删除一条微博 """
    _t_del = bind_api(
        path = '/t/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 4.t/re_add 转播一条微博 """
    _t_re_add = bind_api(
        path = '/t/re_add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'longitude', 'latitude', 'clientip'],

    )

    """ 5.t/reply 回复一条微博 """
    _t_reply = bind_api(
        path = '/t/reply',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'longitude', 'latitude', 'clientip'],

    )

    """ 6.t/add_pic 发表一条带图片的微博 """
    def _t_add_pic(self, filename, content="", longitude=0, latitude=0, clientip='127.0.0.1'):
        _, query = self.auth.authorize_request(
            "dummy", "POST", {}, dict(content=content, clientip=clientip, longitude=longitude, latitude=latitude))
        headers, post_data = mulitpart_urlencode("pic", filename, **dict(query))

        allowed_param = ['content', 'longitude', 'latitude', 'clientip']
        args = [content, longitude, latitude, clientip]
        return bind_api(
            path = '/t/add_pic',
            method = 'POST',
            payload_type = 'retid',
            allowed_param = allowed_param
            )(self, *args, post_data=post_data, headers=headers)

    """ 7.t/re_count 转播数或点评数 """
    _t_re_count = bind_api(
        path = '/t/re_count',
        payload_type = 'json',
        allowed_param = ['ids', 'flag'],
    )

    """ 8.t/re_list 获取单条微博的转发或点评列表 """
    _t_re_list = bind_api(
        path = '/t/re_list',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['rootid', 'reqnum', 'flag', 'pageflag', 'pagetime',
                         'twitterid'],
    )

    """ 9.t/comment 点评一条微博 """
    _t_comment = bind_api(
        path = '/t/comment',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'longitude', 'latitude', 'clientip'],
    )

    """ 10.t/add_music发表音乐微博 """
    _t_add_music = bind_api(
        path = '/t/add_music',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['url', 'title', 'author', 'content',
                         'longitude', 'latitude', 'clientip'],
    )

    """ 11.t/add_video发表视频微博 """
    _t_add_video = bind_api(
        path = '/t/add_video',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['url', 'content', 'longitude', 'latitude', 'clientip'],
    )

    """ 12.t/getvideoinfo 获取视频信息 """
    _t_getvideoinfo = bind_api(
        path = '/t/getvideoinfo',
        method = 'POST',
        payload_type = 'video',
        allowed_param = ['url'],
    )

    """ 13.t/list 根据微博ID批量获取微博内容（与索引合起来用） """
    _t_list = bind_api(
        path = '/t/list',
        method = 'GET',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['ids'],
    )

    """ 14.t/add_video_prev 预发表一条视频微博 """
    _t_add_video_prev = bind_api(
        path = '/t/add_video_prev',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['content', 'longitude', 'latitude', 'vid', 'title', 'clientip'],
    )

    """ 15.t/sub_re_count 获取转播的再次转播数（二次转发次数) """
    _t_sub_re_count = bind_api(
        path = '/t/sub_re_count',
        payload_type = 'dict',
        allowed_param = ['ids'],
    )

    """ 16.t/add_emotion 发表心情帖子 """
    _t_add_emotion = bind_api(
        path = '/t/add_emotion',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['signtype', 'content', 'longitude', 'latitude', 'clientip'],
    )

    _t_add_pic_url = bind_api(
        path = '/t/add_pic_url',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['pic_url', 'content', 'longitude', 'latitude', 'clientip'],
    )

    _t_add_multi = bind_api(
        path = '/t/add_multi',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['content', 'longitude', 'latitude', 'pic_url', 'video_url', 'music_url',
                         'music_title', 'music_author', 'clientip'],
    )

    _t_upload_pic = bind_api(
        path = '/t/upload_pic',
        method = 'POST',
        payload_type = 'json',
        allowed_param = ['pic_url'],
    )

    ## 帐户相关 ##
    """ 1.User/info获取自己的详细资料 """
    _user_info = bind_api(
        path = '/user/info',
        payload_type = 'user',
        allowed_param = [],

    )

    """ 2.user/update 更新用户信息 """
    _user_update = bind_api(
        path = '/user/update',
        method = 'POST',
        allowed_param = ['nick', 'sex', 'year', 'month',
                         'day', 'countrycode', 'provincecode',
                         'citycode', 'introduction'],

    )

    """ 3.user/update_head 更新用户头像信息 """
    def _user_update_head(self, filename):
        headers, post_data = mulitpart_urlencode("pic", filename)
        args = []
        allowed_param = []

        return bind_api(
            path = '/user/update_head',
            method = 'POST',

            allowed_param = allowed_param
            )(self, *args, post_data=post_data, headers=headers)

    """ 4.user/update_edu 更新用户教育信息 """
    # TODO: 吐槽此条API
    _user_update_edu = bind_api(
        path = '/user/update_edu',
        method = 'POST',
        allowed_param = ['feildid', 'year', 'schoolid', 'departmentid', 'level'],

    )

    """ 5.user/other_info 获取其他人资料 """
    _user_other_info = bind_api(
        path = '/user/other_info',
        payload_type = 'user',
        allowed_param = ['name'],

    )

    """ 6.user/infos 获取一批人的简单资料 """
    _user_infos = bind_api(
        path = '/user/infos',
        payload_type = 'user', payload_list = True,
        allowed_param = ['names'],

    )

    """ 7.user/verify 验证账户是否合法（是否注册微博） """
    _user_verify = bind_api(
        path = '/user/verify',
        method = 'POST',
        payload_type = 'json',
        allowed_param = ['name'],

    )

    """ 8.user/emotion 获取心情微博 """ # TODO: if empty returned, may fail
    _user_emotion = bind_api(
        path = '/user/emotion',
        method = 'POST',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['name', 'reqnum', 'pageflag', 'timestamp', 'type',
                         'contenttype', 'accesslevel', 'emotiontype'],

    )

    """ 1.friends/fanslist 我的听众列表 """
    _friends_fanslist = bind_api(
        path = '/friends/fanslist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],

    )

    """ 2.friends/idollist 我收听的人列表 """
    _friends_idollist = bind_api(
        path = '/friends/idollist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 3.Friends/blacklist 黑名单列表 """
    _friends_blacklist = bind_api(
        path = '/friends/blacklist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 4.Friends/speciallist 特别收听列表 """
    _friends_speciallist = bind_api(
        path = '/friends/speciallist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 5.friends/add 收听某个用户 """
    _friends_add = bind_api(
        path = '/friends/add',
        method = 'POST',
        allowed_param = ['name'],
    )

    """ 6.friends/del取消收听某个用户 """
    _friends_del = bind_api(          # fix confilicts with del
        path = '/friends/del',
        method = 'POST',
        allowed_param = ['name'],
    )

    """ 7.friends/addspecial 特别收听某个用户 """
    _friends_addspecial = bind_api(
        path = '/friends/addspecial',
        method = 'POST',
        allowed_param = ['name'],
    )

    """ 8.friends/delspecial 取消特别收听某个用户 """
    _friends_delspecial = bind_api(
        path = '/friends/delspecial',
        method = 'POST',
        allowed_param = ['name'],

    )

    """ 9.friends/addblacklist 添加某个用户到黑名单 """
    _friends_addblacklist = bind_api(
        path = '/friends/addblacklist',
        method = 'POST',
        allowed_param = ['name'],

    )

    """ 10.friends/delblacklist 从黑名单中删除某个用户 """
    _friends_delblacklist = bind_api(
        path = '/friends/delblacklist',
        method = 'POST',
        allowed_param = ['name'],

    )

    """ 11.friends/check 检测是否我的听众或收听的人 """
    _friends_check = bind_api(
        path = '/friends/check',
        payload_type = 'json',
        allowed_param = ['names', 'flag'],

    )

    """ 12.friends/user_fanslist 其他帐户听众列表 """
    _friends_user_fanslist = bind_api(
        path = '/friends/user_fanslist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
    )

    """ 13.friends/user_idollist 其他帐户收听的人列表 """
    _friends_user_idollist = bind_api(
        path = '/friends/user_idollist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
    )

    """ 14.friends/user_speciallist 其他帐户特别收听的人列表 """
    _friends_user_speciallist = bind_api(
        path = '/friends/user_speciallist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
    )

    """ 15.friends/fanslist_s 我的听众列表，简单信息（200个）"""
    _friends_fanslist_s = bind_api(
        path = '/friends/fanslist_s',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 16.friends/idollist_s 我的收听列表，简单信息（200个） """
    _friends_idollist_s = bind_api(
        path = '/friends/idollist_s',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 17.friends/mutual_list 互听关系链列表 """
    _friends_mutual_list = bind_api(
        path = '/friends/mutual_list',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
    )

    """ 18.fanslist_name 我的听众列表，只输出name（200个） """
    _friends_fanslist_name = bind_api(
        path = '/friends/fanslist_name',
        payload_type = 'json', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """ 19.idollist_name 我的收听列表，只输出name（200个） """
    _friends_idollist_name = bind_api(
        path = '/friends/idollist_name',
        payload_type = 'json', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
    )

    """  获取用户最亲密的好友列表 """
    _friends_get_intimate_friends = bind_api(
        path = '/friends/get_intimate_friends',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum'],
    )

    """ 好友帐号输入提示 """
    _friends_match_nick_tips = bind_api(
        path = '/friends/match_nick_tips',
        payload_type = 'user', payload_list = True,
        allowed_param = ['match', 'reqnum'],
    )

    ## 私信相关 ##
    """ 1.private/add 发私信 """
    _private_add = bind_api(
        path = '/private/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['name', 'content', 'longitude', 'latitude', 'clientip'],

    )

    """ 2.private/del 删除一条私信 """
    _private_del = bind_api(
        path = '/private/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 3.private/recv 收件箱 """
    _private_recv = bind_api(
        path = '/private/recv',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],

    )

    """ 4.private/send 发件箱 """
    _private_send = bind_api(
        path = '/private/send',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],

    )

    ## 搜索相关 ##
    """ 1.Search/user 搜索用户 """
    _search_user = bind_api(
        path = '/search/user',
        payload_type = 'user', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],

    )

    """ 2.Search/t 搜索微博 """
    _search_t = bind_api(
        path = '/search/t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],

    )

    """ 3.Search/userbytag 通过标签搜索用户 """
    _search_userbytag = bind_api(
        path = '/search/userbytag',
        payload_type = 'user', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],

    )

    # TODO: model parser
    ## 热度，趋势 ##
    """ 1.trends/ht 话题热榜 """
    _trends_ht = bind_api(
        path = '/trends/ht',
        payload_type = 'json',
        allowed_param = ['reqnum', 'type', 'pos'],

    )

    """ 2.Trends/t 转播热榜 """
    _trends_t = bind_api(
        path = '/trends/t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'type', 'pos'],

    )

    """ 3.trends/famouslist 推荐名人列表 """
    _trends_famouslist = bind_api(
        path = '/trends/famouslist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['classid', 'subclassid'],

    )

    ## 数据更新相关 ##
    """ 1.info/update 查看数据更新条数 """
    _info_update = bind_api(
        path = '/info/update',
        payload_type = 'json',
        allowed_param = ['op', 'type'],

    )

    ## 数据收藏 ##
    """ 1.fav/addt 收藏一条微博 """
    _fav_addt = bind_api(
        path = '/fav/addt',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 2.fav/delt 从收藏删除一条微博 """
    _fav_delt = bind_api(
        path = '/fav/delt',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 3.fav/list_t 收藏的微博列表 """
    _fav_list_t = bind_api(
        path = '/fav/list_t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'nexttime', 'prevtime',
                         'lastid'],

    )

    """ 4.fav/addht 订阅话题 """
    _fav_addht = bind_api(
        path = '/fav/addht',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 5.fav/delht 从收藏删除话题 """
    _fav_delht = bind_api(
        path = '/fav/delht',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],

    )

    """ 6.fav/list_ht 获取已订阅话题列表 """
    _fav_list_ht = bind_api(
        path = '/fav/list_ht',
        payload_type = 'json', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],

    )

    ## lbs
    # todo: list parser
    _lbs_get_poi = bind_api(
        path = '/lbs/get_poi',
        method = 'POST',
        payload_type = 'json',
        allowed_param = ['longitude', 'latitude', 'radius', 'reqnum']
    )

    ## 话题相关 ##
    """ 1.ht/ids 根据话题名称查询话题ID """
    _ht_ids = bind_api(
        path = '/ht/ids',
        payload_type = 'json', payload_list = True,
        allowed_param = ['httexts'],

    )

    """ 2.ht/info 根据话题ID获取话题相关微博 """
    _ht_info = bind_api(
        path = '/ht/info',
        payload_type = 'json', payload_list = True,
        allowed_param = ['ids'],

    )

    ## 标签相关 ##
    """ 1.tag/add 添加标签 """
    _tag_add = bind_api(
        path = '/tag/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['tag'],

    )

    """ 2.tag/del 删除标签 """
    _tag_del = bind_api(
        path = '/tag/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['tagid'],

    )

    ## 名单 ##
    # TODO

    ## 其他 ##
    """ 1.other/kownperson 我可能认识的人 """
    _other_kownperson = bind_api(
        path = '/other/kownperson',
        payload_type = 'user', payload_list = True,
        allowed_param = [],

    )

    """ 2.other/shorturl短URL变长URL """
    _other_shorturl = bind_api(
        path = '/other/shorturl',
        payload_type = 'json',
        allowed_param = ['url'],

    )

    """ 3.other/videokey 获取视频上传的KEY """
    _other_videokey = bind_api(
        path = '/other/videokey',
        payload_type = 'json',
        allowed_param = [],

    )

    """ 4.other/get_emotions 获取表情接口 """
    _other_get_emotions = bind_api(
        path = '/other/get_emotions',
        payload_type = 'json', payload_list = True,
        allowed_param = ['type'],

    )

    """ 5.other/gettopreadd 一键转播热门排行 """
    _other_gettopreadd = bind_api(
        path = '/other/gettopreadd',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['type', 'country', 'province', 'city'],

    )

    """ Get the authenticated user """
    def me(self):
        return self.user.info()

    """ Internal use only """
    def _build_api_path(self):
        """bind all api function to its namespace"""
        self._bind_api_namespace('timeline',
                                 home=self._statuses_home_timeline,
                                 public=self._statuses_public_timeline,
                                 user=self._statuses_user_timeline,
                                 users=self._statuses_users_timeline,
                                 mentions=self._statuses_mentions_timeline,
                                 topic=self._statuses_ht_timeline,
                                 broadcast=self._statuses_broadcast_timeline,
                                 special=self._statuses_special_timeline,
                                 area=self._statuses_area_timeline,
                                 # ids
                                 homeids=self._statuses_home_timeline_ids,
                                 userids=self._statuses_user_timeline_ids,
                                 usersids=self._statuses_users_timeline_ids,
                                 broadcastids=self._statuses_broadcast_timeline_ids,
                                 mentionsids=self._statuses_mentions_timeline_ids)
        self._bind_api_namespace('tweet',
                                 show=self._t_show,
                                 add=self._t_add,
                                 delete=self._t_del,
                                 retweet=self._t_re_add,
                                 reply=self._t_reply,
                                 addpic=self._t_add_pic,
                                 retweetcount=self._t_re_count,
                                 retweetlist=self._t_re_list,
                                 comment=self._t_comment,
                                 addmusic=self._t_add_music,
                                 addvideo=self._t_add_video,
                                 list=self._t_list)
        self._bind_api_namespace('user',
                                 info=self._user_info,
                                 update=self._user_update,
                                 updatehead=self._user_update_head,
                                 userinfo=self._user_other_info,
                                 )
        self._bind_api_namespace('friends',
                                 fanslist=self._friends_fanslist,
                                 idollist=self._friends_idollist,
                                 blacklist=self._friends_blacklist,
                                 speciallist=self._friends_speciallist,
                                 add=self._friends_add,
                                 delete=self._friends_del,
                                 addspecial=self._friends_addspecial,
                                 deletespecial=self._friends_delspecial,
                                 addblacklist=self._friends_addblacklist,
                                 deleteblacklist=self._friends_delblacklist,
                                 check=self._friends_check,
                                 userfanslist=self._friends_user_fanslist,
                                 useridollist=self._friends_user_idollist,
                                 userspeciallist=self._friends_user_speciallist,
                                 )
        self._bind_api_namespace('private',
                                 add=self._private_add,
                                 delete=self._private_del,
                                 inbox=self._private_recv,
                                 outbox=self._private_send,
                                 )
        self._bind_api_namespace('search',
                                 user=self._search_user,
                                 tweet=self._search_t,
                                 userbytag=self._search_userbytag,
                                 )
        self._bind_api_namespace('trends',
                                 topic=self._trends_ht,
                                 tweet=self._trends_t
                                 )
        self._bind_api_namespace('info',
                                 update=self._info_update,
                                 )
        self._bind_api_namespace('fav',
                                 addtweet=self._fav_addt,
                                 deletetweet=self._fav_delt,
                                 listtweet=self._fav_list_t,
                                 addtopic=self._fav_addht,
                                 deletetopic=self._fav_delht,
                                 listtopic=self._fav_list_ht,
                                 )
        self._bind_api_namespace('topic',
                                 ids=self._ht_ids,
                                 info=self._ht_info,
                                 )
        self._bind_api_namespace('tag',
                                 add=self._tag_add,
                                 delete=self._tag_del,
                                 )
        self._bind_api_namespace('other',
                                 kownperson=self._other_kownperson,
                                 shorturl=self._other_shorturl,
                                 videokey=self._other_videokey,
                                 videoinfo=self._t_getvideoinfo,
                                 )
        self.t = self.tweet
        self.statuses = self.timeline   # fix 时间线 相关

    def _bind_api_namespace(self, base, **func_map):
        """ bind api to its path"""
        if base == '':
            for fname in func_map:
                setattr(self, fname, func_map[fname])
        else:
            if callable(getattr(self, base, None)):
                func_map['__call__'] = getattr(self, base)
            mapper = type('ApiPathMapper', (object,), func_map)()
            setattr(self, base, mapper)

    # TODO: more general method
    @staticmethod
    def _pack_image(filename, contentname, max_size=1024, **params):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise QWeiboError('File is too big, must be less than 700kb.')
        except os.error:
            raise QWeiboError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise QWeiboError('Could not determine file type')
        file_type = file_type[0]
        if file_type.split('/')[0] != 'image':
            raise QWeiboError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        BOUNDARY = 'QqWeIbObYaNdElF----'  # qqweibo by andelf
        body = []
        for key, val in params.items():
            if val is not None:
                body.append('--' + BOUNDARY)
                body.append('Content-Disposition: form-data; name="%s"' % key)
                body.append('Content-Type: text/plain; charset=UTF-8')
                body.append('Content-Transfer-Encoding: 8bit')
                body.append('')
                val = convert_to_utf8_bytes(val)
                body.append(val)
        fp = open(filename, 'rb')
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (contentname, filename.encode('utf-8')))
        body.append('Content-Type: %s' % file_type)
        body.append('Content-Transfer-Encoding: binary')
        body.append('')
        body.append(fp.read())
        body.append('--%s--' % BOUNDARY)
        body.append('')
        fp.close()
        body.append('--%s--' % BOUNDARY)
        body.append('')
        # fix py3k
        for i in range(len(body)):
            body[i] = convert_to_utf8_bytes(body[i])
        body = b'\r\n'.join(body)
        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
            'Content-Length': len(body)
        }

        return headers, body

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-04 08:14:39 andelf>

from compat import Request, urlopen, urlencode, urlparse, parse_qsl, quote
import oauth
from error import QWeiboError
from api import API
from utils import convert_to_utf8_bytes
import utils


class AuthHandler(object):

    def authorize_request(self, url, method, headers, parameters):
        raise NotImplementedError



class OAuth1_0_Handler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'open.t.qq.com'
    OAUTH_ROOT = '/cgi-bin/'
    AUTH_TYPE = "OAuth1.0"

    def __init__(self, consumer_key, consumer_secret, callback=None):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback or 'null'  # fixed
        self.username = None

    def _get_oauth_url(self, endpoint):
        if endpoint in ('request_token', 'access_token'):
            prefix = 'https://'
        else:
            prefix = 'http://'
        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def authorize_request(self, url, method, headers, parameters):
        request = oauth.OAuthRequest(http_method=method, http_url=url, parameters=parameters)
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        return request.to_url()

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(request.to_url()))  # must
            return oauth.OAuthToken.from_string(resp.read().decode('ascii'))
        except RuntimeError as e:
            raise QWeiboError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_weibo=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_weibo:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url, callback=self.callback
            )

            return request.to_url()
        except RuntimeError as e:
            raise QWeiboError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')
            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request
            resp = urlopen(Request(request.to_url()))  # must
            self.access_token = oauth.OAuthToken.from_string(resp.read().decode('ascii'))

            #print ('Access token key: ' + str(self.access_token.key))
            #print ('Access token secret: ' + str(self.access_token.secret))

            return self.access_token
        except Exception as e:
            raise QWeiboError(e)

    def setToken(self, token, tokenSecret):
        self.access_token = oauth.OAuthToken(token, tokenSecret)




class OAuth2_0_Handler(AuthHandler):
    BASE_URL = "https://open.t.qq.com/cgi-bin/oauth2/"
    AUTH_TYPE = "OAuth2.0"

    def __init__(self, API_Key, API_Secret, callback, wap=None, state=None, forcelogin=None):

        if callback is None:
            raise ValueError("Redirect_uri must be set.")

        self.callback = callback

        self._api_secret = API_Secret

        self._api_key = API_Key

        self.openid = None
        self.access_token = None
        self.refresh_token = None

        self.params = {}
        if wap is not None:
            self.params['wap'] = wap
        if state is not None:
            self.params['state'] = scope
        if forcelogin is not None:
            self.params['forcelogin'] = forcelogin

    def get_authorization_url(self):
        """return a url for user to open
        Get the URL to redirect the user for client authorization
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-3.5.2.1
        """
        endpoint = 'authorize'
        redirect_uri = self.callback
        params = self.params

        args = {
            'response_type': 'code',
            'client_id': self._api_key
        }

        args['redirect_uri'] = self.callback
        args.update(params or {})

        return '%s?%s' % (urlparse.urljoin(self.BASE_URL, endpoint),
                          urlencode(args))


    def get_access_token(self, code):
        """user code to access token
        Get an access token from the supplied code
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-3.5.2.2
        """
        if code is None:
            raise ValueError("Code must be set.")

        endpoint='access_token'

        params = {}
        if 'state' in self.params:
            params['state'] = self.params['state']

        args = {
            'grant_type': 'authorization_code',
            'client_id': self._api_key,
            'client_secret': self._api_secret,
            'code': code,
            'redirect_uri': self.callback,
        }

        args.update(params or {})

        uri = urlparse.urljoin(self.BASE_URL, endpoint)
        body = urlencode(args)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        req = Request(uri, body, headers)
        resp = urlopen(req)
        content = resp.read()

        if not resp.code == 200:
            print (resp, resp.code, content)
            raise Error(content)

        response_args = dict(parse_qsl(content))

        error = response_args.get('error', None)
        if error is not None:
            msg = "%s:%s" % (error,
                             response_args.get('error_description', ''))
            raise Error(msg)

        refresh_token = response_args.get('refresh_token', None)
        access_token = response_args.get('access_token', None)
        openid = response_args.get('openid', None)

        #if refresh_token is not None:
        #    response_args = self.refresh(refresh_token)

        self.refresh_token = refresh_token
        self.access_token = access_token
        self.openid = openid

        return response_args

    def set_token(self, openid, access_token, refresh_token):
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.openid = openid

    def refresh(self, refresh_token=None):
        """Get a new access token from the supplied refresh token
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-4
        """
        endpoint = 'access_token'
        refresh_token = refresh_token or self.refresh_token
        if not refresh_token:
            raise ValueError("refresh_token can't be empty")

        args = {
            'grant_type': 'refresh_token',
            'client_id': self._api_key,
            'refresh_token': refresh_token,
        }

        uri = urlparse.urljoin(self.BASE_URL, endpoint)
        body = urlencode(args)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        req = Request(uri, body, headers)
        resp = urlopen(req)
        content = resp.read()

        if not resp.code == 200:
            raise Error(content)

        response_args = dict(parse_qsl(content))
        self.access_token = response_args.get("access_token", None)
        self.refresh_token = response_args.get("refresh_token", None)
        return response_args


    def authorize_request(self, url, method, headers, parameters):
        query = dict(parameters)
        if "oauth_consumer_key" not in query:
            query["oauth_consumer_key"] = self._api_key
        if "access_token" not in query:
            query["access_token"] = self.access_token
        if "openid" not in query:
            query["openid"] = self.openid
        if "scope" not in query:
            query["scope"] = "all"
        if "clientip" not in query:
            query["clientip"] = "127.0.0.1"
        query["oauth_version"] = "2.a"

        query = query.items()
        query = [(str(k), convert_to_utf8_bytes(v)) for k,v in query]
        query.sort()
        if method == 'POST':
            return url, query
        elif method == 'GET':
            params = '&'.join(("%s=%s" % kv) for kv in query)
            if '?' in url:
                return "%s&%s" % (url, params), query
            else:
                return "%s?%s" % (url, params), query

########NEW FILE########
__FILENAME__ = binder
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-09-05 19:40:35 wangshuyu>

import time
import re

from qqweibo.compat import Request, urlopen, quote, urlencode
from qqweibo.error import QWeiboError
from qqweibo.utils import convert_to_utf8_str


re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', True)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise QWeiboError('Authentication required!')

            self.api = api
            self.payload_format = api.parser.payload_format
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)
            self.api_root = api.api_root

            self.scheme = 'https://' if api.auth.AUTH_TYPE == "OAuth2.0" else 'http://'

            self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            #self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            # bind here, as default
            self.parameters = {'format': self.payload_format}
            for idx, arg in enumerate(args):
                try:
                    self.parameters[self.allowed_param[idx]] = quote(convert_to_utf8_str(arg))
                except IndexError:
                    raise QWeiboError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if bool(arg) == False:
                    continue
                if k in self.parameters:
                    raise QWeiboError('Multiple values for parameter `%s` supplied!' % k)
                #if k not in self.allowed_param:
                #    raise QWeiboError('`%s` is not allowd in this API function.' % k)
                self.parameters[k] = quote(convert_to_utf8_str(arg))

        def execute(self):
            # Build the request URL
            url = self.scheme + self.host + self.api_root + self.path

            full_url, parameters = self.api.auth.authorize_request(url, self.method, self.headers, self.parameters)
            self.headers.setdefault("User-Agent", "pyqqweibo")
            if self.method == 'POST':
                if self.post_data is None:
                    self.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                    # asure in bytes format
                    self.post_data = '&'.join(("%s=%s" % kv) for kv in parameters)
                req = Request(full_url, data=self.post_data, headers=self.headers)
            elif self.method == 'GET':
                req = Request(full_url)
            try:
                resp = urlopen(req)
            except Exception as e:
                    raise QWeiboError("Failed to request %s headers=%s %s" % \
                                      (url, self.headers, e))
            body = resp.read()
            self.api.last_response = resp
            # log handling
            if self.api.log is not None:
                requestUrl = "URL:http://" + self.host + url
                eTime = '%.0f' % ((time.time() - sTime) * 1000)
                postData = ""
                if self.post_data is not None:
                    postData = ",post:" + self.post_data[:500]
                self.api.log.debug("%s, time: %s, %s result: %s" % (requestUrl, eTime, postData, body))

            retcode = 0
            errcode = 0
            # for py3k, ^_^
            if not hasattr(body, 'encode'):
                body = str(body, 'utf-8')
            # if self.api.parser.payload_format == 'json':
            #     try:
            #         # BUG: API BUG, refer api.doc.rst
            #         if body.endswith('out of memery'):
            #             body = body[:body.rfind('}')+1]
            #         json = self.api.parser.parse_error(self, body)
            #         retcode = json.get('ret', 0)
            #         msg = json.get('msg', '')
            #         # only in some post request
            #         errcode = json.get('errcode', 0)
            #     except ValueError as e:
            #         retcode = -1
            #         msg = "Bad json format (%s)" % e
            #     finally:
            #         if retcode + errcode != 0:
            #             raise QWeiboError("Response error: %s. (ret=%s, errcode=%s)" % \
            #                               (msg, retcode, errcode))

            # Parse the response payload
            result = self.api.parser.parse(self, body)

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)
            return result



            # Query the cache if one is available
            # and this request uses a GET method.
#            if self.api.cache and self.method == 'GET':
#                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
#                if cache_result:
                    # must restore api reference
#                    if isinstance(cache_result, list):
#                        for result in cache_result:
#                            result._api = self.api
#                    else:
#                        cache_result._api = self.api
#                    return cache_result
                #urllib.urlencode(self.parameters)
            # Continue attempting request until successful
            # or maximum number of retries is reached.
#            sTime = time.time()
#            retries_performed = 0
#            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                # Apply authentication
#                if self.require_auth:
#                    url, headers, parameters = self.api.auth.get_authed_url(
#                        self.scheme + self.host + url,
#                        self.method, self.headers, self.parameters
#                    )
#                else:                   # this brunch is never accoured
#                    url_full = self.api.auth.get_signed_url(
#                        self.scheme + self.host + url,
#                        self.method, self.headers, self.parameters
#                    )
                # try:
                #     if self.method == 'POST':
                #         req = Request(url_full, data=self.post_data, headers=self.headers)
                #     else:
                #         req = Request(url_full)
                #     resp = urlopen(req)
                # except Exception as e:
                #     raise QWeiboError("Failed to request %s headers=%s %s" % \
                #                       (url, self.headers, e))

                # # Exit request loop if non-retry error code
                # if self.retry_errors:
                #     if resp.code not in self.retry_errors:
                #         break
                # else:
                #     if resp.code == 200:
                #         break

                # # Sleep before retrying request again
                # time.sleep(self.retry_delay)
                # retries_performed += 1

            # If an error was returned, throw an exception
    def _call(api, *args, **kargs):
        method = APIMethod(api, args, kargs)
        return method.execute()

    # make doc string
    if config.get('payload_list', False):
        rettype = '[%s]' % config.get('payload_type', None)
    else:
        rettype = str(config.get('payload_type', None))
    doc_string = """ \
    Call API Method %s
    (%s) => %s""" % (config['path'],
                     ', '.join(config.get('allowed_param', [])),
                     rettype)
    _call.__doc__ = doc_string

    return _call

########NEW FILE########
__FILENAME__ = cache
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 15:08:40 andelf>

import time
import threading
import os
import hashlib

from qqweibo.compat import pickle
try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print ('Warning! FileCache locking not supported on this system!')
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        # fixed for py3.x
        md5.update(key.encode('utf-8'))
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))


########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-04 01:55:58 andelf>

try:
    from urllib2 import Request, urlopen
    import urlparse
    from urllib import quote, unquote, urlencode
    import htmlentitydefs
    from cgi import parse_qs, parse_qsl
except ImportError:
    from urllib.request import Request, urlopen
    import urllib.parse as urlparse
    from urllib.parse import quote, unquote, urlencode, parse_qs, parse_qsl
    import html.entities as htmlentitydefs

try:
    import cPickle as pickle
except ImportError:
    import pickle


def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError("Can't load a json library")

    return json

json = import_simplejson()

########NEW FILE########
__FILENAME__ = error
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2010 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 15:15:00 andelf>

class QWeiboError(Exception):
    """basic weibo error class"""
    pass


def assertion(condition, msg):
    try:
        assert condition, msg
    except AssertionError as e:
        raise QWeiboError(e.message)


########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-11-09 10:15:42 wangshuyu>

from qqweibo.utils import (parse_datetime, parse_html_value, parse_a_href,
                           parse_search_datetime, unescape_html)
from qqweibo.error import assertion, QWeiboError


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        del pickle['_api']  # do not pickle the API reference
        return pickle

    def as_dict(self):
        ret = dict(self.__dict__)
        # py3k fixed, in py3k, .keys() will be a dict_keys obj
        for k in list(ret.keys()):
            if k.startswith('_'):
                del ret[k]
            elif k == 'as_dict':
                del ret[k]
        return ret

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of
        model instances."""
        results = ResultSet()
        if json_list:                   # or return empty ResultSet
            for obj in json_list:
                results.append(cls.parse(api, obj))
        return results


class Tweet(Model):

    def __repr__(self):
        return '<Tweet object #%s>' % (self.id or 'unkownID')

    @classmethod
    def parse(cls, api, json):
        if not json:
            return None
        tweet = cls(api)
        for k, v in json.items():
            if k == 'source':
                source = Tweet.parse(api, v)
                setattr(tweet, 'source', source)
            elif k == 'video':
                video = Video.parse(api, v) if v else None
                setattr(tweet, 'video', video)
            elif k in ('isvip', 'self'):
                setattr(tweet, k, bool(v))
            elif k == 'from':
                setattr(tweet, 'from_', v)  # avoid keyword
            elif k == 'tweetid':
                #setattr(tweet, k, v)
                setattr(tweet, 'id', v)
            elif '_' in k:
                # avoid xxxx_xxxx
                setattr(tweet, k.replace('_', ''), v)
            else:
                setattr(tweet, k, v)
        return tweet

    def delete(self):
        if self.self:
            return self._api.t.delete(self.id)
        else:
            raise QWeiboError("You can't delete others' tweet")

    def retweet(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.retweet(content=content, clientip=clientip,
                                   jing=jing, wei=wei, reid=self.id)

    def reply(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.reply(content=content, clientip=clientip, jing=jing,
                                 wei=wei, reid=self.id)

    def comment(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.comment(content=content, clientip=clientip,
                                   jing=jing, wei=wei, reid=self.id)

    def retweetlist(self, *args, **kwargs):
        return self._api.t.retweetlist(self.id, *args, **kwargs)

    def retweetcount(self, *args, **kwargs):
        return self._api.t.retweetcount(self.id, *args, **kwargs)[str(self.id)]

    def favorite(self, fav=True):
        if fav:
            return self._api.fav.addtweet(self.id)
        else:
            return self.unfavorite()

    def unfavorite(self):
        return self._api.fav.deletetweet(self.id)


class Geo(Model):
    """ current useless"""
    @classmethod
    def parse(cls, api, json):
        geo = cls(api)
        if json:
            for k, v in json.items():
                setattr(geo, k, v)
        return geo


class User(Model):

    def __repr__(self):
        return '<User object #%s>' % self.name

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k in ('isvip', 'isent',):
                setattr(user, k, bool(v))
            elif k == 'tag':
                tags = TagModel.parse_list(api, v)
                setattr(user, k, tags)
            elif k in ('Ismyblack', 'Ismyfans', 'Ismyidol'):
                # fix name bug
                setattr(user, k.lower(), bool(v))
            elif k == 'isidol':
                setattr(user, 'ismyidol', bool(v))
            elif '_' in k:
                # avoid xxxx_xxxx
                setattr(user, k.replace('_', ''), v)
            elif k == 'tweet':
                tweet = Tweet.parse_list(api, v)  # only 1 item
                setattr(user, k, tweet[0] if tweet else tweet)
            else:
                setattr(user, k, v)

        # FIXME, need better way
        if hasattr(user, 'ismyidol'):
            setattr(user, 'self', False)  # is this myself?
        else:
            setattr(user, 'self', True)
        # fixture for trends/famouslist
        if hasattr(user, 'account') and not hasattr(user, 'name'):
            setattr(user, 'name', user.account)
        return user

    def update(self, **kwargs):
        assertion(self.self, "you can only update youself's profile")

        nick = self.nick = kwargs.get('nick', self.nick)
        sex = self.sex = kwargs.get('sex', self.sex)
        year = self.birthyear = kwargs.get('year', self.birthyear)
        month = self.birthmonth = kwargs.get('month', self.birthmonth)
        day = self.birthday = kwargs.get('day', self.birthday)
        countrycode = self.countrycode = kwargs.get('countrycode',
                                                    self.countrycode)
        provincecode = self.provincecode = kwargs.get('provincecode',
                                                      self.provincecode)
        citycode = self.citycode = kwargs.get('citycode', self.citycode)
        introduction = self.introduction = kwargs.get('introduction',
                                                      self.introduction)
        self._api.user.update(nick, sex, year, month, day, countrycode,
                              provincecode, citycode, introduction)

    def timeline(self, **kargs):
        return self._api.timeline.user(name=self.name, **kargs)

    def add(self):
        """收听某个用户"""
        assertion(not bool(self.self), "you can't follow your self")
        if self.ismyidol:
            return                      # already flollowed
        else:
            self._api.friends.add(name=self.name)
    follow = add

    def delete(self):
        """取消收听某个用户"""
        assertion(not bool(self.self), "you can't unfollow your self")
        if self.ismyidol:
            self._api.friends.delete(name=self.name)
        else:
            pass
    unfollow = delete

    def addspecial(self):
        """特别收听某个用户"""
        assertion(not bool(self.self), "you can't follow yourself")
        self._api.friends.addspecial(name=self.name)

    def deletespecial(self):
        """取消特别收听某个用户"""
        assertion(not bool(self.self), "you can't follow yourself")
        self._api.friends.deletespecial(name=self.name)

    def addblacklist(self):
        """添加某个用户到黑名单"""
        assertion(not bool(self.self), "you can't block yourself")
        self._api.friends.addblacklist(name=self.name)
    block = addblacklist

    def deleteblacklist(self):
        """从黑名单中删除某个用户"""
        assertion(not bool(self.self), "you can't block yourself")
        self._api.friends.deleteblacklist(name=self.name)
    unblock = deleteblacklist

    def fanslist(self, *args, **kwargs):
        """帐户听众列表, 自己或者别人"""
        if self.self:
            return self._api.friends.fanslist(*args, **kwargs)
        else:
            return self._api.friends.userfanslist(self.name, *args, **kwargs)
    followers = fanslist

    def idollist(self, *args, **kwargs):
        """帐户收听的人列表, 自己或者别人"""
        if self.self:
            return self._api.friends.idollist(*args, **kwargs)
        else:
            return self._api.friends.useridollist(self.name, *args, **kwargs)
    followees = idollist

    def speciallist(self, *args, **kwargs):
        """帐户特别收听的人列表, 自己或者别人"""
        if self.self:
            return self._api.friends.speciallist(*args, **kwargs)
        else:
            return self._api.friends.userspeciallist(self.name, *args, **kwargs)

    def pm(self, content, clientip='127.0.0.1', jing=None, wei=None):
        """发私信"""
        assertion(not bool(self.self), "you can't pm yourself")
        return self._api.private.add(self.name, content, clientip, jing, wei)

    def headimg(self, size=100):
        assertion(size in [20, 30, 40, 50, 100],
                  'size must be one of 20 30 40 50 100')
        return '%s/%s' % (self.head, size)


class JSON(Model):

    def __repr__(self):
        if 'id' in self.__dict__:
            return "<%s object #%s>" % (type(self).__name__, self.id)
        else:
            return object.__repr__(self)

    @classmethod
    def parse(cls, api, json):
        lst = JSON(api)
        for k, v in json.items():
            if k == 'tweetid':
                setattr(lst, k, v)
                setattr(lst, 'id', v)   # make `id` always useable
            else:
                setattr(lst, k, v)
        return lst


class RetId(Model):
    def __repr__(self):
        return "<RetId id:%s>" % self.id

    @classmethod
    def parse(cls, api, json):
        lst = RetId(api)
        for k, v in json.items():
            if k == 'tweetid':
                setattr(lst, k, v)
                setattr(lst, 'id', v)   # make `id` always useable
            elif k == 'time':
                setattr(lst, k, v)
                setattr(lst, 'timestamp', v)
            else:
                setattr(lst, k, v)
        return lst

    def as_tweet(self):
        return self._api.tweet.show(self.id)


class Video(Model):
    def __repr__(self):
        return "<Video object #%s>" % self.realurl

    @classmethod
    def parse(cls, api, json):
        lst = Video(api)
        for k, v in json.items():
            # FIX bug names
            if k == 'real':
                k = 'realurl'
            elif k == 'short':
                k = 'shorturl'
            elif k == 'minipic':
                k = 'picurl'
            setattr(lst, k, v)
        return lst


class TagModel(JSON):
    def __repr__(self):
        return '<Tag object #%s>' % self.id

    @classmethod
    def parse(cls, api, json):
        tag = TagModel(api)
        for k, v in json.items():
                setattr(tag, k, v)
        return tag

    def add(self):
        return self._api.tag.add(self.id)

    def delete(self):
        return self._api.tag.delete(self.id)


class Topic(JSON):
    def __repr__(self):
        return '<Topic object #%s>' % self.id

    @classmethod
    def parse(cls, api, json):
        tag = Topic(api)
        for k, v in json.items():
                setattr(tag, k, v)
        return tag


class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    tweet = Tweet
    user = User
    video = Video
    json = JSON
    retid = RetId

########NEW FILE########
__FILENAME__ = oauth
# Copyright 2007 Leah Culver
# Copyright 2011 andelf <andelf@gmail.com>
# Time-stamp: <2011-06-04 10:08:18 andelf>
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


import time
import random
import hmac
import binascii
# drop support for py2.5-
import hashlib

from qqweibo.compat import (urlparse, quote, unquote, urlencode, parse_qs)
from qqweibo.utils import convert_to_utf8_str


VERSION = '1.0'  # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message


def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def escape(s):
    """Escape a URL including any /.
    return py2str py3str
    """
    # py3k
    if hasattr(str, 'decode') and type(s) != str:
        # FIXME assume py2unicode
        s = s.encode('utf-8')
    ret = quote(s, safe='~')
    if type(ret) != str:
        return str(ret)
    return ret


def _utf8_str(s):
    """Convert unicode to utf-8."""
    if not hasattr(__builtins__, 'unicode'):
        # py3k
        return str(s)
    elif type(s) == getattr(__builtins__, 'unicode'):
        return s.encode("utf-8")
    return str(s)


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either
    an access or request token.

    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urlencode(data)

    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params[b'oauth_callback_confirmed'][0]
        except KeyError:
            pass  # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key
        - oauth_token
        - oauth_signature_method
        - oauth_signature
        - oauth_timestamp
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None  # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.items():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.items():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(convert_to_utf8_str(k)),
                                    escape(convert_to_utf8_str(v))) \
            for k, v in self.parameters.items()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(convert_to_utf8_str(k)),
                       escape(convert_to_utf8_str(v))) \
            for k, v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4]  # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.items():
            parameters[k] = unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)


class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300  # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None  # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')

    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'

    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )
        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        # HMAC object.
        hashed = hmac.new(key.encode('ascii'), raw.encode('ascii'), hashlib.sha1)
        # Calculate the digest base 64.
        #return binascii.b2a_base64(hashed.digest())[:-1]
        # fix py3k, str() on a bytes obj will be a "b'...'"
        ret = binascii.b2a_base64(hashed.digest())[:-1]
        return ret.decode('ascii')


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 23:25:48 andelf>

import xml.dom.minidom as dom
import xml.etree.ElementTree as ET

from qqweibo.compat import json
from qqweibo.models import ModelFactory
from qqweibo.error import QWeiboError


class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, method, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class XMLRawParser(Parser):
    """return string of xml"""
    payload_format = 'xml'

    def parse(self, method, payload):
        return payload

    def parse_error(self, method, payload):
        return payload

class XMLDomParser(XMLRawParser):
    """return xml.dom.minidom object"""
    def parse(self, method, payload):
        return dom.parseString(payload)


class XMLETreeParser(XMLRawParser):
    """return elementtree object"""
    def parse(self, method, payload):
        return ET.fromstring(payload)


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = json

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload, encoding='utf-8')
        except Exception as e:
            print ("Failed to parse JSON payload:" + repr(payload))
            raise QWeiboError('Failed to parse JSON payload: %s' % e)

        return json

    def parse_error(self, method, payload):
        return self.json_lib.loads(payload, encoding='utf-8')


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None:
                return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise QWeiboError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        data = json['data']

        # TODO: add pager
        if 'pagetime' in method.allowed_param:
            pass

        if method.payload_list:
            # sometimes data will be a None
            if data:
                if 'hasnext' in data:
                    # need pager here
                    hasnext = data['hasnext'] in [0, 2]
                    # hasNext:2表示不能往上翻 1 表示不能往下翻，
                    # 0表示两边都可以翻 3表示两边都不能翻了
                else:
                    hasnext = False
                if 'info' in data:
                    data = data['info']
            else:
                hasnext = False
            result = model.parse_list(method.api, data)
            result.hasnext = hasnext
        else:
            result = model.parse(method.api, data)
        return result


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 19:22:59 andelf>

from datetime import datetime
import time
import re
import sys
import random
import os
import mimetypes

from qqweibo.compat import htmlentitydefs


def timestamp():
    return int(time.time()*1000)

def parse_datetime(str):
    # We must parse datetime this way to work in python 2.4
    return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0800 %Y')[0:6]))


def parse_html_value(html):
    return html[html.find('>') + 1:html.rfind('<')]


def parse_a_href(atag):
    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):
    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh
    (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
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
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_unicode(arg):
    """TODO: currently useless"""
    pass


def convert_to_utf8_str(arg):
    # written by andelf ^_^
    # return py2str py3str
    # fix py26
    MAJOR_VERSION = sys.version_info[0]
    if MAJOR_VERSION == 3:
        unicodeType = str
        if type(arg) == unicodeType:
            return arg
        elif type(arg) == bytes:
            return arg.decode('utf-8')
    else:
        unicodeType = __builtins__['unicode']
        if type(arg) == unicodeType:
            return arg.encode('utf-8')
        elif type(arg) == str:
            return arg
    # assume list
    if hasattr(arg, '__iter__'):
        arg = ','.join(map(convert_to_utf8_str, arg))
    return str(arg)


def convert_to_utf8_bytes(arg):
    # return py2str py3bytes
    if type(arg) == bytes:
        return arg
    ret = convert_to_utf8_str(arg)
    return ret.encode('utf-8')


def timestamp_to_str(tm):
    return time.ctime(tm)


def parse_json(payload, encoding='ascii'):
    from .compat import json
    if isinstance(payload, bytes):
        payload = payload.decode(encoding)
    return json.loads(payload)

def mulitpart_urlencode(fieldname, filename, max_size=1024, **params):
    """Pack image from file into multipart-formdata post body"""
    # image must be less than 700kb in size
    try:
        if os.path.getsize(filename) > (max_size * 1024):
            raise QWeiboError('File is too big, must be less than 700kb.')
    except os.error:
        raise QWeiboError('Unable to access file')

    # image must be gif, jpeg, or png
    file_type = mimetypes.guess_type(filename)
    if file_type is None:
        raise QWeiboError('Could not determine file type')
    file_type = file_type[0]
    if file_type.split('/')[0] != 'image':
        raise QWeiboError('Invalid file type for image: %s' % file_type)

    # build the mulitpart-formdata body
    BOUNDARY = 'ANDELF%s----' % ''.join(
        random.sample('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 10))
    body = []
    for key, val in params.items():
        if val is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="%s"' % key)
            body.append('Content-Type: text/plain; charset=UTF-8')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            val = convert_to_utf8_bytes(val)
            body.append(val)
    fp = open(filename, 'rb')
    body.append('--' + BOUNDARY)
    body.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (fieldname, filename.encode('utf-8')))
    body.append('Content-Type: %s' % file_type)
    body.append('Content-Transfer-Encoding: binary')
    body.append('')
    body.append(fp.read())
    body.append('--%s--' % BOUNDARY)
    body.append('')
    fp.close()
    body.append('--%s--' % BOUNDARY)
    body.append('')
    # fix py3k
    for i in range(len(body)):
        body[i] = convert_to_utf8_bytes(body[i])
    body = b'\r\n'.join(body)
    # build headers
    headers = {
        'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
        'Content-Length': len(body)
    }

    return headers, body

########NEW FILE########
__FILENAME__ = secret.sample
apiKey = 'yours'
apiSecret = 'yours'
callbackUrl = 'http://fledna.duapp.com/query'
openid = 'yours'
accessToken = 'yours'

########NEW FILE########
__FILENAME__ = test_pyqqweibo
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  FileName    : test_pyqqweibo.py
#  Author      : Feather.et.ELF <fledna@qq.com>
#  Created     : Wed Jun 08 10:20:57 2011 by Feather.et.ELF
#  Copyright   : Feather Workshop (c) 2011
#  Description : testcast
#  Time-stamp: <2011-06-09 22:18:47 andelf>

from __future__ import unicode_literals
from __future__ import print_function

import sys
import time
from random import randint
import unittest

sys.path.insert(0, '..')
from qqweibo import *
from qqweibo import models


def contenttype_tester(apifunc, reqnum, contenttype, **kwargs):
    # contenttype: content filter
    # FIXME: type1 | type2 not supported
    if contenttype not in [1, 2, 4, 8, 0x10]:
        return
    ret = apifunc(reqnum=reqnum, contenttype=contenttype, **kwargs)
    if not ret:
        print ('No test for contenttype 0x%x' % contenttype)
        return
    if contenttype & 1:
        # Text
        for t in ret:
            assert bool(t.text)
    if contenttype & 2:
        # LINK
        for t in ret:
            # typically works, because all url will be translated
            # to http://url.cn/somewhat
            assert ('http://' in t.origtext) or \
                   (t.source and ('http://' in t.source.origtext))
    if contenttype & 4:
        # IMAGE
        for t in ret:
            assert t.image or (t.source and t.source.image)
    if contenttype & 8:
        # VIDEO
        # BUG: .video sometimes is None
        for t in ret:
            assert t.video or (t.source and t.source.video) or \
                   (('视频' in t.origtext) or \
                    (t.source and ('视频' in t.source.origtext)))
    if contenttype & 0x10:
        # MUSIC
        for t in ret:
            assert t.music or (t.source and t.source.music)
    return True


def test():
    """This Must Pass"""
    pass


def test_get_access_token():
    """TODO: write later"""
    pass
    #assert access_token.key
    #assert access_token.secret
    #auth.get_authorization_url()
    #print (a.get_authorization_url())
#verifier = raw_input('PIN: ').strip()
#access_token = a.get_access_token(verifier)

#token = access_token.key
#tokenSecret = access_token.secret

#print (access_token.key)
#print (access_token.secret)
#auth.setToken(token, tokenSecret)


class QWeiboTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """generate OAuthHandler"""
        import secret
        #auth = OAuthHandler(secret.apiKey, secret.apiSecret)
        auth = OAuth2_0_Handler(secret.apiKey, secret.apiSecret, secret.callbackUrl)


        auth.access_token = secret.accessToken
        auth.openid = secret.openid
        cls.auth = auth


class MemoryCacheTestCase(QWeiboTestCase):
    def test_MemoryCache(self):
        """MemoryCache"""
        api = API(self.auth, cache=MemoryCache())
        ret = api.timeline.home(reqnum=100)
        startTime = time.time()
        ret2 = api.timeline.home(reqnum=100)
        endTime = time.time()
        self.assertEqual(ret[0].id, ret2[0].id)
        self.assertEqual(ret[-1].id, ret2[-1].id)
        self.assertLess(endTime - startTime, 0.01)


class FileCacheTestCase(QWeiboTestCase):
    def setUp(self):
        #super(FileCacheTestCase, self).setUp()
        import tempfile
        self.tmpdir = tempfile.mkdtemp()

    def test_FileCache(self):
        """FileCache"""
        api = API(self.auth, cache=FileCache(self.tmpdir), )
        ret = api.timeline.public(reqnum=100)
        startTime = time.time()
        ret2 = api.timeline.public(reqnum=100)
        endTime = time.time()
        self.assertEqual(ret[0].id, ret2[0].id)
        self.assertEqual(ret[-1].id, ret2[-1].id)
        self.assertLess(endTime - startTime, 0.1)

    def teardown():
        import shutil
        shutil.rmtree(self.tmpdir)


class ParserTestCase(QWeiboTestCase):
    def test_XMLRawParser(self):
        """XMLRawParser"""
        import xml.dom.minidom
        api = API(self.auth, parser=XMLRawParser())
        ret = api.info.update()
        assert len(ret) > 0
        xml.dom.minidom.parseString(ret)

    def test_XMLDomParser(self):
        """XMLDomParser"""
        api = API(self.auth, parser=XMLDomParser())
        ret = api.user.userinfo('andelf')
        assert hasattr(ret, 'getElementsByTagName')
        assert len(ret.getElementsByTagName('nick')) == 1

    def test_XMLETreeParser(self):
        """XMLETreeParser"""
        api = API(self.auth, parser=XMLETreeParser())
        ret = api.user.userinfo('andelf')
        assert hasattr(ret, 'findtext')
        assert ret.findtext('data/nick')

    def test_ModelParser(self):
        """ModelParser"""
        from qqweibo.models import User
        api = API(self.auth, parser=ModelParser())
        ret = api.user.userinfo('andelf')
        assert type(ret) == User
        assert hasattr(ret, 'name')
        api = API(self.auth)
        ret = api.user.userinfo('andelf')
        assert type(ret) == User

    def test_JSONParser(self):
        """JSONParser"""
        api = API(self.auth, parser=JSONParser())
        ret = api.user.userinfo('andelf')
        assert 'msg' in ret
        assert ret['msg'] == 'ok'
        assert 'data' in ret
        assert 'name' in ret['data']


# === API test ===

class APITestCase(QWeiboTestCase):
    @classmethod
    def setUpClass(cls):
        super(APITestCase, cls).setUpClass()
        cls.api = API(cls.auth)


class TimelineAPITestCase(APITestCase):
    def test_home(self):
        """api.timeline.home"""
        api = self.api
        ret = api.timeline.home()
        assert isinstance(ret, list)
        assert len(ret) <= 20
        if len(ret) > 1:
            assert isinstance(ret[0], models.Tweet)

        for ct in [1, 2, 4, 8, 0x10]:
            contenttype_tester(api.timeline.home,
                               reqnum=1,
                               contenttype=ct)

        ret = api.timeline.home(reqnum=100)
        assert len(ret) == 70
        assert ret.hasnext

        num = randint(1, 70)
        ret = api.timeline.home(reqnum=num)
        assert len(ret) == num
        assert ret.hasnext

    def test_public(self):
        """api.timeline.public"""
        api = self.api
        ret = api.timeline.public()
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet

        ret = api.timeline.public()
        assert len(ret) == 20

        ret = api.timeline.public(reqnum=130)
        assert len(ret) == 100

    def test_user(self):
        """api.timeline.user"""
        api = self.api
        ret = api.timeline.user('andelf')
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet
        assert ret[0].name == 'andelf'
        assert ret.hasnext

        for ct in [1, 2, 4, 8, 0x10]:
            contenttype_tester(api.timeline.user,
                                    reqnum=1,
                                    contenttype=ct,
                                    name='andelf')

        ret = api.timeline.user(name='andelf', reqnum=120)
        assert len(ret) == 70
        assert ret.hasnext

        num = randint(1, 70)
        ret = api.timeline.user(name='andelf', reqnum=num)
        assert len(ret) == num
        assert ret.hasnext

    def test_mentions(self):
        """api.timeline.mentions"""
        api = self.api
        ret = api.timeline.mentions()
        username = self.auth.get_username()
        assert 1 < len(ret) <= 20
        assert type(ret[0]) == models.Tweet
        # ugly but works
        # BUG: it also returns retweets of my tweet, no @myusername
        assert (username in ret[0].origtext + ret[0].name) or \
               (ret[0].source and (username in \
                ret[0].source.origtext + ret[0].source.name))

        for ct in [1, 2, 4, 8, 0x10]:
            contenttype_tester(api.timeline.mentions,
                                    reqnum=1,
                                    contenttype=ct)

        ret = api.timeline.mentions(reqnum=120)
        assert len(ret) == 70
        assert ret.hasnext

        ret = api.timeline.mentions(reqnum=64)
        assert len(ret) == 64
        assert ret.hasnext

    def test_topic(self):
        """api.timeline.topic"""
        api = self.api
        ret = api.timeline.topic(httext='这里是辽宁')
        # BUG: 默认为 20, 但大部分情况下即使热门话题, 返回都会少一些
        assert len(ret) <= 20
        assert type(ret[0]) == models.Tweet
        assert '这里是辽宁' in ret[0].origtext
        # BUG: hasnext = 2 not 0
        assert ret.hasnext

        for reqnum in [120, randint(1, 100), randint(1, 100)]:
            ret = api.timeline.topic(httext='毕业', reqnum=reqnum)
            # BUG: this will range from 90 or so to 100
            assert len(ret) <= 100
            # BUG: generally return count will be 0-10 less than reqnum
            assert len(ret) <= reqnum
            assert ret.hasnext
            # NOTE: I don't know why, ask tencent please

    def test_broadcast(self):
        """api.timeline.broadcast"""
        api = self.api
        username = api.user.info().username
        ret = api.timeline.broadcast()
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet
        assert username == ret[0].name

        for ct in [1, 2, 4, 8, 0x10]:
            contenttype_tester(api.timeline.broadcast,
                                    reqnum=1,
                                    contenttype=ct)

        ret = api.timeline.broadcast(reqnum=110)
        assert len(ret) == 70

        num = randint(1, 70)
        ret = api.timeline.broadcast(reqnum=num)
        assert len(ret) == num

    def test_special(self):
        """api.timeline.special"""
        api = self.api
        ret = api.timeline.special()
        assert 1 <= len(ret) <= 20, 'You should add special listen ' \
               'friends to pass this test'
        assert type(ret[0]) == models.Tweet

        ret = api.timeline.special(reqnum=110)
        assert len(ret) == 70

        num = randint(1, 70)
        ret = api.timeline.special(reqnum=num)
        assert len(ret) == num

    def test_area(self):
        """api.timeline.area"""
        api = self.api
        ret = api.timeline.area(country=1, province=44, city=3)
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet
        assert int(ret[0].countrycode) == 1
        assert int(ret[0].provincecode) == 44
        assert int(ret[0].citycode) == 3

        ret = api.timeline.area(country=1, province=44, city=3, reqnum=110)
        assert len(ret) == 100

        num = randint(1, 100)
        ret = api.timeline.area(country=1, province=44, city=3, reqnum=num)
        assert len(ret) == num

    def test_users(self):
        """api.timeline.users"""
        api = self.api
        ret = api.timeline.users(names=['andelf', 'NBA'])
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet
        assert ret[0].name in ['andelf', 'NBA']

        for ct in [1, 2, 4, 8, 0x10]:
            contenttype_tester(api.timeline.users,
                               reqnum=1,
                               contenttype=ct,
                               names=['andelf', 'yinyuetai'])

        # BUG: max reqnum is 40, or Exception raised
        # Update Wed Jun 08 14:35:33 2011:
        # seems fixed
        # Update Wed Jun 08 15:06:24 2011
        # bug again.... 囧rz..
        ret = api.timeline.users(names=['andelf', 'NBA'], reqnum=100)
        assert len(ret) == 70

        num = randint(1, 70)
        ret = api.timeline.users(names=['andelf', 'NBA'], reqnum=num)
        assert len(ret) == num

    def test_homeids(self):
        """api.timeline.homeids"""
        api = self.api
        ret = api.timeline.homeids()
        assert len(ret) == 20
        assert type(ret[0]) == models.RetId
        assert hasattr(ret[0], 'id')
        assert hasattr(ret[0], 'timestamp')

        ret = api.timeline.homeids(reqnum=310)
        assert len(ret) == 300

        num = randint(1, 300)
        ret = api.timeline.homeids(reqnum=num)
        assert len(ret) == num

    def test_userids(self):
        """api.timeline.userids"""
        api = self.api
        ret = api.timeline.userids('andelf')
        assert len(ret) == 20
        assert type(ret[0]) == models.RetId
        assert hasattr(ret[0], 'id')
        assert hasattr(ret[0], 'timestamp')

        # use 腾讯薇薇
        # BUG: return count is less than reqnum
        # and it is not a linear relation..... max 210
        # for e.g. :
        # 60 => 60, 70 => 70, 80 => 70, 90 => 70, 100 => 70
        # 110 => 80, 120 => 90, ... 260 => 200, 181 => 140
        # 141 => 111
        ret = api.timeline.userids(name='t', reqnum=300)
        assert len(ret) == 210

        num = randint(1, 210)
        ret = api.timeline.userids(name='t', reqnum=num)
        assert len(ret) <= num

    def test_broadcastids(self):
        """api.timeline.broadcastids"""
        api = self.api
        ret = api.timeline.broadcastids()
        assert len(ret) == 20
        assert type(ret[0]) == models.RetId
        assert hasattr(ret[0], 'id')
        assert hasattr(ret[0], 'timestamp')

        # BUG: same bug as api.timeline.userids
        ret = api.timeline.broadcastids(reqnum=310)
        assert len(ret) == 210

        num = randint(1, 300)
        ret = api.timeline.broadcastids(reqnum=num)
        assert len(ret) <= num

    def test_mentionsids(self):
        """api.timeline.mentionsids"""
        api = self.api
        ret = api.timeline.mentionsids()
        assert len(ret) == 20
        assert type(ret[0]) == models.RetId
        assert hasattr(ret[0], 'id')
        assert hasattr(ret[0], 'timestamp')

        # BUG: same bug as api.timestamp.userids
        ret = api.timeline.mentionsids(reqnum=300)
        assert len(ret) <= 210

        num = randint(1, 300)
        ret = api.timeline.mentionsids(reqnum=num)
        assert len(ret) <= num

    def test_usersids(self):
        """api.timeline.usersids"""
        api = self.api
        ret = api.timeline.usersids(['andelf', 't', 'NBA'])
        assert len(ret) == 20
        assert type(ret[0]) == models.RetId
        assert hasattr(ret[0], 'id')
        assert hasattr(ret[0], 'timestamp')

        ret = api.timeline.usersids(names=['andelf', 't', 'NBA'], reqnum=310)
        assert len(ret) == 300

        num = randint(1, 300)
        ret = api.timeline.usersids(names=['andelf', 't', 'NBA'], reqnum=num)
        assert len(ret) == num

# part 2
test_ids = []


class TweetAPITestCase(APITestCase):
    def test_show(self):
        """api.tweet.show"""
        api = self.api
        id = api.timeline.homeids(reqnum=1)[0].id
        ret = api.tweet.show(id)
        assert type(ret) == models.Tweet
        assert ret.id == id

    def test_add(self):
        """api.tweet.add"""
        api = self.api
        ret = api.tweet.add("#pyqqweibo# unittest auto post."
                            "will be delete later %d" % randint(0, 100),
                            clientip='127.0.0.1',
                            jing=123.422889,
                            wei=41.76627
                            )
        assert type(ret) == models.RetId
        assert hasattr(ret, 'id')
        assert hasattr(ret, 'timestamp')
        test_ids.append(ret.id)

        t = ret.as_tweet()              # also show
        assert t.id == ret.id
        assert 'pyqqweibo' in t.origtext
        assert t.type == 1
        # not implemented yet
        assert not bool(t.geo)

    def test_delete(self):
        """api.tweet.delete"""
        # delete in others
        pass

    def test_retweet(self):
        """api.tweet.retweet"""
        api = self.api
        target_id = test_ids[0]
        ret = api.tweet.retweet(reid=target_id,
                                content="test retweet %d" % randint(0, 100),
                                clientip='127.0.0.1'
                                )
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert t.id == ret.id
        assert t.source.id == target_id
        assert t.type == 2
        assert 'retweet' in t.origtext

    def test_reply(self):
        """api.tweet.reply"""
        api = self.api
        target_id = test_ids[0]
        ret = api.tweet.reply(reid=target_id,
                              content="测试回复 %d" % randint(0, 100),
                              clientip='127.0.0.1'
                              )
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert t.id == ret.id
        assert t.source.id == target_id
        assert t.type == 4
        assert '回复' in t.origtext

    def test_addpic(self):
        """api.tweet.addpic"""
        api = self.api
        ret = api.tweet.addpic("f:/tutu.jpg",
                               "TOO~~~",
                               '127.0.0.1')
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert hasattr(t, 'image')
        assert len(t.image) == 1
        assert 'TOO' in t.origtext

    def test_retweetcount(self):
        """apt.tweet.retweetcount"""
        api = self.api
        ret = api.tweet.retweetcount(ids=[79504073889068,
                                          36575045593232])
        assert type(ret) == models.JSON
        data = ret.as_dict()
        assert '79504073889068' in data
        count = data['79504073889068']
        assert count > 0

        ret0 = api.tweet.retweetcount(ids=79504073889068,
                                     flag=0)
        count0 = ret0.as_dict()['79504073889068']
        assert count0 > 0
        # in some senconds
        assert count0 - 10 <= count <= count0

        ret1 = api.tweet.retweetcount(ids=79504073889068,
                                     flag=1)
        count1 = ret1.as_dict()['79504073889068']
        assert count1 > 0

        ret2 = api.tweet.retweetcount(ids=79504073889068,
                                     flag=2)
        count2 = ret2.as_dict()['79504073889068']
        # {u'count': 16511, u'mcount': 294}
        assert 'count' in count2
        assert 'mcount' in count2

        assert count2['count'] - 5 <= count <= count2['count']
        assert count2['mcount'] - 5 <= count1 <= count2['mcount']

    def test_retweetlist(self):
        """api.tweet.retweetlist"""
        api = self.api
        ret = api.tweet.retweetlist(rootid='79504073889068')
        assert len(ret) == 20
        assert type(ret[0]) == models.Tweet
        assert ret[0].source.id == '79504073889068'
        assert ret.hasnext

        ret = api.tweet.retweetlist(rootid='79504073889068',
                                    reqnum=120)
        assert len(ret) == 100

        num = randint(1, 100)
        ret = api.tweet.retweetlist(rootid='79504073889068',
                                    reqnum=num)
        assert len(ret) == num

    def test_comment(self):
        """api.tweet.comment"""
        api = self.api
        target_id = test_ids[0]
        ret = api.tweet.comment(reid=target_id,
                                content="测试评论 %d" % randint(0, 100),
                                clientip='127.0.0.1'
                                )
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert t.id == ret.id
        assert t.source.id == target_id
        assert t.type == 7
        assert '评论' in t.origtext

    def test_addmusic(self):
        """api.tweet.addmusic"""
        return
        api = self.api
        ret = api.tweet.addmusic(url='',
                                 title='',
                                 author='',
                                 content='Song',
                                 clientip='127.0.0.1')
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert hasattr(t, 'music')
        assert bool(t.music)
        assert 'Song' in t.origtext

    def test_addvideo(self):
        """api.tweet.addvideo"""
        return
        api = self.api
        ret = api.tweet.addvideo(url='',
                                 content='Video',
                                 clientip='127.0.0.1')
        assert type(ret) == models.RetId
        test_ids.append(ret.id)

        t = ret.as_tweet()
        assert hasattr(t, 'video')
        assert bool(t.video)
        assert type(t.video) == models.Video
        assert 'Video' in t.origtext

    def test_list(self):
        """api.tweet.list"""
        api = self.api
        ret = api.tweet.list(ids=[79504073889068,
                                  36575045593232])
        assert len(ret) == 2
        assert type(ret[0]) == models.Tweet

        assert not ret.hasnext

        for t in ret:
            assert t.id in ['79504073889068', '36575045593232']


class UserAPITestCase(APITestCase):
    def test_info(self):
        """api.user.info"""
        api = self.api
        ret = api.user.info()
        assert type(ret) == models.User

    def test_update(self):
        """api.user.update"""
        api = self.api
        ret = api.user.info()
        old_intro = ret.introduction

        ret.introduction = '#pyqqweibo# powered!'
        ret.update()                    # use model interface
        ret = api.user.info()

        assert ret.introduction == '#pyqqweibo# powered!'
        ret.introduction = old_intro
        ret.update()

    def test_updatehead(self):
        """api.user.updatehead"""
        # TODO: implement this
        api = self.api

    def test_userinfo(self):
        """api.user.userinfo"""
        api = self.api
        ret = api.user.userinfo(name='t')
        assert type(ret) == models.User
        assert ret.name == 't'

class FriendsAPITestCase(APITestCase):
    def test_fanslist(self):
        """api.friends.fanslist"""
        api = self.api
        ret = api.friends.fanslist()
        assert len(ret) == 30
        assert type(ret[0]) == models.User
        assert ret.hasnext

        fansnum  = api.user.info().fansnum
        ret = api.friends.fanslist(startindex=fansnum-1)
        assert not ret.hasnext

        ret = api.friends.fanslist(reqnum=100)
        assert len(ret) == 30

        num = randint(1, 30)
        ret = api.friends.fanslist(reqnum=num)
        assert len(ret) == num

    def test_idollist(self):
        """api.friends.idollist"""
        api = self.api
        ret = api.friends.idollist()
        assert len(ret) == 30
        assert type(ret[0]) == models.User
        assert ret.hasnext

        idolnum  = api.user.info().idolnum
        ret = api.friends.idollist(startindex=idolnum-1)
        assert not ret.hasnext

        ret = api.friends.idollist(reqnum=100)
        assert len(ret) == 30

        num = randint(1, 30)
        ret = api.friends.idollist(reqnum=num)
        assert len(ret) == num

    def test_blacklist(self):
        """api.friends.blacklist"""
        api = self.api
        ret = api.friends.blacklist()
        assert len(ret) > 0, "add someone to blacklist to pass test"
        assert type(ret[0]) == models.User

    def test_speciallist(self):
        """api.friends.speciallist"""
        api = self.api
        ret = api.friends.speciallist()
        assert len(ret) > 0, "add someone to special list to pass test"
        assert type(ret[0]) == models.User

    def test_add(self):
        """api.friends.add"""
        api = self.api
        ret = api.friends.add(name='fledna')
        assert ret is None

        info = api.user.userinfo(name='fledna')
        assert info.ismyidol

    def test_delete(self):
        """api.friends.delete"""
        api = self.api
        ret = api.friends.delete(name='t')
        assert ret is None

        info = api.user.userinfo(name='t')
        assert not info.ismyidol

        try:
            # BUG: will cause errcode=65. reason unkown
            api.friends.add(name='t')
        except:
            pass

    def test_addspecial(self):
        """api.friends.addspecial"""
        api = self.api
        ret = api.friends.addspecial('t')
        assert ret is None

    def test_deletespecial(self):
        """api.friends.deletespecial"""
        api = self.api
        try:
            ret = api.friends.add('t')
            ret = api.friends.addspecial('t')
        except:
            pass
        ret = api.friends.deletespecial('t')
        assert ret is None

    def test_addblacklist(self):
        """api.friends.addblacklist"""
        api = self.api
        ret = api.friends.addblacklist(name='t')
        assert ret is None

        info = api.user.userinfo(name='t')
        assert info.ismyblack

    def test_deleteblacklist(self):
        """api.friends.deleteblacklist"""
        api = self.api
        ret = api.friends.deleteblacklist(name='t')
        assert ret is None

        info = api.user.userinfo(name='t')
        assert not info.ismyblack

    def test_check(self):
        """self.friends.check"""
        api = self.api
        ret = api.friends.check(names=['t', 'andelf', 'NBA'])
        assert type(ret) == models.JSON

        assert type(ret.t) == bool
        assert type(ret.as_dict()['andelf']) == bool

    def test_userfanslist(self):
        """api.friends.userfanslist"""
        api = self.api
        ret = api.friends.userfanslist('NBA')
        assert len(ret) == 30
        assert type(ret[0]) == models.User
        assert ret.hasnext

        # BUG: if too large, cause ret=4, errcode=0
        fansnum  = api.user.userinfo('NBA').fansnum
        ret = api.friends.userfanslist('NBA', startindex=fansnum-1)
        assert not ret.hasnext

        ret = api.friends.userfanslist('NBA', reqnum=100)
        assert len(ret) == 30

        num = randint(1, 30)
        ret = api.friends.userfanslist('NBA', reqnum=num)
        assert len(ret) == num

    def test_useridollist(self):
        """api.friends.useridollist"""
        api = self.api
        ret = api.friends.useridollist('andelf')
        assert len(ret) == 30
        assert type(ret[0]) == models.User
        assert ret.hasnext

        idolnum  = api.user.userinfo('andelf').idolnum
        ret = api.friends.useridollist('andelf', startindex=idolnum-1)
        assert not ret.hasnext

        ret = api.friends.useridollist('andelf', reqnum=100)
        assert len(ret) == 30

        num = randint(1, 30)
        ret = api.friends.useridollist('andelf', reqnum=num)
        assert len(ret) == num

    def test_userspeciallist(self):
        """api.friends.userspeciallist"""
        api = self.api

        ret = api.friends.useridollist('andelf')
        assert len(ret) > 0
        assert type(ret[0]) == models.User
        if len(ret)< 30:
            assert not ret.hasnext



if __name__ == '__main__':
    unittest.main(verbosity=2)
    #suite = unittest.TestLoader().loadTestsFromTestCase(FriendsAPITestCase)
    #unittest.TextTestRunner(verbosity=2).run(suite)

if 1:
    print ('\nbegin clean up...')
    APITestCase.setUpClass()
    for i in test_ids:
        ret = APITestCase.api.tweet.delete(i)
        print ('delete id={}'.format(i))
        assert ret.id == i

########NEW FILE########
