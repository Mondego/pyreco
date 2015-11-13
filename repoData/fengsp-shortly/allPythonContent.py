__FILENAME__ = fabfile
"""
    deploy
    ~~~~~~

    Deploying with Fabric (Latest Version)

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""
import os
from fabric.api import *


# -----------------------------------------------------------
# Just modify the following config to get your script running

#: the user you want to use for remote servers
env.user = 'root'
#: the servers
env.hosts = ['server1.remote', 'server2.remote']
#: the place where you want to put your app
ROOT = '/web'
#: temporary directory used to handle tarballs
TMP = '/tmp'
# -----------------------------------------------------------


#: Your app root directory name
DIRNAME = os.path.basename(os.path.abspath(os.path.dirname(__file__)))
#: Your app tarball name
TARNAME = local('python setup.py --fullname', capture=True).strip()
#: Your app tarball path
TARPATH = os.path.join(TMP, TARNAME)


def pack():
    """Pack your source code
    """
    #: source code parent directory
    parent = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    tar_cmd = 'cd %s && tar zcf %s.tar.gz %s' % (parent, TARPATH, DIRNAME)
    local(tar_cmd, capture=False)


def bootstrap():
    """Init your remote servers
    """
    # upload requirement.txt
    put('requirement.txt', os.path.join(TMP, 'requirement.txt'))
    with cd(TMP):
        run('pip install -r requirement.txt')
    # cleaning
    run('rm %s' % os.path.join(TMP, 'requirement.txt'))


def deploy():
    """Deploying
    """
    # upload to remote server tmp folder
    put('%s.tar.gz' % TARPATH, '%s.tar.gz' % TARPATH)
    # create you destination deploy place
    run('mkdir -p ' + ROOT)
    with cd(ROOT):
        run('tar zxf %s.tar.gz' % TARPATH)

    # cleaning
    local('rm %s.tar.gz' % TARPATH)
    run('rm %s.tar.gz' % TARPATH)


def install():
    """Use this if you are deploying a new app

       Usage:
       $> fab install
    """
    pack()
    bootstrap()
    deploy()
    
    with cd(os.path.join(ROOT, DIRNAME)):
        # fire the application up
        # if you are upgrading, just ignore the rebind error
        run('supervisord -c supervisord.conf')


def upgrade():
    """Use this if you are upgrading one existing app

       Usage:
       $> fab upgrade
    """
    pack()
    bootstrap()
    deploy()

    with cd(os.path.join(ROOT, DIRNAME)):
        # upgrade
        run('supervisorctl reload')
        run('supervisorctl restart all')

########NEW FILE########
__FILENAME__ = fire
# -*- coding: utf-8 -*-
"""
    fire
    ~~~~

    Fire the app up.

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""
from shortly import app


if __name__ == "__main__":
    app.run()

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
    shortly.models
    ~~~~~~~~~~~~~~

    Shortly db.

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""

from redis import Redis

from shortly import app


db = Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], 
           db=app.config['REDIS_DB'])

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
"""
    shortly.settings
    ~~~~~~~~~~~~~~~~

    Shortly config.

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""

import os


DEBUG = False
# Detect environment by whether debug named file exists or not
if os.path.exists(os.path.join(os.path.dirname(__file__), 'debug')):
    DEBUG = True

if DEBUG:
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
else:
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    shortly.utils
    ~~~~~~~~~~~~~

    Shortly utils.

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""

from urlparse import urlparse


def is_valid_url(url):
    parts = urlparse(url)
    return parts.scheme in ('http', 'https')


def base52_encode(number):
    assert isinstance(number, int), 'integer required'
    assert number >= 0, 'positive integer required'
    if number == 0:
        return '0'
    base52 = []
    while number != 0:
        number, i = divmod(number, 52)
        base52.append('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'[i])
    return ''.join(reversed(base52))

########NEW FILE########
__FILENAME__ = views
"""
    shortly.views
    ~~~~~~~~~~~~~

    Register actions.

    :copyright: (c) 2014 by fsp.
    :license: BSD.
"""
from flask import request, abort, redirect
from flask import render_template

from shortly import app
from shortly.utils import is_valid_url, base52_encode
from shortly.models import db


def shorten(url):
    """Simple shorten logic.
    `original-short` + url will store the short id.
    `short-original` + short_id will store the corresponding original url.

    :param url: The original url you want to shorten.
    """
    short_id = db.get('original-short:' + url)
    if short_id is not None:
        return short_id
    num = db.incr('url-autoincr-id')
    short_id = base52_encode(num)
    db.set('original-short:' + url, short_id)
    db.set('short-original:' + short_id, url)
    return short_id


@app.route('/', methods=['GET', 'POST'])
def shortly():
    error = None
    url = ''
    shortly_count = db.get('shortly-count') or '0'
    if request.method == 'POST':
        url = request.form['url']
        if not is_valid_url(url):
            error = 'Invalid URL'
        else:
            short_id = shorten(url)
            return short_id
    return render_template('shortly.html', error=error, url=url, 
                                           shortly_count=shortly_count)


@app.route('/<short_id>')
def original(short_id):
    original_url = db.get('short-original:' + short_id)
    if original_url is None:
        abort(404)
    db.incr('shortly-count')
    return redirect(original_url)

########NEW FILE########
