__FILENAME__ = models
from mongoengine import *

class Address(Document):
    street = StringField()

class TypelessAddress(Document):
    meta = {"index_types" : False}
    street = StringField()

class User(Document):
    meta = {
            "indexes": [("address_ref"),
                        ("address_id")
                        ]}

    address_ref = ReferenceField("Address")
    address_id = ObjectIdField()

class TypelessUser(Document):
    meta = {
            "indexes": [("address_id"),
                        ("typeless_address_ref")
                        ],
            "index_types" : False}
    address_id = ObjectIdField()
    typeless_address_ref = ReferenceField("TypelessAddress")


class Things(Document):
    long_field = StringField()
########NEW FILE########
__FILENAME__ = testdata
from bson.objectid import ObjectId
from examples.models import User, Address, Things, TypelessAddress, TypelessUser
from mongoengine.connection import connect

def add_dataset1():
    address = Address(street="123 Main St")
    address.save()
    address.reload()
    typeless_address = TypelessAddress(street="123 Main St")
    typeless_address.save()
    typeless_address.reload()

    for i in range(0, 100000):
        user1 = User(address_ref=address,address_id=address.id)
        user1.save(safe=False)
        user2 = TypelessUser(address_id=address.id,
                     typeless_address=typeless_address)
        user2.save(safe=False)

connect('examples1')
add_dataset1()

def add_dataset2():

    for i in range(0, 100000):
        thing = Things(long_field="http://www.somelongurl.com?foo=bar&id=%s" % ObjectId())
        thing.save(safe=False)

connect('examples2')
add_dataset2()

########NEW FILE########
__FILENAME__ = collection_stats
#!/usr/bin/env python

"""
This script prints some basic collection stats about the size of the
collections and their indexes.
"""

from prettytable import PrettyTable
import psutil
from pymongo import Connection
from pymongo import ReadPreference
from optparse import OptionParser

def compute_signature(index):
    signature = index["ns"]
    for key in index["key"]:
        signature += "%s_%s" % (key, index["key"][key])
    return signature

def get_collection_stats(database, collection):
    print "Checking DB: %s" % collection.full_name
    return database.command("collstats", collection.name)

def get_cli_options():
    parser = OptionParser(usage="usage: python %prog [options]",
                          description="""This script prints some basic collection stats about the size of the collections and their indexes.""")

    parser.add_option("-H", "--host",
                      dest="host",
                      default="localhost",
                      metavar="HOST",
                      help="MongoDB host")
    parser.add_option("-p", "--port",
                      dest="port",
                      default=27017,
                      metavar="PORT",
                      help="MongoDB port")
    parser.add_option("-d", "--database",
                      dest="database",
                      default="",
                      metavar="DATABASE",
                      help="Target database to generate statistics. All if omitted.")
    parser.add_option("-u", "--user",
                      dest="user",
                      default="",
                      metavar="USER",
                      help="Admin username if authentication is enabled")
    parser.add_option("--password",
                      dest="password",
                      default="",
                      metavar="PASSWORD",
                      help="Admin password if authentication is enabled")

    (options, args) = parser.parse_args()

    return options

def get_connection(host, port, username, password):
    userPass = ""
    if username and password:
        userPass = username + ":" + password + "@"

    mongoURI = "mongodb://" + userPass + host + ":" + str(port)
    return Connection(host=mongoURI, read_preference=ReadPreference.SECONDARY)

# From http://www.5dollarwhitebox.org/drupal/node/84
def convert_bytes(bytes):
    bytes = float(bytes)
    magnitude = abs(bytes)
    if magnitude >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif magnitude >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif magnitude >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif magnitude >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size

def main(options):
    summary_stats = {
        "count" : 0,
        "size" : 0,
        "indexSize" : 0
    }
    all_stats = []

    connection = get_connection(options.host, options.port, options.user, options.password)

    all_db_stats = {}

    databases= []
    if options.database:
        databases.append(options.database)
    else:
        databases = connection.database_names()

    for db in databases:
        # FIXME: Add an option to include oplog stats.
        if db == "local":
            continue

        database = connection[db]
        all_db_stats[database.name] = []
        for collection_name in database.collection_names():
            stats = get_collection_stats(database, database[collection_name])
            all_stats.append(stats)
            all_db_stats[database.name].append(stats)

            summary_stats["count"] += stats["count"]
            summary_stats["size"] += stats["size"]
            summary_stats["indexSize"] += stats.get("totalIndexSize", 0)

    x = PrettyTable(["Collection", "Count", "% Size", "DB Size", "Avg Obj Size", "Indexes", "Index Size"])
    x.align["Collection"]  = "l"
    x.align["% Size"]  = "r"
    x.align["Count"]  = "r"
    x.align["DB Size"]  = "r"
    x.align["Avg Obj Size"]  = "r"
    x.align["Index Size"]  = "r"
    x.padding_width = 1

    print

    for db in all_db_stats:
        db_stats = all_db_stats[db]
        count = 0
        for stat in db_stats:
            count += stat["count"]
            x.add_row([stat["ns"], stat["count"], "%0.1f%%" % ((stat["size"] / float(summary_stats["size"])) * 100),
                       convert_bytes(stat["size"]),
                       convert_bytes(stat.get("avgObjSize", 0)),
                       stat.get("nindexes", 0),
                       convert_bytes(stat.get("totalIndexSize", 0))])

    print
    print x.get_string(sortby="% Size")
    print "Total Documents:", summary_stats["count"]
    print "Total Data Size:", convert_bytes(summary_stats["size"])
    print "Total Index Size:", convert_bytes(summary_stats["indexSize"])

    # this is only meaningful if we're running the script on localhost
    if options.host == "localhost":
        ram_headroom = psutil.phymem_usage()[0] - summary_stats["indexSize"]
        print "RAM Headroom:", convert_bytes(ram_headroom)
        print "RAM Used: %s (%s%%)" % (convert_bytes(psutil.phymem_usage()[1]), psutil.phymem_usage()[3])
        print "Available RAM Headroom:", convert_bytes((100 - psutil.phymem_usage()[3]) / 100 * ram_headroom)

if __name__ == "__main__":
    options = get_cli_options()
    main(options)

########NEW FILE########
__FILENAME__ = index_stats
#!/usr/bin/env python

"""
This script prints some basic collection stats about the size of the
collections and their indexes.
"""

from prettytable import PrettyTable
import psutil
from pymongo import Connection
from pymongo import ReadPreference
from optparse import OptionParser

def compute_signature(index):
    signature = index["ns"]
    for key in index["key"]:
        signature += "%s_%s" % (key, index["key"][key])
    return signature

def get_collection_stats(database, collection):
    print "Checking DB: %s" % collection.full_name
    return database.command("collstats", collection.name)

# From http://www.5dollarwhitebox.org/drupal/node/84
def convert_bytes(bytes):
    bytes = float(bytes)
    magnitude = abs(bytes)
    if magnitude >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif magnitude >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif magnitude >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif magnitude >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size

def get_cli_options():
    parser = OptionParser(usage="usage: python %prog [options]",
                          description="""This script prints some basic collection stats about the size of the collections and their indexes.""")

    parser.add_option("-H", "--host",
                      dest="host",
                      default="localhost",
                      metavar="HOST",
                      help="MongoDB host")
    parser.add_option("-p", "--port",
                      dest="port",
                      default=27017,
                      metavar="PORT",
                      help="MongoDB port")
    parser.add_option("-d", "--database",
                      dest="database",
                      default="",
                      metavar="DATABASE",
                      help="Target database to generate statistics. All if omitted.")
    parser.add_option("-u", "--user",
                      dest="user",
                      default="",
                      metavar="USER",
                      help="Admin username if authentication is enabled")
    parser.add_option("--password",
                      dest="password",
                      default="",
                      metavar="PASSWORD",
                      help="Admin password if authentication is enabled")

    (options, args) = parser.parse_args()

    return options

def get_connection(host, port, username, password):
    userPass = ""
    if username and password:
        userPass = username + ":" + password + "@"

    mongoURI = "mongodb://" + userPass + host + ":" + str(port)
    return Connection(host=mongoURI, read_preference=ReadPreference.SECONDARY)

def main(options):
    summary_stats = {
        "count" : 0,
        "size" : 0,
        "indexSize" : 0
    }
    all_stats = []

    connection = get_connection(options.host, options.port, options.user, options.password)

    all_db_stats = {}

    databases = []
    if options.database:
        databases.append(options.database)
    else:
        databases = connection.database_names()

    for db in databases:
        # FIXME: Add an option to include oplog stats.
        if db == "local":
            continue

        database = connection[db]
        all_db_stats[database.name] = []
        for collection_name in database.collection_names():
            stats = get_collection_stats(database, database[collection_name])
            all_stats.append(stats)
            all_db_stats[database.name].append(stats)

            summary_stats["count"] += stats["count"]
            summary_stats["size"] += stats["size"]
            summary_stats["indexSize"] += stats.get("totalIndexSize", 0)

    x = PrettyTable(["Collection", "Index","% Size", "Index Size"])
    x.align["Collection"] = "l"
    x.align["Index"] = "l"
    x.align["% Size"] = "r"
    x.align["Index Size"] = "r"
    x.padding_width = 1

    print

    index_size_mapping = {}
    for db in all_db_stats:
        db_stats = all_db_stats[db]
        count = 0
        for stat in db_stats:
            count += stat["count"]
            for index in stat["indexSizes"]:
                index_size = stat["indexSizes"].get(index, 0)
                row = [stat["ns"], index,
                          "%0.1f%%" % ((index_size / float(summary_stats["indexSize"])) * 100),
                  convert_bytes(index_size)]
                index_size_mapping[index_size] = row
                x.add_row(row)


    print "Index Overview"
    print x.get_string(sortby="Collection")

    print
    print "Top 5 Largest Indexes"
    x = PrettyTable(["Collection", "Index","% Size", "Index Size"])
    x.align["Collection"] = "l"
    x.align["Index"] = "l"
    x.align["% Size"] = "r"
    x.align["Index Size"] = "r"
    x.padding_width = 1

    top_five_indexes = sorted(index_size_mapping.keys(), reverse=True)[0:5]
    for size in top_five_indexes:
        x.add_row(index_size_mapping.get(size))
    print x
    print

    print "Total Documents:", summary_stats["count"]
    print "Total Data Size:", convert_bytes(summary_stats["size"])
    print "Total Index Size:", convert_bytes(summary_stats["indexSize"])

    # this is only meaningful if we're running the script on localhost
    if options.host == "localhost":
        ram_headroom = psutil.phymem_usage()[0] - summary_stats["indexSize"]
        print "RAM Headroom:", convert_bytes(ram_headroom)
        print "RAM Used: %s (%s%%)" % (convert_bytes(psutil.phymem_usage()[1]), psutil.phymem_usage()[3])
        print "Available RAM Headroom:", convert_bytes((100 - psutil.phymem_usage()[3]) / 100 * ram_headroom)

if __name__ == "__main__":
    options = get_cli_options()
    main(options)

########NEW FILE########
__FILENAME__ = helpers
import bson, struct
import itertools
from bson.errors import InvalidBSON


# Helper functions work working with bson files created using mongodump

def bson_iter(bson_file):
    """
    Takes a file handle to a .bson file and returns an iterator for each
    doc in the file.  This will not load all docs into memory.

    with open('User.bson', 'rb') as bs:
        active_users = filter(bson_iter(bs), "type", "active")

    """
    while True:
        size_str = bson_file.read(4)
        if not len(size_str):
            break

        obj_size = struct.unpack("<i", size_str)[0]
        obj = bson_file.read(obj_size - 4)
        if obj[-1] != "\x00":
            raise InvalidBSON("bad eoo")
        yield bson._bson_to_dict(size_str + obj, dict, True)[0]

def _deep_get(obj, field):
    parts = field.split(".")
    if len(parts) == 1:
        return obj.get(field)

    last_value = {}
    for part in parts[0:-1]:
        last_value  = obj.get(part)

    if not last_value:
        return False

    if isinstance(last_value, dict):
        return last_value.get(parts[-1])
    else:
        return getattr(last_value, parts[-1])

def groupby(iterator, field):
    """
    Returns dictionary with the keys beign the field to group by
    and the values a list of the group docs.

    This is useful for converting a list of docs into dict by _id
    for example.
    """
    groups = {}
    for k, g in itertools.groupby(iterator, lambda x: _deep_get(x, field)):
        items = groups.setdefault(k, [])
        for item in g:
            items.append(item)
    return groups

def filter(iterator, field, value):
    """
    Takes an iterator and returns only the docs that have a field == value.

    The field can be a nested field like a.b.c and it will descend into the
    embedded documents.
    """

    return itertools.ifilter(lambda x: _deep_get(x, field) == value, iterator)

########NEW FILE########
__FILENAME__ = parser
# simpleSQL.py
#
# simple demo of using the parsing library to do simple-minded SQL parsing
# could be extended to include where clauses etc.
#
# Copyright (c) 2003, Paul McGuire
#
# Originally from http://pyparsing.wikispaces.com/file/view/simpleSQL.py

from pyparsing import Literal, CaselessLiteral, Word, upcaseTokens, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, restOfLine, Keyword

def test( str ):
    print str,"->"
    try:
        tokens = simpleSQL.parseString( str )
        print "tokens = ",        tokens
        print "tokens.columns =", tokens.columns
        print "tokens.tables =",  tokens.tables
        print "tokens.where =", tokens.where
    except ParseException, err:
        print " "*err.loc + "^\n" + err.msg
        print err
    print


# define SQL tokens
selectStmt = Forward()
selectToken = Keyword("select", caseless=True)
fromToken   = Keyword("from", caseless=True)
whereToken  = Keyword("where", caseless=True)

ident          = Word( alphas+"_", alphanums + "_$." ).setName("identifier")
columnName     = delimitedList( ident, ".", combine=True )
columnNameList = Group( delimitedList( columnName ) )
tableName      = delimitedList( ident, ".", combine=True )
tableNameList  = Group( delimitedList( tableName ) )

whereExpression = Forward()
and_ = Keyword("and", caseless=True)
or_ = Keyword("or", caseless=True)
in_ = Keyword("in", caseless=True)

E = CaselessLiteral("E")
binop = oneOf("= != < > >= <= eq ne lt le gt ge", caseless=True)
arithSign = Word("+-",exact=1)
realNum = Combine( Optional(arithSign) + ( Word( nums ) + "." + Optional( Word(nums) )  |
                                                         ( "." + Word(nums) ) ) +
            Optional( E + Optional(arithSign) + Word(nums) ) )
intNum = Combine( Optional(arithSign) + Word( nums ) +
            Optional( E + Optional("+") + Word(nums) ) )

columnRval = realNum | intNum | quotedString | columnName # need to add support for alg expressions
whereCondition = Group(
    ( columnName + binop + columnRval ) |
    ( columnName + in_ + "(" + delimitedList( columnRval ) + ")" ) |
    ( "(" + whereExpression + ")" )
    )
whereExpression << whereCondition + ZeroOrMore( ( and_ | or_ ) + whereExpression )

# define the grammar
selectStmt      << ( selectToken +
                   ( '*' | columnNameList ).setResultsName( "columns" ) +
                   fromToken +
                   tableNameList.setResultsName( "tables" ) +
                   Optional( Group( whereToken + whereExpression ), "" ).setResultsName("where") )

simpleSQL = selectStmt

# define Oracle comment format, and ignore them
oracleSqlComment = "--" + restOfLine
simpleSQL.ignore( oracleSqlComment )


"""
test( "SELECT * from XYZZY, ABC" )
test( "select * from SYS.XYZZY" )
test( "Select A from Sys.dual" )
test( "Select A,B,C from Sys.dual" )
test( "Select A, B, C from Sys.dual" )
test( "Select A, B, C from Sys.dual, Table2   " )
test( "Xelect A, B, C from Sys.dual" )
test( "Select A, B, C frox Sys.dual" )
test( "Select" )
test( "Select &&& frox Sys.dual" )
test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE')" )
test( "Select A from Sys.dual where a in ('RED','GREEN','BLUE') and b in (10,20,30)" )
test( "Select A,b from table1,table2 where table1.id eq table2.id -- test out comparison operators" )
test( "Select * from User, RemoteAccount where user._id = user.user_id)" )


Test output:
>pythonw -u simpleSQL.py
SELECT * from XYZZY, ABC ->
tokens =  ['select', '*', 'from', ['XYZZY', 'ABC']]
tokens.columns = *
tokens.tables = ['XYZZY', 'ABC']

select * from SYS.XYZZY ->
tokens =  ['select', '*', 'from', ['SYS.XYZZY']]
tokens.columns = *
tokens.tables = ['SYS.XYZZY']

Select A from Sys.dual ->
tokens =  ['select', ['A'], 'from', ['SYS.DUAL']]
tokens.columns = ['A']
tokens.tables = ['SYS.DUAL']

Select A,B,C from Sys.dual ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL']]
tokens.columns = ['A', 'B', 'C']
tokens.tables = ['SYS.DUAL']

Select A, B, C from Sys.dual ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL']]
tokens.columns = ['A', 'B', 'C']
tokens.tables = ['SYS.DUAL']

Select A, B, C from Sys.dual, Table2    ->
tokens =  ['select', ['A', 'B', 'C'], 'from', ['SYS.DUAL', 'TABLE2']]
tokens.columns = ['A', 'B', 'C']
tokens.tables = ['SYS.DUAL', 'TABLE2']

Xelect A, B, C from Sys.dual ->
^
Expected 'select'
Expected 'select' (0), (1,1)

Select A, B, C frox Sys.dual ->
               ^
Expected 'from'
Expected 'from' (15), (1,16)

Select ->
      ^
Expected '*'
Expected '*' (6), (1,7)

Select &&& frox Sys.dual ->
       ^
Expected '*'
Expected '*' (7), (1,8)

>Exit code: 0
"""
########NEW FILE########
__FILENAME__ = redundant_indexes
#!/usr/bin/env python

"""
This is a simple script to print out potentially redundant indexes in a mongdb instance.
For example, if an index is defined on {field1:1,field2:1} and there is another index
with just fields {field1:1}, the latter index is not needed since the first index already
indexes the necessary fields.
"""
from pymongo import Connection
from pymongo import ReadPreference
from optparse import OptionParser


def get_cli_options():
    parser = OptionParser(usage="usage: python %prog [options]",
                          description="""This script prints some basic collection stats about the size of the collections and their indexes.""")

    parser.add_option("-H", "--host",
                      dest="host",
                      default="localhost",
                      metavar="HOST",
                      help="MongoDB host")
    parser.add_option("-p", "--port",
                      dest="port",
                      default=27017,
                      metavar="PORT",
                      help="MongoDB port")
    parser.add_option("-d", "--database",
                      dest="database",
                      default="",
                      metavar="DATABASE",
                      help="Target database to generate statistics. All if omitted.")
    parser.add_option("-u", "--user",
                      dest="user",
                      default="",
                      metavar="USER",
                      help="Admin username if authentication is enabled")
    parser.add_option("--password",
                      dest="password",
                      default="",
                      metavar="PASSWORD",
                      help="Admin password if authentication is enabled")

    (options, args) = parser.parse_args()

    return options

def get_connection(host, port, username, password):
    userPass = ""
    if username and password:
        userPass = username + ":" + password + "@"

    mongoURI = "mongodb://" + userPass + host + ":" + str(port)
    return Connection(host=mongoURI, read_preference=ReadPreference.SECONDARY)

def main(options):
    connection = get_connection(options.host, options.port, options.user, options.password)

    def compute_signature(index):
        signature = index["ns"]
        for key in index["key"]:
            try:
                signature += "%s_%s" % (key, int(index["key"][key]))
            except ValueError:
                signature += "%s_%s" % (key, index["key"][key])
        return signature

    def report_redundant_indexes(current_db):
        print "Checking DB: %s" % current_db.name
        indexes = current_db.system.indexes.find()
        index_map = {}
        for index in indexes:
            signature = compute_signature(index)
            index_map[signature] = index

        for signature in index_map.keys():
            for other_sig in index_map.keys():
                if signature == other_sig:
                    continue
                if other_sig.startswith(signature):
                    print "Index %s[%s] may be redundant with %s[%s]" % (
                        index_map[signature]["ns"],
                        index_map[signature]["name"],
                        index_map[other_sig]["ns"],
                        index_map[other_sig]["name"])

    databases= []
    if options.database:
        databases.append(options.database)
    else:
        databases = connection.database_names()

    for db in databases:
        report_redundant_indexes(connection[db])

if __name__ == "__main__":
    options = get_cli_options()
    main(options)

########NEW FILE########
