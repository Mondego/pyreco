__FILENAME__ = manage
# -*- encoding: utf-8 -*-
#
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

import logging
import string
import re

from datetime import timedelta, datetime
from time import strftime, gmtime

from flask import Flask

from pymongo import Connection
from gridfs import GridFS
from gridfs.errors import NoFile

from regenwolken.utils import ppsize

log = logging.getLogger('regenwolken')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)


def tdelta(input):
    """converts human-readable time deltas to datetime.timedelta.
    >>> tdelta(3w 12m) == datetime.timedelta(weeks=3, minutes=12)"""

    keys = ['weeks', 'days', 'hours', 'minutes']
    regex = ''.join(['((?P<%s>\d+)%s ?)?' % (k, k[0]) for k in keys])
    kwargs = {}
    for k,v in re.match(regex, input).groupdict(default='0').items():
        kwargs[k] = int(v)
    return timedelta(**kwargs)


def account(conf, options, args):
    '''View details or summary of all accounts.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    if options.all:
        query = None
    elif len(args) == 2:
        query = {'_id': int(args[1])} if args[1].isdigit() else {'email': args[1]}
    else:
        log.error('account <email or _id> requires a valid email or _id')
        sys.exit(1)

    for acc in db.accounts.find(query):
        if str(acc['_id']).startswith('_'):
            continue
        print '%s [id:%s]' % (acc['email'], acc['id'])
        for key in acc:
            if key in ['email', '_id', 'id']:
                continue
            if key == 'items':
                try:
                    size = sum([fs.get(_id).length for _id in acc['items']])
                except NoFile:
                    log.warn('Account `%s` has some files missing:', _id)
                    # fail safe counting
                    size = 0
                    missing = []
                    for i in acc['items']:
                        if not fs.exists(i):
                            missing.append(i)
                        else:
                            size += fs.get(i).length
                print'    size: %s' % ppsize(size)
            print '    %s: %s' % (key, acc[key])
    if options.all:  print db.accounts.count()-1, 'accounts total' # -1 for _autoinc

    con.disconnect()


def activate(conf, options, args):
    '''When PUBLIC_REGISTRATION is set to false, you have to activate
    registered accounts manually by invoking "activate $email"'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    accounts = con[conf['MONGODB_NAME']].accounts

    if len(args) == 2:
        acc = accounts.find_one({'email': args[1]})
        if not acc:
            print '`%s` does not exist' % args[1]
            sys.exit(1)
        elif acc['activated_at'] != None:
            print '`%s` already activated' % args[1]
        else:
            act = {'activated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())}
            accounts.update({'_id': acc['_id']}, {'$set': act})
            print '`%s` activated' % args[1]
    else:
        inactivated = [acc for acc in accounts.find() if not acc.get('activated_at', True)]
        if not inactivated:
            print 'no pending non-activated accounts'
        for acc in inactivated:
            print '%s [%s]' % (acc['email'].ljust(16), acc['created_at'])

    con.disconnect()

def info(conf):
    '''A basic, incomplete short info.  Displays overall file size and
    account counts.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    overall_file_size = sum([f['length'] for f in fs._GridFS__files.find()])
    inactivated = [acc for acc in db.accounts.find() if not acc.get('activated_at', True)]
    print fs._GridFS__files.count(), 'files [%s]' % ppsize(overall_file_size)
    print db.accounts.count()-1, 'accounts total,', len(inactivated) , 'not activated'

    con.disconnect()

def purge(conf, options, args):
    '''Purges files or accounts.

    With GNU Opts -a and/or --all a given account/all accounts are removed
    including metadata and files.

    Given a crontab-like timedelta e.g. `3d` will remove every file older
    than 3 days including its metadata. To delete all files write `0d` or --all.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    def delete_account(_id):
        """deletes account with _id and all his files"""

        items = db.accounts.find_one({'_id': _id})['items']
        db.accounts.remove(_id)

        for item in items:
            fs.delete(item)
            db.items.remove(item)
        return True

    if options.account and not options.all and len(args) < 2:
        log.error('purge -a <_id> requires an account _id or email')
        sys.exit(1)
    elif not options.account and not options.all and len(args) < 2:
        log.error('purge <timedelta> requires a time delta')
        sys.exit(1)

    if options.account:
        if options.all:
            yn = raw_input('delete all accounts? [y/n] ')
            if yn != 'y':
                sys.exit(0)
            print 'deleting %s accounts' % (db.accounts.count() - 1)
            for acc in db.accounts.find():
                if str(acc['_id']).startswith('_'):
                    continue
                delete_account(acc['_id'])
        else:
            query = {'_id': int(args[1])} if args[1].isdigit() else {'email': args[1]}
            query = db.accounts.find_one(query)

            if not query:
                log.error('no such _id or email `%s`', args[1])
                sys.exit(1)
            print 'deleting account `%s`' % args[1]
            delete_account(query['_id'])
    else:
        delta = timedelta(0) if options.all else tdelta(args[1])
        if delta == timedelta(0):
            yn = raw_input('delete all files? [y/n] ')
            if yn != 'y':
                sys.exit(0)
        else:
            print 'purging files older than %s' % str(delta)[:-3]

        now = datetime.utcnow()
        delete = []
        for obj in fs._GridFS__files.find():
            if now - delta > obj['uploadDate']:
                delete.append(obj)

        for cur in db.accounts.find():
            # FIXME bookmarks survive
            if str(cur['_id']).startswith('_'):
                continue
            _id, items = cur['_id'], cur['items']
            for obj in delete:
                try:
                    items.remove(obj['_id'])
                except ValueError:
                    pass
            db.accounts.update({'_id': _id}, {'$set': {'items': items}})

        for obj in delete:
            fs.delete(obj['_id'])
            db.items.remove(obj['_id'])

    con.disconnect()


def repair(conf, options):
    '''fixes issues created by myself.  Currently, only orphan files and
    item links are detected and automatically removed.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    objs = [obj['_id'] for obj in fs._GridFS__files.find()]
    meta = [cur['_id'] for cur in db.items.find()]

    if objs != meta:
        # 1. metadata has some files missing, no repair possible
        diff1 = filter(lambda i: not i in objs, meta)
        diff2 = filter(lambda i: not i in meta, objs)
        for item in diff1:
            print 'removing metadata for `%s`' % item
            db.items.remove(item)

        # 2. metadata is missing, but file is there. Recover possible, but not implemented #win
        for item in diff2:
            print 'removing GridFS-File `%s`' % item
            objs.remove(item)

    # rebuild accounts items, when something changed
    for cur in db.accounts.find():
        if str(cur['_id']).startswith('_'):
            continue
        _id, items = cur['_id'], cur['items']
        items = filter(lambda i: i in objs, items)
        db.accounts.update({'_id': _id}, {'$set': {'items': items}})

    con.disconnect()


def main():

    from optparse import OptionParser, make_option

    usage = "usage: %prog [options] info|account|activate|purge|repair\n" + '\n' \
            + "  info     – provides basic information of regenwolken's MongoDB\n" \
            + "  activate – lists inactive accounts or activates given email\n" \
            + "  account  – details of given (email or _id) or --all accounts\n" \
            + "  files    – summary of uploaded files --all works, too\n" \
            + "  purge    – purge -a account or files. --all works, too\n" \
            + "  repair   – repair broken account-file relations in MongoDB"

    options = [
        make_option('-a', '--account', dest='account', action='store_true',
                    default=False, help='purge account and its files'),
        make_option('--all', dest='all', action='store_true',
                    default=False, help='select ALL'),
        make_option('--conf', dest="conf", default="regenwolken.cfg", metavar="FILE",
                    help="regenwolken configuration")
    ]

    parser = OptionParser(option_list=options, usage=usage)
    (options, args) = parser.parse_args()

    app = Flask(__name__)
    app.config.from_object('regenwolken.utils.conf')
    app.config.from_envvar('REGENWOLKEN_SETTINGS', silent=True)

    path = options.conf if options.conf.startswith('/') else '../' + options.conf
    app.config.from_pyfile(path, silent=True)

    if 'info' in args:
        info(app.config)
    elif 'account' in args:
        account(app.config, options, args)
    elif 'activate' in args:
        activate(app.config, options, args)
    elif 'purge' in args:
        purge(app.config, options, args)
    elif 'repair' in args:
        repair(app.config, options)
    else:
        parser.print_help()

########NEW FILE########
__FILENAME__ = mongonic
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from uuid import uuid4
from time import gmtime, strftime
from random import getrandbits

from gridfs import GridFS as Grid
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from regenwolken.utils import Struct, slug


class Sessions:
    """A session handler using MongoDB's capped collections. If you experience
    lots of 401 try to increase size a bit."""

    def __init__(self, database, size=100*1024):

        database.drop_collection('sessions')
        self.col = Collection(database, 'sessions', create=True, capped=True, size=size)

    def new(self, account):

        key = uuid4().hex
        self.col.insert({'account': account, 'key': key})

        return key

    def pop(self, key):

        cur = self.col.find_one({'key': key})
        if cur is None:
            raise KeyError

        self.col.remove(cur)

        return cur


class GridFS:
    """An extended GridFS (+MongoDB) backend to update metadata in a separate
    MongoDB but handle them in one GridOut object.

    As it is not documented: every attribute in GridOut is read-only. You
    can only write these `metadata` once. This extended GridFS will keep
    GridIn's _id, content_type, filename and upload_date and so on intact
    and read-only!"""

    def __init__(self, database, collection='fs'):
        """shortcuts to gridFS(db) and db.items"""

        self.mdb = database.items
        self.gfs = Grid(database, collection)

    def put(self, data, _id, content_type, filename, **kw):
        """upload file-only. Can not handle bookmarks."""

        if _id in ['thumb', 'items', 'login']:
            raise DuplicateKeyError

        item_type, subtype = content_type.split('/', 1)
        if item_type in ['image', 'text', 'audio', 'video']:
            pass
        elif item_type == 'application' and \
        filter(lambda k: subtype.find(k) > -1, ['compress', 'zip', 'tar']):
                item_type = 'archive'
        else:
            item_type = 'unknown'

        if self.mdb.find_one({'short_id': kw['short_id']}):
            raise DuplicateKeyError('short_id already exists')

        _id = self.gfs.put(data, _id=_id, content_type=content_type,
                               filename=filename)

        kw.update({'_id': _id, 'item_type': item_type})
        self.mdb.insert(kw)

        return _id

    def get(self, _id=None, short_id=None):
        """if url is given, we need a reverse lookup in metadata.  Returns
        a GridOut/bookmark with additional metadata added."""

        if _id:
            cur = self.mdb.find_one({'_id': _id})
        else:
            cur = self.mdb.find_one({'short_id': short_id})
            if not cur:
                return None
            _id = cur['_id']

        if cur.get('item_type', '') == 'bookmark':
            return Struct(**cur)
        else:
            obj = self.gfs.get(_id)
            obj.__dict__.update(cur)
            return obj

    def update(self, _id, **kw):
        '''update **kw'''
        self.mdb.update({'_id': _id}, {'$set': kw}, upsert=False)

    def inc_count(self, _id):
        '''find and increase view_counter'''
        self.mdb.update({'_id': _id}, {'$inc': {'view_counter': 1}})

    def delete(self, item):
        '''remove item from gridfs and db.items'''

        if item['item_type'] != 'bookmark':
            self.gfs.delete(item['_id'])
        self.mdb.remove(item['_id'])

    def upload_file(self, conf, account, obj, useragent, privacy):

        if obj is None:
            return None

        # XXX what's this?
        if isinstance(privacy, (str, unicode)):
            privacy = True if privacy == 'private' else False

        timestamp = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

        if obj.filename.find(u'\x00') == len(obj.filename)-1:
            filename = obj.filename[:-1]
        else:
            filename = obj.filename

        _id = str(getrandbits(32))
        retry_count = 3
        short_id_length = conf['SHORT_ID_MIN_LENGTH']
        while True:
            try:
                self.put(obj, _id=_id ,filename=filename, created_at=timestamp,
                       content_type=obj.mimetype, account=account, view_counter=0,
                       short_id=slug(short_id_length), updated_at=timestamp,
                       source=useragent, private=privacy)
                break
            except DuplicateKeyError:
                retry_count += 1
                if retry_count > 3:
                    short_id_length += 1
                    retry_count = 1

        return _id

########NEW FILE########
__FILENAME__ = specs
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from __future__ import unicode_literals

import sys
import mimetypes

from time import strftime, gmtime
from os.path import splitext

from werkzeug.urls import url_quote
from werkzeug.utils import secure_filename
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache(30*60)  # XXX use redis!

from regenwolken.utils import A1, Struct

try:
    import pygments
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    pygments = None

try:
    import markdown
except ImportError:
    markdown = None


def Item(obj, conf, scheme='http'):
    """JSON-compatible dict representing Item.

        href:           used for renaming -> http://developer.getcloudapp.com/rename-item
        name:           item's name, taken from filename
        private:        requires auth when viewing
        subscribed:     true or false, when paid for "Pro"
        url:            url to this file
        content_url:    <unknown>
        item_type:      image, bookmark, ... there are more
        view_counter:   obviously
        icon:           some picture to display `item_type`
        remote_url:     <unknown>, href + quoted name
        thumbnail_url:  <url to thumbnail, when used?>
        redirect_url:   redirection url in bookmark items
        source:         client name
        created_at:     timestamp created - '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:     timestamp updated - '%Y-%m-%dT%H:%M:%SZ' UTC
        deleted_at:     timestamp deleted - '%Y-%m-%dT%H:%M:%SZ' UTC
    """

    x = {}
    if isinstance(obj, dict):
        obj = Struct(**obj)

    result = {
        "href": "%s://%s/items/%s" % (scheme, conf['HOSTNAME'], obj._id),
        "private": obj.private,
        "subscribed": True,
        "item_type": obj.item_type,
        "view_counter": obj.view_counter,
        "icon": "%s://%s/images/item_types/%s.png" % (scheme, conf['HOSTNAME'], obj.item_type),
        "source": obj.source,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "deleted_at": None }

    if obj.item_type == 'bookmark':
        x['name'] = obj.name
        x['url'] = scheme + '://' + conf['HOSTNAME'] + '/' + obj.short_id
        x['content_url'] = x['url'] + '/content'
        x['remote_url'] = None
        x['redirect_url'] = obj.redirect_url
    else:
        x['name'] = obj.filename
        x['url'] = scheme + '://' + conf['HOSTNAME'] + '/' + obj.short_id
        x['content_url'] = x['url'] + '/' + secure_filename(obj.filename)
        x['remote_url'] = x['url'] + '/' + url_quote(obj.filename)
        x['thumbnail_url'] = x['url'] # TODO: thumbails
        x['redirect_url'] = None

    try:
        x['created_at'] = obj.created_at
        x['updated_at'] = obj.updated_at
        x['deleted_at'] = obj.deleted_at
        if obj.deleted_at:
            x['icon'] = scheme + "://" + conf['HOSTNAME'] + "/images/item_types/trash.png"
    except AttributeError:
        pass

    result.update(x)
    return result


def Account(account, conf, **kw):
    """JSON-compatible dict representing cloudapp's account

        domain:           custom domain, only in Pro available
        domain_home_page: http://developer.getcloudapp.com/view-domain-details
        private_items:    http://developer.getcloudapp.com/change-default-security
        subscribed:       Pro feature, custom domain... we don't need this.
        alpha:            <unkown> wtf?
        created_at:       timestamp created - '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:       timestamp updated - '%Y-%m-%dT%H:%M:%SZ' UTC
        activated_at:     timestamp account activated, per default None
        items:            (not official) list of items by this account
        email:            username of this account, characters can be any
                          of "a-zA-Z0-9.- @" and no digit-only name is allowed
        password:         password, md5(username + ':' + realm + ':' + passwd)
    """

    result = {
        'id': account['id'],
        'domain': conf['HOSTNAME'],
        'domain_home_page': None,
        'private_items': False,
        'subscribed': True,
        'subscription_expires_at': '2112-12-21',
        'alpha': False,
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'activated_at': None,
        "items": [],
        'email': account['email'],
        'passwd': A1(account['email'], account['passwd'])
    }

    result.update(kw)
    return result


class Drop:
    """Drop class which renders item-specific layouts."""

    def __init__(self, drop, conf, scheme):

        def guess_type(filename):
            try:
                m = mimetypes.guess_type(filename)[0].split('/')[0]
                if m in ['image', 'text']:
                    return m
            except AttributeError:
                if self.ismarkdown or self.istext or self.iscode:
                    return 'text'
            return 'other'

        self.__dict__.update(Item(drop, conf, scheme))
        self.drop = drop
        self.item_type = guess_type(self.filename)
        self.url = self.__dict__['content_url']

    @property
    def ismarkdown(self):
        return splitext(self.filename)[1][1:] in ['md', 'mkdown', 'markdown']

    @property
    def iscode(self):

        if pygments is None:
            return False

        try:
            get_lexer_for_filename(self.filename)
            return True
        except ClassNotFound:
            return False

    @property
    def istext(self):
        """Uses heuristics to guess whether the given file is text or binary,
        by reading a single block of bytes from the file. If more than 30% of
        the chars in the block are non-text, or there are NUL ('\x00') bytes in
        the block, assume this is a binary file.

        -- via http://eli.thegreenplace.net/2011/10/19/perls-guess-if-file-is-text-or-binary-implemented-in-python/"""

        # A function that takes an integer in the 8-bit range and returns a
        # single-character byte object in py3 / a single-character string in py2.
        int2byte = (lambda x: bytes((x,))) if sys.version_info > (3, 0) else chr

        blocksize = 512
        chars = b''.join(int2byte(i) for i in range(32, 127)) + b'\n\r\t\f\b'

        block = self.read(blocksize); self.seek(0)
        if b'\x00' in block:
            # Files with null bytes are binary
            return False
        elif not block:
            # An empty file is considered a valid text file
            return True

        # Use translate's 'deletechars' argument to efficiently remove all
        # occurrences of chars from the block
        nontext = block.translate(None, chars)
        return float(len(nontext)) / len(block) <= 0.30

    @property
    def markdown(self):
        rv = cache.get('text-'+self.short_id)
        if rv is None:
            rv = markdown.markdown(self.read().decode('utf-8'))
            cache.set('text-'+self.short_id, rv)
        return rv

    @property
    def code(self):
        rv = cache.get('text-'+self.short_id)
        if rv is None:
            rv = highlight(
                self.read().decode('utf-8'),
                get_lexer_for_filename(self.url),
                HtmlFormatter(lineos=False, cssclass='highlight')
            )

            cache.set('text-'+self.short_id, rv)
        return rv

    def __getattr__(self, attr):
        return getattr(self.drop, attr)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

import io
import string
import hashlib

from random import getrandbits, choice

from os import urandom
from base64 import standard_b64encode

import flask
from werkzeug import Response

try:
    from PIL import ImageFile
except ImportError:
    ImageFile = None


def urlscheme(request):
    """return the current scheme (HTTP or HTTPS)"""

    if request.url.startswith('https://'):
        return 'https'
    return request.headers.get('X-Forwarded-Proto', 'http')


def md5(data):
    """returns md5 of data has hexdigest"""
    return hashlib.md5(data).hexdigest()


def A1(username, passwd, realm='Application'):
    """A1 HTTP Digest Authentication"""
    return md5(username + ':' + realm + ':' + passwd)


def prove_auth(app, req):
    """calculates digest response (MD5 and qop)"""
    auth = req.authorization

    account = app.db.accounts.find_one({'email': auth.username})
    _A1 = account['passwd'] if account else standard_b64encode(urandom(16))

    if str(auth.get('qop', '')) == 'auth':
        A2 = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth',
                       md5(req.method + ':' + auth.uri)])
        return md5(_A1 + ':' + A2)
    else:
        # compatibility with RFC 2069: https://tools.ietf.org/html/rfc2069
        A2 = ':'.join([auth.nonce, md5(req.method + ':' + auth.uri)])
        return md5(_A1 + ':' + A2)


def login(f):
    """login decorator using HTTP Digest Authentication.  Pattern based on
    http://flask.pocoo.org/docs/patterns/viewdecorators/

    -- http://developer.getcloudapp.com/usage/#authentication"""

    app = flask.current_app

    def dec(*args, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Digest Auth failed."""

        request = flask.request
        usehtml = request.accept_mimetypes.accept_html

        if not request.authorization:
            response = Response(
                'Unauthorized', 401,
                content_type='text/html; charset=utf-8' if usehtml else 'application/json'
            )
            response.www_authenticate.set_digest(
                'Application', algorithm='MD5',
                nonce=standard_b64encode(urandom(32)),
                qop=('auth', ), opaque='%x' % getrandbits(128))
            return response
        else:
            account = app.db.accounts.find_one({'email': request.authorization.username})
            if account and account['activated_at'] == None:
                return Response('[ "Your account hasn\'t been activated. Please ' \
                                + 'check your email and activate your account." ]', 409)
            elif prove_auth(app, request) != request.authorization.response:
                return Response('Forbidden', 403)
        return f(*args, **kwargs)
    return dec


class private:
    """Check for private items in the web interface and ask for credentials if necessary.
    """
    def __init__(self, condition):
        self.condition = condition

    def __call__(self, f):
        def check(*args, **kwargs):
            item = flask.current_app.db.items.find_one({'short_id': kwargs['short_id']})
            if (item and not item['private']) or not self.condition(flask.request):
                return f(*args, **kwargs)
            return login(f)(*args, **kwargs)
        return check


def slug(length=8, charset=string.ascii_lowercase+string.digits):
    """generates a pseudorandom string of a-z0-9 of given length"""
    return ''.join([choice(charset) for x in xrange(length)])


def clear(account):
    for key in '_id', 'items', 'passwd':
        account.pop(key, None)
    return account


class conf:
    """stores conf.yaml, regenwolken has these config values:
        - HOSTNAME
        - BIND_ADDRESS
        - PORT
        - MONGODB_HOST
        - MONGODB_NAME
        - MONGODB_PORT
        - MONGODB_SESSION_SIZE: size used for the capped collection

        - ALLOWED_CHARS: characters allowed in username
        - MAX_CONTENT_LENGTH: maximum content length before raising 413
        - ALLOW_PRIVATE_BOOKMARKS: True | False
        - PUBLIC_REGISTRATION: instant registration, True | False

        - CACHE_BACKEND: SimpleCache
        - CACHE_TIMEOUT: 15*60

        - THUMBNAILS: True
        - SYNTAX_HIGHLIGHTING: True
        - MARKDOWN_FORMATTING: True
        """

    HOSTNAME = "localhost"
    BIND_ADDRESS = "127.0.0.1"
    PORT = 3000
    LOGFILE = 'rw.log'

    MONGODB_HOST = "127.0.0.1"
    MONGODB_PORT = 27017
    MONGODB_NAME = 'cloudapp'
    MONGODB_SESSION_SIZE = 100*1024

    ALLOWED_CHARS = string.digits + string.ascii_letters + '.- @'
    MAX_CONTENT_LENGTH = 64*1024*1024
    ALLOW_PRIVATE_BOOKMARKS = False
    PUBLIC_REGISTRATION = False
    SHORT_ID_MIN_LENGTH = 3

    CACHE_BACKEND = 'SimpleCache'
    CACHE_TIMEOUT = 15*60

    THUMBNAILS = True
    SYNTAX_HIGHLIGHTING = True
    MARKDOWN_FORMATTING = True


def thumbnail(fp, size=128, bs=2048):
    """generate png thumbnails"""

    p = ImageFile.Parser()

    try:
        while True:
            s = fp.read(bs)
            if not s:
                break
            p.feed(s)

        img = p.close()
        img.thumbnail((size, size))
        op = io.BytesIO()
        img.save(op, 'PNG')
        op.seek(0)
        return op.read().encode('base64')
    except IOError:
        raise


class Struct:
    """dict -> class, http://stackoverflow.com/questions/1305532/convert-python-dict-to-object"""
    def __init__(self, **entries):
        self.__dict__.update(entries)


def ppsize(num):
    '''pretty-print filesize.
    http://blogmag.net/blog/read/38/Print_human_readable_file_size'''
    for x in ['bytes','KiB','MiB','GiB','TB']:
        if num < 1024.0:
            return "%3.2f %s" % (num, x)
        num /= 1024.0

########NEW FILE########
__FILENAME__ = views
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from time import gmtime, strftime
from random import getrandbits
from os.path import basename

from base64 import standard_b64decode

from urllib import unquote
from urlparse import urlparse

from werkzeug import Response
from pymongo import DESCENDING
from flask import request, abort, jsonify, json, current_app, render_template, redirect

from regenwolken.utils import login, private, A1, slug, thumbnail, clear, urlscheme
from regenwolken.specs import Item, Account, Drop


def index():
    """Upload a file, when the client has a valid session key.

    -- http://developer.getcloudapp.com/upload-file"""

    db, fs = current_app.db, current_app.fs
    config, sessions = current_app.config, current_app.sessions

    if request.method == 'POST' and not request.accept_mimetypes.accept_html:

        try:
            account = sessions.pop(request.form.get('key'))['account']
        except KeyError:
            abort(401)

        acc = db.accounts.find_one({'email': account})
        source = request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0]
        privacy = request.form.get('acl', acc['private_items'])

        _id = fs.upload_file(config, account, request.files.get('file'), source, privacy)

        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

        obj = fs.get(_id)

        if obj is None:
            abort(400)
        else:
            return jsonify(Item(obj, config, urlscheme(request)))
    else:
        users = db.accounts.find().count()
        files = fs.gfs._GridFS__files.count()
        size = sum([f['length'] for f in fs.gfs._GridFS__files.find()])
        hits = sum([f['view_counter'] for f in fs.mdb.find()])

        if request.args.get('format') == 'csv':
            fields = [('users', users), ('files', files), ('size', size), ('hits', hits)]
            return Response('\n'.join('%s,%s' % field for field in fields), 200)

        return Response(render_template("index.html", **locals()), 200, content_type="text/html")


@login
def account():
    """Return account details and/or update given keys.

    -- http://developer.getcloudapp.com/view-account-details
    -- http://developer.getcloudapp.com/change-default-security
    -- http://developer.getcloudapp.com/change-email
    -- http://developer.getcloudapp.com/change-password

    PUT: accepts every new password (stored in plaintext) and similar to /register
    no digit-only "email" address is allowed."""

    conf, db = current_app.config, current_app.db
    account = db.accounts.find_one({'email': request.authorization.username})

    if request.method == 'GET':
        return jsonify(clear(account))

    try:
        _id = account['_id']
        data = json.loads(request.data)['user']
    except ValueError:
        return ('Unprocessable Entity', 422)

    if len(data.keys()) == 1 and 'private_items' in data:
        db.accounts.update({'_id': _id}, {'$set': {'private_items': data['private_items']}})
        account['private_items'] = data['private_items']
    elif len(data.keys()) == 2 and 'current_password' in data:
        if not account['passwd'] == A1(account['email'], data['current_password']):
            return abort(403)

        if 'email' in data:
            if filter(lambda c: not c in conf['ALLOWED_CHARS'], data['email']) \
            or data['email'].isdigit(): # no numbers allowed
                abort(400)
            if db.accounts.find_one({'email': data['email']}) and \
            account['email'] != data['email']:
                return ('User already exists', 406)

            new = {'email': data['email'],
                   'passwd': A1(data['email'], data['current_password'])}
            db.accounts.update({'_id': _id}, {'$set': new})
            account['email'] = new['email']
            account['passwd'] = new['passwd']

        elif 'password' in data:
            passwd = A1(account['email'], data['password'])
            db.accounts.update({'_id': _id}, {'$set': {'passwd': passwd}})
            account['passwd'] = passwd

        else:
            abort(400)

    db.accounts.update({'_id': account['_id']}, {'$set':
            {'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())}})

    return jsonify(clear(account))


@login
def account_stats():
    """Show current item count and other statistics.

    -- http://developer.getcloudapp.com/view-account-stats"""

    email = request.authorization.username
    items = current_app.db.accounts.find_one({'email': email})['items']
    views = 0
    for item in items:
        views += current_app.db.items.find_one({'_id': item})['view_counter']

    return jsonify({'items': len(items), 'views': views})


@login
def items():
    """Show items from user.  Optional query parameters:

            - page (int)     - default: 1
            - per_page (int) - default: 5
            - type (str)     - default: None, filter by image, bookmark, text,
                                             archive, audio, video, or unknown
            - deleted (bool) - default: False, show trashed items

    -- http://developer.getcloudapp.com/list-items"""

    db, fs = current_app.db, current_app.fs

    ParseResult = urlparse(request.url)
    params = {'per_page': '5', 'page': '1', 'type': None, 'deleted': False,
              'source': None}

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        params.update(query)

    listing = []
    try:
        pp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        abort(400)

    query = {'account': email}
    if params['type'] != None:
        query['item_type'] = params['type']
    if params['deleted'] == False:
        query['deleted_at'] = None
    if params['source'] != None:
        query['source'] = {'$regex': '^' + unquote(params['source'])}

    items = db.items.find(query)
    for item in items.sort('updated_at', DESCENDING)[pp*(page-1):pp*page]:
        listing.append(Item(fs.get(_id=item['_id']),
                            current_app.config, urlscheme(request)))
    return json.dumps(listing[::-1])


@login
def items_new():
    """Generates a new key for the upload process.  Timeout after 60 minutes!

    -- http://developer.getcloudapp.com/upload-file
    -- http://developer.getcloudapp.com/upload-file-with-specific-privacy"""

    acc = current_app.db.accounts.find_one({'email': request.authorization.username})
    ParseResult = urlparse(request.url)
    privacy = 'private' if acc['private_items'] else 'public-read'

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        privacy = 'private' if query.get('item[private]', None) else 'public-read'


    key = current_app.sessions.new(request.authorization.username)
    res = { "url": urlscheme(request) + '://' + current_app.config['HOSTNAME'],
          "max_upload_size": current_app.config['MAX_CONTENT_LENGTH'],
          "params": { "acl": privacy,
                      "key": key
                    },
        }

    return jsonify(res)


@private(lambda req: req.accept_mimetypes.accept_html)
def items_view(short_id):
    """View item details or show them in the web interface based on Accept-Header or
    returns 404 if the requested short_id does not exist.

    -- http://developer.getcloudapp.com/view-item"""

    db, fs = current_app.db, current_app.fs
    obj = fs.get(short_id=short_id)

    if obj is None:
        abort(404)

    if request.accept_mimetypes.accept_html:

        if getattr(obj, 'deleted_at', None):
            abort(404)

        if obj.item_type != 'image':
            # the browser always loads the blob, so we don't want count it twice
            fs.inc_count(obj._id)

        if obj.item_type == 'bookmark':
            return redirect(obj.redirect_url)

        drop = Drop(obj, current_app.config, urlscheme(request))
        if drop.item_type == 'image':
            return render_template('image.html', drop=drop)
        elif drop.item_type == 'text':
            return render_template('text.html', drop=drop)
        else:
            return render_template('other.html', drop=drop)
    return jsonify(Item(obj, current_app.config, urlscheme(request)))


@login
def items_edit(object_id):
    """rename/delete/change privacy of an item.

    -- http://developer.getcloudapp.com/rename-item
    -- http://developer.getcloudapp.com/delete-item
    -- http://developer.getcloudapp.com/change-security-of-item"""

    conf, db, fs = current_app.config, current_app.db, current_app.fs
    item = db.items.find_one({'account': request.authorization.username,
                              '_id': object_id})
    if not item:
        abort(404)

    if request.method == 'DELETE':
        item['deleted_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    elif request.method == 'PUT':
        try:
            data = json.loads(request.data)['item']
            key, value = data.items()[0]
            if not key in ['private', 'name', 'deleted_at']: raise ValueError
        except ValueError:
            return ('Unprocessable Entity', 422)

        if key == 'name' and item['item_type'] != 'bookmark':
            item['filename'] = value
        elif key == 'private' and item['item_type'] == 'bookmark' and value \
        and not conf['ALLOW_PRIVATE_BOOKMARKS']:
            pass
        else:
            item[key] = value

        item['updated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    db.items.save(item)
    item = fs.get(item['_id'])
    return jsonify(Item(item, conf, urlscheme(request)))


@private(lambda req: True)
def blob(short_id, filename):
    """returns bookmark or file either as direct download with human-readable,
    original filename or inline display using whitelisting"""

    fs = current_app.fs

    obj = fs.get(short_id=short_id)
    if obj is None or getattr(obj, 'deleted_at', None):
        abort(404)

    # views++
    fs.inc_count(obj._id)

    if obj.item_type == 'bookmark':
        return redirect(obj.redirect_url)
    elif not obj.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(obj, content_type=obj.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(obj.filename)})
    return Response(obj, content_type=obj.content_type)


@login
def trash():
    """No official API call yet.  Trash items marked as deleted. Usage:
    curl -u user:pw --digest -H "Accept: application/json" -X POST http://my.cl.ly/items/trash"""

    empty = current_app.db.items.find(
        {'account': request.authorization.username, 'deleted_at': {'$ne': None}})

    for item in empty:
        current_app.fs.delete(item)

    return '', 200


def register():
    """Registration of new users (no digits-only usernames are allowed), if
    PUBLIC_REGISTRATION is set to True new accounts are instantly activated. Otherwise
    you have to do it manually via `manage.py activate $USER`.

    -- http://developer.getcloudapp.com/register"""

    conf, db = current_app.config, current_app.db

    if len(request.data) > 200:
        return ('Request Entity Too Large', 413)
    try:
        d = json.loads(request.data)
        email = d['user']['email']
        if email.isdigit(): raise ValueError # no numbers as username allowed
        passwd = d['user']['password']
    except (ValueError, KeyError):
        return ('Bad Request', 422)

    # TODO: allow more characters, unicode -> ascii, before filter
    if filter(lambda c: not c in conf['ALLOWED_CHARS'], email):
        return ('Bad Request', 422)

    if db.accounts.find_one({'email': email}) != None:
        return ('User already exists', 406)

    if not db.accounts.find_one({"_id":"autoinc"}):
        db.accounts.insert({"_id":"_inc", "seq": 1})

    account = Account({'email': email, 'passwd': passwd,
                       'id': db.accounts.find_one({'_id': '_inc'})['seq']}, conf)
    db.accounts.update({'_id': '_inc'}, {'$inc': {'seq': 1}})
    if conf['PUBLIC_REGISTRATION']:
        account['activated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    account['_id'] = account['id']
    db.accounts.insert(account)

    return (jsonify(clear(account)), 201)


@login
def bookmark():
    """Yet another URL shortener. This implementation prefixes bookmarks with
    a dash (-) so

    -- http://developer.getcloudapp.com/bookmark-link"""

    conf, db = current_app.config, current_app.db

    # XXX move logic into mongonic.py
    def insert(name, redirect_url):

        acc = db.accounts.find_one({'email': request.authorization.username})

        _id = str(getrandbits(32))
        retry_count = 1
        short_id_length = conf['SHORT_ID_MIN_LENGTH']

        while True:
            short_id = slug(short_id_length)
            if not db.items.find_one({'short_id': short_id}):
                break
            else:
                retry_count += 1
                if retry_count > 3:
                    short_id_length += 1
                    retry_count = 1

        x = {
            'account': request.authorization.username,
            'name': name,
            '_id': _id,
            'short_id': slug(short_id_length),
            'redirect_url': redirect_url,
            'item_type': 'bookmark',
            'view_counter': 0,
            'private': request.form.get('acl', acc['private_items'])
                if conf['ALLOW_PRIVATE_BOOKMARKS'] else False,
            'source': request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0],
            'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
            'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        }

        item = Item(x, conf, urlscheme(request))
        db.items.insert(x)

        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

        return item

    try:
        data = json.loads(request.data)
        data = data['item']
    except (ValueError, KeyError):
        return ('Unprocessable Entity', 422)

    if isinstance(data, list):
        return json.dumps([insert(d['name'], d['redirect_url']) for d in data])
    else:
        return jsonify(insert(data['name'], data['redirect_url']))


@private(lambda req: True)
def thumb(short_id):
    """returns 128px thumbnail, when possible and cached for 30 minutes,
    otherwise item_type icons."""

    # th = cache.get('thumb-'+short_id)
    # if th: return Response(standard_b64decode(th), 200, content_type='image/png')

    rv = current_app.fs.get(short_id=short_id)
    if rv is None or getattr(obj, 'deleted_at', None):
        abort(404)

    if rv.item_type == 'image' and current_app.config['THUMBNAILS']:
        try:
            th = thumbnail(rv)
            # cache.set('thumb-'+short_id, th)
            return Response(standard_b64decode(th), 200, content_type='image/png')
        except IOError:
            pass
    return Response(open('wolken/static/images/item_types/%s.png' % rv.item_type),
                    200, content_type='image/png')


def domains(domain):
    """Returns HOSTNAME. Always."""
    return jsonify({"home_page": "http://%s" % current_app.config['HOSTNAME']})

########NEW FILE########
