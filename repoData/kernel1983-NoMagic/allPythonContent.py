__FILENAME__ = migration
import sys
import pickle
import uuid
import binascii
import json
import zlib

sys.path.append("..")

from setting import settings
from setting import conn
from setting import ring

import nomagic
from nomagic import _RING

_NUMBER = len(ring)

def _number(key): return int(key, 16) % _NUMBER

def _node(key): return ring[_RING.get_node(key)]


for r in ring:
    offset = 0
    ids_to_delete = []
    while True:
        users = r.query("SELECT * FROM entities ORDER BY auto_increment LIMIT %s, 100", offset)

        if len(users) == 0:
            break

        for user in users:
            user_id = str(user["id"])
            print user["id"], _number(user_id), nomagic._RING.get_node(user_id)
            if r is not _node(user_id):
                _node(user_id).execute_rowcount("INSERT INTO entities (id, body) VALUES (%s, %s)", user["id"], user["body"])
                ids_to_delete.append(user_id)

        offset += 100

    for id_to_delete in ids_to_delete:
        print r.execute_rowcount("DELETE FROM entities WHERE id = %s", id_to_delete)

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import datetime
import pickle
import uuid
import binascii

import zlib
#import gzip
import hashlib
import json
import random
import string

import __init__ as nomagic

from setting import conn


def create_user(user):
    email = user["email"]
    login = conn.get("SELECT * FROM index_login WHERE login = %s", email)
    assert not login

    user["type"] = "user"
    user["name"] = user.get("name", "")
    user["salt"] = "".join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
    user["password"] = hashlib.sha1(user["password"] + user["salt"]).hexdigest()
    user["title"] = ""
    user["department"] = ""
    user["locatiion"] = ""
    user["mobile"] = ""
    user["tel"] = ""
    user["about"] = ""
    user["profile_img"] = ""
    user["datetime"] = datetime.datetime.now().isoformat()

    new_id = nomagic._new_key()
    rowcount = nomagic._node(new_id).execute_rowcount("INSERT INTO entities (id, body) VALUES(%s, %s)", new_id, nomagic._pack(user))
    assert rowcount

    #update indexes: email
    assert "@" in email
    rowcount = conn.execute_rowcount("INSERT INTO index_login (login, entity_id) VALUES(%s, %s)", email, new_id)
    assert rowcount

    return (new_id, user)

def update_user(user_id, data):
    #valid name
    user = nomagic._get_entity_by_id(user_id)
    user_json1 = nomagic._pack(user)
    result = {}

    if "password0" in data and "password1" in data and data["password0"] != data["password1"] and data["password1"] != "":
        #normal update password with old password0 and new password1
        if user["password"] == hashlib.sha1(data["password0"] + user.get("salt", "")).hexdigest():
            user["password"] = hashlib.sha1(data["password1"] + user.get("salt", "")).hexdigest()
            result["password_updated"] = True
        del data["password0"]
        del data["password1"]

    elif "password" in data and data["password"] != "":
        #force update password
        user["password"] = hashlib.sha1(data["password"] + user.get("salt", "")).hexdigest()
        result["password_updated"] = True
        del data["password"]

    if user:
        user.update(data)
        user_json2 = nomagic._pack(user)
        if user_json1 != user_json2:
            assert nomagic._node(user_id).execute_rowcount("UPDATE entities SET body = %s WHERE id = %s", nomagic._pack(user), nomagic._key(user_id))
    return result

def check_user(login, password):
    login_info = conn.get("SELECT entity_id FROM index_login WHERE login = %s", login)
    if login_info:
        user_id = login_info["entity_id"]
        user = nomagic._get_entity_by_id(user_id)
        if user["password"] == hashlib.sha1(password + user.get("salt", "")).hexdigest():
            return (user_id, user)
    return (None, None)

def get_user_by_login(login):
    index_login = conn.get("SELECT * FROM index_login WHERE login = %s", login)
    entity_id = index_login["entity_id"]

    return nomagic._get_entity_by_id(entity_id)

def get_user_id_by_login(login):
    index_login = conn.get("SELECT * FROM index_login WHERE login = %s", login)
    return index_login["entity_id"] if index_login else None

def email_invite(email):
    """email invite can be used for both self signup and inviting friends to join"""
    # valid email, existing in system?
    # insert into index_invite table
    token = uuid.uuid4().hex
    rowcount = conn.execute_rowcount("INSERT INTO index_invite (email, token) VALUES(%s, %s)", email, token)
    assert rowcount
    # resend? signup? invite?
    return token


########NEW FILE########
__FILENAME__ = connection
#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import datetime
import pickle
import uuid
import binascii

import zlib
import hashlib
import json
import random
import string

import __init__ as nomagic

from setting import conn


def connect_index_and_entity(table_index, index_name, index_connection_name, entity_id, entity_connection_name):
    index = conn.get("SELECT * FROM %s WHERE name = %s" % (table_index, "%s"), index_name)
    index_data = nomagic._unpack(index["data"] or "{}")
    index_connection = set(index_data.get(index_connection_name, []))
    if entity_id not in index_connection:
        index_connection.add(entity_id)
        index_data[index_connection_name] = list(index_connection)
        index_data_updated = nomagic._pack(index_data)
        conn.execute("UPDATE %s SET data = %s WHERE name = %s" % (table_index, "%s", "%s"), index_data_updated, index_name)

    entity = nomagic._get_entity_by_id(entity_id)
    entity_connection = set(entity.get(entity_connection_name, []))
    if index_name not in entity_connection:
        entity_connection.add(index_name)
        entity[entity_connection_name] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id, entity)


def disconnect_index_and_entity(table_index, index_name, index_connection_name, entity_id, entity_connection_name):
    index = conn.get("SELECT * FROM %s WHERE name = %s" % (table_index, "%s"), index_name)
    index_data = nomagic._unpack(index["data"] or "{}")
    index_connection = set(index_data.get(index_connection_name, []))
    if entity_id in index_connection:
        index_connection.remove(entity_id)
        index_data[index_connection_name] = list(index_connection)
        index_data_updated = nomagic._pack(index_data)
        conn.execute("UPDATE %s SET data = %s WHERE name = %s" % (table_index, "%s", "%s"), index_data_updated, index_name)

    entity = nomagic._get_entity_by_id(entity_id)
    entity_connection = set(entity.get(entity_connection_name, []))
    if index_name in entity_connection:
        entity_connection.remove(index_name)
        entity[entity_connection_name] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id, entity)


def connect_entities(entity_id1, entity_connection_name1, entity_id2, entity_connection_name2):
    entity1, entity2 = nomagic._get_entities_by_ids([entity_id1, entity_id2])
    entity_data1, entity_data2 = entity1[1], entity2[1]

    entity_connection = set(entity_data1.get(entity_connection_name1, []))
    if entity_id2 not in entity_connection:
        entity_connection.add(entity_id2)
        entity_data1[entity_connection_name1] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id1, entity_data1)

    entity_connection = set(entity_data2.get(entity_connection_name2, []))
    if entity_id1 not in entity_connection:
        entity_connection.add(entity_id1)
        entity_data2[entity_connection_name2] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id2, entity_data2)


def disconnect_entities(entity_id1, entity_connection_name1, entity_id2, entity_connection_name2):
    entity1, entity2 = nomagic._get_entities_by_ids([entity_id1, entity_id2])
    entity_data1, entity_data2 = entity1[1], entity2[1]

    entity_connection = set(entity_data1.get(entity_connection_name1, []))
    if entity_id2 in entity_connection:
        entity_connection.remove(entity_id2)
        entity_data1[entity_connection_name1] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id1, entity_data1)

    entity_connection = set(entity_data2.get(entity_connection_name2, []))
    if entity_id1 in entity_connection:
        entity_connection.remove(entity_id1)
        entity_data2[entity_connection_name2] = list(entity_connection)
        nomagic._update_entity_by_id(entity_id2, entity_data2)

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = feeds
#!/usr/bin/env python
# -*- coding: utf8 -*-

import time
import datetime
import pickle
import uuid
import binascii
import json
import zlib
#import gzip
import hashlib
import random
import string

import __init__ as nomagic

from setting import conn


def email_invite(email):
    """email invite can be used for both self signup and inviting friends to join"""
    # valid email, existing in system?
    # insert into index_invite table
    token = uuid.uuid4().hex
    assert conn.execute_rowcount("INSERT INTO index_invite (email, token) VALUES(%s, %s)", email, token)
    # resend? signup? invite?
    return token

def follow_users(user_id, friend_ids):
    user = nomagic._get_entity_by_id(user_id)
    following = user.get("following", [])
    suggested_friend_ids = user.get("suggested_friend_ids", [])
    changed = False
    for friend_id in friend_ids:
        if friend_id not in following:
            friend = nomagic._get_entity_by_id(friend_id)
            followed = friend.get("followed", [])
            if user_id not in followed:
                followed.append(user_id)
                friend["followed"] = followed
            update_user(friend_id, friend)
            following.append(friend_id)
            changed = True

        if friend_id in suggested_friend_ids:
            suggested_friend_ids.remove(friend_id)
            changed = True

    if changed:
        user["following"] = following
        user["suggested_friend_ids"] = suggested_friend_ids
        update_user(user_id, user)
    #followed = user.get("followed", [])

def unfollow_users(user_id, friend_ids):
    user = nomagic._get_entity_by_id(user_id)
    following = user.get("following", [])
    for friend_id in friend_ids:
        if friend_id in following:
            friend = nomagic._get_entity_by_id(friend_id)
            followed = friend.get("followed", [])
            if user_id in followed:
                followed.remove(user_id)
                friend["followed"] = followed

                update_user(friend_id, friend)
            following.remove(friend_id)

    user["following"] = following
    update_user(user_id, user)


def new_status(user_id, data):
    now = datetime.datetime.now()
    data["type"] = "status"
    data["user_id"] = user_id
    data["datetime"] = now.isoformat()
    data["likes"] = []
    data["comment_ids"] = []
    assert data.get("content")

    new_id = nomagic._new_key()
    assert nomagic._node(new_id).execute_rowcount("INSERT INTO entities (id, body) VALUES(%s, %s)", new_id, nomagic._pack(data))

    user = nomagic._get_entity_by_id(user_id)
    activity = user.get("activity", [])
    activity.append(new_id)
    user["activity"] = activity
    nomagic._update_entity_by_id(user_id, user)

    data["user"] = user
    data["like_count"] = 0
    data["like"] = False
    data["comment_count"] = 0

    assert conn.execute_rowcount("INSERT INTO index_posts (user_id, entity_id) VALUES(%s, %s)", user_id, new_id)
    return new_id, data


def get_public_news_feed(activity_offset=10, activity_start_id=None):
    if activity_start_id:
        pass
    else:
        posts = conn.query("SELECT * FROM index_posts ORDER BY id DESC LIMIT 0, %s", activity_offset)
    activity_ids = [i["entity_id"] for i in posts]

    if posts:
        activities = [dict(activity, id=activity_id)
                        for activity_id, activity in nomagic._get_entities_by_ids(activity_ids)]
        return [dict(activity,
                     like_count = len(activity.get("likes", [])),
                     comment_count = len(activity.get("comment_ids", [])),
                     ) for activity in activities]
    return []

def get_news_by_id(activity_id):
    activity = nomagic._get_entity_by_id(activity_id)
    activity["id"] = activity_id
    comments, user_ids = get_comments(activity)

    return dict(activity,
                id = activity_id,
                like_count = len(activity.get("likes", [])),
                comment_count = 0, #len(activity.get("comment_ids", [])),
                comments = comments), user_ids


def new_comment(user_id, entity_id, data):
    data["type"] = "comment"
    data["likes"] = []
    data["user_id"] = user_id
    data["activity_id"] = entity_id
    data["datetime"] = datetime.datetime.now().isoformat()
    data["comment_ids"] = []
    #content valid
    assert data.get("content")

    new_comment_id = nomagic._new_key()
    assert nomagic._node(new_comment_id).execute_rowcount("INSERT INTO entities (id, body) VALUES(%s, %s)", new_comment_id, nomagic._pack(data))

    entity = nomagic._get_entity_by_id(entity_id)
    comment_ids = entity.get("comment_ids", [])
    comment_ids.append(new_comment_id)
    entity["comment_ids"] = comment_ids
    nomagic._update_entity_by_id(entity_id, entity)

    return comment_ids, dict(data, id=new_comment_id, like_count=0, like=False, user=nomagic._get_entity_by_id(user_id))


def get_comments(entity, user_ids = set()):
    assert "comment_ids" in entity
    assert "comments" not in entity
    entity_comments = entity.get("comments", [])
    for comment_id, comment in nomagic._get_entities_by_ids(entity.get("comment_ids", [])):
        comment["id"] = comment_id
        comment["like_count"] = len(comment.get("likes", [])),
        comment["comment_count"] = 0, #len(activity.get("comment_ids", [])),
        user_ids.add(comment["user_id"])
        if comment.get("comment_ids"):
            get_comments(comment, user_ids)
        entity_comments.append(comment)

    entity["comments"] = entity_comments
    return entity_comments, user_ids

def like(user_id, entity_id):
    entity = nomagic._get_entity_by_id(entity_id)
    likes = entity.get("likes", [])
    if user_id not in likes:
        likes.append(user_id)
        entity["likes"] = likes
        nomagic._update_entity_by_id(entity_id, entity)
    return likes

def unlike(user_id, entity_id):
    entity = nomagic._get_entity_by_id(entity_id)
    likes = entity.get("likes", [])
    if user_id in likes:
        likes.remove(user_id)
        entity["likes"] = likes
        nomagic._update_entity_by_id(entity_id, entity)
    return likes

########NEW FILE########
__FILENAME__ = friends
#!/usr/bin/env python
# -*- coding: utf8 -*-

import __init__ as nomagic

from setting import conn
import auth

def follow_users(user_id, friend_ids):
    user = nomagic._get_entity_by_id(user_id)
    following = user.get("following", [])
    suggested_friend_ids = user.get("suggested_friend_ids", [])
    changed = False
    for friend_id in friend_ids:
        if friend_id not in following:
            friend = nomagic._get_entity_by_id(friend_id)
            followed = friend.get("followed", [])
            if user_id not in followed:
                followed.append(user_id)
                friend["followed"] = followed
            auth.update_user(friend_id, friend)
            following.append(friend_id)
            changed = True

        if friend_id in suggested_friend_ids:
            suggested_friend_ids.remove(friend_id)
            changed = True

    if changed:
        user["following"] = following
        user["suggested_friend_ids"] = suggested_friend_ids
        auth.update_user(user_id, user)
    #followed = user.get("followed", [])


def unfollow_users(user_id, friend_ids):
    user = nomagic._get_entity_by_id(user_id)
    following = user.get("following", [])
    for friend_id in friend_ids:
        if friend_id in following:
            friend = nomagic._get_entity_by_id(friend_id)
            followed = friend.get("followed", [])
            if user_id in followed:
                followed.remove(user_id)
                friend["followed"] = followed

                auth.update_user(friend_id, friend)
            following.remove(friend_id)

    user["following"] = following
    auth.update_user(user_id, user)


def get_friends(user_ids):
    result = []
    for friend_id, friend in nomagic._get_entities_by_ids(user_ids):
        if "password" in friend:
            del friend["password"]
        if "salt" in friend:
            del friend["salt"]
        result.append(dict(friend, user_id=friend_id))

    return result

########NEW FILE########
__FILENAME__ = hash_ring
# -*- coding: utf-8 -*-
"""
    hash_ring
    ~~~~~~~~~~~~~~
    Implements consistent hashing that can be used when
    the number of server nodes can increase or decrease (like in memcached).

    Consistent hashing is a scheme that provides a hash table functionality
    in a way that the adding or removing of one slot
    does not significantly change the mapping of keys to slots.

    More information about consistent hashing can be read in these articles:

        "Web Caching with Consistent Hashing":
            http://www8.org/w8-papers/2a-webserver/caching/paper2.html

        "Consistent hashing and random trees:
        Distributed caching protocols for relieving hot spots on the World Wide Web (1997)":
            http://citeseerx.ist.psu.edu/legacymapper?did=38148


    Example of usage::

        memcache_servers = ['192.168.0.246:11212',
                            '192.168.0.247:11212',
                            '192.168.0.249:11212']

        ring = HashRing(memcache_servers)
        server = ring.get_node('my_key')

    :copyright: 2008 by Amir Salihefendic.
    :license: BSD
"""

import math
import sys
from bisect import bisect

if sys.version_info >= (2, 5):
    import hashlib
    md5_constructor = hashlib.md5
else:
    import md5
    md5_constructor = md5.new

class HashRing(object):

    def __init__(self, nodes=None, weights=None):
        """`nodes` is a list of objects that have a proper __str__ representation.
        `weights` is dictionary that sets weights to the nodes.  The default
        weight is that all nodes are equal.
        """
        self.ring = dict()
        self._sorted_keys = []

        self.nodes = nodes

        if not weights:
            weights = {}
        self.weights = weights

        self._generate_circle()

    def _generate_circle(self):
        """Generates the circle.
        """
        total_weight = 0
        for node in self.nodes:
            total_weight += self.weights.get(node, 1)

        for node in self.nodes:
            weight = 1

            if node in self.weights:
                weight = self.weights.get(node)

            factor = math.floor((40*len(self.nodes)*weight) / total_weight);

            for j in xrange(0, int(factor)):
                b_key = self._hash_digest( '%s-%s' % (node, j) )

                for i in xrange(0, 3):
                    key = self._hash_val(b_key, lambda x: x+i*4)
                    self.ring[key] = node
                    self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def get_node(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned.

        If the hash ring is empty, `None` is returned.
        """
        pos = self.get_node_pos(string_key)
        if pos is None:
            return None
        return self.ring[ self._sorted_keys[pos] ]

    def get_node_pos(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned
        along with it's position in the ring.

        If the hash ring is empty, (`None`, `None`) is returned.
        """
        if not self.ring:
            return None

        key = self.gen_key(string_key)

        nodes = self._sorted_keys
        pos = bisect(nodes, key)

        if pos == len(nodes):
            return 0
        else:
            return pos

    def iterate_nodes(self, string_key, distinct=True):
        """Given a string key it returns the nodes as a generator that can hold the key.

        The generator iterates one time through the ring
        starting at the correct position.

        if `distinct` is set, then the nodes returned will be unique,
        i.e. no virtual copies will be returned.
        """
        if not self.ring:
            yield None, None

        returned_values = set()
        def distinct_filter(value):
            if str(value) not in returned_values:
                returned_values.add(str(value))
                return value

        pos = self.get_node_pos(string_key)
        for key in self._sorted_keys[pos:]:
            val = distinct_filter(self.ring[key])
            if val:
                yield val

        for i, key in enumerate(self._sorted_keys):
            if i < pos:
                val = distinct_filter(self.ring[key])
                if val:
                    yield val

    def gen_key(self, key):
        """Given a string key it returns a long value,
        this long value represents a place on the hash ring.

        md5 is currently used because it mixes well.
        """
        b_key = self._hash_digest(key)
        return self._hash_val(b_key, lambda x: x)

    def _hash_val(self, b_key, entry_fn):
        return (( b_key[entry_fn(3)] << 24)
                |(b_key[entry_fn(2)] << 16)
                |(b_key[entry_fn(1)] << 8)
                | b_key[entry_fn(0)] )

    def _hash_digest(self, key):
        m = md5_constructor()
        m.update(key)
        return map(ord, m.digest())

########NEW FILE########
__FILENAME__ = setting
#!/usr/bin/env python
# -*- coding: utf8 -*-

try:
    from tornado import database
except:
    import torndb as database

conn = database.Connection("127.0.0.1", "test", "root", "root")
conn1 = database.Connection("127.0.0.1", "test", "root", "root")
conn2 = database.Connection("127.0.0.1", "test", "root", "root")
conn3 = database.Connection("127.0.0.1", "test", "root", "root")

ring = [conn1, conn2, conn3]

########NEW FILE########
__FILENAME__ = torndb
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A lightweight wrapper around MySQLdb.

Originally part of the Tornado framework.  The tornado.database module
is slated for removal in Tornado 3.0, and it is now available separately
as torndb.
"""

from __future__ import absolute_import, division, with_statement

import copy
import itertools
import logging
import os
import time

try:
    import MySQLdb.constants
    import MySQLdb.converters
    import MySQLdb.cursors
except ImportError:
    # If MySQLdb isn't available this module won't actually be useable,
    # but we want it to at least be importable on readthedocs.org,
    # which has limitations on third-party modules.
    if 'READTHEDOCS' in os.environ:
        MySQLdb = None
    else:
        raise

version = "0.1"
version_info = (0, 1, 0, 0)

class Connection(object):
    """A lightweight wrapper around MySQLdb DB-API connections.

    The main value we provide is wrapping rows in a dict/object so that
    columns can be accessed by name. Typical usage::

        db = torndb.Connection("localhost", "mydatabase")
        for article in db.query("SELECT * FROM articles"):
            print article.title

    Cursors are hidden by the implementation, but other than that, the methods
    are very similar to the DB-API.

    We explicitly set the timezone to UTC and the character encoding to
    UTF-8 on all connections to avoid time zone and encoding errors.
    """
    def __init__(self, host, database, user=None, password=None,
                 max_idle_time=7 * 3600, connect_timeout=0,
                 time_zone="+0:00"):
        self.host = host
        self.database = database
        self.max_idle_time = float(max_idle_time)

        args = dict(conv=CONVERSIONS, use_unicode=True, charset="utf8",
                    db=database, init_command=('SET time_zone = "%s"' % time_zone),
                    connect_timeout=connect_timeout, sql_mode="TRADITIONAL")
        if user is not None:
            args["user"] = user
        if password is not None:
            args["passwd"] = password

        # We accept a path to a MySQL socket file or a host(:port) string
        if "/" in host:
            args["unix_socket"] = host
        else:
            self.socket = None
            pair = host.split(":")
            if len(pair) == 2:
                args["host"] = pair[0]
                args["port"] = int(pair[1])
            else:
                args["host"] = host
                args["port"] = 3306

        self._db = None
        self._db_args = args
        self._last_use_time = time.time()
        try:
            self.reconnect()
        except Exception:
            logging.error("Cannot connect to MySQL on %s", self.host,
                          exc_info=True)

    def __del__(self):
        self.close()

    def close(self):
        """Closes this database connection."""
        if getattr(self, "_db", None) is not None:
            self._db.close()
            self._db = None

    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        self.close()
        self._db = MySQLdb.connect(**self._db_args)
        self._db.autocommit(True)

    def iter(self, query, *parameters, **kwparameters):
        """Returns an iterator for the given query and parameters."""
        self._ensure_connected()
        cursor = MySQLdb.cursors.SSCursor(self._db)
        try:
            self._execute(cursor, query, parameters, kwparameters)
            column_names = [d[0] for d in cursor.description]
            for row in cursor:
                yield Row(zip(column_names, row))
        finally:
            cursor.close()

    def query(self, query, *parameters, **kwparameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor()
        params = tuple([i+tuple([None, None]) if isinstance(i, tuple) and len(i) <= 1 else i for i in parameters])
        try:
            self._execute(cursor, query, params, kwparameters)
            column_names = [d[0] for d in cursor.description]
            return [Row(itertools.izip(column_names, row)) for row in cursor]
        finally:
            cursor.close()

    def get(self, query, *parameters, **kwparameters):
        """Returns the first row returned for the given query."""
        rows = self.query(query, *parameters, **kwparameters)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for Database.get() query")
        else:
            return rows[0]

    # rowcount is a more reasonable default return value than lastrowid,
    # but for historical compatibility execute() must return lastrowid.
    def execute(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the lastrowid from the query."""
        return self.execute_lastrowid(query, *parameters, **kwparameters)

    def execute_lastrowid(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the lastrowid from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            return cursor.lastrowid
        finally:
            cursor.close()

    def execute_rowcount(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the rowcount from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters, kwparameters)
            return cursor.rowcount
        finally:
            cursor.close()

    def executemany(self, query, parameters):
        """Executes the given query against all the given param sequences.

        We return the lastrowid from the query.
        """
        return self.executemany_lastrowid(query, parameters)

    def executemany_lastrowid(self, query, parameters):
        """Executes the given query against all the given param sequences.

        We return the lastrowid from the query.
        """
        cursor = self._cursor()
        try:
            cursor.executemany(query, parameters)
            return cursor.lastrowid
        finally:
            cursor.close()

    def executemany_rowcount(self, query, parameters):
        """Executes the given query against all the given param sequences.

        We return the rowcount from the query.
        """
        cursor = self._cursor()
        try:
            cursor.executemany(query, parameters)
            return cursor.rowcount
        finally:
            cursor.close()

    update = execute_rowcount
    updatemany = executemany_rowcount

    insert = execute_lastrowid
    insertmany = executemany_lastrowid

    def _ensure_connected(self):
        # Mysql by default closes client connections that are idle for
        # 8 hours, but the client library does not report this fact until
        # you try to perform a query and it fails.  Protect against this
        # case by preemptively closing and reopening the connection
        # if it has been idle for too long (7 hours by default).
        if (self._db is None or
            (time.time() - self._last_use_time > self.max_idle_time)):
            self.reconnect()
        self._last_use_time = time.time()

    def _cursor(self):
        self._ensure_connected()
        return self._db.cursor()

    def _execute(self, cursor, query, parameters, kwparameters):
        try:
            return cursor.execute(query, kwparameters or parameters)
        except OperationalError:
            logging.error("Error connecting to MySQL on %s", self.host)
            self.close()
            raise


class Row(dict):
    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

if MySQLdb is not None:
    # Fix the access conversions to properly recognize unicode/binary
    FIELD_TYPE = MySQLdb.constants.FIELD_TYPE
    FLAG = MySQLdb.constants.FLAG
    CONVERSIONS = copy.copy(MySQLdb.converters.conversions)

    field_types = [FIELD_TYPE.BLOB, FIELD_TYPE.STRING, FIELD_TYPE.VAR_STRING]
    if 'VARCHAR' in vars(FIELD_TYPE):
        field_types.append(FIELD_TYPE.VARCHAR)

    for field_type in field_types:
        CONVERSIONS[field_type] = [(FLAG.BINARY, str)] + CONVERSIONS[field_type]

    # Alias some common MySQL exceptions
    IntegrityError = MySQLdb.IntegrityError
    OperationalError = MySQLdb.OperationalError

########NEW FILE########
