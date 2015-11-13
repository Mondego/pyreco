__FILENAME__ = api
#coding: utf-8
import time
import sys
import webob
import webob.exc
import util
import config
import globals as g
from user import *
from news import *


def signup(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    if config.InviteOnlySignUp:
        invitecode = request.POST.get('invitecode')

    username, msg = util.check_string(username, 2, 20, config.UsernameChars)
    if not username:
        result = {
            'status': 'error',
            'error': 'username ' + msg
            }
        return util.json_response(result)

    password, msg = util.check_string(password, config.PasswordMinLength)
    if not password:
        result = {
            'status': 'error',
            'error': 'password ' + msg
            }
        return util.json_response(result)

    r = g.redis

    if config.InviteOnlySignUp:
        #race condition here.
        if not r.sismember('invite.code', invitecode):
            result = {
            'status': 'error',
            'error': 'invalid invitation code',
            }
            return util.json_response(result)

        #mark as used
        r.smove('invite.code', 'invite.code.used', invitecode)

    #XXX proxied requests have the same REMOTE_ADDR
    auth, msg = create_user(username, password, request.environ['REMOTE_ADDR'])
    if not auth:
        result = {
            'status': 'error',
            'error': msg,
            }
    else:
        result = {
            'status': 'ok',
            'auth': auth,
            }
    return util.json_response(result)


def login(request):
    username = request.GET.get('username')
    password = request.GET.get('password')

    username, msg = util.check_string(username, 2, 20)
    if not username:
        result = {
            'status': 'error',
            'error': 'username ' + msg
            }
        return util.json_response(result)

    password, msg = util.check_string(password)
    if not password:
        result = {
            'status': 'error',
            'error': 'password ' + msg
            }
        return util.json_response(result)

    auth, apisecret = check_user_credentials(username, password)

    if auth:
        result = {
            'status': 'ok',
            'auth': auth,
            'apisecret': apisecret
            }

    else:
        result = {
            'status': 'error',
            'error': 'bad username/password',
            }

    return util.json_response(result)


def logout(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        apisecret = request.POST.get('apisecret')
        if apisecret == g.user["apisecret"]:
            update_auth_token(g.user)
            return util.json_response({'status': 'ok'})

    result = {'status': 'error',
              'error': 'Wrong auth credentials or API secret.'
              }
    return util.json_response(result)


#submit news or edit news
def submit(request):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        result = {'status': 'error',
                  'error': 'Not authenticated.'
                  }
        return util.json_response(result)

    if request.POST.get('apisecret') != g.user["apisecret"]:
        result = {'status': 'error',
                  'error': 'Wrong form secret'
                  }
        return util.json_response(result)

    title = request.POST.get('title')
    url = request.POST.get('url')
    text = request.POST.get('text')
    news_id = util.force_int(request.POST.get('news_id'))

    if text:
        text = text.lstrip('\r\n').rstrip()

    if not title or (not url and not text):
        result = {'status': 'error',
                  'error': 'title and (url or text) required'
                  }
        return util.json_response(result)

    # Make sure the URL is about an acceptable protocol, that is
    # http:// or https:// for now.
    if url and not url.startswith('http://') and not url.startswith('https://'):
        result = {'status': 'error',
                  'error': 'we only accept http:// and https:// news'
                  }
        return util.json_response(result)

    if len(title) > config.MaxTitleLen or len(url) > config.MaxUrlLen:
        result = {'status': 'error',
                  'error': 'title or url too long'
                  }
        return util.json_response(result)

    if not url and len(text) > config.CommentMaxLength:
        result = {'status': 'error',
                  'error': 'text too long'
                  }
        return util.json_response(result)

    if news_id is None:
        result = {'status': 'error',
                  'error': 'bad news_id'
                  }
        return util.json_response(result)

    if news_id == -1:
        if limit.submitted_recently():
            result = {'status': 'error',
                      'error': "You have submitted a story too recently, " +
                      "please wait %s seconds." % limit.allowed_to_post_in_seconds()
                      }
            return util.json_response(result)

        news_id = insert_news(title, url, text, g.user['id'])

    else:
        news_id = edit_news(news_id, title, url, text, g.user['id'])
        if not news_id:
            result = {'status': 'error',
                      'error': 'Invalid parameters, news too old to be modified' +
                      'or url recently posted.'
                      }
            return util.json_response(result)

    result = {'status': 'ok',
              'news_id': int(news_id)
              }

    return util.json_response(result)


def delete_news(request):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        result = {'status': 'error',
                  'error': 'Not authenticated.'
                  }
        return util.json_response(result)

    if request.POST.get('apisecret') != g.user["apisecret"]:
        result = {'status': 'error',
                  'error': 'Wrong form secret'
                  }
        return util.json_response(result)

    news_id = util.force_int(request.POST.get('news_id'))
    if not news_id:
        result = {'status': 'error',
                  'error': 'bad news_id'
                  }
        return util.json_response(result)

    if del_news(news_id, g.user['id']):
        result = {'status': 'ok',
                  'news_id': -1
                  }
        return util.json_response(result)

    result = {'status': 'err',
              'error': 'News too old or wrong ID/owner.'
              }

    return util.json_response(result)


def update_profile(request):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        result = {'status': 'error',
                  'error': 'Not authenticated.'
                  }
        return util.json_response(result)

    if request.POST.get('apisecret') != g.user["apisecret"]:
        result = {'status': 'error',
                  'error': 'Wrong form secret'
                  }
        return util.json_response(result)


    password = request.POST.get('password')    #optinal
    email = request.POST.get('email')
    about = request.POST.get('about')

    email, msg = util.check_string(email, maxlen=128)
    if email is None:
        result = {
            'status': 'error',
            'error': 'email ' + msg
            }
        return util.json_response(result)

    about, msg = util.check_string(about, maxlen=256)
    if about is None:
        result = {
            'status': 'error',
            'error': 'about ' + msg
            }
        return util.json_response(result)

    r = g.redis

    if password:
        password, msg = util.check_string(password, config.PasswordMinLength)
        if not password:
            result = {
                'status': 'error',
                'error': 'password ' + msg
                }
            return util.json_response(result)

        salt = g.user.get('salt', util.get_rand())
        r.hmset("user:" + g.user['id'], {
                "password": util.hash_password(password, salt),
                "salt": salt
                })

    r.hmset("user:" + g.user['id'], {
            "about": about.rstrip(),
            "email": email
            })
    return util.json_response({'status': "ok"})


def vote_news(request):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        result = {'status': 'error',
                  'error': 'Not authenticated.'
                  }
        return util.json_response(result)

    if request.POST.get('apisecret') != g.user["apisecret"]:
        result = {'status': 'error',
                  'error': 'Wrong form secret'
                  }
        return util.json_response(result)

    news_id = util.force_int(request.POST.get('news_id'))
    vote_type = request.POST.get('vote_type')
    if not news_id or (vote_type != 'up' and vote_type != 'down'):
        result = {'status': 'error',
                  'error': 'Missing news ID or invalid vote type.'
                  }
        return util.json_response(result)

    # Vote the news
    karma, error = do_vote_news(news_id, vote_type)
    if karma:
        return util.json_response({"status": "ok" })
    else:
        return util.json_response({"status": "error" })

########NEW FILE########
__FILENAME__ = app
import urllib
import hashlib
import sys
import re
import webob
import webob.exc
import url
import util

from user import *
from news import *
import globals as g

urlmapping = []

def compile_url_pattern(url_mapping):
    for m in url_mapping:
        urlmapping.append((re.compile(m[0]), m[1]))

def get_handler(request_url):
    for m in urlmapping:
        match = m[0].match(request_url)
        if match:
            module_name, method_name = m[1].rsplit('.', 1)
            try:
                module = __import__(module_name, globals(), locals(), [method_name])
            except ImportError as e:
                return
            try:
                return getattr(module, method_name), match.groups()
            except AttributeError as e:
                return


compile_url_pattern(url.url_mapping)

def application(environ, start_response):
    request_url = environ['PATH_INFO']

    request = webob.Request(environ)
    h = get_handler(request_url)

    if not h:
        #404
        response = webob.exc.HTTPNotFound()
    else:
        g.init()
        handler, param = h
        response = handler(request, *param)

    return response(environ, start_response)


def login(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        return util.redirect('/')
    else:
        return util.render('login.pat')


def signup(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        return util.redirect('/')

    return util.render('signup.pat', invite=config.InviteOnlySignUp)


def logout(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        apisecret = request.GET.get('apisecret')
        if apisecret == g.user["apisecret"]:
            update_auth_token(g.user)

    return util.redirect("/")


def submit(request):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        return util.redirect('/login')
    else:
        return util.render('submit.pat', user=g.user,
                           title=request.GET.get('t', ''),
                           url=request.GET.get('u', ''))

#top news page
def top(request):
    auth_user(request.cookies.get('auth'))
    news, total = get_top_news()
    hack_news(news)
    return util.render('top.pat', news=news, user=g.user)


def index(request):
    return latest(request)


def latest(request, start=None):
    auth_user(request.cookies.get('auth'))

    if not start:
        start = 0
    else:
        try:
            #/200
            start = int(start[1:])
        except ValueError:
            start = 0
        if start < 0:
            start = 0

    news, total = get_latest_news(start)
    hack_news(news)

    next = None
    if total > start + config.LatestNewsPerPage:
        next = start + config.LatestNewsPerPage
    return util.render('latest.pat', news=news, user=g.user,
                       start=start, next=next)


def newspage(request, news_id):
    auth_user(request.cookies.get('auth'))
    news = get_news_by_id(news_id)
    if not news:
        return util.render('error.pat', user=g.user,
                           error="the news does not exist")

    hack_news(news)
    return util.render('news.pat', user=g.user, news=news)


def userpage(request, username):
    auth_user(request.cookies.get('auth'))

    user = get_user_by_name(username)
    if not user:
        return util.render('error.pat', user=g.user,
                           error='the user does not exist')

    user['created'] = "%s days ago" % int((time.time() - int(user['ctime'])) / (3600*24))

    #http://en.gravatar.com/site/implement/images/
    user['gravatar'] = "http://www.gravatar.com/avatar/" + \
        hashlib.md5(user['email'].lower()).hexdigest() + "?" + \
        "d=mm&"

    r = g.redis
    user['posted'] = r.zcard("user.posted:" + user['id'])
    user['saved'] = r.zcard("user.saved:" + user['id'])
    user['posted_comments'] = r.zcard("user.comments:" + user['id'])
    return util.render('user.pat', user=g.user, userinfo=user)


def about(request):
    auth_user(request.cookies.get('auth'))
    return util.render('about.pat', user=g.user)


def editnews(request, news_id):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        return util.render('error.pat', user=g.user,
                           error='you have to login first')

    news = get_news_by_id(news_id)
    if not news:
        return util.render('error.pat', user=g.user,
                           error='the news does not exist')

    if news.get('del'):
        return util.render('error.pat', user=g.user,
                           error='news deleted')

    if news['user_id'] != g.user['id']:
        return util.render('error.pat', user=g.user,
                           error='permission denied')

    hack_news(news)
    return util.render('editnews.pat', user=g.user, news=news)


def comments(request):
    auth_user(request.cookies.get('auth'))
    return util.render('comments.pat', user=g.user)


def rss(request):
    news, total = get_latest_news()
    hack_news(news)

    return util.render('rss.pat', news=news)


def saved(request, start=None):
    auth_user(request.cookies.get('auth'))
    if not g.user:
        return util.render('error.pat', error='you need to login first')

    if not start:
        start = 0
    else:
        try:
            #/200
            start = int(start[1:])
        except ValueError:
            start = 0
        if start < 0:
            start = 0

    news, total = get_saved_news(g.user['id'], start, config.SavedNewsPerPage)
    hack_news(news)

    next = None
    if total > start + config.SavedNewsPerPage:
        next = start + config.SavedNewsPerPage
    return util.render('saved.pat', news=news, user=g.user,
                       start=start, next=next)


def lusers(request):
    auth_user(request.cookies.get('auth'))

    users = get_new_users(10)
    return util.render('lusers.pat', users=users, user=g.user)

########NEW FILE########
__FILENAME__ = config
import string

# Redis config
RedisHost = "127.0.0.1"
RedisPort = 6379

# Security
PBKDF2Iterations = 5000 # Set this to 5000 to improve security. But it is slow.
PasswordMinLength = 6
CreateUserRate = 3600

# limit
#[a-zA-Z_]
UsernameChars =  string.letters + string.digits + '-'
MaxTitleLen = 100
MaxUrlLen = 256


# Karma
UserInitialKarma = 1
KarmaIncrementInterval = 3*3600
KarmaIncrementAmount = 1
NewsDownvoteMinKarma = 30
NewsDownvoteKarmaCost = 6
NewsUpvoteMinKarma = 0
NewsUpvoteKarmaCost = 1
NewsUpvoteKarmaTransfered = 1
KarmaIncrementComment = 1


# Comments
CommentMaxLength = 4096
DisqusName = 'example'   #replace it with your forum shortname

# News and ranking
NewsAgePadding = 100
TopNewsPerPage = 30
LatestNewsPerPage = 30
NewsEditTime = 60*30
NewsScoreLogStart = 10
NewsScoreLogBooster = 2
RankAgingFactor = 1.6
PreventRepostTime = 3600*48
NewsSubmissionBreak = 10
SavedNewsPerPage = 30
TopNewsAgeLimit = 60*72

# path
HomePath = "~/lusernews2/"

TemplatesPath = "templates"
StaticPath = "static"

#Logging
LogFile = "logs/error.log"
LogLevel = "DEBUG"

PidFile = "logs/luser.pid"

#
InviteOnlySignUp = False

# e.g. UA-29222488-1
GoogleAnalytics = ""

github_client_id = "ZZZ"
github_secret = 'top-secret'
github_callback_url = 'http://example.com/oauth/github/callback'


########NEW FILE########
__FILENAME__ = github
import json
import webob
import oauth2  #requires httplib2 0.6
import util
import config
import globals as g
from user import *


# github:login -> id
#

oauth_settings = {
    'client_id': config.github_client_id,
    'client_secret': config.github_secret,
    'base_url': 'https://github.com/login/oauth/',
    'redirect_url': config.github_callback_url,
}

def auth(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        return util.redirect('/')

    oauth_client = oauth2.Client2(
        oauth_settings['client_id'],
        oauth_settings['client_secret'],
        oauth_settings['base_url']
        )
    authorization_url = oauth_client.authorization_url(
        redirect_uri = oauth_settings['redirect_url'],
        # params={'scope': 'user'}
        )
    return util.redirect(authorization_url)


# this function is slow
def callback(request):
    auth_user(request.cookies.get('auth'))
    if g.user:
        return util.redirect('/')

    oauth_client = oauth2.Client2(
        oauth_settings['client_id'],
        oauth_settings['client_secret'],
        oauth_settings['base_url']
        )

    code = request.GET.get('code')
    if not code:
        return util.render('error.pat', user=None,
                           error="no code")

    try:
        data = oauth_client.access_token(code, oauth_settings['redirect_url'])
    except Exception as e:
        return util.render('error.pat', user=None,
                           error="failed to get access token, try again")
    access_token = data.get('access_token')

    (headers, body) = oauth_client.request(
        'https://api.github.com/user',
        access_token=access_token,
        token_param='access_token'
        )

    error = 0
    try:
        if headers['status'] == '200':
            user = json.loads(body)
            username = user['login']
            email = user.get('email', '')
        else:
            error = 1
    except Exception as e:
        error = 1

    if error:
        return util.render('error.pat', user=None, error='bad login, try again')

    user = get_user_by_name(username)
    if not user:
        #create new user
        auth, msg = create_user_github(username, email)
        if not auth:
            return util.render('error.pat', user=None, error=msg)
    else:
        if 'g' in user['flags']:
            auth = user['auth']
        else:
            return util.render('error.pat', user=None, error='account exists :(')

    res = webob.exc.HTTPTemporaryRedirect(location='/')
    res.headers['Set-Cookie'] = 'auth=' + auth + \
        '; expires=Thu, 1 Aug 2030 20:00:00 UTC; path=/';
    return res


# Create a new user with github login name
#
# Return value: the function returns two values, the first is the
#               auth token if the registration succeeded, otherwise
#               is nil. The second is the error message if the function
#               failed (detected testing the first return value).
def create_user_github(username, email):
    r = g.redis
    username = username.lower()

    if r.exists("username.to.id:" + username):
        return None, "Username exists, please try a different one."

    if not util.lock('create_user.' + username):
        return None, "Please wait some time before creating a new user."

    user_id = r.incr("users.count")
    auth_token = util.get_rand()
    now = int(time.time())

    pl = r.pipeline()
    pl.hmset("user:%s" % user_id, {
            "id": user_id,
            "username": username,
            "ctime": now,
            "karma": config.UserInitialKarma,
            "about": "",
            "email": email,
            "auth": auth_token,
            "apisecret": util.get_rand(),
            "flags": "g", #github user
            "karma_incr_time": now,
            "replies": 0,
            })

    pl.set("username.to.id:" + username, user_id)
    pl.set("auth:" + auth_token, user_id)

    pl.execute()
    util.unlock('create_user.' + username)

    return auth_token, None


########NEW FILE########
__FILENAME__ = globals
import jinja2
from redis import StrictRedis
import config

redis = None
user = None
jj = None


def init():
    global redis, user, jj
    redis = StrictRedis(config.RedisHost, config.RedisPort)
    user = None

    loader = jinja2.FileSystemLoader(config.TemplatesPath)
    jj = jinja2.Environment(loader=loader)



########NEW FILE########
__FILENAME__ = limit
import config
import globals as g

# Has the user submitted a news story in the last `NewsSubmissionBreak` seconds?
def submitted_recently():
    return allowed_to_post_in_seconds() > 0

# Indicates when the user is allowed to submit another story after the last.
def allowed_to_post_in_seconds():
    return g.redis.ttl('user:%s:submitted_recently' % g.user['id'])


# Generic API limiting function
def rate_limit_by_ip(delay, *tags):
    r = g.redis
    key = "limit:" + ".".join(tags)
    if r.exists(key):
        return True
    r.setex(key, delay, 1)
    return False

########NEW FILE########
__FILENAME__ = main
import os
import sys
import logging

from scgiwsgi import WSGIServer
from app import application

import config

pid = None

def write_pid_file():
    global pid
    pid = os.getpid()
    f = open(config.PidFile, 'w')
    f.write(str(pid) + '\n')
    f.close()

def remove_pid_file():
    if os.getpid() != pid:
        return
    try:
        os.unlink(config.PidFile)
    except OSError:
        pass

try:
    os.chdir(os.path.expanduser(config.HomePath))
    write_pid_file()
    logging.basicConfig(filename=config.LogFile,
                        level=getattr(logging, config.LogLevel),
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger()

    WSGIServer(application, logger).run(port=7778)
except KeyboardInterrupt:
    pass

finally:
    remove_pid_file()

########NEW FILE########
__FILENAME__ = news
import time
import config
import util
import globals as g
from user import increment_user_karma_by


# Add a news with the specified url or text.
#
# If an url is passed but was already posted in the latest 48 hours the
# news is not inserted, and the ID of the old news with the same URL is
# returned.
#
# Return value: the ID of the inserted news, or the ID of the news with
# the same URL recently added.
def insert_news(title, url, text, user_id):
    r = g.redis
    # If we don't have an url but a comment, we turn the url into
    # text://....first comment..., so it is just a special case of
    # title+url anyway.
    textpost = not url
    if textpost:
        url = "text://" + text[0:config.CommentMaxLength]

    # Check for already posted news with the same URL.
    nid = r.get("url:" + url)
    if not textpost and nid:
        return int(nid)
    # We can finally insert the news.
    ctime = int(time.time())
    news_id = r.incr("news.count")
    r.hmset("news:%s" % news_id, {
            "id": news_id,
            "title": title,
            "url": url,
            "user_id": user_id,
            "ctime": ctime,
            "score": 0,
            "rank": 0,
            "up": 0,
            "down": 0,
            "comments": 0
            })

    # The posting user virtually upvoted the news posting it
    rank, error = do_vote_news(news_id, 'up')
    # Add the news to the user submitted news
    r.zadd("user.posted:%s" % user_id, ctime, news_id)
    # Add the news into the chronological view
    r.zadd("news.cron", ctime, news_id)
    # Add the news into the top view
    r.zadd("news.top", rank, news_id)
    # Add the news url for some time to avoid reposts in short time
    if not textpost:
        r.setex("url:" + url, config.PreventRepostTime, news_id)
    # Set a timeout indicating when the user may post again
    if config.NewsSubmissionBreak > 0:
        r.setex("user:%s:submitted_recently" % user_id, config.NewsSubmissionBreak, '1')
    return news_id


# Edit an already existing news.
#
# On success the news_id is returned.
# On success but when a news deletion is performed (empty title) -1 is returned.
# On failure (for instance news_id does not exist or does not match
#             the specified user_id) false is returned.
def edit_news(news_id, title, url, text, user_id):
    news = get_news_by_id(news_id)
    if not news or news.get('del') or int(news['user_id']) != int(user_id):
        return False

    if not int(news['ctime']) > (time.time() - config.NewsEditTime):
        return False

    # If we don't have an url but a comment, we turn the url into
    # text://....first comment..., so it is just a special case of
    # title+url anyway.
    textpost = not url
    if textpost:
        url = "text://" + text[0:config.CommentMaxLength]

    r = g.redis
    # Even for edits don't allow to change the URL to the one of a
    # recently posted news.
    if not textpost and url != news['url']:
        if r.get("url:" + url):
            return False
        # No problems with this new url, but the url changed
        # so we unblock the old one and set the block in the new one.
        # Otherwise it is easy to mount a DOS attack.
        r.delete("url:" + news['url'])
        r.setex("url:" + url, config.PreventRepostTime, news_id)

    # Edit the news fields.
    r.hmset("news:%s" % (news_id),
            {"title": title,
            "url": url})
    return news_id


# Mark an existing news as removed.
def del_news(news_id, user_id):
    news = get_news_by_id(news_id)
    if not news or news.get('del') or int(news['user_id']) != int(user_id):
        return False

    if not int(news['ctime']) > (time.time() - config.NewsEditTime):
        return False

    r = g.redis.pipeline()
    r.hset("news:%s" % (news_id), "del", 1)
    r.zrem("news.top", news_id)
    r.zrem("news.cron", news_id)
    r.execute()
    return True


# Vote the specified news in the context of a given user.
# type is either :up or :down
#
# The function takes care of the following:
# 1) The vote is not duplicated.
# 2) That the karma is decreased from voting user, accordingly to vote type.
# 3) That the karma is transfered to the author of the post, if different.
# 4) That the news score is updaed.
#
# Return value: two return values are returned: rank,error
#
# If the fucntion is successful rank is not nil, and represents the news karma
# after the vote was registered. The error is set to nil.
#
# On error the returned karma is false, and error is a string describing the
# error that prevented the vote.
def do_vote_news(news_id, vote_type):
    # Fetch news and user
    r = g.redis
    user = g.user
    news = get_news_by_id(news_id)
    if not news:
        return False, "No such news."

    # Now it's time to check if the user already voted that news, either
    # up or down. If so return now.
    if r.zscore("news.up:%s" % news_id, user['id']) or\
            r.zscore("news.down:%s" % news_id, user['id']):
        return False, "Duplicated vote."

    if user['id'] != news['user_id']:
        # Check if the user has enough karma to perform this operation
        if (vote_type == "up" and user['karma']  < config.NewsUpvoteMinKarma) or \
                (vote_type == "down" and (user['karma'] < config.NewsDownvoteMinKarma)):
            return False, "You don't have enough karma to vote " + vote_type

    # News was not already voted by that user. Add the vote.
    # Note that even if there is a race condition here and the user may be
    # voting from another device/API in the time between the ZSCORE check
    # and the zadd, this will not result in inconsistencies as we will just
    # update the vote time with ZADD.
    now = int(time.time())
    if r.zadd("news.%s:%s" % (vote_type, news_id), now, user['id']):
        r.hincrby("news:%s" % news_id, vote_type, 1)

    if vote_type == 'up':
        r.zadd("user.saved:%s" % user['id'], now, news_id)

    # Compute the new values of score and karma, updating the news accordingly.
    score = compute_news_score(news)
    news["score"] = score
    rank = compute_news_rank(news)
    r.hmset("news:%s" % (news_id),
           {"score": score,
            "rank": rank})
    r.zadd("news.top",rank, news_id)

    # Remove some karma to the user if needed, and transfer karma to the
    # news owner in the case of an upvote.
    if user['id'] != news['user_id']:
        if vote_type == "up":
            increment_user_karma_by(user['id'], -config.NewsUpvoteKarmaCost)
            increment_user_karma_by(news['user_id'], config.NewsUpvoteKarmaTransfered)
        else:
            increment_user_karma_by(user['id'], -config.NewsDownvoteKarmaCost)

    return rank, None


# Given the news compute its score.
# No side effects.
def compute_news_score(news):
    r = g.redis
    upvotes = r.zrange("news.up:%s" % news["id"], 0, -1, withscores=True)
    downvotes = r.zrange("news.down:%s" % news["id"], 0, -1, withscores=True)
    # FIXME: For now we are doing a naive sum of votes, without time-based
    # filtering, nor IP filtering.
    # We could use just ZCARD here of course, but I'm using ZRANGE already
    # since this is what is needed in the long term for vote analysis.
    score = len(upvotes) - len(downvotes)
    # Now let's add the logarithm of the sum of all the votes, since
    # something with 5 up and 5 down is less interesting than something
    # with 50 up and 50 down.
    votes = len(upvotes) + len(downvotes)
    if votes > config.NewsScoreLogStart:
        score += math.log(votes - config.NewsScoreLogStart) * config.NewsScoreLogBooster
    return score


# Given the news compute its rank, that is function of time and score.
#
# The general forumla is RANK = SCORE / (AGE ^ AGING_FACTOR)
def compute_news_rank(news):
    now = int(time.time())
    age = (now - int(news["ctime"])) / 60.0  #in minutes

    score = float(news["score"])

    if score <= 0:
        rank = score - (age ** config.RankAgingFactor)/20000

    else:
        rank = ((score-0.9)*20000) / \
            ((age+config.NewsAgePadding)**config.RankAgingFactor)

    if age > config.TopNewsAgeLimit:
        rank -= 6

    return rank



# Updating the rank would require some cron job and worker in theory as
# it is time dependent and we don't want to do any sorting operation at
# page view time. But instead what we do is to compute the rank from the
# score and update it in the sorted set only if there is some sensible error.
# This way ranks are updated incrementally and "live" at every page view
# only for the news where this makes sense, that is, top news.
#
# Note: this function can be called in the context of redis.pipelined {...}
def update_news_rank_if_needed(r, n):
    real_rank = compute_news_rank(n)
    delta_rank = abs(real_rank - float(n["rank"]))
    if delta_rank > 0.001:
        r.hset("news:%s" % n["id"], "rank", real_rank)
        r.zadd("news.top", real_rank, n["id"])
        n["rank"] = str(real_rank)


# Fetch one or more (if an Array is passed) news from Redis by id.
# Note that we also load other informations about the news like
# the username of the poster and other informations needed to render
# the news into HTML.
#
# Doing this in a centralized way offers us the ability to exploit
# Redis pipelining.
def get_news_by_id(news_ids, update_rank=False):
    single = False
    result = []
    if not isinstance(news_ids, list):
        single = True
        news_ids = [news_ids]

    r = g.redis
    pl = r.pipeline()
    for nid in news_ids:
        pl.hgetall('news:%s' % nid)

    news = pl.execute()
    if not news:
        # Can happen only if news_ids is an empty array.
        return []

    # Remove empty elements
    news = [n for n in news if len(n) > 0]

    if len(news) == 0:
        if single:
            return None
        else:
            return []

    if update_rank:
        for n in news:
            update_news_rank_if_needed(pl, n)
        pl.execute()

    # Get the associated users information
    for n in news:
        pl.hget('user:%s' % n['user_id'], 'username')
    usernames = pl.execute()
    for i, n in enumerate(news):
        n['username'] = usernames[i]

    # Load $User vote information if we are in the context of a
    # registered user.
    if g.user:
        for n in news:
            pl.zscore("news.up:%s" % n['id'], g.user['id'])
            pl.zscore("news.down:%s" % n['id'], g.user['id'])

        votes = pl.execute()
        for i, n in enumerate(news):
            if votes[i*2]:
                n['voted'] = 'up'
            elif votes[(i*2)+1]:
                n['voted'] = 'down'

    # Return an array if we got an array as input, otherwise
    # the single element the caller requested.
    if single:
        return news[0]
    return news


# Generate the main page of the web site, the one where news are ordered by
# rank.
#
# As a side effect thsi function take care of checking if the rank stored
# in the DB is no longer correct (as time is passing) and updates it if
# needed.
#
# This way we can completely avoid having a cron job adjusting our news
# score since this is done incrementally when there are pageviews on the
# site.
def get_top_news(start=0, count=config.TopNewsPerPage):
    r = g.redis
    numitems = r.zcard("news.top")
    news_ids = r.zrevrange("news.top", start, start+(count-1))
    result = get_news_by_id(news_ids, update_rank=True)
    # Sort by rank before returning, since we adjusted ranks during iteration.
    result.sort(cmp=lambda a, b: cmp(float(b['rank']), float(a["rank"])))
    return result, numitems


# Get news in chronological order.
def get_latest_news(start=0, count=config.LatestNewsPerPage):
    r = g.redis
    numitems = r.zcard("news.cron")
    news_ids = r.zrevrange("news.cron", start, start + count - 1)
    return get_news_by_id(news_ids, update_rank=True), numitems


# Get saved news of current user
def get_saved_news(user_id, start, count):
    r = g.redis
    numitems = int(r.zcard("user.saved:%s" % user_id))
    news_ids = r.zrevrange("user.saved:%s" % user_id, start, start + (count - 1))
    return get_news_by_id(news_ids), numitems


# Return the host part of the news URL field.
# If the url is in the form text:// nil is returned.
def news_domain(news):
    su = news["url"].split("/")
    if su[0] == "text:":
        return None
    return su[2]


# Assuming the news has an url in the form text:// returns the text
# inside. Otherwise nil is returned.
def news_text(news):
    su = news["url"].split("/")
    if su[0] == "text:":
        return news["url"][7:]
    return None


def hack_news(news):
    if isinstance(news, list):
        for n in news:
            n['when'] = util.str_elapsed(int(n['ctime']))
            n['domain'] = news_domain(n)
            if not n['domain']:
                n['url'] = '/news/%s' % n['id']
            n['title'] = n['title'].decode('utf-8')
            #rss pubDate
            n['date'] = util.rfc822(int(n['ctime']))
    else:
        news['when'] = util.str_elapsed(int(news['ctime']))
        news['domain'] = news_domain(news)
        if not news['domain']:
            news['text'] = news_text(news).decode('utf-8')
            news['url'] = '/news/%s' % news['id']
        news['title'] = news['title'].decode('utf-8')
        if g.user and g.user['id'] == news['user_id'] and\
                not news.get('del'):
            if time.time() - int(news['ctime']) < config.NewsEditTime:
                news['showedit'] = True


########NEW FILE########
__FILENAME__ = oauth2
"""
The MIT License

Copyright (c) 2007 Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel

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

import urllib
import time
import random
import urlparse
import hmac
import binascii
import httplib2

try:
    from urlparse import parse_qs, parse_qsl
except ImportError:
    from cgi import parse_qs, parse_qsl


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class Error(RuntimeError):
    """Generic exception class."""

    def __init__(self, message='OAuth error occured.'):
        self._message = message

    @property
    def message(self):
        """A hack to get around the deprecation errors in 2.6."""
        return self._message

    def __str__(self):
        return self._message

class MissingSignature(Error):
    pass

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class Consumer(object):
    """A consumer of OAuth-protected services.

    The OAuth consumer is a "third-party" service that wants to access
    protected resources from an OAuth service provider on behalf of an end
    user. It's kind of the OAuth client.

    Usually a consumer must be registered with the service provider by the
    developer of the consumer software. As part of that process, the service
    provider gives the consumer a *key* and a *secret* with which the consumer
    software can identify itself to the service. The consumer will include its
    key in each request to identify itself, but will use its secret only when
    signing requests, to prove that the request is from that particular
    registered consumer.

    Once registered, the consumer can then use its consumer credentials to ask
    the service provider for a request token, kicking off the OAuth
    authorization process.
    """

    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

    def __str__(self):
        data = {
            'oauth_consumer_key': self.key,
            'oauth_consumer_secret': self.secret
        }

        return urllib.urlencode(data)


class Token(object):
    """An OAuth credential used to request authorization or a protected
    resource.

    Tokens in OAuth comprise a *key* and a *secret*. The key is included in
    requests to identify the token being used, but the secret is used only in
    the signature, to prove that the requester is who the server gave the
    token to.

    When first negotiating the authorization, the consumer asks for a *request
    token* that the live user authorizes with the service provider. The
    consumer then exchanges the request token for an *access token* that can
    be used to access protected resources.
    """

    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

        if self.key is None or self.secret is None:
            raise ValueError("Key and secret must be set.")

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
        """Returns this token as a plain string, suitable for storage.

        The resulting string includes the token's secret, so you should never
        send or store this string where a third party can read it.
        """

        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }

        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)

    @staticmethod
    def from_string(s):
        """Deserializes a token from a string like one returned by
        `to_string()`."""

        if not len(s):
            raise ValueError("Invalid parameter string.")

        params = parse_qs(s, keep_blank_values=False)
        if not len(params):
            raise ValueError("Invalid parameter string.")

        try:
            key = params['oauth_token'][0]
        except Exception:
            raise ValueError("'oauth_token' not found in OAuth request.")

        try:
            secret = params['oauth_token_secret'][0]
        except Exception:
            raise ValueError("'oauth_token_secret' not found in "
                "OAuth request.")

        token = Token(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token

    def __str__(self):
        return self.to_string()


def setter(attr):
    name = attr.__name__

    def getter(self):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError(name)

    def deleter(self):
        del self.__dict__[name]

    return property(getter, attr, deleter)


class Request(dict):

    """The parameters and information for an HTTP request, suitable for
    authorizing with OAuth credentials.

    When a consumer wants to access a service's protected resources, it does
    so using a signed HTTP request identifying itself (the consumer) with its
    key, and providing an access token authorized by the end user to access
    those resources.

    """

    version = VERSION

    def __init__(self, method=HTTP_METHOD, url=None, parameters=None):
        self.method = method
        self.url = url
        if parameters is not None:
            self.update(parameters)

    @setter
    def url(self, value):
        self.__dict__['url'] = value
        if value is not None:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(value)

            # Exclude default port numbers.
            if scheme == 'http' and netloc[-3:] == ':80':
                netloc = netloc[:-3]
            elif scheme == 'https' and netloc[-4:] == ':443':
                netloc = netloc[:-4]
            if scheme not in ('http', 'https'):
                raise ValueError("Unsupported URL %s (%s)." % (value, scheme))

            # Normalized URL excludes params, query, and fragment.
            self.normalized_url = urlparse.urlunparse((scheme, netloc, path, None, None, None))
        else:
            self.normalized_url = None
            self.__dict__['url'] = None

    @setter
    def method(self, value):
        self.__dict__['method'] = value.upper()

    def _get_timestamp_nonce(self):
        return self['oauth_timestamp'], self['oauth_nonce']

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        return dict([(k, v) for k, v in self.iteritems()
                    if not k.startswith('oauth_')])

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        oauth_params = ((k, v) for k, v in self.items()
                            if k.startswith('oauth_'))
        stringy_params = ((k, escape(str(v))) for k, v in oauth_params)
        header_params = ('%s="%s"' % (k, v) for k, v in stringy_params)
        params_header = ', '.join(header_params)

        auth_header = 'OAuth realm="%s"' % realm
        if params_header:
            auth_header = "%s, %s" % (auth_header, params_header)

        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        # tell urlencode to deal with sequence values and map them correctly
        # to resulting querystring. for example self["k"] = ["v1", "v2"] will
        # result in 'k=v1&k=v2' and not k=%5B%27v1%27%2C+%27v2%27%5D
        return urllib.urlencode(self, True)

    def to_url(self):
        """Serialize as a URL for a GET request."""
        base_url = urlparse.urlparse(self.url)
        query = parse_qs(base_url.query)
        for k, v in self.items():
            query.setdefault(k, []).append(v)
        url = (base_url.scheme, base_url.netloc, base_url.path, base_url.params,
               urllib.urlencode(query, True), base_url.fragment)
        return urlparse.urlunparse(url)

    def get_parameter(self, parameter):
        ret = self.get(parameter)
        if ret is None:
            raise Error('Parameter not found: %s' % parameter)

        return ret

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        items = []
        for key, value in self.iteritems():
            if key == 'oauth_signature':
                continue
            # 1.0a/9.1.1 states that kvp must be sorted by key, then by value,
            # so we unpack sequence values into multiple items for sorting.
            if hasattr(value, '__iter__'):
                items.extend((key, item) for item in value)
            else:
                items.append((key, value))

        # Include any query string parameters from the provided URL
        query = urlparse.urlparse(self.url)[4]
        items.extend(self._split_url_string(query).items())

        encoded_str = urllib.urlencode(sorted(items))
        # Encode signature parameters per Oauth Core 1.0 protocol
        # spec draft 7, section 3.6
        # (http://tools.ietf.org/html/draft-hammer-oauth-07#section-3.6)
        # Spaces must be encoded with "%20" instead of "+"
        return encoded_str.replace('+', '%20')

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of sign."""

        if 'oauth_consumer_key' not in self:
            self['oauth_consumer_key'] = consumer.key

        if token and 'oauth_token' not in self:
            self['oauth_token'] = token.key

        self['oauth_signature_method'] = signature_method.name
        self['oauth_signature'] = signature_method.sign(self, consumer, token)

    @classmethod
    def make_timestamp(cls):
        """Get seconds since epoch (UTC)."""
        return str(int(time.time()))

    @classmethod
    def make_nonce(cls):
        """Generate pseudorandom number."""
        return str(random.randint(0, 100000000))

    @classmethod
    def from_request(cls, http_method, http_url, headers=None, parameters=None,
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
                    header_params = cls._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise Error('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = cls._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = cls._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return cls(http_method, http_url, parameters)

        return None

    @classmethod
    def from_consumer_and_token(cls, consumer, token=None,
            http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': consumer.key,
            'oauth_timestamp': cls.make_timestamp(),
            'oauth_nonce': cls.make_nonce(),
            'oauth_version': cls.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.verifier:
                parameters['oauth_verifier'] = token.verifier

        return Request(http_method, http_url, parameters)

    @classmethod
    def from_token_and_callback(cls, token, callback=None,
        http_method=HTTP_METHOD, http_url=None, parameters=None):

        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return cls(http_method, http_url, parameters)

    @staticmethod
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
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params

    @staticmethod
    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters


class Server(object):
    """A skeletal implementation of a service provider, providing protected
    resources to requests from authorized consumers.

    This class implements the logic to check requests for authorization. You
    can use it with your web server or web framework to protect certain
    resources with OAuth.
    """

    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None

    def __init__(self, signature_methods=None):
        self.signature_methods = signature_methods or {}

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.name] = signature_method
        return self.signature_methods

    def verify_request(self, request, consumer, token):
        """Verifies an api call and checks all the parameters."""

        version = self._get_version(request)
        self._check_signature(request, consumer, token)
        parameters = request.get_nonoauth_parameters()
        return parameters

    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, request):
        """Verify the correct version request for this server."""
        try:
            version = request.get_parameter('oauth_version')
        except:
            version = VERSION

        if version and version != self.version:
            raise Error('OAuth version %s not supported.' % str(version))

        return version

    def _get_signature_method(self, request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = request.get_parameter('oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD

        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise Error('Signature method %s not supported try one of the following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_verifier(self, request):
        return request.get_parameter('oauth_verifier')

    def _check_signature(self, request, consumer, token):
        timestamp, nonce = request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        signature_method = self._get_signature_method(request)

        try:
            signature = request.get_parameter('oauth_signature')
        except:
            raise MissingSignature('Missing oauth_signature.')

        # Validate the signature.
        valid = signature_method.check(request, consumer, token, signature)

        if not valid:
            key, base = signature_method.signing_base(request, consumer, token)

            raise Error('Invalid signature. Expected signature base '
                'string: %s' % base)

        built = signature_method.sign(request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise Error('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' % (timestamp, now, self.timestamp_threshold))


class Client(httplib2.Http):
    """OAuthClient is a worker to attempt to execute a request."""

    def __init__(self, consumer, token=None, cache=None, timeout=None,
        proxy_info=None):

        if consumer is not None and not isinstance(consumer, Consumer):
            raise ValueError("Invalid consumer.")

        if token is not None and not isinstance(token, Token):
            raise ValueError("Invalid token.")

        self.consumer = consumer
        self.token = token
        self.method = SignatureMethod_HMAC_SHA1()

        httplib2.Http.__init__(self, cache=cache, timeout=timeout,
            proxy_info=proxy_info)

    def set_signature_method(self, method):
        if not isinstance(method, SignatureMethod):
            raise ValueError("Invalid signature method.")

        self.method = method

    def request(self, uri, method="GET", body=None, headers=None,
        redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None):
        DEFAULT_CONTENT_TYPE = 'application/x-www-form-urlencoded'

        if not isinstance(headers, dict):
            headers = {}

        is_multipart = method == 'POST' and headers.get('Content-Type', DEFAULT_CONTENT_TYPE) != DEFAULT_CONTENT_TYPE

        if body and method == "POST" and not is_multipart:
            parameters = dict(parse_qsl(body))
        else:
            parameters = None

        req = Request.from_consumer_and_token(self.consumer, token=self.token,
            http_method=method, http_url=uri, parameters=parameters)

        req.sign_request(self.method, self.consumer, self.token)


        if method == "POST":
            headers['Content-Type'] = headers.get('Content-Type', DEFAULT_CONTENT_TYPE)
            if is_multipart:
                headers.update(req.to_header())
            else:
                body = req.to_postdata()
        elif method == "GET":
            uri = req.to_url()
        else:
            headers.update(req.to_header())

        return httplib2.Http.request(self, uri, method=method, body=body,
            headers=headers, redirections=redirections,
            connection_type=connection_type)


class SignatureMethod(object):
    """A way of signing requests.

    The OAuth protocol lets consumers and service providers pick a way to sign
    requests. This interface shows the methods expected by the other `oauth`
    modules for signing requests. Subclass it and implement its methods to
    provide a new way to sign requests.
    """

    def signing_base(self, request, consumer, token):
        """Calculates the string that needs to be signed.

        This method returns a 2-tuple containing the starting key for the
        signing and the message to be signed. The latter may be used in error
        messages to help clients debug their software.

        """
        raise NotImplementedError

    def sign(self, request, consumer, token):
        """Returns the signature for the given request, based on the consumer
        and token also provided.

        You should use your implementation of `signing_base()` to build the
        message to sign. Otherwise it may be less useful for debugging.

        """
        raise NotImplementedError

    def check(self, request, consumer, token, signature):
        """Returns whether the given signature is the correct signature for
        the given consumer and token signing the given request."""
        built = self.sign(request, consumer, token)
        return built == signature


class SignatureMethod_HMAC_SHA1(SignatureMethod):
    name = 'HMAC-SHA1'

    def signing_base(self, request, consumer, token):
        sig = (
            escape(request.method),
            escape(request.normalized_url),
            escape(request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def sign(self, request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.signing_base(request, consumer, token)

        # HMAC object.
        try:
            from hashlib import sha1 as sha
        except ImportError:
            import sha # Deprecated

        hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]

class SignatureMethod_PLAINTEXT(SignatureMethod):

    name = 'PLAINTEXT'

    def signing_base(self, request, consumer, token):
        """Concatenates the consumer key and secret with the token's
        secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def sign(self, request, consumer, token):
        key, raw = self.signing_base(request, consumer, token)
        return raw

class Client2(object):
    """Client for OAuth 2.0 draft spec
    https://svn.tools.ietf.org/html/draft-hammer-oauth2-00
    """

    def __init__(self, client_id, client_secret, oauth_base_url,
        redirect_uri=None, cache=None, timeout=None, proxy_info=None):

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.oauth_base_url = oauth_base_url

        if self.client_id is None or self.client_secret is None or \
           self.oauth_base_url is None:
            raise ValueError("Client_id and client_secret must be set.")

        self.http = httplib2.Http(cache=cache, timeout=timeout,
            proxy_info=proxy_info)

    @staticmethod
    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str, keep_blank_values=False)
        for key, val in parameters.iteritems():
            parameters[key] = urllib.unquote(val[0])
        return parameters

    def authorization_url(self, redirect_uri=None, params=None, state=None,
        immediate=None, endpoint='authorize'):
        """Get the URL to redirect the user for client authorization
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-3.5.2.1
        """

        # prepare required args
        args = {
            'type': 'web_server',
            'client_id': self.client_id,
        }

        # prepare optional args
        redirect_uri = redirect_uri or self.redirect_uri
        if redirect_uri is not None:
            args['redirect_uri'] = redirect_uri
        if state is not None:
            args['state'] = state
        if immediate is not None:
            args['immediate'] = str(immediate).lower()

        args.update(params or {})

        return '%s?%s' % (urlparse.urljoin(self.oauth_base_url, endpoint),
            urllib.urlencode(args))

    def access_token(self, code, redirect_uri, params=None, secret_type=None,
        endpoint='access_token'):
        """Get an access token from the supplied code
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-3.5.2.2
        """

        # prepare required args
        if code is None:
            raise ValueError("Code must be set.")
        if redirect_uri is None:
            raise ValueError("Redirect_uri must be set.")
        args = {
            'type': 'web_server',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
        }

        # prepare optional args
        if secret_type is not None:
            args['secret_type'] = secret_type

        args.update(params or {})

        uri = urlparse.urljoin(self.oauth_base_url, endpoint)
        body = urllib.urlencode(args)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response, content = self.http.request(uri, method='POST', body=body,
            headers=headers)
        if not response.status == 200:
            raise Error(content)
        response_args = Client2._split_url_string(content)

        error = response_args.pop('error', None)
        if error is not None:
            raise Error(error)

        refresh_token = response_args.pop('refresh_token', None)
        if refresh_token is not None:
            response_args = self.refresh(refresh_token, secret_type=secret_type)
        return response_args

    def refresh(self, refresh_token, params=None, secret_type=None,
        endpoint='access_token'):
        """Get a new access token from the supplied refresh token
        https://svn.tools.ietf.org/html/draft-hammer-oauth2-00#section-4
        """

        if refresh_token is None:
            raise ValueError("Refresh_token must be set.")

        # prepare required args
        args = {
            'type': 'refresh',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }

        # prepare optional args
        if secret_type is not None:
            args['secret_type'] = secret_type

        args.update(params or {})

        uri = urlparse.urljoin(self.oauth_base_url, endpoint)
        body = urllib.urlencode(args)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response, content = self.http.request(uri, method='POST', body=body,
            headers=headers)
        if not response.status == 200:
            raise Error(content)

        response_args = Client2._split_url_string(content)
        return response_args

    def request(self, base_uri, access_token=None, method='GET', body=None,
        headers=None, params=None, token_param='oauth_token'):
        """Make a request to the OAuth API"""

        args = {}
        args.update(params or {})
        if access_token is not None and method == 'GET':
            args[token_param] = access_token
        uri = '%s?%s' % (base_uri, urllib.urlencode(args))
        return self.http.request(uri, method=method, body=body, headers=headers)

########NEW FILE########
__FILENAME__ = pbkdf2
# -*- coding: utf-8 -*-
"""
    pbkdf2
    ~~~~~~

    This module implements pbkdf2 for Python.  It also has some basic
    tests that ensure that it works.  The implementation is straightforward
    and uses stdlib only stuff and can be easily be copy/pasted into
    your favourite application.

    Use this as replacement for bcrypt that does not need a c implementation
    of a modified blowfish crypto algo.

    Example usage:

    >>> pbkdf2_hex('what i want to hash', 'the random salt')
    'fa7cc8a2b0a932f8e6ea42f9787e9d36e592e0c222ada6a9'

    How to use this:

    1.  Use a constant time string compare function to compare the stored hash
        with the one you're generating::

            def safe_str_cmp(a, b):
                if len(a) != len(b):
                    return False
                rv = 0
                for x, y in izip(a, b):
                    rv |= ord(x) ^ ord(y)
                return rv == 0

    2.  Use `os.urandom` to generate a proper salt of at least 8 byte.
        Use a unique salt per hashed password.

    3.  Store ``algorithm$salt:costfactor$hash`` in the database so that
        you can upgrade later easily to a different algorithm if you need
        one.  For instance ``PBKDF2-256$thesalt:10000$deadbeef...``.


    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import hmac
import hashlib
from struct import Struct
from operator import xor
from itertools import izip, starmap


_pack_int = Struct('>I').pack


def pbkdf2_hex(data, salt, iterations=1000, keylen=24, hashfunc=None):
    """Like :func:`pbkdf2_bin` but returns a hex encoded string."""
    return pbkdf2_bin(data, salt, iterations, keylen, hashfunc).encode('hex')


def pbkdf2_bin(data, salt, iterations=1000, keylen=24, hashfunc=None):
    """Returns a binary digest for the PBKDF2 hash algorithm of `data`
    with the given `salt`.  It iterates `iterations` time and produces a
    key of `keylen` bytes.  By default SHA-1 is used as hash function,
    a different hashlib `hashfunc` can be provided.
    """
    hashfunc = hashfunc or hashlib.sha1
    mac = hmac.new(data, None, hashfunc)
    def _pseudorandom(x, mac=mac):
        h = mac.copy()
        h.update(x)
        return map(ord, h.digest())
    buf = []
    for block in xrange(1, -(-keylen // mac.digest_size) + 1):
        rv = u = _pseudorandom(salt + _pack_int(block))
        for i in xrange(iterations - 1):
            u = _pseudorandom(''.join(map(chr, u)))
            rv = starmap(xor, izip(rv, u))
        buf.extend(rv)
    return ''.join(map(chr, buf))[:keylen]


def test():
    failed = []
    def check(data, salt, iterations, keylen, expected):
        rv = pbkdf2_hex(data, salt, iterations, keylen)
        if rv != expected:
            print 'Test failed:'
            print '  Expected:   %s' % expected
            print '  Got:        %s' % rv
            print '  Parameters:'
            print '    data=%s' % data
            print '    salt=%s' % salt
            print '    iterations=%d' % iterations
            print
            failed.append(1)

    # From RFC 6070
    check('password', 'salt', 1, 20,
          '0c60c80f961f0e71f3a9b524af6012062fe037a6')
    check('password', 'salt', 2, 20,
          'ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957')
    check('password', 'salt', 4096, 20,
          '4b007901b765489abead49d926f721d065a429c1')
    check('passwordPASSWORDpassword', 'saltSALTsaltSALTsaltSALTsaltSALTsalt',
          4096, 25, '3d2eec4fe41c849b80c8d83662c0e44a8b291a964cf2f07038')
    check('pass\x00word', 'sa\x00lt', 4096, 16,
          '56fa6aa75548099dcc37d7f03425e0c3')
    # This one is from the RFC but it just takes for ages
    ##check('password', 'salt', 16777216, 20,
    ##      'eefe3d61cd4da4e4e9945b3d6ba2158c2634e984')

    # From Crypt-PBKDF2
    check('password', 'ATHENA.MIT.EDUraeburn', 1, 16,
          'cdedb5281bb2f801565a1122b2563515')
    check('password', 'ATHENA.MIT.EDUraeburn', 1, 32,
          'cdedb5281bb2f801565a1122b25635150ad1f7a04bb9f3a333ecc0e2e1f70837')
    check('password', 'ATHENA.MIT.EDUraeburn', 2, 16,
          '01dbee7f4a9e243e988b62c73cda935d')
    check('password', 'ATHENA.MIT.EDUraeburn', 2, 32,
          '01dbee7f4a9e243e988b62c73cda935da05378b93244ec8f48a99e61ad799d86')
    check('password', 'ATHENA.MIT.EDUraeburn', 1200, 32,
          '5c08eb61fdf71e4e4ec3cf6ba1f5512ba7e52ddbc5e5142f708a31e2e62b1e13')
    check('X' * 64, 'pass phrase equals block size', 1200, 32,
          '139c30c0966bc32ba55fdbf212530ac9c5ec59f1a452f5cc9ad940fea0598ed1')
    check('X' * 65, 'pass phrase exceeds block size', 1200, 32,
          '9ccad6d468770cd51b10e6a68721be611a8b4d282601db3b36be9246915ec82a')

    raise SystemExit(bool(failed))


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = url

url_mapping = [
    # api

    ('/api/signup', 'api.signup'),
    ('/api/login', 'api.login'),
    ('/api/logout', 'api.logout'),
    ('/api/submit', 'api.submit'),
    ('/api/delnews', 'api.delete_news'),
    ('/api/updateprofile', 'api.update_profile'),
    ('/api/votenews', 'api.vote_news'),

    ('/$', 'app.top'),
    ('/top$', 'app.top'),
    ('/about$', 'app.about'),
    ('/signup$', 'app.signup'),
    ('/login$', 'app.login'),
    ('/logout$', 'app.logout'),
    ('/submit$', 'app.submit'),
    ('/rss$', 'app.rss'),

    ('/login/github$', 'github.auth'),
    ('/oauth/github/callback$', 'github.callback'),

    ('/latest(/\d+)?$', 'app.latest'),
    ('/saved(/\d+)?$', 'app.saved'),
    ('/comments$', 'app.comments'),

    ('/news/(\d+)$', 'app.newspage'),
    ('/editnews/(\d+)$', 'app.editnews'),
    ('/user/(\w+)$', 'app.userpage'),
    ('/luser/(\w+)$', 'app.userpage'),

    ('/lusers$', 'app.lusers'),
    ]


########NEW FILE########
__FILENAME__ = user
import time
import config
import util
import limit
import globals as g


# Create a new user with the specified username/password
#
# Return value: the function returns two values, the first is the
#               auth token if the registration succeeded, otherwise
#               is nil. The second is the error message if the function
#               failed (detected testing the first return value).
def create_user(username, password, userip):
    r = g.redis
    username = username.lower()
    if r.exists("username.to.id:" + username):
        return None, "Username exists, please try a different one."

    if not util.lock('create_user.' + username):
        return None, "Please wait some time before creating a new user."

    user_id = r.incr("users.count")
    auth_token = util.get_rand()
    salt = util.get_rand()
    now = int(time.time())

    pl = r.pipeline()
    pl.hmset("user:%s" % user_id, {
            "id": user_id,
            "username": username,
            "salt": salt,
            "password": util.hash_password(password, salt),
            "ctime": now,
            "karma": config.UserInitialKarma,
            "about": "",
            "email": "",
            "auth": auth_token,
            "apisecret": util.get_rand(),
            "flags": "",
            "karma_incr_time": now,
            "replies": 0,
            })

    pl.set("username.to.id:" + username, user_id)
    pl.set("auth:" + auth_token, user_id)
    pl.execute()

    util.unlock('create_user.' + username)

    return auth_token, None


# Try to authenticate the user, if the credentials are ok we populate the
# g.user global with the user information.
# Otherwise g.user is set to nil, so you can test for authenticated user
# just with: if g.user ...
def auth_user(auth):
    if not auth:
        return
    r = g.redis
    user_id = r.get("auth:%s" % auth)
    if user_id:
        g.user = r.hgetall("user:%s" % user_id)
        increment_karma_if_needed()


def get_user_by_id(user_id):
    r = g.redis
    return r.hgetall('user:%s' % user_id)


def get_user_by_name(username):
    r = g.redis
    user_id = r.get('username.to.id:%s' % username)
    if user_id:
        return get_user_by_id(user_id)


# Update the specified user authentication token with a random generated
# one. This in other words means to logout all the sessions open for that
# user.
#
# Return value: on success the new token is returned. Otherwise nil.
# Side effect: the auth token is modified.
def update_auth_token(user):
    r = g.redis
    r.delete("auth:%s" % user['auth'])
    new_auth_token = util.get_rand()
    r.hset("user:%s" % user['id'], "auth", new_auth_token)
    r.set("auth:%s" % new_auth_token, user['id'])
    return new_auth_token


# Check if the username/password pair identifies an user.
# If so the auth token and form secret are returned, otherwise nil is returned.
def check_user_credentials(username, password):
    user = get_user_by_name(username)
    if not (user and user.has_key('password') and \
                user['password'] ==  util.hash_password(password, user['salt'])):
        return None, None
    return user['auth'], user['apisecret']


def increment_karma_if_needed():
    now = time.time()
    if int(g.user['karma_incr_time']) < now - config.KarmaIncrementInterval:
        userkey = "user:%s" % g.user['id']
        g.redis.hset(userkey, "karma_incr_time", int(now))
        increment_user_karma_by(g.user['id'], config.KarmaIncrementAmount)


# Increment the user karma by the specified amount and make sure to
# update g.user to reflect the change if it is the same user.
def increment_user_karma_by(user_id, increment):
    userkey = "user:" + user_id
    g.redis.hincrby(userkey, "karma", increment)
    if g.user and int(user_id) == int(g.user['id']):
        g.user['karma'] = int(g.user['karma']) + increment


def get_new_users(count):
    r = g.redis
    n = int(r.get('users.count'))
    pl = r.pipeline()
    for i in range(n, n-count, -1):
        if i == 0:
            break
        key = "user:%s" % i
        pl.hgetall(key)

    users = pl.execute()

    return users

########NEW FILE########
__FILENAME__ = util
import json
import time
import os
import binascii
import webob
import webob.exc
import jinja2
import globals as g
import config

# Return the hex representation of an unguessable 160 bit random number.
def get_rand(length=20):
    return binascii.hexlify(os.urandom(length))


def hash_password(password, salt):
    from pbkdf2 import pbkdf2_hex
    return pbkdf2_hex(password, salt, config.PBKDF2Iterations)


def check_string(string, minlen=-1, maxlen=-1, charset=None):
    if isinstance(string, unicode):
        try:
            string = str(string)
        except UnicodeError:
            return None, "invalid"
    elif not isinstance(string, str):
        return None, "invalid"

    if maxlen != -1 and len(string) > maxlen:
        return None, "too long"
    elif minlen != -1 and len(string) < minlen:
        return None, "too short"

    if charset:
        for c in string:
            if c not in charset:
                return None, 'invalid char'

    return string, ''


# Given an unix time in the past returns a string stating how much time
# has elapsed from the specified time, in the form "2 hours ago".
def str_elapsed(t):
    seconds = int(time.time()) - t
    if seconds <= 1:
        return "now"

    elif seconds < 60:
        return "%s seconds ago" % seconds

    elif seconds < 3600:
        minutes = seconds / 60
        return "%d minute%s ago" % (minutes, 's' if minutes > 1 else '')

    elif seconds < 86400:
        hours = seconds / 3600
        return "%d hour%s ago" % (hours, 's' if hours > 1 else '')

    days = seconds / 86400
    return "%d day%s ago" % (days, 's' if days > 1 else '')


def redirect(location='/'):
    return webob.exc.HTTPTemporaryRedirect(location=location)

def json_response(result):
    return webob.Response(json.dumps(result), content_type='application/json')

def static_response(file):
    f = open(os.path.join(config.StaticPath, file))
    html = f.read()
    f.close()
    return webob.Response(html)


#template
def render(template, **kwargs):
    kwargs.update({'disqus_name': config.DisqusName})
    if config.GoogleAnalytics:
        kwargs.update({'ga': config.GoogleAnalytics})
    return webob.Response(g.jj.get_template(template).render(kwargs))

def rfc822(when=None):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(when))


def lock(string):
    key = "lock:" + string
    return g.redis.setnx(key, int(time.time()))

def unlock(string):
    key = "lock:" + string
    return g.redis.delete(key)


def force_int(s):
    try:
        return int(s)
    except:
        return None

########NEW FILE########
