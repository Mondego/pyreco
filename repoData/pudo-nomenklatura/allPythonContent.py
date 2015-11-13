__FILENAME__ = heroku_settings
import os

#DEBUG = True
SECRET_KEY = os.environ.get('SECRET_KEY')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
                            os.environ.get('SHARED_DATABASE_URL'))

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

MEMCACHE_HOST = os.environ.get('MEMCACHIER_SERVERS')

S3_BUCKET = os.environ.get('S3_BUCKET', 'nomenklatura')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')

CELERY_BROKER = os.environ.get('CLOUDAMQP_URL')

########NEW FILE########
__FILENAME__ = authz
from flask import request

from nomenklatura.exc import Forbidden

def logged_in():
    return request.account is not None

def dataset_create():
    return logged_in()

def dataset_edit(dataset):
    if not logged_in():
        return False
    if dataset.public_edit:
        return True
    if dataset.owner_id == request.account.id:
        return True
    return False

def dataset_manage(dataset):
    if not logged_in():
        return False
    if dataset.owner_id == request.account.id:
        return True
    return False

def require(pred):
    if not pred:
        raise Forbidden("Sorry, you're not permitted to do this!")


########NEW FILE########
__FILENAME__ = core
import logging

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.oauth import OAuth
from flask.ext.assets import Environment

import certifi
from celery import Celery

from nomenklatura import default_settings

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.from_object(default_settings)
app.config.from_envvar('NOMENKLATURA_SETTINGS', silent=True)

db = SQLAlchemy(app)
assets = Environment(app)

celery = Celery('nomenklatura', broker=app.config['CELERY_BROKER_URL'])

oauth = OAuth()
github = oauth.remote_app('github',
        base_url='https://github.com/login/oauth/',
        authorize_url='https://github.com/login/oauth/authorize',
        request_token_url=None,
        access_token_url='https://github.com/login/oauth/access_token',
        consumer_key=app.config.get('GITHUB_CLIENT_ID'),
        consumer_secret=app.config.get('GITHUB_CLIENT_SECRET'))

github._client.ca_certs = certifi.where()
########NEW FILE########
__FILENAME__ = default_settings
DEBUG = True
SECRET_KEY = 'no'
SQLALCHEMY_DATABASE_URI = 'sqlite:///master.sqlite3'
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'

GITHUB_CLIENT_ID = 'da79a6b5868e690ab984'
GITHUB_CLIENT_SECRET = '1701d3bd20bbb29012592fd3a9c64b827e0682d6'

ALLOWED_EXTENSIONS = set(['csv', 'tsv', 'ods', 'xls', 'xlsx', 'txt'])


########NEW FILE########
__FILENAME__ = exc
# This file exists because I'm not sure we'll need to subclass them later.
from werkzeug.exceptions import HTTPException, NotFound, Gone
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from werkzeug.exceptions import InternalServerError as InternalError


########NEW FILE########
__FILENAME__ = importer
from formencode import Invalid

from nomenklatura.core import db
from nomenklatura.core import celery as app
from nomenklatura.model import Dataset, Entity, Account, Upload


def apply_mapping(row, mapping):
    out = {'attributes': {}, 'reviewed': mapping['reviewed']}
    for column, prop in mapping['columns'].items():
        value = row.get(column)
        if value is None or not len(value.strip()):
            continue
        if prop.startswith('attributes.'):
            a, prop = prop.split('.', 1)
            out[a][prop] = value
        else:
            out[prop] = value
    return out


@app.task
def import_upload(upload_id, account_id, mapping):
    upload = Upload.all().filter_by(id=upload_id).first()
    account = Account.by_id(account_id)
    mapped = mapping['columns'].values()

    rows = [apply_mapping(r, mapping) for r in upload.tab.dict]
    # put aliases second.
    rows = sorted(rows, key=lambda r: 2 if r.get('canonical') else 1)

    for i, row in enumerate(rows):
        try:
            entity = None
            if row.get('id'):
                entity = Entity.by_id(row.get('id'))
            if entity is None:
                entity = Entity.by_name(upload.dataset, row.get('name'))
            if entity is None:
                entity = Entity.create(upload.dataset, row, account)

            # restore some defaults: 
            if entity.canonical_id and 'canonical' not in mapped:
                row['canonical'] = entity.canonical_id
            if entity.invalid and 'invalid' not in mapped:
                row['invalid'] = entity.invalid 

            if entity.attributes:
                attributes = entity.attributes.copy()
            else:
                attributes = {}
            attributes.update(row['attributes'])
            row['attributes'] = attributes

            entity.update(row, account)
            print entity
            if i % 100 == 0:
                print 'COMMIT'
                db.session.commit()
        except Invalid, inv:
            # TODO: logging. 
            print inv
    db.session.commit()
########NEW FILE########
__FILENAME__ = manage
from flask.ext.script import Manager

from nomenklatura.core import app, db
from nomenklatura.model import *
from nomenklatura import views

manager = Manager(app)


@manager.command
def createdb():
    """ Make the database. """
    db.create_all()


@manager.command
def postproc_20131119():
    from nomenklatura.model.text import normalize_text
    for entity in Entity.query:
        print [entity]
        entity.normalized = normalize_text(entity.name)
        #entity.attributes = entity.data
        db.session.add(entity)
        db.session.commit()


@manager.command
def flush(dataset):
    ds = Dataset.by_name(dataset)
    for alias in Alias.all_unmatched(ds):
        db.session.delete(alias)
    db.session.commit()


if __name__ == '__main__':
    manager.run()


########NEW FILE########
__FILENAME__ = account
from datetime import datetime

from nomenklatura.core import db
from nomenklatura.model.common import make_key


class Account(db.Model):
    __tablename__ = 'account'

    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.Integer)
    login = db.Column(db.Unicode)
    email = db.Column(db.Unicode)
    api_key = db.Column(db.Unicode, default=make_key)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
            onupdate=datetime.utcnow)

    datasets = db.relationship('Dataset', backref='owner',
                               lazy='dynamic')
    uploads = db.relationship('Upload', backref='creator',
                               lazy='dynamic')
    entities_created = db.relationship('Entity', backref='creator',
                               lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'github_id': self.github_id,
            'login': self.login,
            'created_at': self.created_at, 
            'updated_at': self.updated_at,
            }

    @classmethod
    def by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def by_github_id(cls, github_id):
        return cls.query.filter_by(github_id=github_id).first()

    @classmethod
    def create(cls, data):
        account = cls()
        account.github_id = data['id']
        account.login = data['login']
        account.email = data.get('email')
        db.session.add(account)
        db.session.flush()
        return account

    def update(self, data):
        self.login = data['login']
        self.email = data.get('email')
        db.session.add(self)



########NEW FILE########
__FILENAME__ = common
import re
import json
from uuid import uuid4

from formencode import FancyValidator, Invalid
from sqlalchemy.types import TypeDecorator, VARCHAR

VALID_NAME = re.compile(r"^[a-zA-Z0-9_\-]{2,1999}$")


def make_key():
    return unicode(uuid4())


class Name(FancyValidator):
    """ Check if a given name is valid for datasets. """

    def _to_python(self, value, state):
        if VALID_NAME.match(value):
            return value
        raise Invalid('Invalid name.', value, None)

########NEW FILE########
__FILENAME__ = dataset
from datetime import datetime

from formencode import Schema, All, Invalid, validators

from nomenklatura.core import db
from nomenklatura.model.common import Name, FancyValidator
from nomenklatura.exc import NotFound


class AvailableDatasetName(FancyValidator):

    def _to_python(self, value, state):
        if Dataset.by_name(value) is None:
            return value
        raise Invalid('Dataset already exists.', value, None)


class ValidDataset(FancyValidator):

    def _to_python(self, value, state):
        dataset = Dataset.by_name(value)
        if dataset is None:
            raise Invalid('Dataset not found.', value, None)
        return dataset


class DatasetNewSchema(Schema):
    name = All(AvailableDatasetName(), Name(not_empty=True))
    label = validators.String(min=3, max=255)


class FormDatasetSchema(Schema):
    allow_extra_fields = True
    dataset = ValidDataset()


class DatasetEditSchema(Schema):
    allow_extra_fields = True
    label = validators.String(min=3, max=255)
    match_aliases = validators.StringBool(if_missing=False)
    ignore_case = validators.StringBool(if_missing=False)
    public_edit = validators.StringBool(if_missing=False)
    normalize_text = validators.StringBool(if_missing=False)
    enable_invalid = validators.StringBool(if_missing=False)


class Dataset(db.Model):
    __tablename__ = 'dataset'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode)
    label = db.Column(db.Unicode)
    ignore_case = db.Column(db.Boolean, default=False)
    match_aliases = db.Column(db.Boolean, default=False)
    public_edit = db.Column(db.Boolean, default=False)
    normalize_text = db.Column(db.Boolean, default=True)
    enable_invalid = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
            onupdate=datetime.utcnow)

    entities = db.relationship('Entity', backref='dataset',
                             lazy='dynamic')
    uploads = db.relationship('Upload', backref='dataset',
                               lazy='dynamic')

    def to_dict(self):
        from nomenklatura.model.entity import Entity
        num_aliases = Entity.all(self).filter(Entity.canonical_id!=None).count()
        num_review = Entity.all(self).filter_by(reviewed=False).count()
        num_entities = Entity.all(self).count()
        num_invalid = Entity.all(self).filter_by(invalid=True).count()
    
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'owner': self.owner.to_dict(),
            'stats': {
                'num_aliases': num_aliases,
                'num_entities': num_entities,
                'num_review': num_review,
                'num_invalid': num_invalid
            },
            'ignore_case': self.ignore_case,
            'match_aliases': self.match_aliases,
            'public_edit': self.public_edit,
            'normalize_text': self.normalize_text,
            'enable_invalid': self.enable_invalid,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @property
    def last_modified(self):
        dates = [self.updated_at]
        from nomenklatura.model.entity import Entity
        latest_entity = self.entities.order_by(Entity.updated_at.desc()).first()
        if latest_entity is not None:
            dates.append(latest_entity.updated_at)

        from nomenklatura.model.alias import Alias
        latest_alias = self.aliases.order_by(Alias.updated_at.desc()).first()
        if latest_alias is not None:
            dates.append(latest_alias.updated_at)
        return max(dates)

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def find(cls, name):
        dataset = cls.by_name(name)
        if dataset is None:
            raise NotFound("No such dataset: %s" % name)
        return dataset

    @classmethod
    def from_form(cls, form_data):
        data = FormDatasetSchema().to_python(form_data)
        return data.get('dataset')

    @classmethod
    def all(cls):
        return cls.query

    @classmethod
    def create(cls, data, account):
        data = DatasetNewSchema().to_python(data)
        dataset = cls()
        dataset.owner = account
        dataset.name = data['name']
        dataset.label = data['label']
        db.session.add(dataset)
        db.session.flush()
        return dataset

    def update(self, data):
        data = DatasetEditSchema().to_python(data)
        self.label = data['label']
        self.normalize_text = data['normalize_text']
        self.ignore_case = data['ignore_case']
        self.public_edit = data['public_edit']
        self.match_aliases = data['match_aliases']
        self.enable_invalid = data['enable_invalid']
        db.session.add(self)
        db.session.flush()


########NEW FILE########
__FILENAME__ = entity
from datetime import datetime

from formencode import Schema, All, Invalid, validators
from formencode import FancyValidator
from sqlalchemy import func
from sqlalchemy.orm import joinedload_all, backref
from sqlalchemy.dialects.postgresql import HSTORE

from nomenklatura.core import db
from nomenklatura.exc import NotFound
from nomenklatura.model.text import normalize_text


class EntityState():

    def __init__(self, dataset, entity):
        self.dataset = dataset
        self.entity = entity


class AvailableName(FancyValidator):

    def _to_python(self, name, state):
        entity = Entity.by_name(state.dataset, name)
        if entity is None:
            return name
        if state.entity and entity.id == state.entity.id:
            return name
        raise Invalid('Entity already exists.', name, None)


class ValidCanonicalEntity(FancyValidator):

    def _to_python(self, value, state):
        if isinstance(value, dict):
            value = value.get('id')
        entity = Entity.by_id(value)
        if entity is None:
            entity = Entity.by_name(state.dataset, value)
        if entity is None:
            raise Invalid('Entity does not exist: %s' % value, value, None)
        if entity == state.entity:
            return None
        if entity.dataset != state.dataset:
            raise Invalid('Entity belongs to a different dataset.',
                          value, None)
        return entity


class AttributeSchema(Schema):
    allow_extra_fields = True


class EntitySchema(Schema):
    allow_extra_fields = True
    name = All(validators.String(min=0, max=5000), AvailableName())
    attributes = AttributeSchema()
    reviewed = validators.StringBool(if_empty=False, if_missing=False)
    invalid = validators.StringBool(if_empty=False, if_missing=False)
    canonical = ValidCanonicalEntity(if_missing=None, if_empty=None)


class Entity(db.Model):
    __tablename__ = 'entity'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode)
    normalized = db.Column(db.Unicode)
    attributes = db.Column(HSTORE)
    reviewed = db.Column(db.Boolean, default=False)
    invalid = db.Column(db.Boolean, default=False)
    canonical_id = db.Column(db.Integer,
        db.ForeignKey('entity.id'), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
            onupdate=datetime.utcnow)

    canonical = db.relationship('Entity', backref=backref('aliases', lazy='dynamic'),
        remote_side='Entity.id')

    def to_dict(self, shallow=False):
        d = {
            'id': self.id,
            'name': self.name,
            'dataset': self.dataset.name,
            'reviewed': self.reviewed,
            'invalid': self.invalid,
            'canonical': self.canonical,
            #'normalized': self.normalized,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        if not shallow:
            d['creator'] = self.creator.to_dict()
            d['attributes'] = self.attributes
            d['num_aliases'] = self.aliases.count()
        return d

    def to_row(self):
        row = self.attributes or {}
        row = row.copy()
        row.update(self.to_dict(shallow=True))
        if self.canonical is not None:
            row['canonical'] = self.canonical.name
        return row

    @property
    def display_name(self):
        return self.name

    @classmethod
    def by_name(cls, dataset, name):
        q = cls.query.filter_by(dataset=dataset)
        attr = Entity.name
        if dataset.normalize_text:
            attr = Entity.normalized
            name = normalize_text(name)
        if dataset.ignore_case:
            attr = func.lower(attr)
            if isinstance(name, basestring):
                name = name.lower()
        q = q.filter(attr==name)
        return q.first()

    @classmethod
    def by_id(cls, id):
        try:
            return cls.query.filter_by(id=int(id)).first()
        except ValueError:
            return None

    @classmethod
    def id_map(cls, ids):
        entities = {}
        for entity in cls.query.filter(cls.id.in_(ids)):
            entities[entity.id] = entity
        return entities

    @classmethod
    def find(cls, dataset, id):
        entity = cls.by_id(id)
        if entity is None:
            raise NotFound("No such value ID: %s" % id)
        return entity

    @classmethod
    def all(cls, dataset=None, query=None, eager_aliases=False, eager=False):
        q = cls.query
        if dataset is not None:
            q = q.filter_by(dataset=dataset)
        if query is not None and len(query.strip()):
            q = q.filter(cls.name.ilike('%%%s%%' % query.strip()))
        if eager_aliases:
            q = q.options(joinedload_all(cls.aliases_static))
        if eager:
            q = q.options(db.joinedload('dataset'))
            q = q.options(db.joinedload('creator'))
        return q


    @classmethod
    def create(cls, dataset, data, account):
        state = EntityState(dataset, None)
        data = EntitySchema().to_python(data, state)
        entity = cls()
        entity.dataset = dataset
        entity.creator = account
        entity.name = data['name']
        entity.normalized = normalize_text(entity.name)
        entity.attributes = data.get('attributes', {})
        entity.reviewed = data['reviewed']
        entity.invalid = data['invalid']
        entity.canonical = data['canonical']
        db.session.add(entity)
        db.session.flush()
        return entity


    def update(self, data, account):
        state = EntityState(self.dataset, self)
        data = EntitySchema().to_python(data, state)
        self.creator = account
        self.name = data['name']
        self.normalized = normalize_text(self.name)
        self.attributes = data['attributes']
        self.reviewed = data['reviewed']
        self.invalid = data['invalid']
        self.canonical = data['canonical']

        # redirect all aliases of this entity
        if self.canonical:
            if self.canonical.canonical_id:
                if self.canonial.canonical_id == self.id:
                    self.canonical.canonical = None
                else:
                    self.canonical = self.canonical.canonical

            for alias in self.aliases:
                alias.canonical = self.canonical
        
        db.session.add(self)

########NEW FILE########
__FILENAME__ = matching
from sqlalchemy import func, select, and_

from nomenklatura.model.entity import Entity
from nomenklatura.model.text import normalize
from nomenklatura.core import db


class Matches(object):

    def __init__(self, q):
        self.lq = self.q = q

    def limit(self, l):
        self.lq = self.lq.limit(l)
        return self

    def offset(self, o):
        self.lq = self.lq.offset(o)
        return self

    def count(self):
        rp = db.engine.execute(self.q.alias('count').count())
        (count,) = rp.fetchone()
        return count

    def __iter__(self):
        rp = db.engine.execute(self.lq)
        rows = rp.fetchall()
        ids = [r[0] for r in rows]
        entities = Entity.id_map(ids)
        for (id, score) in rows:
            yield {'score': int(score), 'entity': entities.get(id)}


def find_matches(dataset, text, filter=None, exclude=None):
    entities = Entity.__table__
    match_text = normalize(text, dataset)[:254]

    # select text column and apply necesary transformations
    text_field = entities.c.name
    if dataset.normalize_text:
        text_field = entities.c.normalized
    if dataset.ignore_case:
        text_field = func.lower(text_field)
    text_field = func.left(text_field, 254)
    
    # calculate the difference percentage
    l = func.greatest(1.0, func.least(len(match_text), func.length(text_field)))
    score = func.greatest(0.0, ((l - func.levenshtein(text_field, match_text)) / l) * 100.0)
    score = func.max(score).label('score')

    # coalesce the canonical identifier
    id_ = func.coalesce(entities.c.canonical_id, entities.c.id).label('id')
    
    # apply filters
    filters = [entities.c.dataset_id==dataset.id,
               entities.c.invalid==False]
    if not dataset.match_aliases:
        filters.append(entities.c.canonical_id==None)
    if exclude is not None:
        filters.append(entities.c.id!=exclude)
    if filter is not None:
        filters.append(text_field.ilike('%%%s%%' % filter))

    q = select([id_, score], and_(*filters), [entities],
        group_by=[id_], order_by=[score.desc()])
    return Matches(q)


def attribute_keys(dataset):
    entities = Entity.__table__
    col = func.distinct(func.skeys(entities.c.attributes)).label('keys')
    q = select([col], entities.c.dataset_id==dataset.id, [entities])
    rp = db.engine.execute(q)
    keys = set()
    for row in rp.fetchall():
        keys.add(row[0])
    return sorted(keys)


########NEW FILE########
__FILENAME__ = text
import re
from unidecode import unidecode
from unicodedata import normalize as ucnorm, category
from Levenshtein import distance


REMOVE_SPACES = re.compile(r' +')


def normalize_text(text):
    if not isinstance(text, unicode):
        text = unicode(text)
    chars = []
    # http://www.fileformat.info/info/unicode/category/index.htm
    for char in ucnorm('NFKD', text):
        cat = category(char)[0]
        if cat in ['C', 'Z']:
            chars.append(u' ')
        elif cat in ['P']:
            chars.append(u'.')
        elif cat in ['M']:
            continue
        else:
            chars.append(char)
    text = u''.join(chars)
    text = REMOVE_SPACES.sub(' ', text)
    return unidecode(text).strip()


def normalize(text, dataset):
    if dataset.ignore_case:
        text = text.lower()
    if dataset.normalize_text:
        text = normalize_text(text)
    return text


def similarity(text, txet):
    l = float(max(1, min(len(text), len(txet))))
    s = (l - distance(text, txet)) / l
    return int(max(0, s*100))


########NEW FILE########
__FILENAME__ = upload
from datetime import datetime
from tablib import Dataset as TablibDataset

from nomenklatura.exc import NotFound
from nomenklatura.core import db


class Upload(db.Model):
    __tablename__ = 'upload'

    id = db.Column(db.Integer, primary_key=True)
    mimetype = db.Column(db.Unicode)
    filename = db.Column(db.Unicode)
    data = db.deferred(db.Column(db.LargeBinary))
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


    def to_dict(self):
        data = {
            'id': self.id,
            'mimetype': self.mimetype,
            'filename': self.filename,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'headers': None,
            'sample': None,
            'rows': 0
        }
        if self.tab is not None:
            data['headers'] = self.tab.headers
            data['sample'] = self.tab.dict[:5]
            data['rows'] = self.tab.height
        data['parse_error'] = self._tab_error
        return data

    @property
    def tab(self):
        if not hasattr(self, '_tab'):
            try:
                self._tab = TablibDataset()
                self._tab.csv = self.data
                self._tab_error = None
            except Exception, e:
                self._tab = None
                self._tab_error = unicode(e)
        return self._tab

    @classmethod
    def by_id(cls, dataset, id):
        q = cls.query.filter_by(id=id)
        q = q.filter_by(dataset_id=dataset.id)
        return q.first()

    @classmethod
    def find(cls, dataset, id):
        upload = cls.by_id(dataset, id)
        if upload is None:
            raise NotFound("No such upload: %s" % id)
        return upload

    @classmethod
    def all(cls):
        return cls.query

    @classmethod
    def create(cls, dataset, account, file_):
        upload = cls()
        upload.dataset = dataset
        upload.creator = account
        upload.mimetype = file_.mimetype
        upload.filename = file_.filename
        upload.filename = file_.filename
        upload.data = file_.read()
        db.session.add(upload)
        db.session.flush()
        return upload

########NEW FILE########
__FILENAME__ = common
from datetime import datetime
from StringIO import StringIO
import csv

from flask import Response, request
from formencode import htmlfill
from flask.ext.utils.args import arg_bool, arg_int

from nomenklatura.exc import BadRequest, NotFound
from flask.ext.utils.serialization import jsonify


def get_limit(default=50, field='limit'):
    return max(0, min(1000, arg_int(field, default=default)))


def get_offset(default=0, field='offset'):
    return max(0, arg_int(field, default=default))


def request_data():
    data = request.json
    if data is None:
        raise BadRequest()
    return data


def object_or_404(obj):
    if obj is None:
        raise NotFound()
    return obj


def csv_value(v):
    if v is None:
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    return unicode(v).encode('utf-8')


def csvify(iterable, status=200, headers=None):
    rows = filter(lambda r: r is not None, [r.to_row() for r in iterable])
    keys = set()
    for row in rows:
        keys = keys.union(row.keys())
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([k.encode('utf-8') for k in keys])
    for row in rows:
        writer.writerow([csv_value(row.get(k, '')) for k in keys])
    return Response(buf.getvalue(), headers=headers,
                    status=status, mimetype='text/csv')


def dataset_filename(dataset, format):
    ts = datetime.utcnow().strftime('%Y%m%d')
    return '%s-%s.%s' % (dataset.name, ts, format)

########NEW FILE########
__FILENAME__ = datasets
from flask import Blueprint, request, url_for
from flask import redirect
from flask.ext.utils.serialization import jsonify

from nomenklatura.core import db
from nomenklatura.views.common import request_data
from nomenklatura.views.pager import query_pager
from nomenklatura import authz
from nomenklatura.model import Dataset
from nomenklatura.model.matching import attribute_keys

section = Blueprint('datasets', __name__)


@section.route('/datasets', methods=['GET'])
def index():
    datasets = Dataset.all()
    return query_pager(datasets)


@section.route('/datasets', methods=['POST'])
def create():
    authz.require(authz.dataset_create())
    dataset = Dataset.create(request_data(), request.account)
    db.session.commit()
    return redirect(url_for('.view', dataset=dataset.name))


@section.route('/datasets/<dataset>', methods=['GET'])
def view(dataset):
    dataset = Dataset.find(dataset)
    return jsonify(dataset)


@section.route('/datasets/<dataset>/attributes', methods=['GET'])
def attributes(dataset):
    dataset = Dataset.find(dataset)
    return jsonify({'attributes': attribute_keys(dataset)})


@section.route('/datasets/<dataset>', methods=['POST'])
def update(dataset):
    dataset = Dataset.find(dataset)
    authz.require(authz.dataset_manage(dataset))
    dataset.update(request_data())
    db.session.commit()
    return redirect(url_for('.view', dataset=dataset.name))

########NEW FILE########
__FILENAME__ = entities
from flask import Blueprint, request, url_for
from flask import redirect
from flask.ext.utils.args import arg_bool
from flask.ext.utils.serialization import jsonify

from nomenklatura.core import db
from nomenklatura.views.pager import query_pager
from nomenklatura.views.common import request_data, csvify
from nomenklatura.views.common import dataset_filename, object_or_404
from nomenklatura import authz
from nomenklatura.model import Entity, Dataset

section = Blueprint('entities', __name__)


@section.route('/entities', methods=['GET'])
def index():
    entities = Entity.all()
    dataset_arg = request.args.get('dataset')
    if dataset_arg is not None:
        dataset = Dataset.find(dataset_arg)
        entities = entities.filter_by(dataset=dataset)
    filter_name = request.args.get('filter_name', '')
    if len(filter_name):
        query = '%' + filter_name + '%'
        entities = entities.filter(Entity.name.ilike(query))
    
    # TODO, other filters.
    
    format = request.args.get('format', 'json').lower().strip()
    if format == 'csv':
        res = csvify(entities)
    else:
        res = query_pager(entities)

    if arg_bool('download'):
        fn = dataset_filename(dataset, format)
        res.headers['Content-Disposition'] = 'attachment; filename=' + fn
    return res


@section.route('/entities', methods=['POST'])
def create():
    data = request_data()
    dataset = Dataset.from_form(data)
    authz.require(authz.dataset_edit(dataset))
    entity = Entity.create(dataset, data, request.account)
    db.session.commit()
    return redirect(url_for('.view', id=entity.id))


@section.route('/entities/<int:id>', methods=['GET'])
def view(id):
    entity = object_or_404(Entity.by_id(id))
    return jsonify(entity)


@section.route('/datasets/<dataset>/find', methods=['GET'])
def by_name(dataset):
    dataset = Dataset.find(dataset)
    name = request.args.get('name')
    entity = object_or_404(Entity.by_name(dataset, name))
    return jsonify(entity)


@section.route('/entities/<int:id>/aliases', methods=['GET'])
def aliases(id):
    entity = Entity.by_id(id)
    return query_pager(entity.aliases, id=id)


@section.route('/entities/<id>', methods=['POST'])
def update(id):
    entity = Entity.by_id(id)
    authz.require(authz.dataset_edit(entity.dataset))
    entity.update(request_data(), request.account)
    db.session.commit()
    return redirect(url_for('.view', id=entity.id))


########NEW FILE########
__FILENAME__ = matching
from random import randint

from flask import Blueprint, request
from flask.ext.utils.serialization import jsonify
from flask.ext.utils.args import arg_int

from nomenklatura.views.pager import query_pager
#from nomenklatura import authz
from nomenklatura.model.matching import find_matches
from nomenklatura.model import Dataset, Entity


section = Blueprint('matching', __name__)


@section.route('/match', methods=['GET'])
def match():
    dataset_arg = request.args.get('dataset')
    dataset = Dataset.find(dataset_arg)
    matches = find_matches(dataset,
        request.args.get('name'),
        filter=request.args.get('filter'),
        exclude=arg_int('exclude'))
    return query_pager(matches)


@section.route('/datasets/<dataset>/review', methods=['GET'])
def review(dataset):
    entities = Entity.all()
    dataset = Dataset.find(dataset)
    entities = entities.filter_by(dataset=dataset)
    entities = entities.filter(Entity.reviewed==False)
    review_count = entities.count()
    if review_count == 0:
        return jsonify(None)
    entities = entities.offset(randint(0, review_count-1))
    return jsonify(entities.first())

########NEW FILE########
__FILENAME__ = pager
from urllib import urlencode

from flask import url_for, request
from flask.ext.utils.serialization import jsonify

from nomenklatura.views.common import get_limit, get_offset


SKIP_ARGS = ['limit', 'offset', '_']


def args(limit, offset):
    _args = [('limit', limit), ('offset', offset)]
    for k, v in request.args.items():
        if k not in SKIP_ARGS:
            _args.append((k, v.encode('utf-8')))
    return '?' + urlencode(_args)


def next_url(url, count, offset, limit):
    if count <= (offset + limit):
        return
    return url + args(limit, min(limit + offset, count))


def prev_url(url, count, offset, limit):
    if (offset - limit) < 0:
        return
    return url + args(limit, max(offset - limit, 0))


def query_pager(q, paginate=True, serializer=lambda x: x, **kw):
    limit = get_limit()
    offset = get_offset()
    if paginate:
        results = q.offset(offset).limit(limit)
    else:
        results = q
    url = url_for(request.endpoint, _external=True, **kw)
    count = q.count()
    data = {
        'count': count,
        'limit': limit,
        'offset': offset,
        'format': url + args('LIMIT', 'OFFSET'),
        'previous': prev_url(url, count, offset, limit),
        'next': next_url(url, count, offset, limit),
        'results': map(serializer, results)
    }
    response = jsonify(data, refs=True)
    if data['next']:
        response.headers.add_header('Link', '<%s>; rel=next' % data['next'])
    if data['previous']:
        response.headers.add_header('Link', '<%s>; rel=previous' % data['previous'])
    return response

########NEW FILE########
__FILENAME__ = reconcile
import json 

from flask import Blueprint, request, url_for
from flask.ext.utils.serialization import jsonify

from nomenklatura.exc import BadRequest
from nomenklatura.model import Dataset, Entity
from nomenklatura.views.common import get_limit, get_offset
from nomenklatura.model.matching import find_matches


section = Blueprint('reconcile', __name__)


def reconcile_index(dataset):
    domain = url_for('index', _external=True).strip('/')
    urlp = domain + '/entities/{{id}}'
    meta = {
        'name': 'nomenklatura: %s' % dataset.label,
        'identifierSpace': 'http://rdf.freebase.com/ns/type.object.id',
        'schemaSpace': 'http://rdf.freebase.com/ns/type.object.id',
        'view': {'url': urlp},
        'preview': {
            'url': urlp + '?preview=true', 
            'width': 600,
            'height': 300
        },
        'suggest': {
            'entity': {
                'service_url': domain,
                'service_path': '/api/2/datasets/' + dataset.name + '/suggest'
            }
        },
        'defaultTypes': [{'name': dataset.label, 'id': '/' + dataset.name}]
    }
    return jsonify(meta)


def reconcile_op(dataset, query):
    try:
        limit = max(1, min(100, int(query.get('limit'))))
    except:
        limit = 5

    matches = find_matches(dataset, query.get('query', ''))
    matches = matches.limit(limit)

    results = []
    for match in matches:
        results.append({
            'name': match['entity'].name,
            'score': match['score'],
            'type': [{
                'id': '/' + dataset.name,
                'name': dataset.label
                }],
            'id': match['entity'].id,
            'uri': url_for('entities.view', id=match['entity'].id, _external=True),
            'match': match['score']==100
        })
    return {
        'result': results, 
        'num': len(results)
        }


@section.route('/datasets/<dataset>/reconcile', methods=['GET', 'POST'])
def reconcile(dataset):
    """
    Reconciliation API, emulates Google Refine API. See: 
    http://code.google.com/p/google-refine/wiki/ReconciliationServiceApi
    """
    dataset = Dataset.by_name(dataset)

    # TODO: Add proper support for types and namespacing.
    data = request.args.copy()
    data.update(request.form.copy())
    if 'query' in data:
        # single 
        q = data.get('query')
        if q.startswith('{'):
            try:
                q = json.loads(q)
            except ValueError:
                raise BadRequest()
        else:
            q = data
        return jsonify(reconcile_op(dataset, q))
    elif 'queries' in data:
        # multiple requests in one query
        qs = data.get('queries')
        try:
            qs = json.loads(qs)
        except ValueError:
            raise BadRequest()
        queries = {}
        for k, q in qs.items():
            queries[k] = reconcile_op(dataset, q)
        return jsonify(queries)
    else:
        return reconcile_index(dataset)


@section.route('/datasets/<dataset>/suggest', methods=['GET', 'POST'])
def suggest(dataset):
    """ 
    Suggest API, emulates Google Refine API. See:
    http://code.google.com/p/google-refine/wiki/SuggestApi
    """
    dataset = Dataset.by_name(dataset)
    entities = Entity.all().filter(Entity.invalid!=True)
    query = request.args.get('prefix', '').strip()
    entities = entities.filter(Entity.name.ilike('%s%%' % query))
    entities = entities.offset(get_offset(field='start'))
    entities = entities.limit(get_limit(default=20))

    matches = []
    for entity in entities:
        matches.append({
            'name': entity.name,
            'n:type': {
                'id': '/' + dataset.name,
                'name': dataset.label
                },
            'id': entity.id
            })
    return jsonify({
        "code" : "/api/status/ok",
        "status" : "200 OK",
        "prefix" : query,
        "result" : matches
        })

########NEW FILE########
__FILENAME__ = sessions
import requests
from flask import url_for, session, Blueprint, redirect
from flask import request
from flask.ext.utils.serialization import jsonify

from nomenklatura import authz
from nomenklatura.core import db, github
from nomenklatura.model import Account, Dataset

section = Blueprint('sessions', __name__)


@section.route('/sessions')
def status():
    return jsonify({
        'logged_in': authz.logged_in(),
        'api_key': request.account.api_key if authz.logged_in() else None,
        'account': request.account,
        'base_url': url_for('index', _external=True)
    })


@section.route('/sessions/authz')
def get_authz():
    permissions = {}
    dataset_name = request.args.get('dataset')
    if dataset_name is not None:
        dataset = Dataset.find(dataset_name)
        permissions[dataset_name] = {
            'view': True,
            'edit': authz.dataset_edit(dataset),
            'manage': authz.dataset_manage(dataset)
        }
    return jsonify(permissions)


@section.route('/sessions/login')
def login():
    callback=url_for('sessions.authorized', _external=True)
    return github.authorize(callback=callback)


@section.route('/sessions/logout')
def logout():
    authz.require(authz.logged_in())
    session.clear()
    return redirect('/')


@section.route('/sessions/callback')
@github.authorized_handler
def authorized(resp):
    if not 'access_token' in resp:
        return redirect(url_for('index'))
    access_token = resp['access_token']
    session['access_token'] = access_token, ''
    res = requests.get('https://api.github.com/user?access_token=%s' % access_token,
            verify=False)
    data = res.json()
    for k, v in data.items():
        session[k] = v
    account = Account.by_github_id(data.get('id'))
    if account is None:
        account = Account.create(data)
        db.session.commit()
    return redirect('/')

########NEW FILE########
__FILENAME__ = upload
from flask import Blueprint, request, url_for, flash
from formencode import Invalid
from flask.ext.utils.serialization import jsonify

from nomenklatura.views.common import request_data
from nomenklatura import authz
from nomenklatura.core import db
from nomenklatura.model import Dataset, Upload
from nomenklatura.importer import import_upload

section = Blueprint('upload', __name__)


@section.route('/datasets/<dataset>/uploads', methods=['POST'])
def upload(dataset):
    dataset = Dataset.find(dataset)
    authz.require(authz.dataset_edit(dataset))
    file_ = request.files.get('file')
    if not file_ or not file_.filename:
        err = {'file': "You need to upload a file"}
        raise Invalid("No file.", None, None, error_dict=err)
    upload = Upload.create(dataset, request.account, file_)
    db.session.commit()
    return jsonify(upload)


@section.route('/datasets/<dataset>/uploads/<id>', methods=['GET'])
def view(dataset, id):
    dataset = Dataset.find(dataset)
    authz.require(authz.dataset_edit(dataset))
    upload = Upload.find(dataset, id)
    return jsonify(upload)


@section.route('/datasets/<dataset>/uploads/<id>', methods=['POST'])
def process(dataset, id):
    dataset = Dataset.find(dataset)
    authz.require(authz.dataset_edit(dataset))
    upload = Upload.find(dataset, id)
    mapping = request_data()
    mapping['reviewed'] = mapping.get('reviewed') or False
    mapping['columns'] = mapping.get('columns', {})
    fields = mapping['columns'].values()
    for header in mapping['columns'].keys():
        if header not in upload.tab.headers:
            raise Invalid("Invalid header: %s" % header, None, None)    

    if 'name' not in fields and 'id' not in fields:
        raise Invalid("You have not selected a field that definies entity names.", None, None)

    import_upload.delay(upload.id, request.account.id, mapping)
    return jsonify({'status': 'Loading data...'})

########NEW FILE########
