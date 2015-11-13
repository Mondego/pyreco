__FILENAME__ = model
import ming
from ming.datastore import DataStore
from datetime import datetime

ds = DataStore('mongodb://localhost:27017', database='tutorial')
sess = ming.Session(ds)

Forum = ming.collection(
    'forum.forum', sess, 
    ming.Field('_id', ming.schema.ObjectId),
    ming.Field('name', str),
    ming.Field('description', str),
    ming.Field('created', datetime, if_missing=datetime.utcnow),
    ming.Field('last_post', dict(
        when=datetime,
        user=str,
        subject=str)),
    ming.Field('num_threads', int),
    ming.Field('num_posts', int))

Thread = ming.collection(
    'forum.thread', sess,
    ming.Field('_id', ming.schema.ObjectId),
    ming.Field(
        'forum_id', ming.schema.ObjectId(if_missing=None),
        index=True),
    ming.Field('subject', str),
    ming.Field('last_post', dict(
        when=datetime,
        user=str,
        subject=str)),
    ming.Field('num_posts', int))

Post = ming.collection(
    'forum.post', sess,
    ming.Field('_id', ming.schema.ObjectId),
    ming.Field('subject', str),
    ming.Field('forum_id', ming.schema.ObjectId(if_missing=None)),
    ming.Field('thread_id', ming.schema.ObjectId(if_missing=None)),
    ming.Field('parent_id', ming.schema.ObjectId(if_missing=None)),
    ming.Field('timestamp', datetime, if_missing=datetime.utcnow),
    ming.Field('slug', str),
    ming.Field('fullslug', str, unique=True),
    ming.Index([('forum_id', 1), ('thread_id', 1)]),
    ming.Index('slug', unique=True))

# Create hierarchy
Product = ming.collection(
    'product', sess,
    ming.Field('_id', str), # sku
    ming.Field('category', str, if_missing='product'),
    ming.Field('name', str),
    ming.Field('price', int), # in cents
    polymorphic_on='category',
    polymorphic_identity='base')
    
Shirt = ming.collection(
    Product, 
    ming.Field('category', str, if_missing='shirt'),
    ming.Field('size', str),
    polymorphic_identity='shirt')
    
Film = ming.collection(
    Product,
    ming.Field('category', str, if_missing='film'),
    ming.Field('genre', str),
    polymorphic_identity='film')

########NEW FILE########
__FILENAME__ = migrations_a
def content():

    from flyway import Migration

    class Version0(Migration):
        version = 0

        def up(self):
            collection = self.session.db['forum.forum']
            for doc in collection.find():
                doc['metadata'] = dict(
                    name=doc.pop('name'),
                    description=doc.pop('description'),
                    created=doc.pop('created'))
                collection.save(doc)

        def down(self):
            collection = self.session.db['forum.forum']
            for doc in collection.find():
                metadata = doc.pop('metadata')
                doc.update(
                    name=metadata['name'],
                    description=metadata['description'],
                    created=metadata['created'])
                collection.save(doc)

content()    

########NEW FILE########
__FILENAME__ = migrations_b
def content():
    from flyway import Migration

    class Version0(Migration):
        version=0
        def up(self):
            pass
        def down(self):
            pass
        def up_requires(self):
            yield ('a', self.version)
            for req in Migration.up_requires(self):
                yield req
        def down_requires(self):
            yield ('a', self.version)
            for req in Migration.down_requires(self):
                yield req

content()

########NEW FILE########
__FILENAME__ = model
from datetime import datetime

import ming

from lesson_2_0 import model as M20

sess = M20.sess

def migrate_forum(doc):
    metadata = dict(
        name=doc.pop('name'),
        description=doc.pop('description'),
        created=doc.pop('created'))
    return dict(doc, metadata=metadata)

Forum = ming.collection(
    'forum.forum', sess, 
    ming.Field('_id', ming.schema.ObjectId),
    ming.Field('name', str),
    ming.Field('description', str),
    ming.Field('created', datetime, if_missing=datetime.utcnow),
    ming.Field('last_post', dict(
        when=datetime,
        user=str,
        subject=str)),
    ming.Field('num_threads', int),
    ming.Field('num_posts', int),
    version_of=M20.Forum,
    migrate=migrate_forum)

# Clear the database and put an 'old' forum document in
M20.Forum.m.remove()
M20.Forum.make(dict(name='My Forum')).m.insert()

def migrate_forum(doc):
    metadata = dict(
        name=doc.pop('name'),
        description=doc.pop('description'),
        created=doc.pop('created'))
    return dict(doc, metadata=metadata, version=2)

Forum = ming.collection(
    'forum.forum', sess, 
    ming.Field('_id', ming.schema.ObjectId),
    ming.Field('metadata', dict(
            name=str,
            description=str,
            created=ming.schema.DateTime(if_missing=datetime.utcnow))),
    ming.Field('last_post', dict(
            when=datetime,
            user=str,
            subject=str)),
    ming.Field('num_threads', int),
    ming.Field('num_posts', int),
    ming.Field('schema_version', ming.schema.Value(2, required=True)),
    version_of=M20.Forum,
    migrate=migrate_forum)

########NEW FILE########
__FILENAME__ = model
import ming
from ming import fs

from lesson_2_0 import model as M20

sess = M20.sess

Attachment = fs.filesystem(
    'forum.attachment', sess)

Attachment = fs.filesystem(
    'forum.attachment', sess,
    ming.Field('author', str))
    
Attachment = fs.filesystem(
    'forum.attachment', sess,
    ming.Field('metadata', dict(
            author=str)))
    

########NEW FILE########
__FILENAME__ = model
from ming.odm import ThreadLocalODMSession, Mapper
from ming.odm import ForeignIdProperty, RelationProperty

from lesson_2_0 import model as M

sess = ThreadLocalODMSession(M.sess)

class Forum(object):
    pass

class Thread(object):
    pass

class Post(object):
    pass

sess.mapper(Forum, M.Forum, properties=dict(
        threads=RelationProperty('Thread')))
sess.mapper(Thread, M.Thread, properties=dict(
        forum_id=ForeignIdProperty('Forum'),
        forum=RelationProperty('Forum'),
        posts=RelationProperty('Post')))
sess.mapper(Post, M.Post, properties=dict(
        forum_id=ForeignIdProperty('Forum'),
        thread_id=ForeignIdProperty('Thread'),
        forum=RelationProperty('Forum'),
        thread=RelationProperty('Thread')))

Mapper.compile_all()

class Product(object):
    pass

class Shirt(Product):
    pass

class Film(Product):
    pass

sess.mapper(Product, M.Product,
            polymorphic_on='category',
            polymorphic_identity='base')
sess.mapper(Shirt, M.Shirt,
            polymorphic_identity='shirt')
sess.mapper(Film, M.Film,
            polymorphic_identity='film')

Mapper.compile_all()

########NEW FILE########
__FILENAME__ = geo_examples
# Simple examples of doing various Geo queries using pymongo.
#
# Created for Where2.0 2011 Working with Geo data in MongoDB.
# Bernie Hackett <bernie@10gen.com>
#
import math

import bson
import pymongo

# Approximate radius of Earth according to Google calculator
RADIUS_MILES = 3963
# Very rough scale multiplier for distance on Earth.
# For standard $near queries. Spherical queries just use radius.
DISTANCE_MULTIPLIER = RADIUS_MILES * (math.pi / 180)

# Connect to mongod
connection = pymongo.Connection()

# Some examples require a newer mongod versions...
version_string = (connection.server_info()['version'])[:3]
version = tuple([int(num) for num in version_string.split('.')])

def bart_foreign_cinema(num_stops=1):
    """Find the BART station(s) closest to the Foreign Cinema
    in San Francisco.

    :Parameters:
        - `num_stops`: How many stations to list.
    """
    db = connection.bart
    cursor = db.stops.find(
            {'stop_geo': {'$near': [-122.419088, 37.75689]}}).limit(num_stops)
    for doc in cursor:
        print doc['stop_name']

# Using geoNear we can get an approximte or spherical
# distance and scale it to our needs
def bart_foreign_cinema_geonear(spherical=False):
    """How far away is the closest BART station to the
    Foreign Cinema in San Francisco.

    :Parameters:
        - `spherical`: Should we do a spherical query?
    """
    db = connection.bart
    if spherical:
        mult = RADIUS_MILES
    else:
        mult = DISTANCE_MULTIPLIER
    q = bson.son.SON({'geoNear': 'stops'})
    q.update({'near': [-122.419088, 37.75689]})
    q.update({'distanceMultiplier': mult})
    if spherical:
        q.update({'spherical': True})
    results = db.command(q)
    name = results['results'][0]['obj']['stop_name']
    dist = results['results'][0]['dis']
    print "Distance to %s: %r miles" % (name, dist)

map_func = "function(){ emit(this.state, this.pop); }"
reduce_func = "function(key, values){ return Array.sum(values); }"

# Calculate the entire population of the zipcode dataset.
# Inline map reduce just returns the result set instead
# of storing it in the database.
def calculate_population():
    """Use inline map reduce to calculate the entire
    population from the zips dataset.
    """
    if version < (1, 8):
        print "inline map reduce requires mongod >= 1.8"
    db = connection.geo
    print sum([res['value']
              for res
              in db.zips.inline_map_reduce(map_func, reduce_func)])

# How many people live within 100 miles of the
# Empire State Building (based on our dataset)?

range_in_miles = 100.0
max_distance = range_in_miles / DISTANCE_MULTIPLIER
nearq = bson.son.SON({'$near': [-73.985656, 40.748433]})
nearq.update({'$maxDistance': max_distance})
# Standard $near queries are limited to a result set of 100 documents.
# We use $within to get around that limitation.
withinq = {'$within': {'$center': [[-73.985656, 40.748433], max_distance]}}

def empire_state_find():
    """How many people live within 100 miles of the Empire State Building
    (according to our dataset). This calculates the answer twice. Once
    with $within, once with $near.
    """
    db = connection.geo
    # We only really care about the 'pop' field in the result documents.
    # The second parameter of find() tells mongod what fields to return
    # to us. MongoDB always returns '_id' unless you tell it not to.
    cursor = db.zips.find({'loc': withinq}, {'pop': True, '_id': False})
    print '$within: %d' % (sum([doc['pop'] for doc in cursor]),)
    cursor = db.zips.find({'loc': nearq},
                          {'pop': True, '_id': False}).limit(60000)
    print '$near: %d' % (sum([doc['pop'] for doc in cursor]),)

def empire_state_spherical():
    """How many people live within 100 miles of the Empire State Building
    (according to our dataset). This calculates the answer using $nearSphere
    so the distance calulation should be accurate.
    """
    db = connection.geo
    q = bson.son.SON({'$nearSphere': [-73.985656, 40.748433]})
    q.update({'$maxDistance': 100.0 / 3963})
    cursor = db.zips.find({'loc': q}).limit(60000)
    print '$nearSphere: %d' % (sum([doc['pop'] for doc in cursor]),)

# Using map/reduce or group with GEO queries requires MongoDB 1.9.
# ----------------------------------------------------------------------------
# Same result using map/reduce.
def empire_state_map_reduce():
    """Same $within query from above using map/reduce.
    """
    if version < (1, 9):
        print "map/reduce with geo requires mongod >= 1.9"
    else:
        db = connection.geo
        result = db.zips.inline_map_reduce(map_func,
                                           reduce_func,
                                           query={'loc': withinq})
        print sum([doc['value'] for doc in result])

# Same result using group.
def empire_state_group():
    """Same $within query again using group.
    """
    if version < (1, 9):
        print "group with geo requires mongod >= 1.9"
    else:
        db = connection.geo
        pop_reduce = "function(obj, prev){ prev.sum += obj.pop; }"
        result = db.zips.group(['state'], {'loc': withinq}, {'sum': 0}, pop_reduce)
        print sum([doc['sum'] for doc in result])
# ----------------------------------------------------------------------------


########NEW FILE########
__FILENAME__ = geo_index_data
#!/usr/bin/python
#
# GeoIndexer for MongoDB Where2.0 Datasets
#
# Original script by:
# Brendan W. McAdams <bmcadams@evilmonkeylabs.com>
#
# Quick and dirty script which creates Geo Indices in MongoDB.
#
# Assumes you already loaded it with the provided shell script.
# 
# Needs PyMongo 1.6 or greater

import pymongo
from pymongo import Connection

connection = Connection()
db = connection['bart']
print "Indexing the Stops Data."
for row in db.stops.find():
    row['stop_geo'] = [row['stop_lon'], row['stop_lat']]
    db.stops.save(row)

db.stops.ensure_index([('stop_geo', pymongo.GEO2D)])
print "Reindexed stops with Geospatial data."

print "Indexing the Shapes data"
for row in db.shapes.find():
    row['shape_pt_geo'] = {'lon': row['shape_pt_lon'], 'lat': row['shape_pt_lat']}
    db.shapes.save(row)

db.shapes.ensure_index([('shape_pt_geo', pymongo.GEO2D)])
print "Reindexed shapes with Geospatial data."

db = connection['geo']
print "Indexing the Zips Data."
for row in db.zips.find():
    row['loc'] = [-(row['loc']['x']), row['loc']['y']]
    db.zips.save(row)

db.zips.ensure_index([('loc', pymongo.GEO2D)])
print "Reindexed zips with Geospatial data."

print "Done."

########NEW FILE########
