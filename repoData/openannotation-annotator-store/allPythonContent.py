__FILENAME__ = annotation
from annotator import authz, document, es

from flask import current_app, g

TYPE = 'annotation'
MAPPING = {
    'annotator_schema_version': {'type': 'string'},
    'created': {'type': 'date'},
    'updated': {'type': 'date'},
    'quote': {'type': 'string'},
    'tags': {'type': 'string', 'index_name': 'tag'},
    'text': {'type': 'string'},
    'uri': {'type': 'string', 'index': 'not_analyzed'},
    'user': {'type': 'string', 'index': 'not_analyzed'},
    'consumer': {'type': 'string', 'index': 'not_analyzed'},
    'ranges': {
        'index_name': 'range',
        'properties': {
            'start': {'type': 'string', 'index': 'not_analyzed'},
            'end': {'type': 'string', 'index': 'not_analyzed'},
            'startOffset': {'type': 'integer'},
            'endOffset': {'type': 'integer'},
        }
    },
    'permissions': {
        'index_name': 'permission',
        'properties': {
            'read': {'type': 'string', 'index': 'not_analyzed'},
            'update': {'type': 'string', 'index': 'not_analyzed'},
            'delete': {'type': 'string', 'index': 'not_analyzed'},
            'admin': {'type': 'string', 'index': 'not_analyzed'}
        }
    },
    'document': {
        'properties': document.MAPPING
    }
}


class Annotation(es.Model):

    __type__ = TYPE
    __mapping__ = MAPPING

    def save(self, *args, **kwargs):
        _add_default_permissions(self)

        # If the annotation includes document metadata look to see if we have
        # the document modeled already. If we don't we'll create a new one
        # If we do then we'll merge the supplied links into it.

        if 'document' in self:
            d = self['document']
            uris = [link['href'] for link in d['link']]
            docs = document.Document.get_all_by_uris(uris)

            if len(docs) == 0:
                doc = document.Document(d)
                doc.save()
            else:
                doc = docs[0]
                links = d.get('link', [])
                doc.merge_links(links)
                doc.save()

        super(Annotation, self).save(*args, **kwargs)

    @classmethod
    def _build_query(cls, offset=0, limit=20, **kwargs):
        q = super(Annotation, cls)._build_query(offset, limit, **kwargs)

        # attempt to expand query to include uris for other representations
        # using information we may have on hand about the Document
        if 'uri' in kwargs:
            term_filter = q['query']['filtered']['filter']
            doc = document.Document.get_by_uri(kwargs['uri'])
            if doc:
                new_terms = []
                for term in term_filter['and']:
                    if 'uri' in term['term']:
                        term = {'or': []}
                        for uri in doc.uris():
                            term['or'].append({'term': {'uri': uri}})
                    new_terms.append(term)

                term_filter['and'] = new_terms

        if current_app.config.get('AUTHZ_ON'):
            f = authz.permissions_filter(g.user)
            if not f:
                return False  # Refuse to perform the query
            q['query'] = {'filtered': {'query': q['query'], 'filter': f}}

        return q

    @classmethod
    def _build_query_raw(cls, request):
        q, p = super(Annotation, cls)._build_query_raw(request)

        if current_app.config.get('AUTHZ_ON'):
            f = authz.permissions_filter(g.user)
            if not f:
                return {'error': 'Authorization error!', 'status': 400}, None
            q['query'] = {'filtered': {'query': q['query'], 'filter': f}}

        return q, p


def _add_default_permissions(ann):
    if 'permissions' not in ann:
        ann['permissions'] = {'read': [authz.GROUP_CONSUMER]}

########NEW FILE########
__FILENAME__ = atoi
def atoi(v, default=0):
    try:
        return int(v or default)
    except ValueError:
        return default

########NEW FILE########
__FILENAME__ = auth
import datetime

import iso8601
import jwt

DEFAULT_TTL = 86400


class Consumer(object):
    def __init__(self, key):
        self.key = key


class User(object):
    def __init__(self, id, consumer, is_admin):
        self.id = id
        self.consumer = consumer
        self.is_admin = is_admin

    @classmethod
    def from_token(cls, token):
        return cls(token['userId'],
                   Consumer(token['consumerKey']),
                   token.get('admin', False))


class Authenticator(object):
    """
    A wrapper around the low-level encode_token() and decode_token() that is
    backend inspecific, and swallows all possible exceptions thrown by badly-
    formatted, invalid, or malicious tokens.
    """

    def __init__(self, consumer_fetcher):
        """
        Arguments:
        consumer_fetcher -- a function which takes a consumer key and returns
                            an object with 'key', 'secret', and 'ttl'
                            attributes
        """
        self.consumer_fetcher = consumer_fetcher

    def request_user(self, request):
        """
        Retrieve the user object associated with the current request.

        Arguments:
        request -- a Flask Request object

        Returns: a user object
        """
        token = self._decode_request_token(request)

        if token:
            try:
                return User.from_token(token)
            except KeyError:
                return None
        else:
            return None

    def _decode_request_token(self, request):
        """
        Retrieve any request token from the passed request, verify its
        authenticity and validity, and return the parsed contents of the token
        if and only if all such checks pass.

        Arguments:
        request -- a Flask Request object
        """

        token = request.headers.get('x-annotator-auth-token')
        if token is None:
            return False

        try:
            unsafe_token = decode_token(token, verify=False)
        except TokenInvalid:  # catch junk tokens
            return False

        key = unsafe_token.get('consumerKey')
        if not key:
            return False

        consumer = self.consumer_fetcher(key)
        if not consumer:
            return False

        try:
            return decode_token(token,
                                secret=consumer.secret,
                                ttl=consumer.ttl)
        except TokenInvalid:  # catch inauthentic or expired tokens
            return False


class TokenInvalid(Exception):
    pass


# Main auth routines

def encode_token(token, secret):
    token.update({'issuedAt': _now().isoformat()})
    return jwt.encode(token, secret)


def decode_token(token, secret='', ttl=DEFAULT_TTL, verify=True):
    try:
        token = jwt.decode(str(token), secret, verify=verify)
    except jwt.DecodeError:
        import sys
        exc_class, exc, tb = sys.exc_info()
        new_exc = TokenInvalid("error decoding JSON Web Token: %s" %
                               exc or exc_class)
        raise new_exc.__class__, new_exc, tb

    if verify:
        issue_time = token.get('issuedAt')
        if issue_time is None:
            raise TokenInvalid("'issuedAt' is missing from token")

        issue_time = iso8601.parse_date(issue_time)
        expiry_time = issue_time + datetime.timedelta(seconds=ttl)

        if issue_time > _now():
            raise TokenInvalid("token is not yet valid")
        if expiry_time < _now():
            raise TokenInvalid("token has expired")

    return token


def _now():
    return datetime.datetime.now(iso8601.iso8601.UTC).replace(microsecond=0)

########NEW FILE########
__FILENAME__ = authz
# An action is permitted in any of the following scenarios:
#
# 1) the permissions field for the specified action contains the magic value
#    'group:__world__'
#
# 2) the user and consumer match those of the annotation (i.e. the
#    authenticated user is the owner of the annotation)
#
# 3) a user and consumer are provided and the permissions field contains the
#    magic value 'group:__authenticated__'
#
# 4) the provided consumer matches that of the annotation and the permissions
#    field for the specified action contains the magic value
#    'group:__consumer__'
#
# 5) the consumer matches that of the annotation and the user is listed in the
#    permissions field for the specified action
#
# 6) the consumer matches that of the annotation and the user is an admin

GROUP_WORLD = 'group:__world__'
GROUP_AUTHENTICATED = 'group:__authenticated__'
GROUP_CONSUMER = 'group:__consumer__'


def authorize(annotation, action, user=None):
    action_field = annotation.get('permissions', {}).get(action, [])

    # Scenario 1
    if GROUP_WORLD in action_field:
        return True

    elif user is not None:
        # Fail fast if this looks dodgy
        if user.id.startswith('group:'):
            return False

        ann_uid, ann_ckey = _annotation_owner(annotation)

        # Scenario 2
        if (user.id, user.consumer.key) == (ann_uid, ann_ckey):
            return True

        # Scenario 3
        elif GROUP_AUTHENTICATED in action_field:
            return True

        # Scenario 4
        elif user.consumer.key == ann_ckey and GROUP_CONSUMER in action_field:
            return True

        # Scenario 5
        elif user.consumer.key == ann_ckey and user.id in action_field:
            return True

        # Scenario 6
        elif user.consumer.key == ann_ckey and user.is_admin:
            return True

    return False


def _annotation_owner(annotation):
    user = annotation.get('user')
    consumer = annotation.get('consumer')

    if not user:
        return (user, consumer)

    try:
        return (user.get('id', None), consumer)
    except AttributeError:
        return (user, consumer)


def permissions_filter(user=None):
    """Filter an ElasticSearch query by the permissions of the current user"""

    # Scenario 1
    perm_f = {'term': {'permissions.read': GROUP_WORLD}}

    if user is not None:
        # Fail fast if this looks dodgy
        if user.id.startswith('group:'):
            return False

        perm_f = {'or': [perm_f]}

        # Scenario 2
        perm_f['or'].append(
            {'and': [{'term': {'consumer': user.consumer.key}},
                     {'or': [{'term': {'user': user.id}},
                             {'term': {'user.id': user.id}}]}]})

        # Scenario 3
        perm_f['or'].append(
            {'term': {'permissions.read': GROUP_AUTHENTICATED}})

        # Scenario 4
        perm_f['or'].append(
            {'and': [{'term': {'consumer': user.consumer.key}},
                     {'term': {'permissions.read': GROUP_CONSUMER}}]})

        # Scenario 5
        perm_f['or'].append(
            {'and': [{'term': {'consumer': user.consumer.key}},
                     {'term': {'permissions.read': user.id}}]})

        # Scenario 6
        if user.is_admin:
            perm_f['or'].append({'term': {'consumer': user.consumer.key}})

    return perm_f

########NEW FILE########
__FILENAME__ = document
from annotator import es

TYPE = 'document'
MAPPING = {
    'annotator_schema_version': {'type': 'string'},
    'created': {'type': 'date'},
    'updated': {'type': 'date'},
    'title': {'type': 'string'},
    'link': {
        'type': 'nested',
        'properties': {
            'type': {'type': 'string', 'index': 'not_analyzed'},
            'href': {'type': 'string', 'index': 'not_analyzed'},
        }
    },
    'dc': {
        'type': 'nested',
        'properties': {
            # by default elastic search will try to parse this as
            # a date but unfortunately the data that is in the wild
            # may not be parsable by ES which throws an exception
            'date': {'type': 'string', 'index': 'not_analyzed'}
        }
    }
}


class Document(es.Model):
    __type__ = TYPE
    __mapping__ = MAPPING

    @classmethod
    def get_by_uri(cls, uri):
        """Returns the first document match for a given URI."""
        results = cls.get_all_by_uris([uri])
        return results[0] if len(results) > 0 else []

    @classmethod
    def get_all_by_uris(cls, uris):
        """
        Returns a list of documents that have any of the supplied URIs.

        It is only necessary for one of the supplied URIs to match.
        """
        q = {'query': {'nested': {'path': 'link',
                                  'query': {'terms': {'link.href': uris}}}},
             'sort': [{'updated': {'order': 'asc'}}]}

        res = cls.es.conn.search(index=cls.es.index,
                                 doc_type=cls.__type__,
                                 body=q)
        return [cls(d['_source'], id=d['_id']) for d in res['hits']['hits']]

    def uris(self):
        """Returns a list of the URIs for the document."""
        return self._uris_from_links(self.get('link', []))

    def merge_links(self, links):
        current_uris = self.uris()
        for l in links:
            if 'href' in l and 'type' in l and l['href'] not in current_uris:
                self['link'].append(l)

    def _uris_from_links(self, links):
        uris = []
        for link in links:
            uris.append(link.get('href'))
        return uris

########NEW FILE########
__FILENAME__ = elasticsearch
from __future__ import absolute_import

import csv
import json
import logging
import datetime
import urlparse

import iso8601

import elasticsearch
from flask import current_app
from flask import _app_ctx_stack as stack
from annotator.atoi import atoi

log = logging.getLogger(__name__)

RESULTS_MAX_SIZE = 200


class ElasticSearch(object):
    """

    Thin wrapper around an ElasticSearch connection to make connection handling
    transparent in a Flask application. Usage:

        app = Flask(__name__)
        es = ElasticSearch(app)

    Or, you can bind the object to the application later:

        es = ElasticSearch()

        def create_app():
            app = Flask(__name__)
            es.init_app(app)
            return app

    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

        self.Model = make_model(self)

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_HOST', 'http://127.0.0.1:9200')
        app.config.setdefault('ELASTICSEARCH_INDEX', app.name)
        app.config.setdefault('ELASTICSEARCH_COMPATIBILITY_MODE', None)

    def connect(self):
        host = current_app.config['ELASTICSEARCH_HOST']
        parsed = urlparse.urlparse(host)

        connargs = {
          'host': parsed.hostname,
        }

        username = parsed.username
        password = parsed.password
        if username is not None or password is not None:
            connargs['http_auth'] = ((username or ''), (password or ''))

        if parsed.port is not None:
            connargs['port'] = parsed.port

        if parsed.path:
            connargs['url_prefix'] = parsed.path

        conn = elasticsearch.Elasticsearch(
            hosts=[connargs],
            connection_class=elasticsearch.Urllib3HttpConnection)
        return conn

    @property
    def conn(self):
        ctx = stack.top
        if not hasattr(ctx, 'elasticsearch'):
            ctx.elasticsearch = self.connect()
        return ctx.elasticsearch

    @property
    def index(self):
        return current_app.config['ELASTICSEARCH_INDEX']

    @property
    def compatibility_mode(self):
        return current_app.config['ELASTICSEARCH_COMPATIBILITY_MODE']


class _Model(dict):

    @classmethod
    def create_all(cls):
        logging.info("creating index " + cls.es.index)
        try:
            cls.es.conn.indices.create(cls.es.index)
        except elasticsearch.exceptions.RequestError as e:
            # Reraise anything that isn't just a notification that the index
            # already exists
            if not e.error.startswith('IndexAlreadyExistsException'):
                raise
            log.warn('Index creation failed. If you are running against '
                     'Bonsai Elasticsearch, this is expected and ignorable.')
        mapping = {cls.__type__: {'properties': cls.__mapping__}}
        cls.es.conn.indices.put_mapping(index=cls.es.index,
                                        doc_type=cls.__type__,
                                        body=mapping)

    @classmethod
    def drop_all(cls):
        if cls.es.conn.indices.exists(cls.es.index):
            cls.es.conn.indices.close(cls.es.index)
            cls.es.conn.indices.delete(cls.es.index)

    # It would be lovely if this were called 'get', but the dict semantics
    # already define that method name.
    @classmethod
    def fetch(cls, id):
        try:
            doc = cls.es.conn.get(index=cls.es.index,
                                  doc_type=cls.__type__,
                                  id=id)
        except elasticsearch.exceptions.NotFoundError:
            return None
        return cls(doc['_source'], id=id)

    @classmethod
    def _build_query(cls, offset=0, limit=20, **kwargs):
        return _build_query(offset, limit, kwargs)

    @classmethod
    def _build_query_raw(cls, request):
        return _build_query_raw(request)

    @classmethod
    def search(cls, **kwargs):
        q = cls._build_query(**kwargs)
        if not q:
            return []
        logging.debug("doing search: %s", q)
        res = cls.es.conn.search(index=cls.es.index,
                                 doc_type=cls.__type__,
                                 body=q)
        docs = res['hits']['hits']
        return [cls(d['_source'], id=d['_id']) for d in docs]

    @classmethod
    def search_raw(cls, request):
        q, params = cls._build_query_raw(request)
        if 'error' in q:
            return q
        try:
            res = cls.es.conn.search(index=cls.es.index,
                                     doc_type=cls.__type__,
                                     body=q,
                                     **params)
        except elasticsearch.exceptions.ElasticsearchException as e:
            return e.result
        else:
            return res

    @classmethod
    def count(cls, **kwargs):
        q = cls._build_query(**kwargs)
        if not q:
            return 0

        # Extract the query, and wrap it in the expected object. This has the
        # effect of removing sort or paging parameters that aren't allowed by
        # the count API.
        q = {'query': q['query']}

        # In elasticsearch prior to 1.0.0, the payload to `count` was a bare
        # query.
        if cls.es.compatibility_mode == 'pre-1.0.0':
            q = q['query']

        res = cls.es.conn.count(index=cls.es.index,
                                doc_type=cls.__type__,
                                body=q)
        return res['count']

    def _set_id(self, rhs):
        self['id'] = rhs

    def _get_id(self):
        return self.get('id')

    id = property(_get_id, _set_id)

    def save(self, refresh=True):
        _add_created(self)
        _add_updated(self)
        res = self.es.conn.index(index=self.es.index,
                                 doc_type=self.__type__,
                                 id=self.id,
                                 body=self,
                                 refresh=refresh)
        self.id = res['_id']

    def delete(self):
        if self.id:
            self.es.conn.delete(index=self.es.index,
                                doc_type=self.__type__,
                                id=self.id)


def make_model(es):
    return type('Model', (_Model,), {'es': es})


def _csv_split(s, delimiter=','):
    return [r for r in csv.reader([s], delimiter=delimiter)][0]


def _build_query(offset, limit, kwds):
    # Base query is a filtered match_all
    q = {'match_all': {}}

    if kwds:
        f = {'and': []}
        q = {'filtered': {'query': q, 'filter': f}}

    # Add a term query for each keyword
    for k, v in kwds.iteritems():
        q['filtered']['filter']['and'].append({'term': {k: v}})

    return {
        'sort': [{'updated': {'order': 'desc'}}],  # Sort most recent first
        'from': max(0, offset),
        'size': min(RESULTS_MAX_SIZE, max(0, limit)),
        'query': q
    }


def _build_query_raw(request):
    query = {}
    params = {}

    if request.method == 'GET':
        for k, v in request.args.iteritems():
            _update_query_raw(query, params, k, v)

        if 'query' not in query:
            query['query'] = {'match_all': {}}

    elif request.method == 'POST':

        try:
            query = json.loads(request.json or
                               request.data or
                               request.form.keys()[0])
        except (ValueError, IndexError):
            return ({'error': 'Could not parse request payload!',
                     'status': 400},
                    None)

        params = request.args

    for o in (params, query):
        if 'from' in o:
            o['from'] = max(0, atoi(o['from']))
        if 'size' in o:
            o['size'] = min(RESULTS_MAX_SIZE, max(0, atoi(o['size'])))

    return query, params


def _update_query_raw(qo, params, k, v):
    if 'query' not in qo:
        qo['query'] = {}
    q = qo['query']

    if 'query_string' not in q:
        q['query_string'] = {}
    qs = q['query_string']

    if k == 'q':
        qs['query'] = v

    elif k == 'df':
        qs['default_field'] = v

    elif k in ('explain', 'track_scores', 'from', 'size', 'timeout',
               'lowercase_expanded_terms', 'analyze_wildcard'):
        qo[k] = v

    elif k == 'fields':
        qo[k] = _csv_split(v)

    elif k == 'sort':
        if 'sort' not in qo:
            qo[k] = []

        split = _csv_split(v, ':')

        if len(split) == 1:
            qo[k].append(split[0])
        else:
            fld = ':'.join(split[0:-1])
            drn = split[-1]
            qo[k].append({fld: drn})

    elif k == 'search_type':
        params[k] = v


def _add_created(ann):
    if 'created' not in ann:
        ann['created'] = datetime.datetime.now(iso8601.iso8601.UTC).isoformat()


def _add_updated(ann):
    ann['updated'] = datetime.datetime.now(iso8601.iso8601.UTC).isoformat()

########NEW FILE########
__FILENAME__ = store
import json

from flask import Blueprint, Response
from flask import g
from flask import request
from flask import url_for

from annotator.atoi import atoi
from annotator.annotation import Annotation

store = Blueprint('store', __name__)

CREATE_FILTER_FIELDS = ('updated', 'created', 'consumer')
UPDATE_FILTER_FIELDS = ('updated', 'created', 'user', 'consumer')


# We define our own jsonify rather than using flask.jsonify because we wish
# to jsonify arbitrary objects (e.g. index returns a list) rather than kwargs.
def jsonify(obj, *args, **kwargs):
    res = json.dumps(obj, indent=None if request.is_xhr else 2)
    return Response(res, mimetype='application/json', *args, **kwargs)


@store.before_request
def before_request():
    if not hasattr(g, 'annotation_class'):
        g.annotation_class = Annotation

    user = g.auth.request_user(request)
    if user is not None:
        g.user = user
    elif not hasattr(g, 'user'):
        g.user = None


@store.after_request
def after_request(response):
    ac = 'Access-Control-'
    rh = response.headers

    rh[ac + 'Allow-Origin'] = request.headers.get('origin', '*')
    rh[ac + 'Expose-Headers'] = 'Content-Length, Content-Type, Location'

    if request.method == 'OPTIONS':
        rh[ac + 'Allow-Headers'] = ('Content-Length, Content-Type, '
                                    'X-Annotator-Auth-Token, X-Requested-With')
        rh[ac + 'Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        rh[ac + 'Max-Age'] = '86400'

    return response


# ROOT
@store.route('/')
def root():
    return jsonify({
        'message': "Annotator Store API",
        'links': {
            'annotation': {
                'create': {
                    'method': 'POST',
                    'url': url_for('.create_annotation', _external=True),
                    'query': {
                        'refresh': {
                            'type': 'bool',
                            'desc': ("Force an index refresh after create "
                                     "(default: true)")
                        }
                    },
                    'desc': "Create a new annotation"
                },
                'read': {
                    'method': 'GET',
                    'url': url_for('.read_annotation',
                                   id=':id',
                                   _external=True),
                    'desc': "Get an existing annotation"
                },
                'update': {
                    'method': 'PUT',
                    'url':
                    url_for(
                        '.update_annotation',
                        id=':id',
                        _external=True),
                    'query': {
                        'refresh': {
                            'type': 'bool',
                            'desc': ("Force an index refresh after update "
                                     "(default: true)")
                        }
                    },
                    'desc': "Update an existing annotation"
                },
                'delete': {
                    'method': 'DELETE',
                    'url': url_for('.delete_annotation',
                                   id=':id',
                                   _external=True),
                    'desc': "Delete an annotation"
                }
            },
            'search': {
                'method': 'GET',
                'url': url_for('.search_annotations', _external=True),
                'desc': 'Basic search API'
            },
            'search_raw': {
                'method': 'GET/POST',
                'url': url_for('.search_annotations_raw', _external=True),
                'desc': ('Advanced search API -- direct access to '
                         'ElasticSearch. Uses the same API as the '
                         'ElasticSearch query endpoint.')
            }
        }
    })


# INDEX
@store.route('/annotations')
def index():
    annotations = g.annotation_class.search()
    return jsonify(annotations)

# CREATE
@store.route('/annotations', methods=['POST'])
def create_annotation():
    # Only registered users can create annotations
    if g.user is None:
        return _failed_authz_response('create annotation')

    if request.json is not None:
        annotation = g.annotation_class(
            _filter_input(
                request.json,
                CREATE_FILTER_FIELDS))

        annotation['consumer'] = g.user.consumer.key
        if _get_annotation_user(annotation) != g.user.id:
            annotation['user'] = g.user.id

        if hasattr(g, 'before_annotation_create'):
            g.before_annotation_create(annotation)

        if hasattr(g, 'after_annotation_create'):
            annotation.save(refresh=False)
            g.after_annotation_create(annotation)

        refresh = request.args.get('refresh') != 'false'
        annotation.save(refresh=refresh)

        return jsonify(annotation)
    else:
        return jsonify('No JSON payload sent. Annotation not created.',
                       status=400)


# READ
@store.route('/annotations/<id>')
def read_annotation(id):
    annotation = g.annotation_class.fetch(id)
    if not annotation:
        return jsonify('Annotation not found!', status=404)

    failure = _check_action(annotation, 'read')
    if failure:
        return failure

    return jsonify(annotation)


# UPDATE
@store.route('/annotations/<id>', methods=['POST', 'PUT'])
def update_annotation(id):
    annotation = g.annotation_class.fetch(id)
    if not annotation:
        return jsonify('Annotation not found! No update performed.',
                       status=404)

    failure = _check_action(annotation, 'update')
    if failure:
        return failure

    if request.json is not None:
        updated = _filter_input(request.json, UPDATE_FILTER_FIELDS)
        updated['id'] = id  # use id from URL, regardless of what arrives in
                            # JSON payload

        changing_permissions = (
            'permissions' in updated and
            updated['permissions'] != annotation.get('permissions', {}))

        if changing_permissions:
            failure = _check_action(annotation,
                                    'admin',
                                    message='permissions update')
            if failure:
                return failure

        annotation.update(updated)

        if hasattr(g, 'before_annotation_update'):
            g.before_annotation_update(annotation)

        refresh = request.args.get('refresh') != 'false'
        annotation.save(refresh=refresh)

        if hasattr(g, 'after_annotation_update'):
            g.after_annotation_update(annotation)

    return jsonify(annotation)


# DELETE
@store.route('/annotations/<id>', methods=['DELETE'])
def delete_annotation(id):
    annotation = g.annotation_class.fetch(id)

    if not annotation:
        return jsonify('Annotation not found. No delete performed.',
                       status=404)

    failure = _check_action(annotation, 'delete')
    if failure:
        return failure

    if hasattr(g, 'before_annotation_delete'):
        g.before_annotation_delete(annotation)

    annotation.delete()

    if hasattr(g, 'after_annotation_delete'):
        g.after_annotation_delete(annotation)

    return '', 204


# SEARCH
@store.route('/search')
def search_annotations():
    kwargs = dict(request.args.items())

    if 'offset' in kwargs:
        kwargs['offset'] = atoi(kwargs['offset'])
    if 'limit' in kwargs:
        kwargs['limit'] = atoi(kwargs['limit'], 20)

    results = g.annotation_class.search(**kwargs)
    total = g.annotation_class.count(**kwargs)
    return jsonify({'total': total,
                    'rows': results})


# RAW ES SEARCH
@store.route('/search_raw', methods=['GET', 'POST'])
def search_annotations_raw():
    res = g.annotation_class.search_raw(request)
    return jsonify(res, status=res.get('status', 200))


def _filter_input(obj, fields):
    for field in fields:
        obj.pop(field, None)

    return obj


def _get_annotation_user(ann):
    """Returns the best guess at this annotation's owner user id"""
    user = ann.get('user')

    if not user:
        return None

    try:
        return user.get('id', None)
    except AttributeError:
        return user


def _check_action(annotation, action, message=''):
    if not g.authorize(annotation, action, g.user):
        return _failed_authz_response(message)


def _failed_authz_response(msg=''):
    user = g.user.id if g.user else None
    consumer = g.user.consumer.key if g.user else None
    return jsonify("Cannot authorize request{0}. Perhaps you're not logged in "
                   "as a user with appropriate permissions on this "
                   "annotation? "
                   "(user={user}, consumer={consumer})".format(
                       ' (' + msg + ')' if msg else '',
                       user=user,
                       consumer=consumer),
                   status=401)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Annotator documentation build configuration file, created by
# sphinx-quickstart on Thu Feb 27 00:10:13 2014.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, pkg_resources

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Annotator'
copyright = u'2014, Open Knowledge Foundation and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = pkg_resources.get_distribution('annotator').version

# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Annotatordoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Annotator.tex', u'Annotator Documentation',
   u'Open Knowledge Foundation and contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'annotator', u'Annotator Documentation',
     [u'Open Knowledge Foundation and contributors'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Annotator', u'Annotator Documentation',
   u'Open Knowledge Foundation and contributors', 'Annotator', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
"""
run.py: A simple example app for using the Annotator Store blueprint

This file creates and runs a Flask[1] application which mounts the Annotator
Store blueprint at its root. It demonstrates how the major components of the
Annotator Store (namely the 'store' blueprint, the annotation model and the
auth and authz helper modules) fit together, but it is emphatically NOT
INTENDED FOR PRODUCTION USE.

[1]: http://flask.pocoo.org
"""

from __future__ import print_function

import os
import sys

from flask import Flask, g, current_app
from annotator import es, annotation, auth, authz, document, store
from tests.helpers import MockUser, MockConsumer, MockAuthenticator
from tests.helpers import mock_authorizer

here = os.path.dirname(__file__)

def main():
    app = Flask(__name__)

    cfg_file = 'annotator.cfg'
    if len(sys.argv) == 2:
        cfg_file = sys.argv[1]

    cfg_path = os.path.join(here, cfg_file)

    try:
        app.config.from_pyfile(cfg_path)
    except IOError:
        print("Could not find config file %s" % cfg_path, file=sys.stderr)
        print("Perhaps you need to copy annotator.cfg.example to annotator.cfg", file=sys.stderr)
        sys.exit(1)

    es.init_app(app)

    with app.test_request_context():
        annotation.Annotation.create_all()
        document.Document.create_all()

    @app.before_request
    def before_request():
        # In a real app, the current user and consumer would be determined by
        # a lookup in either the session or the request headers, as described
        # in the Annotator authentication documentation[1].
        #
        # [1]: https://github.com/okfn/annotator/wiki/Authentication
        g.user = MockUser('alice')

        # By default, this test application won't do full-on authentication
        # tests. Set AUTH_ON to True in the config file to enable (limited)
        # authentication testing.
        if current_app.config['AUTH_ON']:
            g.auth = auth.Authenticator(lambda x: MockConsumer('annotateit'))
        else:
            g.auth = MockAuthenticator()

        # Similarly, this test application won't prevent you from modifying
        # annotations you don't own, deleting annotations you're disallowed
        # from deleting, etc. Set AUTHZ_ON to True in the config file to
        # enable authorization testing.
        if current_app.config['AUTHZ_ON']:
            g.authorize = authz.authorize
        else:
            g.authorize = mock_authorizer

    app.register_blueprint(store.store)

    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = helpers
class MockConsumer(object):
    def __init__(self, key='mockconsumer'):
        self.key = key
        self.secret = 'top-secret'
        self.ttl = 86400

class MockUser(object):
    def __init__(self, id='alice', consumer=None):
        self.id = id
        self.consumer = MockConsumer(consumer if consumer is not None else 'mockconsumer')
        self.is_admin = False


class MockAuthenticator(object):
    def request_user(self, request):
        return MockUser()

def mock_authorizer(*args, **kwargs):
    return True

########NEW FILE########
__FILENAME__ = test_annotation
from nose.tools import *
from mock import MagicMock
from . import TestCase, helpers as h

from flask import g

from annotator import es
from annotator.annotation import Annotation

class TestAnnotation(TestCase):
    def setup(self):
        super(TestAnnotation, self).setup()
        self.ctx = self.app.test_request_context(path='/api')
        self.ctx.push()

        g.user = None

    def teardown(self):
        self.ctx.pop()
        super(TestAnnotation, self).teardown()

    def test_new(self):
        a = Annotation()
        assert_equal('{}', repr(a))

    def test_save_refresh(self):
        a = Annotation(name='bob')
        c = a.es.conn
        a.save(refresh=True)
        assert_true('id' in a)

    def test_save_assert_refresh(self):
        a = Annotation(name='bob')
        a.es = MagicMock()
        a.es.index = 'foo'
        a.save()
        args, kwargs = a.es.conn.index.call_args
        assert_equal(kwargs['refresh'], True)

    def test_save_refresh_disable(self):
        a = Annotation(name='bob')
        a.es = MagicMock()
        a.es.index = 'foo'
        a.save(refresh=False)
        args, kwargs = a.es.conn.index.call_args
        assert_equal(kwargs['refresh'], False)

    def test_fetch(self):
        a = Annotation(foo='bar')
        a.save()
        b = Annotation.fetch(a.id)
        assert_equal(b['foo'], 'bar')

    def test_delete(self):
        ann = Annotation(id=1)
        ann.save()

        newann = Annotation.fetch(1)
        newann.delete()

        noann = Annotation.fetch(1)
        assert noann == None

    def test_basics(self):
        user = "alice"
        ann = Annotation(text="Hello there", user=user)
        ann['ranges'] = []
        ann['ranges'].append({})
        ann['ranges'].append({})
        ann['document'] = {
            'title': 'Annotation for Dummies',
            'link': [
                {'href': 'http://example.com/1234', 'type': 'application/pdf'}
            ]
        }
        ann.save()

        ann = Annotation.fetch(ann.id)
        assert_equal(ann['text'], "Hello there")
        assert_equal(ann['user'], "alice")
        assert_equal(len(ann['ranges']), 2)
        assert_equal(ann['document']['title'], 'Annotation for Dummies')
        assert_equal(ann['document']['link'][0]['href'], 'http://example.com/1234')
        assert_equal(ann['document']['link'][0]['type'], 'application/pdf')

    def test_search(self):
        perms = {'read': ['group:__world__']}
        uri1 = u'http://xyz.com'
        uri2 = u'urn:uuid:xxxxx'
        user1 = u'levin'
        user2 = u'anna'
        anno1 = Annotation(uri=uri1, text=uri1, user=user1, permissions=perms)
        anno2 = Annotation(uri=uri1, text=uri1 + uri1, user=user2, permissions=perms)
        anno3 = Annotation(uri=uri2, text=uri2, user=user1, permissions=perms)
        anno1.save()
        anno2.save()
        anno3.save()

        res = Annotation.search()
        assert_equal(len(res), 3)

        # ordering (most recent first)
        assert_equal(res[0]['text'], uri2)

        res = Annotation.count()
        assert_equal(res, 3)

        res = Annotation.search(limit=1)
        assert_equal(len(res), 1)
        res = Annotation.count(limit=1)
        assert_equal(res, 3)

        res = Annotation.search(uri=uri1)
        assert_equal(len(res), 2)
        assert_equal(res[0]['uri'], uri1)
        assert_equal(res[0]['id'], anno2.id)

        res = Annotation.search(user=user1)
        assert_equal(len(res), 2)
        assert_equal(res[0]['user'], user1)
        assert_equal(res[0]['id'], anno3.id)

        res = Annotation.search(user=user1, uri=uri2)
        assert_equal(len(res), 1)
        assert_equal(res[0]['user'], user1)
        assert_equal(res[0]['id'], anno3.id)

        res = Annotation.count(user=user1, uri=uri2)
        assert_equal(res, 1)

    def test_search_permissions_null(self):
        anno = Annotation(text='Foobar')
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('bob')
        res = Annotation.search()
        assert_equal(len(res), 0)

    def test_search_permissions_simple(self):
        anno = Annotation(text='Foobar',
                          consumer='testconsumer',
                          permissions={'read': ['bob']})
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('alice', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('bob')
        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('bob', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

    def test_search_permissions_world(self):
        anno = Annotation(text='Foobar',
                          consumer='testconsumer',
                          permissions={'read': ['group:__world__']})
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 1)

        g.user = h.MockUser('alice', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

        g.user = h.MockUser('bob')
        res = Annotation.search()
        assert_equal(len(res), 1)

        g.user = h.MockUser('bob', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

    def test_search_permissions_authenticated(self):
        anno = Annotation(text='Foobar',
                          consumer='testconsumer',
                          permissions={'read': ['group:__authenticated__']})
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('alice', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

        g.user = h.MockUser('bob', 'anotherconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)


    def test_search_permissions_consumer(self):
        anno = Annotation(text='Foobar',
                          user='alice',
                          consumer='testconsumer',
                          permissions={'read': ['group:__consumer__']})
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('bob', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

        g.user = h.MockUser('alice', 'anotherconsumer')
        res = Annotation.search()
        assert_equal(len(res), 0)

    def test_search_permissions_owner(self):
        anno = Annotation(text='Foobar',
                          user='alice',
                          consumer='testconsumer')
        anno.save()

        res = Annotation.search()
        assert_equal(len(res), 0)

        g.user = h.MockUser('alice', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 1)

    def test_search_permissions_malicious(self):
        anno = Annotation(text='Foobar',
                          user='alice',
                          consumer='testconsumer',
                          permissions={'read': ['group:__consumer__']})
        anno.save()

        # Any user whose username starts with "group:" must be refused any results
        g.user = h.MockUser('group:anyone', 'testconsumer')
        res = Annotation.search()
        assert_equal(len(res), 0)

    def test_search_permissions_admin(self):
        anno = Annotation(text='Foobar',
                          user='alice',
                          consumer='testconsumer')
        anno.save()

        g.user = h.MockUser('bob', 'testconsumer')
        g.user.is_admin = True

        res = Annotation.search()
        assert_equal(len(res), 1)

    def test_cross_representations(self):

        # create an annotation for an html document which we can
        # scrape some document metadata from, including a link to a pdf

        a1 = Annotation(uri='http://example.com/1234',
                        text='annotation1',
                        user='alice',
                        document = {
                            "link": [
                                {
                                    "href": "http://example.com/1234",
                                    "type": "text/html"
                                },
                                {
                                    "href": "http://example.com/1234.pdf",
                                    "type": "application/pdf"
                                }
                            ]
                        },
                        consumer='testconsumer')
        a1.save()

        # create an annotation for the pdf that lacks document metadata since
        # annotator doesn't currently extract information from pdfs

        a2 = Annotation(uri='http://example.com/1234.pdf',
                        text='annotation2',
                        user='alice',
                        consumer='testconsumer')
        a2.save()

        # now a query for annotations of the pdf should yield both annotations

        g.user = h.MockUser('alice', 'testconsumer')
        res = Annotation.search(uri='http://example.com/1234.pdf')
        assert_equal(len(res), 2)

        # and likewise for annotations of the html
        res = Annotation.search(uri='http://example.com/1234')
        assert_equal(len(res), 2)

########NEW FILE########
__FILENAME__ = test_auth
import datetime
import hashlib
import time

from nose.tools import *
from mock import Mock, patch

from werkzeug import Headers

from annotator import auth

class MockRequest():
    def __init__(self, headers):
        self.headers = headers

class MockConsumer(Mock):
    key    = 'Consumer'
    secret = 'ConsumerSecret'
    ttl    = 300

def make_request(consumer, obj=None):
    obj = obj or {}
    obj.update({'consumerKey': consumer.key})
    return MockRequest(Headers([
        ('x-annotator-auth-token', auth.encode_token(obj, consumer.secret))
    ]))

class TestAuthBasics(object):
    def setup(self):
        self.now = auth._now()

        self.time_patcher = patch('annotator.auth._now')
        self.time = self.time_patcher.start()
        self.time.return_value = self.now

    def time_travel(self, **kwargs):
        self.time.return_value = self.now + datetime.timedelta(**kwargs)

    def teardown(self):
        self.time_patcher.stop()

    def test_decode_token(self):
        tok = auth.encode_token({}, 'secret')
        assert auth.decode_token(tok, 'secret'), "token should have been successfully decoded"

    def test_decode_token_unicode(self):
        tok = auth.encode_token({}, 'secret')
        assert auth.decode_token(unicode(tok), 'secret'), "token should have been successfully decoded"

    def test_reject_inauthentic_token(self):
        tok = auth.encode_token({'userId': 'alice'}, 'secret')
        tok += 'extrajunk'
        assert_raises(auth.TokenInvalid, auth.decode_token, tok, 'secret')

    def test_reject_notyetvalid_token(self):
        tok = auth.encode_token({}, 'secret')
        self.time_travel(minutes=-1)
        assert_raises(auth.TokenInvalid, auth.decode_token, tok, 'secret')

    def test_reject_expired_token(self):
        tok = auth.encode_token({}, 'secret')
        self.time_travel(seconds=310)
        assert_raises(auth.TokenInvalid, auth.decode_token, tok, 'secret', ttl=300)

class TestAuthenticator(object):
    def setup(self):
        self.consumer = MockConsumer()
        fetcher = lambda x: self.consumer
        self.auth = auth.Authenticator(fetcher)

    def test_request_user(self):
        request = make_request(self.consumer)
        user = self.auth.request_user(request)
        assert_equal(user, None) # No userId supplied

    def test_request_user_user(self):
        request = make_request(self.consumer, {'userId': 'alice'})
        user = self.auth.request_user(request)
        assert_equal(user.consumer.key, 'Consumer')
        assert_equal(user.id, 'alice')

    def test_request_user_missing(self):
        request = make_request(self.consumer)
        del request.headers['x-annotator-auth-token']
        assert_equal(self.auth.request_user(request), None)

    def test_request_user_junk_token(self):
        request = MockRequest(Headers([
            ('x-annotator-auth-token', 'foo.bar.baz')
        ]))
        assert_equal(self.auth.request_user(request), None)

    def test_request_user_invalid(self):
        request = make_request(self.consumer)
        request.headers['x-annotator-auth-token'] += 'LookMaIAmAHacker'
        assert_equal(self.auth.request_user(request), None)

########NEW FILE########
__FILENAME__ = test_authz
from . import helpers as h
from annotator.authz import authorize

class TestAuthorization(object):

    def test_authorize_empty(self):
        # An annotation with no permissions field is private
        ann = {}
        assert not authorize(ann, 'read')
        assert not authorize(ann, 'read', h.MockUser('bob'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))

    def test_authorize_null_consumer(self):
        # An annotation with no consumer set is private
        ann = {'permissions': {'read': ['bob']}}
        assert not authorize(ann, 'read')
        assert not authorize(ann, 'read', h.MockUser('bob'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))

    def test_authorize_basic(self):
        # Annotation with consumer and permissions fields is actionable as
        # per the permissions spec
        ann = {
            'consumer': 'consumerkey',
            'permissions': {'read': ['bob']}
        }

        assert not authorize(ann, 'read')
        assert not authorize(ann, 'read', h.MockUser('bob'))
        assert authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))
        assert not authorize(ann, 'read', h.MockUser('alice', 'consumerkey'))

        assert not authorize(ann, 'update')
        assert not authorize(ann, 'update', h.MockUser('bob', 'consumerkey'))

    def test_authorize_world(self):
        # Annotation (even without consumer key) is actionable if the action
        # list includes the special string 'group:__world__'
        ann = {
            'permissions': {'read': ['group:__world__']}
        }
        assert authorize(ann, 'read')
        assert authorize(ann, 'read', h.MockUser('bob'))
        assert authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))

    def test_authorize_authenticated(self):
        # Annotation (even without consumer key) is actionable if the action
        # list includes the special string 'group:__authenticated__' and the user
        # is authenticated (i.e. a user and consumer tuple is provided)
        ann = {
            'permissions': {'read': ['group:__authenticated__']}
        }
        assert not authorize(ann, 'read')
        assert authorize(ann, 'read', h.MockUser('bob'))

    def test_authorize_consumer(self):
        # Annotation (WITH consumer key) is actionable if the action
        # list includes the special string 'group:__consumer__' and the user
        # is authenticated to the same consumer as that of the annotation
        ann = {
            'permissions': {'read': ['group:__consumer__']}
        }
        assert not authorize(ann, 'read')
        assert not authorize(ann, 'read', h.MockUser('bob'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))
        ann = {
            'consumer': 'consumerkey',
            'permissions': {'read': ['group:__consumer__']}
        }
        assert not authorize(ann, 'read')
        assert not authorize(ann, 'read', h.MockUser('bob'))
        assert authorize(ann, 'read', h.MockUser('alice', 'consumerkey'))
        assert authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'adifferentconsumerkey'))
        assert not authorize(ann, 'read', h.MockUser('group:__consumer__', 'consumerkey'))
        assert not authorize(ann, 'read', h.MockUser('group:__consumer__', 'adifferentconsumerkey'))

    def test_authorize_owner(self):
        # The annotation-owning user can do anything ('user' is a string)
        ann = {
            'consumer': 'consumerkey',
            'user': 'bob',
            'permissions': {'read': ['alice', 'charlie']}
        }
        assert authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'adifferentconsumer'))
        assert not authorize(ann, 'read', h.MockUser('sally', 'consumerkey'))

    def test_authorize_read_annotation_user_dict(self):
        # The annotation-owning user can do anything ('user' is an object)
        ann = {
            'consumer': 'consumerkey',
            'user': {'id': 'bob'},
            'permissions': {'read': ['alice', 'charlie']}
        }
        assert authorize(ann, 'read', h.MockUser('bob', 'consumerkey'))
        assert not authorize(ann, 'read', h.MockUser('bob', 'adifferentconsumer'))
        assert not authorize(ann, 'read', h.MockUser('sally', 'consumerkey'))

    def test_authorize_admin(self):
        # An admin user can do anything
        ann = {
            'consumer': 'consumerkey',
            'user': 'bob'
        }
        admin = h.MockUser('walter', 'consumerkey')
        admin.is_admin = True
        assert authorize(ann, 'read', admin)
        assert authorize(ann, 'update', admin)
        assert authorize(ann, 'admin', admin)

########NEW FILE########
__FILENAME__ = test_document
from flask import g
from nose.tools import *

from . import TestCase
from annotator.document import Document

class TestDocument(TestCase):

    def setup(self):
        super(TestDocument, self).setup()
        self.ctx = self.app.test_request_context(path='/api')
        self.ctx.push()
        g.user = None

    def teardown(self):
        self.ctx.pop()
        super(TestDocument, self).teardown()

    def test_new(self):
        d = Document()
        assert_equal('{}', repr(d))

    def test_basics(self):
        d = Document({
            "id": "1",
            "title": "Annotations: The Missing Manual",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                }
            ],
        })
        d.save()
        d = Document.fetch("1")
        assert_equal(d["title"], "Annotations: The Missing Manual")
        assert_equal(len(d['link']), 2)
        assert_equal(d['link'][0]['href'], "https://peerj.com/articles/53/")
        assert_equal(d['link'][0]['type'], "text/html")
        assert_equal(d['link'][1]['href'], "https://peerj.com/articles/53.pdf")
        assert_equal(d['link'][1]['type'], "application/pdf")
        assert d['created']
        assert d['updated']

    def test_delete(self):
        ann = Document(id=1)
        ann.save()

        newdoc = Document.fetch(1)
        newdoc.delete()

        nodoc = Document.fetch(1)
        assert nodoc == None

    def test_search(self):
        d = Document({
            "id": "1",
            "title": "document",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                }
            ],
        })
        d.save()
        res = Document.search(title='document')
        assert_equal(len(res), 1)

    def test_get_by_uri(self):

        # create 3 documents and make sure get_by_uri works properly

        d = Document({
            "id": "1",
            "title": "document1",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                },
            ],
        })
        d.save()

        d = Document({
            "id": "2",
            "title": "document2",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                },
            ],
        })
        d.save()

        d = Document({
            "id": "3",
            "title": "document3",
            "link": [
                {
                    "href": "http://nature.com/123/",
                    "type": "text/html"
                }
            ],
        })
        d.save()

        doc = Document.get_by_uri("https://peerj.com/articles/53/")
        assert doc
        assert_equal(doc['title'], "document1") 

    def test_get_all_by_uri(self):
        # add two documents and make sure we can search for both

        d = Document({
            "id": "1",
            "title": "document1",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
            ]
        })
        d.save()

        d = Document({
            "id": "2",
            "title": "document2",
            "link": [
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                }
            ]
        })
        d.save()

        docs = Document.get_all_by_uris(["https://peerj.com/articles/53/", "https://peerj.com/articles/53.pdf"])
        assert_equal(len(docs), 2)

    def test_uris(self):
        d = Document({
            "id": "1",
            "title": "document",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                }
            ],
        })
        assert_equal(d.uris(), [
            "https://peerj.com/articles/53/",
            "https://peerj.com/articles/53.pdf"
        ])

    def test_merge_links(self):
        d = Document({
            "id": "1",
            "title": "document",
            "link": [
                {
                    "href": "https://peerj.com/articles/53/",
                    "type": "text/html"
                },
                {
                    "href": "https://peerj.com/articles/53.pdf",
                    "type": "application/pdf"
                }
            ],
        })
        d.save()

        d = Document.fetch(1)
        assert d
        assert_equal(len(d['link']), 2)

        d.merge_links([
            {
                "href": "https://peerj.com/articles/53/",
                "type": "text/html"
            },
            {
                "href": "http://peerj.com/articles/53.doc",
                "type": "application/vnd.ms-word.document"
            }
        ])
        d.save()

        assert_equal(len(d['link']), 3)
        d = Document.fetch(1)
        assert d
        assert_equal(len(d['link']), 3)

        doc = Document.get_by_uri("https://peerj.com/articles/53/")
        assert doc
        assert_equal(len(doc['link']), 3)



########NEW FILE########
__FILENAME__ = test_elasticsearch
from nose.tools import *
from mock import MagicMock, patch
from flask import Flask

import elasticsearch

from annotator.elasticsearch import ElasticSearch, _Model

class TestElasticSearch(object):

    def test_noapp_error(self):
        es = ElasticSearch()
        assert_raises(RuntimeError, lambda: es.conn)

    def test_conn(self):
        app = Flask('testy')
        app.config['ELASTICSEARCH_HOST'] = 'http://127.0.1.1:9202'
        app.config['ELASTICSEARCH_INDEX'] = 'foobar'
        es = ElasticSearch(app)
        with app.app_context():
            assert_true(isinstance(es.conn, elasticsearch.Elasticsearch))

    def test_auth(self):
        app = Flask('testy')
        app.config['ELASTICSEARCH_HOST'] = 'http://foo:bar@127.0.1.1:9202'
        app.config['ELASTICSEARCH_INDEX'] = 'foobar'
        es = ElasticSearch(app)
        with app.app_context():
            assert_equal(('foo', 'bar'),
                         es.conn.transport.hosts[0]['http_auth'])

    def test_index(self):
        app = Flask('testy')
        app.config['ELASTICSEARCH_INDEX'] = 'foobar'
        es = ElasticSearch(app)
        with app.app_context():
            assert_equal(es.index, 'foobar')

class TestModel(object):
    def setup(self):
        app = Flask('testy')
        app.config['ELASTICSEARCH_HOST'] = 'http://127.0.1.1:9202'
        app.config['ELASTICSEARCH_INDEX'] = 'foobar'
        self.es = ElasticSearch(app)

        class MyModel(self.es.Model):
            __type__ = 'footype'

        self.Model = MyModel

        self.ctx = app.app_context()
        self.ctx.push()

    def teardown(self):
        self.ctx.pop()

    @patch('annotator.elasticsearch.elasticsearch.Elasticsearch')
    def test_fetch(self, es_mock):
        conn = es_mock.return_value
        conn.get.return_value = {'_source': {'foo': 'bar'}}
        o = self.Model.fetch(123)
        assert_equal(o['foo'], 'bar')
        assert_equal(o['id'], 123)
        assert_true(isinstance(o, self.Model))

    @patch('annotator.elasticsearch.elasticsearch.Elasticsearch')
    def test_fetch_not_found(self, es_mock):
        conn = es_mock.return_value
        def raise_exc(*args, **kwargs):
            raise elasticsearch.exceptions.NotFoundError('foo')
        conn.get.side_effect = raise_exc
        o = self.Model.fetch(123)
        assert_equal(o, None)

########NEW FILE########
__FILENAME__ = test_store
from . import TestCase
from .helpers import MockUser
from nose.tools import *
from mock import patch

from flask import json, g

from annotator import auth, es
from annotator.annotation import Annotation


class TestStore(TestCase):
    def setup(self):
        super(TestStore, self).setup()

        self.user = MockUser()

        payload = {'consumerKey': self.user.consumer.key, 'userId': self.user.id}
        token = auth.encode_token(payload, self.user.consumer.secret)
        self.headers = {'x-annotator-auth-token': token}

        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def teardown(self):
        self.ctx.pop()
        super(TestStore, self).teardown()

    def _create_annotation(self, refresh=True, **kwargs):
        opts = {
            'user': self.user.id,
            'consumer': self.user.consumer.key
        }
        opts.update(kwargs)
        ann = Annotation(**opts)
        ann.save(refresh=refresh)
        return ann

    def _get_annotation(self, id_):
        return Annotation.fetch(id_)

    def test_cors_preflight(self):
        response = self.cli.open('/api/annotations', method="OPTIONS")

        headers = dict(response.headers)

        assert headers['Access-Control-Allow-Methods'] == 'GET, POST, PUT, DELETE, OPTIONS', \
            "Did not send the right Access-Control-Allow-Methods header."

        assert headers['Access-Control-Allow-Origin'] == '*', \
            "Did not send the right Access-Control-Allow-Origin header."

        assert headers['Access-Control-Expose-Headers'] == 'Content-Length, Content-Type, Location', \
            "Did not send the right Access-Control-Expose-Headers header."

    @patch('annotator.store.Annotation')
    def test_pluggable_class(self, ann_mock):
        g.annotation_class = ann_mock
        response = self.cli.get('/api/annotations/testID', headers=self.headers)
        ann_mock.return_value.fetch.assert_called_once()

    def test_index(self):
        response = self.cli.get('/api/annotations', headers=self.headers)
        assert response.data == "[]", "response should be empty list"

    def test_create(self):
        payload = json.dumps({'name': 'Foo'})

        response = self.cli.post('/api/annotations',
                                 data=payload,
                                 content_type='application/json',
                                 headers=self.headers)

        # import re
        # See http://bit.ly/gxJBHo for details of this change.
        # assert response.status_code == 303, "response should be 303 SEE OTHER"
        # assert re.match(r"http://localhost/store/\d+", response.headers['Location']), "response should redirect to read_annotation url"

        assert response.status_code == 200, "response should be 200 OK"
        data = json.loads(response.data)
        assert 'id' in data, "annotation id should be returned in response"
        assert data['user'] == self.user.id
        assert data['consumer'] == self.user.consumer.key

    def test_create_ignore_created(self):
        payload = json.dumps({'created': 'abc'})

        response = self.cli.post('/api/annotations',
                                 data=payload,
                                 content_type='application/json',
                                 headers=self.headers)

        data = json.loads(response.data)
        ann = self._get_annotation(data['id'])

        assert ann['created'] != 'abc', "annotation 'created' field should not be used by API"

    def test_create_ignore_updated(self):
        payload = json.dumps({'updated': 'abc'})

        response = self.cli.post('/api/annotations',
                                 data=payload,
                                 content_type='application/json',
                                 headers=self.headers)

        data = json.loads(response.data)
        ann = self._get_annotation(data['id'])

        assert ann['updated'] != 'abc', "annotation 'updated' field should not be used by API"

    def test_create_ignore_auth_in_payload(self):
        payload = json.dumps({'user': 'jenny', 'consumer': 'myconsumer'})

        response = self.cli.post('/api/annotations',
                                 data=payload,
                                 content_type='application/json',
                                 headers=self.headers)

        data = json.loads(response.data)
        ann = self._get_annotation(data['id'])

        assert ann['user'] == self.user.id, "annotation 'user' field should not be futzable by API"
        assert ann['consumer'] == self.user.consumer.key, "annotation 'consumer' field should not be used by API"

    @patch('annotator.store.json')
    @patch('annotator.store.Annotation')
    def test_create_refresh(self, ann_mock, json_mock):
        json_mock.dumps.return_value = "{}"
        response = self.cli.post('/api/annotations?refresh=true',
                                 data="{}",
                                 content_type='application/json',
                                 headers=self.headers)
        ann_mock.return_value.save.assert_called_once_with(refresh=True)

    @patch('annotator.store.json')
    @patch('annotator.store.Annotation')
    def test_create_disable_refresh(self, ann_mock, json_mock):
        json_mock.dumps.return_value = "{}"
        response = self.cli.post('/api/annotations?refresh=false',
                                 data="{}",
                                 content_type='application/json',
                                 headers=self.headers)
        ann_mock.return_value.save.assert_called_once_with(refresh=False)

    def test_read(self):
        kwargs = dict(text=u"Foo", id='123')
        self._create_annotation(**kwargs)
        response = self.cli.get('/api/annotations/123', headers=self.headers)
        data = json.loads(response.data)
        assert data['id'] == '123', "annotation id should be returned in response"
        assert data['text'] == "Foo", "annotation text should be returned in response"

    def test_read_notfound(self):
        response = self.cli.get('/api/annotations/123', headers=self.headers)
        assert response.status_code == 404, "response should be 404 NOT FOUND"

    def test_update(self):
        self._create_annotation(text=u"Foo", id='123', created='2010-12-10')

        payload = json.dumps({'id': '123', 'text': 'Bar'})
        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.headers)

        ann = self._get_annotation('123')
        assert ann['text'] == "Bar", "annotation wasn't updated in db"

        data = json.loads(response.data)
        assert data['text'] == "Bar", "update annotation should be returned in response"

    def test_update_without_payload_id(self):
        self._create_annotation(text=u"Foo", id='123')

        payload = json.dumps({'text': 'Bar'})
        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.headers)

        ann = self._get_annotation('123')
        assert ann['text'] == "Bar", "annotation wasn't updated in db"

    def test_update_with_wrong_payload_id(self):
        self._create_annotation(text=u"Foo", id='123')

        payload = json.dumps({'text': 'Bar', 'id': 'abc'})
        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.headers)

        ann = self._get_annotation('123')
        assert ann['text'] == "Bar", "annotation wasn't updated in db"

    def test_update_notfound(self):
        response = self.cli.put('/api/annotations/123', headers=self.headers)
        assert response.status_code == 404, "response should be 404 NOT FOUND"

    def test_update_ignore_created(self):
        ann = self._create_annotation(text=u"Foo", id='123')

        payload = json.dumps({'created': 'abc'})

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.headers)

        upd = self._get_annotation('123')

        assert upd['created'] == ann['created'], "annotation 'created' field should not be updated by API"

    def test_update_ignore_updated(self):
        ann = self._create_annotation(text=u"Foo", id='123')

        payload = json.dumps({'updated': 'abc'})

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.headers)

        upd = self._get_annotation('123')

        assert upd['created'] != 'abc', "annotation 'updated' field should not be updated by API"

    def test_update_ignore_auth_in_payload(self):
        ann = self._create_annotation(text=u"Foo", id='123')

        payload = json.dumps({'user': 'jenny', 'consumer': 'myconsumer'})

        response = self.cli.put('/api/annotations/123',
                                 data=payload,
                                 content_type='application/json',
                                 headers=self.headers)

        upd = self._get_annotation('123')

        assert_equal(upd['user'], self.user.id, "annotation 'user' field should not be futzable by API")
        assert_equal(upd['consumer'], self.user.consumer.key, "annotation 'consumer' field should not be futzable by API")


    def test_delete(self):
        kwargs = dict(text=u"Bar", id='456')
        ann = self._create_annotation(**kwargs)

        response = self.cli.delete('/api/annotations/456', headers=self.headers)
        assert response.status_code == 204, "response should be 204 NO CONTENT"

        assert self._get_annotation('456') == None, "annotation wasn't deleted in db"

    def test_delete_notfound(self):
        response = self.cli.delete('/api/annotations/123', headers=self.headers)
        assert response.status_code == 404, "response should be 404 NOT FOUND"

    def test_search(self):
        uri1 = u'http://xyz.com'
        uri2 = u'urn:uuid:xxxxx'
        user = u'levin'
        user2 = u'anna'
        anno = self._create_annotation(uri=uri1, text=uri1, user=user)
        anno2 = self._create_annotation(uri=uri1, text=uri1 + uri1, user=user2)
        anno3 = self._create_annotation(uri=uri2, text=uri2, user=user)

        res = self._get_search_results()
        assert_equal(res['total'], 3)

        res = self._get_search_results('limit=1')
        assert_equal(res['total'], 3)
        assert_equal(len(res['rows']), 1)

        res = self._get_search_results('uri=' + uri1)
        assert_equal(res['total'], 2)
        assert_equal(len(res['rows']), 2)
        assert_equal(res['rows'][0]['uri'], uri1)
        assert_true(res['rows'][0]['id'] in [anno.id, anno2.id])

    def test_search_limit(self):
        for i in xrange(250):
            self._create_annotation(refresh=False)

        es.conn.indices.refresh(es.index)

        # by default return 20
        res = self._get_search_results()
        assert_equal(len(res['rows']), 20)

        # return maximum 200
        res = self._get_search_results('limit=250')
        assert_equal(len(res['rows']), 200)

        # return minimum 0
        res = self._get_search_results('limit=-10')
        assert_equal(len(res['rows']), 0)

        # ignore bogus values
        res = self._get_search_results('limit=foobar')
        assert_equal(len(res['rows']), 20)

    def test_search_offset(self):
        for i in xrange(250):
            self._create_annotation(refresh=False)

        es.conn.indices.refresh(es.index)

        res = self._get_search_results()
        assert_equal(len(res['rows']), 20)
        first = res['rows'][0]

        res = self._get_search_results('offset=240')
        assert_equal(len(res['rows']), 10)

        # ignore negative values
        res = self._get_search_results('offset=-10')
        assert_equal(len(res['rows']), 20)
        assert_equal(res['rows'][0], first)

        # ignore bogus values
        res = self._get_search_results('offset=foobar')
        assert_equal(len(res['rows']), 20)
        assert_equal(res['rows'][0], first)

    def _get_search_results(self, qs=''):
        res = self.cli.get('/api/search?{qs}'.format(qs=qs), headers=self.headers)
        return json.loads(res.data)


class TestStoreAuthz(TestCase):

    def setup(self):
        super(TestStoreAuthz, self).setup()

        self.user = MockUser() # alice

        self.anno_id = '123'
        self.permissions = {
            'read': [self.user.id, 'bob'],
            'update': [self.user.id, 'charlie'],
            'admin': [self.user.id]
        }

        self.ctx = self.app.test_request_context()
        self.ctx.push()

        ann = Annotation(id=self.anno_id,
                         user=self.user.id,
                         consumer=self.user.consumer.key,
                         text='Foobar',
                         permissions=self.permissions)
        ann.save()

        for u in ['alice', 'bob', 'charlie']:
            token = auth.encode_token({'consumerKey': self.user.consumer.key, 'userId': u}, self.user.consumer.secret)
            setattr(self, '%s_headers' % u, {'x-annotator-auth-token': token})

    def teardown(self):
        self.ctx.pop()
        super(TestStoreAuthz, self).teardown()

    def test_read(self):
        response = self.cli.get('/api/annotations/123')
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"

        response = self.cli.get('/api/annotations/123', headers=self.charlie_headers)
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"

        response = self.cli.get('/api/annotations/123', headers=self.alice_headers)
        assert response.status_code == 200, "response should be 200 OK"
        data = json.loads(response.data)
        assert data['text'] == 'Foobar'

    def test_update(self):
        payload = json.dumps({'id': self.anno_id, 'text': 'Bar'})

        response = self.cli.put('/api/annotations/123', data=payload, content_type='application/json')
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.bob_headers)
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.charlie_headers)
        assert response.status_code == 200, "response should be 200 OK"

    def test_update_change_permissions_not_allowed(self):
        self.permissions['read'] = ['alice', 'charlie']
        payload = json.dumps({
            'id': self.anno_id,
            'text': 'Bar',
            'permissions': self.permissions
        })

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json')
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.charlie_headers)
        assert response.status_code == 401, "response should be 401 NOT AUTHORIZED"
        assert 'permissions update' in response.data

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.alice_headers)
        assert response.status_code == 200, "response should be 200 OK"

    def test_update_other_users_annotation(self):
        ann = Annotation(id=123,
                         user='foo',
                         consumer=self.user.consumer.key,
                         permissions={'update': ['group:__consumer__']})
        ann.save()

        payload = json.dumps({
            'id': 123,
            'text': 'Foo'
        })

        response = self.cli.put('/api/annotations/123',
                                data=payload,
                                content_type='application/json',
                                headers=self.bob_headers)
        assert response.status_code == 200, "response should be 200 OK"

    def test_search_public(self):
        # Not logged in: no results
        results = self._get_search_results()
        assert results['total'] == 0
        assert results['rows'] == []

    def test_search_authenticated(self):
        # Logged in as Bob: 1 result
        results = self._get_search_results(headers=self.bob_headers)
        assert results['total'] == 1
        assert results['rows'][0]['id'] == self.anno_id

        # Logged in as Charlie: 0 results
        results = self._get_search_results(headers=self.charlie_headers)
        assert results['total'] == 0
        assert results['rows'] == []

    def test_search_raw_public(self):
        # Not logged in: no results
        results = self._get_search_raw_results()
        assert results['hits']['total'] == 0
        assert results['hits']['hits'] == []

    def test_search_raw_authorized(self):
        # Logged in as Bob: 1 result
        results = self._get_search_raw_results(headers=self.bob_headers)
        assert results['hits']['total'] == 1
        assert results['hits']['hits'][0]['_source']['id'] == self.anno_id

        # Logged in as Charlie: 0 results
        results = self._get_search_raw_results(headers=self.charlie_headers)
        assert results['hits']['total'] == 0
        assert results['hits']['hits'] == []

    def _get_search_results(self, qs='', **kwargs):
        res = self.cli.get('/api/search?{qs}'.format(qs=qs), **kwargs)
        return json.loads(res.data)

    def _get_search_raw_results(self, qs='', **kwargs):
        res = self.cli.get('/api/search_raw?{qs}'.format(qs=qs), **kwargs)
        return json.loads(res.data)

########NEW FILE########
