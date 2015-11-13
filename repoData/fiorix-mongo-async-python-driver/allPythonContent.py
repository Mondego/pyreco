__FILENAME__ = aggregate
#!/usr/bin/env python
# coding: utf-8

import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    yield test.insert({"src":"Twitter", "content":"bla bla"}, safe=True)
    yield test.insert({"src":"Twitter", "content":"more data"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"blog article 1"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"blog article 2"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"some comments"}, safe=True)

    # Read more about the aggregation pipeline in MongoDB's docs
    pipeline = [
        {'$group': {'_id':'$src', 'content_list': {'$push': '$content'} } }
    ]
    result = yield test.aggregate(pipeline)

    print "result:", result

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = insert-concise
#!/usr/bin/env python
# coding: utf-8
import sys
import time

from twisted.internet import reactor
from twisted.python import log

import txmongo


def insertData(conn):
    print "inserting data..."
    collection = conn.foo.test
    for x in xrange(10000):
        d = collection.insert({"something":x*time.time()}, safe=True)
        d.addErrback(log.err)
    return d


def processResult(result):
    print "processing last insert ..."
    print "last inserted id: %s" % result


def finish(ignore):
    print "finishing up..."
    reactor.stop()


def example():
    d = txmongo.MongoConnectionPool()
    d.addCallback(insertData)
    d.addCallback(processResult)
    d.addErrback(log.err)
    d.addCallback(finish)
    return d


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    example()
    reactor.run()

########NEW FILE########
__FILENAME__ = insert
#!/usr/bin/env python
# coding: utf-8
import sys
import time

from twisted.internet import defer, reactor
from twisted.python import log

import txmongo


def getConnection():
    print "getting connection..."
    return txmongo.MongoConnectionPool()


def getDatabase(conn, dbName):
    print "getting database..."
    return getattr(conn, dbName)


def getCollection(db, collName):
    print "getting collection..."
    return getattr(db, collName)


def insertData(coll):
    print "inserting data..."
    # insert some data, building a deferred list so that we can later check
    # the succes or failure of each deferred result
    deferreds = []
    for x in xrange(10000):
        d = coll.insert({"something":x*time.time()}, safe=True)
        deferreds.append(d)
    return defer.DeferredList(deferreds)


def processResults(results):
    print "processing results..."
    failures = 0
    successes = 0
    for success, result in results:
        if success:
            successes += 1
        else:
            failures += 1
    print "There were %s successful inserts and %s failed inserts." % (
        successes, failures)


def finish(ignore):
    print "finishing up..."
    reactor.stop()


def example():
    d = getConnection()
    d.addErrback(log.err)
    d.addCallback(getDatabase, "foo")
    d.addCallback(getCollection, "test")
    d.addCallback(insertData)
    d.addErrback(log.err)
    d.addCallback(processResults)
    d.addErrback(log.err)
    d.addCallback(finish)
    return d


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    example()
    reactor.run()


########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python
# coding: utf-8
import sys
import time

from twisted.internet import reactor
from twisted.python import log

import txmongo


def updateData(ignored, conn):
    print "updating data..."
    collection = conn.foo.test
    d = collection.update(
        {"foo": "bar"}, {"$set": {"name": "jane doe"}}, safe=True)
    d.addErrback(log.err)
    return d


def insertData(conn):
    print "inserting data..."
    collection = conn.foo.test
    d = collection.insert({"foo": "bar", "name": "john doe"}, safe=True)
    d.addErrback(log.err)
    d.addCallback(updateData, conn)
    return d


def finish(ignore):
    print "finishing up..."
    reactor.stop()


def example():
    d = txmongo.MongoConnection()
    d.addCallback(insertData)
    d.addCallback(finish)
    return d


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    example()
    reactor.run()

########NEW FILE########
__FILENAME__ = dbref
#!/usr/bin/env python
# coding: utf-8

import txmongo
from txmongo.dbref import DBRef
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    doc_a = {"username":"foo", "password":"bar"}
    result = yield test.insert(doc_a, safe=True)

    doc_b = {"settings":"foobar", "owner":DBRef(test, result)}
    yield test.insert(doc_b, safe=True)

    doc = yield test.find_one({"settings":"foobar"})
    print "doc is:", doc

    if isinstance(doc["owner"], DBRef):
        ref = doc["owner"]
        owner = yield foo[ref.collection].find_one(ref.id)
        print "owner:", owner

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = drop
#!/usr/bin/env python
# coding: utf-8

import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    result = yield test.drop(safe=True)
    print result

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = group
#!/usr/bin/env python
# coding: utf-8

import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    yield test.insert({"src":"Twitter", "content":"bla bla"}, safe=True)
    yield test.insert({"src":"Twitter", "content":"more data"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"blog article 1"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"blog article 2"}, safe=True)
    yield test.insert({"src":"Wordpress", "content":"some comments"}, safe=True)

    result = yield test.group(keys=["src"],
        initial={"count":0}, reduce="function(obj,prev){prev.count++;}")

    print "result:", result

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python
# coding: utf-8

import txmongo
from txmongo import filter
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    idx = filter.sort(filter.ASCENDING("something") + filter.DESCENDING("else"))
    print "IDX:", idx

    result = yield test.create_index(idx)
    print "create_index:", result

    result = yield test.index_information()
    print "index_information:", result

    result = yield test.drop_index(idx)
    print "drop_index:", result

    # Geohaystack example
    geoh_idx = filter.sort(filter.GEOHAYSTACK("loc") + filter.ASCENDING("type"))
    print "IDX:", geoh_idx
    result = yield test.create_index(geoh_idx, **{'bucketSize':1})
    print "index_information:", result
    
    result = yield test.drop_index(geoh_idx)
    print "drop_index:", result

    # 2D geospatial index
    geo_idx = filter.sort(filter.GEO2D("pos"))
    print "IDX:", geo_idx
    result = yield test.create_index(geo_idx, **{ 'min':-100, 'max':100 })
    print "index_information:", result

    result = yield test.drop_index(geo_idx)
    print "drop_index:", result


if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = insert
#!/usr/bin/env python
# coding: utf-8

import time
import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    # insert some data
    for x in xrange(10000):
        result = yield test.insert({"something":x*time.time()}, safe=True)
        print result

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = query
#!/usr/bin/env python
# coding: utf-8

import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    # fetch some documents
    docs = yield test.find(limit=10)
    for doc in docs:
        print doc

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = query_fields
#!/usr/bin/env python
# coding: utf-8

import txmongo
import txmongo.filter
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo # `foo` database
    test = foo.test # `test` collection

    # specify the fields to be returned by the query
    # reference: http://www.mongodb.org/display/DOCS/Retrieving+a+Subset+of+Fields
    whitelist = {'_id': 1, 'name': 1}
    blacklist = {'_id': 0}
    quickwhite = ['_id', 'name']

    fields = blacklist

    # fetch some documents
    docs = yield test.find(limit=10, fields=fields)
    for n, doc in enumerate(docs):
        print n, doc

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = query_filter
#!/usr/bin/env python
# coding: utf-8

import txmongo
import txmongo.filter
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    # create the filter
    f = txmongo.filter.sort(txmongo.filter.DESCENDING("something"))
    #f += txmongo.filter.hint(txmongo.filter.DESCENDING("myindex"))
    #f += txmongo.filter.explain()

    # fetch some documents
    docs = yield test.find(limit=10, filter=f)
    for n, doc in enumerate(docs):
        print n, doc

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python
# coding: utf-8

import txmongo
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def example():
    mongo = yield txmongo.MongoConnection()

    foo = mongo.foo  # `foo` database
    test = foo.test  # `test` collection

    # insert
    yield test.insert({"foo":"bar", "name":"bla"}, safe=True)

    # update
    result = yield test.update({"foo":"bar"}, {"$set": {"name":"john doe"}}, safe=True)
    print "result:", result

if __name__ == '__main__':
    example().addCallback(lambda ign: reactor.stop())
    reactor.run()

########NEW FILE########
__FILENAME__ = test_xmlrpc
#!/usr/bin/env python
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import xmlrpclib

srv = xmlrpclib.Server("http://localhost:8888/xmlrpc")
print "insert:", srv.insert({"name":"foobar"})
print "update:", srv.update({"name":"foo"}, {"name":"oof"})
print "find:", srv.find({"name":"oof"})

########NEW FILE########
__FILENAME__ = test_aggregate
# coding: utf-8
# Copyright 2010 Tryggvi Bjorgvinsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.internet import defer
from twisted.trial import unittest
import txmongo

mongo_host = "localhost"
mongo_port = 27017


class TestAggregate(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_Aggregate(self):
        yield self.coll.insert([{'oh':'hai', 'lulz':123},
                                {'oh':'kthxbye', 'lulz':456},
                                {'oh':'hai', 'lulz':789},], safe=True)

        res = yield self.coll.aggregate([
                {'$project': {'oh':1, 'lolz':'$lulz'}}, 
                {'$group': {'_id':'$oh', 'many_lolz': {'$sum':'$lolz'}}},
                {'$sort': {'_id':1}}
                ])

        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['_id'], 'hai')
        self.assertEqual(res[0]['many_lolz'], 912)
        self.assertEqual(res[1]['_id'], 'kthxbye')
        self.assertEqual(res[1]['many_lolz'], 456)

        res = yield self.coll.aggregate([
                {'$match': {'oh':'hai'}}
                ], full_response=True)

        self.assertIn('ok', res)
        self.assertIn('result', res)
        self.assertEqual(len(res['result']), 2)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop()
        yield self.conn.disconnect()


########NEW FILE########
__FILENAME__ = test_collection
# -*- coding: utf-8 -*-

# Copyright 2012 Renzo S.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the collection module.
Based on pymongo driver's test_collection.py
"""

from bson.son import SON
from pymongo import errors

from twisted.internet import defer
from twisted.trial import unittest

import txmongo

from txmongo import filter
from txmongo.collection import Collection

mongo_host = "localhost"
mongo_port = 27017


class TestCollection(unittest.TestCase):
    
    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.db = self.conn.mydb
        self.coll = self.db.mycol

    @defer.inlineCallbacks
    def tearDown(self):
        ret = yield self.coll.drop()
        ret = yield self.conn.disconnect()

    @defer.inlineCallbacks
    def test_collection(self):
        self.assertRaises(TypeError, Collection, self.db, 5)

        def make_col(base, name):
            return base[name]

        self.assertRaises(errors.InvalidName, make_col, self.db, "")
        self.assertRaises(errors.InvalidName, make_col, self.db, "te$t")
        self.assertRaises(errors.InvalidName, make_col, self.db, ".test")
        self.assertRaises(errors.InvalidName, make_col, self.db, "test.")
        self.assertRaises(errors.InvalidName, make_col, self.db, "tes..t")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, "")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, "te$t")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, ".test")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, "test.")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, "tes..t")
        self.assertRaises(errors.InvalidName, make_col, self.db.test, "tes\x00t")
        self.assertRaises(TypeError, self.coll.save, 'test')
        self.assertRaises(ValueError, self.coll.filemd5, 'test')
        self.assertFailure(self.db.test.find(spec="test"), TypeError)
        self.assertFailure(self.db.test.find(fields="test"), TypeError)
        self.assertFailure(self.db.test.find(skip="test"), TypeError)
        self.assertFailure(self.db.test.find(limit="test"), TypeError)
        self.assertFailure(self.db.test.insert([1]), TypeError)
        self.assertFailure(self.db.test.insert(1), TypeError)
        self.assertFailure(self.db.test.update(1, 1), TypeError)
        self.assertFailure(self.db.test.update({}, 1), TypeError)
        self.assertFailure(self.db.test.update({}, {}, 'a'), TypeError)

        self.assert_(isinstance(self.db.test, Collection))
        self.assertEqual(-1, cmp(self.db.test, 7))
        self.assertEqual(self.db.test, Collection(self.db, "test"))
        self.assertEqual(self.db.test.mike, self.db["test.mike"])
        self.assertEqual(self.db.test["mike"], self.db["test.mike"])
        self.assertEqual(repr(self.db.test), 'Collection(mydb, test)')
        self.assertEqual(self.db.test.test, self.db.test('test'))

        options = yield self.db.test.options()
        print options
        self.assertIsInstance(options, dict)

        yield self.db.drop_collection('test')
        collection_names = yield self.db.collection_names()
        self.assertFalse('test' in collection_names)

    @defer.inlineCallbacks
    def test_create_index(self):
        db = self.db
        coll = self.coll

        self.assertRaises(TypeError, coll.create_index, 5)
        self.assertRaises(TypeError, coll.create_index, {"hello": 1})

        yield coll.insert({'c': 1}) # make sure collection exists.

        yield coll.drop_indexes()
        count = yield db.system.indexes.count({"ns": u"mydb.mycol"})
        self.assertEqual(count, 1)

        result1 = yield coll.create_index(filter.sort(filter.ASCENDING("hello")))
        result2 = yield coll.create_index(filter.sort(filter.ASCENDING("hello") + \
                                          filter.DESCENDING("world")))

        count = yield db.system.indexes.count({"ns": u"mydb.mycol"}) 
        self.assertEqual(count, 3)

        yield coll.drop_indexes()
        ix = yield coll.create_index(filter.sort(filter.ASCENDING("hello") + \
                                   filter.DESCENDING("world")), name="hello_world")
        self.assertEquals(ix, "hello_world")

        yield coll.drop_indexes()
        count = yield db.system.indexes.count({"ns": u"mydb.mycol"}) 
        self.assertEqual(count, 1)
        
        yield coll.create_index(filter.sort(filter.ASCENDING("hello")))
        indices = yield db.system.indexes.find({"ns": u"mydb.mycol"}) 
        self.assert_(u"hello_1" in [a["name"] for a in indices])

        yield coll.drop_indexes()
        count = yield db.system.indexes.count({"ns": u"mydb.mycol"}) 
        self.assertEqual(count, 1)

        ix = yield coll.create_index(filter.sort(filter.ASCENDING("hello") + \
                                   filter.DESCENDING("world")))
        self.assertEquals(ix, "hello_1_world_-1")
    
    @defer.inlineCallbacks
    def test_create_index_nodup(self):
        coll = self.coll

        ret = yield coll.drop()
        ret = yield coll.insert({'b': 1})
        ret = yield coll.insert({'b': 1})

        ix = coll.create_index(filter.sort(filter.ASCENDING("b")), unique=True)
        yield self.assertFailure(ix, errors.DuplicateKeyError)


    @defer.inlineCallbacks
    def test_ensure_index(self):
        db = self.db
        coll = self.coll
        
        yield coll.ensure_index(filter.sort(filter.ASCENDING("hello")))
        indices = yield db.system.indexes.find({"ns": u"mydb.mycol"}) 
        self.assert_(u"hello_1" in [a["name"] for a in indices])

        yield coll.drop_indexes()

    @defer.inlineCallbacks
    def test_index_info(self):
        db = self.db

        yield db.test.drop_indexes()
        yield db.test.remove({})

        db.test.save({})  # create collection
        ix_info = yield db.test.index_information()
        self.assertEqual(len(ix_info), 1)

        self.assert_("_id_" in ix_info)

        yield db.test.create_index(filter.sort(filter.ASCENDING("hello")))
        ix_info = yield db.test.index_information()
        self.assertEqual(len(ix_info), 2)
        
        self.assertEqual(ix_info["hello_1"], [("hello", 1)])

        yield db.test.create_index(filter.sort(filter.DESCENDING("hello") + filter.ASCENDING("world")), unique=True)
        ix_info = yield db.test.index_information()

        self.assertEqual(ix_info["hello_1"], [("hello", 1)])
        self.assertEqual(len(ix_info), 3)
        self.assertEqual([("world", 1), ("hello", -1)], ix_info["hello_-1_world_1"])
        # Unique key will not show until index_information is updated with changes introduced in version 1.7
        #self.assertEqual(True, ix_info["hello_-1_world_1"]["unique"])

        yield db.test.drop_indexes()
        yield db.test.remove({})
        

    @defer.inlineCallbacks
    def test_index_geo2d(self):
        db = self.db
        coll = self.coll 
        yield coll.drop_indexes()
        geo_ix = yield coll.create_index(filter.sort(filter.GEO2D("loc")))

        self.assertEqual('loc_2d', geo_ix)

        index_info = yield coll.index_information()
        self.assertEqual([('loc', '2d')], index_info['loc_2d'])

    @defer.inlineCallbacks
    def test_index_haystack(self):
        db = self.db
        coll = self.coll
        yield coll.drop_indexes()

        _id = yield coll.insert({
            "pos": {"long": 34.2, "lat": 33.3},
            "type": "restaurant"
        })
        yield coll.insert({
            "pos": {"long": 34.2, "lat": 37.3}, "type": "restaurant"
        })
        yield coll.insert({
            "pos": {"long": 59.1, "lat": 87.2}, "type": "office"
        })

        yield coll.create_index(filter.sort(filter.GEOHAYSTACK("pos") + filter.ASCENDING("type")), **{'bucket_size': 1})

        # TODO: A db.command method has not been implemented yet.
        # Sending command directly
        command = SON([
            ("geoSearch", "mycol"),
            ("near", [33, 33]),
            ("maxDistance", 6),
            ("search", {"type": "restaurant"}),
            ("limit", 30),
        ])
           
        results = yield db["$cmd"].find_one(command)
        self.assertEqual(2, len(results['results']))
        self.assertEqual({
            "_id": _id,
            "pos": {"long": 34.2, "lat": 33.3},
            "type": "restaurant"
        }, results["results"][0])



########NEW FILE########
__FILENAME__ = test_dbref
# -*- coding: utf-8 -*-

# Copyright 2012 Renzo S.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the collection module.
Based on pymongo driver's test_collection.py
"""

from twisted.trial import unittest

from txmongo.dbref import DBRef
from txmongo.collection import Collection
from bson.son import SON
from bson.objectid import ObjectId


class TestDBRef(unittest.TestCase):

    def test_dbref(self):
        self.assertRaises(TypeError, DBRef, 5, "test_id")
        self.assertRaises(TypeError, DBRef, "test", "test_id", 5)
        oid = ObjectId()
        ref = DBRef("testc", oid, "testdb")
        self.assertEqual(ref.collection, "testc")
        self.assertEqual(ref.id, oid)
        self.assertEqual(ref.database, "testdb")
        collection = Collection("testdb", "testcoll")
        ref = DBRef(collection, oid)
        self.assertEqual(ref.collection, "testcoll")
        ref_son = SON([("$ref", "testcoll"), ("$id", oid)])
        self.assertEqual(ref.as_doc(), ref_son)
        self.assertEqual(repr(ref), "DBRef(testcoll, %r)" % oid)

        ref = DBRef(collection, oid, "testdb")
        ref_son = SON([("$ref", "testcoll"), ("$id", oid), ("$db", "testdb")])
        self.assertEqual(ref.as_doc(), ref_son)
        self.assertEqual(repr(ref), "DBRef(testcoll, %r, testdb)" % oid)

        ref1 = DBRef('a', oid)
        ref2 = DBRef('b', oid)

        self.assertEqual(cmp(ref1, ref2), -1)
        self.assertEqual(cmp(ref1, 0), -1)

        ref1 = DBRef('a', oid)
        ref2 = DBRef('a', oid)

        self.assertEqual(hash(ref1), hash(ref2))

########NEW FILE########
__FILENAME__ = test_find_and_modify
# coding: utf-8
# Copyright 2010 Mark L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.internet import defer
from twisted.trial import unittest
import txmongo

mongo_host = "localhost"
mongo_port = 27017


class TestFindAndModify(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_Update(self):
        yield self.coll.insert([{'oh':'hai', 'lulz':123},
                {'oh':'kthxbye', 'lulz':456}], safe=True)

        res = yield self.coll.find_one({'oh':'hai'})
        self.assertEqual(res['lulz'], 123)

        res = yield self.coll.find_and_modify({'o2h':'hai'},{'$inc':{'lulz':1}})
        self.assertEqual(res, None)

        res = yield self.coll.find_and_modify({'oh':'hai'},{'$inc':{'lulz':1}})
        #print res
        self.assertEqual(res['lulz'], 123)
        res = yield self.coll.find_and_modify({'oh':'hai'},{'$inc':{'lulz':1}},new=True)
        self.assertEqual(res['lulz'], 125)

        res = yield self.coll.find_one({'oh':'kthxbye'})
        self.assertEqual(res['lulz'], 456)


    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop()
        yield self.conn.disconnect()


########NEW FILE########
__FILENAME__ = test_objects
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import time
from StringIO import StringIO

from bson import objectid, timestamp
import txmongo
from txmongo import database
from txmongo import collection
from txmongo import gridfs
from txmongo import filter as qf
from txmongo._gridfs import GridIn
from twisted.trial import unittest
from twisted.trial import runner
from twisted.internet import base, defer

mongo_host="localhost"
mongo_port=27017
base.DelayedCall.debug = False


class TestMongoObjects(unittest.TestCase):
    @defer.inlineCallbacks
    def test_MongoObjects(self):
        """ Tests creating mongo objects """
        conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        mydb = conn.mydb
        self.assertEqual(isinstance(mydb, database.Database), True)
        mycol = mydb.mycol
        self.assertEqual(isinstance(mycol, collection.Collection), True)
        yield conn.disconnect()

    @defer.inlineCallbacks
    def test_MongoOperations(self):
        """ Tests mongo operations """
        conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        test = conn.foo.test
        
        # insert
        doc = {"foo":"bar", "items":[1, 2, 3]}
        yield test.insert(doc, safe=True)
        result = yield test.find_one(doc)
        self.assertEqual(result.has_key("_id"), True)
        self.assertEqual(result["foo"], "bar")
        self.assertEqual(result["items"], [1, 2, 3])
        
        # insert preserves object id
        doc.update({'_id': objectid.ObjectId()})
        yield test.insert(doc, safe=True)
        result = yield test.find_one(doc)
        self.assertEqual(result.get('_id'), doc.get('_id'))
        self.assertEqual(result["foo"], "bar")
        self.assertEqual(result["items"], [1, 2, 3])

        # update
        yield test.update({"_id":result["_id"]}, {"$set":{"one":"two"}}, safe=True)
        result = yield test.find_one({"_id":result["_id"]})
        self.assertEqual(result["one"], "two")

        # delete
        yield test.remove(result["_id"], safe=True)

        # disconnect
        yield conn.disconnect()

    @defer.inlineCallbacks
    def test_Timestamps(self):
        """Tests mongo operations with Timestamps"""
        conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        test = conn.foo.test_ts

        test.drop()

        # insert with specific timestamp
        doc1 = {'_id':objectid.ObjectId(),
                'ts':timestamp.Timestamp(1, 2)}
        yield test.insert(doc1, safe=True)

        result = yield test.find_one(doc1)
        self.assertEqual(result.get('ts').time, 1)
        self.assertEqual(result.get('ts').inc, 2)

        # insert with specific timestamp
        doc2 = {'_id':objectid.ObjectId(),
                'ts':timestamp.Timestamp(2, 1)}
        yield test.insert(doc2, safe=True)

        # the objects come back sorted by ts correctly.
        # (test that we stored inc/time in the right fields)
        result = yield test.find(filter=qf.sort(qf.ASCENDING('ts')))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['_id'], doc1['_id'])
        self.assertEqual(result[1]['_id'], doc2['_id'])

        # insert with null timestamp
        doc3 = {'_id':objectid.ObjectId(),
                'ts':timestamp.Timestamp(0, 0)}
        yield test.insert(doc3, safe=True)

        # time field loaded correctly
        result = yield test.find_one(doc3['_id'])
        now = time.time()
        self.assertTrue(now - 2 <= result['ts'].time <= now)

        # delete
        yield test.remove(doc1["_id"], safe=True)
        yield test.remove(doc2["_id"], safe=True)
        yield test.remove(doc3["_id"], safe=True)

        # disconnect
        yield conn.disconnect()


class TestGridFsObjects(unittest.TestCase):
    """ Test the GridFS operations from txmongo._gridfs """
    @defer.inlineCallbacks
    def _disconnect(self, conn):
        """ Disconnect the connection """
        yield conn.disconnect()
    
    @defer.inlineCallbacks
    def test_GridFsObjects(self):
        """ Tests gridfs objects """
        conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        db = conn.test
        collection = db.fs
        
        gfs = gridfs.GridFS(db) # Default collection
        
        gridin = GridIn(collection, filename='test', contentType="text/plain",
                        chunk_size=2**2**2**2)
        new_file = gfs.new_file(filename='test2', contentType="text/plain",
                        chunk_size=2**2**2**2)
        
        # disconnect
        yield conn.disconnect()
        
    @defer.inlineCallbacks
    def test_GridFsOperations(self):
        """ Tests gridfs operations """
        conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        db = conn.test
        collection = db.fs
        
        # Don't forget to disconnect
        self.addCleanup(self._disconnect, conn)
        try:
            in_file = StringIO("Test input string")
            out_file = StringIO()
        except Exception, e:
            self.fail("Failed to create memory files for testing: %s" % e)

        g_out = None
        
        try:
            # Tests writing to a new gridfs file
            gfs = gridfs.GridFS(db) # Default collection
            g_in = gfs.new_file(filename='optest', contentType="text/plain",
                            chunk_size=2**2**2**2) # non-default chunk size used
            # yielding to ensure writes complete before we close and close before we try to read
            yield g_in.write(in_file.read())
            yield g_in.close()
            
            # Tests reading from an existing gridfs file
            g_out = yield gfs.get_last_version('optest')
            data = yield g_out.read()
            out_file.write(data)
            _id = g_out._id
        except Exception,e:
            self.fail("Failed to communicate with the GridFS. " +
                      "Is MongoDB running? %s" % e)
        else:
            self.assertEqual(in_file.getvalue(), out_file.getvalue(),
                         "Could not read the value from writing an input")        
        finally:
            in_file.close()
            out_file.close()
            if g_out:
                g_out.close()

        
        listed_files = yield gfs.list()
        self.assertEqual(['optest'], listed_files,
                         "'optest' is the only expected file and we received %s" % listed_files)
        
        yield gfs.delete(_id)

if __name__ == "__main__":
    suite = runner.TrialSuite((TestMongoObjects, TestGridFsObjects))
    suite.run()

########NEW FILE########
__FILENAME__ = test_queries
# coding: utf-8
# Copyright 2010 Mark L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.internet import defer
from twisted.trial import unittest
import txmongo

mongo_host = "localhost"
mongo_port = 27017


class TestMongoQueries(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_SingleCursorIteration(self):
        yield self.coll.insert([{'v':i} for i in xrange(10)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 10)

    @defer.inlineCallbacks
    def test_MultipleCursorIterations(self):
        yield self.coll.insert([{'v':i} for i in xrange(450)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 450)

    @defer.inlineCallbacks
    def test_LargeData(self):
        yield self.coll.insert([{'v':' '*(2**19)} for i in xrange(4)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 4)

    @defer.inlineCallbacks
    def test_SpecifiedFields(self):
        yield self.coll.insert([{k: v for k in 'abcdefg'} for v in xrange(5)], safe=True)
        res = yield self.coll.find(fields={'a': 1, 'c': 1})
        cnt = yield self.coll.count(fields={'a': 1, 'c': 1})
        self.assertEqual(res[0].keys(), ['a', 'c', '_id'])
        res = yield self.coll.find(fields=['a', 'c'])
        cnt = yield self.coll.count(fields=['a', 'c'])
        self.assertEqual(res[0].keys(), ['a', 'c', '_id'])
        res = yield self.coll.find(fields=[])
        cnt = yield self.coll.count(fields=[])
        self.assertEqual(res[0].keys(), ['_id'])
        self.assertRaises(TypeError, self.coll._fields_list_to_dict, [1])

    @defer.inlineCallbacks
    def test_group(self):
        yield self.coll.insert([{'v': i % 2} for i in xrange(5)], safe=True)
        reduce_ = '''
        function(curr, result) {
            result.total += curr.v;
        }
        '''
        keys = {'v': 1}
        initial = {'total': 0}
        cond = {'v': {'$in': [0, 1]}}
        final = '''
        function(result) {
            result.five = 5;
        }
        '''
        res = yield self.coll.group(keys, initial, reduce_, cond, final)
        self.assertEqual(len(res['retval']), 2)

        keys = '''
        function(doc) {
            return {'value': 5, 'v': 1};
        }
        '''

        res = yield self.coll.group(keys, initial, reduce_, cond, final)
        self.assertEqual(len(res['retval']), 1)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop()
        yield self.conn.disconnect()


class TestMongoQueriesEdgeCases(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_BelowBatchThreshold(self):
        yield self.coll.insert([{'v':i} for i in xrange(100)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 100)

    @defer.inlineCallbacks
    def test_EqualToBatchThreshold(self):
        yield self.coll.insert([{'v':i} for i in xrange(101)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 101)

    @defer.inlineCallbacks
    def test_AboveBatchThreshold(self):
        yield self.coll.insert([{'v':i} for i in xrange(102)], safe=True)
        res = yield self.coll.find()
        self.assertEqual(len(res), 102)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop()
        yield self.conn.disconnect()


class TestLimit(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_LimitBelowBatchThreshold(self):
        yield self.coll.insert([{'v':i} for i in xrange(50)], safe=True)
        res = yield self.coll.find(limit=20)
        self.assertEqual(len(res), 20)

    @defer.inlineCallbacks
    def test_LimitAboveBatchThreshold(self):
        yield self.coll.insert([{'v':i} for i in xrange(200)], safe=True)
        res = yield self.coll.find(limit=150)
        self.assertEqual(len(res), 150)

    @defer.inlineCallbacks
    def test_LimitAtBatchThresholdEdge(self):
        yield self.coll.insert([{'v':i} for i in xrange(200)], safe=True)
        res = yield self.coll.find(limit=100)
        self.assertEqual(len(res), 100)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(200)], safe=True)
        res = yield self.coll.find(limit=101)
        self.assertEqual(len(res), 101)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(200)], safe=True)
        res = yield self.coll.find(limit=102)
        self.assertEqual(len(res), 102)

    @defer.inlineCallbacks
    def test_LimitAboveMessageSizeThreshold(self):
        yield self.coll.insert([{'v':' '*(2**20)} for i in xrange(8)], safe=True)
        res = yield self.coll.find(limit=5)
        self.assertEqual(len(res), 5)

    @defer.inlineCallbacks
    def test_HardLimit(self):
        yield self.coll.insert([{'v':i} for i in xrange(200)], safe=True)
        res = yield self.coll.find(limit=-150)
        self.assertEqual(len(res), 150)

    @defer.inlineCallbacks
    def test_HardLimitAboveMessageSizeThreshold(self):
        yield self.coll.insert([{'v':' '*(2**20)} for i in xrange(8)], safe=True)
        res = yield self.coll.find(limit=-6)
        self.assertEqual(len(res), 4)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop(safe=True)
        yield self.conn.disconnect()


class TestSkip(unittest.TestCase):

    timeout = 5

    @defer.inlineCallbacks
    def setUp(self):
        self.conn = yield txmongo.MongoConnection(mongo_host, mongo_port)
        self.coll = self.conn.mydb.mycol

    @defer.inlineCallbacks
    def test_Skip(self):
        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=3)
        self.assertEqual(len(res), 2)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=5)
        self.assertEqual(len(res), 0)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=6)
        self.assertEqual(len(res), 0)

    @defer.inlineCallbacks
    def test_SkipWithLimit(self):
        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=3, limit=1)
        self.assertEqual(len(res), 1)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=4, limit=2)
        self.assertEqual(len(res), 1)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=4, limit=1)
        self.assertEqual(len(res), 1)

        yield self.coll.drop(safe=True)

        yield self.coll.insert([{'v':i} for i in xrange(5)], safe=True)
        res = yield self.coll.find(skip=5, limit=1)
        self.assertEqual(len(res), 0)

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.coll.drop(safe=True)
        yield self.conn.disconnect()

########NEW FILE########
__FILENAME__ = collection
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bson
from bson import ObjectId
from bson.code import Code
from bson.son import SON
import types
from pymongo import errors
from txmongo import filter as qf
from txmongo.protocol import DELETE_SINGLE_REMOVE, UPDATE_UPSERT, \
                             UPDATE_MULTI, Query, Getmore, Insert, \
                             Update, Delete
from twisted.internet import defer

class Collection(object):
    def __init__(self, database, name):
        if not isinstance(name, basestring):
            raise TypeError("name must be an instance of basestring")

        if not name or ".." in name:
            raise errors.InvalidName("collection names cannot be empty")
        if "$" in name and not (name.startswith("oplog.$main") or
                                name.startswith("$cmd")):
            raise errors.InvalidName("collection names must not "
                              "contain '$': %r" % name)
        if name[0] == "." or name[-1] == ".":
            raise errors.InvalidName("collection names must not start "
                              "or end with '.': %r" % name)
        if "\x00" in name:
            raise errors.InvalidName("collection names must not contain the "
                              "null character")

        self._database = database
        self._collection_name = unicode(name)

    def __str__(self):
        return "%s.%s" % (str(self._database), self._collection_name)

    def __repr__(self):
        return "Collection(%s, %s)" % (self._database, self._collection_name)

    def __getitem__(self, collection_name):
        return Collection(self._database,
                          "%s.%s" % (self._collection_name, collection_name))

    def __cmp__(self, other):
        if isinstance(other, Collection):
            return cmp((self._database, self._collection_name),
                       (other._database, other._collection_name))
        return NotImplemented

    def __getattr__(self, collection_name):
        return self[collection_name]

    def __call__(self, collection_name):
        return self[collection_name]

    def _fields_list_to_dict(self, fields):
        """
        transform a list of fields from ["a", "b"] to {"a":1, "b":1}
        """
        as_dict = {}
        for field in fields:
            if not isinstance(field, types.StringTypes):
                raise TypeError("fields must be a list of key names")
            as_dict[field] = 1
        return as_dict

    def _gen_index_name(self, keys):
        return u"_".join([u"%s_%s" % item for item in keys])

    def options(self):
        def wrapper(result):
            if result:
                options = result.get("options", {})
                if "create" in options:
                    del options["create"]
                return options
            return {}

        d = self._database.system.namespaces.find_one({"name": str(self)})
        d.addCallback(wrapper)
        return d

    @defer.inlineCallbacks
    def find(self, spec=None, skip=0, limit=0, fields=None, filter=None, **kwargs):
        if spec is None:
            spec = SON()

        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(fields, (types.DictType, types.ListType, types.NoneType)):
            raise TypeError("fields must be an instance of dict or list")
        if not isinstance(skip, types.IntType):
            raise TypeError("skip must be an instance of int")
        if not isinstance(limit, types.IntType):
            raise TypeError("limit must be an instance of int")

        if fields is not None:
            if not isinstance(fields, types.DictType):
                if not fields:
                    fields = ["_id"]
                fields = self._fields_list_to_dict(fields)

        if isinstance(filter, (qf.sort, qf.hint, qf.explain, qf.snapshot)):
            if '$query' not in spec:
                spec = {'$query': spec}
                for k,v in filter.iteritems():
                    spec['$' + k] = dict(v)

        if self._database._authenticated:
            proto = yield self._database.connection.get_authenticated_protocol(self._database)
        else :
            proto = yield self._database.connection.getprotocol()

        flags = kwargs.get('flags', 0)
        query = Query(flags=flags, collection=str(self),
                      n_to_skip=skip, n_to_return=limit,
                      query=spec, fields=fields)

        reply = yield proto.send_QUERY(query)
        documents = reply.documents
        while reply.cursor_id:
            if limit <= 0:
                to_fetch = 0
            else:
                to_fetch = -1 if len(documents) > limit else limit - len(documents)
            if to_fetch < 0:
                break
                
            getmore = Getmore(collection=str(self),
                              n_to_return=to_fetch,
                              cursor_id=reply.cursor_id)
            reply = yield proto.send_GETMORE(getmore)
            documents.extend(reply.documents)

        if limit > 0:
            documents = documents[:limit]

        as_class = kwargs.get('as_class', dict)

        defer.returnValue([d.decode(as_class=as_class) for d in documents])

    def find_one(self, spec=None, fields=None, **kwargs):
        if isinstance(spec, ObjectId):
            spec = {'_id': spec}
        df = self.find(spec=spec, limit=1, fields=fields, **kwargs)
        df.addCallback(lambda r: r[0] if r else {})
        return df

    def count(self, spec=None, fields=None):
        def wrapper(result):
            return result["n"]

        if fields is not None:
            if not fields:
                fields = ["_id"]
            fields = self._fields_list_to_dict(fields)

        spec = SON([("count", self._collection_name),
                    ("query", spec or SON()),
                    ("fields", fields)])
        d = self._database["$cmd"].find_one(spec)
        d.addCallback(wrapper)
        return d

    def group(self, keys, initial, reduce, condition=None, finalize=None):
        body = {
            "ns": self._collection_name,
            "initial": initial,
            "$reduce": Code(reduce),
        }

        if isinstance(keys, basestring):
            body['$keyf'] = Code(keys)
        else:
            body['key'] = self._fields_list_to_dict(keys)

        if condition:
            body["cond"] = condition
        if finalize:
            body["finalize"] = Code(finalize)

        return self._database["$cmd"].find_one({"group": body})

    def filemd5(self, spec):
        def wrapper(result):
            return result.get('md5')

        if not isinstance(spec, ObjectId):
            raise ValueError("filemd5 expected an objectid for its "
                             "non-keyword argument")

        spec = SON([("filemd5", spec),
                    ("root", self._collection_name)])

        d = self._database['$cmd'].find_one(spec)
        d.addCallback(wrapper)
        return d

    @defer.inlineCallbacks
    def insert(self, docs, safe=True, **kwargs):
        if isinstance(docs, types.DictType):
            ids = docs.get('_id', ObjectId())
            docs["_id"] = ids
            docs = [docs]
        elif isinstance(docs, types.ListType):
            ids = []
            for doc in docs:
                if isinstance(doc, types.DictType):
                    id = doc.get('_id', ObjectId())
                    ids.append(id)
                    doc["_id"] = id
                else:
                    raise TypeError("insert takes a document or a list of documents")
        else:
            raise TypeError("insert takes a document or a list of documents")

        docs = [bson.BSON.encode(d) for d in docs]
        flags = kwargs.get('flags', 0)
        insert = Insert(flags=flags, collection=str(self), documents=docs)

        if self._database._authenticated :
            proto = yield self._database.connection.get_authenticated_protocol(self._database)
        else :
            proto = yield self._database.connection.getprotocol()

        proto.send_INSERT(insert)

        if safe:
            yield proto.getlasterror(str(self._database))

        defer.returnValue(ids)

    @defer.inlineCallbacks
    def update(self, spec, document, upsert=False, multi=False, safe=True, **kwargs):
        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(document, types.DictType):
            raise TypeError("document must be an instance of dict")
        if not isinstance(upsert, types.BooleanType):
            raise TypeError("upsert must be an instance of bool")

        flags = kwargs.get('flags', 0)

        if multi:
            flags |= UPDATE_MULTI
        if upsert:
            flags |= UPDATE_UPSERT

        spec = bson.BSON.encode(spec)
        document = bson.BSON.encode(document)
        update = Update(flags=flags, collection=str(self),
                        selector=spec, update=document)
        if self._database._authenticated :
            proto = yield self._database.connection.get_authenticated_protocol(self._database)
        else :
            proto = yield self._database.connection.getprotocol()

        proto.send_UPDATE(update)

        if safe:
            ret = yield proto.getlasterror(str(self._database))
            defer.returnValue(ret)

    def save(self, doc, safe=True, **kwargs):
        if not isinstance(doc, types.DictType):
            raise TypeError("cannot save objects of type %s" % type(doc))

        objid = doc.get("_id")
        if objid:
            return self.update({"_id": objid}, doc, safe=safe, upsert=True, **kwargs)
        else:
            return self.insert(doc, safe=safe, **kwargs)

    @defer.inlineCallbacks
    def remove(self, spec, safe=True, single=False, **kwargs):
        if isinstance(spec, ObjectId):
            spec = SON(dict(_id=spec))
        if not isinstance(spec, types.DictType):
            raise TypeError("spec must be an instance of dict, not %s" % type(spec))

        flags = kwargs.get('flags', 0)
        if single:
            flags |= DELETE_SINGLE_REMOVE

        spec = bson.BSON.encode(spec)
        delete = Delete(flags=flags, collection=str(self), selector=spec)
        if self._database._authenticated :
            proto = yield self._database.connection.get_authenticated_protocol(self._database)
        else :
            proto = yield self._database.connection.getprotocol()

        proto.send_DELETE(delete)

        if safe:
            ret = yield proto.getlasterror(str(self._database))
            defer.returnValue(ret)

    def drop(self, **kwargs):
        return self._database.drop_collection(self._collection_name)

    def create_index(self, sort_fields, **kwargs):
        def wrapper(result, name):
            return name

        if not isinstance(sort_fields, qf.sort):
            raise TypeError("sort_fields must be an instance of filter.sort")

        if "name" not in kwargs:
            name = self._gen_index_name(sort_fields["orderby"])
        else:
            name = kwargs.pop("name")

        key = SON()
        for k,v in sort_fields["orderby"]:
            key.update({k:v})

        index = SON(dict(
            ns=str(self),
            name=name,
            key=key
        ))

        if "drop_dups" in kwargs:
            kwargs["dropDups"] = kwargs.pop("drop_dups")

        if "bucket_size" in kwargs:
            kwargs["bucketSize"] = kwargs.pop("bucket_size")

        index.update(kwargs)
        d = self._database.system.indexes.insert(index, safe=True)
        d.addCallback(wrapper, name)
        return d

    def ensure_index(self, sort_fields, **kwargs):
        # ensure_index is an alias of create_index since we are not 
        # keep an index cache same way pymongo does
        return self.create_index(sort_fields, **kwargs)

    def drop_index(self, index_identifier):
        if isinstance(index_identifier, types.StringTypes):
            name = index_identifier
        elif isinstance(index_identifier, qf.sort):
            name = self._gen_index_name(index_identifier["orderby"])
        else:
            raise TypeError("index_identifier must be a name or instance of filter.sort")

        cmd = SON([("deleteIndexes", self._collection_name), ("index", name)])
        return self._database["$cmd"].find_one(cmd)

    def drop_indexes(self):
        return self.drop_index("*")

    def index_information(self):
        def wrapper(raw):
            info = {}
            for idx in raw:
                info[idx["name"]] = idx["key"].items()
            return info

        d = self._database.system.indexes.find({"ns": str(self)})
        d.addCallback(wrapper)
        return d

    def rename(self, new_name):
        cmd = SON([("renameCollection", str(self)), ("to", "%s.%s" % \
            (str(self._database), new_name))])
        return self._database("admin")["$cmd"].find_one(cmd)

    def distinct(self, key, spec=None):
        def wrapper(result):
            if result:
                return result.get("values")
            return {}

        cmd = SON([("distinct", self._collection_name), ("key", key)])
        if spec:
            cmd["query"] = spec

        d = self._database["$cmd"].find_one(cmd)
        d.addCallback(wrapper)
        return d

    def aggregate(self, pipeline, full_response=False):
        def wrapper(result, full_response):
            if full_response:
                return result
            return result.get("result")

        cmd = SON([("aggregate", self._collection_name),
                   ("pipeline", pipeline)])

        d = self._database["$cmd"].find_one(cmd)
        d.addCallback(wrapper, full_response)
        return d

    def map_reduce(self, map, reduce, full_response=False, **kwargs):
        def wrapper(result, full_response):
            if full_response:
                return result
            return result.get("result")

        cmd = SON([("mapreduce", self._collection_name),
                       ("map", map), ("reduce", reduce)])
        cmd.update(**kwargs)
        d = self._database["$cmd"].find_one(cmd)
        d.addCallback(wrapper, full_response)
        return d

    def find_and_modify(self, query={}, update=None, upsert=False, **kwargs):
        def wrapper(result):
            no_obj_error = "No matching object found"
            if not result['ok']:
                if result["errmsg"] == no_obj_error:
                    return None
                else:
                    raise ValueError("Unexpected Error: %s" % (result,))
            return result.get('value')

        if (not update and not kwargs.get('remove', None)):
            raise ValueError("Must either update or remove")

        if (update and kwargs.get('remove', None)):
            raise ValueError("Can't do both update and remove")

        cmd = SON([("findAndModify", self._collection_name)])
        cmd.update(kwargs)
        # No need to include empty args
        if query:
            cmd['query'] = query
        if update:
            cmd['update'] = update
        if upsert:
            cmd['upsert'] = upsert

        d = self._database["$cmd"].find_one(cmd)
        d.addCallback(wrapper)

        return d

########NEW FILE########
__FILENAME__ = connection
# coding: utf-8
# Copyright 2012 Christian Hergert
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pymongo
from pymongo import errors
from pymongo.uri_parser import parse_uri
from pymongo import auth

from bson.son import SON

from twisted.internet import defer, reactor, task
from twisted.internet.protocol import ReconnectingClientFactory

from txmongo.database import Database
from txmongo.protocol import MongoProtocol, Query

class _Connection(ReconnectingClientFactory):
    __notify_ready = None
    __discovered = None
    __index = -1
    __uri = None
    __conf_loop = None
    __conf_loop_seconds = 300.0
    
    instance = None
    protocol = MongoProtocol
    maxDelay = 60
    
    def __init__(self, pool, uri,id):
        self.__discovered = []
        self.__notify_ready = []
        self.__pool = pool
        self.__uri = uri
        self.__conf_loop = task.LoopingCall(lambda: self.configure(self.instance))
        self.__conf_loop.start(self.__conf_loop_seconds, now=False)
        self.connectionid = id
        self.auth_set = set()
    
    def buildProtocol(self, addr):
        # Build the protocol.
        p = ReconnectingClientFactory.buildProtocol(self, addr)
        
        # If we do not care about connecting to a slave, then we can simply
        # return the protocol now and fire that we are ready.
        if self.uri['options'].get('slaveok', False):
            p.connectionReady().addCallback(lambda _: self.setInstance(instance=p))
            return p
        
        # Update our server configuration. This may disconnect if the node
        # is not a master.
        p.connectionReady().addCallback(lambda _: self.configure(p))
        
        return p
    
    def configure(self, proto):
        """
            Configures the protocol using the information gathered from the
            remote Mongo instance. Such information may contain the max
            BSON document size, replica set configuration, and the master
            status of the instance.
            """
        if proto:
            query = Query(collection='admin.$cmd', query={'ismaster': 1})
            df = proto.send_QUERY(query)
            df.addCallback(self._configureCallback, proto)
            return df
        return defer.succeed(None)
    
    def _configureCallback(self, reply, proto):
        """
            Handle the reply from the "ismaster" query. The reply contains
            configuration information about the peer.
            """
        # Make sure we got a result document.
        if len(reply.documents) != 1:
            proto.fail(errors.OperationFailure('Invalid document length.'))
            return
        
        # Get the configuration document from the reply.
        config = reply.documents[0].decode()
        
        # Make sure the command was successful.
        if not config.get('ok'):
            code = config.get('code')
            msg = config.get('err', 'Unknown error')
            proto.fail(errors.OperationFailure(msg, code))
            return
        
        # Check that the replicaSet matches.
        set_name = config.get('setName')
        expected_set_name = self.uri['options'].get('setname')
        if expected_set_name and (expected_set_name != set_name):
            # Log the invalid replica set failure.
            msg = 'Mongo instance does not match requested replicaSet.'
            reason = pymongo.errros.ConfigurationError(msg)
            proto.fail(reason)
            return
        
        # Track max bson object size limit.
        max_bson_size = config.get('maxBsonObjectSize')
        if max_bson_size:
            proto.max_bson_size = max_bson_size
        
        # Track the other hosts in the replica set.
        hosts = config.get('hosts')
        if isinstance(hosts, list) and hosts:
            hostaddrs = []
            for host in hosts:
                if ':' not in host:
                    host = (host, 27017)
                else:
                    host = host.split(':', 1)
                    host[1] = int(host[1])
                hostaddrs.append(host)
            self.__discovered = hostaddrs
        
        # Check if this node is the master.
        ismaster = config.get('ismaster')
        if not ismaster:
            reason = pymongo.errors.AutoReconnect('not master')
            proto.fail(reason)
            return
        
        # Notify deferreds waiting for completion.
        self.setInstance(instance=proto)
    
    def clientConnectionFailed(self, connector, reason):
        self.auth_set = set()
        if self.continueTrying:
            self.connector = connector
            self.retryNextHost()
    
    def clientConnectionLost(self, connector, reason):
        self.auth_set = set()
        if self.continueTrying:
            self.connector = connector
            self.retryNextHost()
    
    def notifyReady(self):
        """
            Returns a deferred that will fire when the factory has created a
            protocol that can be used to communicate with a Mongo server.
            
            Note that this will not fire until we have connected to a Mongo
            master, unless slaveOk was specified in the Mongo URI connection
            options.
            """
        if self.instance:
            return defer.succeed(self.instance)
        if self.__notify_ready is None:
            self.__notify_ready = []
        df = defer.Deferred()
        self.__notify_ready.append(df)
        return df
    
    def retryNextHost(self, connector=None):
        """
            Have this connector connect again, to the next host in the
            configured list of hosts.
            """
        if not self.continueTrying:
            log.msg("Abandoning %s on explicit request" % (connector,))
            return
        
        if connector is None:
            if self.connector is None:
                raise ValueError("no connector to retry")
            else:
                connector = self.connector
        
        delay = False
        self.__index += 1
        
        allNodes = list(self.uri['nodelist']) + list(self.__discovered)
        if self.__index >= len(allNodes):
            self.__index = 0
            delay = True
        
        connector.host, connector.port = allNodes[self.__index]
        
        if delay:
            self.retry(connector)
        else:
            connector.connect()
    
    def setInstance(self, instance=None, reason=None):
        self.instance = instance
        deferreds, self.__notify_ready = self.__notify_ready, []
        if deferreds:
            for df in deferreds:
                if instance:
                    df.callback(self)
                else:
                    df.errback(reason)
    
    def stopTrying(self):
        ReconnectingClientFactory.stopTrying(self)
        self.__conf_loop.stop()

    @property
    def uri(self):
        return self.__uri

        
class ConnectionPool(object):
    __index = 0
    __pool = None
    __pool_size = None
    __uri = None


    def __init__(self, uri='mongodb://127.0.0.1:27017', pool_size=1):
        assert isinstance(uri, basestring)
        assert isinstance(pool_size, int)
        assert pool_size >= 1
        
        if not uri.startswith('mongodb://'):
            uri = 'mongodb://' + uri
        
        self.cred_cache = {}
        self.__uri = parse_uri(uri)
        self.__pool_size = pool_size
        self.__pool = [_Connection(self, self.__uri,i) for i in xrange(pool_size)]
        
        host, port = self.__uri['nodelist'][0]
        for factory in self.__pool:
            factory.connector = reactor.connectTCP(host, port, factory)
    
    def getprotocols(self):
        return self.__pool
    
    def __getitem__(self, name):
        return Database(self, name)
    
    def __getattr__(self, name):
        return self[name]
    
    def __repr__(self):
        if self.uri['nodelist']:
            return 'Connection(%r, %r)' % self.uri['nodelist'][0]
        return 'Connection()'
    

    @defer.inlineCallbacks
    def authenticate_with_nonce (self,database,name,password) :

        database_name = str(database)
        self.cred_cache[database_name] = (name,password)
        current_connection = self.__pool[self.__index]
        proto = yield self.getprotocol()

        collection_name = database_name+'.$cmd'
        query = Query(collection=collection_name, query={'getnonce': 1})
        result = yield proto.send_QUERY(query)
           
        result = result.documents[0].decode()
        
        if result["ok"] :
            nonce = result["nonce"]
        else :
            defer.returnValue(result["errmsg"])
        
        key = auth._auth_key(nonce, name, password)
        
        # hacky because order matters
        auth_command = SON(authenticate=1)
        auth_command['user'] = unicode(name)
        auth_command['nonce'] = nonce
        auth_command['key'] = key

        query = Query(collection=str(collection_name), query=auth_command)
        result = yield proto.send_QUERY(query)
                
        result = result.documents[0].decode()
                
        if result["ok"]:
            database._authenticated = True
            current_connection.auth_set.add(database_name)
            defer.returnValue(result["ok"])
        else:
            del self.cred_cache[database_name]
            defer.returnValue(result["errmsg"])
            
    def disconnect(self):
        for factory in self.__pool:
            factory.stopTrying()
            factory.stopFactory()
            if factory.instance and factory.instance.transport:
                factory.instance.transport.loseConnection()
            if factory.connector:
                factory.connector.disconnect()
        # Wait for the next iteration of the loop for resolvers
        # to potentially cleanup.
        df = defer.Deferred()
        reactor.callLater(0, df.callback, None)
        return df

    @defer.inlineCallbacks
    def get_authenticated_protocol(self,database) :
        # Get the next protocol available for communication in the pool
        connection = self.__pool[self.__index]
        database_name = str(database)
        
        if database_name not in connection.auth_set :
            name  = self.cred_cache[database_name][0]
            password = self.cred_cache[database_name][1]
            yield self.authenticate_with_nonce(database,name,password)
        else :
            self.__index = (self.__index + 1) % self.__pool_size

        defer.returnValue(connection.instance)

    def getprotocol(self):
        # Get the next protocol available for communication in the pool.
        connection = self.__pool[self.__index]
        self.__index = (self.__index + 1) % self.__pool_size

        # If the connection is already connected, just return it.
        if connection.instance:
            return defer.succeed(connection.instance)
        
        # Wait for the connection to connection.
        return connection.notifyReady().addCallback(lambda c: c.instance)
    
    @property
    def uri(self):
        return self.__uri


###
# Begin Legacy Wrapper
###

class MongoConnection(ConnectionPool):
    def __init__(self, host, port, pool_size=1):
        uri = 'mongodb://%s:%d/' % (host, port)
        ConnectionPool.__init__(self, uri, pool_size=pool_size)
lazyMongoConnectionPool = MongoConnection
lazyMongoConnection = MongoConnection
MongoConnectionPool = MongoConnection

###
# End Legacy Wrapper
###


########NEW FILE########
__FILENAME__ = database
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#from bson.son import SON
#from pymongo import auth
from twisted.internet import defer
from txmongo.collection import Collection


class Database(object):
    __factory = None
    _authenticated = False

    def __init__(self, factory, database_name):
        self.__factory = factory
        self._database_name = unicode(database_name)

    def __str__(self):
        return self._database_name

    def __repr__(self):
        return "Database(%r, %r)" % (self.__factory, self._database_name,)

    def __call__(self, database_name):
        return Database(self._factory, database_name)

    def __getitem__(self, collection_name):
        return Collection(self, collection_name)

    def __getattr__(self, collection_name):
        return self[collection_name]

    @property
    def connection(self):
        return self.__factory

    def create_collection(self, name, options={}):
        def wrapper(result, deferred, collection):
            if result.get("ok", 0.0):
                deferred.callback(collection)
            else:
                deferred.errback(RuntimeError(result.get("errmsg", "unknown error")))

        deferred = defer.Deferred()
        collection = Collection(self, name)

        if options:
            if "size" in options:
                options["size"] = float(options["size"])

            command = SON({"create": name})
            command.update(options)
            d = self["$cmd"].find_one(command)
            d.addCallback(wrapper, deferred, collection)
        else:
            deferred.callback(collection)

        return deferred

    def drop_collection(self, name_or_collection):
        if isinstance(name_or_collection, Collection):
            name = name_or_collection._collection_name
        elif isinstance(name_or_collection, basestring):
            name = name_or_collection
        else:
            raise TypeError("name must be an instance of basestring or txmongo.Collection")

        return self["$cmd"].find_one({"drop": unicode(name)})

    def collection_names(self):
        def wrapper(results):
            names = [r["name"] for r in results]
            names = [n[len(str(self)) + 1:] for n in names
                if n.startswith(str(self) + ".")]
            names = [n for n in names if "$" not in n]
            return names

        d = self["system.namespaces"].find()
        d.addCallback(wrapper)
        return d

    @defer.inlineCallbacks
    def authenticate(self, name, password):
        """
        Send an authentication command for this database.
        mostly stolen from pymongo
        """
        if not isinstance(name, basestring):
            raise TypeError("name must be an instance of basestring")
        if not isinstance(password, basestring):
            raise TypeError("password must be an instance of basestring")
    
        """
        Authenticating
        """
        yield self.connection.authenticate_with_nonce(self,name,password)

########NEW FILE########
__FILENAME__ = dbref
# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for manipulating DBRefs (references to MongoDB documents)."""

from bson.son import SON
from txmongo.collection import Collection
import types

class DBRef(object):
    """A reference to a document stored in a Mongo database.
    """

    def __init__(self, collection, id, database=None):
        """Initialize a new DBRef.

        Raises TypeError if collection or database is not an instance of
        (str, unicode). `database` is optional and allows references to
        documents to work across databases.

        :Parameters:
          - `collection`: name of the collection the document is stored in
          - `id`: the value of the document's _id field
          - `database` (optional): name of the database to reference

        .. versionadded:: 1.1.1
           The `database` parameter.
        """
        if isinstance(collection, Collection):
            collection = collection._collection_name

        if not isinstance(collection, types.StringTypes):
            raise TypeError("collection must be an instance of (str, unicode)")

        if not isinstance(database, (types.StringTypes, types.NoneType)):
            raise TypeError("database must be an instance of (str, unicode)")

        self.__collection = collection
        self.__id = id
        self.__database = database

    def collection(self):
        """Get the name of this DBRef's collection as unicode.
        """
        return self.__collection
    collection = property(collection)

    def id(self):
        """Get this DBRef's _id.
        """
        return self.__id
    id = property(id)

    def database(self):
        """Get the name of this DBRef's database.

        Returns None if this DBRef doesn't specify a database.

        .. versionadded:: 1.1.1
        """
        return self.__database
    database = property(database)

    def as_doc(self):
        """Get the SON document representation of this DBRef.

        Generally not needed by application developers
        """
        doc = SON([("$ref", self.collection),
                         ("$id", self.id)])
        if self.database is not None:
            doc["$db"] = self.database
        return doc

    def __repr__(self):
        if self.database is None:
            return "DBRef(%s, %r)" % (self.collection, self.id)
        return "DBRef(%s, %r, %s)" % (self.collection, self.id, self.database)

    def __cmp__(self, other):
        if isinstance(other, DBRef):
            return cmp([self.__database, self.__collection, self.__id],
                       [other.__database, other.__collection, other.__id])
        return NotImplemented

    def __hash__(self):
        """Get a hash value for this :class:`DBRef`.

        .. versionadded:: 1.1
        """
        return hash((self.__collection, self.__id, self.__database))

########NEW FILE########
__FILENAME__ = filter
# coding: utf-8
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import types
from collections import defaultdict

"""Query filters"""


def _DIRECTION(keys, direction):
    if isinstance(keys, types.StringTypes):
        return (keys, direction),
    elif isinstance(keys, (types.ListType, types.TupleType)):
        return tuple([(k, direction) for k in keys])


def ASCENDING(keys):
    """Ascending sort order"""
    return _DIRECTION(keys, 1)


def DESCENDING(keys):
    """Descending sort order"""
    return _DIRECTION(keys, -1)


def GEO2D(keys):
    """
    Two-dimensional geospatial index
    http://www.mongodb.org/display/DOCS/Geospatial+Indexing
    """
    return _DIRECTION(keys, "2d")


def GEOHAYSTACK(keys):
    """
    Bucket-based geospatial index
    http://www.mongodb.org/display/DOCS/Geospatial+Haystack+Indexing
    """
    return _DIRECTION(keys, "geoHaystack")


 
class _QueryFilter(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, lambda: ())

    def __add__(self, obj):
        for k, v in obj.items():
            if isinstance(v, types.TupleType):
                self[k] += v
            else:
                self[k] = v
        return self

    def _index_document(self, operation, index_list):
        name = self.__class__.__name__
        try:
            assert isinstance(index_list, (types.ListType, types.TupleType))
            for key, direction in index_list:
                if not isinstance(key, types.StringTypes):
                    raise TypeError("Invalid %sing key: %s" % (name, repr(key)))
                if direction not in (1, -1, "2d", "geoHaystack"):
                    raise TypeError("Invalid %sing direction: %s" % (name, direction))
                self[operation] += tuple(((key, direction),))
        except Exception:
            raise TypeError("Invalid list of keys for %s: %s" % (name, repr(index_list)))

    def __repr__(self):
        return "<mongodb QueryFilter: %s>" % dict.__repr__(self)


class sort(_QueryFilter):
    """Sorts the results of a query."""

    def __init__(self, key_list):
        _QueryFilter.__init__(self)
        try:
            assert isinstance(key_list[0], (types.ListType, types.TupleType))
        except:
            key_list = (key_list,)
        self._index_document("orderby", key_list)


class hint(_QueryFilter):
    """Adds a `hint`, telling Mongo the proper index to use for the query."""

    def __init__(self, index_list):
        _QueryFilter.__init__(self)
        try:
            assert isinstance(index_list[0], (types.ListType, types.TupleType))
        except:
            index_list = (index_list,)
        self._index_document("$hint", index_list)


class explain(_QueryFilter):
    """Returns an explain plan for the query."""

    def __init__(self):
        _QueryFilter.__init__(self)
        self["explain"] = True


class snapshot(_QueryFilter):
    def __init__(self):
        _QueryFilter.__init__(self)
        self["snapshot"] = True

########NEW FILE########
__FILENAME__ = gridfs
from txmongo._gridfs import *

########NEW FILE########
__FILENAME__ = protocol
# coding: utf-8
# Copyright 2009 Alexandre Fiori
# Copyright 2012 Christian Hergert
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Low level connection to Mongo.

This module contains the wire protocol implementation for txmongo.
The various constants from the protocl are available as constants.

This implementation requires pymongo so that as much of the
implementation can be shared. This includes BSON encoding and
decoding as well as Exception types, when applicable.
"""

import bson
from   collections      import namedtuple
from   pymongo          import errors
import struct
from   twisted.internet import defer, protocol
from   twisted.python   import failure, log

INT_MAX = 2147483647

OP_REPLY        = 1
OP_MSG          = 1000
OP_UPDATE       = 2001
OP_INSERT       = 2002
OP_QUERY        = 2004
OP_GETMORE      = 2005
OP_DELETE       = 2006
OP_KILL_CURSORS = 2007

OP_NAMES = {
    OP_REPLY:        'REPLY',
    OP_MSG:          'MSG',
    OP_UPDATE:       'UPDATE',
    OP_INSERT:       'INSERT',
    OP_QUERY:        'QUERY',
    OP_GETMORE:      'GETMORE',
    OP_DELETE:       'DELETE',
    OP_KILL_CURSORS: 'KILL_CURSORS'
}

DELETE_SINGLE_REMOVE = 1 << 0

QUERY_TAILABLE_CURSOR   = 1 << 1
QUERY_SLAVE_OK          = 1 << 2
QUERY_OPLOG_REPLAY      = 1 << 3
QUERY_NO_CURSOR_TIMEOUT = 1 << 4
QUERY_AWAIT_DATA        = 1 << 5
QUERY_EXHAUST           = 1 << 6
QUERY_PARTIAL           = 1 << 7

REPLY_CURSOR_NOT_FOUND   = 1 << 0
REPLY_QUERY_FAILURE      = 1 << 1
REPLY_SHARD_CONFIG_STALE = 1 << 2
REPLY_AWAIT_CAPABLE      = 1 << 3

UPDATE_UPSERT = 1 << 0
UPDATE_MULTI  = 1 << 1

Msg = namedtuple('Msg', ['len', 'request_id', 'response_to', 'opcode', 'message'])
KillCursors = namedtuple('KillCursors', ['len', 'request_id', 'response_to', 'opcode', 'zero', 'n_cursors', 'cursors'])

class Delete(namedtuple('Delete', ['len', 'request_id', 'response_to', 'opcode', 'zero', 'collection', 'flags', 'selector'])):
    def __new__(cls, len=0, request_id=0, response_to=0, opcode=OP_DELETE,
                zero=0, collection='', flags=0, selector=None):
        return super(Delete, cls).__new__(cls, len, request_id, response_to,
                                           opcode, zero, collection,
                                           flags, selector)

class Getmore(namedtuple('Getmore', ['len', 'request_id', 'response_to',
                                     'opcode', 'zero', 'collection',
                                     'n_to_return', 'cursor_id'])):
    def __new__(cls, len=0, request_id=0, response_to=0, opcode=OP_GETMORE,
                zero=0, collection='', n_to_return=-1, cursor_id=-1):
        return super(Getmore, cls).__new__(cls, len, request_id, response_to,
                                           opcode, zero, collection,
                                           n_to_return, cursor_id)

class Insert(namedtuple('Insert', ['len', 'request_id', 'response_to',
                                   'opcode', 'flags', 'collection',
                                   'documents'])):
    def __new__(cls, len=0, request_id=0, response_to=0, opcode=OP_INSERT,
                flags=0, collection='', documents=None):
        return super(Insert, cls).__new__(cls, len, request_id, response_to,
                                          opcode, flags, collection, documents)

class Reply(namedtuple('Reply', ['len', 'request_id', 'response_to', 'opcode',
                                 'response_flags', 'cursor_id',
                                 'starting_from', 'n_returned', 'documents'])):
    def __new__(cls, _len=0, request_id=0, response_to=0, opcode=OP_REPLY,
                response_flags=0, cursor_id=0, starting_from=0,
                n_returned=None, documents=None):
        if documents is None:
            documents = []
        if n_returned is None:
            n_returned = len(documents)
        documents = [b if isinstance(b, bson.BSON) else bson.BSON.encode(b) for b in documents]
        return super(Reply, cls).__new__(cls, _len, request_id, response_to,
                                         opcode, response_flags, cursor_id,
                                         starting_from, n_returned,
                                         documents)

class Query(namedtuple('Query', ['len', 'request_id', 'response_to', 'opcode',
                                 'flags', 'collection', 'n_to_skip',
                                 'n_to_return', 'query', 'fields'])):
    def __new__(cls, len=0, request_id=0, response_to=0, opcode=OP_QUERY,
                flags=0, collection='', n_to_skip=0, n_to_return=-1,
                query=None, fields=None):
        if query is None:
            query = {}
        if not isinstance(query, bson.BSON):
            query = bson.BSON.encode(query)
        if fields is not None and not isinstance(fields, bson.BSON):
            fields = bson.BSON.encode(fields)
        return super(Query, cls).__new__(cls, len, request_id, response_to,
                                         opcode, flags, collection, n_to_skip,
                                         n_to_return, query, fields)

class Update(namedtuple('Update', ['len', 'request_id', 'response_to',
                                   'opcode', 'zero', 'collection', 'flags',
                                   'selector', 'update'])):
    def __new__(cls, len=0, request_id=0, response_to=0, opcode=OP_UPDATE,
                zero=0, collection='', flags=0, selector=None, update=None):
        return super(Update, cls).__new__(cls, len, request_id, response_to,
                                          opcode, zero, collection, flags,
                                          selector, update)

class MongoClientProtocol(protocol.Protocol):
    __request_id = 1

    def getrequestid(self):
        return self.__request_id

    def _send(self, iovec):
        request_id, self.__request_id = self.__request_id, self.__request_id + 1
        if self.__request_id >= INT_MAX:
            self.__request_id = 1
        datalen = sum([len(chunk) for chunk in iovec]) + 8
        datareq = struct.pack('<ii', datalen, request_id)
        iovec.insert(0, datareq)
        self.transport.write(''.join(iovec))
        return request_id

    def send(self, request):
        opname = OP_NAMES[request.opcode]
        sender = getattr(self, 'send_%s' % opname, None)
        if callable(sender):
            return sender(request)
        else:
            log.msg("No sender for opcode: %d" % request.opcode)

    def send_REPLY(self, request):
        iovec = [struct.pack('<iiiqii', *request[2:8])]
        iovec.extend(request.documents)
        self._send(iovec)

    def send_MSG(self, request):
        iovec = [struct.pack('<ii', *request[2:4]), request.message, '\x00']
        return self._send(iovec)

    def send_UPDATE(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00',
                 struct.pack('<i', request.flags),
                 request.selector,
                 request.update]
        return self._send(iovec)

    def send_INSERT(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00']
        iovec.extend(request.documents)
        return self._send(iovec)

    def send_QUERY(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00',
                 struct.pack('<ii', request.n_to_skip, request.n_to_return),
                 request.query,
                 (request.fields or '')]
        return self._send(iovec)

    def send_GETMORE(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00',
                 struct.pack('<iq', request.n_to_return, request.cursor_id)]
        return self._send(iovec)

    def send_DELETE(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00',
                 struct.pack('<i', request.flags),
                 request.selector]
        return self._send(iovec)

    def send_KILL_CURSORS(self, request):
        iovec = [struct.pack('<iii', *request[2:5]),
                 request.collection.encode('ascii'), '\x00',
                 struct.pack('<i', len(request.cursors))]
        for cursor in request.cursors:
            iovec.append(struct.pack('<q', cursor))
        return self._send(iovec)

class MongoServerProtocol(protocol.Protocol):
    __decoder = None

    def __init__(self):
        self.__decoder = MongoDecoder()

    def dataReceived(self, data):
        self.__decoder.feed(data)

        try:
            request = self.__decoder.next()
            while request:
                self.handle(request)
                request = self.__decoder.next()
        except Exception, ex:
            self.fail(reason=failure.Failure(ex))

    def handle(self, request):
        opname = OP_NAMES[request.opcode]
        handler = getattr(self, 'handle_%s' % opname, None)
        if callable(handler):
            handler(request)
        else:
            log.msg("No handler found for opcode: %d" % request.opcode)

    def handle_REPLY(self, request):
        pass

    def handle_MSG(self, request):
        pass

    def handle_UPDATE(self, request):
        pass

    def handle_INSERT(self, request):
        pass

    def handle_QUERY(self, request):
        pass

    def handle_GETMORE(self, request):
        pass

    def handle_DELETE(self, request):
        pass

    def handle_KILL_CURSORS(self, request):
        pass

class MongoProtocol(MongoServerProtocol, MongoClientProtocol):
    __connection_ready = None
    __deferreds = None

    def __init__(self):
        MongoServerProtocol.__init__(self)
        self.__connection_ready = []
        self.__deferreds = {}

    def inflight(self):
        return len(self.__deferreds)

    def connectionMade(self):
        deferreds, self.__connection_ready = self.__connection_ready, []
        if deferreds:
            for df in deferreds:
                df.callback(self)

    def connectionLost(self, reason):
        if self.__deferreds:
            deferreds, self.__deferreds = self.__deferreds, {}
            for df in deferreds.itervalues():
                df.errback(reason)
        deferreds, self.__connection_ready = self.__connection_ready, []
        if deferreds:
            for df in deferreds:
                df.errback(reason)
        protocol.Protocol.connectionLost(self, reason)

    def connectionReady(self):
        if self.transport:
            return defer.succeed(None)
        if not self.__connection_ready:
            self.__connection_ready = []
        df = defer.Deferred()
        self.__connection_ready.append(df)
        return df

    def send_GETMORE(self, request):
        request_id = MongoClientProtocol.send_GETMORE(self, request)
        df = defer.Deferred()
        self.__deferreds[request_id] = df
        return df

    def send_QUERY(self, request):
        request_id = MongoClientProtocol.send_QUERY(self, request)
        df = defer.Deferred()
        self.__deferreds[request_id] = df
        return df

    def handle_REPLY(self, request):
        if request.response_to in self.__deferreds:
            df = self.__deferreds.pop(request.response_to)
            if request.response_flags & REPLY_QUERY_FAILURE:
                doc = request.documents[0].decode()
                code = doc.get('code')
                msg = doc.get('$err', 'Unknown error')
                fail_conn = False
                if code == 13435:
                    err = errors.AutoReconnect(msg)
                    fail_conn = True
                else:
                    err = errors.OperationFailure(msg, code)
                df.errback(err)
                if fail_conn:
                    self.transport.loseConnection()
            else:
                df.callback(request)

    def fail(self, reason):
        if not isinstance(reason, failure.Failure):
            reason = failure.Failure(reason)
        log.err(reason)
        self.transport.loseConnection()

    @defer.inlineCallbacks
    def getlasterror(self, db):
        command = {'getlasterror': 1}
        db = '%s.$cmd' % db.split('.', 1)[0]
        uri = self.factory.uri
        if 'w' in uri['options']:
            command['w'] = int(uri['options']['w'])
        if 'wtimeoutms' in uri['options']:
            command['wtimeout'] = int(uri['options']['wtimeoutms'])
        if 'fsync' in uri['options']:
            command['fsync'] = bool(uri['options']['fsync'])
        if 'journal' in uri['options']:
            command['journal'] = bool(uri['options']['journal'])

        query = Query(collection=db, query=command)
        reply = yield self.send_QUERY(query)

        assert len(reply.documents) == 1

        document = reply.documents[0].decode()
        err = document.get('err', None)
        code = document.get('code', None)

        if err is not None:
            if code == 11000:
                raise errors.DuplicateKeyError(err, code=code)
            else:
                raise errors.OperationFailure(err, code=code)

        defer.returnValue(document)

class MongoDecoder:
    dataBuffer = None

    def __init__(self):
        self.dataBuffer = ''

    def feed(self, data):
        self.dataBuffer += data

    def next(self):
        if len(self.dataBuffer) < 16:
            return None
        msglen, = struct.unpack('<i', self.dataBuffer[:4])
        if len(self.dataBuffer) < msglen:
            return None
        if msglen < 16:
            raise errors.ConnectionFailure()
        msgdata = self.dataBuffer[:msglen]
        self.dataBuffer = self.dataBuffer[msglen:]
        return self.decode(msgdata)

    def decode(self, msgdata):
        msglen = len(msgdata)
        header = struct.unpack('<iiii', msgdata[:16])
        opcode = header[3]
        if opcode == OP_UPDATE:
            zero, = struct.unpack('<i', msgdata[16:20])
            if zero != 0:
                raise errors.ConnectionFailure()
            name = msgdata[20:].split('\x00', 1)[0]
            offset = 20 + len(name) + 1
            flags, = struct.unpack('<i', msgdata[offset:offset+4])
            offset += 4
            selectorlen, = struct.unpack('<i', msgdata[offset:offset+4])
            selector = bson.BSON(msgdata[offset:offset+selectorlen])
            offset += selectorlen
            updatelen, = struct.unpack('<i', msgdata[offset:offset+4])
            update = bson.BSON(msgdata[offset:offset+updatelen])
            return Update(*(header + (zero, name, flags, selector, update)))
        elif opcode == OP_INSERT:
            flags, = struct.unpack('<i', msgdata[16:20])
            name = msgdata[20:].split('\x00', 1)[0]
            offset = 20 + len(name) + 1
            docs = []
            while offset < len(msgdata):
                doclen, = struct.unpack('<i', msgdata[offset:offset+4])
                docdata = msgdata[offset:offset+doclen]
                doc = bson.BSON(docdata)
                docs.append(doc)
                offset += doclen
            return Insert(*(header + (flags, name, docs)))
        elif opcode == OP_QUERY:
            flags, = struct.unpack('<i', msgdata[16:20])
            name = msgdata[20:].split('\x00', 1)[0]
            offset = 20 + len(name) + 1
            ntoskip, ntoreturn = struct.unpack('<ii', msgdata[offset:offset+8])
            offset += 8
            querylen, = struct.unpack('<i', msgdata[offset:offset+4])
            querydata = msgdata[offset:offset+querylen]
            query = bson.BSON(querydata)
            offset += querylen
            fields = None
            if msglen > offset:
                fieldslen, = struct.unpack('<i', msgdata[offset:offset+4])
                fields = bson.BSON(msgdata[offset:offset+fieldslen])
            return Query(*(header + (flags, name, ntoskip, ntoreturn, query, fields)))
        elif opcode == OP_GETMORE:
            zero, = struct.unpack('<i', msgdata[16:20])
            if zero != 0:
                raise errors.ConnectionFailure()
            name = msgdata[20:].split('\x00', 1)[0]
            offset = 20 + len(name) + 1
            ntoreturn, cursorid = struct.unpack('<iq', msgdata[offset:offset+12])
            return Getmore(*(header + (zero, name, ntoreturn, cursorid)))
        elif opcode == OP_DELETE:
            zero, = struct.unpack('<i', msgdata[16:20])
            if zero != 0:
                raise errors.ConnectionFailure()
            name = msgdata[20:].split('\x00', 1)[0]
            offset = 20 + len(name) + 1
            flags, = struct.unpack('<i', msgdata[offset:offset+4])
            offset += 4
            selector = bson.BSON(msgdata[offset:])
            return Delete(*(header + (zero, name, flags, selector)))
        elif opcode == OP_KILL_CURSORS:
            cursors = struct.unpack('<ii', msgdata[16:24])
            if cursors[0] != 0:
                raise errors.ConnectionFailure()
            offset = 24
            cursor_list = []
            for i in xrange(cursors[1]):
                cursor, = struct.unpack('<q', msgdata[offset:offset+8])
                cursor_list.append(cursor)
                offset += 8
            return KillCursors(*(header + cursors + (cursor_list,)))
        elif opcode == OP_MSG:
            if msgdata[-1] != '\x00':
                raise errors.ConnectionFailure()
            return Msg(*(header + (msgdata[16:-1].decode('ascii'),)))
        elif opcode == OP_REPLY:
            reply = struct.unpack('<iqii', msgdata[16:36])
            docs = []
            offset = 36
            for i in xrange(reply[3]):
                doclen, = struct.unpack('<i', msgdata[offset:offset+4])
                if doclen > (msglen - offset):
                    raise errors.ConnectionFailure()
                docdata = msgdata[offset:offset+doclen]
                doc = bson.BSON(docdata)
                docs.append(doc)
                offset += doclen
            return Reply(*(header + reply + (docs,)))
        else:
            raise errors.ConnectionFailure()
        return header

########NEW FILE########
__FILENAME__ = errors
# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Exceptions raised by the :mod:`gridfs` package"""


class GridFSError(Exception):
    """Base class for all GridFS exceptions.

    .. versionadded:: 1.5
    """


class CorruptGridFile(GridFSError):
    """Raised when a file in :class:`~gridfs.GridFS` is malformed.
    """


class NoFile(GridFSError):
    """Raised when trying to read from a non-existent file.

    .. versionadded:: 1.6
    """


class UnsupportedAPI(GridFSError):
    """Raised when trying to use the old GridFS API.

    In version 1.6 of the PyMongo distribution there were backwards
    incompatible changes to the GridFS API. Upgrading shouldn't be
    difficult, but the old API is no longer supported (with no
    deprecation period). This exception will be raised when attempting
    to use unsupported constructs from the old API.

    .. versionadded:: 1.6
    """

########NEW FILE########
__FILENAME__ = grid_file
# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for representing files stored in GridFS."""

import datetime
import math
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from twisted.python import log
from twisted.internet import defer
from txmongo._gridfs.errors import (CorruptGridFile,
                                    NoFile,
                                    UnsupportedAPI)
from bson import Binary, ObjectId
from txmongo.collection import Collection

try:
    _SEEK_SET = os.SEEK_SET
    _SEEK_CUR = os.SEEK_CUR
    _SEEK_END = os.SEEK_END
except AttributeError:  # before 2.5
    _SEEK_SET = 0
    _SEEK_CUR = 1
    _SEEK_END = 2


"""Default chunk size, in bytes."""
DEFAULT_CHUNK_SIZE = 256 * 1024


def _create_property(field_name, docstring,
                      read_only=False, closed_only=False):
    """Helper for creating properties to read/write to files.
    """
    def getter(self):
        if closed_only and not self._closed:
            raise AttributeError("can only get %r on a closed file" %
                                 field_name)
        return self._file.get(field_name, None)

    def setter(self, value):
        if self._closed:
            raise AttributeError("cannot set %r on a closed file" %
                                 field_name)
        self._file[field_name] = value

    if read_only:
        docstring = docstring + "\n\nThis attribute is read-only."
    elif not closed_only:
        docstring = "%s\n\n%s" % (docstring, "This attribute can only be "
                                  "set before :meth:`close` has been called.")
    else:
        docstring = "%s\n\n%s" % (docstring, "This attribute is read-only and "
                                  "can only be read after :meth:`close` "
                                  "has been called.")

    if not read_only and not closed_only:
        return property(getter, setter, doc=docstring)
    return property(getter, doc=docstring)


class GridIn(object):
    """Class to write data to GridFS.
    """
    def __init__(self, root_collection, **kwargs):
        """Write a file to GridFS

        Application developers should generally not need to
        instantiate this class directly - instead see the methods
        provided by :class:`~gridfs.GridFS`.

        Raises :class:`TypeError` if `root_collection` is not an
        instance of :class:`~pymongo.collection.Collection`.

        Any of the file level options specified in the `GridFS Spec
        <http://dochub.mongodb.org/core/gridfsspec>`_ may be passed as
        keyword arguments. Any additional keyword arguments will be
        set as additional fields on the file document. Valid keyword
        arguments include:

          - ``"_id"``: unique ID for this file (default:
            :class:`~pymongo.objectid.ObjectId`)

          - ``"filename"``: human name for the file

          - ``"contentType"`` or ``"content_type"``: valid mime-type
            for the file

          - ``"chunkSize"`` or ``"chunk_size"``: size of each of the
            chunks, in bytes (default: 256 kb)

        :Parameters:
          - `root_collection`: root collection to write to
          - `**kwargs` (optional): file level options (see above)
        """
        if not isinstance(root_collection, Collection):
            raise TypeError("root_collection must be an instance of Collection")

        # Handle alternative naming
        if "content_type" in kwargs:
            kwargs["contentType"] = kwargs.pop("content_type")
        if "chunk_size" in kwargs:
            kwargs["chunkSize"] = kwargs.pop("chunk_size")

        # Defaults
        kwargs["_id"] = kwargs.get("_id", ObjectId())
        kwargs["chunkSize"] = kwargs.get("chunkSize", DEFAULT_CHUNK_SIZE)

        object.__setattr__(self, "_coll", root_collection)
        object.__setattr__(self, "_chunks", root_collection.chunks)
        object.__setattr__(self, "_file", kwargs)
        object.__setattr__(self, "_buffer", StringIO())
        object.__setattr__(self, "_position", 0)
        object.__setattr__(self, "_chunk_number", 0)
        object.__setattr__(self, "_closed", False)

    @property
    def closed(self):
        """Is this file closed?
        """
        return self._closed

    _id = _create_property("_id", "The ``'_id'`` value for this file.",
                            read_only=True)
    filename = _create_property("filename", "Name of this file.")
    content_type = _create_property("contentType", "Mime-type for this file.")
    length = _create_property("length", "Length (in bytes) of this file.",
                               closed_only=True)
    chunk_size = _create_property("chunkSize", "Chunk size for this file.",
                                   read_only=True)
    upload_date = _create_property("uploadDate",
                                    "Date that this file was uploaded.",
                                    closed_only=True)
    md5 = _create_property("md5", "MD5 of the contents of this file "
                            "(generated on the server).",
                            closed_only=True)

    def __getattr__(self, name):
        if name in self._file:
            return self._file[name]
        raise AttributeError("GridIn object has no attribute '%s'" % name)

    def __setattr__(self, name, value):
        if self._closed:
            raise AttributeError("cannot set %r on a closed file" % name)
        object.__setattr__(self, name, value)

    @defer.inlineCallbacks
    def __flush_data(self, data):
        """Flush `data` to a chunk.
        """
        if data:
            assert(len(data) <= self.chunk_size)
            chunk = {"files_id": self._file["_id"],
                     "n": self._chunk_number,
                     "data": Binary(data)}

            # Continue writing after the insert completes (non-blocking)
            yield self._chunks.insert(chunk)
            self._chunk_number += 1
            self._position += len(data)

    @defer.inlineCallbacks
    def __flush_buffer(self):
        """Flush the buffer contents out to a chunk.
        """
        yield self.__flush_data(self._buffer.getvalue())
        self._buffer.close()
        self._buffer = StringIO()

    @defer.inlineCallbacks
    def __flush(self):
        """Flush the file to the database.
        """
        yield self.__flush_buffer()

        md5 = yield self._coll.filemd5(self._id)

        self._file["md5"] = md5
        self._file["length"] = self._position
        self._file["uploadDate"] = datetime.datetime.utcnow()
        yield self._coll.files.insert(self._file)

    @defer.inlineCallbacks
    def close(self):
        """Flush the file and close it.

        A closed file cannot be written any more. Calling
        :meth:`close` more than once is allowed.
        """
        if not self._closed:
            yield self.__flush()
            self._closed = True

    @defer.inlineCallbacks
    def write(self, data):
        """Write data to the file. There is no return value.

        `data` can be either a string of bytes or a file-like object
        (implementing :meth:`read`).

        Due to buffering, the data may not actually be written to the
        database until the :meth:`close` method is called. Raises
        :class:`ValueError` if this file is already closed. Raises
        :class:`TypeError` if `data` is not an instance of
        :class:`str` or a file-like object.

        :Parameters:
          - `data`: string of bytes or file-like object to be written
            to the file
        """
        if self._closed:
            raise ValueError("cannot write to a closed file")

        try:
            # file-like
            read = data.read
        except AttributeError:
            # string
            if not isinstance(data, basestring):
                raise TypeError("can only write strings or file-like objects")
            if isinstance(data, unicode):
                try:
                    data = data.encode(self.encoding)
                except AttributeError:
                    raise TypeError("must specify an encoding for file in "
                                    "order to write %s" % (text_type.__name__,))
            read = StringIO(data).read
        
        if self._buffer.tell() > 0:
            # Make sure to flush only when _buffer is complete
            space = self.chunk_size - self._buffer.tell()
            if space:
                to_write = read(space)
                self._buffer.write(to_write)
                if len(to_write) < space:
                    return # EOF or incomplete
            yield self.__flush_buffer()
        to_write = read(self.chunk_size)
        while to_write and len(to_write) == self.chunk_size:
            yield self.__flush_data(to_write)
            to_write = read(self.chunk_size)
        self._buffer.write(to_write)

    @defer.inlineCallbacks
    def writelines(self, sequence):
        """Write a sequence of strings to the file.

        Does not add separators.
        """
        for line in sequence:
            yield self.write(line)

    def __enter__(self):
        """Support for the context manager protocol.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for the context manager protocol.

        Close the file and allow exceptions to propogate.
        """
        self.close()
        return False  # untrue will propogate exceptions


class GridOut(object):
    """Class to read data out of GridFS.
    """
    def __init__(self, root_collection, doc):
        """Read a file from GridFS

        Application developers should generally not need to
        instantiate this class directly - instead see the methods
        provided by :class:`~gridfs.GridFS`.

        Raises :class:`TypeError` if `root_collection` is not an instance of
        :class:`~pymongo.collection.Collection`.

        :Parameters:
          - `root_collection`: root collection to read from
          - `file_id`: value of ``"_id"`` for the file to read
        """
        if not isinstance(root_collection, Collection):
            raise TypeError("root_collection must be an instance of Collection")

        self.__chunks = root_collection.chunks
        self._file = doc
        self.__current_chunk = -1
        self.__buffer = ''
        self.__position = 0

    _id = _create_property("_id", "The ``'_id'`` value for this file.", True)
    name = _create_property("filename", "Name of this file.", True)
    content_type = _create_property("contentType", "Mime-type for this file.",
                                     True)
    length = _create_property("length", "Length (in bytes) of this file.",
                               True)
    chunk_size = _create_property("chunkSize", "Chunk size for this file.",
                                   True)
    upload_date = _create_property("uploadDate",
                                    "Date that this file was first uploaded.",
                                    True)
    aliases = _create_property("aliases", "List of aliases for this file.",
                                True)
    metadata = _create_property("metadata", "Metadata attached to this file.",
                                 True)
    md5 = _create_property("md5", "MD5 of the contents of this file "
                            "(generated on the server).", True)

    def __getattr__(self, name):
        if name in self._file:
            return self._file[name]
        raise AttributeError("GridOut object has no attribute '%s'" % name)

    @defer.inlineCallbacks
    def read(self, size=-1):
        """Read at most `size` bytes from the file (less if there
        isn't enough data).

        The bytes are returned as an instance of :class:`str`. If
        `size` is negative or omitted all data is read.

        :Parameters:
          - `size` (optional): the number of bytes to read
        """
        if size:
            remainder = int(self.length) - self.__position
            if size < 0 or size > remainder:
                size = remainder

            data = self.__buffer
            chunk_number = (len(data) + self.__position) / self.chunk_size

            while len(data) < size:
                chunk = yield self.__chunks.find_one({"files_id": self._id,
                                                      "n": chunk_number})
                if not chunk:
                    raise CorruptGridFile("no chunk #%d" % chunk_number)

                if not data:
                    data += chunk["data"][self.__position % self.chunk_size:]
                else:
                    data += chunk["data"]

                chunk_number += 1

            self.__position += size
            to_return = data[:size]
            self.__buffer = data[size:]
            defer.returnValue(to_return)

    def tell(self):
        """Return the current position of this file.
        """
        return self.__position

    def seek(self, pos, whence=_SEEK_SET):
        """Set the current position of this file.

        :Parameters:
         - `pos`: the position (or offset if using relative
           positioning) to seek to
         - `whence` (optional): where to seek
           from. :attr:`os.SEEK_SET` (``0``) for absolute file
           positioning, :attr:`os.SEEK_CUR` (``1``) to seek relative
           to the current position, :attr:`os.SEEK_END` (``2``) to
           seek relative to the file's end.
        """
        if whence == _SEEK_SET:
            new_pos = pos
        elif whence == _SEEK_CUR:
            new_pos = self.__position + pos
        elif whence == _SEEK_END:
            new_pos = int(self.length) + pos
        else:
            raise IOError(22, "Invalid value for `whence`")

        if new_pos < 0:
            raise IOError(22, "Invalid value for `pos` - must be positive")

        self.__position = new_pos

    def close(self):
        self.__buffer = ''
        self.__current_chunk = -1

    def __iter__(self):
        """Deprecated."""
        raise UnsupportedAPI("Iterating is deprecated for iterated reading")

    def __repr__(self):
        return str(self._file)


class GridOutIterator(object):
    def __init__(self, grid_out, chunks):
        self.__id = grid_out._id
        self.__chunks = chunks
        self.__current_chunk = 0
        self.__max_chunk = math.ceil(float(grid_out.length) /
                                     grid_out.chunk_size)

    def __iter__(self):
        return self

    @defer.inlineCallbacks
    def next(self):
        if self.__current_chunk >= self.__max_chunk:
            raise StopIteration
        chunk = yield self.__chunks.find_one({"files_id": self.__id,
                                        "n": self.__current_chunk})
        if not chunk:
            raise CorruptGridFile("no chunk #%d" % self.__current_chunk)
        self.__current_chunk += 1
        defer.returnValue(str(chunk["data"]))


class GridFile(object):
    """No longer supported.

    .. versionchanged:: 1.6
       The GridFile class is no longer supported.
    """
    def __init__(self, *args, **kwargs):
        raise UnsupportedAPI("The GridFile class is no longer supported. "
                             "Please use GridIn or GridOut instead.")

########NEW FILE########
