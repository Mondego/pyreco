__FILENAME__ = auth
import hashlib
import uuid

from kule import Kule, jsonify, request, response, abort


class KuleWithAuth(Kule):
    """
    Adds authentication endpoints to kule
    """
    def authenticate(self):
        collection = self.connection['users']
        username = request.json.get('username')
        password = request.json.get('password')
        hasher = hashlib.md5()
        hasher.update(password)
        user = collection.find_one({
            'username': username,
            'password': hasher.hexdigest(),
        }) or abort(400, 'Wrong username or password')
        access_token = str(uuid.uuid4())
        self.connection['access_tokens'].insert({
            'access_token': access_token,
            'user_id': user.get('id')})
        user.pop('password')
        user.update({'access_token': access_token})
        return jsonify(user)

    def register(self):
        collection = self.connection['users']
        password = request.json.get('password')
        username = request.json.get('username')
        email = request.json.get('email')
        if not username or not password:
            abort(400, 'Please give an username and password')
        if collection.find_one({'username': username}):
            abort(400, 'A user with that username already exists')
        if collection.find_one({'email': email}):
            abort(400, 'A user with that email already exists')
        hasher = hashlib.md5()
        hasher.update(password)
        response.status = 201
        return jsonify({"_id": collection.insert({
            'username': request.json.get('username'),
            'email': request.json.get('email'),
            'password': hasher.hexdigest()
        })})

    def dispatch_views(self):
        super(KuleWithAuth, self).dispatch_views()
        self.app.route('/sessions', method='post')(self.authenticate)
        self.app.route('/sessions', method='options')(self.empty_response)
        self.app.route('/users', method='post')(self.register)
        self.app.route('/users', method='options')(self.empty_response)

kule = KuleWithAuth

########NEW FILE########
__FILENAME__ = helpers
import json
import datetime

import bson


def int_or_default(value, default=None):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class MongoEncoder(json.JSONEncoder):
    """
    Custom encoder for dumping MongoDB documents
    """
    def default(self, obj):

        if isinstance(obj, bson.ObjectId):
            return str(obj)

        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()

        return super(MongoEncoder, self).default(obj)


jsonify = MongoEncoder().encode

########NEW FILE########
__FILENAME__ = kule
import json
from functools import partial

from bson import ObjectId
from pymongo import Connection

from helpers import int_or_default, jsonify

from bottle import Bottle, route, run, request, response, abort, error


class Kule(object):
    """Wraps bottle app."""

    def __init__(self, database=None, host=None, port=None,
                 collections=None):
        self.connection = self.connect(database, host, port)
        self.collections = collections

    def connect(self, database, host=None, port=None):
        """Connects to the MongoDB"""
        return Connection(host=host, port=port)[database]

    def get_collection(self, collection):
        """Returns the given collection if it permitted"""
        if self.collections and collection not in self.collections:
            abort(403)
        return self.connection[collection]

    def get_detail(self, collection, pk):
        """Returns a single document."""
        cursor = self.get_collection(collection)
        data = cursor.find_one({"_id": ObjectId(pk)}) or abort(404)
        return jsonify(self.get_bundler(cursor)(data))

    def put_detail(self, collection, pk):
        """Updates whole document."""
        collection = self.get_collection(collection)
        if '_id' in request.json:
            # we are ignoring id fields of bundle,
            # because _id field is immutable
            del request.json['_id']
        collection.update({"_id": ObjectId(pk)}, request.json)
        response.status = 202
        return jsonify(request.json)

    def patch_detail(self, collection, pk):
        """Updates specific parts of the document."""
        collection = self.get_collection(collection)
        collection.update({"_id": ObjectId(pk)},
                          {"$set": request.json})
        response.status = 202
        return self.get_detail(collection.name, str(pk))

    def delete_detail(self, collection, pk):
        """Deletes a single document"""
        collection = self.get_collection(collection)
        collection.remove({"_id": ObjectId(pk)})
        response.status = 204

    def post_list(self, collection):
        """Creates new document"""
        collection = self.get_collection(collection)
        inserted = collection.insert(request.json)
        response.status = 201
        return jsonify({"_id": inserted})

    def get_list(self, collection):
        """Returns paginated objects."""
        collection = self.get_collection(collection)
        limit = int_or_default(request.query.limit, 20)
        offset = int_or_default(request.query.offset, 0)
        query = self.get_query()
        cursor = collection.find(query)

        meta = {
            "limit": limit,
            "offset": offset,
            "total_count": cursor.count(),
        }

        objects = cursor.skip(offset).limit(limit)
        objects = map(self.get_bundler(collection), objects)

        return jsonify({"meta": meta,
                        "objects": objects})

    def get_query(self):
        """Loads the given json-encoded query."""
        query = request.GET.get("query")
        return json.loads(query) if query else {}

    def get_bundler(self, collection):
        """Returns a bundler function for collection"""
        method_name = "build_%s_bundle" % collection.name
        return getattr(self, method_name, self.build_bundle)

    def build_bundle(self, data):
        """Dummy bundler"""
        return data

    def empty_response(self, *args, **kwargs):
        """Empty response"""

    # we are returning an empty response for OPTIONS method
    # it's required for enabling CORS.
    options_list = empty_response
    options_detail = empty_response

    def get_error_handler(self):
        """Customized errors"""
        return {
            500: partial(self.error, message="Internal Server Error."),
            404: partial(self.error, message="Document Not Found."),
            501: partial(self.error, message="Not Implemented."),
            405: partial(self.error, message="Method Not Allowed."),
            403: partial(self.error, message="Forbidden."),
            400: self.error,
        }

    def dispatch_views(self):
        """Routes bottle app. Also determines the magical views."""
        for method in ("get", "post", "put", "patch", "delete", "options"):
            self.app.route('/:collection', method=method)(
                getattr(self, "%s_list" % method, self.not_implemented))
            self.app.route('/:collection/:pk', method=method)(
                getattr(self, "%s_detail" % method, self.not_implemented))

            # magical views
            for collection in self.collections or []:
                list_view = getattr(self, "%s_%s_list" % (
                    method, collection), None)
                detail_view = getattr(self, "%s_%s_detail" % (
                    method, collection), None)
                if list_view:
                    self.app.route('/%s' % collection, method=method)(
                        list_view)
                if detail_view:
                    self.app.route('/%s/:id' % collection, method=method)(
                        detail_view)

    def after_request(self):
        """A bottle hook for json responses."""
        response["content_type"] = "application/json"
        methods = 'PUT, PATCH, GET, POST, DELETE, OPTIONS'
        headers = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = methods
        response.headers['Access-Control-Allow-Headers'] = headers

    def get_bottle_app(self):
        """Returns bottle instance"""
        self.app = Bottle()
        self.dispatch_views()
        self.app.hook('after_request')(self.after_request)
        self.app.error_handler = self.get_error_handler()
        return self.app

    def not_implemented(self, *args, **kwargs):
        """Returns not implemented status."""
        abort(501)

    def error(self, error, message=None):
        """Returns the error response."""
        return jsonify({"error": error.status_code,
                        "message": error.body or message})

    def run(self, *args, **kwargs):
        """Shortcut method for running kule"""
        kwargs.setdefault("app", self.get_bottle_app())
        run(*args, **kwargs)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--bind", dest="address",
                      help="Binds an address to kule")
    parser.add_option("--mongodb-host", dest="mongodb_host",
                      help="MongoDB host")
    parser.add_option("--mongodb-port", dest="mongodb_port",
                      help="MongoDB port")
    parser.add_option("-d", "--database", dest="database",
                      help="MongoDB database name")
    parser.add_option("-c", "--collections", dest="collections",
                      help="Comma-separated collections.")
    parser.add_option("-k", "--klass", dest="klass",
                      help="Kule class")
    options, args = parser.parse_args()
    collections = (options.collections or "").split(",")
    database = options.database
    if not database:
        parser.error("MongoDB database not given.")
    host, port = (options.address or 'localhost'), 8000
    if ':' in host:
        host, port = host.rsplit(':', 1)

    try:
        klass = __import__(options.klass, fromlist=['kule']).kule
    except AttributeError:
        raise ImportError('Bad kule module.')
    except TypeError:
        klass = Kule

    kule = klass(
        host=options.mongodb_host,
        port=options.mongodb_port,
        database=options.database,
        collections=collections
    )
    run(host=host, port=port, app=kule.get_bottle_app())

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = __main__
from kule import main
main()
########NEW FILE########
__FILENAME__ = tests
import unittest
import operator
import json
import bson

from webtest import TestApp

from kule import Kule

first = operator.itemgetter(0)


class KuleTests(unittest.TestCase):
    """
    Functionality tests for kule.
    """
    def setUp(self):
        self.kule = Kule(database="kule_test",
                         collections=["documents"])
        self.app = TestApp(self.kule.get_bottle_app())
        self.collection = self.kule.get_collection("documents")

    def tearDown(self):
        self.collection.remove()

    def test_empty_response(self):
        response = self.app.get("/documents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json,
                         {'meta': {
                             'total_count': 0,
                             'limit': 20,
                             'offset': 0},
                          'objects': []})

    def test_get_list(self):
        self.collection.insert({"foo": "bar"})
        response = self.app.get("/documents")
        self.assertEqual(response.status_code, 200)
        objects = response.json.get("objects")
        meta = response.json.get("meta")
        self.assertEqual(1, len(objects))
        self.assertEqual(1, meta.get("total_count"))
        record = first(objects)
        self.assertEqual(record.get("foo"), "bar")

    def test_post_list(self):
        response = self.app.post("/documents", json.dumps({"foo": "bar"}),
                                 content_type="application/json")
        self.assertEqual(201, response.status_code)
        object_id = response.json.get("_id")
        query = {"_id": bson.ObjectId(object_id)}
        self.assertEqual(1, self.collection.find(query).count())
        record = self.collection.find_one(query)
        self.assertEqual(record.get("foo"), "bar")

    def test_get_detail(self):
        object_id = str(self.collection.insert({"foo": "bar"}))
        response = self.app.get("/documents/%s" % object_id)
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json, {'_id': object_id,
                                         'foo': 'bar'})

    def test_put_detail(self):
        object_id = self.collection.insert({"foo": "bar"})
        response = self.app.put("/documents/%s" % object_id,
                                json.dumps({"bar": "foo"}),
                                content_type="application/json")
        self.assertEqual(response.status_code, 202)
        record = self.collection.find_one({"_id": object_id})
        self.assertEqual(record, {'_id': object_id,
                                  'bar': 'foo'})

    def test_patch_detail(self):
        object_id = self.collection.insert({"foo": "bar"})
        response = self.app.patch("/documents/%s" % object_id,
                                  json.dumps({"bar": "foo"}),
                                  content_type="application/json")
        self.assertEqual(response.status_code, 202)
        record = self.collection.find_one({"_id": object_id})
        self.assertEqual(record, {'_id': object_id,
                                  'foo': 'bar',
                                  'bar': 'foo'})

    def test_delete_detail(self):
        object_id = self.collection.insert({"foo": "bar"})
        response = self.app.delete("/documents/%s" % object_id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, self.collection.find(
            {"_id": object_id}).count())

    def test_magical_methods(self):
        class MyKule(Kule):
            def get_documents_list(self):
                return {"foo": "bar"}
        kule = MyKule(database="kule_test", collections=["documents"])
        app = TestApp(kule.get_bottle_app())
        self.assertEqual(app.get("/documents").json, {"foo": "bar"})

    def test_bundler(self):
        class MyKule(Kule):
            def build_documents_bundle(self, document):
                return {"_title": document.get("title")}
        kule = MyKule(database="kule_test", collections=["documents"])
        app = TestApp(kule.get_bottle_app())
        object_id = kule.get_collection("documents").insert({"title": "bar"})
        result = app.get("/documents/%s" % object_id).json
        self.assertEqual(result ,{"_title": "bar"})


unittest.main()

########NEW FILE########
