__FILENAME__ = generate_data
#!/usr/bin/env python
import hashlib
import json
import os
import random
import sqlite3
import string
import sys

def random_string(length=7):
    return ''.join(random.choice(string.ascii_lowercase) for x in range(length))

def main(basedir, level03, proof, plans):
    print 'Generating users.db'
    conn = sqlite3.connect(os.path.join(basedir, 'users.db'))
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(255),
        password_hash VARCHAR(255),
        salt VARCHAR(255)
    );""")

    id = 1
    dict = {}

    list = [('bob', level03), ('eve', proof), ('mallory', plans)]
    random.shuffle(list)
    for username, secret in list:
        password = random_string()
        salt = random_string()
        password_hash = hashlib.sha256(password + salt).hexdigest()
        print '- Adding {0}'.format(username)
        cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", (username, password_hash, salt))

        dict[id] = secret
        id += 1

    conn.commit()

    print 'Generating secrets.json'
    f = open(os.path.join(basedir, 'secrets.json'), 'w')
    json.dump(dict,
              f,
              indent=2)
    f.write('\n')

    print 'Generating entropy.dat'
    f = open(os.path.join(basedir, 'entropy.dat'), 'w')
    f.write(os.urandom(24))

if __name__ == '__main__':
    if not len(sys.argv) == 5:
        print 'Usage: %s <basedir> <level03> <proof> <plans>' % sys.argv[0]
        sys.exit(1)
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = secretvault
#!/usr/bin/env python
#
# Welcome to the Secret Safe!
#
# - users/users.db stores authentication info with the schema:
#
# CREATE TABLE users (
#   id VARCHAR(255) PRIMARY KEY AUTOINCREMENT,
#   username VARCHAR(255),
#   password_hash VARCHAR(255),
#   salt VARCHAR(255)
# );
#
# - For extra security, the dictionary of secrets lives
#   data/secrets.json (so a compromise of the database won't
#   compromise the secrets themselves)

import flask
import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
from werkzeug import debug

# Generate test data when running locally
data_dir = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_dir):
    import generate_data
    os.mkdir(data_dir)
    generate_data.main(data_dir, 'dummy-password', 'dummy-proof', 'dummy-plans')

secrets = json.load(open(os.path.join(data_dir, 'secrets.json')))
index_html = open('index.html').read()
app = flask.Flask(__name__)

# Turn on backtraces, but turn off code execution (that'd be an easy level!)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.wsgi_app = debug.DebuggedApplication(app.wsgi_app, evalex=False)

app.logger.addHandler(logging.StreamHandler(sys.stderr))
# use persistent entropy file for secret_key
app.secret_key = open(os.path.join(data_dir, 'entropy.dat')).read()

# Allow setting url_root if needed
try:
    from local_settings import url_root
except ImportError:
    pass

def absolute_url(path):
    return url_root + path

@app.route('/')
def index():
    try:
        user_id = flask.session['user_id']
    except KeyError:
        return index_html
    else:
        secret = secrets[str(user_id)]
        return (u'Welcome back! Your secret is: "{0}"'.format(secret) +
                u' (<a href="./logout">Log out</a>)\n')

@app.route('/logout')
def logout():
    flask.session.pop('user_id', None)
    return flask.redirect(absolute_url('/'))

@app.route('/login', methods=['POST'])
def login():
    username = flask.request.form.get('username')
    password = flask.request.form.get('password')

    if not username:
        return "Must provide username\n"

    if not password:
        return "Must provide password\n"

    conn = sqlite3.connect(os.path.join(data_dir, 'users.db'))
    cursor = conn.cursor()

    query = """SELECT id, password_hash, salt FROM users
               WHERE username = '{0}' LIMIT 1""".format(username)
    cursor.execute(query)

    res = cursor.fetchone()
    if not res:
        return "There's no such user {0}!\n".format(username)
    user_id, password_hash, salt = res

    calculated_hash = hashlib.sha256(password + salt)
    if calculated_hash.hexdigest() != password_hash:
        return "That's not the password for {0}!\n".format(username)

    flask.session['user_id'] = user_id
    return flask.redirect(absolute_url('/'))

if __name__ == '__main__':
    # In development: app.run(debug=True)
    app.run()

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
import hashlib
import json
import sys
import urllib

import requests

class ClientError(Exception):
    pass

class Client(object):
    def __init__(self, endpoint, user_id, api_secret):
        self.endpoint = endpoint
        self.user_id = user_id
        self.api_secret = api_secret

    def order(self, waffle_name, coords, count=1):
        """Order one or more waffles."""
        params = {'waffle': waffle_name, 'count': count,
                  'lat': coords[0], 'long': coords[1]}
        return self.api_call('/orders', params)

    def api_call(self, path, params, debug_response=False):
        """Make an API call with parameters to the specified path."""
        body = self._make_post(params)
        resp = requests.post(self.endpoint + path, data=body)

        # for debugging
        if debug_response:
            return resp

        # try to decode response as json
        data = None
        if resp.headers['content-type'] == 'application/json':
            try:
                data = json.loads(resp.text)
            except ValueError:
                pass
            else:
                # raise error message if any
                error = data.get('error')
                if error:
                    raise ClientError(error)

        # raise error on non-200 status codes
        resp.raise_for_status()

        # return response data decoded from JSON or just response body
        return data or resp.text

    def _make_post(self, params):
        params['user_id'] = self.user_id
        body = urllib.urlencode(params)

        sig = self._signature(body)
        body += '|sig:' + sig

        return body

    def _signature(self, message):
        h = hashlib.sha1()
        h.update(self.api_secret + message)
        return h.hexdigest()

if __name__ == '__main__':
    if len(sys.argv) != 7:
        print 'usage: client.py ENDPOINT USER_ID SECRET WAFFLE LAT LONG'
        sys.exit(1)

    c = Client(*sys.argv[1:4])
    print c.order(sys.argv[4], sys.argv[5:7])

########NEW FILE########
__FILENAME__ = db
import os
import sqlite3
import sys

class NotFound(Exception):
    pass
class ManyFound(Exception):
    pass

# for app.secret_key
def rewrite_entropy_file(path):
    f = open(path, 'w')
    f.write(os.urandom(24))
    f.close()

class DB(object):
    def __init__(self, database):
        self.conn = sqlite3.connect(database,
                                    detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.debug = False

    def log(self, *args):
        if self.debug:
            for i in args:
                sys.stderr.write(str(i))
            sys.stderr.write('\n')

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

    def select(self, table, where=None):
        if where is None:
            where = {}
        self.do_select(table, where)
        return map(dict, self.cursor.fetchall())

    def select_one(self, table, where=None):
        where = where or {}
        self.do_select(table, where)

        row = self.cursor.fetchone()
        if row is None:
            raise NotFound

        if self.cursor.fetchone() is not None:
            raise ManyFound

        return dict(row)

    def do_select(self, table, where=None):
        where = where or {}
        where_clause = ' AND '.join('%s=?' % key for key in where.iterkeys())
        values = where.values()
        q = 'select * from ' + str(table)
        if where_clause:
            q += ' where ' + where_clause
        self.log(q, '<==', values)
        self.cursor.execute(q, values)

    def insert(self, table, data):
        cols = ', '.join(data.keys())
        vals = data.values()
        placeholders = ', '.join('?' for i in data)
        q = 'insert into %s (%s) values (%s)' % (table, cols, placeholders)
        self.log(q, '<==', vals)
        self.cursor.execute(q, vals)
        self.commit()
        return self.cursor.rowcount

########NEW FILE########
__FILENAME__ = initialize_db
#!/usr/bin/env python
import sys
from datetime import datetime
from random import SystemRandom

import bcrypt
import sqlite3

import client
import db
import settings

conn = db.DB(settings.database)
conn.debug = True
c = conn.cursor

db.rewrite_entropy_file(settings.entropy_file)

rand = SystemRandom()

def rand_choice(alphabet, length):
    return ''.join(rand.choice(alphabet) for i in range(length))

alphanum = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
def rand_alnum(length):
    return rand_choice(alphanum, length)

def main(level_password):
    create_tables()
    add_users()
    add_waffles(level_password)
    add_logs()

def add_users():
    add_user(1, 'larry', rand_alnum(16), 1)
    add_user(2, 'randall', rand_alnum(16), 1)
    add_user(3, 'alice', rand_alnum(16), 0)
    add_user(4, 'bob', rand_alnum(16), 0)
    add_user(5, 'ctf', 'password', 0)

def add_waffles(level_password):
    add_waffle('liege', 1, level_password)
    add_waffle('dream', 1, rand_alnum(14))
    add_waffle('veritaffle', 0, rand_alnum(14))
    add_waffle('chicken', 1, rand_alnum(14))
    add_waffle('belgian', 0, rand_alnum(14))
    add_waffle('brussels', 0, rand_alnum(14))
    add_waffle('eggo', 0, rand_alnum(14))

def add_logs():
    gen_log(1, '/orders', {'waffle': 'eggo', 'count': 10,
                           'lat': 37.351, 'long': -119.827})
    gen_log(1, '/orders', {'waffle': 'chicken', 'count': 2,
                           'lat': 37.351, 'long': -119.827})
    gen_log(2, '/orders', {'waffle': 'dream', 'count': 2,
                           'lat': 42.39561, 'long': -71.13051},
            date=datetime(2007, 9, 23, 14, 38, 00))
    gen_log(3, '/orders', {'waffle': 'veritaffle', 'count': 1,
                           'lat': 42.376, 'long': -71.116})

def create_tables():
    c.execute('drop table if exists users')
    c.execute('''
    CREATE TABLE users(
    id int not null primary key,
    name varchar(255) not null,
    password varchar(255) not null,
    premium int not null,
    secret varchar(255) not null,
    unique (name)
    )
    ''')

    c.execute('drop table if exists waffles')
    c.execute('''
    CREATE TABLE waffles(
    name varchar(255) not null primary key,
    premium int not null,
    confirm varchar(255) not null
    )
    ''')

    c.execute('drop table if exists logs')
    c.execute('''
    CREATE TABLE logs(
    user_id int not null,
    path varchar(255) not null,
    body text not null,
    date timestamp not null default current_timestamp
    )
    ''')
    c.execute('create index user_id on logs (user_id)')
    c.execute('create index date on logs (date)')

def add_user(uid, username, password, premium):
    hashed = bcrypt.hashpw(password, bcrypt.gensalt(10))
    secret = rand_alnum(14)
    data = {'id': uid, 'name': username, 'password': hashed,
            'premium': premium, 'secret': secret}
    conn.insert('users', data)

def get_user(uid):
    return conn.select_one('users', {'id': uid})

def add_waffle(name, premium, confirm):
    data = {'name': name, 'premium': premium, 'confirm': confirm}
    conn.insert('waffles', data)

def gen_log(user_id, path, params, date=None):
    user = get_user(user_id)

    # generate signature using client library
    cl = client.Client(None, user_id, user['secret'])
    body = cl._make_post(params)

    # prepare data for insert
    data = {'user_id': user_id, 'path': path, 'body': body}

    if date:
        data['date'] = date

    conn.insert('logs', data)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage: initialize_db.py LEVEL_PASSWORD'
        sys.exit(1)

    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = settings
import os

DEBUG = False
database = os.path.join(os.path.dirname(__file__), 'wafflecopter.db')
entropy_file = os.path.join(os.path.dirname(__file__), 'entropy.dat')

url_root = ''

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = wafflecopter
#!/usr/bin/env python
import hashlib
import json
import logging
import os
import sys
import urllib
from functools import wraps

import bcrypt
import sqlite3
from flask import Flask, session, request, redirect, render_template, g, abort
from flask import make_response

import db
import settings

app = Flask(__name__)
app.config.from_object(settings)
app.logger.addHandler(logging.StreamHandler(sys.stderr))


if not os.path.exists(settings.entropy_file):
    print 'Entropy file not found. Have you run initialize_db.py?'

# use persistent entropy file for secret_key
app.secret_key = open(settings.entropy_file, 'r').read()

class BadSignature(Exception):
    pass
class BadRequest(Exception):
    pass

def valid_user(user, passwd):
    try:
        row = g.db.select_one('users', {'name': user})
    except db.NotFound:
        print 'Invalid user', repr(user)
        return False
    if bcrypt.hashpw(passwd, row['password']) == row['password']:
        print 'Valid user:', repr(user)
        return row
    else:
        print 'Invalid password for', repr(user)
        return False

def log_in(user, row):
    session['user'] = row
    session['username'] = user

def absolute_url(path):
    return settings.url_root + path

def require_authentication(func):
    @wraps(func)
    def newfunc(*args, **kwargs):
        if 'user' not in session:
            return redirect(absolute_url('/login'))
        return func(*args, **kwargs)
    return newfunc

def json_response(obj, status_code=200):
    text = json.dumps(obj) + '\n'
    resp = make_response(text, status_code)
    resp.headers['content-type'] = 'application/json'
    return resp

def json_error(message, status_code):
    return json_response({'error': message}, status_code)

def log_api_request(user_id, path, body):
    if isinstance(body, str):
        # body is a string byte stream, but sqlite will think it's utf-8
        # convert each character to unicode so it's unambiguous
        body = ''.join(unichr(ord(c)) for c in body)
    g.db.insert('logs', {'user_id': user_id, 'path': path, 'body': body})

def get_logs(user_id):
    return g.db.select('logs', {'user_id': user_id})

def get_waffles():
    return g.db.select('waffles')

@app.before_request
def before_request():
    g.db = db.DB(settings.database)
    g.cursor = g.db.cursor

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.commit()
        g.db.close()

@app.route('/')
@require_authentication
def index():
    user = session['user']
    waffles = get_waffles()
    return render_template('index.html', user=user, waffles=waffles,
                           endpoint=request.url_root)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = request.form['username']
        password = request.form['password']
        row = valid_user(user, password)
        if row:
            log_in(user, row)
            return redirect(absolute_url('/'))
        else:
            error = 'Invalid username or password'

    return render_template('login.html', error=error)

@app.route('/logs/<int:id>')
@require_authentication
def logs(id):
    rows = get_logs(id)
    return render_template('logs.html', logs=rows)

def verify_signature(user_id, sig, raw_params):
    # get secret token for user_id
    try:
        row = g.db.select_one('users', {'id': user_id})
    except db.NotFound:
        raise BadSignature('no such user_id')
    secret = str(row['secret'])

    h = hashlib.sha1()
    h.update(secret + raw_params)
    print 'computed signature', h.hexdigest(), 'for body', repr(raw_params)
    if h.hexdigest() != sig:
        raise BadSignature('signature does not match')
    return True

def parse_params(raw_params):
    pairs = raw_params.split('&')
    params = {}
    for pair in pairs:
        key, val = pair.split('=')
        key = urllib.unquote_plus(key)
        val = urllib.unquote_plus(val)
        params[key] = val
    return params

def parse_post_body(body):
    try:
        raw_params, sig = body.strip('\n').rsplit('|sig:', 1)
    except ValueError:
        raise BadRequest('Request must be of form params|sig:da39a3ee5e6b...')

    return raw_params, sig

def process_order(params):
    user = g.db.select_one('users', {'id': params['user_id']})

    # collect query parameters
    try:
        waffle_name = params['waffle']
    except KeyError:
        return json_error('must specify waffle', 400)
    try:
        count = int(params['count'])
    except (KeyError, ValueError):
        return json_error('must specify count', 400)
    try:
        lat, long = float(params['lat']), float(params['long'])
    except (KeyError, ValueError):
        return json_error('where would you like your waffle today?', 400)

    if count < 1:
        return json_error('count must be >= 1', 400)

    # get waffle info
    try:
        waffle = g.db.select_one('waffles', {'name': waffle_name})
    except db.NotFound:
        return json_error('no such waffle: %s' % waffle_name, 404)

    # check premium status
    if waffle['premium'] and not user['premium']:
        return json_error('that waffle requires a premium subscription', 402)

    # return results
    plural = 's' if count > 1 else ''
    msg = 'Great news: %d %s waffle%s will soon be flying your way!' \
        % (count, waffle_name, plural)
    return json_response({'success': True, 'message': msg,
                          'confirm_code': waffle['confirm']})

@app.route('/orders', methods=['POST'])
def order():
    # We need the original POST body in order to check the hash, so we use
    # request.input_stream rather than request.form.
    request.shallow = True
    body = request.input_stream.read(
        request.headers.get('content-length', type=int) or 0)

    # parse POST body
    try:
        raw_params, sig = parse_post_body(body)
    except BadRequest, e:
        print 'failed to parse', repr(body)
        return json_error(e.message, 400)

    print 'raw_params:', repr(raw_params)

    try:
        params = parse_params(raw_params)
    except ValueError:
        raise BadRequest('Could not parse params')

    print 'sig:', repr(sig)

    # look for user_id and signature
    try:
        user_id = params['user_id']
    except KeyError:
        print 'user_id not provided'
        return json_error('must provide user_id', 401)

    # check that signature matches
    try:
        verify_signature(user_id, sig, raw_params)
    except BadSignature, e:
        return json_error('signature check failed: ' + e.message, 401)

    # all OK -- process the order
    log_api_request(params['user_id'], '/orders', body)
    return process_order(params)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9233)


########NEW FILE########
__FILENAME__ = common
import atexit
import json
import logging
import os

from twisted.internet import reactor, protocol
from twisted.protocols import basic

from twisted.web import server, resource, client

logger = logging.getLogger('password_db.common')


class Halt(Exception):
    pass


class HTTPServer(object, resource.Resource):
    isLeaf = True

    def __init__(self, processor, args):
        self.processor = processor
        self.args = args

    def render_GET(self, request):
        return ('{"success": false, "message": "GET not supported.'
                ' Try POSTing instead."}\n')

    def render_POST(self, request):
        processor_instance = self.processor(request, self.args)
        processor_instance.processRaw()
        return server.NOT_DONE_YET

class PayloadProcessor(object):
    request_count = 0

    def __init__(self, request):
        PayloadProcessor.request_count += 1
        self.request_id = PayloadProcessor.request_count
        self.request = request

    def processRaw(self):
        raw_data = self.request.content.read()
        self.log_info('Received payload: %r', raw_data)

        try:
            parsed = json.loads(raw_data)
        except ValueError as e:
            self.respondWithMessage('Could not parse message: %s' % e)
            return

        try:
            self.process(parsed)
        except Halt:
            pass

    # API method
    def process(self, data):
        raise NotImplementedError

    # Utility methods
    def getArg(self, data, name):
        try:
            return data[name]
        except KeyError:
            self.respondWithMessage('Missing required param: %s' % name)
            raise Halt()

    def respondWithMessage(self, message):
        response = {
            'success' : False,
            'message' : message
            }
        self.respond(response)

    def respond(self, response):
        if self.request.notifyFinish():
            self.log_error("Request already finished!")
        formatted = json.dumps(response) + '\n'
        self.log_info('Responding with: %r', formatted)
        self.request.write(formatted)
        self.request.finish()

    def log_info(self, *args):
        self.log('info', *args)

    def log_error(self, *args):
        self.log('error', *args)

    def log(self, level, msg, *args):
        # Make this should actually be handled by a formatter.
        client = self.request.client
        try:
            host = client.host
            port = client.port
        except AttributeError:
            prefix = '[%r:%d] '  % (client, self.request_id)
        else:
            prefix = '[%s:%d:%d] '  % (host, port, self.request_id)
        method = getattr(logger, level)
        interpolated = msg % args
        method(prefix + interpolated)

def chunkPassword(chunk_count, password, request=None):
    # Equivalent to ceil(password_length / chunk_count)
    chunk_size = (len(password) + chunk_count - 1) / chunk_count

    chunks = []
    for i in xrange(0, len(password), chunk_size):
        chunks.append(password[i:i+chunk_size])

    while len(chunks) < chunk_count:
        chunks.append('')

    msg = 'Split length %d password into %d chunks of size about %d: %r'
    args = [len(password), chunk_count, chunk_size, chunks]
    if request:
        request.log_info(msg, *args)
    else:
        logger.info(msg, *args)

    return chunks

def isUnix(spec):
    return spec.startswith('unix:')

def parseHost(host):
    host, port = host.split(':')
    port = int(port)
    return host, port

def parseUnix(unix):
    path = unix[len('unix:'):]
    return path

def makeRequest(address_spec, data, callback, errback):
    # Change the signature of the errback
    def wrapper(error):
        errback(address_spec, error)

    host, port = address_spec
    factory = client.HTTPClientFactory('/',
                                       agent='PasswordChunker',
                                       method='POST',
                                       postdata=json.dumps(data))
    factory.deferred.addCallback(callback)
    factory.deferred.addErrback(wrapper)
    reactor.connectTCP(host, port, factory)

def listenTCP(address_spec, http_server):
    host, port = address_spec
    site = server.Site(http_server)
    reactor.listenTCP(port, site, 50, host)

def cleanupSocket(path):
    try:
        os.remove(path)
    except OSError:
        pass

def listenUNIX(path, http_server):
    site = server.Site(http_server)
    reactor.listenUNIX(path, site, 50)
    atexit.register(cleanupSocket, path)

########NEW FILE########
