__FILENAME__ = app
#!/usr/bin/env python
#
# Copyright 2012 Major Hayden
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

"""MySQL <-> JSON bridge"""

import datetime
import decimal
import json
import logging
import os
from urlparse import urlparse
import yaml


from tornado.database import Connection
from flask import Flask, Response, abort, request


app = Flask(__name__)
app.debug = True


# Helps us find non-python files installed by setuptools
def data_file(fname):
    """Return the path to a data file of ours."""
    return os.path.join(os.path.split(__file__)[0], fname)

if not app.debug:
    logyaml = ""
    with open(data_file('config/log.yml'), 'r') as f:
        logyaml = yaml.load(f)
    try:
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        if logyaml['type'] == "file":
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                logyaml['logfile'], backupCount=logyaml['backupCount'])
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
        elif logyaml['type'] == 'syslog':
            from logging.handlers import SysLogHandler
            syslog_handler = SysLogHandler()
            syslog_handler.setLevel(logging.INFO)
            syslog_handler.setFormatter(formatter)
            app.logger.addHandler(syslog_handler)
    except:
        pass


# Decorator to return JSON easily
def jsonify(f):
    def inner(*args, **kwargs):
        jsonstring = json.dumps(f(*args, **kwargs), default=json_fixup)
        return Response(jsonstring, mimetype='application/json')
    return inner


def json_fixup(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    else:
        return None


def read_config():
    with open(data_file('config/databases.yml'), 'r') as f:
        databases = yaml.load(f)
    return databases


# Pull the database credentials from our YAML file
def get_db_creds(database):
    databases = read_config()
    mysql_uri = databases.get(database)

    # If the database doesn't exist in the yaml, we're done
    if not mysql_uri:
        return False

    # Parse the URL in the .yml file
    try:
        o = urlparse(mysql_uri)
        creds = {
            'host':         o.hostname,
            'database':     o.path[1:],
            'user':         o.username,
            'password':     o.password,
        }
    except:
        creds = False

    return creds


# Handles the listing of available databases
@app.route("/list", methods=['GET'])
def return_database_list():
    databases = read_config()
    data = {'databases': databases.keys()}
    return Response(json.dumps(data), mimetype='application/json')


# This is what receives our SQL queries
@app.route("/query/<database>", methods=['POST'])
@jsonify
def do_query(database=None):
    # Pick up the database credentials
    app.logger.warning("%s requesting access to %s database" % (
        request.remote_addr, database))
    creds = get_db_creds(database)

    # If we couldn't find corresponding credentials, throw a 404
    if creds == False:
        return {"ERROR": "Unable to find credentials matching %s." % database}
        abort(404)

    # Prepare the database connection
    app.logger.debug("Connecting to %s database (%s)" % (
        database, request.remote_addr))
    db = Connection(**creds)

    # See if we received a query
    sql = request.form.get('sql')
    if not sql:
        return {"ERROR": "SQL query missing from request."}

    # If the query has a percent sign, we need to excape it
    if '%' in sql:
        sql = sql.replace('%', '%%')

    # Attempt to run the query
    try:
        app.logger.info("%s attempting to run \" %s \" against %s database" % (
            request.remote_addr, sql, database))
        results = db.query(sql)
    except Exception, e:
        return {"ERROR": ": ".join(str(i) for i in e.args)}

    # Disconnect from the DB
    db.close()

    return {'result': results}


if __name__ == "__main__":
    app.run(host='0.0.0.0')

########NEW FILE########
__FILENAME__ = query_test
#!/usr/bin/env python
import json
import pprint
import requests


payload = {'sql': 'SELECT * FROM information_schema.tables'}
url = "http://localhost:5000/query/my_database"

r = requests.post(url, data=payload)

print r.status_code
try:
    pprint.pprint(json.loads(r.text))
except:
    pprint.pprint(r.text)

########NEW FILE########
__FILENAME__ = database
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

"""A lightweight wrapper around MySQLdb."""

from __future__ import absolute_import, division, with_statement

import copy
import MySQLdb.constants
import MySQLdb.converters
import MySQLdb.cursors
import itertools
import logging
import time


class Connection(object):
    """A lightweight wrapper around MySQLdb DB-API connections.

    The main value we provide is wrapping rows in a dict/object so that
    columns can be accessed by name. Typical usage::

        db = database.Connection("localhost", "mydatabase")
        for article in db.query("SELECT * FROM articles"):
            print article.title

    Cursors are hidden by the implementation, but other than that, the methods
    are very similar to the DB-API.

    We explicitly set the timezone to UTC and the character encoding to
    UTF-8 on all connections to avoid time zone and encoding errors.
    """
    def __init__(self, host, database, user=None, password=None,
                 max_idle_time=7 * 3600):
        self.host = host
        self.database = database
        self.max_idle_time = max_idle_time

        args = dict(conv=CONVERSIONS, use_unicode=True, charset="utf8",
                    db=database, init_command='SET time_zone = "+0:00"',
                    sql_mode="TRADITIONAL")
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

    def iter(self, query, *parameters):
        """Returns an iterator for the given query and parameters."""
        self._ensure_connected()
        cursor = MySQLdb.cursors.SSCursor(self._db)
        try:
            self._execute(cursor, query, parameters)
            column_names = [d[0] for d in cursor.description]
            for row in cursor:
                yield Row(zip(column_names, row))
        finally:
            cursor.close()

    def query(self, query, *parameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters)
            column_names = [d[0] for d in cursor.description]
            return [Row(itertools.izip(column_names, row)) for row in cursor]
        finally:
            cursor.close()

    def get(self, query, *parameters):
        """Returns the first row returned for the given query."""
        rows = self.query(query, *parameters)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned for Database.get() query")
        else:
            return rows[0]

    # rowcount is a more reasonable default return value than lastrowid,
    # but for historical compatibility execute() must return lastrowid.
    def execute(self, query, *parameters):
        """Executes the given query, returning the lastrowid from the query."""
        return self.execute_lastrowid(query, *parameters)

    def execute_lastrowid(self, query, *parameters):
        """Executes the given query, returning the lastrowid from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters)
            return cursor.lastrowid
        finally:
            cursor.close()

    def execute_rowcount(self, query, *parameters):
        """Executes the given query, returning the rowcount from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters)
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

    def _execute(self, cursor, query, parameters):
        try:
            return cursor.execute(query, parameters)
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
