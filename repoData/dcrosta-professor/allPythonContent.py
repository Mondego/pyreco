__FILENAME__ = forms
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('LoginForm', 'DatabaseForm', 'PreferencesForm')

from wtforms import *
from wtforms.validators import *

from professor import app, db

from pytz import common_timezones
timezones = [(x, x) for x in common_timezones]

class LoginForm(Form):
    username = TextField(validators=[Required()])
    password = PasswordField(validators=[Required()])

class DatabaseForm(Form):
    hostname = TextField(label='Host:Port', validators=[Required()])
    dbname = TextField(label='Database', validators=[Required()])
    username = TextField()
    password = PasswordField()

    def validate(self):
        if not super(DatabaseForm, self).validate():
            return False
        return db.databases.find_one({
            'hostname': self.hostname.data,
            'dbname': self.dbname.data}) is None

class PreferencesForm(Form):
    referrer = HiddenField()
    timezone = SelectField(choices=timezones, default='UTC')


########NEW FILE########
__FILENAME__ = logic
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('update', 'parse', 'aggregate')

from datetime import datetime
from pymongo import ASCENDING, DESCENDING

from professor import app, db
from professor.skeleton import skeleton, sanitize
from professor.util import *

PARSERS = {}
def parser(optype):
    def inner(func):
        PARSERS[optype] = func
        return func
    return inner

GROUPERS = {}
def grouper(optype):
    def inner(func):
        GROUPERS[optype] = func
        return func
    return inner

SUMMARIZERS = {}
def summarizer(optype):
    def inner(func):
        SUMMARIZERS[optype] = func
        return func
    return inner

@parser('query')
def parse_query(entry):
    # {'responseLength': 20,
    #  'millis': 40,
    #  'ts': datetime.datetime(2011, 9, 19, 15, 8, 1, 976000),
    #  'scanAndOrder': True,
    #  'client': '127.0.0.1',
    #  'user': '',
    #  'query': {'$orderby': {'date': 1},
    #            '$query': {'processing.status': 'new'}},
    #  'ns': 'www.formcapture',
    #  'nscanned': 12133,
    #  'op': 'query'}

    query = entry.get('query', {}).get('$query', None)
    if query is None:
        query = entry.get('query', {})

    orderby = entry.get('query', {}).get('$orderby', None)
    if orderby is None:
        orderby = {}

    entry['skel'] = skeleton(query)
    entry['sort'] = skeleton(orderby)
    return True

def parse(database, entry):
    collection = entry['ns']
    collection = collection[len(database['dbname']) + 1:]
    entry['collection'] = collection

    # skip certain namespaces
    if collection.startswith('system.') or \
       collection.startswith('tmp.mr.'):
        return False

    optype = entry.get('op')
    subparser = PARSERS.get(optype)
    if subparser:
        if not subparser(entry):
            return False

    entry = sanitize(entry)
    entry['database'] = database['_id']

    db.profiles.save(entry)
    return True

def update(database):
    now = datetime.utcnow()
    query = {'ts': {'$lt': now}}
    if database['timestamp']:
        query['ts']['$gte'] = database['timestamp']

    query['op'] = {'$in': PARSERS.keys()}

    conndb = connect_to(database)
    i = 0
    for entry in conndb.system.profile.find(query):
        if parse(database, entry):
            i += 1

    database['timestamp'] = now
    db.databases.save(database)

    return i

@grouper('query')
def group_by_skel(last_entry, entry):
    return last_entry.get('skel') is not None and \
           last_entry.get('skel') == entry.get('skel') and \
           last_entry.get('collection') == entry.get('collection')

@summarizer('query')
def summarize_timings(entries):
    times = [e['millis'] for e in entries]
    info = {
        'total': sum(times),
        'min': min(times),
        'max': max(times),
        'avg': avg(times),
        'median': median(times),
        'stddev': stddev(times),
        'histogram': loghistogram(times),
    }
    out = entries[0]
    out['count'] = len(times)
    out['times'] = info
    return out

def aggregate(database, optype, collection=None):

    query = {'database': database['_id'], 'op': optype}
    if collection is not None:
        query['collection'] = collection

    entries = db.profiles.find(query).sort([
        ('collection', ASCENDING),
        ('op', ASCENDING),
        ('skel', ASCENDING),
    ])

    last_entry = None
    group = []
    for entry in entries:
        if last_entry is None:
            last_entry = entry
        if not GROUPERS[optype](last_entry, entry):
            if group:
                yield SUMMARIZERS[optype](group)
            group = []
        group.append(entry)
        last_entry = entry

    if group:
        yield SUMMARIZERS[optype](group)


########NEW FILE########
__FILENAME__ = scripts
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
from pymongo import ASCENDING, DESCENDING
import re
import time

from professor import db
from professor.logic import *

db_name = re.compile('(\S+)/(\S+)')

def do_list(parser, args):
    print 'Known Databases:'
    for d in db.databases.find().sort([('hostname', ASCENDING), ('dbname', ASCENDING)]):
        print "   %s/%s" % (d['hostname'], d['dbname'])

def get_database(parser, args):
    if not hasattr(args, 'databases'):
        args.databases = {}
    if args.database in args.databases:
        return args.databases[args.database]

    m = db_name.match(args.database)
    if not m:
        parser.error('"%s" is not a valid database' % args.database)

    hostname, dbname = m.groups()
    database = db.databases.find_one({'hostname': hostname, 'dbname': dbname})
    if not database:
        parser.error('"%s" is not a known database' % args.database)

    if args.database not in args.databases:
        args.databases[args.database] = database

    return database

def do_update(parser, args):
    database = get_database(parser, args)
    count = update(database)
    print "%s: updated %d entries" % (args.database, count)

def do_reset(parser, args):
    database = get_database(parser, args)
    db.profiles.remove({'database': database['_id']})
    db.databases.update({'_id': database['_id']}, {'$set': {'timestamp': None}})
    print "reset %s" % args.database

def do_clean(parser, args):
    database = get_database(parser, args)
    db.profiles.remove({'database': database['_id']})
    print "cleaned %s" % args.database

def do_remove(parser, args):
    database = get_database(parser, args)
    db.databases.remove({'_id': database['_id']})
    db.profiles.remove({'database': database['_id']})
    print "removed %s" % args.database



def profess():
    parser = argparse.ArgumentParser(description='Painless MongoDB Profiling')
    parser.add_argument('-s', '--seconds', dest='interval', metavar='N', type=int,
                        help='Repeat this command every N seconds', default=None)

    commands = parser.add_subparsers()

    list = commands.add_parser('list', help='List databases known to professor')
    list.set_defaults(cmd=do_list)

    reset = commands.add_parser('reset', help='Erase profiling information and reset last sync timestamp')
    reset.set_defaults(cmd=do_reset)
    reset.add_argument('database', help='Database to clean', nargs='+')

    update = commands.add_parser('update', help="Update a database's profiling information")
    update.set_defaults(cmd=do_update)
    update.add_argument('database', help='Database to update', nargs='+')

    clean = commands.add_parser('clean', help='Delete existing profiling information for database')
    clean.set_defaults(cmd=do_clean)
    clean.add_argument('database', help='Database to clean', nargs='+')

    remove = commands.add_parser('remove', help='Completely remove a database from professor')
    remove.set_defaults(cmd=do_remove)
    remove.add_argument('database', help='Database to remove', nargs='+')


    parser.set_defaults(databases={})
    parser.set_defaults(database=[])
    args = parser.parse_args()

    dbs = args.database
    def run_commands():
        if dbs:
            for database in dbs:
                args.database = database
                args.cmd(parser, args)
        else:
            args.cmd(parser, args)

    run_commands()
    while args.interval is not None:
        time.sleep(args.interval)
        run_commands()

if __name__ == '__main__':
    profess()


########NEW FILE########
__FILENAME__ = session
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('SessionMixin', 'MongoSessionStore')

from datetime import datetime, timedelta

from werkzeug.contrib.sessions import SessionStore

class SessionMixin(object):
    __slots__ = ('session_store',)

    @property
    def session_key(self):
        return self.config.get('SESSION_COOKIE_NAME', '_plog_session')

    def open_session(self, request):
        sid = request.cookies.get(self.session_key, None)
        if sid is not None:
            return self.session_store.get(sid)
        return self.session_store.new()

    def save_session(self, session, response):
        if session.should_save:
            self.session_store.save(session)

            lifetime = self.config.get('PERMANENT_SESSION_LIFETIME', timedelta(minutes=30))
            response.set_cookie(
                self.session_key,
                session.sid,
                max_age=lifetime.seconds + lifetime.days * 24 * 3600,
                expires= datetime.utcnow() + lifetime,
                secure=self.config.get('SESSION_COOKIE_SECURE', False),
                httponly=self.config.get('SESSION_COOKIE_HTTPONLY', False),
                domain=self.config.get('SESSION_COOKIE_DOMAIN', None),
                path=self.config.get('SESSION_COOKIE_PATH', '/'),
            )
        return response

    def end_session(self, session):
        self.session_store.delete(session)

class MongoSessionStore(SessionStore):
    """Subclass of :class:`werkzeug.contrib.sessions.SessionStore`
    which stores sessions using MongoDB documents.
    """

    def __init__(self, collection):
        super(MongoSessionStore, self).__init__()
        self.collection = collection

    def save(self, session):
        self.collection.save({'_id': session.sid, 'data': dict(session)}, safe=True)

    def delete(self, session):
        self.collection.remove({'_id': session.sid}, safe=True)

    def get(self, sid):
        doc = self.collection.find_one({'_id': sid})
        if doc:
            return self.session_class(dict(doc['data']), sid, False)
        else:
            return self.session_class({}, sid, True)


########NEW FILE########
__FILENAME__ = skeleton
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('skeleton', 'sanitize')

from bson.binary import Binary
from bson.code import Code
from bson.dbref import DBRef
from bson.errors import InvalidDocument
from bson.objectid import ObjectId
from bson.son import SON
from datetime import datetime
import re

BSON_TYPES = set([
    int,
    long,
    str,
    unicode,
    bool,
    float,
    datetime,
    ObjectId,
    type(re.compile('')),
    Code,
    type(None),
    Binary,
    DBRef,
    SON,
])


def skeleton(query_part):
    """
    Generate a "skeleton" of a document (or embedded document). A
    skeleton is a (unicode) string indicating the keys present in
    a document, but not the values, and is used to group queries
    together which have identical key patterns regardless of the
    particular values used. Keys in the skeleton are always sorted
    lexicographically.

    Raises :class:`~bson.errors.InvalidDocument` when the document
    cannot be converted into a skeleton (this usually indicates that
    the type of a key or value in the document is not known to
    Professor).

    For example:

        >>> skeleton({'hello': 'World'})
        u'{hello}'
        >>> skeleton({'title': 'My Blog Post', 'author': 'Dan Crosta'})
        u'{author,title}
        >>> skeleton({})
        u'{}'
    """
    t = type(query_part)
    if t == list:
        out = []
        for element in query_part:
            sub = skeleton(element)
            if sub is not None:
                out.append(sub)
        return u'[%s]' % ','.join(out)
    elif t in (dict, SON):
        out = []
        for key in sorted(query_part.keys()):
            sub = skeleton(query_part[key])
            if sub is not None:
                out.append('%s:%s' % (key, sub))
            else:
                out.append(key)
        return u'{%s}' % ','.join(out)
    elif t not in BSON_TYPES:
        raise InvalidDocument('unknown BSON type %r' % t)

def sanitize(value):
    """"Sanitize" a value (e.g. a document) for safe storage
    in MongoDB. Converts periods (``.``) and dollar signs
    (``$``) in key names to escaped versions. See
    :func:`~professor.skeleton.desanitize` for the inverse.
    """
    t = type(value)
    if t == list:
        return map(sanitize, value)
    elif t == dict:
        return dict((k.replace('$', '_$_').replace('.', '_,_'), sanitize(v))
                    for k, v in value.iteritems())
    elif t not in BSON_TYPES:
        raise InvalidDocument('unknown BSON type %r' % t)
    else:
        return value

def desanitize(value):
    """Does the inverse of :func:`~professor.skeleton.sanitize`.
    """
    t = type(value)
    if t == list:
        return map(desanitize, value)
    elif t == dict:
        return dict((k.replace('_$_', '$').replace('_,_', '.'), desanitize(v))
                    for k, v in value.iteritems())
    elif t not in BSON_TYPES:
        raise InvalidDocument('unknown BSON type %r' % t)
    else:
        return value


########NEW FILE########
__FILENAME__ = util
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ('get_or_404', 'avg', 'stddev', 'median', 'loghistogram', 'connect_to')

from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import pymongo
import pytz
import re

from flask import abort, request

from professor import app

def get_or_404(collection, **kwargs):
    if '_id' in kwargs:
        try:
            kwargs['_id'] = ObjectId(kwargs['_id'])
        except InvalidId:
            abort(404)
    obj = collection.find_one(kwargs)
    if obj is None:
        abort(404)
    return obj

def avg(values):
    return sum(map(float, values)) / len(values)

def stddev(values):
    mean = avg(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

def median(values):
    return sorted(values)[len(values) / 2]

@app.template_filter('float')
def floatfmt(value):
    return re.sub('(0+)$', '0', ('%.2f' % value))

from professor.skeleton import desanitize as desanitize_query
@app.template_filter('desanitize')
def desanitize(value):
    def build_out(value):
        if isinstance(value, list):
            return '[%s]' % ', '.join(map(build_out, value))
        elif isinstance(value, dict):
            return '{%s}' % ', '.join(('%s: %s' % (k, build_out(v)) for k, v in value.iteritems()))
        else:
            if isinstance(value, unicode):
                try:
                    return "'%s'" % value
                except:
                    pass
            return repr(value)

    clean = desanitize_query(value)
    out = build_out(clean)
    return out

@app.template_filter('humansize')
def humansize(value):
    value = float(value)
    kb = 1024
    mb = 1024 * kb
    gb = 1024 * mb
    tb = 1024 * gb
    for threshold, label in ((tb, 'TB'), (gb, 'GB'), (mb, 'MB')):
        if value > threshold:
            return '%.2f %s' % (value / threshold, label)

    return '%.2f KB' % (value / kb)

@app.template_filter('strftime')
def strftime(value, fmt):
    if not isinstance(value, datetime):
        return value

    timezone = request.cookies.get('timezone', 'utc')
    timezone = pytz.timezone(timezone)
    if timezone == pytz.utc:
        return value

    value = value.replace(tzinfo=pytz.utc).astimezone(timezone)
    return value.strftime(fmt)


def loghistogram(values, base=2, buckets=8):
    # generate a histogram with logaritmic scale buckets
    # with default params, first bucket will be [0,1),
    # second will be [1,2), third will be [2,4), etc;
    # the last bucket will include up to infinity

    ranges = []
    last = -1
    for i in xrange(buckets):
        next = base ** i
        ranges.append((last + 1, next))
        last = next

    # make the last range include everything
    ranges[-1] = (ranges[-1][0], float('inf'))

    out = []
    for start, end in ranges:
        out.append(sum(1 for value in values if start <= value < end))

    return out

def connect_to(database):
    match = re.match(r'^(?P<host>[^:]+):(?P<port>\d+)$', database['hostname'])
    if match:
        host = match.group('host')
        port = int(match.group('port'))
    else:
        host = database['hostname']
        port = 27017
    conn = pymongo.Connection(
        host=host,
        port=port,
        network_timeout=2,
        slaveok=True,
    )
    conndb = conn[database['dbname']]

    return conndb


########NEW FILE########
__FILENAME__ = views
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from datetime import datetime, timedelta
import pymongo
from pymongo import ASCENDING, DESCENDING
import urllib

from flask import g
from flask import session
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.datastructures import MultiDict

from professor import app, db
from professor.util import *
from professor.forms import *
from professor.skeleton import *
from professor.logic import *

@app.route('/db/new', methods=['GET'])
def new_database():
    form = DatabaseForm()
    return render_template(
        'simpleform.html',
        form=form,
    )

@app.route('/db/new', methods=['POST'])
def save_database():
    form = DatabaseForm(formdata=request.form)
    if form.validate():
        db.databases.save({
            'hostname': form.hostname.data,
            'dbname': form.dbname.data,
            'username': form.username.data,
            'password': form.password.data,
            'timestamp': None,
        })
        return redirect(url_for('database', hostname=form.hostname.data, dbname=form.dbname.data))

    return render_template(
        'simpleform.html',
        form=form,
    )

@app.route('/')
def index():
    databases = db.databases.find().sort([('hostname', ASCENDING), ('dbname', ASCENDING)])
    return render_template('index.html', databases=databases)

@app.route('/db/<hostname>')
def host(hostname):
    databases = db.databases.find({'hostname': hostname}).sort([('hostname', ASCENDING), ('dbname', ASCENDING)])
    return render_template('index.html', databases=databases, hostname=hostname)

def connect_status(database):
    try:
        conndb = connect_to(database)
    except Exception, e:
        return None, False, str(e)

    connected = True
    profiling = conndb.command('profile', -1)
    level = profiling['was']
    if level == 0:
        status = 'connected, not profiling'
    elif level == 1:
        ms = profiling['slowms']
        status = 'connected, slowms: %d' % ms
    elif level == 2:
        status = 'connected, profiling, all ops'

    return conndb, connected, status

@app.route('/db/<hostname>/<dbname>/profile')
def profile(hostname, dbname):
    database = get_or_404(db.databases, hostname=hostname, dbname=dbname)
    update(database)

    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for('database', hostname=database['hostname'], dbname=database['dbname']))

@app.route('/db/<hostname>/<dbname>')
def database(hostname, dbname):
    database = get_or_404(db.databases, hostname=hostname, dbname=dbname)

    count = db.profiles.find({'database': database['_id']}).count()

    queries = list(aggregate(database, 'query'))
    queries.sort(key=lambda x: x['times']['avg'], reverse=True)

    conndb, connected, status = connect_status(database)

    return render_template(
        'database.html',
        database=database,
        connected=connected,
        status=status,
        count=count,
        queries=queries,
    )

@app.route('/db/<hostname>/<dbname>/<collection>')
def collection(hostname, dbname, collection):
    database = get_or_404(db.databases, hostname=hostname, dbname=dbname)

    count = db.profiles.find({'database': database['_id']}).count()

    queries = list(aggregate(database, 'query', collection))
    queries.sort(key=lambda x: x['times']['avg'], reverse=True)

    conndb, connected, status = connect_status(database)

    collstats = conndb.command("collstats", collection)
    indexes = []
    for name, info in  conndb[collection].index_information().iteritems():
        info['name'] = name
        indexes.append(info)
    indexes.sort(key=lambda x: x['name'])

    return render_template(
        'database.html',
        database=database,
        collection=collection,
        collstats=collstats,
        indexes=indexes,
        connected=connected,
        status=status,
        count=count,
        queries=queries,
    )

@app.route('/db/<hostname>/<dbname>/<collection>/<skel>')
def query(hostname, dbname, collection, skel):
    database = get_or_404(db.databases, hostname=hostname, dbname=dbname)

    count = db.profiles.find({'database': database['_id']}).count()

    queries = db.profiles.find({'database': database['_id'], 'collection': collection, 'skel': skel, 'op': 'query'})
    queries.sort([
        ('ts', DESCENDING),
    ])

    conndb, connected, status = connect_status(database)

    collstats = conndb.command("collstats", collection)
    indexes = []
    for name, info in  conndb[collection].index_information().iteritems():
        info['name'] = name
        indexes.append(info)
    indexes.sort(key=lambda x: x['name'])

    return render_template(
        'queries.html',
        skel=skel,
        count=count,
        database=database,
        collection=collection,
        queries=queries,
        connected=connected,
        status=status,
        collstats=collstats,
        indexes=indexes,
    )

class Preferences(object):
    def __getattr__(self, name):
        if name == 'referrer':
            return request.referrer
        elif name in request.cookies:
            return request.cookies[name]
        else:
            raise AttributeError(name)

@app.route('/preferences', methods=['GET'])
def preferences():
    form = PreferencesForm(obj=Preferences())
    return render_template('preferences.html', form=form)

@app.route('/preferences', methods=['POST'])
def setpreferences():
    form = PreferencesForm(request.form, obj=Preferences())
    if form.validate():
        lifetime = timedelta(days=365 * 20)
        if form.referrer.data:
            response = redirect(urllib.unquote(form.referrer.data))
        else:
            response = redirect(url_for('index'))
        for field in form:
            if field.name == 'referrer':
                continue
            response.set_cookie(
                field.name,
                field.data,
                max_age=lifetime.seconds + lifetime.days * 24 * 3600,
                expires=datetime.utcnow() + lifetime,
            )
        return response
    return render_template('preferences.html', form=form)

@app.errorhandler(404)
@app.errorhandler(500)
def not_found(error):
    return render_template(str(error.code) + '.html')


########NEW FILE########
__FILENAME__ = server
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# this file may be used as a WSGI script
from professor import app as application

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='Port number to run development server [8080]', default=8080, type=int)
    parser.add_argument('-b', '--bind-ip', help='IP address run development server [0.0.0.0]', default='0.0.0.0')
    parser.add_argument('-d', '--debug', help='Run development server in debug mode [false]', default=False, action='store_true')

    options = parser.parse_args()
    application.run(host=options.bind_ip, port=options.port, debug=options.debug)


########NEW FILE########
__FILENAME__ = test_skeleton
# Copyright (c) 2011-2012, Daniel Crosta
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from bson.binary import Binary
from bson.code import Code
from bson.dbref import DBRef
from bson.errors import InvalidDocument
from bson.objectid import ObjectId
from bson.son import SON
from datetime import datetime
import re
import unittest

from professor import skeleton as s

class SkeletonTest(unittest.TestCase):

    def test_skeleton_simple(self):
        self.assertEqual(s.skeleton({'hello': 'world'}), '{hello}')
        self.assertEqual(s.skeleton({'hello': 'world', 'foo': 'bar'}), '{foo,hello}')
        self.assertEqual(s.skeleton({}), '{}')

    def test_skeleton_list(self):
        self.assertEqual(s.skeleton({'a': []}), '{a:[]}')
        self.assertEqual(s.skeleton({'a': [1,2,3]}), '{a:[]}')
        self.assertEqual(s.skeleton({'a': [{'b': 1}, {'b': 2}]}), '{a:[{b},{b}]}')
        self.assertEqual(s.skeleton({'a': [{'b': 1}, {'c': 2}]}), '{a:[{b},{c}]}')

        # TODO: this is weird, what should this do?
        self.assertEqual(s.skeleton({'a': [{'b': 1}, 2]}), '{a:[{b}]}')

    def test_skeleton_embedded_objects(self):
        self.assertEqual(s.skeleton({'a': {'b': 1}}), '{a:{b}}')
        self.assertEqual(s.skeleton({'a': {'b': 1}, 'c': 1}), '{a:{b},c}')
        self.assertEqual(s.skeleton({'a': {'b': 1, 'd': 2}, 'c': 1}), '{a:{b,d},c}')

        # make sure top-level SON objects work
        self.assertEqual(s.skeleton(SON([('a', 1)])), '{a}')

        # and embedded SON objects
        self.assertEqual(s.skeleton({'a': SON([('b', 1)])}), '{a:{b}}')
        self.assertEqual(s.skeleton({'a': SON([('b', 1)]), 'c': 1}), '{a:{b},c}')
        self.assertEqual(s.skeleton({'a': SON([('b', 1), ('d', 2)]), 'c': 1}), '{a:{b,d},c}')

    def test_skeleton_types(self):
        # ensure that all valid BSON types can be
        # skeleton'd; lists and subobjects are
        # tested in other functions and omitted here
        self.assertEqual(s.skeleton({'a': 1}), '{a}')
        self.assertEqual(s.skeleton({'a': 1L}), '{a}')
        self.assertEqual(s.skeleton({'a': 1.0}), '{a}')
        self.assertEqual(s.skeleton({'a': '1'}), '{a}')
        self.assertEqual(s.skeleton({'a': u'1'}), '{a}')
        self.assertEqual(s.skeleton({'a': True}), '{a}')
        self.assertEqual(s.skeleton({'a': datetime.now()}), '{a}')
        self.assertEqual(s.skeleton({'a': ObjectId('000000000000000000000000')}), '{a}')
        self.assertEqual(s.skeleton({'a': re.compile(r'^$')}), '{a}')
        self.assertEqual(s.skeleton({'a': Code('function(){}')}), '{a}')
        self.assertEqual(s.skeleton({'a': None}), '{a}')
        self.assertEqual(s.skeleton({'a': Binary('123456')}), '{a}')
        self.assertEqual(s.skeleton({'a': DBRef('coll', 123)}), '{a}')

    def test_error_message(self):
        class NonBsonType(object):
            def __init__(self, value):
                self.value = value
            def __repr__(self):
                return 'NonBsonType(%r)' % self.value

        self.assertRaises(InvalidDocument, s.skeleton, ({'a': NonBsonType(1)}, ))
        try:
            s.skeleton({'a': NonBsonType(1)})
        except InvalidDocument as e:
            msg = e.args[0]
            self.assertTrue(re.match(r'unknown BSON type <.*NonBsonType.*>', msg))

class SanitizerTest(unittest.TestCase):

    def test_sanitize(self):
        self.assertEqual(s.sanitize({'a': 'b'}), {'a': 'b'})
        self.assertEqual(s.sanitize({'a': [1, 2]}), {'a': [1, 2]})
        self.assertEqual(s.sanitize({'a.b': 'c'}), {'a_,_b': 'c'})
        self.assertEqual(s.sanitize({'a': {'b': 'c'}}), {'a': {'b': 'c'}})
        self.assertEqual(s.sanitize({'a': {'b.c': 'd'}}), {'a': {'b_,_c': 'd'}})

        self.assertEqual(s.sanitize({'a.$.b': 'c'}), {'a_,__$__,_b': 'c'})

    def test_desanitize(self):
        self.assertEqual(s.desanitize({'a': 'b'}), {'a': 'b'})
        self.assertEqual(s.desanitize({'a': [1, 2]}), {'a': [1, 2]})
        self.assertEqual(s.desanitize({'a_,_b': 'c'}), {'a.b': 'c'})
        self.assertEqual(s.desanitize({'a': {'b': 'c'}}), {'a': {'b': 'c'}})
        self.assertEqual(s.desanitize({'a': {'b_,_c': 'd'}}), {'a': {'b.c': 'd'}})

        self.assertEqual(s.desanitize({'a_,__$__,_b': 'c'}), {'a.$.b': 'c'})

    def test_error_message(self):
        class NonBsonType(object):
            def __init__(self, value):
                self.value = value
            def __repr__(self):
                return 'NonBsonType(%r)' % self.value

        self.assertRaises(InvalidDocument, s.sanitize, ({'a': NonBsonType(1)}, ))
        try:
            s.skeleton({'a': NonBsonType(1)})
        except InvalidDocument as e:
            msg = e.args[0]
            self.assertTrue(re.match(r'unknown BSON type <.*NonBsonType.*>', msg))

        self.assertRaises(InvalidDocument, s.desanitize, ({'a': NonBsonType(1)}, ))
        try:
            s.skeleton({'a': NonBsonType(1)})
        except InvalidDocument as e:
            msg = e.args[0]
            self.assertTrue(re.match(r'unknown BSON type <.*NonBsonType.*>', msg))


########NEW FILE########
