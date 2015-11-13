__FILENAME__ = auth
from functools import wraps
import authdigest
import flask


class FlaskRealmDigestDB(authdigest.RealmDigestDB):
    def requires_auth(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            request = flask.request
            if not self.isAuthenticated(request):
                return self.challenge()

            return f(*args, **kwargs)

        return decorated


class AuthMiddleware(object):

    def __init__(self, app, authDB):
        self.app = app
        self.authDB = authDB

    def __call__(self, environ, start_response):
        req = flask.Request(environ)
        if not self.authDB.isAuthenticated(req):
            response = self.authDB.challenge()
            return response(environ, start_response)
        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = authdigest
# -*- coding: utf-8 -*-
"""
    werkzeug.contrib.authdigest
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The authdigest module contains classes to support
    digest authentication compliant with RFC 2617.


    Usage
    =====

    ::

        from werkzeug.contrib.authdigest import RealmDigestDB

        authDB = RealmDigestDB('test-realm')
        authDB.add_user('admin', 'test')

        def protectedResource(environ, start_reponse):
            request = Request(environ)
            if not authDB.isAuthenticated(request):
                return authDB.challenge()

            return get_protected_response(request)

    :copyright: (c) 2010 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os
import weakref
import hashlib
import werkzeug

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Realm Digest Credentials Database
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class RealmDigestDB(object):
    """Database mapping user to hashed password.

    Passwords are hashed using realm key, and specified
    digest algorithm.

    :param realm: string identifing the hashing realm
    :param algorthm: string identifying hash algorithm to use,
                     default is 'md5'
    """

    def __init__(self, realm, algorithm='md5'):
        self.realm = realm
        self.alg = self.newAlgorithm(algorithm)
        self.db = self.newDB()

    @property
    def algorithm(self):
        return self.alg.algorithm

    def toDict(self):
        r = {'cfg':{ 'algorithm': self.alg.algorithm,
                'realm': self.realm},
            'db': self.db, }
        return r
    def toJson(self, **kw):
        import json
        kw.setdefault('sort_keys', True)
        kw.setdefault('indent', 2)
        return json.dumps(self.toDict(), **kw)

    def add_user(self, user, password):
        r = self.alg.hashPassword(user, self.realm, password)
        self.db[user] = r
        return r

    def __contains__(self, user):
        return user in self.db
    def get(self, user, default=None):
        return self.db.get(user, default)
    def __getitem__(self, user):
        return self.db.get(user)
    def __setitem__(self, user, password):
        return self.add_user(user, password)
    def __delitem__(self, user):
        return self.db.pop(user, None)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def newDB(self):
        return dict()
    def newAlgorithm(self, algorithm):
        return DigestAuthentication(algorithm)

    def isAuthenticated(self, request, **kw):
        authResult = AuthenticationResult(self)
        request.authentication = authResult

        authorization = request.authorization
        if authorization is None:
            return authResult.deny('initial', None)
        authorization.result = authResult

        hashPass = self[authorization.username]
        if hashPass is None:
            return authResult.deny('unknown_user')
        elif not self.alg.verify(authorization, hashPass, method=request.method, **kw):
            return authResult.deny('invalid_password')
        else:
            return authResult.approve('success')

    challenge_class = werkzeug.Response
    def challenge(self, response=None, status=401):
        try:
            authReq = response.www_authenticate
        except AttributeError:
            response = self.challenge_class(response, status)
            authReq = response.www_authenticate
        else:
            if isinstance(status, (int, long)):
                response.status_code = status
            else: response.status = status

        authReq.set_digest(self.realm, os.urandom(8).encode('hex'))
        return response


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Authentication Result
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AuthenticationResult(object):
    """Authentication Result object

    Created by RealmDigestDB.isAuthenticated to operate as a boolean result,
    and storage of authentication information."""

    authenticated = None
    reason = None
    status = 500

    def __init__(self, authDB):
        self.authDB = weakref.ref(authDB)

    def __repr__(self):
        return '<authenticated: %r reason: %r>' % (
            self.authenticated, self.reason)
    def __nonzero__(self):
        return bool(self.authenticated)

    def deny(self, reason, authenticated=False):
        if bool(authenticated):
            raise ValueError("Denied authenticated parameter must evaluate as False")
        self.authenticated = authenticated
        self.reason = reason
        self.status = 401
        return self

    def approve(self, reason, authenticated=True):
        if not bool(authenticated):
            raise ValueError("Approved authenticated parameter must evaluate as True")
        self.authenticated = authenticated
        self.reason = reason
        self.status = 200
        return self

    def challenge(self, response=None, force=False):
        if force or not self:
            return self.authDB().challenge(response, self.status)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Digest Authentication Algorithm
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class DigestAuthentication(object):
    """Digest Authentication implementation.

    references:
        "HTTP Authentication: Basic and Digest Access Authentication". RFC 2617.
            http://tools.ietf.org/html/rfc2617

        "Digest access authentication"
            http://en.wikipedia.org/wiki/Digest_access_authentication
    """

    def __init__(self, algorithm='md5'):
        self.algorithm = algorithm.lower()
        self.H = self.hashAlgorithms[self.algorithm]

    def verify(self, authorization, hashPass=None, **kw):
        reqResponse = self.digest(authorization, hashPass, **kw)
        if reqResponse:
            return (authorization.response.lower() == reqResponse.lower())

    def digest(self, authorization, hashPass=None, **kw):
        if authorization is None:
            return None

        if hashPass is None:
            hA1 = self._compute_hA1(authorization, kw['password'])
        else: hA1 = hashPass

        hA2 = self._compute_hA2(authorization, kw.pop('method', 'GET'))

        if 'auth' in authorization.qop:
            res = self._compute_qop_auth(authorization, hA1, hA2)
        elif not authorization.qop:
            res = self._compute_qop_empty(authorization, hA1, hA2)
        else:
            raise ValueError("Unsupported qop: %r" % (authorization.qop,))
        return res

    def hashPassword(self, username, realm, password):
        return self.H(username, realm, password)

    def _compute_hA1(self, auth, password=None):
        return self.hashPassword(auth.username, auth.realm, password or auth.password)
    def _compute_hA2(self, auth, method):
        return self.H(method, auth.uri)
    def _compute_qop_auth(self, auth, hA1, hA2):
        return self.H(hA1, auth.nonce, auth.nc, auth.cnonce, auth.qop, hA2)
    def _compute_qop_empty(self, auth, hA1, hA2):
        return self.H(hA1, auth.nonce, hA2)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    hashAlgorithms = {}

    @classmethod
    def addDigestHashAlg(klass, key, hashObj):
        key = key.lower()
        def H(*args):
            x = ':'.join(map(str, args))
            return hashObj(x).hexdigest()

        H.__name__ = "H_"+key
        klass.hashAlgorithms[key] = H
        return H

DigestAuthentication.addDigestHashAlg('md5', hashlib.md5)
DigestAuthentication.addDigestHashAlg('sha', hashlib.sha1)

########NEW FILE########
__FILENAME__ = create_db
#!/usr/bin/env python
from route53.models import db
db.drop_all()
db.create_all()

########NEW FILE########
__FILENAME__ = connection
from boto.route53 import Route53Connection


def get_connection():
    from route53 import app
    return Route53Connection(aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
             aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'])

########NEW FILE########
__FILENAME__ = forms
from flaskext import wtf
from flaskext.wtf import validators


RECORD_CHOICES = [
    ('A', 'A'),
    ('AAAA', 'AAAA'),
    ('CNAME', 'CNAME'),
    ('MX', 'MX'),
    ('NS', 'NS'),
    ('PTR', 'PTR'),
    ('SOA', 'SOA'),
    ('SPF', 'SPF'),
    ('SRV', 'SRV'),
    ('TXT', 'TXT'),
]


class ZoneForm(wtf.Form):
    name = wtf.TextField('Domain Name', validators=[validators.Required()])
    comment = wtf.TextAreaField('Comment')


class RecordForm(wtf.Form):
    type = wtf.SelectField("Type", choices=RECORD_CHOICES)
    name = wtf.TextField("Name", validators=[validators.Required()])
    value = wtf.TextField("Value", validators=[validators.Required()])
    ttl = wtf.IntegerField("TTL", default="86400",
            validators=[validators.Required()])
    comment = wtf.TextAreaField("Comment")

    @property
    def values(self):
        if self.type.data != 'TXT':
            return filter(lambda x: x,
                      map(lambda x: x.strip(),
                          self.value.data.strip().split(';')))
        else:
            return [self.value.data.strip()]

class RecordAliasForm(wtf.Form):
    type = wtf.SelectField("Type", choices=RECORD_CHOICES)
    name = wtf.TextField("Name", validators=[validators.Required()])
    alias_hosted_zone_id = wtf.TextField("Alias hosted zone ID", validators=[validators.Required()])
    alias_dns_name = wtf.TextField("Alias DNS name", validators=[validators.Required()])
    ttl = wtf.IntegerField("TTL", default="86400",
            validators=[validators.Required()])
    comment = wtf.TextAreaField("Comment")

class APIKeyForm(wtf.Form):
    key = wtf.TextField('API Key', validators=[validators.Required()])

########NEW FILE########
__FILENAME__ = models
import simplejson

from route53 import app

from flaskext.sqlalchemy import SQLAlchemy

# initialize db
db = SQLAlchemy(app)

# Models


class ChangeBatch(db.Model):
    __tablename__ = "change_batches"

    id = db.Column(db.Integer, primary_key=True)
    change_id = db.Column(db.String(255))
    status = db.Column(db.String(255))
    comment = db.Column(db.String(255))

    changes = db.relation("Change", backref="change_batch")

    def process_response(self, resp):
        change_info = resp['ChangeResourceRecordSetsResponse']['ChangeInfo']
        self.change_id = change_info['Id'][8:]
        self.status = change_info['Status']


class Change(db.Model):
    __tablename__ = "changes"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255))
    name = db.Column(db.String(255))
    type = db.Column(db.String(255))
    ttl = db.Column(db.String(255))
    value = db.Column(db.String(255))

    change_batch_id = db.Column(db.Integer, db.ForeignKey("change_batches.id"))

    @property
    def values(self):
        return simplejson.loads(self.value)

    @values.setter
    def values(self, values):
        self.value = simplejson.dumps(values)

########NEW FILE########
__FILENAME__ = main
from flask import redirect, Module, url_for, request

main = Module(__name__)


@main.route('/')
def index():
    return redirect(url_for('zones.zones_list'))

########NEW FILE########
__FILENAME__ = records
from boto.route53.exception import DNSServerError
from flask import Module, redirect, url_for, render_template, request, abort

from route53.forms import RecordForm
from route53.connection import get_connection
from route53.xmltools import render_change_batch


records = Module(__name__)


@records.route('/<zone_id>/new', methods=['GET', 'POST'])
def records_new(zone_id):
    from route53.models import ChangeBatch, Change, db
    conn = get_connection()
    zone = conn.get_hosted_zone(zone_id)['GetHostedZoneResponse']['HostedZone']
    form = RecordForm()
    error = None
    if form.validate_on_submit():
        change_batch = ChangeBatch(change_id='',
                                   status='created',
                                   comment=form.comment.data)
        db.session.add(change_batch)
        change = Change(action="CREATE",
                        name=form.name.data,
                        type=form.type.data,
                        ttl=form.ttl.data,
                        values={'values': form.values},
                        change_batch_id=change_batch.id)
        db.session.add(change)
        rendered_xml = render_change_batch({'changes': [change],
                                            'comment': change_batch.comment})
        try:
            resp = conn.change_rrsets(zone_id, rendered_xml)
            change_batch.process_response(resp)
            db.session.commit()
            return redirect(url_for('zones.zones_records', zone_id=zone_id))
        except DNSServerError as error:
            error = error
            db.session.rollback()
    return render_template('records/new.html',
                           form=form,
                           zone=zone,
                           zone_id=zone_id,
                           error=error)


def get_record_fields():
    fields = [
        'name',
        'type',
        'ttl',
    ]
    val_dict = {}
    for field in fields:
        if request.method == "GET":
            result = request.args.get(field, None)
        elif request.method == "POST":
            result = request.form.get("data_"+field, None)
        if result is None:
            abort(404)
        val_dict[field] = result
    return val_dict


@records.route('/<zone_id>/delete', methods=['GET', 'POST'])
def records_delete(zone_id):
    from route53.models import ChangeBatch, Change, db
    conn = get_connection()
    zone = conn.get_hosted_zone(zone_id)['GetHostedZoneResponse']['HostedZone']
    val_dict = get_record_fields()

    if request.method == "GET":
        values = request.args.getlist('value')
        alias_hosted_zone_id = request.args.get('alias_hosted_zone_id', None)
        alias_dns_name = request.args.get('alias_dns_name', None)
        if not values and not alias_hosted_zone_id and not alias_dns_name:
            abort(404)

    error = None
    if request.method == "POST":
        change_batch = ChangeBatch(change_id='', status='created', comment='')
        db.session.add(change_batch)
        values = request.form.getlist('data_value')
        alias_hosted_zone_id = request.form.get('data_alias_hosted_zone_id', None)
        alias_dns_name = request.form.get('data_alias_dns_name', None)
        change = Change(action="DELETE",
                        change_batch_id=change_batch.id,
                        values={
                            'values': values,
                            'alias_hosted_zone_id': alias_hosted_zone_id,
                            'alias_dns_name': alias_dns_name,
                        },
                        **val_dict)
        db.session.add(change)
        rendered_xml = render_change_batch({'changes': [change],
                                            'comment': change_batch.comment})
        try:
            resp = conn.change_rrsets(zone_id, rendered_xml)
            change_batch.process_response(resp)
            db.session.commit()
            return redirect(url_for('zones.zones_records', zone_id=zone_id))
        except DNSServerError as error:
            error = error
    return render_template('records/delete.html',
                           val_dict=val_dict,
                           values=values,
                           alias_hosted_zone_id=alias_hosted_zone_id,
                           alias_dns_name=alias_dns_name,
                           zone=zone,
                           zone_id=zone_id,
                           error=error)


@records.route('/<zone_id>/update', methods=['GET', 'POST'])
def records_update(zone_id):
    from route53.models import ChangeBatch, Change, db
    conn = get_connection()
    zone = conn.get_hosted_zone(zone_id)['GetHostedZoneResponse']['HostedZone']
    val_dict = get_record_fields()

    if request.method == "GET":
        values = request.args.getlist('value')
        if not values:
            abort(404)
        initial_data = dict(val_dict)
        initial_data['value'] = ';'.join(values)
        form = RecordForm(**initial_data)

    error = None
    if request.method == "POST":
        form = RecordForm()
        change_batch = ChangeBatch(change_id='', status='created', comment=form.comment.data)
        db.session.add(change_batch)
        values = request.form.getlist('data_value')
        delete_change = Change(action="DELETE",
                               change_batch_id=change_batch.id,
                               values={'values': values},
                               **val_dict)
        create_change = Change(action="CREATE",
                               change_batch_id=change_batch.id,
                               values={'values': form.values},
                               type=form.type.data,
                               ttl=form.ttl.data,
                               name=form.name.data)
        db.session.add(delete_change)
        db.session.add(create_change)
        rendered_xml = render_change_batch({'changes': [delete_change, create_change],
                                            'comment': change_batch.comment})
        try:
            resp = conn.change_rrsets(zone_id, rendered_xml)
            change_batch.process_response(resp)
            db.session.commit()
            return redirect(url_for('zones.zones_records', zone_id=zone_id))
        except DNSServerError as error:
            error = error
    return render_template('records/update.html',
                           val_dict=val_dict,
                           values=values,
                           form=form,
                           zone=zone,
                           zone_id=zone_id,
                           error=error)

########NEW FILE########
__FILENAME__ = slicehost
from boto.route53.exception import DNSServerError
from functools import wraps
from itertools import groupby

from flask import Module, session, redirect, url_for, render_template, request

from pyactiveresource.activeresource import ActiveResource

from route53.connection import get_connection
from route53.forms import APIKeyForm
from route53.xmltools import render_change_batch

slicehost = Module(__name__)

API_KEY = 'slicehost_api_key'
API_URL = 'https://%s@api.slicehost.com/'


def get_zone_class():
    class Zone(ActiveResource):
        _site = API_URL % session[API_KEY]
    return Zone


def get_record_class():
    class Record(ActiveResource):
        _site = API_URL % session[API_KEY]
    return Record


def requires_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY in session:
            return redirect(url_for('slicehost.index'))
        return f(*args, **kwargs)
    return decorated


@slicehost.route('/', methods=['GET', 'POST'])
def index():
    if 'clean' in request.args:
        del session[API_KEY]
    if API_KEY in session:
        return redirect(url_for('slicehost.zones'))
    form = APIKeyForm()
    if form.validate_on_submit():
        session[API_KEY] = form.key.data
        return redirect(url_for('slicehost.zones'))
    return render_template('slicehost/index.html', form=form)


@slicehost.route('/zones')
@requires_key
def zones():
    Zone = get_zone_class()
    zones = Zone.find()
    return render_template('slicehost/zones.html', zones=zones)


@slicehost.route('/zones/<zone_id>')
@requires_key
def records(zone_id):
    Zone = get_zone_class()
    zone = Zone.find(zone_id)
    Record = get_record_class()
    records = Record.find(zone_id=zone_id)
    records = sorted(records, key=lambda x: x.record_type)
    results = []
    for k, g in groupby(records, key=lambda x: (x.record_type, x.name)):
        record_type, name = k
        results.append((record_type, name, list(g)))
    return render_template('slicehost/records.html', zone=zone, records=results)


@slicehost.route('/zones/<zone_id>/import', methods=['GET', 'POST'])
@requires_key
def import_zone(zone_id):
    from route53.models import ChangeBatch, Change, db

    Zone = get_zone_class()
    zone = Zone.find(zone_id)
    Record = get_record_class()

    # filter out NS records
    records = filter(lambda x: x.record_type != 'NS', Record.find(zone_id=zone_id))

    records = sorted(records, key=lambda x: x.record_type)

    # order records by record_type and name into recordsets

    conn = get_connection()
    response = conn.create_hosted_zone(zone.origin)
    info = response['CreateHostedZoneResponse']
    new_zone_id = info['HostedZone']['Id']

    errors = []

    for k, g in groupby(records, key=lambda x: (x.record_type, x.name)):
        change_batch = ChangeBatch(change_id='',
                                   status='created',
                                   comment='')

        db.session.add(change_batch)
        record_type, name = k
        rcds = list(g)
        record_name = zone.origin in name and name or name + "." + zone.origin

        if record_type not in ('MX', 'SRV'):
            values = map(lambda x: x.data, rcds)
        else:
            values = map(lambda x: "%s %s" % (x.aux, x.data), rcds)
        change = Change(action="CREATE",
                        name=record_name,
                        type=record_type,
                        ttl=rcds[0].ttl,
                        values={'values':values},
                        change_batch_id=change_batch.id)
        db.session.add(change)
        changes = [change]

        rendered_xml = render_change_batch({'changes': changes, 'comment': ''})

        try:
            from route53 import shortid
            resp = conn.change_rrsets(shortid(new_zone_id), rendered_xml)
            change_batch.process_response(resp)
            db.session.commit()
        except DNSServerError as error:
            errors.append((record_type, name, error))
            db.session.rollback()

    if errors:
        return render_template('slicehost/import_zone.html',
                errors=errors,
                zone=zone)

    return redirect(url_for('main.index'))

########NEW FILE########
__FILENAME__ = zones
from boto.route53.exception import DNSServerError
from itertools import groupby
from flask import Module

from flask import url_for, render_template, \
        redirect, flash, request

from route53.forms import ZoneForm
from route53.connection import get_connection

from route53.xmltools import render_change_batch

zones = Module(__name__)


@zones.route('/')
def zones_list():
    conn = get_connection()
    response = conn.get_all_hosted_zones()
    zones = response['ListHostedZonesResponse']['HostedZones']
    return render_template('zones/list.html', zones=zones)


@zones.route('/new', methods=['GET', 'POST'])
def zones_new():
    conn = get_connection()

    form = ZoneForm()
    if form.validate_on_submit():
        response = conn.create_hosted_zone(
                form.name.data,
                comment=form.comment.data)

        info = response['CreateHostedZoneResponse']

        nameservers = ', '.join(info['DelegationSet']['NameServers'])
        zone_id = info['HostedZone']['Id']

        flash(u"A zone with id %s has been created. "
              u"Use following nameservers %s"
               % (zone_id, nameservers))

        return redirect(url_for('zones_list'))
    return render_template('zones/new.html', form=form)


@zones.route('/<zone_id>/delete', methods=['GET', 'POST'])
def zones_delete(zone_id):
    conn = get_connection()
    zone = conn.get_hosted_zone(zone_id)['GetHostedZoneResponse']['HostedZone']

    error = None

    if request.method == 'POST' and 'delete' in request.form:
        try:
            conn.delete_hosted_zone(zone_id)

            flash(u"A zone with id %s has been deleted" % zone_id)

            return redirect(url_for('zones_list'))
        except DNSServerError as error:
            error = error
    return render_template('zones/delete.html',
                           zone_id=zone_id,
                           zone=zone,
                           error=error)


@zones.route('/<zone_id>')
def zones_detail(zone_id):
    conn = get_connection()
    resp = conn.get_hosted_zone(zone_id)
    zone = resp['GetHostedZoneResponse']['HostedZone']
    nameservers = resp['GetHostedZoneResponse']['DelegationSet']['NameServers']

    return render_template('zones/detail.html',
            zone_id=zone_id,
            zone=zone,
            nameservers=nameservers)


@zones.route('/<zone_id>/records')
def zones_records(zone_id):
    conn = get_connection()
    resp = conn.get_hosted_zone(zone_id)
    zone = resp['GetHostedZoneResponse']['HostedZone']

    record_resp = sorted(conn.get_all_rrsets(zone_id), key=lambda x: x.type)

    groups = groupby(record_resp, key=lambda x: x.type)

    groups = [(k, list(v)) for k, v in groups]

    return render_template('zones/records.html',
            zone_id=zone_id,
            zone=zone,
            groups=groups)


@zones.route('/clone/<zone_id>', methods=['GET', 'POST'])
def zones_clone(zone_id):
    conn = get_connection()

    zone_response = conn.get_hosted_zone(zone_id)
    original_zone = zone_response['GetHostedZoneResponse']['HostedZone']

    form = ZoneForm()
    errors = []

    if form.validate_on_submit():
        response = conn.create_hosted_zone(
                form.name.data,
                comment=form.comment.data)

        info = response['CreateHostedZoneResponse']

        nameservers = ', '.join(info['DelegationSet']['NameServers'])

        new_zone_id = info['HostedZone']['Id']

        original_records = conn.get_all_rrsets(zone_id)

        from route53.models import ChangeBatch, Change, db

        for recordset in original_records:
            if not recordset.type in ["SOA", "NS"]:

                change_batch = ChangeBatch(change_id='',
                                           status='created',
                                           comment='')
                db.session.add(change_batch)
                change = Change(action="CREATE",
                                name=recordset.name.replace(original_zone['Name'],
                                                            form.name.data),
                                type=recordset.type,
                                ttl=recordset.ttl,
                                values = recordset.resource_records,
                                change_batch_id=change_batch.id)

                db.session.add(change)
                changes = [change]

                rendered_xml = render_change_batch({'changes': changes, 'comment': ''})

                try:
                    from route53 import shortid
                    resp = conn.change_rrsets(shortid(new_zone_id), rendered_xml)
                    change_batch.process_response(resp)
                    db.session.commit()
                except DNSServerError as error:
                    errors.append((recordset.type, recordset.name, error))
                    db.session.rollback()

        if not errors:
            flash(u"A zone with id %s has been created. "
                  u"Use following nameservers %s"
                   % (new_zone_id, nameservers))
            return redirect(url_for('zones_list'))

    return render_template('zones/clone.html',
        form=form, errors=errors, original_zone=original_zone)

########NEW FILE########
__FILENAME__ = xmltools
try:
    import lxml.etree as etree
except ImportError:
    try:
        import cElementTree as etree
        print "Using cElementTree"
    except ImportError:
        try:
            import elementtree.ElementTree as etree
        except ImportError:
            from xml.etree import ElementTree as etree


NAMESPACE = "{https://route53.amazonaws.com/doc/2010-10-01/}"
RECORDSET_TAG = NAMESPACE + 'ResourceRecordSet'
NAME_TAG = NAMESPACE + 'Name'
TYPE_TAG = NAMESPACE + 'Type'
TTL_TAG = NAMESPACE + 'TTL'
RECORD_TAG = NAMESPACE + 'ResourceRecord'
VALUE_TAG = NAMESPACE + 'Value'
RECORDS_TAG = NAMESPACE + 'ResourceRecords'


def render_change_batch(context):
    from route53 import app
    template = app.jinja_env.get_template('xml/change_batch.xml')
    rendered_xml = template.render(context)
    return rendered_xml

########NEW FILE########
__FILENAME__ = runserver
#!/usr/bin/env python
from route53 import app
app.run()

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env ipython
from route53 import app

ctx = app.test_request_context()
ctx.push()

########NEW FILE########
