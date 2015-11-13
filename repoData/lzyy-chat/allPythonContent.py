__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = clear_key
#coding=utf-8
import redis

rc = redis.Redis()
for item in ['online_*', 'room_*']:
    for key in rc.keys(item):
        print 'deleting %s'%key
        rc.delete(key)

########NEW FILE########
__FILENAME__ = app
#coding=utf-8

from flask import Flask, request, session, render_template, Response, jsonify, redirect, flash
from gevent.wsgi import WSGIServer
from utils.text import linkify, escape_text
import gevent
import redis
import time
import config
import json

app = Flask(__name__)
app.config.from_object(config)
app.debug = True

rc = redis.Redis()

def is_admin():
    if session.get('admin'):
        return True
    return False

def is_duplicate_name():
    user_name = session.get('user', '')
    for online_user in rc.zrange(config.ONLINE_USER_CHANNEL, 0, -1):
        if online_user == user_name.encode('utf-8'):
            flash(u'该名(%s)已被抢占，换一个吧'%user_name, 'error')
            session.pop('user', None)
            return True
    return False

@app.route('/adm1n')
def admin():
    session['admin'] = 1
    return redirect('/chat')

@app.route('/')
def index():
    if session.get('user'):
        return redirect('/chat')
    return render_template('index.html')

@app.route('/change_name')
def change_name():
    session.pop('user', None)
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    user_name = request.form.get('user_name', '')
    session['user'] = user_name
    if is_duplicate_name():
        return redirect('/')
    return redirect('/chat')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if not session.get('user'):
        return redirect('/')

    if request.method == 'POST':
        title = request.form.get('title', '')
        if not title:
            return jsonify(status='error', message={'title': 'empty title'})

        room_id = rc.incr(config.ROOM_INCR_KEY)
        rc.set(config.ROOM_INFO_KEY.format(room=room_id),
                json.dumps({'title': title,
                    'room_id': room_id,
                    'user': session['user'],
                    'created': time.time()
                    }))
        return redirect('/chat')

    rooms = []
    room_info_keys = config.ROOM_INFO_KEY.format(room='*')
    for room_info_key in rc.keys(room_info_keys):
        room_info = json.loads(rc.get(room_info_key))
        users = rc.zrevrange(config.ROOM_ONLINE_USER_CHANNEL.format(room=room_info['room_id']), 0, -1)
        rm_channel_placeholder(users)
        rooms.append({
            'id': room_info['room_id'],
            'creator': room_info['user'],
            'content': map(json.loads, reversed(rc.zrevrange(config.ROOM_CHANNEL.format(room=room_info['room_id']), 0, 4))),
            'title': room_info['title'],
            'users': users,
            })

    return render_template('chat.html',
            rooms = rooms,
            uri = request.path,
            is_admin = is_admin(),
            )

@app.route('/rm_room', methods=['POST'])
def rm_room():
    if not session.get('user'):
        return redirect('/')

    room_id = request.form.get('room_id')
    room_key = config.ROOM_INFO_KEY.format(room=room_id)
    room_channel = config.ROOM_CHANNEL.format(room=room_id)
    room = json.loads(rc.get(room_key))
    if not is_admin():
        return jsonify(status='error', content={'message': 'permission denied'})

    rc.delete(room_key)
    rc.delete(room_channel)
    return jsonify(status='ok', content={'url': '/chat'})

@app.route('/chat/<int:room_id>')
def chat_room(room_id):
    if not session.get('user'):
        return redirect('/')

    user_name = session['user']
    room = json.loads(rc.get(config.ROOM_INFO_KEY.format(room=room_id)))
    room_online_user_channel = config.ROOM_ONLINE_USER_CHANNEL.format(room=room_id)
    room_online_user_signal = config.ROOM_ONLINE_USER_SIGNAL.format(room=room_id)

    rc.zadd(config.ONLINE_USER_CHANNEL, user_name, time.time())
    rc.zadd(room_online_user_channel, user_name, time.time())
    rc.publish(config.ONLINE_USER_SIGNAL, '')
    rc.publish(room_online_user_signal, json.dumps({'room_id':room_id}))

    room_content = reversed(rc.zrevrange(config.ROOM_CHANNEL.format(room=room_id), 0, 200, withscores=True))
    room_content_list = []
    for item in room_content:
        room_content_list.append(json.loads(item[0]))

    room_online_users =[]
    for user in rc.zrange(room_online_user_channel, 0, -1):
        if user == config.CHANNEL_PLACEHOLDER:
            continue
        room_online_users.append(user.decode('utf-8'))

    return render_template('room.html',
            room_content = room_content_list,
            uri = request.path,
            room_name = room['title'],
            room_id = room_id,
            room_online_users = room_online_users)

@app.route('/post_content', methods=['POST'])
def post_content():
    if not session.get('user'):
        return redirect('/')

    room_id = request.form.get('room_id')
    data = {'user': session.get('user'),
            'content': linkify(escape_text(request.form.get('content', ''))),
            'created': time.strftime('%m-%d %H:%M:%S'),
            'room_id': room_id,
            'id': rc.incr(config.ROOM_CONTENT_INCR_KEY),
            }
    rc.zadd(config.ROOM_CHANNEL.format(room=room_id), json.dumps(data), time.time())
    return jsonify(**data)

@app.route('/comet')
def comet():
    uri = request.args.get('uri', '')
    room_id = request.args.get('room_id', '')
    comet = request.args.get('comet', '').split(',')
    ts = request.args.get('ts', time.time())
    channel = config.CONN_CHANNEL_SET.format(channel=request.args.get('channel'))

    cmt = Comet()

    result = cmt.check(channel, comet, ts, room_id)
    if result:
        return jsonify(**result)

    passed_time = 0
    while passed_time < config.COMET_TIMEOUT:
        comet = rc.smembers(config.CONN_CHANNEL_SET.format(channel=channel))
        result = cmt.check(channel, comet, ts, room_id)
        if result:
            return jsonify(**result)
        passed_time += config.COMET_POLL_TIME
        gevent.sleep(config.COMET_POLL_TIME)

    if room_id:
        room_online_user_channel = config.ROOM_ONLINE_USER_CHANNEL.format(room=room_id)
        rc.zadd(room_online_user_channel, session['user'], time.time())
    rc.zadd(config.ONLINE_USER_CHANNEL, session['user'], time.time())

    return jsonify(ts=time.time())

def rm_channel_placeholder(data):
    for index, item in enumerate(data):
        if item == config.CHANNEL_PLACEHOLDER:
            data.pop(index)

class Comet(object):
    def check(self, channel, comet, ts, room_id = 0):
        conn_channel_set = config.CONN_CHANNEL_SET.format(channel=channel)
        if 'online_users' in comet:
            rc.sadd(conn_channel_set, 'online_users')
            new_data = rc.zrangebyscore(config.ONLINE_USER_CHANNEL, ts, '+inf')
            if new_data:
                data=rc.zrevrange(config.ONLINE_USER_CHANNEL, 0, -1)
                data.pop(0) if data[0] == config.CHANNEL_PLACEHOLDER else True
                return dict(data=data,
                        ts=time.time(), type='online_users')

        if 'room_online_users' in comet:
            rc.sadd(conn_channel_set, 'room_online_users')
            room_online_user_channel = config.ROOM_ONLINE_USER_CHANNEL.format(room=room_id)
            new_data = rc.zrangebyscore(room_online_user_channel, ts, '+inf')
            if new_data:
                users=rc.zrevrange(room_online_user_channel, 0, -1)
                rm_channel_placeholder(users)
                data = {'room_id': room_id, 'users': users}
                return dict(data=data,
                    ts=time.time(), type='room_online_users')

        if 'room_content' in comet:
            rc.sadd(conn_channel_set, 'room_content')
            room_channel = config.ROOM_CHANNEL.format(room=room_id)
            new_data = rc.zrangebyscore(room_channel, ts, '+inf')
            if new_data:
                data = {'room_id': room_id, 'content':[]}
                for item in new_data:
                    data['content'].append(json.loads(item))
                return dict(data=data, ts=time.time(), type='add_content')

        if 'room_online_users_count_all' in comet:
            rc.sadd(conn_channel_set, 'room_online_users_count_all')
            room_online_user_channels = config.ROOM_ONLINE_USER_CHANNEL.format(room='*')
            for room_online_user_channel in rc.keys(room_online_user_channels):
                new_data = rc.zrangebyscore(room_online_user_channel, ts, '+inf')
                if new_data:
                    users=rc.zrevrange(room_online_user_channel, 0, -1)
                    rm_channel_placeholder(users)
                    room_id = room_online_user_channel.split('_')[-1]
                    data = {'room_id': room_id, 'users': users}
                    return dict(data=data, ts=time.time(), type='room_online_users')

        if 'room_content_all' in comet:
            rc.sadd(conn_channel_set, 'room_content_all')
            room_channels = config.ROOM_CHANNEL.format(room='*')
            for room_channel in rc.keys(room_channels):
                new_data = rc.zrangebyscore(room_channel, ts, '+inf')
                if new_data:
                    room_id = room_channel.split('_')[-1]
                    data = {'room_id': room_id, 'content':[]}
                    for item in new_data:
                        data['content'].append(json.loads(item))
                    return dict(data=data, ts=time.time(), type='add_content')

def run():
    http_server = WSGIServer(('', config.PORT), app)
    http_server.serve_forever()
    #app.run(port=config.PORT)

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = config
#coding=utf-8

DEBUG = True
PORT = 9527
SECRET_KEY = 'i have a dream'
SESSION_COOKIE_HTTPONLY = False

CHAT_NAME = u'谈天说地老天荒'

ONLINE_USER_CHANNEL = 'online_user_channel'
ROOM_ONLINE_USER_CHANNEL = 'room_online_user_channel_{room}'
ROOM_CHANNEL = 'room_channel_{room}'

ROOM_INCR_KEY = 'room_incr_key'
ROOM_CONTENT_INCR_KEY = 'room_content_incr_key'
ROOM_INFO_KEY = 'room_info_key_{room}'

ONLINE_USER_SIGNAL = ONLINE_USER_CHANNEL
ROOM_ONLINE_USER_SIGNAL = ROOM_ONLINE_USER_CHANNEL
ROOM_SIGNAL = ROOM_CHANNEL

CONN_CHANNEL_SET = 'conn_channel_set_{channel}'

COMET_TIMEOUT = 30
COMET_POLL_TIME = 2

CHANNEL_PLACEHOLDER = 'jwdlh'

########NEW FILE########
__FILENAME__ = gc
from apscheduler.scheduler import Scheduler
import signal
import redis
import config
import time
import json

rc = redis.Redis()

sched = Scheduler()
sched.start()

def clear():
    current_time = time.time()
    affcted_num = rc.zremrangebyscore(config.ONLINE_USER_CHANNEL, '-inf', current_time - 60)
    if affcted_num:
        rc.zadd(config.ONLINE_USER_CHANNEL, config.CHANNEL_PLACEHOLDER, time.time())

    for key in rc.keys(config.ROOM_ONLINE_USER_CHANNEL.format(room='*')):
        affcted_num = rc.zremrangebyscore(key, '-inf', current_time - 60)
        if affcted_num:
            rc.zadd(key, config.CHANNEL_PLACEHOLDER, time.time())

sched.add_cron_job(clear,  minute='*')

signal.pause()

########NEW FILE########
__FILENAME__ = text
#coding=utf-8

import re

def escape_text(txt):
    return txt.replace('<', '&lt;').replace('>', '&gt;')

def make_re_url():
    url = r"""
    (?xi)
\b
(                       # Capture 1: entire matched URL
  (?:
    https?://               # http or https protocol
    |                       #   or
    www\d{0,3}[.]           # "www.", "www1.", "www2." … "www999."
    |                           #   or
    [a-z0-9.\-]+[.][a-z]{2,4}/  # looks like domain name followed by a slash
  )
  (?:                       # One or more:
    [^\s()<>]+                  # Run of non-space, non-()<>
    |                           #   or
    \(([^\s()<>]+|(\([^\s()<>]+\)))*\)  # balanced parens, up to 2 levels
  )+
  (?:                       # End with:
    \(([^\s()<>]+|(\([^\s()<>]+\)))*\)  # balanced parens, up to 2 levels
    |                               #   or
    [^\s`!()\[\]{};:'".,<>?«»“”‘’]        # not a space or one of these punct chars
  )
)
    """
    return re.compile(url, re.VERBOSE | re.MULTILINE)

RE_URL = make_re_url()

def linkify(txt,
            shorten = True,
            target_blank = False,
            require_protocol = False,
            permitted_protocols = ["http", "https"],
            local_domain = None):
    """Converts plain txt into HTML with links. back ported from tornado 2.0

    For example: ``linkify("Hello http://tornadoweb.org!")`` would return
    ``Hello <a href="http://tornadoweb.org">http://tornadoweb.org</a>!``

    Parameters:

    shorten: Long urls will be shortened for display.

    extra_params: Extra txt to include in the link tag,
        e.g. linkify(txt, extra_params='rel="nofollow" class="external"')

    require_protocol: Only linkify urls which include a protocol. If this is
        False, urls such as www.facebook.com will also be linkified.

    permitted_protocols: List (or set) of protocols which should be linkified,
        e.g. linkify(txt, permitted_protocols=["http", "ftp", "mailto"]).
        It is very unsafe to include protocols such as "javascript".
    local_domain: domain link
    """

    if txt is None or not txt.strip():
        return txt
    extra_params = ' rel="nofollow"'

    def make_link(m):
        tb = target_blank
        url = m.group(1)
        proto = m.group(2)
        if require_protocol and not proto:
            return url  # not protocol, no linkify

        if proto and proto not in permitted_protocols:
            return url  # bad protocol, no linkify

        href = m.group(1)
        #href = xhtml_unescape(href).strip()
        if not proto:
            href = "http://" + href   # no proto specified, use http

        params = extra_params
        if proto:
            proto_len = len(proto) + 1 + len(m.group(3) or "")  # +1 for :
        else:
            proto_len = 0

        parts = url[proto_len:].split("/")

        proto_part = url[:proto_len] if proto != 'http' else ''
        host_part = parts[0]

        if host_part.startswith('www.'):
            host_part = '.'.join(host_part.split('.')[1:]) # add extra idnetification for external link
        if not local_domain or not host_part.endswith(local_domain):
            params  += ' class="external" '
            tb = True

        if tb:
            params  += 'target="_blank"'

        # clip long urls. max_len is just an approximation
        max_len = 30
        if shorten and len(url) > max_len:
            before_clip = url[proto_len:]
            url = proto_part + host_part
            #if len(parts) > 2:
                # Grab the whole host part plus the first bit of the path
                # The path is usually not that interesting once shortened
                # (no more slug, etc), so it really just provides a little
                # extra indication of shortening.
            for n,p in enumerate(parts[1:]):
                if n:
                    cut = 6
                else:
                    cut = 8
                url += '/' + p[:cut].split('?')[0].split('.')[0]
                if len(p) < 4:
                    continue
                break
                #url = proto_part + host_part  + "/" + \
                        #parts[1][:8].split('?')[0].split('.')[0]

            if len(url) > max_len * 1.5:  # still too long
                url = url[:max_len]

            if url != before_clip:
                amp = url.rfind('&')
                # avoid splitting html char entities
                if amp > max_len - 5:
                    url = url[:amp]
                url += "..."

                if len(url) >= len(before_clip):
                    url = before_clip
                else:
                    # full url is visible on mouse-over (for those who don't
                    # have a status bar, such as Safari by default)
                    params += ' title="%s"' % href

        return u'<a href="%s"%s>%s</a>' % (href, params, url)

    return RE_URL.sub(make_link, txt)

if __name__ == '__main__':
    txt = 'have a link test www.zhihu.com/question/19550224?noti_id=123 how about?'
    txt1 = 'hello http://tornadoweb.org!'
    print linkify(txt)

########NEW FILE########
