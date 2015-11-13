__FILENAME__ = alltests
#!/usr/bin/python
"""Runs all unit tests in *_test.py files in the current directory.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import glob
import imp
import logging
import os
import sys
import unittest


def main():
  # don't show logging messages
  logging.disable(logging.CRITICAL + 1)

  for filename in glob.glob('*_test.py'):
    name = os.path.splitext(filename)[0]

    # this is wishlisted right now.
    if name in ('graph_on_fql_test',):
      continue
    elif name in sys.modules:
      # this is important. imp.load_module() twice is effectively a reload,
      # which duplicates multiply inherited test case base classes and makes
      # super() think an instance of one isn't an instance of another.
      module = sys.modules[name]
    else:
      module = imp.load_module(name, *imp.find_module(name))

    # ugh. this is the simplest way to make all of the test classes defined in
    # the modules visible to unittest.main(), but it's really ugly.
    globals().update(vars(module))

  unittest.main()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = download
#!/usr/bin/python
"""Downloads FQL and Graph API schemas and example data.

Gets the FQL schema by scraping the Facebook API docs and the Graph API schema
and example data by querying the user's own data with the given access token.
Writes the schemas and example data as Python dictionaries (see schemautil.py),
and writes the FQL schemas and example data as SQLite CREATE TABLE and INSERT
statements.

You can get an access token here:
http://developers.facebook.com/tools/explorer?method=GET&path=me

You'll need to grant it pretty much all available permissions.

Here's what happens:
1. Fetch the Facebook FQL docs.
2. Scrape the HTML and generate a CREATE TABLE statement for each FQL table.
3. Write those statements, plus a couple more mockfacebook-specific tables, to
the schema files.
4. Fetch one or more rows of real Facebook data for each table, via FQL queries.
5. Writes those rows to the FQL example data files.
4. Fetch real Graph API objects for each Graph API object type.
5. Writes those objects to the Graph API example data file.


Here's a script to download of the FQL and Graph API reference docs:

#!/bin/tcsh
cd ~/docs/facebook/
foreach dir (api fql)
  wget --mirror --html-extension --page-requisites --no-host-directories \
    --cut-dirs=2 --include-directories=/docs/reference/$dir/ \
    http://developers.facebook.com/docs/reference/$dir/

  # remove the auto-redirect to developers.facebook.com and convert links to
  # absolute file:/// url. (wget --convert-links makes them relative.)
  find $dir -type f | xargs sed -ri '\
    s/<script .+\/script>//g; \
    s/<a href="http:\/\/developers.facebook.com\/docs\/reference([^"]+)"/<a href="file:\/\/\/home\/$USER\/docs\/facebook\1index.html"/g'
end
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import collections
import httplib
import itertools
import json
import logging
import operator
import optparse
import re
import sys
import traceback
import urllib
import urllib2
import urlparse

import graph
import schemautil


HTTP_RETRIES = 5
HTTP_TIMEOUT_S = 20

# Facebook's limit on Graph API batch request size
MAX_REQUESTS_PER_BATCH = 50

# regexps for scraping facebook docs. naturally, these are very brittle.
# TODO: use something like BeautifulSoup instead.
TABLE_RE = re.compile('<h1> *(?P<name>\w+)[^<]*</h1>')
TABLE_LINKS_RE = re.compile("""\
<h2 id="(objects|tables)">(Objects|Tables)</h2><div class="refindex">\
(<div class="page">.+
</div></div>)+""")
TABLE_LINK_RE = re.compile('<div class="title"><a href="([^"]+)"')
FQL_COLUMN_RE = re.compile("""\
<td class="indexable">(?P<indexable>\\*|)</td>\
<td class="name"> *(?P<name>[^< ]+) *</td>\
<td class="type"> *(?P<fb_type>[^< ]+) *</td>\
""")
GRAPH_COLUMN_RE = re.compile("""\
(?P<indexable>)\
</td></tr><tr><td><code>(?P<name>.+)</code></td><td><p>.+</p>
</td><td><p>.+</p>
</td><td><p>(?:<code>)?(?P<fb_type>\w+).*</p>\
""")

# regexp for extracting the fb type from a graph api metadata field description
# e.g.: "The user's birthday. `user_birthday`. Date `string` in `MM/DD/YYYY` format."
GRAPH_DESCRIPTION_TYPE_RE = re.compile('\\. *`?(\w+)[^.]*\\.? *$')

# maps Facebook column type to (sanitized type name, SQLite type). unknown
# types map to no (ie unspecified) SQLite type.
COLUMN_TYPES = {
  'array':      ('array', ''),
  'booelean':   ('bool', 'INTEGER'), # typo for application.is_facebook_app
  'bool':       ('bool', 'INTEGER'),
  'boolean':    ('bool', 'INTEGER'),
  'comments':   ('array', ''),       # only comment.comments
  'contains':   ('object', ''),      # Post.to: "Contains in `data` an array..."
  'date':       ('string', 'TEXT'),  # User.birthday: "Date `string`..."
  'dictionary': ('object', ''),
  'float':      ('float', 'REAL'),
  'int':        ('int', 'INTEGER'),
  'integer':    ('int', 'INTEGER'),
  'number':     ('int', 'INTEGER'),
  'object':     ('object', ''),
  'string':     ('string', 'TEXT'),
  'structure':  ('object', ''),
  'time':       ('int', 'INTEGER'),
  'uid':        ('int', 'INTEGER'),
}

# overridden column types. maps table name to dict mapping column name to
# facebook type. lower case tables are FQL, capitalized tables are Graph API.
#
# Filed a Facebook API bug to fix the docs:
# http://bugs.developers.facebook.net/show_bug.cgi?id=20470
OVERRIDE_COLUMN_TYPES = collections.defaultdict(dict, {
    # FQL tables
    'album': {'cover_object_id': 'string'},
    'application': {'app_id': 'string', 'developers': 'object'},
    'comment': {'id': 'string', 'object_id': 'int'},
    'domain_admin': {'domain_id': 'string', 'owner_id': 'string'},
    'event': {'venue': 'object'},
    'friend': {'uid1': 'string', 'uid2': 'string'},
    'friendlist': {'owner': 'integer'},
    'friendlist_member': {'uid': 'integer'},
    'group': {'version': 'int'},
    'group_member': {'positions': 'object'},
    'link': {'link_id': 'int'},
    'like': {'object_id': 'int'},
    'mailbox_folder': {'viewer_id': 'string'},
    'page': {'hours': 'object', 'is_community_page': 'boolean',
             'location': 'object', 'parking': 'object'},
    'page_fan': {'uid': 'int', 'page_id': 'int'},
    'place': {'page_id': 'int'},
    'photo': {
      'owner': 'string', 'src_big_height': 'int', 'src_big_width': 'int',
      'src_small_height': 'int', 'src_small_width': 'int',
      'src_height': 'int', 'src_width': 'int',
      },
    'photo_tag': {'subject': 'string'},
    'privacy': {'id': 'int', 'object_id': 'int'},
    'profile': {'pic_crop': 'object'},
    'status': {'status_id': 'int', 'source': 'int', 'time': 'int'},
    'stream': {'actor_id': 'int', 'target_id': 'int'},
    'stream_filter': {'uid': 'int'},
    'user': {'timezone': 'int'},
    'video': {'vid': 'int'},
    })

# overridden indexable columns. maps table name to dict mapping column name to
# boolean for whether the column is indexable. Filed a Facebook API bug to fix
# the docs:
# http://bugs.developers.facebook.net/show_bug.cgi?id=20472
OVERRIDE_COLUMN_INDEXABLE = collections.defaultdict(dict, {
    'connection': {'target_id': True},
    'friend_request': {'uid_from': True},
    'friendlist_member': {'uid': True},
    'like': {'user_id': True},
    'stream_filter': {'filter_key': True},
    })

# these aren't just flat tables, they're more complicated.
UNSUPPORTED_TABLES = ('insights', 'permissions', 'subscription')

# query snippets used in a few WHERE clauses for fetching FQL example data.
#
MY_IDS = 'id = me() OR id IN (SELECT uid2 FROM friend WHERE uid1 = me())'
MY_UIDS = 'uid = me() OR uid IN (SELECT uid2 FROM friend WHERE uid1 = me())'
MY_ALBUM_IDS = '(SELECT aid FROM album WHERE owner = me())'
MY_APP_IDS = \
    'app_id IN (SELECT application_id FROM developer WHERE developer_id = me())'
MY_PAGE_IDS = \
    'page_id IN (SELECT page_id FROM page_admin WHERE uid = me())'
MY_QUESTION_IDS = 'id in (SELECT id FROM question WHERE owner = me())'
MY_QUESTION_OPTION_IDS = \
    'option_id in (SELECT id FROM question_option WHERE %s)' % MY_QUESTION_IDS
MY_THREAD_IDS = \
    'thread_id IN (SELECT thread_id FROM thread where folder_id = 0)' # 0 is inbox

# maps table name to WHERE clause used in query for FQL example row(s) for that
# table, based on the access token's user. a None value means the table isn't
# currently supported.
FQL_DATA_WHERE_CLAUSES = {
  'album': 'owner = me()',
  'application': MY_APP_IDS,
  'apprequest': 'app_id = 145634995501895 AND recipient_uid = me()', # Graph API Explorer
  'checkin': 'author_uid = me()',
  'comment': 'post_id IN (SELECT post_id FROM stream WHERE source_id = me())',
  'comments_info': MY_APP_IDS,
  'connection': 'source_id = me()',
  'cookies': 'uid = me()',
  'developer': 'developer_id = me()',
  'domain': 'domain_id IN (SELECT domain_id FROM domain_admin WHERE owner_id = me())',
  'domain_admin': 'owner_id = me()',
  'event': 'eid in (SELECT eid FROM event_member WHERE uid = me())',
  'event_member': 'uid = me()',
  'family': 'profile_id = me()',
  'friend': 'uid1 = me()',
  'friend_request': 'uid_to = me()',
  'friendlist': 'owner = me()',
  'friendlist_member': 'flid in (SELECT flid FROM friendlist WHERE owner = me())',
  'group': 'gid IN (SELECT gid FROM group_member WHERE uid = me())',
  'group_member': 'uid = me()',
  'insights': None,  # not supported yet
  'like': 'user_id = me()',
  'link': 'owner = me()',
  'link_stat': 'url IN (SELECT url FROM link WHERE owner = me())',
  'mailbox_folder': '1',  # select all of the user's folders
  'message': MY_THREAD_IDS,
  'note': 'uid = me()',
  'notification': 'recipient_id = me()',
  'object_url': MY_IDS,
  'page': MY_PAGE_IDS,
  'page_admin': MY_UIDS,
  'page_blocked_user': MY_PAGE_IDS,
  'page_fan': 'uid = me()',
  'permissions': None,
  'permissions_info': 'permission_name = "read_stream"',
  'photo': 'aid IN %s' % MY_ALBUM_IDS,
  'photo_tag': 'subject = me()',
  'place': MY_PAGE_IDS,
  'privacy': 'id IN %s' % MY_ALBUM_IDS,
  'privacy_setting': None,
  'profile': MY_IDS,
  'question': 'owner = me()',
  'question_option': MY_QUESTION_IDS,
  'question_option_votes': MY_QUESTION_OPTION_IDS,
  'review': 'reviewer_id = me()',
  'standard_friend_info': None,  # these need an app access token
  'standard_user_info': None,
  'status': 'uid = me()',
  'stream': 'source_id = me()',
  'stream_filter': 'uid = me()',
  'stream_tag': 'actor_id = me()',
  'thread': MY_THREAD_IDS,
  'translation': None,  # not supported yet
  # these need an access token for an app where me() is a developer, which takes
  # more work than getting one from the graph explorer.
  'unified_message': None,
  'unified_thread': None,
  'unified_thread_action': None,
  'unified_thread_count': None,
  'url_like': 'user_id = me()',
  'user': MY_UIDS,
  'video': 'owner = me()',
  'video_tag': 'vid IN (SELECT vid FROM video WHERE owner = me())',
}

# Object IDs for example Graph API data.
GRAPH_DATA_IDS = [
  '10150146071791729', # album
  '145634995501895',   # application (Graph API Explorer)
  '19292868552_10150367816498553_19393342', # comment
  '10150150038100285', # domain (snarfed.org)
  '331218348435',      # event
  '195466193802264',   # group
  '19292868552_10150367816498553', # link
  '122788341354',      # note
  'platform',          # page
  '10150318315203553', # photo
  '19292868552_10150189643478553', # post
  '10150224661566729', # status
  'me',                # user
  '10100722614406743', # video
]

# Connections used to pull extra Graph API object ids based on the access
# token's user.
GRAPH_DATA_ID_CONNECTIONS = ('checkins', 'friendlists', 'accounts')

# names of connections that need special handling.
UNSUPPORTED_CONNECTIONS = (
  'mutualfriends',  # needs either /USER_ID suffix or other user's access token
  'payments',       # http://developers.facebook.com/docs/creditsapi/#getorders
  'subscriptions',  # http://developers.facebook.com/docs/reference/api/realtime/
  'insights',       # http://developers.facebook.com/docs/reference/api/insights/
  # Comment.likes gives the error described here:
  # http://stackoverflow.com/questions/7635627/facebook-graph-api-batch-requests-retrieve-comments-likes-error
  )

# global optparse.OptionValues that holds flags
options = None


def print_and_flush(str):
  """Prints str to stdout, without a newline, and flushes immediately.
  """
  sys.stdout.write(str)
  sys.stdout.flush()


def urlopen_with_retries(url, data=None):
  """Wrapper for urlopen that automatically retries on HTTP errors.

  If redirect is False and the url is 302 redirected, raises Redirected
  with the destination URL in the exception value.
  """
  for i in range(HTTP_RETRIES + 1):
    try:
      opened = urllib2.urlopen(url, data=data, timeout=HTTP_TIMEOUT_S)
      # if we ever need to determine whether we're redirected here, do something
      # like this:
      #
      # if opened.geturl() != url:
      #   ...
      #
      # it's not great - you can easily imagine failure cases - but it's by far
      # the simplest way. discussion: http://stackoverflow.com/questions/110498
      return opened

    except (IOError, urllib2.HTTPError), e:
      logging.debug('retrying due to %s' % e)

  print >> sys.stderr, 'Gave up on %s after %d tries. Last error:' % (
    url, HTTP_RETRIES)
  traceback.print_exc(file=sys.stderr)
  raise e


def make_column(table, column, raw_fb_type, indexable=None):
  """Populates and returns a Column for a schema.

  Args:
    table: string
    column: string
    raw_fb_type: string, type in facebook docs or graph api metadata field
    indexable: boolean, optional

  Returns: Column
  """
  fb_type, sqlite_type = COLUMN_TYPES.get(raw_fb_type.lower(), (None, None))
  if fb_type is None:
    print >> sys.stderr, 'TODO: %s.%s has unknown type %s' % (
      table, column, raw_fb_type)

  return schemautil.Column(name=column,
                           fb_type=fb_type,
                           sqlite_type=sqlite_type,
                           indexable=indexable)

def column_from_metadata_field(table, field):
  """Converts a Graph API metadata field JSON dict to a Column for a schema.

  Args:
    table: string
    field: JSON dict from object['metadata']['field'], where object is a JSON
      object retrieved from the Graph API with ?metadata=true

  Returns: Column
  """
  name = field['name']
  match = GRAPH_DESCRIPTION_TYPE_RE.search(field['description'])
  if match:
    fb_type = match.group(1)
  else:
    print >> sys.stderr, 'Could not determine type of %s.%s from %r.' % (
      table, name, field['description'])
    fb_type = ''

  return make_column(table, name, fb_type)


def scrape_schema(schema, url, column_re):
  """Scrapes a schema from FQL or Graph API docs.

  Args:
    schema: schemautil.Schema to fill in
    url: base docs page URL to start from
    column_re: regexp that matches a column in a table page. Should include
      these named groups: name, fb_type, indexable (optional)
  """
  print_and_flush('Generating %s' % schema.__class__.__name__)

  index_html = urlopen_with_retries(url).read()
  print_and_flush('.')

  links_html = TABLE_LINKS_RE.search(index_html).group()
  for link in TABLE_LINK_RE.findall(links_html):
    table_html = urlopen_with_retries(link).read()
    tables = TABLE_RE.findall(table_html)
    assert len(tables) == 1
    table = tables[0].strip()

    if table in UNSUPPORTED_TABLES:
      continue

    # column_re has three groups: indexable, name, type
    column_data = column_re.findall(table_html)
    column_names = [c[1] for c in column_data]
    override_types = OVERRIDE_COLUMN_TYPES[table]
    override_indexable = OVERRIDE_COLUMN_INDEXABLE[table]
    for name in set(override_types.keys()) | set(override_indexable.keys()):
      if name not in column_names:
        column_data.append(('', name, ''))

    # preserve the column order so it matches the docs
    columns = []
    for indexable, name, fb_type in column_data:
      name = name.lower()
      fb_type = OVERRIDE_COLUMN_TYPES[table].get(name, fb_type)
      indexable = override_indexable.get(name, indexable == '*')
      columns.append(make_column(table, name, fb_type, indexable=indexable))

    schema.tables[table] = tuple(columns)
    print_and_flush('.')

  print
  return schema


def fetch_fql_data(schema):
  """Downloads the FQL example data.

  Args:
    schema: schemautil.FqlSchema

  Returns:
    schemautil.FqlDataset
  """
  print_and_flush('Generating FQL example data')
  dataset = schemautil.FqlDataset(schema)
  where_clauses = FQL_DATA_WHERE_CLAUSES

  # preprocess where clauses. inject limits into subselects so that they return
  # the same results when querying the example data later, since it only has
  # the rows we downloaded.
  for table, query in where_clauses.items():
    if query:
      where_clauses[table] = re.sub(
        '([^(])\)$', '\\1 LIMIT %d)' % options.num_per_type, query)

  # build FQL queries. this dict maps url to (table, query) tuple.
  urls = {}
  for table, columns in sorted(schema.tables.items()):
    if table not in where_clauses:
      print >> sys.stderr, 'TODO: found new FQL table: %s' % table
      continue

    where = where_clauses[table]
    if not where:
      # we don't currently support fetching example data for this table
      continue

    select_columns = ', '.join(c.name for c in columns)
    query = 'SELECT %s FROM %s WHERE %s LIMIT %d' % (
        select_columns, table, where, options.num_per_type)
    url = 'method/fql.query?%s' % urllib.urlencode(
      {'query': query, 'format': 'json'})
    urls[url] = (table, query)

  # fetch data
  responses = batch_request(urls.keys())

  # store data
  for url, resp in responses.items():
    table, query = urls[url]
    dataset.data[table] = schemautil.Data(table=table, query=query, data=resp)

  print
  return dataset


def get_graph_ids():
  """Returns a list of Graph API ids/aliases to fetch as example data.

  This depends on the access token, --graph_ids, and --crawl_friends.
  """
  if options.graph_ids:
    return options.graph_ids
  elif options.crawl_friends:
    return [f['id'] for f in batch_request(['me/friends'])['me/friends']['data']]
  else:
    urls = ['me/%s?limit=%s' % (conn, options.num_per_type) for conn in GRAPH_DATA_ID_CONNECTIONS]
    conn_ids = []
    for resp in batch_request(urls).values():
        conn_ids.extend(item['id'] for item in resp['data'])
    return GRAPH_DATA_IDS + conn_ids


def fetch_graph_schema_and_data(ids):
  """Downloads the Graph API schema and example data.

  Args:
    ids: sequence of ids and/or aliases to download

  Returns: (schemautil.GraphSchema, schemautil.GraphDataset) tuple.
  """
  schema = schemautil.GraphSchema()
  dataset = schemautil.GraphDataset(schema)
  print_and_flush('Generating Graph API schema and example data')

  # fetch the objects
  objects = batch_request(ids, args={'metadata': 'true',
                                     'limit': options.num_per_type})

  # strip the metadata and generate and store the schema
  connections = []  # list of (name, url) tuples
  for id, object in objects.items():
    metadata = object.pop('metadata')

    if 'type' not in object:
      object['type'] = metadata['type']
    table = object.get('type')

    # columns
    fields = metadata.get('fields')
    if fields:
      schema.tables[table] = [column_from_metadata_field(table, f) for f in fields]

    # connections
    conns = metadata.get('connections')
    if conns:
      schema.connections[table] = conns.keys()
      connections.extend(conns.items())

  # store the objects in the dataset
  dataset.data = dict(
    (id, schemautil.Data(table=object['type'], query=id, data=object))
    for id, object in objects.items())

  conn_paths = [urlparse.urlparse(url).path
                for name, url in connections if name not in UNSUPPORTED_CONNECTIONS]
  results = batch_request(conn_paths, args={'limit': options.num_per_type})

  # store the connections in the dataset
  for path, result in results.items():
    path = path.strip('/')
    id, name = path.split('/')
    object = objects[id]
    dataset.connections[path] = schemautil.Connection(
      table=object['type'],
      # id may be an alias, so get the real numeric id
      id=object['id'],
      name=name,
      # strip all but the 'data' key/value
      data={'data': result['data']})

  print_and_flush('.')
  print
  return schema, dataset


# this code works fine, but it's been replaced with batch_request().
# it's still good though. keep it or dump it?
#
# def facebook_query(url=None, args=None, query=None, table=None):
#   """Makes an FQL or Graph API request.

#   Args:
#     url: string
#     args: dict of query parameters
#     query: value for the query field in the returned Data object
#     table: string

#   Returns:
#     schemautil.Data
#   """
#   parts = list(urlparse.urlparse(url))
#   args['access_token'] = options.access_token
#   for arg, vals in urlparse.parse_qs(parts[4]).items():
#     args[arg] = vals[0]
#   parts[4] = urllib.urlencode(args)

#   url = urlparse.urlunparse(parts)
#   result = json.loads(urlopen_with_retries(url).read())
#   assert 'error_code' not in result, 'FQL error:\n%s' % result
#   url = re.sub('access_token=[^&]+', 'access_token=XXX', url)

#   return schemautil.Data(table=table, query=query, url=url, data=result)


def batch_request(urls, args=None):
  """Makes a Graph API batch request.

  https://developers.facebook.com/docs/reference/api/batch/

  Args:
    urls: sequence of string relative url
    args: dict with extra query parameters for each individual request

  Returns: dict mapping string url to decoded JSON object. only includes the
    urls that succeeded.
  """
  print_and_flush('.')

  urls = list(urls)
  params = '?%s' % urllib.urlencode(args) if args else ''
  requests = [{'method': 'GET', 'relative_url': url + params} for url in urls]

  responses = []
  for i in range(0, len(requests), MAX_REQUESTS_PER_BATCH):
    data = urllib.urlencode({'access_token': options.access_token,
                             'batch': json.dumps(requests[i:i + 50])})
    response = urlopen_with_retries(options.graph_api_url, data=data)
    responses.extend(json.loads(response.read()))
    print_and_flush('.')

  assert len(responses) == len(requests)

  results = {}
  for url, resp in zip(urls, responses):
    if not resp:
      # no data for this request
      continue

    code = resp['code']
    body = resp['body']
    if code == 200:
      results[url] = json.loads(body)
    elif code == 302:
      headers = dict((h['name'], h['value']) for h in resp['headers'])
      results[url] = {'data': [headers['Location']]}
    else:
      print >> sys.stderr, 'Skipping %s due to %d error:\n%s' % (url, code, body)

  print_and_flush('.')
  return results


def parse_args():
  """Returns optparse.OptionValues with added access_token attr.
  """
  parser = optparse.OptionParser(
    usage='Usage: %prog [options] ACCESS_TOKEN',
    description="""\
Generates FQL and Graph API schemas and example data for mockfacebook.
You can get an access token here (grant it all permissions!):
http://developers.facebook.com/tools/explorer?method=GET&path=me""")

  parser.add_option(
    '--fql_docs_url', type='string',
    default='http://developers.facebook.com/docs/reference/fql/',
    help='Base URL for the Facebook FQL reference docs (default %default).')
  # only needed for facebook_query(), which is commented out above and may die.
  # parser.add_option(
  #   '--fql_url', type='string',
  #   default='https://api.facebook.com/method/fql.query',
  #   help='Facebook FQL API endpoint URL (default %default).')
  parser.add_option(
    '--graph_api_url', type='string',
    default='https://graph.facebook.com/',
    help='Facebook Graph API endpoint URL (default %default).')
  parser.add_option(
    '--num_per_type', type='int', default=3,
    help='max objects/connections to fetch per type (with some exceptions)')
  parser.add_option(
    '--fql_schema', action='store_true', dest='fql_schema', default=False,
    help="Scrape the FQL schema instead of using the existing schema file.")
  parser.add_option(
    '--fql_data', action='store_true', dest='fql_data', default=False,
    help="Generate FQL example data.")
  parser.add_option(
    '--no_graph', action='store_false', dest='graph', default=True,
    help="Don't generate Graph API schema or data. Use the existing files instead.")
  parser.add_option(
    '--graph_ids', type='string', dest='graph_ids', default=None,
    help='comma separated list of Graph API ids/aliases to download.')
  parser.add_option(
    '--crawl_friends', action='store_true', dest='crawl_friends', default=False,
    help='follow and download friends of the current user. Graph API data only.')
  parser.add_option(
    '--db_file', type='string', default=schemautil.DEFAULT_DB_FILE,
    help='SQLite database file (default %default). Set to the empty string to prevent writing a database file.')

  options, args = parser.parse_args()
  logging.debug('Command line options: %s' % options)

  if len(args) != 1:
    parser.print_help()
    sys.exit(1)
  elif options.crawl_friends and options.graph_ids:
    print >> sys.stderr, '--crawl_friends and --graph_ids are mutually exclusive.'
    sys.exit(1)

  if options.graph_ids:
    options.graph_ids = options.graph_ids.split(',')

  options.access_token = args[0]
  return options


def main():
  global options
  options = parse_args()

  if options.db_file:  # FIXME - should do dupe checking
    sql = 'INSERT INTO oauth_access_tokens(code, token) VALUES("asdf", "%s");' % options.access_token
    schemautil.get_db(options.db_file).executescript(sql)

  if options.fql_schema:
    fql_schema = schemautil.FqlSchema()
    scrape_schema(fql_schema, options.fql_docs_url, FQL_COLUMN_RE)
    fql_schema.write()
  else:
    fql_schema = schemautil.FqlSchema.read()

  if options.fql_data:
    dataset = fetch_fql_data(fql_schema)
    dataset.write(db_file=options.db_file)

  if options.graph:
    ids = get_graph_ids()
    schema, dataset = fetch_graph_schema_and_data(ids)
    schema.write()
    dataset.write(db_file=options.db_file)



if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = fql
"""FQL request handler and support classes.

Based on https://developers.facebook.com/docs/reference/fql/ .
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import logging
import re
import json
import sqlite3
import time

import sqlparse
from sqlparse import sql
from sqlparse import tokens
import webapp2

import oauth
import schemautil


class FqlError(Exception):
  """Base error class.

  Attributes:
    code: integer error_code
    msg: string error_msg
  """
  code = None
  msg = None

  def __init__(self, *args):
    self.msg = self.msg % args

class UnexpectedError(FqlError):
  code = 601
  msg = "Parser error: unexpected '%s' at position <not implemented>."

class UnexpectedEndError(FqlError):
  code = 601
  msg = 'Parser error: unexpected end of query.'

class WildcardError(FqlError):
  code = 601
  msg = 'Parser error: SELECT * is not supported.  Please manually list the columns you are interested in.'

class NotIndexableError(FqlError):
  code = 604
  msg = 'Your statement is not indexable. The WHERE clause must contain an indexable column. Such columns are marked with * in the tables linked from http://developers.facebook.com/docs/reference/fql '

class InvalidFunctionError(FqlError):
  code = 605
  msg = '%s is not a valid function name.'

class ParamMismatchError(FqlError):
  code = 606
  msg = '%s function expects %d parameters; %d given.'

class SqliteError(FqlError):
  code = -1
  msg = 'SQLite error: %s'

class MissingParamError(FqlError):
  code = -1
  msg = 'The parameter %s is required'

class InvalidAccessTokenError(FqlError):
  code = 190
  msg = 'Invalid access token signature.'


class Fql(object):
  """A parsed FQL statement. Just a thin wrapper around sqlparse.sql.Statement.

  Attributes:
    query: original FQL query string
    me: integer, the user id that me() should return
    schema: schemautil.FqlSchema
    Statement: sqlparse.sql.Statement
    table: sql.Token or None
    where: sql.Where or None
  """

  # FQL functions. Maps function name to expected number of parameters.
  FUNCTIONS = {
    'me': 0,
    'now': 0,
    'strlen': 1,
    'substr': 3,
    'strpos': 2,
    }

  def __init__(self, schema, query, me):
    """Args:
      query: FQL statement
      me: integer, the user id that me() should return
    """
    logging.debug('parsing %s' % query)
    self.schema = schema
    self.query = query
    self.me = me
    self.statement = stmt = sqlparse.parse(query)[0]

    # extract table and WHERE clause, if any
    self.table = None
    self.where = None

    from_ = stmt.token_next_match(0, tokens.Keyword, 'FROM')
    if from_:
      index = stmt.token_index(from_)
      self.table = stmt.token_next(index)
      if self.table.is_group():
        self.table = self.table.token_first()

    self.where = stmt.token_next_by_instance(0, sql.Where)

    logging.debug('table %s, where %s' % (self.table, self.where))

  def table_name(self):
    """Returns the table name, or '' if None.
    """
    if self.table:
      return self.table.value
    else:
      return ''

  def validate(self):
    """Checks the query for Facebook API semantic errors.

    Returns the error response string if there is an error, otherwise None.
    """
    first = self.statement.tokens[0].value
    if first != 'SELECT':
      raise UnexpectedError(first)
    elif self.statement.token_next(1).match(tokens.Wildcard, '*'):
      raise WildcardError()
    elif not self.where:
      raise UnexpectedEndError()
    elif not self.table:
      raise UnexpectedError('WHERE')

    def check_indexable(token_list):
      """Recursive function that checks for non-indexable columns."""
      for tok in token_list.tokens:
        if tok.ttype == tokens.Name:
          col = self.schema.get_column(self.table.value, tok.value)
          if col and not col.indexable:
            raise NotIndexableError()
        elif isinstance(tok, (sql.Comparison, sql.Identifier)):
          check_indexable(tok)

    check_indexable(self.where)

  def to_sqlite(self):
    """Converts to a SQLite query.

    Specifically:
    - validates
    - processes functions
    - prefixes table names with underscores
    """
    self.validate()
    self.process_functions()
    self.table.value = '`%s`' % self.table.value
    return self.statement.to_unicode()

  def process_functions(self, group=None):
    """Recursively parse and process FQL functions in the given group token.

    TODO: switch to sqlite3.Connection.create_function().

    Currently handles: me(), now()
    """
    if group is None:
      group = self.statement

    for tok in group.tokens:
      if isinstance(tok, sql.Function):
        assert isinstance(tok.tokens[0], sql.Identifier)
        name = tok.tokens[0].tokens[0]
        if name.value not in Fql.FUNCTIONS:
          raise InvalidFunctionError(name.value)

        # check number of params
        #
        # i wish i could use tok.get_parameters() here, but it doesn't work
        # with string parameters for some reason. :/
        assert isinstance(tok.tokens[1], sql.Parenthesis)
        params = [t for t in tok.tokens[1].flatten()
                  if t.ttype not in (tokens.Punctuation, tokens.Whitespace)]
        actual_num = len(params)
        expected_num = Fql.FUNCTIONS[name.value]
        if actual_num != expected_num:
          raise ParamMismatchError(name.value, expected_num, actual_num)

        # handle each function
        replacement = None
        if name.value == 'me':
          replacement = str(self.me)
        elif name.value == 'now':
          replacement = str(int(time.time()))
        elif name.value == 'strlen':
          # pass through to sqlite's length() function
          name.value = 'length'
        elif name.value == 'substr':
          # the index param is 0-based in FQL but 1-based in sqlite
          params[1].value = str(int(params[1].value) + 1)
        elif name.value == 'strpos':
          # strip quote chars
          string = params[0].value[1:-1]
          sub = params[1].value[1:-1]
          replacement = str(string.find(sub))
        else:
          # shouldn't happen
          assert False, 'unknown function: %s' % name.value

        if replacement is not None:
          tok.tokens = [sql.Token(tokens.Number, replacement)]

      elif tok.is_group():
        self.process_functions(tok)


class FqlHandler(webapp2.RequestHandler):
  """The FQL request handler.

  Not thread safe!

  Class attributes:
    conn: sqlite3.Connection
    me: integer, the user id that me() should return
    schema: schemautil.FqlSchema
  """

  XML_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<fql_query_response xmlns="http://api.facebook.com/1.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" list="true">
%s
</fql_query_response>"""
  XML_ERROR_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<error_response xmlns="http://api.facebook.com/1.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://api.facebook.com/1.0/ http://api.facebook.com/1.0/facebook.xsd">
%s
</error_response>"""

  ROUTES = [(r'/method/fql.query/?', 'fql.FqlHandler'),
            ('/fql', 'fql.FqlHandler'),
            ]

  @classmethod
  def init(cls, conn, me):
    """Args:
      conn: sqlite3.Connection
      me: integer, the user id that me() should return
    """
    cls.conn = conn
    cls.me = me
    cls.schema = schemautil.FqlSchema.read()

  def get(self):
    table = ''
    graph_endpoint = (self.request.path == '/fql')

    try:
      query_arg = 'q' if graph_endpoint else 'query'
      query = self.request.get(query_arg)
      if not query:
        raise MissingParamError(query_arg)

      token =  self.request.get('access_token')
      if token and not oauth.AccessTokenHandler.is_valid_token(self.conn, token):
        raise InvalidAccessTokenError()

      logging.debug('Received FQL query: %s' % query)

      fql = Fql(self.schema, query, self.me)
      # grab the table name before it gets munged
      table = fql.table_name()
      sqlite = fql.to_sqlite()
      logging.debug('Running SQLite query: %s' % sqlite)

      try:
        cursor = self.conn.execute(sqlite)
      except sqlite3.OperationalError, e:
        logging.debug('SQLite error: %s', e)
        raise SqliteError(unicode(e))

      results = self.schema.sqlite_to_json(cursor, table)

    except FqlError, e:
      results = self.error(self.request.GET, e.code, e.msg)

    if self.request.get('format') == 'json' or graph_endpoint:
      json.dump(results, self.response.out, indent=2)
    else:
      self.response.out.write(self.render_xml(results, table))

    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'

  def render_xml(self, results, table):
    """Renders a query result into an XML string response.

    Args:
      results: dict mapping strings to strings or lists of (key, value) tuples
      table: string table name
    """
    if 'error_code' in results:
      template = self.XML_ERROR_TEMPLATE
      results['request_args'] = [{'arg': elem} for elem in results['request_args']]
    else:
      template = self.XML_TEMPLATE
      results = [{table: row} for row in results]

    return template % self.render_xml_part(results)

  def render_xml_part(self, results):
    """Recursively renders part of a query result into an XML string response.

    Args:
      results: dict or list or primitive
    """

    if isinstance(results, (list, tuple)):
      return '\n'.join([self.render_xml_part(elem) for elem in results])
    elif isinstance(results, dict):
      elems = []
      for key, val in results.iteritems():
        list_attr = ' list="true"' if isinstance(val, list) else ''
        br = '\n' if isinstance(val, (list, dict)) else ''
        rendered = self.render_xml_part(val)
        elems.append('<%(key)s%(list_attr)s>%(br)s%(rendered)s%(br)s</%(key)s>' %
                     locals())
      return '\n'.join(elems)
    else:
      return unicode(results)

  def error(self, args, code, msg):
    """Renders an error response.

    Args:
      args: dict, the parsed URL query string arguments
      code: integer, the error_code
      msg: string, the error_msg

    Returns: the response string
    """
    args['method'] = 'fql.query'  # (always)
    request_args = [{'key': key, 'value': val} for key, val in args.items()]
    return {'error_code': code,
            'error_msg': msg,
            'request_args': request_args,
            }

########NEW FILE########
__FILENAME__ = fql_schema
# Do not edit! Generated automatically by mockfacebook.
# https://github.com/rogerhu/mockfacebook
# 2012-10-23 22:34:02.059169

{'tables': {'album': (Column(name='aid', fb_type='string', sqlite_type='TEXT', indexable=True),
                      Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='cover_pid', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='cover_object_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='created', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='modified', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='location', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='size', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='link', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='visible', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='modified_major', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='edit_link', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='can_upload', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                      Column(name='photo_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='video_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='like_info', fb_type='object', sqlite_type='', indexable=False),
                      Column(name='comment_info', fb_type='object', sqlite_type='', indexable=False)),
            'application': (Column(name='app_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='api_key', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='namespace', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='display_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='icon_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='logo_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='company_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='developers', fb_type='object', sqlite_type='', indexable=False),
                            Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='daily_active_users', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='weekly_active_users', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='monthly_active_users', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='category', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='subcategory', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='is_facebook_app', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='restriction_info', fb_type='object', sqlite_type='', indexable=False),
                            Column(name='app_domains', fb_type='array', sqlite_type='', indexable=False),
                            Column(name='auth_dialog_data_help_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='auth_dialog_description', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='auth_dialog_headline', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='auth_dialog_perms_explanation', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='auth_referral_user_perms', fb_type='array', sqlite_type='', indexable=False),
                            Column(name='auth_referral_friend_perms', fb_type='array', sqlite_type='', indexable=False),
                            Column(name='auth_referral_default_activity_privacy', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='auth_referral_enabled', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='auth_referral_extended_perms', fb_type='array', sqlite_type='', indexable=False),
                            Column(name='auth_referral_response_type', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='canvas_fluid_height', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='canvas_fluid_width', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='canvas_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='contact_email', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                            Column(name='creator_uid', fb_type='int', sqlite_type='INTEGER', indexable=False),
                            Column(name='deauth_callback_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='iphone_app_store_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='hosting_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='mobile_web_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='page_tab_default_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='page_tab_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='privacy_policy_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='secure_canvas_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='secure_page_tab_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='server_ip_whitelist', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='social_discovery', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='terms_of_service_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='update_ip_whitelist', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='user_support_email', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='user_support_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='website_url', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'apprequest': (Column(name='request_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='app_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='recipient_uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='sender_uid', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='data', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'checkin': (Column(name='checkin_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='author_uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='page_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='post_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='coords', fb_type='array', sqlite_type='', indexable=False),
                        Column(name='timestamp', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='tagged_uids', fb_type='array', sqlite_type='', indexable=False),
                        Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'comment': (Column(name='xid', fb_type='string', sqlite_type='TEXT', indexable=True),
                        Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='post_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                        Column(name='fromid', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='text', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='id', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='username', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='reply_xid', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='post_fbid', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='likes', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='comments', fb_type='array', sqlite_type='', indexable=False),
                        Column(name='can_like', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                        Column(name='user_likes', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                        Column(name='text_tags', fb_type='array', sqlite_type='', indexable=False),
                        Column(name='is_private', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'comments_info': (Column(name='app_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                              Column(name='xid', fb_type='string', sqlite_type='TEXT', indexable=False),
                              Column(name='count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                              Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'connection': (Column(name='source_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                           Column(name='target_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                           Column(name='target_type', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='is_following', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'cookies': (Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                        Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='value', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='expires', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='path', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'developer': (Column(name='developer_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='application_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='role', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'domain': (Column(name='domain_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='domain_name', fb_type='string', sqlite_type='TEXT', indexable=True)),
            'domain_admin': (Column(name='owner_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                             Column(name='domain_id', fb_type='string', sqlite_type='TEXT', indexable=True)),
            'event': (Column(name='eid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic_square', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='host', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='start_time', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='end_time', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='creator', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='update_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='location', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='venue', fb_type='object', sqlite_type='', indexable=False),
                      Column(name='privacy', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='hide_guest_list', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                      Column(name='can_invite_friends', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                      Column(name='all_members_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='attending_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='unsure_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='declined_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='not_replied_count', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'event_member': (Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                             Column(name='eid', fb_type='string', sqlite_type='TEXT', indexable=True),
                             Column(name='rsvp_status', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='start_time', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'family': (Column(name='profile_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='birthday', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='relationship', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'friend': (Column(name='uid1', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='uid2', fb_type='string', sqlite_type='TEXT', indexable=True)),
            'friend_request': (Column(name='uid_to', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='uid_from', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='unread', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'friendlist': (Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=True),
                           Column(name='flid', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'friendlist_member': (Column(name='flid', fb_type='string', sqlite_type='TEXT', indexable=True),
                                  Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True)),
            'group': (Column(name='gid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='nid', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='pic_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='pic', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='group_type', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='group_subtype', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='recent_news', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='creator', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='update_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='office', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='website', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='venue', fb_type='object', sqlite_type='', indexable=False),
                      Column(name='privacy', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='icon', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='icon34', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='icon68', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='email', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='version', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'group_member': (Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                             Column(name='gid', fb_type='string', sqlite_type='TEXT', indexable=True),
                             Column(name='administrator', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                             Column(name='positions', fb_type='object', sqlite_type='', indexable=False),
                             Column(name='unread', fb_type='int', sqlite_type='INTEGER', indexable=False),
                             Column(name='bookmark_order', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'like': (Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='post_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='user_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='object_type', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'link': (Column(name='link_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='owner_comment', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='title', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='summary', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='picture', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='image_urls', fb_type='array', sqlite_type='', indexable=False)),
            'link_stat': (Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='normalized_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                          Column(name='share_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='like_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='comment_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='total_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='click_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='comments_fbid', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='commentsbox_count', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'location_post': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                              Column(name='author_uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                              Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                              Column(name='timestamp', fb_type='int', sqlite_type='INTEGER', indexable=False),
                              Column(name='tagged_uids', fb_type='array', sqlite_type='', indexable=True),
                              Column(name='page_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                              Column(name='page_type', fb_type='string', sqlite_type='TEXT', indexable=False),
                              Column(name='coords', fb_type='object', sqlite_type='', indexable=False),
                              Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'mailbox_folder': (Column(name='folder_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='viewer_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='unread_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='total_count', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'message': (Column(name='message_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                        Column(name='thread_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                        Column(name='author_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='body', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='attachment', fb_type='array', sqlite_type='', indexable=False),
                        Column(name='viewer_id', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'note': (Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='note_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='content', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='content_html', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='title', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='like_info', fb_type='object', sqlite_type='', indexable=False),
                     Column(name='comment_info', fb_type='object', sqlite_type='', indexable=False)),
            'notification': (Column(name='notification_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='sender_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                             Column(name='recipient_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                             Column(name='title_html', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='title_text', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='body_html', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='body_text', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='href', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                             Column(name='is_unread', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                             Column(name='is_hidden', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                             Column(name='object_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='object_type', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='icon_url', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'object_url': (Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                           Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                           Column(name='site', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'offer': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='owner_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='title', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='image_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='terms', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='claim_limit', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='expiration_time', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'page': (Column(name='page_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='username', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='page_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='categories', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='is_community_page', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='pic_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_square', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_large', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_cover', fb_type='object', sqlite_type='', indexable=False),
                     Column(name='unread_notif_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='new_like_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='fan_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='global_brand_like_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='global_brand_talking_about_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='global_brand_parent_page_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='website', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='has_added_app', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='general_info', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='can_post', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='checkins', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='is_published', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='founded', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='company_overview', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='mission', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='products', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='location', fb_type='object', sqlite_type='', indexable=False),
                     Column(name='parking', fb_type='object', sqlite_type='', indexable=False),
                     Column(name='hours', fb_type='object', sqlite_type='', indexable=False),
                     Column(name='pharma_safety_info', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='public_transit', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='attire', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='payment_options', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='culinary_team', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='general_manager', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='price_range', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='restaurant_services', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='restaurant_specialties', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='phone', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='release_date', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='genre', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='starring', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='screenplay_by', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='directed_by', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='produced_by', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='studio', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='awards', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='plot_outline', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='season', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='network', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='schedule', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='written_by', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='band_members', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='hometown', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='current_location', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='record_label', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='booking_agent', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='press_contact', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='artists_we_like', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='influences', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='band_interests', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='bio', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='affiliation', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='birthday', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='personal_info', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='personal_interests', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='built', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='features', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='mpg', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'page_admin': (Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='page_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'page_blocked_user': (Column(name='page_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                  Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'page_fan': (Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                         Column(name='page_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                         Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                         Column(name='profile_section', fb_type='string', sqlite_type='TEXT', indexable=False),
                         Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'page_global_brand_child': (Column(name='parent_page_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                        Column(name='global_brand_child_page_id', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'page_milestone': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                               Column(name='owner_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                               Column(name='title', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='start_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='end_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'permissions_info': (Column(name='permission_name', fb_type='string', sqlite_type='TEXT', indexable=True),
                                 Column(name='header', fb_type='string', sqlite_type='TEXT', indexable=False),
                                 Column(name='summary', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'photo': (Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='pid', fb_type='string', sqlite_type='TEXT', indexable=True),
                      Column(name='aid', fb_type='string', sqlite_type='TEXT', indexable=True),
                      Column(name='owner', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='src_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='src_small_width', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='src_small_height', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='src_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='src_big_width', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='src_big_height', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='src', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='src_width', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='src_height', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='link', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='caption', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='caption_tags', fb_type='array', sqlite_type='', indexable=False),
                      Column(name='created', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='modified', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='position', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='album_object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='place_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='images', fb_type='array', sqlite_type='', indexable=False),
                      Column(name='like_info', fb_type='object', sqlite_type='', indexable=False),
                      Column(name='comment_info', fb_type='object', sqlite_type='', indexable=False),
                      Column(name='can_delete', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'photo_src': (Column(name='photo_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                          Column(name='size', fb_type='string', sqlite_type='TEXT', indexable=False),
                          Column(name='width', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='height', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='src', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'photo_tag': (Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                          Column(name='pid', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='subject', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='text', fb_type='string', sqlite_type='TEXT', indexable=False),
                          Column(name='xcoord', fb_type='float', sqlite_type='REAL', indexable=False),
                          Column(name='ycoord', fb_type='float', sqlite_type='REAL', indexable=False),
                          Column(name='created', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'place': (Column(name='page_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='geometry', fb_type='array', sqlite_type='', indexable=False),
                      Column(name='latitude', fb_type='float', sqlite_type='REAL', indexable=False),
                      Column(name='longitude', fb_type='float', sqlite_type='REAL', indexable=False),
                      Column(name='checkin_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='display_subtext', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'privacy': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='value', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='allow', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='deny', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='owner_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='networks', fb_type='int', sqlite_type='INTEGER', indexable=False),
                        Column(name='friends', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'privacy_setting': (Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=True),
                                Column(name='value', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='allow', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='deny', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='networks', fb_type='int', sqlite_type='INTEGER', indexable=False),
                                Column(name='friends', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'profile': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                        Column(name='can_post', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                        Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='pic', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='pic_square', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='pic_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='pic_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='pic_crop', fb_type='object', sqlite_type='', indexable=False),
                        Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                        Column(name='username', fb_type='string', sqlite_type='TEXT', indexable=True)),
            'profile_pic': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                            Column(name='width', fb_type='int', sqlite_type='INTEGER', indexable=True),
                            Column(name='height', fb_type='int', sqlite_type='INTEGER', indexable=True),
                            Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='is_silhouette', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                            Column(name='real_width', fb_type='int', sqlite_type='INTEGER', indexable=False),
                            Column(name='real_height', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'profile_view': (Column(name='profile_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                             Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                             Column(name='link', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='custom_image_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                             Column(name='position', fb_type='int', sqlite_type='INTEGER', indexable=False),
                             Column(name='is_permanent', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'question': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                         Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=True),
                         Column(name='question', fb_type='string', sqlite_type='TEXT', indexable=False),
                         Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                         Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'question_option': (Column(name='id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                Column(name='question_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='votes', fb_type='int', sqlite_type='INTEGER', indexable=False),
                                Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                                Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=False),
                                Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'question_option_votes': (Column(name='option_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                      Column(name='voter_id', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'review': (Column(name='reviewee_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='reviewer_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='review_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='rating', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'standard_friend_info': (Column(name='uid1', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                     Column(name='uid2', fb_type='int', sqlite_type='INTEGER', indexable=True)),
            'standard_user_info': (Column(name='uid', fb_type='string', sqlite_type='TEXT', indexable=True),
                                   Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=True),
                                   Column(name='username', fb_type='string', sqlite_type='TEXT', indexable=True),
                                   Column(name='third_party_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                   Column(name='first_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='last_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='locale', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='affiliations', fb_type='array', sqlite_type='', indexable=False),
                                   Column(name='profile_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='timezone', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='birthday', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='sex', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='proxied_email', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='current_location', fb_type='string', sqlite_type='TEXT', indexable=False),
                                   Column(name='allowed_restrictions', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'status': (Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='status_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='source', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='place_id', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'stream': (Column(name='post_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='viewer_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='app_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='source_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='filter_key', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='attribution', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='actor_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='target_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='message', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='app_data', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='action_links', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='attachment', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='impressions', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='comments', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='likes', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='place', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='privacy', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='permalink', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='xid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                       Column(name='tagged_ids', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='message_tags', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='description_tags', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='type', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'stream_filter': (Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                              Column(name='filter_key', fb_type='string', sqlite_type='TEXT', indexable=True),
                              Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                              Column(name='rank', fb_type='int', sqlite_type='INTEGER', indexable=False),
                              Column(name='icon_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                              Column(name='is_visible', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                              Column(name='type', fb_type='string', sqlite_type='TEXT', indexable=False),
                              Column(name='value', fb_type='int', sqlite_type='INTEGER', indexable=False)),
            'stream_tag': (Column(name='post_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='actor_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                           Column(name='target_id', fb_type='string', sqlite_type='TEXT', indexable=True)),
            'thread': (Column(name='thread_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='folder_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                       Column(name='subject', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='recipients', fb_type='array', sqlite_type='', indexable=False),
                       Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='parent_message_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='parent_thread_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='message_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='snippet', fb_type='string', sqlite_type='TEXT', indexable=False),
                       Column(name='snippet_author', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='object_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='unread', fb_type='int', sqlite_type='INTEGER', indexable=False),
                       Column(name='viewer_id', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'translation': (Column(name='locale', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='native_hash', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='native_string', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='translation', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='approval_status', fb_type='string', sqlite_type='TEXT', indexable=False),
                            Column(name='pre_hash_string', fb_type='string', sqlite_type='TEXT', indexable=True),
                            Column(name='best_string', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'unified_message': (Column(name='message_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                Column(name='thread_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                Column(name='subject', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='body', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='unread', fb_type='bool', sqlite_type='INTEGER', indexable=True),
                                Column(name='action_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='timestamp', fb_type='string', sqlite_type='TEXT', indexable=True),
                                Column(name='tags', fb_type='array', sqlite_type='', indexable=False),
                                Column(name='sender', fb_type='object', sqlite_type='', indexable=False),
                                Column(name='recipients', fb_type='array', sqlite_type='', indexable=False),
                                Column(name='object_sender', fb_type='object', sqlite_type='', indexable=False),
                                Column(name='html_body', fb_type='string', sqlite_type='TEXT', indexable=False),
                                Column(name='attachments', fb_type='array', sqlite_type='', indexable=False),
                                Column(name='attachment_map', fb_type='array', sqlite_type='', indexable=False),
                                Column(name='shares', fb_type='array', sqlite_type='', indexable=False),
                                Column(name='share_map', fb_type='array', sqlite_type='', indexable=False)),
            'unified_thread': (Column(name='action_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='archived', fb_type='bool', sqlite_type='INTEGER', indexable=True),
                               Column(name='can_reply', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                               Column(name='folder', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='former_participants', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='has_attachments', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                               Column(name='is_subscribed', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                               Column(name='last_visible_add_action_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='num_messages', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='num_unread', fb_type='int', sqlite_type='INTEGER', indexable=False),
                               Column(name='object_participants', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='participants', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='senders', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='single_recipient', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='snippet', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='snippet_sender', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='snippet_message_has_attachment', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                               Column(name='subject', fb_type='string', sqlite_type='TEXT', indexable=False),
                               Column(name='tags', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='thread_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='thread_participants', fb_type='array', sqlite_type='', indexable=False),
                               Column(name='timestamp', fb_type='string', sqlite_type='TEXT', indexable=True),
                               Column(name='unread', fb_type='bool', sqlite_type='INTEGER', indexable=True)),
            'unified_thread_action': (Column(name='action_id', fb_type='string', sqlite_type='TEXT', indexable=False),
                                      Column(name='actor', fb_type='object', sqlite_type='', indexable=False),
                                      Column(name='thread_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                                      Column(name='timestamp', fb_type='string', sqlite_type='TEXT', indexable=False),
                                      Column(name='type', fb_type='int', sqlite_type='INTEGER', indexable=False),
                                      Column(name='users', fb_type='array', sqlite_type='', indexable=False)),
            'unified_thread_count': (Column(name='folder', fb_type='string', sqlite_type='TEXT', indexable=True),
                                     Column(name='unread_count', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                     Column(name='unseen_count', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                     Column(name='last_action_id', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                     Column(name='last_seen_time', fb_type='int', sqlite_type='INTEGER', indexable=True),
                                     Column(name='total_threads', fb_type='int', sqlite_type='INTEGER', indexable=True)),
            'url_like': (Column(name='user_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                         Column(name='url', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'user': (Column(name='uid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                     Column(name='username', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='first_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='middle_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='last_name', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='name', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='pic_small', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_big', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_square', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='affiliations', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='profile_update_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='timezone', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='religion', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='birthday', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='birthday_date', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='devices', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='sex', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='hometown_location', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='meeting_sex', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='meeting_for', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='relationship_status', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='significant_other_id', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='political', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='current_location', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='activities', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='interests', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='is_app_user', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='music', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='tv', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='movies', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='books', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='quotes', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='about_me', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='hs_info', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='education_history', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='work_history', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='notes_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='wall_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='status', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='has_added_app', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='online_presence', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='locale', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='proxied_email', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='profile_url', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='email_hashes', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='pic_small_with_logo', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_big_with_logo', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_square_with_logo', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_with_logo', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='pic_cover', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='allowed_restrictions', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='verified', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='profile_blurb', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='family', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='website', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='is_blocked', fb_type='bool', sqlite_type='INTEGER', indexable=False),
                     Column(name='contact_email', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='email', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='third_party_id', fb_type='string', sqlite_type='TEXT', indexable=True),
                     Column(name='name_format', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='video_upload_limits', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='games', fb_type='string', sqlite_type='TEXT', indexable=False),
                     Column(name='work', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='education', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='sports', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='favorite_athletes', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='favorite_teams', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='inspirational_people', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='languages', fb_type='array', sqlite_type='', indexable=False),
                     Column(name='likes_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='friend_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='mutual_friend_count', fb_type='int', sqlite_type='INTEGER', indexable=False),
                     Column(name='can_post', fb_type='bool', sqlite_type='INTEGER', indexable=False)),
            'video': (Column(name='vid', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='owner', fb_type='int', sqlite_type='INTEGER', indexable=True),
                      Column(name='title', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='description', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='link', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='thumbnail_link', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='embed_html', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                      Column(name='length', fb_type='float', sqlite_type='REAL', indexable=False),
                      Column(name='src', fb_type='string', sqlite_type='TEXT', indexable=False),
                      Column(name='src_hq', fb_type='string', sqlite_type='TEXT', indexable=False)),
            'video_tag': (Column(name='vid', fb_type='string', sqlite_type='TEXT', indexable=True),
                          Column(name='subject', fb_type='int', sqlite_type='INTEGER', indexable=True),
                          Column(name='updated_time', fb_type='int', sqlite_type='INTEGER', indexable=False),
                          Column(name='created_time', fb_type='int', sqlite_type='INTEGER', indexable=False))}}

########NEW FILE########
__FILENAME__ = fql_test
#!/usr/bin/python
"""Unit tests for fql.py.

TODO: test subselects, other advanced features
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import httplib
import json
import threading
import time
import traceback
import unittest
import urllib

import fql
import schemautil
import testutil


def insert_test_data(conn):
  """Args:
    conn: SQLite connection
  """
  conn.executescript("""
INSERT INTO profile(id, username, can_post, pic_crop)
  VALUES(1, 'alice', 1, '{"right": 1, "bottom": 2, "uri": "http://picture/url"}');
INSERT INTO page(name, categories) VALUES('my_page', '["foo", "bar"]');
""")
  conn.commit()


class FqlTest(unittest.TestCase):

  schema = schemautil.FqlSchema.read()

  def fql(self, query):
    return fql.Fql(self.schema, query, 1)

  def test_table(self):
    self.assertEquals(None, self.fql('SELECT *').table)
    self.assertEquals('foo', self.fql('SELECT * FROM foo').table.value)
    self.assertEquals(None, self.fql('SELECT * WHERE x').table)

    # table names that are keywords should still work
    self.assertEquals('comment', self.fql('SELECT * FROM comment').table.value)

  def test_where(self):
    self.assertEquals(None, self.fql('SELECT *').where)
    self.assertEquals(None, self.fql('SELECT * FROM foo').where)

    for query in ('SELECT * FROM foo WHERE bar', 'SELECT * WHERE bar'):
      where = self.fql(query).where
      self.assertEquals('WHERE', where.tokens[0].value)
      self.assertEquals('bar', where.tokens[2].get_name())


class FqlHandlerTest(testutil.HandlerTest):

  def setUp(self):
    super(FqlHandlerTest, self).setUp(fql.FqlHandler)
    insert_test_data(self.conn)

  def expect_fql(self, fql, expected, args=None):
    """Runs an FQL query and checks the response.

    Args:
      fql: string
      expected: list or dict that the JSON response should match
      args: dict, extra query parameters
    """
    full_args = {'format': 'json', 'query': fql}
    if args:
      full_args.update(args)
    self.expect('/method/fql.query', expected, full_args)

  def expect_error(self, query, error, args=None):
    """Runs a query and checks that it returns the given error code and message.

    Args:
      fql: string
      error: expected error
      args: dict, extra query parameters
    """
    request_args = {'format': 'json', 'query': query, 'method': 'fql.query'}
    if args:
      request_args.update(args)

    expected = {
      'error_code': error.code,
      'error_msg': error.msg,
      'request_args': [{'key': k, 'value': v} for k, v in request_args.items()],
      }
    self.expect_fql(query, expected, args=args)

  def test_example_data(self):
    dataset = testutil.maybe_read(schemautil.FqlDataset)
    if not dataset:
      return

    self.conn.executescript(dataset.to_sql())
    self.conn.commit()
    fql.FqlHandler.me = dataset.data['user'].data[0]['uid']
    passed = True

    for table, data in dataset.data.items():
      try:
        self.expect_fql(data.query, data.data)
      except Exception:
        passed = False
        print 'Table: %s' % table
        traceback.print_exc()

    self.assertTrue(passed)

  def test_graph_endpoint(self):
    args = {'q': 'SELECT id FROM profile WHERE username = "alice"'}
    expected = [{'id': 1}]
    self.expect('/fql', expected, args)

    # this endpoint doesn't support XML format
    args['format'] = 'xml'
    self.expect('/fql', expected, args)

  def test_multiple_where_conditions(self):
    self.expect_fql(
      'SELECT username FROM profile WHERE id = me() AND username = "alice"',
      [{'username': 'alice'}])

  def test_me_function(self):
    query = 'SELECT username FROM profile WHERE id = me()'
    self.expect_fql(query, [{'username': 'alice'}])

    # try a different value for me()
    fql.FqlHandler.init(self.conn, int(self.ME) + 1)
    self.expect_fql(query, [])

  def test_now_function(self):
    orig_time = time.time
    try:
      time.time = lambda: 3.14
      self.expect_fql('SELECT now() FROM profile WHERE id = me()',
                      [{'3': 3}])
    finally:
      time.time = orig_time

  def test_strlen_function(self):
    self.expect_fql('SELECT strlen("asdf") FROM profile WHERE id = me()',
                    [{'length("asdf")': 4}])
    self.expect_fql('SELECT strlen(username) FROM profile WHERE id = me()',
                    [{'length(username)': 5}])

    self.expect_error('SELECT strlen() FROM profile WHERE id = me()',
                      fql.ParamMismatchError('strlen', 1, 0))
    self.expect_error('SELECT strlen("asdf", "qwert") FROM profile WHERE id = me()',
                      fql.ParamMismatchError('strlen', 1, 2))

  def test_substr_function(self):
    self.expect_fql('SELECT substr("asdf", 1, 2) FROM profile WHERE id = me()',
                    [{'substr("asdf", 2, 2)': 'sd'}])
    self.expect_fql('SELECT substr("asdf", 1, 6) FROM profile WHERE id = me()',
                    [{'substr("asdf", 2, 6)': 'sdf'}])

    self.expect_error('SELECT substr("asdf", 0) FROM profile WHERE id = me()',
                      fql.ParamMismatchError('substr', 3, 2))

  def test_strpos_function(self):
    self.expect_fql('SELECT strpos("asdf", "sd") FROM profile WHERE id = me()',
                    [{'1': 1}])
    self.expect_fql('SELECT strpos("asdf", "x") FROM profile WHERE id = me()',
                    [{'-1': -1}])

    self.expect_error('SELECT strpos("asdf") FROM profile WHERE id = me()',
                      fql.ParamMismatchError('strpos', 2, 1))

  def test_fql_types(self):
    # array
    self.expect_fql('SELECT categories FROM page WHERE name = "my_page"',
                    [{'categories': ['foo', 'bar']}])
    # bool
    self.expect_fql('SELECT can_post FROM profile WHERE id = me()',
                    [{'can_post': True}])
    # object
    self.expect_fql(
      'SELECT pic_crop FROM profile WHERE id = me()',
      [{'pic_crop': {"right": 1, "bottom": 2, "uri": "http://picture/url"}}])

  def test_non_indexable_column_error(self):
    self.expect_error('SELECT id FROM profile WHERE pic = "http://url.to/image"',
                      fql.NotIndexableError())

    # check that non-indexable columns inside strings are ignored
    self.expect_fql('SELECT id FROM profile WHERE username = "pic pic_big type"', [])

  def test_xml_format(self):
    self.expect_fql(
      'SELECT id, username FROM profile WHERE id = me()',
      """<?xml version="1.0" encoding="UTF-8"?>
<fql_query_response xmlns="http://api.facebook.com/1.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" list="true">
<profile>
<username>alice</username>
<id>%s</id>
</profile>
</fql_query_response>""" % self.ME,
      args={'format': 'xml'})

  def test_format_defaults_to_xml(self):
    for format in ('foo', ''):
      self.expect_fql(
        'SELECT username FROM profile WHERE id = me()',
        """<?xml version="1.0" encoding="UTF-8"?>
<fql_query_response xmlns="http://api.facebook.com/1.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" list="true">
<profile>
<username>alice</username>
</profile>
</fql_query_response>""",
        args={'format': format})

  def test_xml_format_error(self):
    self.expect_fql(
      'SELECT strlen() FROM profile WHERE id = me()',
      """<?xml version="1.0" encoding="UTF-8"?>
<error_response xmlns="http://api.facebook.com/1.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://api.facebook.com/1.0/ http://api.facebook.com/1.0/facebook.xsd">
<error_code>606</error_code>
<error_msg>strlen function expects 1 parameters; 0 given.</error_msg>
<request_args list="true">
<arg>
<value>SELECT strlen() FROM profile WHERE id = me()</value>
<key>query</key>
</arg>
<arg>
<value>xml</value>
<key>format</key>
</arg>
<arg>
<value>fql.query</value>
<key>method</key>
</arg>
</request_args>
</error_response>""",
      args={'format': 'xml'})

  def test_no_select_error(self):
    self.expect_error('INSERT id FROM profile WHERE id = me()',
                      fql.UnexpectedError('INSERT'))

  def test_no_table_error(self):
    self.expect_error('SELECT id', fql.UnexpectedEndError())

  def test_no_where_error(self):
    self.expect_error('SELECT id FROM profile', fql.UnexpectedEndError())

  def test_where_and_no_table_error(self):
    self.expect_error('SELECT name WHERE id = me()', fql.UnexpectedError('WHERE'))

  def test_invalid_function_error(self):
    self.expect_error('SELECT name FROM profile WHERE foo()',
                      fql.InvalidFunctionError('foo'))

  def test_wildcard_error(self):
    self.expect_error('SELECT * FROM profile WHERE id = me()',
                      fql.WildcardError())

  def test_sqlite_error(self):
    self.expect_error('SELECT bad syntax FROM profile WHERE id = me()',
                      fql.SqliteError('no such column: bad'))

  def test_no_query_error(self):
    self.expect_error('', fql.MissingParamError('query'))

  def test_access_token(self):
    self.conn.execute(
      'INSERT INTO oauth_access_tokens(code, token) VALUES("asdf", "qwert")')
    self.conn.commit()
    self.expect_fql('SELECT username FROM profile WHERE id = me()',
                    [{'username': 'alice'}],
                    args={'access_token': 'qwert'})

  def test_invalid_access_token(self):
    self.expect_error('SELECT username FROM profile WHERE id = me()',
                      fql.InvalidAccessTokenError(),
                      args={'access_token': 'bad'})


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = graph
"""Graph API request handler that uses the Graph API data in SQLite.

Based on http://developers.facebook.com/docs/reference/api/ .

Note that this code uses the term 'name' to mean something that's either an id
or an alias.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import json
import os
import sqlite3
import traceback
import types
import urllib
import re

import datetime
import random
import sys

import webapp2

import oauth
import schemautil

# the one connection that returns an HTTP 302 redirect instead of a normal
# 200 with response data.
# http://developers.facebook.com/docs/reference/api/#pictures
REDIRECT_CONNECTION = 'picture'

# this is here because GraphHandler handles the "/" front page request when it
# has query parameters, e.g. /?ids=..., and webapp2 can't route based on query
# parameters alone.
FRONT_PAGE = """
<html>
<body>
<h2>Welcome to <a href="https://github.com/rogerhu/mockfacebook">mockfacebook</a>!</h2>
<p>This server is currently serving these endpoints:</p>
<table style="border-spacing: .5em">
<tr><td><a href="http://developers.facebook.com/docs/reference/api/">Graph API</a></td>
 <td><code>/...[/...]</code></td></tr>
<tr><td><a href="http://developers.facebook.com/docs/reference/fql/">FQL</a></td>
 <td><code>/method/fql.query</code> and <code>/fql</code></td></tr>
<tr><td><a href="http://developers.facebook.com/docs/authentication/">OAuth</a></td>
 <td><code>/dialog/oauth</code> and <code>/oauth/access_token</code></td></tr>
</table>
<p>See <code>README.md</code> and the
<a href="https://github.com/rogerhu/mockfacebook#readme">online docs</a> for more
information.</p>
</body>
</html>
"""

class GraphError(Exception):
  """Base error class.

  Attributes:
    message: string
    status: integer
  """
  status = 400
  message = None

  def __init__(self, *args):
    self.message = self.message % args

class JsonError(GraphError):
  """JSON-formatted error class.

  Attributes:
    type: string
  """
  type = 'OAuthException'
    
  def __init__(self, *args):
    self.message = json.dumps(
      {'error': {'message': self.message % args, 'type': self.type}},
      indent=2)

class ObjectNotFoundError(GraphError):
  """Used for /<id> requests."""
  status = 200
  message = 'false'

class ObjectsNotFoundError(GraphError):
  """Used for /?ids=... requests."""
  status = 200
  message = '[\n\n]'

class AccessTokenError(JsonError):
  message = 'An access token is required to request this resource.'

class ValidationError(JsonError):
  message = 'Error validating application.'

class AliasNotFoundError(JsonError):
  status = 404
  message = '(#803) Some of the aliases you requested do not exist: %s'

class BadGetError(JsonError):
  message = 'Unsupported get request.'
  type = 'GraphMethodException'

class UnknownPathError(JsonError):
  message = 'Unknown path components: /%s'

class IdSpecifiedError(JsonError):
  message = 'Invalid token: \"%s\".  An ID has already been specified.'

class EmptyIdentifierError(JsonError):
  message = 'Cannot specify an empty identifier'

class NoNodeError(JsonError):
  message = 'No node specified'
  type = 'Exception'

class InternalError(JsonError):
  status = 500
  message = '%s'
  type = 'InternalError'


class NameDict(dict):
  """Maps ids map to the names (eiter id or alias) they were requested by.

  Attributes:
    single: True if this request was of the form /<id>, False if it was of the
      form /?ids=...
  """
  pass


def is_int(str):
  """Returns True if str is an integer, False otherwise."""
  try:
    int(str)
    return True
  except ValueError:
    return False

not_int = lambda str: not is_int(str)

class UTCTZ(datetime.tzinfo):
  def utcoffset(self, dt):
    return datetime.timedelta(0)
  def dst(self, dt):
    return datetime.timedelta(0)

utctz = UTCTZ()

class PostField(object):
  def __init__(self, name, required=False, is_argument=True, default="", arg_type=types.StringTypes, validator=None):
    """Represents a post field/argument

    Args:
      name: name of the argument
      required: set to True if the argument is required
      is_argument: if set to true, then field can be specified by the user (i.e. an argument)
      default: the default value to be used. This can be a string or a callback that returns a string
      arg_type: the Python type that this argument must be. The type must be JSON serializable
      validator: the callback to use to validate the argument.
    """
    self.name = name
    self.required = required
    self.is_argument = is_argument
    self.default = default
    self.arg_type = arg_type
    self.validator = validator

  def get_default(self, *args, **kwargs):
    if callable(self.default):
      return self.default(*args, **kwargs)
    return self.default

  def is_valid(self, arg):
    if not isinstance(arg, self.arg_type):
      return False
    if callable(self.validator):
      return self.validator(arg)
    return True

class MultiType(object):
  def __init__(self, *args):
    self.connections = args

DEFAULT_URL = "http://invalid/invalid"
YOUTUBE_LINK_RE = re.compile("http://[^/]*youtube")

def get_generic_id(*args, **kwargs):
  obj_id = kwargs.get("obj_id", "obj_id")
  return "%s_%s" % (obj_id, random.randint(0, sys.maxint))

def get_comment_id(*args, **kwargs):
  return get_generic_id(*args, **kwargs)

def get_note_id(*args, **kwargs):
  return get_generic_id(*args, **kwargs)

def get_photo_id(*args, **kwargs):
  return str(random.randint(0, sys.maxint))

def get_link_id(*args, **kwargs):
  return get_generic_id(*args, **kwargs)

def get_status_id(*args, **kwargs):
  return get_generic_id(*args, **kwargs)

def get_post_id(*args, **kwargs):
  return get_generic_id(*args, **kwargs)

def get_actions(*args, **kwargs):
  obj_id = kwargs.get("obj_id", "obj_id")
  obj_type = kwargs.get("type", "obj_type")
  gen_id = kwargs.get("id", "gen_id").split('_')[-1]
  return [{"name": "Comment", "link": "https://www.facebook.com/%s/%s/%s" % (obj_id, obj_type, gen_id)},
          {"name": "Like", "link": "https://www.facebook.com/%s/%s/%s" % (obj_id, obj_type, gen_id)}]

def get_comments(*args, **kwargs):
  return {"count": 0}

def get_name_from_link(*args, **kwargs):
  return kwargs.get("link", DEFAULT_URL)

def get_likes(*args, **kwargs):
  return {"data": []}

def get_from(*args, **kwargs):
  user_id = kwargs.get("user_id")
  return {"name": "Test", "category": "Test", "id": user_id}

def get_application(*args, **kwargs):
  return {"name": "TestApp", "canvas_name": "test", "namespace": "test", "id":"1234567890"}

def get_time(*args, **kwargs):
  return datetime.datetime.now(utctz).strftime("%Y-%m-%dT%H:%S:%M%z")

# TODO: support posting of events (attending, maybe, declined), albums (photos), and checkins
# Note: the order of the fields matter because the default values of some fields depend on the value of other fields.
#       "id" should always be first. and "type" should be before "action".
# Note: "posts" is not an actual type, and you can't publish to it. "posts" is just another way to get data from "feed"
CONNECTION_POST_ARGUMENTS = {"feed": MultiType("statuses", "links"),
                             "comments": [PostField("message", True),
                                          PostField("type", False, False, default="comment"),
                                          PostField("id", False, False, default=get_comment_id),
                                          PostField("from", False, False, arg_type=dict, default=get_from),
                                          PostField("created_time", False, False, default=get_time),
                                          PostField("likes", False, False, arg_type=int, default=0),
                                          # TODO: support user_likes
                                          ],
                             "notes": [PostField("subject", True),
                                       PostField("message", True),
                                       PostField("id", False, False, default=get_note_id),
                                       PostField("from", False, False, arg_type=dict, default=get_from),
                                       PostField("created_time", False, False, default=get_time),
                                       PostField("updated_time", False, False, default=get_time),
                                       # TODO: build out more stuff for notes
                                       ],
                             "photos":[PostField("message", True),
                                       PostField("source", True),
                                       PostField("id", False, False, default=get_photo_id),
                                       PostField("from", False, False, arg_type=dict, default=get_from),
                                       PostField("type", False, False, default="photo"),
                                       PostField("name", False, False, default=""),
                                       PostField("icon", False, False, default=DEFAULT_URL),
                                       PostField("picture", False, False, default=DEFAULT_URL),
                                       PostField("height", False, False, arg_type=int, default=100),  # TODO: detect the height and width from the image
                                       PostField("width", False, False, arg_type=int, default=100),
                                       PostField("link", False, False, default=DEFAULT_URL),
                                       PostField("created_time", False, False, default=get_time),
                                       PostField("updated_time", False, False, default=get_time)
                                       # TODO: support tags, images, and position
                                       ],
                             "links": [PostField("link", True, default=DEFAULT_URL),
                                       PostField("message", False),
                                       PostField("id", False, False, default=get_link_id),
                                       PostField("from", False, False, arg_type=dict, default=get_from),
                                       PostField("type", False, False, default="link"),
                                       PostField("name", False, False, default=get_name_from_link),
                                       PostField("caption", False, False),
                                       PostField("comments", False, False, arg_type=list, default=get_comments),
                                       PostField("description", False, False),
                                       PostField("icon", False, False, default=DEFAULT_URL),
                                       PostField("actions", False, False, arg_type=list, default=get_actions),
                                       PostField("application", False, False, arg_type=dict, default=get_application),
                                       PostField("picture", False, False, default=DEFAULT_URL),
                                       PostField("created_time", False, False, default=get_time),
                                       PostField("updated_time", False, False, default=get_time),
                                       ],
                             "statuses": [PostField("message", True, default=None),
                                          PostField("id", False, False, default=get_status_id),
                                          PostField("from", False, False, arg_type=dict, default=get_from),
                                          PostField("created_time", False, False, default=get_time),
                                          PostField("updated_time", False, False, default=get_time),
                                          PostField("type", False, False, default="status"),
                                          PostField("actions", False, False, arg_type=list, default=get_actions),
                                          PostField("comments", False, False, arg_type=dict, default=get_comments),
                                          PostField("icon", False, False, default=DEFAULT_URL),
                                          PostField("application", False, False, arg_type=dict, default=get_application),
                                          ]}


class GraphHandler(webapp2.RequestHandler):
  """Request handler class for Graph API handlers.

  This is a single class, instead of separate classes for objects and
  connections, because /xyz?... could be either an object or connection request
  depending on what xyz is.

  Class attributes:
    conn: sqlite3.Connection
    me: integer, the user id that /me should use
    schema: schemautil.GraphSchema
    all_connections: set of all string connection names
  """

  ROUTES = [webapp2.Route('<id:(/[^/]*)?><connection:(/[^/]*)?/?>', 'graph.GraphHandler')]

  @classmethod
  def init(cls, conn, me):
    """Args:
      conn: sqlite3.Connection
      me: integer, the user id that /me should use
    """
    cls.conn = conn
    cls.me = me
    cls.schema = schemautil.GraphSchema.read()
    cls.all_connections = reduce(set.union, cls.schema.connections.values(), set())
    cls.posted_graph_objects = {}
    cls.posted_connections = {}  # maps id -> connection -> list of elements

  def _get(self, id, connection):
    if id in self.all_connections and not connection:
      connection = id
      id = None

    try:
      token =  self.request.get('access_token')
      if token and not oauth.AccessTokenHandler.is_valid_token(self.conn, token):
        raise ValidationError()

      namedict = self.prepare_ids(id)

      if connection:
        resp = self.get_connections(namedict, connection)
      else:
        resp = self.get_objects(namedict)

      if namedict.single:
        if not resp:
          resp = []
        else:
          assert len(resp) == 1
          resp = resp.values()[0]
      return resp
    except GraphError as e:
      raise e


  def get(self, id, connection):
    """Handles GET requests.
    """
    if (id == '/' or not id) and not connection and not self.request.arguments():
      self.response.out.write(FRONT_PAGE)
      return

    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'

    # strip slashes
    if connection:
      connection = connection.strip("/")
    if id:
      id = id.strip("/")

    try:
      resp = self._get(id, connection)
      json.dump(resp, self.response.out, indent=2)
    except GraphError, e:
      # i don't use webapp2's handle_exception() because there's no way to get
      # the original exception's traceback, which makes testing difficult.
      self.response.write(e.message)
      self.response.set_status(e.status)


  def post(self, id, connection):
    id = id.strip("/")
    connection = connection.strip("/")

    # try to get the base object we're posting to
    try:
      graph_obj = self._get(id, None)
    except GraphError as e:
      self.response.write(e.message)
      self.response.set_status(e.status)
      return

    # validate the object type and connection
    try:
      obj_type = graph_obj.get("type")
      if obj_type is None:
        raise InternalError("object does not have a type")

      valid_connections =  self.schema.connections.get(obj_type)
      if valid_connections is None:
        raise InternalError("object type: %s is not supported" % obj_type)

      if connection not in valid_connections:
        raise InternalError("Connection: %s is not supported" % connection)
    except GraphError as e:
      self.response.write(e.message)
      self.response.set_status(e.status)
      return

    # TODO: validate that the mock is in sync with Facebook's metadata (except their metadata is really stale right now)
    #fields = self.schema.tables.get(obj_type)
    fields = []

    if self.update_graph_object(id, connection, graph_obj):
      resp = True
    else:
      # The connection determines what type of object to create
      try:
        graph_obj = self.create_graph_object(fields, self.request.POST, id, connection, graph_obj)
        obj_id = graph_obj["id"]
        GraphHandler.posted_graph_objects[obj_id] = graph_obj
        resp = {"id": obj_id}
      except GraphError as e:
        self.response.write(e.message)
        self.response.set_status(e.status)
        return

    # check the arguments

    # get the object w/ the given id and check it's type
    # lookup in the schema, the type and get the list of available options next.
    # Only some of those options are postable (does fb have a schema for this or do we just hardcode it?)
    # Then each option has a list of arguments it accepts (some require and some not) (does fb have a scheme for this or hardcode it?)
    # Note: hardcoding is possible b/c it's all documented (what's available and required) but it'd be better if they had a schema for this.

    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    json.dump(resp, self.response.out, indent=2)

  def delete(self, id, connection):
    if id == "/clear":
      GraphHandler.posted_graph_objects = {}
      GraphHandler.posted_connections = {}
      response_code = "ok"
    else:
      response_code = "fail"
    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    resp = {"response": response_code}
    json.dump(resp, self.response.out, indent=2)

  def get_objects(self, namedict):
    if not namedict:
      raise BadGetError()

    ids = namedict.keys()


    cursor = self.conn.execute(
      'SELECT id, data FROM graph_objects WHERE id IN (%s)' % self.qmarks(ids),
      ids)
    ret_dict = dict((namedict[obj_id], json.loads(data)) for obj_id, data in cursor.fetchall())

    # Anything in the published graph objects overwrite the normal results
    for obj_id in ids:
      if obj_id in GraphHandler.posted_graph_objects:
        ret_dict[obj_id] = GraphHandler.posted_graph_objects[obj_id]

    return ret_dict

  def get_connections(self, namedict, connection):
    if not namedict:
      raise NoNodeError()
    elif connection not in self.all_connections:
      raise UnknownPathError(connection)

    ids = namedict.keys()
    query = ('SELECT id, data FROM graph_connections '
               'WHERE id IN (%s) AND connection = ?' % self.qmarks(ids))
    cursor = self.conn.execute(query, ids + [connection])
    rows = cursor.fetchall()

    if connection == REDIRECT_CONNECTION and rows:
      self.redirect(json.loads(rows[0][1]), abort=True)  # this raises

    resp = {}
    # add posted data first b/c it must be newer
    for name in namedict.values():
      posted_data = GraphHandler.posted_connections.get(name, {}).get(connection, [])
      resp[name] = {"data": posted_data}

    for id, data in rows:
      resp[namedict[id]]['data'].extend(posted_data)
      resp[namedict[id]]['data'].append(json.loads(data))

    return resp

  def prepare_ids(self, path_id):
    """Returns the id(s) for this request.

    Looks at both path_id and the ids URL query parameter. Both can contain
    ids and/or aliases.

    Args:
      path_id: string

    Returns: NameDict

    Raises: GraphError if the query both path_id and ids are specified or an id is
      empty, 0, or not found
    """
    names = set()
    if 'ids' in self.request.arguments():
      names = set(self.request.get('ids').split(','))

    if path_id:
      if names:
        raise IdSpecifiedError(path_id)
      names = set([path_id])

    if not all(name and name != '0' for name in names):
      raise EmptyIdentifierError()

    me = 'me' in names
    if me:
      names.remove('me')
      names.add(self.me)

    qmarks = self.qmarks(names)
    cursor = self.conn.execute(
      'SELECT id, alias FROM graph_objects WHERE id IN (%s) OR alias IN (%s)' %
        (qmarks, qmarks),
      tuple(names) * 2)

    namedict = NameDict()
    namedict.single = bool(path_id)
    for id, alias in cursor.fetchall():
      assert id in names or alias in names
      namedict[id] = 'me' if me else alias if alias in names else id
    for name in names:
      if name in GraphHandler.posted_graph_objects:
        namedict[name] = name

    not_found = names - set(namedict.values() + namedict.keys())
    if not_found:
      # the error message depends on whether any of the not found names are
      # aliases and whether this was ?ids= or /id.
      aliases = filter(not_int, not_found)
      if aliases:
        raise AliasNotFoundError(','.join(aliases))
      elif path_id:
        raise ObjectNotFoundError()
      else:
        raise ObjectsNotFoundError()

    return namedict

  def qmarks(self, values):
    """Returns a '?, ?, ...' string with a question mark per value.
    """
    return ','.join('?' * len(values))

  def update_graph_object(self, id, connection, graph_object):
    if connection == "likes":
      liker = id  # TODO: get the the user performing the like
      like_data = graph_object.setdefault("likes", {"data": []})["data"]
      for data in like_data:
        if data["id"] == liker:
          return True  # probably should be False, but Facebook returns True
      like_data.append({"id": liker, "name":"Test", "category": "Test"})
      GraphHandler.posted_graph_objects[id] = graph_object  # keep a copy the graph object to modify it
      return True
    return False

  def create_blob_from_args(self, obj_id, fields, spec, args):
    """
    Args:
      fields: The known fields given by Facebook's metadata
      spec: The argument specification
      args: The arguments to use to create the blob

    Returns:
    Raises: GraphError
    """
    # TODO: validate that the mock is in sync with Facebook's metadata (except their metadata is really stale right now)
    # field_names = set([f.name for f in fields])
    # spec_names = set([a.name for a in spec])
    # removed_arguments = spec_names - field_names
    # if len(removed_arguments) > 0:
    #   raise InternalError("Update the mock. The following arguments are no longer supported by Facebook: %s" % ",".join(removed_arguments))

    default_args = {"obj_id": obj_id,
                    "user_id": self.me,   # TODO: get the user_id from the access_token
                    }

    blob = {}
    for field in spec:
      arg_value = args.get(field.name)
      # Facebook currently doesn't return errors if required arguments are not specified, they just have default values
      if arg_value is None:
        arg_value = field.get_default(**default_args)
      else:
        if not field.is_valid(arg_value):
          arg_value = field.get_default(**default_args)
        else:
          if field.name == "picture":  # Facebook automatically proxies pictures
            # TODO: figure out how facebook generates the checksum (looks like MD5), v, and size attributes
            arg_value = "https://www.facebook.com/app_full_proxy.php?app=1234567890&v=1&size=z&cksum=0&src=%s" % urllib.quote_plus(arg_value)
      if arg_value is not None:
        blob[field.name] = arg_value

      # populate the default_args
      default_args[field.name] = arg_value

    return blob


  def create_graph_object(self, fields, arguments, id, connection, parent_obj):
    argument_spec = CONNECTION_POST_ARGUMENTS.get(connection)
    if argument_spec is None:
      raise InternalError("Connection: %s is not supported. You can add it yourself. :)")

    if isinstance(argument_spec, MultiType):
      last_exception = InternalError("Could not parse POST arguments")
      if "link" in arguments and "links" in argument_spec.connections:
        blob = self.create_blob_from_args(id, fields, CONNECTION_POST_ARGUMENTS.get("links"), arguments)

        # Facebook detects YouTube links and changes the type to swf
        if YOUTUBE_LINK_RE.search(blob.get("link", "")):
          blob["type"] = "swf"

        connections = GraphHandler.posted_connections.setdefault(id, {})
        connections.setdefault(connection, []).insert(0,blob)
        if connection == "feed":
          connections.setdefault("posts", []).insert(0,blob)  # posts mirror feed
        return blob
      for c in argument_spec.connections:
        try:
          blob = self.create_blob_from_args(id, fields, CONNECTION_POST_ARGUMENTS.get(c), arguments)
          connections = GraphHandler.posted_connections.setdefault(id, {})
          connections.setdefault(connection, []).insert(0,blob)
          if connection == "feed":
            connections.setdefault("posts", []).insert(0,blob)  # posts mirror feed
          return blob
        except GraphError as e:
          last_exception = e
      raise last_exception
    else:
      blob = self.create_blob_from_args(id, fields, argument_spec, arguments)
      if parent_obj is not None:
        connection_obj = parent_obj.get(connection)
        if connection_obj is not None:
          # update the parent object if there is a list of this connection stored there
          connection_obj["count"] += 1
          data = connection_obj.setdefault("data", [])
          data.append(blob)

      return blob

########NEW FILE########
__FILENAME__ = graph_on_fql
"""Graph API request handler that uses the FQL data in SQLite.

This is currently on hold. It requires a schema mapping between FQL and the
Graph API, which is labor intensive. This is a good start, but there's a fair
amount of work left to do.

TODO:
- finish schema mapping (all the TODOs inside OBJECT_QUERIES)
- errors
- field selection with ?fields=...
- multiple object selection with ?ids=...
- /picture suffix
- paging
- ?date_format=...
- ?metadata=1 introspection

- handle special cases for which values are omitted when, e.g. null, 0, ''. 0
  is omitted for some things, like page.likes, but not others, like
  group.version. same with '', e.g. group.venue.street. may need another
  override dict in download.py. :/
- time zones in timestamps. (it 's currently hard coded to PST.)
- id aliases, e.g. comment ids can have the user id as a prefix, or not:
  https://graph.facebook.com/212038_227980440569633_3361295
  https://graph.facebook.com/227980440569633_3361295
- connections
- unusual objects: messages, reviews, insights
- comments via .../comments
- likes via .../likes
- batch requests: http://developers.facebook.com/docs/reference/api/batch/
- real time updates: http://developers.facebook.com/docs/reference/api/realtime/
- insights: http://developers.facebook.com/docs/reference/api/insights/
- search via /search?q=...&type=...
- publishing via POST
- deleting via DELETE
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import logging
import json
import sqlite3

import webapp2

import schemautil


# Columns that should always be included, even if they have null/empty/0 value.
OVERRIDE_PINNED_COLUMNS = frozenset(
  ('Group', 'version'),
)

# SQLite queries to fetch and generate Graph API objects. Maps FQL table name
# to SQLite query. (The FQL table name is used when converting values from
# SQLite to JSON.)

# TODO: names with double quotes inside them will break this. ideally i'd use
# quote(u.name) and quote(owner), but that uses single quotes, which JSON
# doesn't support for string literals. :/
USER_TEMPLATE = """ '{"name": "' || %s.name || '", "id": "' || %s.uid || '"}' """
USER_OBJECT = USER_TEMPLATE % ('user', 'user')
APP_OBJECT = """ '{"name": "' || application.display_name || '", "id": "' || application.app_id || '"}' """

OBJECT_QUERIES = {
  'Album': """
SELECT
 CAST(object_id AS TEXT) AS id,
 """ +  USER_OBJECT + """ AS `from`,
 album.name as name,
 description,
 location,
 link,
 CAST(cover_object_id AS TEXT) AS cover_photo,
 visible AS privacy,
 photo_count AS count,
 strftime("%Y-%m-%dT%H:%M:%S+0000", created, "unixepoch") AS created_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", modified, "unixepoch") AS updated_time,
 type
FROM album
  LEFT JOIN user ON (owner = uid)
WHERE object_id = ?;
""",

  'Application': """
SELECT
 CAST(app_id AS TEXT) as id,
 display_name as name,
 description,
 category,
 subcategory,
 "http://www.facebook.com/apps/application.php?id=" || app_id as link,
 icon_url,
 logo_url
FROM application
WHERE app_id = ?;
""",

  'Checkin': """
SELECT
 CAST(checkin_id AS TEXT) as id,
 """ +  USER_OBJECT + """ AS `from`,
 tagged_uids as tags,
 coords as place,
 """ + APP_OBJECT + """ as application,
 strftime("%Y-%m-%dT%H:%M:%S+0000", timestamp, "unixepoch") AS created_time,
-- stream.likes.count, TODO
 checkin.message,
 stream.comments
FROM checkin
  LEFT JOIN application USING (app_id)
  LEFT JOIN stream USING(post_id)
  LEFT JOIN user ON (checkin.author_uid = uid)
WHERE checkin_id = ?;
""",

  'Comment': """
SELECT
 id,
 """ +  USER_OBJECT + """ AS `from`,
 text as message,
 1 as can_remove,
 strftime("%Y-%m-%dT%H:%M:%S+0000", time, "unixepoch") AS created_time,
 likes,
 nullif(user_likes, 0) as user_likes
FROM comment
  LEFT JOIN user ON (fromid = uid)
WHERE id = ?;
""",

  'Domain': """
SELECT
 CAST(domain_id AS TEXT) as id,
 domain_name as name
FROM domain
WHERE domain_id = ?;
""",

  'Event': """
SELECT
 CAST(eid AS TEXT) as id,
 -- TODO test data event is owned by FB Eng page, add that or get new event
 """ +  USER_OBJECT + """ AS owner,
 event.name,
 description,
 -- TODO these should be PST (7h behind) but they're UTC
 strftime("%Y-%m-%dT%H:%M:%S+0000", start_time, "unixepoch") AS start_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", end_time, "unixepoch") AS end_time,
 location,
 venue,  -- TODO id is int but should be string 
 privacy,
 strftime("%Y-%m-%dT%H:%M:%S+0000", update_time, "unixepoch") AS updated_time
FROM event
  LEFT JOIN user ON (creator = uid)
WHERE eid = ?;
""",

  'FriendList': """
SELECT
 CAST(flid AS TEXT) as id,
 name
FROM friendlist
WHERE flid = ?;
""",

  'Group': """
SELECT
 CAST(gid AS TEXT) as id,
 CAST(version AS INTEGER) as version,
 "http://static.ak.fbcdn.net/rsrc.php/v1/y_/r/CbwcMZjMUbR.png" as icon,
 """ +  USER_OBJECT + """ AS owner,
 g.name,
 description,
 g.website as link,
 venue,
 privacy,
 strftime("%Y-%m-%dT%H:%M:%S+0000", update_time, "unixepoch") AS updated_time
FROM `group` g
  LEFT JOIN user ON (creator = uid)
WHERE gid = ?;
""",

  'Link': """
SELECT
 CAST(link_id AS TEXT) as id,
 """ +  USER_OBJECT + """ AS `from`,
 url as link,
 title as name,
 null as comments, -- TODO
 summary as description,
 "http://static.ak.fbcdn.net/rsrc.php/v1/yD/r/aS8ecmYRys0.gif" as icon,
 picture,
 owner_comment as message,
 strftime("%Y-%m-%dT%H:%M:%S+0000", created_time, "unixepoch") AS created_time
FROM link
  LEFT JOIN user ON (owner = uid)
WHERE link_id = ?;
""",

  'Note': """
SELECT
 note_id as id,
 """ +  USER_OBJECT + """ AS `from`,
 title as subject,
 content_html as message,
 null as comments, -- TODO
 strftime("%Y-%m-%dT%H:%M:%S+0000", created_time, "unixepoch") AS created_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", updated_time, "unixepoch") AS updated_time,
 "http://static.ak.fbcdn.net/rsrc.php/v1/yY/r/1gBp2bDGEuh.gif" as icon
FROM note
  LEFT JOIN user USING (uid)
WHERE note_id = ?;
""",

  'Page': """
SELECT
 CAST(page_id AS TEXT) as id,
 name,
 pic as picture,
 page_url as link,
 -- capitalize
 upper(substr(type, 1, 1)) || lower(substr(type, 2)) as category,
 -- if page_url is of the form http://www.facebook.com/[USERNAME], parse
 -- username out of that. otherwise give up and return null.
 nullif(replace(page_url, "http://www.facebook.com/", ""), page_url) as username,
 founded,
 company_overview,
 fan_count as likes,
 parking,
 hours,
 null as payment_options, -- TODO
 null as restaurant_services, -- TODO
 null as restaurant_specialties, -- TODO
 null as general_info, -- TODO
 '{"amex": 0, "cash_only": 0, "visa": 0, "mastercard": 0, "discover": 0}'
   as payment_options, -- TODO
 location,
 null as phone, -- TODO
 null as checkins, -- TODO: use place.checkin_count? but this isn't a place :/
 null as access_token, -- TODO
 1 as can_post -- TODO
FROM page
WHERE page_id = ?;
""",

  'Photo': """
SELECT
 CAST(object_id AS TEXT) as id,
 """ +  USER_OBJECT + """ AS `from`,
 null as tags, -- TODO
 caption as name,
 "http://static.ak.fbcdn.net/rsrc.php/v1/yz/r/StEh3RhPvjk.gif" as icon,
 src as picture,
 src_big as source,
 CAST(src_big_height AS INTEGER) as height,
 CAST(src_big_width AS INTEGER) as width,
 null as images, -- TODO
 link,
 null as comments, -- TODO
 strftime("%Y-%m-%dT%H:%M:%S+0000", created, "unixepoch") AS created_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", modified, "unixepoch") AS updated_time,
 1 as position -- TODO: this isn't in FQL?
FROM photo
  LEFT JOIN user ON (owner = uid)
WHERE object_id = ?;
""",

 'Post': """
SELECT
 post_id AS id,
 """ +  (USER_TEMPLATE % ('from_user', 'from_user')) + """ AS `from`,
 '{"data": [' || """ +  (USER_TEMPLATE % ('to_user', 'to_user')) + """ || ']}' AS `to`,
 message,
 null AS picture, -- TODO parse all of these out of attachment
 null AS link,
 null AS name,
 null AS caption,
 null AS description,
 null AS source,
 null AS properties,
 null AS icon,
 action_links AS actions,
 privacy,
 null AS type, -- TODO parse out of attachment
 likes, -- TODO parse out of attachment and restructure
 null as comments, -- TODO parse comments and restructure (remove can_remove, can_post)
 null AS object_id, -- TODO
 """ + APP_OBJECT + """ AS application,
 strftime("%Y-%m-%dT%H:%M:%S+0000", created_time, "unixepoch") AS created_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", updated_time, "unixepoch") AS updated_time,
 null as targeting
FROM stream
  LEFT JOIN application USING (app_id)
  LEFT JOIN user AS from_user ON (actor_id = from_user.uid)
  LEFT JOIN user AS to_user ON (target_id = to_user.uid)
WHERE post_id = ?;
""",

  'Status': """
SELECT
 CAST(status_id AS TEXT) as id,
 """ +  USER_OBJECT + """ AS `from`,
 message,
 strftime("%Y-%m-%dT%H:%M:%S+0000", time, "unixepoch") AS updated_time
FROM status
  LEFT JOIN user USING (uid)
WHERE status_id = ?;
""",

  'User': """
SELECT
 CAST(uid AS TEXT) AS id,
 name,
 first_name,
 middle_name,
 last_name,
 sex AS gender,
 locale,
 null AS languages,
 profile_url AS link,
 username,
 third_party_id, -- TODO ok as is
   -- should just append ?fields=third_party_id to the User ID in the
   -- download.py publishable graph api ID URLs, but then it doesn't return the
   -- rest of the fields. :/
 CAST(timezone AS INTEGER) AS timezone,
 strftime("%Y-%m-%dT%H:%M:%S+0000", profile_update_time, "unixepoch") AS updated_time,
 verified,
 about_me AS bio,
 birthday_date AS birthday,
 education,
 contact_email AS email,
 hometown_location AS hometown,
 meeting_sex AS interested_in,
 current_location AS location,  -- TODO ok as is
 political,
 null AS favorite_athletes,  -- TODO
 null AS favorite_teams,  -- TODO
 quotes,
 relationship_status,
 null AS religion,  -- TODO
 null AS significant_other, -- significant_other_id
 null AS video_upload_limits,
 website,
 work -- TODO close enough
FROM user
WHERE uid = ?;
""",

  'Video': """
SELECT
 CAST(vid AS TEXT) as id,
 """ +  USER_OBJECT + """ AS `from`,
 null as tags, -- TODO
 title as name,
 description,
 thumbnail_link as picture,
 embed_html,
 "http://static.ak.fbcdn.net/rsrc.php/v1/yD/r/DggDhA4z4tO.gif" as icon,
 src as source,
 strftime("%Y-%m-%dT%H:%M:%S+0000", created_time, "unixepoch") AS created_time,
 strftime("%Y-%m-%dT%H:%M:%S+0000", updated_time, "unixepoch") AS updated_time,
 null as comments -- TODO
FROM video
  LEFT JOIN user ON (owner = uid)
WHERE vid = ?;
""",
}


class OverrideValueFunctions(object):
  """Holds custom processing functions for some field values. Each function
  takes a single parameter, the object id.
  """

  @classmethod
  def get(cls, table, field):
    """Returns the function for the given table and field, or None.
    """
    name = '%s_%s' % (table.lower(), field.lower())
    try:
      return getattr(cls, name)
    except AttributeError:
      return None

  @staticmethod
  def photo_images(id):
    return 'foobax'


class GraphOnFqlHandler(webapp2.RequestHandler):
  """The Graph API request handler.

  Not thread safe!

  Class attributes:
    conn: sqlite3.Connection
    me: integer, the user id that /me should use
    schema: schemautil.GraphSchema
  """

  @classmethod
  def init(cls, conn, me):
    """Args:
      conn: sqlite3.Connection
      me: integer, the user id that /me should use
    """
    cls.conn = conn
    cls.me = me
    cls.schema = schemautil.GraphSchema.read()

  def get(self, id):
    if id == 'me':
      id = self.me

    result = None
    # TODO: parallelize these queries
    for table, query in OBJECT_QUERIES.items():
      cursor = self.conn.execute(query, [id])
      result = self.schema.values_from_sqlite(cursor, table)
      if result:
        break

    if result:
      assert len(result) == 1
      result = result[0]
      for field, val in result.items():
        fn = OverrideValueFunctions.get(table, field)
        if fn:
          result[field] = fn(val)
        # Facebook omits null/empty values entirely in the Graph API
        # TODO: there are some exceptions, e.g. Group.version = 0
        if val in (None, [], 0):
          del result[field]
    else:
      # Facebook reports no results with 'false'.
      # TODO: if the id has non-digits, then it's an "alias," and Facebook says:
      # {"error":
      #   {"message": "(#803) Some of the aliases you requested do not exist: abc",
      #    "type": "OAuthException"}
      # }
      resp = 'false'

    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    self.response.out.write(json.dumps(result))

########NEW FILE########
__FILENAME__ = graph_on_fql_test
#!/usr/bin/python
"""Unit tests for graph_on_fql.py.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import re
import sys
import traceback
import unittest

import webapp2

import graph_on_fql
import schemautil
import testutil


class GraphOnFqlTest(testutil.HandlerTest):
  """Tests GraphApplication with the data in fql_data.sql and graph_data.py.
  """

  def setUp(self):
    super(GraphOnFqlTest, self).setUp(graph_on_fql.GraphOnFqlHandler, '/(.*)')

  def test_every_object_type(self):
    dataset = schemautil.GraphDataset.read()
    passed = True

    for table, data in dataset.data.items():
      try:
        self.expect('/%s' % data.query, data.data)
      except Exception:
        passed = False
        print 'Table: %s' % table
        traceback.print_exc()

    self.assertTrue(passed)

  def test_not_found(self):
    self.expect('/doesnt_exist', 'false')



if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = graph_schema
# Do not edit! Generated automatically by mockfacebook.
# https://github.com/rogerhu/mockfacebook
# 2012-10-23 22:47:33.406235

{'connections': {u'application': [u'feed',
                                  u'picture',
                                  u'tagged',
                                  u'videos',
                                  u'links',
                                  u'subscriptions',
                                  u'notes',
                                  u'posts',
                                  u'photos',
                                  u'albums',
                                  u'events',
                                  u'statuses',
                                  u'insights'],
                 u'checkin': [u'likes', u'comments', u'tags'],
                 u'comment': [u'likes', u'comments'],
                 u'event': [u'feed',
                            u'picture',
                            u'noreply',
                            u'maybe',
                            u'invited',
                            u'attending',
                            u'admins',
                            u'declined'],
                 u'friendlist': [u'members'],
                 u'group': [u'feed',
                            u'picture',
                            u'files',
                            u'members',
                            u'docs'],
                 u'link': [u'likes', u'comments'],
                 u'normal': [u'photos',
                             u'likes',
                             u'comments',
                             u'sharedposts'],
                 u'note': [u'comments', u'sharedposts'],
                 u'page': [u'feed',
                           u'picture',
                           u'tagged',
                           u'milestones',
                           u'videos',
                           u'links',
                           u'notes',
                           u'posts',
                           u'global_brand_children',
                           u'photos',
                           u'offers',
                           u'questions',
                           u'albums',
                           u'events',
                           u'statuses'],
                 u'photo': [u'sharedposts', u'likes', u'comments', u'tags'],
                 u'status': [u'sharedposts', u'likes', u'comments', u'tags'],
                 u'user': [u'feed',
                           u'tagged',
                           u'subscribers',
                           u'family',
                           u'picture',
                           u'mutualfriends',
                           u'locations',
                           u'books',
                           u'accounts',
                           u'likes',
                           u'questions',
                           u'home',
                           u'statuses',
                           u'friendrequests',
                           u'links',
                           u'checkins',
                           u'subscribedto',
                           u'music',
                           u'videos',
                           u'events',
                           u'adaccounts',
                           u'interests',
                           u'activities',
                           u'apprequests',
                           u'photos',
                           u'updates',
                           u'groups',
                           u'scores',
                           u'friendlists',
                           u'outbox',
                           u'albums',
                           u'friends',
                           u'permissions',
                           u'television',
                           u'notifications',
                           u'notes',
                           u'posts',
                           u'movies',
                           u'games',
                           u'payments',
                           u'inbox'],
                 u'video': [u'likes', u'comments']},
 'tables': {u'application': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'description', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'category', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'company', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'icon_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'subcategory', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'logo_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'daily_active_users', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'weekly_active_users', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'monthly_active_users', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'migrations', fb_type='array', sqlite_type='', indexable=None),
                             Column(name=u'namespace', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'restrictions', fb_type='object', sqlite_type='', indexable=None),
                             Column(name=u'app_domains', fb_type='array', sqlite_type='', indexable=None),
                             Column(name=u'auth_dialog_data_help_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'auth_dialog_description', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'auth_dialog_headline', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'auth_dialog_perms_explanation', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'auth_referral_user_perms', fb_type='array', sqlite_type='', indexable=None),
                             Column(name=u'auth_referral_friend_perms', fb_type='array', sqlite_type='', indexable=None),
                             Column(name=u'auth_referral_default_activity_privacy', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'auth_referral_enabled', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'auth_referral_extended_perms', fb_type='array', sqlite_type='', indexable=None),
                             Column(name=u'auth_referral_response_type', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'canvas_fluid_height', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'canvas_fluid_width', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'canvas_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'contact_email', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'created_time', fb_type='int', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'creator_uid', fb_type='int', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'deauth_callback_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'iphone_app_store_id', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'hosting_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'mobile_web_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'page_tab_default_name', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'page_tab_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'privacy_policy_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'secure_canvas_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'secure_page_tab_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'server_ip_whitelist', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'social_discovery', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                             Column(name=u'terms_of_service_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'user_support_email', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'user_support_url', fb_type='string', sqlite_type='TEXT', indexable=None),
                             Column(name=u'website_url', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'checkin': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                         Column(name=u'tags', fb_type='array', sqlite_type='', indexable=None),
                         Column(name=u'place', fb_type='object', sqlite_type='', indexable=None),
                         Column(name=u'application', fb_type='object', sqlite_type='', indexable=None),
                         Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'likes', fb_type='array', sqlite_type='', indexable=None),
                         Column(name=u'message', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'comments', fb_type='array', sqlite_type='', indexable=None),
                         Column(name=u'type', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'comment': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                         Column(name=u'message', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'likes', fb_type='int', sqlite_type='INTEGER', indexable=None),
                         Column(name=u'user_likes', fb_type='string', sqlite_type='TEXT', indexable=None),
                         Column(name=u'type', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'domain': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'event': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'owner', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'description', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'start_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'end_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'location', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'venue', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'privacy', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'picture', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'friendlist': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                            Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                            Column(name=u'list_type', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'group': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'version', fb_type='int', sqlite_type='INTEGER', indexable=None),
                       Column(name=u'icon', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'owner', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'description', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'privacy', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'normal': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                        Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'description', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'location', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'cover_photo', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'privacy', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'count', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'type', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'can_upload', fb_type='bool', sqlite_type='INTEGER', indexable=None)],
            u'note': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'subject', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'message', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'comments', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'icon', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'page': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'category', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'is_published', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'can_post', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'likes', fb_type='int', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'location', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'phone', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'checkins', fb_type='int', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'picture', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'cover', fb_type=None, sqlite_type=None, indexable=None),
                      Column(name=u'website', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'talking_about_count', fb_type='int', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'global_brand_like_count', fb_type=None, sqlite_type=None, indexable=None),
                      Column(name=u'global_brand_talking_about_count', fb_type=None, sqlite_type=None, indexable=None),
                      Column(name=u'global_brand_parent_page', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'access_token', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'photo': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'tags', fb_type='array', sqlite_type='', indexable=None),
                       Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'name_tags', fb_type='array', sqlite_type='', indexable=None),
                       Column(name=u'icon', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'picture', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'source', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'height', fb_type='int', sqlite_type='INTEGER', indexable=None),
                       Column(name=u'width', fb_type='int', sqlite_type='INTEGER', indexable=None),
                       Column(name=u'images', fb_type='array', sqlite_type='', indexable=None),
                       Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'place', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'position', fb_type='int', sqlite_type='INTEGER', indexable=None)],
            u'status': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                        Column(name=u'message', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'place', fb_type='object', sqlite_type='', indexable=None),
                        Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                        Column(name=u'type', fb_type='string', sqlite_type='TEXT', indexable=None)],
            u'user': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'first_name', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'middle_name', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'last_name', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'gender', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'locale', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'languages', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'link', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'username', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'third_party_id', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'installed', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'timezone', fb_type='int', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'verified', fb_type='bool', sqlite_type='INTEGER', indexable=None),
                      Column(name=u'bio', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'birthday', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'cover', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'currency', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'devices', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'education', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'email', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'hometown', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'interested_in', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'location', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'political', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'payment_pricepoints', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'favorite_athletes', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'favorite_teams', fb_type='array', sqlite_type='', indexable=None),
                      Column(name=u'picture', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'quotes', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'relationship_status', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'religion', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'security_settings', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'significant_other', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'video_upload_limits', fb_type='object', sqlite_type='', indexable=None),
                      Column(name=u'website', fb_type='string', sqlite_type='TEXT', indexable=None),
                      Column(name=u'work', fb_type='array', sqlite_type='', indexable=None)],
            u'video': [Column(name=u'id', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'from', fb_type='object', sqlite_type='', indexable=None),
                       Column(name=u'tags', fb_type='array', sqlite_type='', indexable=None),
                       Column(name=u'name', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'description', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'picture', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'embed_html', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'icon', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'source', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'created_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'updated_time', fb_type='string', sqlite_type='TEXT', indexable=None),
                       Column(name=u'comments', fb_type='array', sqlite_type='', indexable=None)]}}

########NEW FILE########
__FILENAME__ = graph_test
#!/usr/bin/python
"""Unit tests for graph.py.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import re
import traceback
import unittest

import graph
import schemautil
import testutil


def insert_test_data(conn):
  """Args:
    conn: SQLite connection
  """
  conn.executescript("""
INSERT INTO graph_objects VALUES('1', 'alice', '{"id": "1", "foo": "bar"}');
INSERT INTO graph_objects VALUES('2', 'bob', '{"id": "2", "inner": {"foo": "baz"}}');
INSERT INTO graph_objects VALUES('3', null, '{"id": "3", "type": "page", "inner": {"foo": "baz"}}');
INSERT INTO graph_connections VALUES('1', 'albums', '{"id": "3"}');
INSERT INTO graph_connections VALUES('1', 'albums', '{"id": "4"}');
INSERT INTO graph_connections VALUES('2', 'albums', '{"id": "5"}');
INSERT INTO graph_connections VALUES('1', 'picture', '"http://alice/picture"');
INSERT INTO graph_connections VALUES('2', 'picture', '"http://bob/picture"');
""")
  conn.commit()


class TestBase(testutil.HandlerTest):

  dataset = testutil.maybe_read(schemautil.GraphDataset)

  def setUp(self, *args):
    super(TestBase, self).setUp(*args)
    self.alice = {'id': '1', 'foo': 'bar'}
    self.bob = {'id': '2', 'inner': {'foo': 'baz'}}
    self.alice_albums = {'data': [{'id': '3'}, {'id': '4'}]}
    self.bob_albums = {'data': [{'id': '5'}]}
    insert_test_data(self.conn)

  def _test_example_data(self, data):
    """Args:
      data: list of Data or Connection with url paths and expected results
    """
    self.conn.executescript(self.dataset.to_sql())
    self.conn.commit()
    graph.GraphHandler.me = self.dataset.data['me'].data['id']
    for datum in data:
      self.expect('/%s' % datum.query, datum.data)

  def expect_redirect(self, path, redirect_to):
    resp = self.get_response(path)
    self.assertEquals(302, resp.status_int)
    self.assertEquals(redirect_to, resp.headers['Location'])

  def expect_error(self, path, exception, args=None):
    """Args:
      path: string
      exception: expected instance of a GraphError subclass
    """
    self.expect(path, exception.message, expected_status=exception.status, args=args)


class ObjectTest(TestBase):

  def setUp(self):
    super(ObjectTest, self).setUp(graph.GraphHandler)

  def test_example_data(self):
    if self.dataset:
      self._test_example_data(self.dataset.data.values())

  def test_id(self):
    self.expect('/1', self.alice)

  def test_alias(self):
    self.expect('/alice', self.alice)

  def test_me(self):
    self.expect('/me', self.alice)

  def test_no_id(self):
    self.expect_error('/?foo', graph.BadGetError())

  def test_not_found(self):
    self.expect_error('/9', graph.ObjectNotFoundError())

  def test_single_ids_not_found(self):
    self.expect_error('/?ids=9', graph.ObjectsNotFoundError())

  def test_multiple_ids_not_found(self):
    self.expect_error('/?ids=9,8', graph.ObjectsNotFoundError())

  def test_alias_not_found(self):
    for bad_query in '/foo', '/?ids=foo', '/?ids=alice,foo':
      self.expect_error(bad_query, graph.AliasNotFoundError('foo'))

    self.expect_error('/?ids=foo,bar', graph.AliasNotFoundError('foo,bar'))

  def test_id_already_specified(self):
    self.expect_error('/foo?ids=bar', graph.IdSpecifiedError('foo'))

  def test_empty_identifier(self):
    for bad_query in '/?ids=', '/?ids=alice,', '/?ids=alice,,2':
      self.expect_error(bad_query, graph.EmptyIdentifierError())

  def test_ids_query_param(self):
    self.expect('/?ids=alice,bob',
                {'alice': self.alice, 'bob': self.bob})
    self.expect('/?ids=bob,1',
                {'1': self.alice, 'bob': self.bob})

  def test_ids_query_param_no_trailing_slash(self):
    self.expect('?ids=alice', {'alice': self.alice})

  def test_ids_always_prefers_alias(self):
    self.expect('/?ids=alice,1', {'alice': self.alice})
    self.expect('/?ids=1,alice', {'alice': self.alice})

  def test_access_token(self):
    self.conn.execute(
      'INSERT INTO oauth_access_tokens(code, token) VALUES("asdf", "qwert")')
    self.conn.commit()

    token = {'access_token': 'qwert'}
    self.expect('/alice', self.alice, args=token)
    self.expect('/alice/albums', self.alice_albums, args=token)

  def test_invalid_access_token(self):
    for path in '/alice', '/alice/albums':
      self.expect_error(path, graph.ValidationError(),
                        args={'access_token': 'bad'})


class ConnectionTest(TestBase):

  def setUp(self):
    super(ConnectionTest, self).setUp(graph.GraphHandler)

  def test_example_data(self):
    if self.dataset:
      self._test_example_data(conn for conn in self.dataset.connections.values()
                              if conn.name != graph.REDIRECT_CONNECTION)

  def test_id(self):
    self.expect('/1/albums', self.alice_albums)

  def test_alias(self):
    self.expect('/alice/albums', self.alice_albums)

  def test_me(self):
    self.expect('/me/albums', self.alice_albums)

  def test_no_id(self):
    self.expect_error('/albums?foo', graph.NoNodeError())

  def test_id_not_found(self):
    self.expect('/9/albums', 'false')

  def test_alias_not_found(self):
    self.expect_error('/foo/albums', graph.AliasNotFoundError('foo'))

  def test_connection_not_found(self):
    self.expect_error('/alice/foo', graph.UnknownPathError('foo'))

  def test_no_connection_data(self):
    self.expect('/alice/family', {'data': []})
    self.expect('//family?ids=alice', {'alice': {'data': []}})

  def test_ids_query_param(self):
    self.expect('/albums?ids=alice,bob',
                {'alice': self.alice_albums, 'bob': self.bob_albums})

  def test_picture_redirect(self):
    for path in ('/alice/picture',
                 '/picture?ids=alice',
                 '//picture?ids=alice,bob'):
      self.expect_redirect(path, 'http://alice/picture')


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = oauth
"""The OAuth request handler.

Based on http://developers.facebook.com/docs/authentication/ .
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import base64
import logging
import os
import urllib
import urlparse

from webob import exc
import webapp2


AUTH_CODE_PATH = '/dialog/oauth'
ACCESS_TOKEN_PATH = '/oauth/access_token'
EXPIRES = '999999'
RANDOM_BYTES = 16

ERROR_TEXT = """
mockfacebook

Error

An error occurred: %s. Please try again later. (In the real Facebook, this is
nicely formatted HTML.)
"""

ERROR_JSON = '{"error":{"type":"OAuthException","message":"%s."}}'


class BaseHandler(webapp2.RequestHandler):
  """Base handler class for OAuth handlers.

  Attributes:
    conn: sqlite3.Connection
  """

  @classmethod
  def init(cls, conn, me=None):
    # me is unused
    cls.conn = conn

  def get_required_args(self, *args):
    """Checks that one or more args are in the query args.

    If any are not in args or are empty, raises an AssertionError with the
    argument name as its associated value.

    Args:
      args: tuple of strings

    Returns: list of strings
    """
    values = [self.request.get(arg) for arg in args]
    for arg, val in zip(args, values):
      assert val, arg
    return values

  def create_auth_code(self, client_id, redirect_uri):
    """Generates, stores, and returns an auth code using the given parameters.

    Args:
      client_id: string
      redirect_uri: string

    Returns: string auth code
    """
    code = base64.urlsafe_b64encode(os.urandom(RANDOM_BYTES))
    self.conn.execute(
      'INSERT INTO oauth_codes(code, client_id, redirect_uri) VALUES(?, ?, ?)',
      (code, client_id, redirect_uri))
    self.conn.commit()
    return code

  def create_access_token(self, code, client_id, redirect_uri):
    """Generates, stores, and returns an access token using the given parameters.

    Args:
      code: string auth code
      client_id: string
      redirect_uri: string

    Returns: string auth code
    """
    cursor = self.conn.execute(
      'SELECT client_id, redirect_uri FROM oauth_codes WHERE code = ?', (code,))
    row = cursor.fetchone()
    assert row, ERROR_JSON % (
      'Error validating verification code: auth code %s not found' % code)
    code_client_id, code_redirect = row

    for code_arg, arg, name in ((code_client_id, client_id, 'client_id'),
                                (code_redirect, redirect_uri, 'redirect_uri')):
      assert code_arg == arg, ERROR_JSON % (
        'mismatched %s values: %s received %s, %s received %s' %
        (name, AUTH_CODE_PATH, code_arg, ACCESS_TOKEN_PATH, arg))

    token = base64.urlsafe_b64encode(os.urandom(RANDOM_BYTES))
    self.conn.execute('INSERT INTO oauth_access_tokens(code, token) VALUES(?, ?)',
                      (code, token))
    self.conn.commit()

    return token


class AuthCodeHandler(BaseHandler):
  """The auth code request handler.
  """

  ROUTES = [(r'/dialog/oauth/?', 'oauth.AuthCodeHandler')]

  def get(self):
    state = self.request.get('state')
    response_type = self.request.get('response_type')
    try:
      client_id, redirect_uri = self.get_required_args('client_id',
                                                       'redirect_uri')
    except AssertionError, e:
      self.response.out.write(ERROR_TEXT % 'missing %s' % unicode(e))
      return

    code = self.create_auth_code(client_id, redirect_uri)

    redirect_parts = list(urlparse.urlparse(redirect_uri))
    if response_type == 'token':
      # client side flow. get an access token and put it in the fragment of the
      # redirect URI. (also uses expires_in, not expires.) background:
      # http://developers.facebook.com/docs/authentication/#client-side-flow
      token = self.create_access_token(code, client_id, redirect_uri)
      if redirect_parts[5]:
        logging.warning('dropping original redirect URI fragment: %s' %
                        redirect_parts[5])
      redirect_parts[5] = urllib.urlencode(
        {'access_token': token, 'expires_in': EXPIRES})
    else:
      # server side flow. just put the auth code in the query args of the
      # redirect URI. background:
      # http://developers.facebook.com/docs/authentication/#server-side-flow
      #
      # dict(parse_qsl()) here instead of just parse_qs() so that the dict
      # values are individual elements, not lists.
      redirect_args = dict(urlparse.parse_qsl(redirect_parts[4]))
      redirect_args['code'] = code
      if state:
        redirect_args['state'] = state
      redirect_parts[4] = urllib.urlencode(redirect_args)

    # wsgiref/webob expects a non Unicode redirect_url, otherwise it
    # breaks with assert type(val) is StringType, "Header values must be strings" error.
    redirect_url = str(urlparse.urlunparse(redirect_parts))
    self.redirect(redirect_url)


class AccessTokenHandler(BaseHandler):
  """The access token request handler.
  """

  ROUTES = [(r'/oauth/access_token/?', 'oauth.AccessTokenHandler')]

  @staticmethod
  def is_valid_token(conn, access_token):
    """Returns True if the given access token is valid, False otherwise."""
    cursor = conn.execute('SELECT token FROM oauth_access_tokens WHERE token = ?',
                          (access_token,))
    return cursor.fetchone() is not None

  def get(self):
    """Handles a /oauth/access_token request to allocate an access token.

    Writes the response directly.
    """
    try:
      grant_type = self.request.get('grant_type')
      redirect_uri = self.request.get('redirect_uri')
      try:
        client_id, _, code = self.get_required_args('client_id', 'client_secret',
                                                    'code')
      except AssertionError, e:
        assert False, ERROR_JSON % 'Missing %s parameter' % unicode(e)

      # app login. background:
      # http://developers.facebook.com/docs/authentication/#applogin
      if grant_type == 'client_credentials':
        redirect_uri = ''
        code = self.create_auth_code(client_id, redirect_uri)

      token = self.create_access_token(code, client_id, redirect_uri)

      self.response.charset = 'utf-8'
      self.response.out.write(
          urllib.urlencode({'access_token': token, 'expires': EXPIRES}))
    except AssertionError, e:
      raise exc.HTTPClientError(unicode(e).encode('utf8'))

########NEW FILE########
__FILENAME__ = oauth_test
#!/usr/bin/python
"""Unit tests for oauth.py.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import httplib
import json
import re
import sqlite3
import threading
import time
import unittest
import urllib
import urlparse

import testutil

import oauth


class OAuthHandlerTest(testutil.HandlerTest):

  def setUp(self):
    super(OAuthHandlerTest, self).setUp(oauth.AuthCodeHandler,
                                        oauth.AccessTokenHandler)
    self.access_token_args = {
      'client_id': '123',
      'client_secret': '456',
      'redirect_uri': 'http://x/y',
      'code': None  # filled in by individual tests
      }

  def expect_oauth_redirect(self, redirect_re='http://x/y\?code=(.+)',
                            args=None):
    """Requests an access code, checks the redirect, and returns the code.
    """
    full_args = {
      'client_id': '123',
      'redirect_uri': 'http://x/y',
      }
    if args:
      full_args.update(args)

    resp = self.get_response('/dialog/oauth', args=full_args)
    self.assertEquals('302 Moved Temporarily', resp.status)
    location = resp.headers['Location']
    match = re.match(redirect_re, location)
    assert match, location
    return urllib.unquote(match.group(1))

  def test_auth_code(self):
    self.expect_oauth_redirect()

  def test_auth_code_with_redirect_uri_with_params(self):
    self.expect_oauth_redirect('http://x/y\?code=(.+)&foo=bar',
                               args={'redirect_uri': 'http://x/y?foo=bar'})

  def test_auth_code_with_state(self):
    self.expect_oauth_redirect('http://x/y\?state=my_state&code=(.+)',
                               args={'state': 'my_state'})

  def test_auth_code_missing_args(self):
    for arg in ('client_id', 'redirect_uri'):
      resp = self.get_response('/dialog/oauth/', args={arg: 'x'})
      self.assertEquals('200 OK', resp.status)
      assert 'An error occurred: missing' in resp.body, resp.body

  def test_access_token(self):
    code = self.expect_oauth_redirect()
    self.access_token_args['code'] = code
    resp = self.get_response('/oauth/access_token', args=self.access_token_args)

    args = urlparse.parse_qs(resp.body)
    self.assertEquals(2, len(args), `args`)
    self.assertEquals('999999', args['expires'][0])
    assert oauth.AccessTokenHandler.is_valid_token(self.conn, args['access_token'][0])

  def test_access_token_nonexistent_auth_code(self):
    self.access_token_args['code'] = 'xyz'
    resp = self.get_response('/oauth/access_token/', args=self.access_token_args)
    assert 'not found' in resp.body

  def test_nonexistent_access_token(self):
    self.assertFalse(oauth.AccessTokenHandler.is_valid_token(self.conn, ''))
    self.assertFalse(oauth.AccessTokenHandler.is_valid_token(self.conn, 'xyz'))

  def test_access_token_missing_args(self):
    for arg in ('client_id', 'client_secret'):
      args = dict(self.access_token_args)
      del args[arg]
      resp = self.get_response('/oauth/access_token', args=args)
      self.assertEquals('400 Bad Request', resp.status)
      assert ('Missing %s parameter.' % arg) in resp.body, (arg, resp.body)

  def test_access_token_different_redirect_uri_or_client_id(self):
    for arg in ('redirect_uri', 'client_id'):
      code = self.expect_oauth_redirect()
      args = dict(self.access_token_args)
      args['code'] = code
      args[arg] = 'different'
      resp = self.get_response('/oauth/access_token', args)
      self.assertEquals('400 Bad Request', resp.status)
      assert ('mismatched %s values' % arg) in resp.body, resp.body

  def test_app_login(self):
    del self.access_token_args['redirect_uri']
    self.access_token_args['grant_type'] = 'client_credentials'
    resp = self.get_response('/oauth/access_token', args=self.access_token_args)
    args = urlparse.parse_qs(resp.body)
    assert oauth.AccessTokenHandler.is_valid_token(self.conn, args['access_token'][0])

  def test_client_side_flow(self):
    token = self.expect_oauth_redirect(
      'http://x/y#access_token=(.+)&expires_in=999999',
      args={'response_type': 'token'})
    assert oauth.AccessTokenHandler.is_valid_token(self.conn, token)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = schemautil
"""Code for reading, writing, and representing the FQL schema and example data.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import collections
import copy
import datetime
import json
import os
import pprint
import re
import sqlite3

def thisdir(filename):
  return os.path.join(os.path.dirname(__file__), filename)

FQL_SCHEMA_PY_FILE = thisdir('fql_schema.py')
FQL_SCHEMA_SQL_FILE = thisdir('fql_schema.sql')
FQL_DATA_PY_FILE = thisdir('fql_data.py')
FQL_DATA_SQL_FILE = thisdir('fql_data.sql')
GRAPH_SCHEMA_PY_FILE = thisdir('graph_schema.py')
GRAPH_DATA_PY_FILE = thisdir('graph_data.py')
GRAPH_DATA_SQL_FILE = thisdir('graph_data.sql')
MOCKFACEBOOK_SCHEMA_SQL_FILE = thisdir('mockfacebook.sql')

PY_HEADER = """\
# Do not edit! Generated automatically by mockfacebook.
# https://github.com/rogerhu/mockfacebook
# %s
""" % datetime.datetime.now()
SQL_HEADER = PY_HEADER.replace('#', '--')

# TODO: other object types have aliases too, e.g. name for applications?
# see: http://graph.facebook.com/FarmVille
# but not all, e.g. http://graph.facebook.com/256884317673197 (bridgy)
# maybe the "link" field?
ALIAS_FIELD = 'username'

DEFAULT_DB_FILE = thisdir('mockfacebook.db')

def get_db(filename):
  """Returns a SQLite db connection to the given file.

  Also creates the mockfacebook and FQL schemas if they don't already exist.

  Args:
    filename: the SQLite database file
  """
  conn = sqlite3.connect(filename)
  for schema in MOCKFACEBOOK_SCHEMA_SQL_FILE, FQL_SCHEMA_SQL_FILE:
    with open(schema) as f:
      conn.executescript(f.read())
  return conn


def values_to_sqlite(input):
  """Serializes Python values into a comma separated SQLite value string.

  The returned string can be used in the VALUES(...) section of an INSERT
  statement.
  """
  output = []

  for val in input:
    if isinstance(val, bool):
      val = str(int(val))
    elif isinstance(val, basestring):
      # can't use json.dumps() because SQLite doesn't support backslash escapes.
      # also note that sqlite escapes 's by doubling them.
      val = "'%s'" % val.replace("'", "''").encode('utf8')
      # val = string_to_sqlite(val)
    elif val is None:
      val = 'NULL'
    else:
      val = json.dumps(val)

    output.append(val)

  return ',\n  '.join(output)


class PySqlFiles(object):
  """A mixin that stores data in a Python file and a SQL file.

  Subclasses must override to_sql() and py_attrs if they want SQL and Python
  file output, respectively.

  Attributes:
    py_file: string filename
    sql_file: string filename

  Class attributes:
    py_attrs: tuple of string attributes to store in the .py file
  """
  py_attrs = ()

  def __init__(self, py_file, sql_file=None):
    self.py_file = py_file
    self.sql_file = sql_file

  def to_sql(self):
    pass

  def write(self, db_file=None):
    """Writes to the Python and optionally SQL and SQLite database files.

    Args:
      db_file: string, SQLite database filename
    """
    with open(self.py_file, 'w') as f:
      print >> f, PY_HEADER
      data = dict((attr, getattr(self, attr)) for attr in self.py_attrs)
      pprint.pprint(data, f)
    self.wrote_message(self.py_file)

    sql = self.to_sql()
    if self.sql_file:
      with open(self.sql_file, 'w') as f:
        print >> f, SQL_HEADER
        print >> f, sql
      self.wrote_message(self.sql_file)

    if db_file:
      get_db(db_file).executescript(sql)      

  @classmethod
  def read(cls):
    """Factory method.
    """
    inst = cls()
    with open(inst.py_file) as f:
      for attr, val in eval(f.read()).items():
        setattr(inst, attr, val)
    return inst

  def wrote_message(self, filename):
    print 'Wrote %s to %s.' % (self.__class__.__name__, filename)


# A column in a table.
#
# Defined at the top level so that Column(...)'s in .py files can be eval'ed.
#
# Attributes:
#   name: string
#   fb_type: string FQL type
#   sqlite_type: string SQLite type
#   indexable: boolean
Column = collections.namedtuple(
  'Column', ('name', 'fb_type', 'sqlite_type', 'indexable'))


class Schema(PySqlFiles):
  """An FQL or Graph API schema.

  Attributes:
    tables: dict mapping string table name to tuple of Column
  """
  py_attrs = ('tables',)

  def __init__(self, *args, **kwargs):
    super(Schema, self).__init__(*args, **kwargs)
    self.tables = {}

  def get_column(self, table, column):
    """Looks up a column.
  
    Args:
      table: string
      column: string
  
    Returns: Column or None
    """
    # TODO: store schema columns in ordered-dict (python 2.7), then remove this.
    for col in self.tables[table]:
      if col.name == column:
        return col

  def to_sql(self):
    """Returns the SQL CREATE TABLE statements for this schema.
    """
    tables = []

    # order tables alphabetically
    for table, cols in sorted(self.tables.items()):
      col_defs = ',\n'.join('  %s %s' % (c.name, c.sqlite_type) for c in cols)
      col_names = ', '.join(c.name for c in cols)
      tables.append("""
CREATE TABLE IF NOT EXISTS `%s` (
%s,
  UNIQUE (%s)
);
""" % (table, col_defs, col_names))

    return ''.join(tables)

  def json_to_sqlite(self, object, table):
    """Serializes a JSON object into a comma separated SQLite value string.
  
    The order of the values will match the order of the columns in the schema.

    Args:
      object: decoded JSON dict
      table: string
  
    Returns: string
    """
    columns = self.tables[table]
    values = []
  
    for i, col in enumerate(columns):
      val = object.get(col.name, '')
      if isinstance(val, (list, dict)):
        # store composite types as JSON strings
        val = json.dumps(val)
      values.append(val)
  
    return values_to_sqlite(values)

  def sqlite_to_json(self, cursor, table):
    """Converts SQLite query results to JSON result objects.

    This is used in fql.py.
  
    Args:
      cursor: SQLite query cursor
      table: string
  
    Returns:
      list of dicts representing JSON result objects
    """
    colnames = [d[0] for d in cursor.description]
    columns = [self.get_column(table, name) for name in colnames]
    objects = []

    for row in cursor.fetchall():
      object = {}
      for colname, column, val in zip(colnames, columns, row):
        # by default, use the SQLite type
        object[colname] = val
        # ...except for a couple special cases
        if column:
          if val and not column.sqlite_type:
            # composite types are stored as JSON strings
            object[colname] = json.loads(val)
          elif column.fb_type == 'bool':
            object[colname] = bool(val)

      objects.append(object)

    return objects


class FqlSchema(Schema):
  """The FQL schema.
  """
  def __init__(self):
    super(FqlSchema, self).__init__(FQL_SCHEMA_PY_FILE, FQL_SCHEMA_SQL_FILE)


class GraphSchema(Schema):
  """The Graph API schema.

  Attributes:
    connections: dict mapping string table name to tuple of string connection
      names
  """
  py_attrs = ('tables', 'connections')
  connections = {}

  def __init__(self):
    super(GraphSchema, self).__init__(GRAPH_SCHEMA_PY_FILE)


# A collection of objects for a given FQL or Graph API table.
#
# Defined at the top level so that Data(...)'s in .py files can be eval'ed.
#
# Attributes:
#   query: FQL query or Graph API path used to fetch the data.
#   data: decoded JSON object (usually dict or list of dicts)
Data = collections.namedtuple('Data', ('table', 'query', 'data'))

# A single Graph API connection.
#
# Attributes:
#   table: table name
#   id: id of the source object of this connection
#   name: name of this connection
#   data: decoded JSON object (usually dict or list of dicts)
#   query (derived, read only): Graph API path used to fetch the data.
Connection = collections.namedtuple('Connection', ('table', 'id', 'name', 'data'))

@property
def _Connection_query(self):
  return '%s/%s' % (self.id, self.name)

Connection.query = _Connection_query


class Dataset(PySqlFiles):
  """A set of FQL or Graph API example data.

  Attributes:
    schema: Schema
    data: dict mapping string FQL table name or Graph API object id to Data
  """
  py_attrs = ('data',)

  def __init__(self, py_file, sql_file=None, schema=None):
    super(Dataset, self).__init__(py_file, sql_file)
    self.schema = schema
    self.data = {}
  
  
class FqlDataset(Dataset):
  """An FQL dataset.
  """
  def __init__(self, schema=None):
    if not schema:
      schema = FqlSchema.read()
    super(FqlDataset, self).__init__(FQL_DATA_PY_FILE, FQL_DATA_SQL_FILE, schema)

  def to_sql(self):
    """Returns a string with the SQL INSERT statements for this data.
    """
    output = ['BEGIN TRANSACTION;\n']

    # order tables alphabetically
    for table, data in sorted(self.data.items()):
      output.append("""
-- %s
--
-- %s
""" % (table, data.query))

      columns_str = ', '.join('`%s`' % col.name
                              for col in self.schema.tables[table])
      for object in data.data:
        # order columns to match schema (which is the order in FQL docs)
        values_str = self.schema.json_to_sqlite(object, table)
        output.append("""\
INSERT OR IGNORE INTO `%s` (
  %s
) VALUES (
  %s
);
""" % (table, columns_str, values_str))

    output.append('COMMIT;')
    return '\n'.join(output)


class GraphDataset(Dataset):
  """A Graph API dataset.

  Attributes:
    connections: list of (table name, Connection) tuples
  """
  py_attrs = ('data', 'connections')

  def __init__(self, schema=None):
    if not schema:
      schema = GraphSchema.read()
    super(GraphDataset, self).__init__(GRAPH_DATA_PY_FILE, GRAPH_DATA_SQL_FILE,
                                       schema)
    self.connections = {}

  def to_sql(self):
    """Generate SQL INSERT statements for the Graph API tables.

    One insert per row in SQLite, unfortunately. Details:
    http://stackoverflow.com/questions/1609637/
    """
    output = ['BEGIN TRANSACTION;']

    # objects and aliases
    for data in self.data.values():
      id = data.data['id']
      alias = data.data.get(ALIAS_FIELD)
      output.append(self.make_insert('graph_objects',
                                     id, alias, json.dumps(data.data)))

    # connections
    for conn in self.connections.values():
      for object in conn.data['data']:
        output.append(self.make_insert('graph_connections',
                                       conn.id, conn.name, json.dumps(object)))

    output.append('COMMIT;')
    return '\n'.join(output)

  def make_insert(self, table, *values):
    """Generates an INSERT statement for the given table and column values.

    Args:
      table: string
      values: string column values

    Returns: string
    """
    return """INSERT OR IGNORE INTO %s VALUES (\n  %s\n);""" % (
      table, values_to_sqlite(values))

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
"""mockfacebook is a mock HTTP server for the Facebook FQL and Graph APIs.

https://github.com/rogerhu/mockfacebook

Top-level HTTP server:
  server.py [--port PORT] [--me USER_ID] [--file SQLITE_DB_FILE]
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import itertools
import logging
import optparse
import sqlite3
import sys
import wsgiref.simple_server

import webapp2

import fql
import graph
import oauth
import schemautil

# how often the HTTP server should poll for shutdown, in seconds
SERVER_POLL_INTERVAL = 0.5

# optparse.Values object that holds command line options
options = None

# if there are fewer than this many FQL or Graph API rows, print a warning.
ROW_COUNT_WARNING_THRESHOLD = 10


# order matters here! the first handler with a matching route is used.
HANDLER_CLASSES = (
  oauth.AuthCodeHandler,
  oauth.AccessTokenHandler,
  fql.FqlHandler,
  # note that this also includes the front page
  graph.GraphHandler,
  )


def application():
  """Returns the WSGIApplication to run.
  """
  routes = list(itertools.chain(*[cls.ROUTES for cls in HANDLER_CLASSES]))
  return webapp2.WSGIApplication(routes, debug=True)


def parse_args(argv):
  global options

  parser = optparse.OptionParser(
    description='mockfacebook is a mock HTTP server for the Facebook Graph API.')
  parser.add_option('-p', '--port', type='int', default=8000,
                    help='port to serve on (default %default)')
  parser.add_option('-f', '--db_file', default=schemautil.DEFAULT_DB_FILE,
                    help='SQLite database file (default %default)')
  parser.add_option('--me', type='str', default=1,
                    help='user id that me() should return (default %default)')

  options, args = parser.parse_args(args=argv)
  logging.debug('Command line options: %s' % options)


def warn_if_no_data(conn):
  for kind, tables in (('FQL', fql.FqlHandler.schema.tables.keys()),
                       ('Graph API', ('graph_objects', 'graph_connections'))):
    queries = ['SELECT COUNT(*) FROM `%s`;' % t for t in tables]
    # can't use executemany because it doesn't support placeholders for table
    # names. can't use executescript because it doesn't return results. :/
    count = sum(conn.execute(q).fetchall()[0][0] for q in queries)
    if count <= ROW_COUNT_WARNING_THRESHOLD:
      quantity = 'Only %d' % count if count > 0 else 'No'
      print '%s %s rows found. Consider inserting more or running download.py.' % (
        quantity, kind)


def main(args, started=None):
  """Args:
    args: list of string command line arguments
    started: an Event to set once the server has started. for testing.
  """
  parse_args(args)
  print 'Options: %s' % options

  conn = schemautil.get_db(options.db_file)
  for cls in HANDLER_CLASSES:
    cls.init(conn, options.me)

  # must run after FqlHandler.init() since that reads the FQL schema
  warn_if_no_data(conn)

  global server  # for server_test.ServerTest
  server = wsgiref.simple_server.make_server('', options.port, application())

  print 'Serving on port %d...' % options.port
  if started:
    started.set()
  server.serve_forever(poll_interval=SERVER_POLL_INTERVAL)


if __name__ == '__main__':
  main(sys.argv)

########NEW FILE########
__FILENAME__ = server_test
#!/usr/bin/python
"""Unit tests for server.py.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import json
import os
import re
import threading
import unittest
import urllib
import urllib2
import urlparse
import warnings

import fql_test
import graph_test
import schemautil
import server
import testutil


TIME_RE = re.compile("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{4}", re.MULTILINE)


def get_data(port, path, args, data=None, method=None):
  url = 'http://localhost:%d%s?%s' % (port, path, urllib.urlencode(args))
  request = urllib2.Request(url, data)
  if method is not None:
    request.get_method = lambda: method
  return urllib2.urlopen(request).read()


def replace_ids(obj_id, string):
  composite_id = obj_id
  obj_id = composite_id.split("_")[-1]
  return string.replace(composite_id, "COMPOSITE_ID").replace(obj_id, "OBJECT_ID")


class ServerTest(unittest.TestCase):
  """Integration test. Starts the server and makes HTTP requests to localhost.

  Ideally the _test_*() methods would be real, top-level test methods, but
  starting and stopping the server for each test was too slow,
  and without class-level setUp() and tearDown(), I couldn 't hook into shutdown
  easily to stop the server. Not even an atexit handler worked. :/

  Attributes:
    db_filename: string SQLite db filename
    thread: Thread running the server
  """

  PORT = 60000
  db_filename = None
  thread = None

  def setUp(self):
    warnings.filterwarnings('ignore', 'tempnam is a potential security risk')
    self.db_filename = os.tempnam('/tmp', 'mockfacebook_test.')

    conn = schemautil.get_db(self.db_filename)
    fql_test.insert_test_data(conn)
    graph_test.insert_test_data(conn)
    conn.close()

    started = threading.Event()
    self.thread = threading.Thread(
      target=server.main,
      args=(['--db_file', self.db_filename,
             '--port', str(self.PORT),
             '--me', '1',
             ],),
      kwargs={'started': started})
    self.thread.start()
    started.wait()

  def tearDown(self):
    server.server.shutdown()
    self.thread.join()

    try:
      os.remove(self.db_filename)
    except:
      pass

  def expect(self, path, args, expected, data=None, method=None):
    """Makes an HTTP request and optionally checks the result.

    Args:
      path: string
      args: dict mapping string to string
      expected: string or regexp, or None
      method: the HTTP request method to use. i.e. GET, POST, DELETE, PUT

    Returns:
      string response
    """
    resp = get_data(self.PORT, path, args, data, method)
    if expected:
      self.assertEquals(json.loads(expected), json.loads(resp))
    return resp

  def check_fb_result(self, obj_id, result, expected):
    """Checks the given Facebook result against the given expected result
       This will use regular expressions to replace Facebook ids and timestamps

    Args:
      obj_id: The Facebook object id
      result: The result from the mock to check. Will be cleaned by regexes.
      expected: The expected result. Should contain the regex cleaned result.
    """
    result_cleaned = replace_ids(obj_id, TIME_RE.sub("TIMESTAMP", result))
    # print result_cleaned.replace("\n", "\\n")  # useful for getting the expected output
    self.assertEquals(json.loads(result_cleaned), json.loads(expected))

  def test_all(self):
    self._test_post_and_delete()
    self._test_fql()
    self._test_graph()
    self._test_oauth()
    self._test_404()

  def _test_fql(self):
    query = 'SELECT username FROM profile WHERE id = me()'
    expected = '[{"username": "alice"}]'
    self.expect('/method/fql.query', {'query': query, 'format': 'json'}, expected)
    self.expect('/fql', {'q': query}, expected)

  def _test_graph(self):
    self.expect('/1', {}, '{"foo": "bar", "id": "1"}')
    self.expect('/bob/albums', {}, '{"data": [{"id": "5"}]}')
    self.expect('/me', {}, '{\n  "foo": "bar", \n  "id": "1"\n}')

  def _test_post_and_delete(self):
    resp = get_data(self.PORT, "/3/feed", {}, method="POST")
    resp_json = json.loads(resp)
    status_id = resp_json["id"]
    resp = get_data(self.PORT, "/%s" % status_id, {})

    # verify the correct the correct data was posted.
    expected_status = '{\n  "from": {\n    "category": "Test", \n    "name": "Test", \n    "id": "1"\n  }, \n  "actions": [\n    {\n      "link": "https://www.facebook.com/3/status/OBJECT_ID", \n      "name": "Comment"\n    }, \n    {\n      "link": "https://www.facebook.com/3/status/OBJECT_ID", \n      "name": "Like"\n    }\n  ], \n  "updated_time": "TIMESTAMP", \n  "application": {\n    "id": "1234567890", \n    "namespace": "test", \n    "name": "TestApp", \n    "canvas_name": "test"\n  }, \n  "comments": {\n    "count": 0\n  }, \n  "created_time": "TIMESTAMP", \n  "type": "status", \n  "id": "COMPOSITE_ID", \n  "icon": "http://invalid/invalid"\n}'
    self.check_fb_result(status_id, resp, expected_status)

    # make sure the publish shows up in the feed
    resp = get_data(self.PORT, "/3/feed", {})
    self.check_fb_result(status_id, resp, '{\n  "data": [\n    %s\n  ]\n}' % expected_status)
    # feed should be the same as posts
    self.assertEquals(resp, get_data(self.PORT, "/3/posts", {}))

    # add a comment
    resp = get_data(self.PORT, "/%s/comments" % status_id, {}, method="POST")
    resp_json = json.loads(resp)
    comment_id = resp_json["id"]
    # check that the comment is there
    resp = get_data(self.PORT, "/%s" % comment_id, {})
    expected_comment = '{\n  "from": {\n    "category": "Test", \n    "name": "Test", \n    "id": "1"\n  }, \n  "likes": 0, \n  "created_time": "TIMESTAMP", \n  "message": "", \n  "type": "comment", \n  "id": "COMPOSITE_ID"\n}'
    self.check_fb_result(comment_id, resp, expected_comment)
    # check that the post has the comment
    expected_status_2 = json.loads(expected_status)
    expected_status_2["comments"] = {"count": 1, "data": [json.loads(expected_comment)]}
    resp = get_data(self.PORT, "/%s" % status_id, {})
    self.check_fb_result(status_id, replace_ids(comment_id, resp), json.dumps(expected_status_2))

    # Test clearing posts
    self.expect("/clear", {}, '{"response": "ok"}', method="DELETE")
    self.assertRaises(urllib2.HTTPError, get_data, self.PORT, '/%s' % status_id, {})
    self.expect('/3/feed', {}, '{\n  "data": []\n}')

  def _test_oauth(self):
    args = {'client_id': 'x',
            'client_secret': 'y',
            'redirect_uri': 'http://localhost:%d/placeholder' % self.PORT,
            }
    try:
      self.expect('/dialog/oauth', args, None)
      self.fail('Expected 404 not found on placeholder redirect')
    except urllib2.HTTPError, e:
      self.assertEquals(404, e.code)
      url = e.url

    args['code'] = urlparse.parse_qs(urlparse.urlparse(url).query)['code'][0]
    resp = self.expect('/oauth/access_token', args, None)
    assert re.match('access_token=.+&expires=999999', resp), resp

  def _test_404(self):
    try:
      resp = self.expect('/not_found', {}, '')
      self.fail('Should have raised HTTPError')
    except urllib2.HTTPError, e:
      self.assertEquals(404, e.code)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = testutil
"""Unit test utilities.
"""

__author__ = ['Ryan Barrett <mockfacebook@ryanb.org>']

import cStringIO
import json
import re
import sqlite3
import sys
import unittest
import urllib

import webapp2

import schemautil
import server


def maybe_read(dataset_cls):
  """Tries to read and return a dataset. If it fails, prints an error.
  """
  try:
    return dataset_cls.read()
  except IOError, e:
    print >> sys.stderr, 'Warning: skipping example data tests due to:\n%s' % e
    return None


class HandlerTest(unittest.TestCase):
  """Base test class for webapp2 request handlers.

  Attributes:
    conn: SQLite db connection
    app: WSGIApplication
  """

  ME = '1'
  conn = None

  def setUp(self, *handler_classes):
    """Args:
    handler_classes: RequestHandlers to initialize
    """
    super(HandlerTest, self).setUp()

    self.conn = schemautil.get_db(':memory:')
    for cls in handler_classes:
      cls.init(self.conn, self.ME)

    self.app = server.application()

  def expect(self, path, expected, args=None, expected_status=200):
    """Makes a request and checks the response.

    Args:
      path: string
      expected: if string, the expected response body. if list or dict,
        the expected JSON response contents.
      args: passed to get_response()
      expected_status: integer, expected HTTP response status
    """
    response = None
    results = None
    try:
      response = self.get_response(path, args=args)
      self.assertEquals(expected_status, response.status_int)
      response = response.body
      if isinstance(expected, basestring):
        self.assertEquals(expected, response)
      else:
        results = json.loads(response)
        if not isinstance(expected, list):
          expected = [expected]
        if not isinstance(results, list):
          results = [results]
        expected.sort()
        results.sort()
        self.assertEquals(len(expected), len(results), `expected, results`)
        for e, r in zip(expected, results):
          self.assert_dict_equals(e, r)
    except:
      print >> sys.stderr, '\nquery: %s %s' % (path, args)
      print >> sys.stderr, 'expected: %r' % expected
      print >> sys.stderr, 'received: %r' % results if results else response
      raise

  def get_response(self, path, args=None):
    if args:
      path = '%s?%s' % (path, urllib.urlencode(args))
    return self.app.get_response(path)

  # TODO: for the love of god, refactor, or even better, find a more supported
  # utility somewhere else.
  def assert_dict_equals(self, expected, actual):
    msgs = []

    if isinstance(expected, re._pattern_type):
      if not re.match(expected, actual):
        self.fail("%r doesn't match %s" % (expected, actual))
    # this is only here because we don't exactly match FB in whether we return
    # or omit some "empty" values, e.g. 0, null, ''. see the TODO in graph_on_fql.py.
    elif not expected and not actual:
      return True
    elif isinstance(expected, dict) and isinstance(actual, dict):
      for key in set(expected.keys()) | set(actual.keys()):
        self.assert_dict_equals(expected.get(key), actual.get(key))
    else:
      if isinstance(expected, list) and isinstance(actual, list):
        expected.sort()
        actual.sort()
      self.assertEquals(expected, actual)

########NEW FILE########
__FILENAME__ = webapp2
webapp-improved/webapp2.py
########NEW FILE########
