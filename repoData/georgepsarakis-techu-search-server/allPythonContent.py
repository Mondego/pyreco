__FILENAME__ = fabfile
from fabric.api import run
from fabric.context_manages import cd, lcd

OPTIONAL_PACKAGES = [ 'beautifulsoup4', 'hiredis', ]
REQUIRED_PACKAGES = [
  'django', 'django_graceful', 'redis', 'hiredis',  
]

def compiler(url, folder):
  with cd('/tmp'):
    run('wget "%s" -O source.tar.gz' % url)
    run('tar -zxvf source.tar.gz')
    run('cd %s' % folder)
    run('make')
    run('make install')
    run('make test')
    run('rm -rf /tmp/' + folder.strip('/'))
  
#  redis-2.6.13')
  run('cd redis-2.6.13')
  
  run('wget http://redis.googlecode.com/files/redis-2.6.13.tar.gz')

run('apt-get install python-setuptools')
run('apt-get install nginx python-flup')
run('apt-get install mysql-server python-mysqldb')
http://sphinxsearch.com/files/sphinx-2.1.1-beta.tar.gz
run('apt-get install libhiredis0.10 libhiredis-dev')

python_packages = REQUIRED_PACKAGES + OPTIONAL_PACKAGES
for package in python_packages:
  run('easy_install %s' % package)



########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techu.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = views
from techu.libraries.generic import *
from django.shortcuts import render
from django.http import HttpResponse
from techu.models import *
import requests
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

def highlighter(request):
  code = request.REQUEST['code']
  if not 'lang' in request.REQUEST:
    language = 'json'
  else:
    language = request.REQUEST['lang']
  lexer = get_lexer_by_name(language)
  formatter = HtmlFormatter(linenos = False)
  result = highlight(code, lexer, formatter)
  return R({ 'code' : result })

def home(request):
  params = { 'content' : '<h1>Dashboard</h1>' }
  params['json_data'] = configurations()
  params['url'] = request.get_full_path()
  return render(request, 'dashboard.html', params)

def configurations():
  data = {
    'configurations'        : json.dumps(Configuration.objects.all().order_by('name'), cls=Serializer),
    'indexes'               : json.dumps(Index.objects.all().order_by('name'), cls=Serializer),
    'searchd'               : json.dumps(Searchd.objects.all(), cls=Serializer),
    'configuration_index'   : json.dumps(ConfigurationIndex.objects.all(), cls=Serializer),
    'configuration_searchd' : json.dumps(ConfigurationSearchd.objects.all(), cls=Serializer),
    'index_options'         : json.dumps(IndexOption.objects.all(), cls=Serializer),
    'searchd_options'       : json.dumps(SearchdOption.objects.all(), cls=Serializer),
    'options'               : json.dumps(Option.objects.all().order_by('name'), cls=Serializer),
  }
  return ";\n".join([ k + ' = ' + data[k] for k in data.keys() ])

def api_playground(request, request_type = ''):
  base_url = 'https://techu'
  params = { 
    'request_type' : request_type,
    'url'          : base_url + '/' + request_type,    
    'data'         : {}
    }
  if request_type == '':
    params['data']['pretty'] = 1
    api_response = fetch_url(params['url'], params['data']) 
    params['api_response'] = api_response
  params['json_data'] = configurations()
  params['url'] = request.get_full_path()
  return render(request, 'api-playground.html', params)

def fetch_url(url, data):
  r = requests.post(url, data = data, verify = False)
  r.encoding = 'utf-8'
  return r.content

def fetch_api(request):
  data = {}
  url = request.POST['url']
  if 'pretty' in request.POST and request.POST['pretty'] == '1':
    data['pretty'] = 1
  else:
    data['pretty'] = 0
  return R(fetch_url(url, data), request, serialize=False)

########NEW FILE########
__FILENAME__ = encode
#!/usr/bin/python
import sys
from urllib import urlencode

variable = sys.argv[1]
data = sys.argv[2]

print urlencode({ variable : data})

########NEW FILE########
__FILENAME__ = se-fetch
#!/usr/bin/python
import os, sys
import time 
import json
import codecs
from bs4 import BeautifulSoup as bs
import requests

def strip_tags(el):
  return '' . join( el.findAll(text = True) )

fetch_url = r'wget -q -O- --header\="Accept-Encoding: gzip" "%(url)s" | gunzip > %(json)s'

url = 'http://api.stackexchange.com/2.1/posts?page=%d&pagesize=100&order=desc&sort=activity&site=stackoverflow'

''' Download 20x100 posts (questions & answers) from StackOverflow '''
fw = codecs.open('data.json', mode = 'a', encoding = 'utf-8')
for n in range(1, 21):
  print 'Downloading page', n
  cmd = fetch_url % { 'url' : url % n, 'json' : 'page.%d.json' % n }
  print cmd
  os.system(cmd)
  print 'Formatting JSON data for import ...'
  f = codecs.open('page.%d.json' %n, mode = 'r', encoding = 'utf-8')
  d = json.loads(''.join(f.readlines()))
  f.close()
  os.system("rm 'page.%d.json'" % n)
  for item in d['items']:
    post_item = {}
    post_item['id'] = item['post_id']
    post_item['title'] = ''
    post_item['body'] = ''
    post_item['creation_date'] = item['creation_date']
    post_item['last_activity_date'] = item['last_activity_date']
    post_item['is_answer'] = int(item['post_type'] == 'answer')
    post_item['score'] = item['score']
    if 'owner' in item:
      post_item['user_id'] = item['owner']['user_id']
    else:
      post_item['user_id'] = 0
    html = requests.get(item['link'])
    soup = bs(html.text)
    body = ''
    title = ''
    if item['post_type'] == 'answer':
      body = soup.find('div', id = 'answer-' + str(item['post_id']))      
    else:
      body = soup.find('div', id = 'question')
      title = soup.find('div', id = 'question-header').find('a', {'class' : 'question-hyperlink'});
    post_item['body'] = strip_tags( body.find('div', { 'class' : 'post-text' }))
    if title != '':
      post_item['title'] = strip_tags( title )
    fw.write(json.dumps(post_item) + "\n")
    time.sleep(0.001)
  time.sleep(10.0)

fw.close()

########NEW FILE########
__FILENAME__ = urls
#!/usr/bin/python
import codecs
from urllib import urlencode

f = codecs.open('data.json', encoding = 'utf-8', mode = 'r')
print '#!/bin/bash'
for r in f.readlines():
  print "echo '%s'" % urlencode({ 'data' : r })
  print "curl --silent 'http://techu:81/indexer/insert/28/' -d '%s'" % urlencode({ 'data' : r })
f.close()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Techu documentation build configuration file, created by
# sphinx-quickstart on Tue May  7 16:17:04 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.append('/home/techu-search-server/techu/') # The directory that contains settings.py

# Set up the Django settings/environment
from django.core.management import setup_environ
import settings

setup_environ(settings)

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [ 'sphinx.ext.autodoc' ]
autodoc_string_signature = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Techu'
copyright = u'2013, George Psarakis'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2'
# The full version, including alpha/beta/rc tags.
release = '0.2-beta'

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
exclude_patterns = []

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'Techudoc'


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
  ('index', 'Techu.tex', u'Techu Documentation',
   u'George Psarakis', 'manual'),
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
    ('index', 'techu', u'Techu Documentation',
     [u'George Psarakis'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Techu', u'Techu Documentation',
   u'George Psarakis', 'Techu', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = applier
#!/usr/bin/python
import imp, os, sys
import time, re 
import marshal
from generic import *
from django.db import transaction, connections
from django.db import IntegrityError, DatabaseError
from daemon import Daemon
from middleware import ConnectionMiddleware
import logging

class QueueDaemon(Daemon):
  '''
  |  Daemon script that applies queued operations to indexes
  
  *Notes*
  * Different instances should be spawned for each index
  '''
  Logger = None
  def fetch_indexes(self):
    '''
    Get all active realtime indexes.
    '''
    sql = '''SELECT i.id, i.name FROM sp_indexes i 
      JOIN sp_configuration_index sci ON i.id = sci.sp_index_id 
      WHERE sci.is_active AND i.index_type = 1'''
    c = connections['default'].cursor()
    c.execute(sql)
    indexes = {}
    for row in cursorfetchall(c):
      indexes[row['id']] = row['name']
    return indexes

  def run(self):
    '''
    **UNDER DEVELOPMENT**
    The actual code for applying operations.
    '''
    sys.stdout.write("Applier daemon started ...\n" )
    sys.stdout.flush()
    indexes = self.fetch_indexes()
    r = redis_client()
    replace = re.compile(r'^INSERT\s+')
    while(True):
      for index_id, index in indexes.iteritems():
        m = connections['sphinx:' + str(index_id)].cursor()
        keys = r.lrange('queue:' + str(index_id), 0, -1)
        if keys:
          for key in keys:
            data = r.get(key)
            data = marshal.loads(data) 
            self.Logger.info('Applying key ' + key)
            action = key.split(':')[0]
            try:
              m.executemany(data['sql'], data['values'])
            except IntegrityError as e:
              pass
            except DatabaseError as e:
              if action == 'insert':
                m.executemany(replace.sub('REPLACE ', data['sql']), data['values'])
              else:
                pass            
            p = r.pipeline()
            p.lpop('queue:' + str(index_id))
            p.delete(key)
            p.hset(index + ':last-modified', action, int(time.time()*10**6))
            p.execute()            
      time.sleep(0.001) #sleep for 1ms

if __name__ == '__main__':
  connection = ConnectionMiddleware()
  connection.process_request({})
  try:
    action = sys.argv[1].lower()
  except:
    action = 'start'  
  ''' Move to settings.py '''
  LOGFORMAT = '%(asctime)s %(message)s' 
  DATEFORMAT = '%Y%m%d %H:%M:%S'
  PIDFILE = os.path.join( '/' . join(os.path.dirname(os.path.realpath(__file__)).split('/')[0:-2]), 'sphinxqueue.pid')
  OUTFILE = os.path.join(os.path.dirname(PIDFILE), 'sphinxqueue.out')
  LOGFILE = os.path.join(os.path.dirname(PIDFILE), 'sphinxqueue.log')
  queue = QueueDaemon(PIDFILE, stdout = OUTFILE)
  if action == 'start':
    logging.basicConfig(format = LOGFORMAT, filename = LOGFILE, datefmt = DATEFORMAT, level = logging.DEBUG)
    queue.Logger = logging.getLogger('Queue Applier')
    queue.start()
  elif action == 'status':
    queue.status()
  elif action == 'restart':
    queue.restart()
  elif action == 'stop':
    queue.stop()

########NEW FILE########
__FILENAME__ = authentication
#!/usr/bin/python
from generic import settings
import sys, hmac
from techu.models import Authentication
from time import time
from hashlib import sha1
from random import choice
from string import digits, ascii_letters

class Auth(object):
  '''
  Authentication protocol
  Resembles OAuth process: 
  *  Client receives a Consumer Key/Secret pair
  *  Constructs an authentication token with HMAC-SHA1 which is sent on each request.
  The Consumer Key and the Secret are comprised from ASCII uppercase & lowercase letters & digits
  This script can also be used as a command-line executable to generate key/secret pairs

  :ivar __token_salt: a salt for the generated secret
  :ivar __consumer_key: the consumer_key sent on each request and is unique for each client (8 characters)
  :ivar __secret: the secret from which a the request token is generated (16 characters)
  '''
  __token_salt   = ''
  __consumer_key = ''
  __secret       = ''

  def __init__(self, consumer_key = ''):
    self.__token_salt = str(time())
    self.__consumer_key = consumer_key

  def get_secret(self):
    '''
    Returns the secret for a consumer key.
    '''
    if self.__consumer_key == '': 
      return True
    auth = Authentication.objects.filter(consumer_key=self.__consumer_key)
    if not auth:
      return False
    else:
      return auth[0].secret

  def update_secret(self):
    '''
    Re-generate secret for a specific consumer key.
    '''
    if self.__consumer_key != '':
      auth = Authentication.objects.filter(consumer_key = self.__consumer_key, secret = self.__secret)
      if not auth:
        return False
      else:
        auth.secret = self.generate_secret()
        auth.save()
        self.__secret = auth.secret
        return True
    return False

  def randomize(self, length, elements = None):
    '''
    |  Return a random string of specified length.
    |  If *elements* parameter is *None* (default) ASCII uppercase, lowercase & digits are used as selection group.
    '''
    if elements is None:
      elements = ascii_letters + digits
    return ''.join([ choice(elements) for n in range(length) ])

  def generate_secret(self):
    '''
    Generate a random secret with a length of 16 characters.
    '''   
    return self.randomize(16, sha1(self.__token_salt + self.randomize(20)).hexdigest())
    
  def generate(self):
    '''
    Returns a consumer key & secret pair.
    '''
    self.__consumer_key = self.randomize(8)
    while self.get_secret():
      self.__consumer_key = self.randomize(8)
    self.__secret = self.generate_secret()
    Authentication.objects.create(consumer_key = self.__consumer_key, secret = self.__secret)
   
  def verify(self, token):
    '''
    Test token using HMAC-SHA1.
    '''
    h = hmac.new(str(self.get_secret()), str(self.__consumer_key), sha1)
    return ( h.hexdigest() == token, token )
  
  def __str__(self):
    '''
    Print consumer key/secret pair.
    '''
    return self.__consumer_key + ' ' + self.__secret

if __name__ == '__main__':
  if len(sys.argv) == 1:
    sys.argv.append('test')
  if sys.argv[1] == 'test':
    ''' test pair -> NBA1e4Ah 1e7fc2c4a1d5d7d1 '''
    test_consumer = 'NBA1e4Ah'
    test_secret = '1e7fc2c4a1d5d7d1'
    auth = Auth(test_consumer)
    token = hmac.new(test_secret, test_consumer, sha1).hexdigest()
    print token
    print auth.verify(token)  
  elif sys.argv[1] == 'generate':
    auth = Auth()
    auth.generate()
    print auth


########NEW FILE########
__FILENAME__ = caching
from __future__ import unicode_literals
from generic import *
import time
import marshal
from hashlib import sha1

class FunctionCache(object):
  '''
  |  Creates a key with the function name and a hash of the arguments.
  |  Parameter values (or keyword argument parameter values) **must be serializable**.
  |  Used as a view decorator.
  '''
  __cache = None
  def __init__(self, fn):
    self.fn = fn
    self.__cache = Cache()

  def __call__(self, *args, **kwargs):
    if settings.FUNCTION_CACHE and not (len(args) > 0 and 'c' in args[0].REQUEST and args[0].REQUEST['c'] == '0'):
      cache_key = json.dumps(args, cls=Serializer) + json.dumps(kwargs, cls=Serializer)
      cache_key = cache_key.encode('utf-8')
      cache_key = self.fn.__name__ + ':' + sha1(cache_key).hexdigest()
      ''' check if function result is cached '''
      result = self.__cache.get(cache_key)
      if result:
        return result
      else:
        result = self.fn(*args, **kwargs)
        self.__cache.set(cache_key, result)
      return result
    else:
      return self.fn(*args, **kwargs)

class Cache(object):
  '''
  |  Caching wrapper around Redis client.
  |  Supports setting keys with *WATCH* as a CAS device along with expiration.
  |  Also supports hash (dictionary) operations, handles invalidations and marks indexes as "dirty".
  '''
  __R = None

  def __init__(self):
    self.__R = redis_client()
  
  def delete(self, keys, expires = 500):
    ''' 
    |  Set key expiration at specified time in milliseconds.
    |  Allows *soft* deletion by setting low expiration times.
    |  If you set the *expires* parameter to 0 an immediate delete is performed (via the *DELETE* command)
    '''
    if isinstance(keys, basestring):
      keys = [keys]
    p = self.transaction()
    for key in keys:
      try:
        if expires == 0:
          p.delete(key)
        else:
          p.pexpire(key, expires)
      except:
        return False
    try:
      p.execute()
    except:
      return False
    return True

  def exists(self, key):
    '''
    Check if a key exists in Redis
    '''
    return self.__R.exists(key)

  def hget(self, key):
    '''
    Return all entries in a Redis hash structure as a dict
    '''
    return self.__R.hgetall(key)

  def get(self, key, unserialize = True):
    '''
    Return a value from Redis.
    Optionally transforms result ( when *unserialize* parameter is True - default ) through `marshal.loads <http://docs.python.org/2/library/marshal.html#marshal.loads>`_
    '''
    value = self.__R.get(key)
    if value is None:
      return None
    if unserialize:
      return marshal.loads(value)
    else:
      return value

  def hset(self, key, inner_key, value, watch = False, expire = 0., lock = None):
    '''
    Set a hash entry in the structure specified by *key* and hash key *inner_key*
    '''
    r = None
    try:
      p = self.transaction()
      p.hset(key, inner_key, value)
      if watch:
        p.watch(key)
      r = p.execute()
    except:
      r = False
    return r

  def set(self, key, value, watch = False, expire = 0., lock = None, keylist = None):
    ''' 
    |  Store a key-value pair in Redis.
    |  Optionally add *WATCH* for implementing CAS.
    |  Supports also key-lock releasing in case cache locks are implemented (avoiding stampeding herd).
    |  *expire* parameter is in seconds but of float type, multiplied by 10**3 and passed to *PEXPIRE* command
    '''
    try:
      cache_time = int(time.time() * 10**6)
      value = marshal.dumps(value)
      p = self.transaction()      
      if watch:
        p.watch(key)
      p.set(key, value)
      if not keylist is None:
        p.rpush(keylist, key)
      if expire > 0:
        p.pexpire(key, int(expire * 10**3))
      if not lock is None:
        p.delete(lock)
      p.execute()
      return True
    except:
      return False

  def invalidate(self, index_id, version):
    '''
    Invalidate cache entries
    '''
    version_pattern = '*:%d:%s' % (index_id, version)
    p = self.transaction()
    self.delete( self.__R.keys(version_pattern) )
  
  def version(self, index_id):
    '''
    Index version
    '''
    index_key = 'version:%d' % (index_id,)
    version = self.get(index_key, False)
    if version is None:
      return 1
    else:
      return int(version)
  
  def transaction(self):
    '''
    Start a consistent & isolated operation (transaction)
    '''
    return self.__R.pipeline()

  def dirty(self, index_id, action = ''):
    '''
    |  Mark an index as "dirty" thus containing changes that 
    |  require cache entries concerning that index to be invalidated.
    |  Specific actions will give finer control over invalidations in the future.
    '''
    modification_time = int(time.time() * 10**6)
    index_key = 'version:%s' % (str(index_id),)
    old_version = self.__R.get(index_key)
    p = self.transaction()
    p.watch(index_key)
    p.set(index_key, modification_time)
    try:
      p.execute()
      self.invalidate(index_id, old_version)
    except redis.WatchError as e:
      pass
    return True


########NEW FILE########
__FILENAME__ = daemon
"""
http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
"""
import sys, os, time, atexit
from signal import SIGTERM 

class Daemon:
  """
  A generic daemon class.
  
  Usage: subclass the Daemon class and override the run() method
  """
  def __init__(self, pidfile, stdin = '/dev/null', stdout = '/dev/null', stderr = '/dev/null'):
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    self.pidfile = pidfile
  
  def daemonize(self):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced 
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try: 
      pid = os.fork() 
      if pid > 0:
        # exit first parent
        sys.exit(0) 
    except OSError, e: 
      sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)
  
    # decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(0) 
  
    # do second fork
    try: 
      pid = os.fork() 
      if pid > 0:
        # exit from second parent
        sys.exit(0) 
    except OSError, e: 
      sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1) 
  
    # redirect standard file descriptors
      if self.stdout.upper() == 'STDOUT':
        sys.stdout.flush()
        so = file(self.stdout, 'a+')
        os.dup2(so.fileno(), sys.stdout.fileno())
      if self.stderr.upper() == 'STDERR':
        sys.stderr.flush()
        se = file(self.stderr, 'a+', 0)
        os.dup2(se.fileno(), sys.stderr.fileno())
    si = file(self.stdin, 'r')
    os.dup2(si.fileno(), sys.stdin.fileno())
  
    # write pidfile
    atexit.register(self.delpid)
    pid = str(os.getpid())
    file(self.pidfile,'w+').write("%s\n" % pid)
  
  def delpid(self):
    os.remove(self.pidfile)
  
  def status(self):
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None
      sys.exit(1)
    sys.stdout.write('Daemon running with PID %d' % pid)
    sys.stdout.flush()
 

  def start(self):
    """
    Start the daemon
    """
    # Check for a pidfile to see if the daemon already runs
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None
  
    if pid:
      message = "pidfile %s already exist. Daemon already running?\n"
      sys.stderr.write(message % self.pidfile)
      sys.exit(1)
    
    # Start the daemon
    self.daemonize()
    self.run()

  def stop(self):
    """
    Stop the daemon
    """
    # Get the pid from the pidfile
    try:
      pf = file(self.pidfile,'r')
      pid = int(pf.read().strip())
      pf.close()
    except IOError:
      pid = None
  
    if not pid:
      message = "pidfile %s does not exist. Daemon not running?\n"
      sys.stderr.write(message % self.pidfile)
      return # not an error in a restart

    # Try killing the daemon process  
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(0.1)
    except OSError, err:
      err = str(err)
      if err.find("No such process") > 0:
        if os.path.exists(self.pidfile):
          os.remove(self.pidfile)
      else:
        print str(err)
        sys.exit(1)

  def restart(self):
    """
    Restart the daemon
    """
    self.stop()
    self.start()

  def run(self):
    """
    You should override this method when you subclass Daemon. It will be called after the process has been
    daemonized by start() or restart().
    """

########NEW FILE########
__FILENAME__ = generic
import os, imp
import MySQLdb
import re, json, datetime
import redis
from django.core.management import setup_environ
settings_path = '/'.join(os.path.dirname(os.path.realpath(__file__)).split('/')[0:-1])
settings = imp.load_source('settings', os.path.join( settings_path,  'settings.py'))
setup_environ(settings)
from django.http import HttpResponse
from django.db import models
from time import mktime

modules = None
def _import(module_list):
  ''' 
  Dynamic imports may boost performance since functions require different packages 
  e.g. libraries.sphinxapi is only used for search and excerpts calls (needs some benchmarking)
  '''
  global modules
  for m in map(__import__, module_list):
    if not m in modules:
      modules.append(m)

def filter_list(r, fields):
  '''
  |  Filter conditions from a request and create an appropriate dictionary which is passed to *filter* as kwargs.
  |  Example:

  `filter_list(r, { 'name' : 'startswith', 'section' : None })`
  
  | Passing *None* will use *__exact* as an operator.
  '''
  conditions = {}
  for param, field in fields.iteritems():
    if param in r:
      if field is None:
        field = param + '__exact'
      else:
        field = param + '__' + field
      conditions[field] = r[param]
  return conditions

def is_queryset(o):
  '''
  Check if a variable is QuerySet. Returns Boolean.
  '''
  return isinstance(o, models.query.QuerySet)

def is_model(o):
  '''
  Check if a variable is instance of Model. Returns Boolean.
  '''
  return isinstance(o, models.Model)

def debug(r):
  '''
  Raise exception so that passes through the Exception logging middleware.
  '''
  indent = 4
  separators = (',', ': ')
  r = { 'debug' : r }
  raise Exception(json.dumps(r, cls=Serializer, indent = indent, separators = separators))

def is_queued(request):
  '''
  Check if a request requires operation queueing. Returns Boolean.
  '''
  if 'queue' in request.REQUEST:
    return ( int(request.REQUEST['queue']) == 1 )
  else:
    return False

class Serializer(json.JSONEncoder):
  ''' 
  JSON serializer for list, dict and QuerySet objects.
  '''
  def default(self, o):
    '''
    Default serializer method. Enables QuerySet & datetime support.
    '''
    if is_queryset(o):
      obj = []
      for q in o:
        opts = q._meta
        data = {}
        for field in opts.fields:
          if field.name == 'id':
            value = q.pk 
          else:
            value = field.value_from_object(q)
          name = field.name                      
          data[name] = value
        obj.append(data)
      return obj
    if isinstance(o, datetime.datetime):
      return int( mktime(o.timetuple()) )
    return json.JSONEncoder.default(self, o)

def E(code = 500, **kwargs):
  '''
  Return an HttpResponse with error code. 
  '''
  response = HttpResponse()
  response.status_code = code
  if 'message' in kwargs:
    message = kwargs['message']
  else:
    message = 'Internal Server Error'
  response.content = message
  return response

def R(data, request = None, **kwargs):
  ''' 
  |  Return a successful, normal HttpResponse (status code 200).   
  |  Serializes by default any object passed.
  |  Passing the GET/POST parameter *pretty=1* will result in pretty-printed output.
  '''
  if not request is None:
    if 'pretty' in request.REQUEST:
      kwargs['pretty'] = (request.REQUEST['pretty'].lower() in [ '1', 'true'])
  defaults = { 'code' : 200, 'serialize' : True, 'pretty' : False }
  kwargs = dict(defaults.items() + kwargs.items())
  if kwargs['pretty']:
    indent = 4
    separators = (',', ': ')
  else:
    indent = None
    separators = (',', ':')
  if kwargs['serialize']:
    data = json.dumps(data, cls=Serializer, indent = indent, separators = separators)
  r = HttpResponse(content = data, status = kwargs['code'], content_type = 'application/json;charset=utf-8')
  return r

def redis_client():
  '''
  Return a Redis 2.6 `client instance <https://github.com/andymccurdy/redis-py>`_
  '''
  return redis.StrictRedis(
                 host = settings.REDIS_HOST, 
                 port = settings.REDIS_PORT, 
                 password = settings.REDIS_PASSWORD)

def cursorfetchall(cursor):
  '''
  Returns all rows from a DB cursor as a dictionary 
  '''
  desc = cursor.description
  return [
      dict(zip([col[0] for col in desc], row))
      for row in cursor.fetchall()
  ]

def regex_check(s, r = r'[^a-zA-Z0-9\-_]+'):
  '''
  Regex check for ASCII letters & digits, dash & underscore
  '''
  return (re.match(r, s) is None)

def identq(s):
  '''
  Quote an SQL identifier.
  '''
  return '`' + s.replace('`', '') + '`'

def model_to_dict(instance, fields_only = []):
  '''
  |  Convert a model instance to dictionary.
  |  Use *fields_only* parameter to narrow down the returned field values.
  '''
  data = {}
  for field in instance._meta.fields:
    if fields_only and not field in fields_only:
      continue 
    data[field.name] = field.value_from_object(instance)
  return data

def request_data(req):
  ''' 
  |  Combine GET & POST dictionaries. POST has higher priority.
  |  If request contains *data* parameter then it is unserialized from JSON format and the result is returned.  
  '''
  p = req.POST.dict()
  g = req.GET.dict()
  r = dict(req.GET.dict().items() + req.POST.dict().items())
  if 'data' in r:
    try:
      r = json.loads(r['data'])
    except:
      pass
  return r

def model_fields(model, r):  
  '''
  |  Filter values from dictionary parameter *r* which are fields of the model parameter *model*.
  |  Returns dictionary with the model field values and fields as keys.
  '''
  opts = model._meta
  model_data = {}
  for f in model._meta.fields:
    if f.name in r:
      model_data[f.name] = r[f.name]  
  return model_data

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.db import connections, connection
from generic import *
from copy import deepcopy
from traceback import format_exception
import sys, re

class ExceptionLoggingMiddleware(object):
  '''
  |  Exception middleware which allows more clear & efficient printouts of errors raised.
  |  Particularly, it overrides the default debug pages of Django which contain extensive HTML
  |  and returns plain text in case the request is performed with the *curl* command-line tool
  |  or JSON-formatted as an API response inside client applications.
  '''
  def process_response(self, request, response):
    if response.status_code != 200:
      ''' 
      If called from command line print output plain text, otherwise return as JSON
      '''
      if not re.match(r'^curl/', request.META['HTTP_USER_AGENT'].lower()) is None:
        response.content = r
      else:      
        indent = 4
        separators = (',', ': ')
        response.content = json.dumps(r, cls=Serializer, indent = indent, separators = separators)
    return response

class ConnectionMiddleware(object):
  '''    
  |  Automatically setup connections to the mysql41 interface of the Sphinx realtime indexes. 
  |  One connection is created for each index. 
  |  This is implemented as a middleware in order to make connections available to all requests.
  '''
  def process_request(self, request):
    cursor = connection.cursor()
    sql = '''SELECT sp_searchd_id, value FROM sp_searchd_option 
             WHERE sp_option_id = 138 AND value LIKE "%%mysql41"'''
    cursor.execute(sql)
    ports = {}
    for row in cursorfetchall(cursor):
      ports[row['sp_searchd_id']] = int(row['value'].split(':')[-2])
    sql = '''SELECT sp_searchd_id, value FROM sp_searchd_option 
             WHERE sp_option_id = 188'''
    hosts = {}
    for row in cursorfetchall(cursor):
      hosts[row['sp_searchd_id']] = row['value']

    sql = '''SELECT sci.sp_index_id 
             FROM sp_configuration_index sci 
             JOIN sp_configuration_searchd scs 
             ON sci.sp_configuration_id = scs.sp_configuration_id
             WHERE scs.sp_searchd_id = %d'''
    for searchd, port in ports.iteritems():          
      cursor.execute(sql % searchd)
      r = cursorfetchall(cursor)
      for row in r:
        alias = 'sphinx:' + str(row['sp_index_id'])
        connections.databases[alias] = deepcopy(connections.databases['default'])
        connections.databases[alias]['NAME'] = '_'
        connections.databases[alias]['USER'] = ''
        connections.databases[alias]['PASSWORD'] = ''
        host = settings.APPHOST
        if searchd in hosts:
          host = hosts[searchd]
        connections.databases[alias]['HOST'] = host
        connections.databases[alias]['PORT'] = ports[searchd]
    return None


########NEW FILE########
__FILENAME__ = profiler
from generic import redis_client
from generic import settings
from time import time

class Profiler(object):
  '''
  |  Simple Profiling. Stores number of requests and total time for a function.
  |  Used as a view decorator. Can be disabled by setting `PROFILER = False` in *settings.py*.
  '''
  def __init__(self, fn):
    self.fn = fn

  def __call__(self, *args, **kwargs):
    if settings.PROFILER:
      r = redis_client()
      r.incr('hits:' + self.fn.__name__)
      start_time = time()
      response = self.fn(*args, **kwargs)
      r.set('time:' + self.fn.__name__, time() - start_time)
      return response
    else:
      return self.fn(*args, **kwargs)


########NEW FILE########
__FILENAME__ = scripting
from generic import settings
from generic import R
import PyV8 
import json

class Scripting(object):
  def __init__(self, fn):
    self.fn = fn
  
  def __call__(self, *args, **kwargs):
    '''
    |  Javascript Scripting for responses with PyV8.
    |  JS code is passed through the request in the *callback* parameter.
    |  Used as a view decorator. Disable by setting `SCRIPTING = False` in *settings.py*.
    '''
    response = self.fn(*args, **kwargs)
    request = args[0]
    if not settings.SCRIPTING:
      return response
    if hasattr(response, 'content') and response.status_code == 200:
      if 'callback' in request.REQUEST:
        callback = request.REQUEST['callback']
        response_object = json.loads(response.content)
        js_context = PyV8.JSContext({ 'response' : response_object })
        js_context.enter()
        js_context.eval(callback)
        js_context.leave()
        return R(response_object)
    return response
        

########NEW FILE########
__FILENAME__ = sphinxapi
#
# $Id: sphinxapi.py 3701 2013-02-20 18:10:18Z deogar $
#
# Python version of Sphinx searchd client (Python API)
#
# Copyright (c) 2006, Mike Osadnik
# Copyright (c) 2006-2013, Andrew Aksyonoff
# Copyright (c) 2008-2013, Sphinx Technologies Inc
# All rights reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License. You should have
# received a copy of the GPL license along with this program; if you
# did not, you can find it at http://www.gnu.org/
#

import sys
import select
import socket
import re
from struct import *


# known searchd commands
SEARCHD_COMMAND_SEARCH		= 0
SEARCHD_COMMAND_EXCERPT		= 1
SEARCHD_COMMAND_UPDATE		= 2
SEARCHD_COMMAND_KEYWORDS	= 3
SEARCHD_COMMAND_PERSIST		= 4
SEARCHD_COMMAND_STATUS		= 5
SEARCHD_COMMAND_FLUSHATTRS	= 7

# current client-side command implementation versions
VER_COMMAND_SEARCH		= 0x11D
VER_COMMAND_EXCERPT		= 0x104
VER_COMMAND_UPDATE		= 0x103
VER_COMMAND_KEYWORDS	= 0x100
VER_COMMAND_STATUS		= 0x100
VER_COMMAND_FLUSHATTRS	= 0x100

# known searchd status codes
SEARCHD_OK				= 0
SEARCHD_ERROR			= 1
SEARCHD_RETRY			= 2
SEARCHD_WARNING			= 3

# known match modes
SPH_MATCH_ALL			= 0
SPH_MATCH_ANY			= 1
SPH_MATCH_PHRASE		= 2
SPH_MATCH_BOOLEAN		= 3
SPH_MATCH_EXTENDED		= 4
SPH_MATCH_FULLSCAN		= 5
SPH_MATCH_EXTENDED2		= 6

# known ranking modes (extended2 mode only)
SPH_RANK_PROXIMITY_BM25	= 0 # default mode, phrase proximity major factor and BM25 minor one
SPH_RANK_BM25			= 1 # statistical mode, BM25 ranking only (faster but worse quality)
SPH_RANK_NONE			= 2 # no ranking, all matches get a weight of 1
SPH_RANK_WORDCOUNT		= 3 # simple word-count weighting, rank is a weighted sum of per-field keyword occurence counts
SPH_RANK_PROXIMITY		= 4
SPH_RANK_MATCHANY		= 5
SPH_RANK_FIELDMASK		= 6
SPH_RANK_SPH04			= 7
SPH_RANK_EXPR			= 8
SPH_RANK_TOTAL			= 9

# known sort modes
SPH_SORT_RELEVANCE		= 0
SPH_SORT_ATTR_DESC		= 1
SPH_SORT_ATTR_ASC		= 2
SPH_SORT_TIME_SEGMENTS	= 3
SPH_SORT_EXTENDED		= 4
SPH_SORT_EXPR			= 5

# known filter types
SPH_FILTER_VALUES		= 0
SPH_FILTER_RANGE		= 1
SPH_FILTER_FLOATRANGE	= 2

# known attribute types
SPH_ATTR_NONE			= 0
SPH_ATTR_INTEGER		= 1
SPH_ATTR_TIMESTAMP		= 2
SPH_ATTR_ORDINAL		= 3
SPH_ATTR_BOOL			= 4
SPH_ATTR_FLOAT			= 5
SPH_ATTR_BIGINT			= 6
SPH_ATTR_STRING			= 7
SPH_ATTR_FACTORS		= 1001
SPH_ATTR_MULTI			= 0X40000001L
SPH_ATTR_MULTI64		= 0X40000002L

SPH_ATTR_TYPES = (SPH_ATTR_NONE,
				  SPH_ATTR_INTEGER,
				  SPH_ATTR_TIMESTAMP,
				  SPH_ATTR_ORDINAL,
				  SPH_ATTR_BOOL,
				  SPH_ATTR_FLOAT,
				  SPH_ATTR_BIGINT,
				  SPH_ATTR_STRING,
				  SPH_ATTR_MULTI,
				  SPH_ATTR_MULTI64)

# known grouping functions
SPH_GROUPBY_DAY	 		= 0
SPH_GROUPBY_WEEK		= 1
SPH_GROUPBY_MONTH		= 2
SPH_GROUPBY_YEAR		= 3
SPH_GROUPBY_ATTR		= 4
SPH_GROUPBY_ATTRPAIR	= 5


class SphinxClient:
	def __init__ (self):
		"""
		Create a new client object, and fill defaults.
		"""
		self._host			= 'localhost'					# searchd host (default is "localhost")
		self._port			= 9312							# searchd port (default is 9312)
		self._path			= None							# searchd unix-domain socket path
		self._socket		= None
		self._offset		= 0								# how much records to seek from result-set start (default is 0)
		self._limit			= 20							# how much records to return from result-set starting at offset (default is 20)
		self._mode			= SPH_MATCH_ALL					# query matching mode (default is SPH_MATCH_ALL)
		self._weights		= []							# per-field weights (default is 1 for all fields)
		self._sort			= SPH_SORT_RELEVANCE			# match sorting mode (default is SPH_SORT_RELEVANCE)
		self._sortby		= ''							# attribute to sort by (defualt is "")
		self._min_id		= 0								# min ID to match (default is 0)
		self._max_id		= 0								# max ID to match (default is UINT_MAX)
		self._filters		= []							# search filters
		self._groupby		= ''							# group-by attribute name
		self._groupfunc		= SPH_GROUPBY_DAY				# group-by function (to pre-process group-by attribute value with)
		self._groupsort		= '@group desc'					# group-by sorting clause (to sort groups in result set with)
		self._groupdistinct	= ''							# group-by count-distinct attribute
		self._maxmatches	= 1000							# max matches to retrieve
		self._cutoff		= 0								# cutoff to stop searching at
		self._retrycount	= 0								# distributed retry count
		self._retrydelay	= 0								# distributed retry delay
		self._anchor		= {}							# geographical anchor point
		self._indexweights	= {}							# per-index weights
		self._ranker		= SPH_RANK_PROXIMITY_BM25		# ranking mode
		self._rankexpr		= ''							# ranking expression for SPH_RANK_EXPR
		self._maxquerytime	= 0						# max query time, milliseconds (default is 0, do not limit)
		self._timeout = 1.0								# connection timeout
		self._fieldweights	= {}							# per-field-name weights
		self._overrides		= {}							# per-query attribute values overrides
		self._select		= '*'								# select-list (attributes or expressions, with optional aliases)
		self._query_flags	= 0							# per-query various flags
		self._predictedtime = 0							# per-query max_predicted_time
		self._outerorderby = ''							# outer match sort by
		self._outeroffset = 0								# outer offset
		self._outerlimit = 0								# outer limit
		self._hasouter = False							# sub-select enabled
		
		self._error			= ''							# last error message
		self._warning		= ''							# last warning message
		self._reqs			= []							# requests array for multi-query
		
	def __del__ (self):
		if self._socket:
			self._socket.close()


	def GetLastError (self):
		"""
		Get last error message (string).
		"""
		return self._error


	def GetLastWarning (self):
		"""
		Get last warning message (string).
		"""
		return self._warning


	def SetServer (self, host, port = None):
		"""
		Set searchd server host and port.
		"""
		assert(isinstance(host, str))
		if host.startswith('/'):
			self._path = host
			return
		elif host.startswith('unix://'):
			self._path = host[7:]
			return
		self._host = host
		if isinstance(port, int):
			assert(port>0 and port<65536)
			self._port = port
		self._path = None

	def SetConnectTimeout ( self, timeout ):
		"""
		Set connection timeout ( float second )
		"""
		assert (isinstance(timeout, float))
		# set timeout to 0 make connaection non-blocking that is wrong so timeout got clipped to reasonable minimum
		self._timeout = max ( 0.001, timeout )
					
	def _Connect (self):
		"""
		INTERNAL METHOD, DO NOT CALL. Connects to searchd server.
		"""
		if self._socket:
			# we have a socket, but is it still alive?
			sr, sw, _ = select.select ( [self._socket], [self._socket], [], 0 )

			# this is how alive socket should look
			if len(sr)==0 and len(sw)==1:
				return self._socket

			# oops, looks like it was closed, lets reopen
			self._socket.close()
			self._socket = None

		try:
			if self._path:
				af = socket.AF_UNIX
				addr = self._path
				desc = self._path
			else:
				af = socket.AF_INET
				addr = ( self._host, self._port )
				desc = '%s;%s' % addr
			sock = socket.socket ( af, socket.SOCK_STREAM )
			sock.settimeout ( self._timeout )
			sock.connect ( addr )
		except socket.error, msg:
			if sock:
				sock.close()
			self._error = 'connection to %s failed (%s)' % ( desc, msg )
			return

		v = unpack('>L', sock.recv(4))
		if v<1:
			sock.close()
			self._error = 'expected searchd protocol version, got %s' % v
			return

		# all ok, send my version
		sock.send(pack('>L', 1))
		return sock


	def _GetResponse (self, sock, client_ver):
		"""
		INTERNAL METHOD, DO NOT CALL. Gets and checks response packet from searchd server.
		"""
		(status, ver, length) = unpack('>2HL', sock.recv(8))
		response = ''
		left = length
		while left>0:
			chunk = sock.recv(left)
			if chunk:
				response += chunk
				left -= len(chunk)
			else:
				break

		if not self._socket:
			sock.close()

		# check response
		read = len(response)
		if not response or read!=length:
			if length:
				self._error = 'failed to read searchd response (status=%s, ver=%s, len=%s, read=%s)' \
					% (status, ver, length, read)
			else:
				self._error = 'received zero-sized searchd response'
			return None

		# check status
		if status==SEARCHD_WARNING:
			wend = 4 + unpack ( '>L', response[0:4] )[0]
			self._warning = response[4:wend]
			return response[wend:]

		if status==SEARCHD_ERROR:
			self._error = 'searchd error: '+response[4:]
			return None

		if status==SEARCHD_RETRY:
			self._error = 'temporary searchd error: '+response[4:]
			return None

		if status!=SEARCHD_OK:
			self._error = 'unknown status code %d' % status
			return None

		# check version
		if ver<client_ver:
			self._warning = 'searchd command v.%d.%d older than client\'s v.%d.%d, some options might not work' \
				% (ver>>8, ver&0xff, client_ver>>8, client_ver&0xff)

		return response


	def _Send ( self, sock, req ):
		"""
		INTERNAL METHOD, DO NOT CALL. send request to searchd server.
		"""
		total = 0
		while True:
			sent = sock.send ( req[total:] )
			if sent<=0:
				break
				
			total = total + sent
		
		return total
		

	def SetLimits (self, offset, limit, maxmatches=0, cutoff=0):
		"""
		Set offset and count into result set, and optionally set max-matches and cutoff limits.
		"""
		assert ( type(offset) in [int,long] and 0<=offset<16777216 )
		assert ( type(limit) in [int,long] and 0<limit<16777216 )
		assert(maxmatches>=0)
		self._offset = offset
		self._limit = limit
		if maxmatches>0:
			self._maxmatches = maxmatches
		if cutoff>=0:
			self._cutoff = cutoff


	def SetMaxQueryTime (self, maxquerytime):
		"""
		Set maximum query time, in milliseconds, per-index. 0 means 'do not limit'.
		"""
		assert(isinstance(maxquerytime,int) and maxquerytime>0)
		self._maxquerytime = maxquerytime


	def SetMatchMode (self, mode):
		"""
		Set matching mode.
		"""
		assert(mode in [SPH_MATCH_ALL, SPH_MATCH_ANY, SPH_MATCH_PHRASE, SPH_MATCH_BOOLEAN, SPH_MATCH_EXTENDED, SPH_MATCH_FULLSCAN, SPH_MATCH_EXTENDED2])
		self._mode = mode


	def SetRankingMode ( self, ranker, rankexpr='' ):
		"""
		Set ranking mode.
		"""
		assert(ranker>=0 and ranker<SPH_RANK_TOTAL)
		self._ranker = ranker
		self._rankexpr = rankexpr


	def SetSortMode ( self, mode, clause='' ):
		"""
		Set sorting mode.
		"""
		assert ( mode in [SPH_SORT_RELEVANCE, SPH_SORT_ATTR_DESC, SPH_SORT_ATTR_ASC, SPH_SORT_TIME_SEGMENTS, SPH_SORT_EXTENDED, SPH_SORT_EXPR] )
		assert ( isinstance ( clause, str ) )
		self._sort = mode
		self._sortby = clause


	def SetWeights (self, weights): 
		"""
		Set per-field weights.
		WARNING, DEPRECATED; do not use it! use SetFieldWeights() instead
		"""
		assert(isinstance(weights, list))
		for w in weights:
			AssertUInt32 ( w )
		self._weights = weights


	def SetFieldWeights (self, weights):
		"""
		Bind per-field weights by name; expects (name,field_weight) dictionary as argument.
		"""
		assert(isinstance(weights,dict))
		for key,val in weights.items():
			assert(isinstance(key,str))
			AssertUInt32 ( val )
		self._fieldweights = weights


	def SetIndexWeights (self, weights):
		"""
		Bind per-index weights by name; expects (name,index_weight) dictionary as argument.
		"""
		assert(isinstance(weights,dict))
		for key,val in weights.items():
			assert(isinstance(key,str))
			AssertUInt32(val)
		self._indexweights = weights


	def SetIDRange (self, minid, maxid):
		"""
		Set IDs range to match.
		Only match records if document ID is beetwen $min and $max (inclusive).
		"""
		assert(isinstance(minid, (int, long)))
		assert(isinstance(maxid, (int, long)))
		assert(minid<=maxid)
		self._min_id = minid
		self._max_id = maxid


	def SetFilter ( self, attribute, values, exclude=0 ):
		"""
		Set values set filter.
		Only match records where 'attribute' value is in given 'values' set.
		"""
		assert(isinstance(attribute, str))
		assert iter(values)

		for value in values:
			AssertInt32 ( value )

		self._filters.append ( { 'type':SPH_FILTER_VALUES, 'attr':attribute, 'exclude':exclude, 'values':values } )


	def SetFilterRange (self, attribute, min_, max_, exclude=0 ):
		"""
		Set range filter.
		Only match records if 'attribute' value is beetwen 'min_' and 'max_' (inclusive).
		"""
		assert(isinstance(attribute, str))
		AssertInt32(min_)
		AssertInt32(max_)
		assert(min_<=max_)

		self._filters.append ( { 'type':SPH_FILTER_RANGE, 'attr':attribute, 'exclude':exclude, 'min':min_, 'max':max_ } )


	def SetFilterFloatRange (self, attribute, min_, max_, exclude=0 ):
		assert(isinstance(attribute,str))
		assert(isinstance(min_,float))
		assert(isinstance(max_,float))
		assert(min_ <= max_)
		self._filters.append ( {'type':SPH_FILTER_FLOATRANGE, 'attr':attribute, 'exclude':exclude, 'min':min_, 'max':max_} ) 


	def SetGeoAnchor (self, attrlat, attrlong, latitude, longitude):
		assert(isinstance(attrlat,str))
		assert(isinstance(attrlong,str))
		assert(isinstance(latitude,float))
		assert(isinstance(longitude,float))
		self._anchor['attrlat'] = attrlat
		self._anchor['attrlong'] = attrlong
		self._anchor['lat'] = latitude
		self._anchor['long'] = longitude


	def SetGroupBy ( self, attribute, func, groupsort='@group desc' ):
		"""
		Set grouping attribute and function.
		"""
		assert(isinstance(attribute, str))
		assert(func in [SPH_GROUPBY_DAY, SPH_GROUPBY_WEEK, SPH_GROUPBY_MONTH, SPH_GROUPBY_YEAR, SPH_GROUPBY_ATTR, SPH_GROUPBY_ATTRPAIR] )
		assert(isinstance(groupsort, str))

		self._groupby = attribute
		self._groupfunc = func
		self._groupsort = groupsort


	def SetGroupDistinct (self, attribute):
		assert(isinstance(attribute,str))
		self._groupdistinct = attribute


	def SetRetries (self, count, delay=0):
		assert(isinstance(count,int) and count>=0)
		assert(isinstance(delay,int) and delay>=0)
		self._retrycount = count
		self._retrydelay = delay


	def SetOverride (self, name, type, values):
		assert(isinstance(name, str))
		assert(type in SPH_ATTR_TYPES)
		assert(isinstance(values, dict))

		self._overrides[name] = {'name': name, 'type': type, 'values': values}

	def SetSelect (self, select):
		assert(isinstance(select, str))
		self._select = select

	def SetQueryFlag ( self, name, value ):
		known_names = [ "reverse_scan", "sort_method", "max_predicted_time", "boolean_simplify", "idf" ]
		flags = { "reverse_scan":[0, 1], "sort_method":["pq", "kbuffer"],"max_predicted_time":[0], "boolean_simplify":[True, False], "idf":["normalized", "plain"] }
		assert ( name in known_names )
		assert ( value in flags[name] or ( name=="max_predicted_time" and isinstance(value, (int, long)) and value>=0))
		
		if name=="reverse_scan":
			self._query_flags = SetBit ( self._query_flags, 0, value==1 )
		if name=="sort_method":
			self._query_flags = SetBit ( self._query_flags, 1, value=="kbuffer" )
		if name=="max_predicted_time":
			self._query_flags = SetBit ( self._query_flags, 2, value>0 )
			self._predictedtime = int(value)
		if name=="boolean_simplify":
			self._query_flags= SetBit ( self._query_flags, 3, value )
		if name=="idf":
			self._query_flags = SetBit ( self._query_flags, 4, value=="plain" )

	def SetOuterSelect ( self, orderby, offset, limit ):
		assert(isinstance(orderby, str))
		assert(isinstance(offset, (int, long)))
		assert(isinstance(limit, (int, long)))
		assert ( offset>=0 )
		assert ( limit>0 )

		self._outerorderby = orderby
		self._outeroffset = offset
		self._outerlimit = limit
		self._hasouter = True
			
	def ResetOverrides (self):
		self._overrides = {}


	def ResetFilters (self):
		"""
		Clear all filters (for multi-queries).
		"""
		self._filters = []
		self._anchor = {}


	def ResetGroupBy (self):
		"""
		Clear groupby settings (for multi-queries).
		"""
		self._groupby = ''
		self._groupfunc = SPH_GROUPBY_DAY
		self._groupsort = '@group desc'
		self._groupdistinct = ''

	def ResetQueryFlag (self):
		self._query_flags = 0
		self._predictedtime = 0
		
	def ResetOuterSelect (self):
		self._outerorderby = ''
		self._outeroffset = 0
		self._outerlimit = 0
		self._hasouter = False

	def Query (self, query, index='*', comment=''):
		"""
		Connect to searchd server and run given search query.
		Returns None on failure; result set hash on success (see documentation for details).
		"""
		assert(len(self._reqs)==0)
		self.AddQuery(query,index,comment)
		results = self.RunQueries()
		self._reqs = [] # we won't re-run erroneous batch

		if not results or len(results)==0:
			return None
		self._error = results[0]['error']
		self._warning = results[0]['warning']
		if results[0]['status'] == SEARCHD_ERROR:
			return None
		return results[0]


	def AddQuery (self, query, index='*', comment=''):
		"""
		Add query to batch.
		"""
		# build request
		req = []
		req.append(pack('>5L', self._query_flags, self._offset, self._limit, self._mode, self._ranker))
		if self._ranker==SPH_RANK_EXPR:
			req.append(pack('>L', len(self._rankexpr)))
			req.append(self._rankexpr)
		req.append(pack('>L', self._sort))
		req.append(pack('>L', len(self._sortby)))
		req.append(self._sortby)

		if isinstance(query,unicode):
			query = query.encode('utf-8')
		assert(isinstance(query,str))

		req.append(pack('>L', len(query)))
		req.append(query)

		req.append(pack('>L', len(self._weights)))
		for w in self._weights:
			req.append(pack('>L', w))
		assert(isinstance(index,str))
		req.append(pack('>L', len(index)))
		req.append(index)
		req.append(pack('>L',1)) # id64 range marker
		req.append(pack('>Q', self._min_id))
		req.append(pack('>Q', self._max_id))
		
		# filters
		req.append ( pack ( '>L', len(self._filters) ) )
		for f in self._filters:
			req.append ( pack ( '>L', len(f['attr'])) + f['attr'])
			filtertype = f['type']
			req.append ( pack ( '>L', filtertype))
			if filtertype == SPH_FILTER_VALUES:
				req.append ( pack ('>L', len(f['values'])))
				for val in f['values']:
					req.append ( pack ('>q', val))
			elif filtertype == SPH_FILTER_RANGE:
				req.append ( pack ('>2q', f['min'], f['max']))
			elif filtertype == SPH_FILTER_FLOATRANGE:
				req.append ( pack ('>2f', f['min'], f['max']))
			req.append ( pack ( '>L', f['exclude'] ) )

		# group-by, max-matches, group-sort
		req.append ( pack ( '>2L', self._groupfunc, len(self._groupby) ) )
		req.append ( self._groupby )
		req.append ( pack ( '>2L', self._maxmatches, len(self._groupsort) ) )
		req.append ( self._groupsort )
		req.append ( pack ( '>LLL', self._cutoff, self._retrycount, self._retrydelay)) 
		req.append ( pack ( '>L', len(self._groupdistinct)))
		req.append ( self._groupdistinct)

		# anchor point
		if len(self._anchor) == 0:
			req.append ( pack ('>L', 0))
		else:
			attrlat, attrlong = self._anchor['attrlat'], self._anchor['attrlong']
			latitude, longitude = self._anchor['lat'], self._anchor['long']
			req.append ( pack ('>L', 1))
			req.append ( pack ('>L', len(attrlat)) + attrlat)
			req.append ( pack ('>L', len(attrlong)) + attrlong)
			req.append ( pack ('>f', latitude) + pack ('>f', longitude))

		# per-index weights
		req.append ( pack ('>L',len(self._indexweights)))
		for indx,weight in self._indexweights.items():
			req.append ( pack ('>L',len(indx)) + indx + pack ('>L',weight))

		# max query time
		req.append ( pack ('>L', self._maxquerytime) ) 

		# per-field weights
		req.append ( pack ('>L',len(self._fieldweights) ) )
		for field,weight in self._fieldweights.items():
			req.append ( pack ('>L',len(field)) + field + pack ('>L',weight) )

		# comment
		comment = str(comment)
		req.append ( pack('>L',len(comment)) + comment )

		# attribute overrides
		req.append ( pack('>L', len(self._overrides)) )
		for v in self._overrides.values():
			req.extend ( ( pack('>L', len(v['name'])), v['name'] ) )
			req.append ( pack('>LL', v['type'], len(v['values'])) )
			for id, value in v['values'].iteritems():
				req.append ( pack('>Q', id) )
				if v['type'] == SPH_ATTR_FLOAT:
					req.append ( pack('>f', value) )
				elif v['type'] == SPH_ATTR_BIGINT:
					req.append ( pack('>q', value) )
				else:
					req.append ( pack('>l', value) )

		# select-list
		req.append ( pack('>L', len(self._select)) )
		req.append ( self._select )
		if self._predictedtime>0:
			req.append ( pack('>L', self._predictedtime ) )

		# outer
		req.append ( pack('>L',len(self._outerorderby)) + self._outerorderby )
		req.append ( pack ( '>2L', self._outeroffset, self._outerlimit ) )
		if self._hasouter:
			req.append ( pack('>L', 1) )
		else:
			req.append ( pack('>L', 0) )
			
		# send query, get response
		req = ''.join(req)

		self._reqs.append(req)
		return


	def RunQueries (self):
		"""
		Run queries batch.
		Returns None on network IO failure; or an array of result set hashes on success.
		"""
		if len(self._reqs)==0:
			self._error = 'no queries defined, issue AddQuery() first'
			return None

		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(self._reqs)
		length = len(req)+8
		req = pack('>HHLLL', SEARCHD_COMMAND_SEARCH, VER_COMMAND_SEARCH, length, 0, len(self._reqs))+req
		self._Send ( sock, req )

		response = self._GetResponse(sock, VER_COMMAND_SEARCH)
		if not response:
			return None

		nreqs = len(self._reqs)

		# parse response
		max_ = len(response)
		p = 0

		results = []
		for i in range(0,nreqs,1):
			result = {}
			results.append(result)

			result['error'] = ''
			result['warning'] = ''
			status = unpack('>L', response[p:p+4])[0]
			p += 4
			result['status'] = status
			if status != SEARCHD_OK:
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				message = response[p:p+length]
				p += length

				if status == SEARCHD_WARNING:
					result['warning'] = message
				else:
					result['error'] = message
					continue

			# read schema
			fields = []
			attrs = []

			nfields = unpack('>L', response[p:p+4])[0]
			p += 4
			while nfields>0 and p<max_:
				nfields -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				fields.append(response[p:p+length])
				p += length

			result['fields'] = fields

			nattrs = unpack('>L', response[p:p+4])[0]
			p += 4
			while nattrs>0 and p<max_:
				nattrs -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				attr = response[p:p+length]
				p += length
				type_ = unpack('>L', response[p:p+4])[0]
				p += 4
				attrs.append([attr,type_])

			result['attrs'] = attrs

			# read match count
			count = unpack('>L', response[p:p+4])[0]
			p += 4
			id64 = unpack('>L', response[p:p+4])[0]
			p += 4
		
			# read matches
			result['matches'] = []
			while count>0 and p<max_:
				count -= 1
				if id64:
					doc, weight = unpack('>QL', response[p:p+12])
					p += 12
				else:
					doc, weight = unpack('>2L', response[p:p+8])
					p += 8

				match = { 'id':doc, 'weight':weight, 'attrs':{} }
				for i in range(len(attrs)):
					if attrs[i][1] == SPH_ATTR_FLOAT:
						match['attrs'][attrs[i][0]] = unpack('>f', response[p:p+4])[0]
					elif attrs[i][1] == SPH_ATTR_BIGINT:
						match['attrs'][attrs[i][0]] = unpack('>q', response[p:p+8])[0]
						p += 4
					elif attrs[i][1] == SPH_ATTR_STRING:
						slen = unpack('>L', response[p:p+4])[0]
						p += 4
						match['attrs'][attrs[i][0]] = ''
						if slen>0:
							match['attrs'][attrs[i][0]] = response[p:p+slen]
						p += slen-4
					elif attrs[i][1] == SPH_ATTR_FACTORS:
						slen = unpack('>L', response[p:p+4])[0]
						p += 4
						match['attrs'][attrs[i][0]] = ''
						if slen>0:
							match['attrs'][attrs[i][0]] = response[p:p+slen-4]
							p += slen-4
						p -= 4
					elif attrs[i][1] == SPH_ATTR_MULTI:
						match['attrs'][attrs[i][0]] = []
						nvals = unpack('>L', response[p:p+4])[0]
						p += 4
						for n in range(0,nvals,1):
							match['attrs'][attrs[i][0]].append(unpack('>L', response[p:p+4])[0])
							p += 4
						p -= 4
					elif attrs[i][1] == SPH_ATTR_MULTI64:
						match['attrs'][attrs[i][0]] = []
						nvals = unpack('>L', response[p:p+4])[0]
						nvals = nvals/2
						p += 4
						for n in range(0,nvals,1):
							match['attrs'][attrs[i][0]].append(unpack('>q', response[p:p+8])[0])
							p += 8
						p -= 4
					else:
						match['attrs'][attrs[i][0]] = unpack('>L', response[p:p+4])[0]
					p += 4

				result['matches'].append ( match )

			result['total'], result['total_found'], result['time'], words = unpack('>4L', response[p:p+16])

			result['time'] = '%.3f' % (result['time']/1000.0)
			p += 16

			result['words'] = []
			while words>0:
				words -= 1
				length = unpack('>L', response[p:p+4])[0]
				p += 4
				word = response[p:p+length]
				p += length
				docs, hits = unpack('>2L', response[p:p+8])
				p += 8

				result['words'].append({'word':word, 'docs':docs, 'hits':hits})
		
		self._reqs = []
		return results
	

	def BuildExcerpts (self, docs, index, words, opts=None):
		"""
		Connect to searchd server and generate exceprts from given documents.
		"""
		if not opts:
			opts = {}
		if isinstance(words,unicode):
			words = words.encode('utf-8')

		assert(isinstance(docs, list))
		assert(isinstance(index, str))
		assert(isinstance(words, str))
		assert(isinstance(opts, dict))

		sock = self._Connect()

		if not sock:
			return None

		# fixup options
		opts.setdefault('before_match', '<b>')
		opts.setdefault('after_match', '</b>')
		opts.setdefault('chunk_separator', ' ... ')
		opts.setdefault('html_strip_mode', 'index')
		opts.setdefault('limit', 256)
		opts.setdefault('limit_passages', 0)
		opts.setdefault('limit_words', 0)
		opts.setdefault('around', 5)
		opts.setdefault('start_passage_id', 1)
		opts.setdefault('passage_boundary', 'none')

		# build request
		# v.1.0 req

		flags = 1 # (remove spaces)
		if opts.get('exact_phrase'):	flags |= 2
		if opts.get('single_passage'):	flags |= 4
		if opts.get('use_boundaries'):	flags |= 8
		if opts.get('weight_order'):	flags |= 16
		if opts.get('query_mode'):		flags |= 32
		if opts.get('force_all_words'):	flags |= 64
		if opts.get('load_files'):		flags |= 128
		if opts.get('allow_empty'):		flags |= 256
		if opts.get('emit_zones'):		flags |= 512
		if opts.get('load_files_scattered'):	flags |= 1024
		
		# mode=0, flags
		req = [pack('>2L', 0, flags)]

		# req index
		req.append(pack('>L', len(index)))
		req.append(index)

		# req words
		req.append(pack('>L', len(words)))
		req.append(words)

		# options
		req.append(pack('>L', len(opts['before_match'])))
		req.append(opts['before_match'])

		req.append(pack('>L', len(opts['after_match'])))
		req.append(opts['after_match'])

		req.append(pack('>L', len(opts['chunk_separator'])))
		req.append(opts['chunk_separator'])

		req.append(pack('>L', int(opts['limit'])))
		req.append(pack('>L', int(opts['around'])))
		
		req.append(pack('>L', int(opts['limit_passages'])))
		req.append(pack('>L', int(opts['limit_words'])))
		req.append(pack('>L', int(opts['start_passage_id'])))
		req.append(pack('>L', len(opts['html_strip_mode'])))
		req.append((opts['html_strip_mode']))
		req.append(pack('>L', len(opts['passage_boundary'])))
		req.append((opts['passage_boundary']))

		# documents
		req.append(pack('>L', len(docs)))
		for doc in docs:
			if isinstance(doc,unicode):
				doc = doc.encode('utf-8')
			assert(isinstance(doc, str))
			req.append(pack('>L', len(doc)))
			req.append(doc)

		req = ''.join(req)

		# send query, get response
		length = len(req)

		# add header
		req = pack('>2HL', SEARCHD_COMMAND_EXCERPT, VER_COMMAND_EXCERPT, length)+req
		self._Send ( sock, req )

		response = self._GetResponse(sock, VER_COMMAND_EXCERPT )
		if not response:
			return []

		# parse response
		pos = 0
		res = []
		rlen = len(response)

		for i in range(len(docs)):
			length = unpack('>L', response[pos:pos+4])[0]
			pos += 4

			if pos+length > rlen:
				self._error = 'incomplete reply'
				return []

			res.append(response[pos:pos+length])
			pos += length

		return res


	def UpdateAttributes ( self, index, attrs, values, mva=False, ignorenonexistent=False ):
		"""
		Update given attribute values on given documents in given indexes.
		Returns amount of updated documents (0 or more) on success, or -1 on failure.

		'attrs' must be a list of strings.
		'values' must be a dict with int key (document ID) and list of int values (new attribute values).
		optional boolean parameter 'mva' points that there is update of MVA attributes.
		In this case the 'values' must be a dict with int key (document ID) and list of lists of int values
		(new MVA attribute values).
		Optional boolean parameter 'ignorenonexistent' points that the update will silently ignore any warnings about
		trying to update a column which is not exists in current index schema.

		Example:
			res = cl.UpdateAttributes ( 'test1', [ 'group_id', 'date_added' ], { 2:[123,1000000000], 4:[456,1234567890] } )
		"""
		assert ( isinstance ( index, str ) )
		assert ( isinstance ( attrs, list ) )
		assert ( isinstance ( values, dict ) )
		for attr in attrs:
			assert ( isinstance ( attr, str ) )
		for docid, entry in values.items():
			AssertUInt32(docid)
			assert ( isinstance ( entry, list ) )
			assert ( len(attrs)==len(entry) )
			for val in entry:
				if mva:
					assert ( isinstance ( val, list ) )
					for vals in val:
						AssertInt32(vals)
				else:
					AssertInt32(val)

		# build request
		req = [ pack('>L',len(index)), index ]

		req.append ( pack('>L',len(attrs)) )
		ignore_absent = 0
		if ignorenonexistent: ignore_absent = 1
		req.append ( pack('>L', ignore_absent ) )
		mva_attr = 0
		if mva: mva_attr = 1
		for attr in attrs:
			req.append ( pack('>L',len(attr)) + attr )
			req.append ( pack('>L', mva_attr ) )

		req.append ( pack('>L',len(values)) )
		for docid, entry in values.items():
			req.append ( pack('>Q',docid) )
			for val in entry:
				val_len = val
				if mva: val_len = len ( val )
				req.append ( pack('>L',val_len ) )
				if mva:
					for vals in val:
						req.append ( pack ('>L',vals) )

		# connect, send query, get response
		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(req)
		length = len(req)
		req = pack ( '>2HL', SEARCHD_COMMAND_UPDATE, VER_COMMAND_UPDATE, length ) + req
		self._Send ( sock, req )

		response = self._GetResponse ( sock, VER_COMMAND_UPDATE )
		if not response:
			return -1

		# parse response
		updated = unpack ( '>L', response[0:4] )[0]
		return updated


	def BuildKeywords ( self, query, index, hits ):
		"""
		Connect to searchd server, and generate keywords list for a given query.
		Returns None on failure, or a list of keywords on success.
		"""
		assert ( isinstance ( query, str ) )
		assert ( isinstance ( index, str ) )
		assert ( isinstance ( hits, int ) )

		# build request
		req = [ pack ( '>L', len(query) ) + query ]
		req.append ( pack ( '>L', len(index) ) + index )
		req.append ( pack ( '>L', hits ) )

		# connect, send query, get response
		sock = self._Connect()
		if not sock:
			return None

		req = ''.join(req)
		length = len(req)
		req = pack ( '>2HL', SEARCHD_COMMAND_KEYWORDS, VER_COMMAND_KEYWORDS, length ) + req
		self._Send ( sock, req )

		response = self._GetResponse ( sock, VER_COMMAND_KEYWORDS )
		if not response:
			return None

		# parse response
		res = []

		nwords = unpack ( '>L', response[0:4] )[0]
		p = 4
		max_ = len(response)

		while nwords>0 and p<max_:
			nwords -= 1

			length = unpack ( '>L', response[p:p+4] )[0]
			p += 4
			tokenized = response[p:p+length]
			p += length

			length = unpack ( '>L', response[p:p+4] )[0]
			p += 4
			normalized = response[p:p+length]
			p += length

			entry = { 'tokenized':tokenized, 'normalized':normalized }
			if hits:
				entry['docs'], entry['hits'] = unpack ( '>2L', response[p:p+8] )
				p += 8

			res.append ( entry )

		if nwords>0 or p>max_:
			self._error = 'incomplete reply'
			return None

		return res

	def Status ( self ):
		"""
		Get the status
		"""

		# connect, send query, get response
		sock = self._Connect()
		if not sock:
			return None

		req = pack ( '>2HLL', SEARCHD_COMMAND_STATUS, VER_COMMAND_STATUS, 4, 1 )
		self._Send ( sock, req )

		response = self._GetResponse ( sock, VER_COMMAND_STATUS )
		if not response:
			return None

		# parse response
		res = []

		p = 8
		max_ = len(response)

		while p<max_:
			length = unpack ( '>L', response[p:p+4] )[0]
			k = response[p+4:p+length+4]
			p += 4+length
			length = unpack ( '>L', response[p:p+4] )[0]
			v = response[p+4:p+length+4]
			p += 4+length
			res += [[k, v]]

		return res

	### persistent connections

	def Open(self):
		if self._socket:
			self._error = 'already connected'
			return None
		
		server = self._Connect()
		if not server:
			return None

		# command, command version = 0, body length = 4, body = 1
		request = pack ( '>hhII', SEARCHD_COMMAND_PERSIST, 0, 4, 1 )
		self._Send ( server, request )
		
		self._socket = server
		return True

	def Close(self):
		if not self._socket:
			self._error = 'not connected'
			return
		self._socket.close()
		self._socket = None
	
	def EscapeString(self, string):
		return re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", string)


	def FlushAttributes(self):
		sock = self._Connect()
		if not sock:
			return -1

		request = pack ( '>hhI', SEARCHD_COMMAND_FLUSHATTRS, VER_COMMAND_FLUSHATTRS, 0 ) # cmd, ver, bodylen
		self._Send ( sock, request )

		response = self._GetResponse ( sock, VER_COMMAND_FLUSHATTRS )
		if not response or len(response)!=4:
			self._error = 'unexpected response length'
			return -1

		tag = unpack ( '>L', response[0:4] )[0]
		return tag

def AssertInt32 ( value ):
	assert(isinstance(value, (int, long)))
	assert(value>=-2**32-1 and value<=2**32-1)

def AssertUInt32 ( value ):
	assert(isinstance(value, (int, long)))
	assert(value>=0 and value<=2**32-1)

def SetBit ( flag, bit, on ):
	if on:
		flag += ( 1<<bit )
	else:
		reset = 255 ^ ( 1<<bit )
		flag = flag & reset

	return flag

	
#
# $Id: sphinxapi.py 3701 2013-02-20 18:10:18Z deogar $
#

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Constants(models.Model):
  '''
  Table constants: various constants (ENUM replacement).
  '''
  table_name = models.CharField()
  table_field = models.CharField()
  constant_name = models.CharField()
  constant_value = models.CharField()
  constant_type = models.CharField()

  def save(self, *args, **kwargs):
    raise NotImplementedError("constants table cannot be edited")
  
  class Meta:
    db_table = "constants"
          
class Configuration(models.Model):
  '''
  Table sp_configurations: stores Sphinx Configurations.
  '''
  name = models.CharField(max_length = 50)
  hash = models.CharField(max_length = 32)
  description = models.TextField()
  is_active = models.PositiveSmallIntegerField(default = 1)
  date_inserted = models.DateTimeField(auto_now_add = True)

  class Meta:
    db_table = "sp_configurations"

class Option(models.Model):
  '''
  Table sp_options: stores available options.
  '''
  name = models.CharField(max_length = 30)
  description = models.TextField()
  possible_values = models.TextField()
  section = models.PositiveSmallIntegerField()

  class Meta:
    db_table = "sp_options"    

class Index(models.Model):
  '''
  Table sp_indexes: stores indexes.
  '''
  name = models.CharField(max_length = 30)
  index_type = models.PositiveSmallIntegerField(default = 1) # 1 -> realtime, 2 -> distributed
  is_active = models.PositiveSmallIntegerField(default = 1)
  parent_id = models.PositiveIntegerField(default = 0)
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_indexes"        

class ConfigurationIndex(models.Model):
  '''
  Table *sp_configuration_index*: stores the connections between configurations and indexes.
  '''
  is_active = models.PositiveSmallIntegerField(default = 1)
  sp_index_id = models.PositiveIntegerField()
  sp_configuration_id = models.PositiveIntegerField()
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_configuration_index"        

class IndexOption(models.Model):
  '''
  Table *sp_index_option*: stores the connections between options and indexes.
  '''
  sp_index_id = models.PositiveIntegerField()
  sp_option_id = models.PositiveIntegerField()
  value = models.TextField()
  value_hash = models.CharField(max_length = 32)
  is_active = models.PositiveSmallIntegerField()
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_index_option"
 
class Sources(models.Model):
  '''
  Table *sp_sources*: stores datasource entities.
  '''
  name = models.CharField(max_length = 30)
  is_active = models.PositiveSmallIntegerField(default = 1)
  parent_id = models.PositiveIntegerField(default = 0)
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_sources"

class Searchd(models.Model):
  '''
  Table *sp_searchd*: stores searchd entities.
  '''
  name = models.CharField(max_length = 30)
  is_active = models.PositiveSmallIntegerField(default = 1)
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_searchd"
 
class ConfigurationSource(models.Model):
  '''
  Table *sp_configuration_source*: stores the connections between configurations and datasource entities.
  '''
  sp_configuration_id = models.PositiveIntegerField()
  sp_source_id = models.PositiveIntegerField()
  class Meta:
    db_table = "sp_configuration_source"

class ConfigurationSearchd(models.Model):
  '''
  Table *sp_configuration_searchd*: stores the connections between configurations and searchd entities.
  '''
  sp_configuration_id = models.PositiveIntegerField()
  sp_searchd_id = models.PositiveIntegerField()

  class Meta:
    db_table = "sp_configuration_searchd"

class SourceOption(models.Model):
  '''
  Table *sp_source_option*: stores the connections between datasource entities and options.
  '''
  sp_source_id = models.PositiveIntegerField()
  sp_option_id = models.PositiveIntegerField()
  value = models.TextField()
  value_hash = models.CharField(max_length = 32)
  is_active = models.PositiveSmallIntegerField()
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_source_option"
 
class SearchdOption(models.Model):
  '''
  Table *sp_searchd_option*: stores the connections between searchd entities and options.
  '''
  sp_searchd_id = models.PositiveIntegerField()
  sp_option_id = models.PositiveIntegerField()
  value = models.TextField()
  value_hash = models.CharField(max_length = 32)
  is_active = models.PositiveSmallIntegerField()
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)
  date_modified = models.DateTimeField(auto_now = True, auto_now_add = True)

  class Meta:
    db_table = "sp_searchd_option"

class Authentication(models.Model):
  '''
  Table *authentication*: stores consumer key/secret pairs for authenticated requests.
  '''
  consumer_key = models.CharField(primary_key = True, max_length = 8)
  secret = models.CharField(max_length = 16)
  date_inserted = models.DateTimeField(auto_now = False, auto_now_add = True)

  class Meta:
    db_table = "authentication"

########NEW FILE########
__FILENAME__ = settings
# Django settings for techu project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CONN_MAX_AGE = None
ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'techu',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '3306',                      # Set to empty string for default.
    },
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Athens'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/admin/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    '/home/techu-search-server/techu/admin/static/'
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!3klksdfo$*#@)kdsd;lds;0bfn&!jd$rof8aq_!n76$@&-8vcwrc-'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'techu.libraries.middleware.ExceptionLoggingMiddleware',
    'django.middleware.common.CommonMiddleware',
    'techu.libraries.middleware.ConnectionMiddleware',
    )

ROOT_URLCONF = 'techu.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'techu.wsgi.application'

TEMPLATE_DIRS = (
    '/home/techu-search-server/techu/admin/templates/'
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_graceful',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


import os, sys
''' 
    Techu Project Settings 
    Version 0.1beta
'''
PROFILER = True
SCRIPTING = True
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PROJECT_ROOT)
TECHU_COUNTER = '84920c64c98c9cf2a7ab4af756c84b33'
MAX_RETRIES = 10
SEARCH_FAIL_ERROR = 1
SEARCH_FAIL_WARNING = 2
SEARCH_FAILURE_LEVEL = SEARCH_FAIL_WARNING
SEARCH_CACHE = True
EXCERPTS_CACHE = True
EXCERPTS_CACHE_EXPIRE = 10 # Cache expiration in seconds
APPHOST = 'techu'
CACHE_LOCK_TIMEOUT = 10
SEARCH_CACHE_EXPIRE = 120.
''' Redis '''
REDIS_PORT = 6379
REDIS_HOST = 'localhost'
REDIS_PASSWORD = None
''' Graceful restart (thanks to https://github.com/andreiko/django_graceful) '''
GRACEFUL_STATEDIR = '/home/techu-search-server/run/'
SPHINX_CONFIGURATION_DIR = '/home/techu-search-server/techu/sphinx.conf'
FUNCTION_CACHE = True

########NEW FILE########
__FILENAME__ = caching
#!/usr/bin/python
import sys
import unittest
import random
sys.path.append('..')
from libraries import caching
import time

class TestCaching(unittest.TestCase):

  def setUp(self):
    self.cache = caching.Cache()
    self.prefix = str(random.randint(1, 10**6)) + '-'

  def _testSet(self):
    ''' Set some keys & values '''
    self.assertTrue(self.cache.set(self.prefix + 'key-1', 'value-1'))
    self.assertTrue(self.cache.set(self.prefix + 'key-2', { 'a' : 1, 'b' : 2 }))

  def _testGet(self):
    value_1 = self.cache.get(self.prefix + 'key-1')
    value_2 = self.cache.get(self.prefix + 'key-2')
    self.assertEqual(value_1, 'value-1')
    self.assertEqual(value_2, {'a' : 1, 'b' : 2})
    
  def _testDelete(self):
    self.cache.delete(self.prefix + 'key-1', 1000)
    value_1 = self.cache.get(self.prefix + 'key-1')
    ''' check that key still exists '''
    self.assertEqual(value_1, 'value-1')
    ''' check that it is deleted after 1000 msec '''
    time.sleep(1.001)
    self.assertEqual(self.cache.get(self.prefix + 'key-1'), None)
    ''' delete key-2 immediately '''
    self.cache.delete(self.prefix + 'key-2', 0)
    self.assertEqual(self.cache.get(self.prefix + 'key-2'), None)

  def testSetGetDelete(self):
    self._testSet()
    self._testGet()
    self._testDelete()


if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(TestCaching)
  unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = generic
#!/usr/bin/python
import sys
import unittest
sys.path.append('..')
from libraries.generic import *

class TestGeneric(unittest.TestCase):

  def testRedisConnection(self):
    self.assertTrue(isinstance(redis_client(), redis.StrictRedis))

  def testRegexCheck(self):
    self.assertTrue(regex_check('techu_123'))

  def testIdentq(self):
    self.assertEqual(identq('table`1'), '`table1`')
  
if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(TestGeneric)
  unittest.TextTestRunner(verbosity=2).run(suite)    

########NEW FILE########
__FILENAME__ = responses
#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys, codecs
import unittest
sys.path.append('..')
import requests
import re, json

class TestResponses(unittest.TestCase):
  BaseURL = 'http://techu:81'

  def _status(self, r):
    self.assertEqual(r.status_code, 200)

  def setUp(self):
    f = codecs.open('./responses.txt', encoding = 'utf-8', mode = 'r')
    self.responses = [ response.replace("\\\n", "\n")  for response in f.readlines() ]
    f.close()

  def testHome(self):
    r = requests.get(self.BaseURL)
    self._status(r)

  def testIndexOptions(self):
    data = { "path" : "/usr/local/sphinx/data/so_posts_rt" }
    data = { "data" : json.dumps(data) }
    print data
    print self.BaseURL + '/option/index/28/'
    r = requests.post(self.BaseURL + '/option/index/28/', data = data)
    self._status(r)


  def testGenerateConfiguration(self):
    r = requests.get(self.BaseURL + '/generate/25/')
    self._status(r)
    self.assertEqual(json.loads(r.content), json.loads(self.responses[0].strip()))

if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(TestResponses)
  unittest.TextTestRunner(verbosity=2).run(suite)    

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('techu.views',
  url(r'^configuration[/]*$', 'configuration', name = 'configuration_insert'),
  url(r'^configuration/list[/]*$', 'configuration_list', name = 'configuration_list'),
  url(r'^configuration/(?P<configuration_id>\d+)[/]*$', 'configuration', name = 'configuration'),
  url(r'^searchd[/]*(?P<searchd_id>\d+)[/]*$', 'searchd', name = 'searchd'),
  url(r'^searchd[/]*$', 'searchd', name = 'searchd'),
  url(r'^option/list[/]*$', 'option_list', name = 'option_list'),
  url(r'^option/(?P<section>[a-z]+)/(?P<section_instance_id>\d+)[/]*$', 'option', name = 'option'),
  url(r'^index[/]*$', 'index', name = 'index_insert'),
  url(r'^index/(?P<index_id>\d+)[/]*$', 'index', name = 'index'),
  url(r'^index/list[/]*$', 'index_list', name = 'index_list'),
  url(r'^indexer/(?P<action>[a-z]+)/(?P<index_id>\d+)[/]*$', 'indexer', name = 'indexer'),
  url(r'^indexer/(?P<action>[a-z]+)/(?P<index_id>\d+)[/]*(?P<doc_id>\d+)[/]*$', 'indexer', name = 'indexer'),
  url(r'^search/(?P<index_id>\d+)[/]*$', 'search', name = 'search'),
  url(r'^excerpts/(?P<index_id>\d+)[/]*$', 'excerpts', name = 'excerpts'),
  url(r'^generate/(?P<configuration_id>\d+)[/]*$', 'generate', name = 'generate'),
  url(r'^batch/(?P<action>[a-z]+)/(?P<index_id>\d+)[/]*$', 'batch_indexer', name = 'batch_indexer'),
  url(r'^[/]*$', 'home', name = 'home'),
)

urlpatterns += patterns('techu.admin.views',
  url(r'^admin[/]*$', 'home', name = 'admin_home'),
  url(r'^admin/api-playground/(?P<request_type>[a-z]+)[/]*$', 'api_playground', name = 'admin_api_playground'),
  url(r'^admin/api-playground[/]*$', 'api_playground', name = 'admin_api_playground'),
  url(r'^admin/api[/]*$', 'fetch_api', name = 'fetch_api'),
  url(r'^admin/highlighter[/]*$', 'highlighter', name = 'highlighter'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os, sys, time
import json, marshal
from hashlib import md5
import settings 
from django.db import connections, IntegrityError, DatabaseError
from libraries.generic import *
from techu.models import *
from libraries.sphinxapi import *
from libraries.caching import Cache, FunctionCache
from libraries.profiler import Profiler
from libraries.scripting import Scripting

@Scripting
@Profiler
def home(request):
  '''
  Home Page
  '''
  return R({ "Greetings-From" : "Techu Indexing Server" }, request)

@FunctionCache
def constants():
  '''
  |  Read all constants values from the database and associate via a 2-level dictionary
  |  1st level contains *name_of_table_name_of_field* keys and the 2nd level contains the constant value.
  '''
  constant_list = Constants.objects.all()  
  constants_hash = {}
  for c in constant_list:
    constant_key = c.table_name + '_' + c.table_field
    if not constant_key in constants_hash:
      constants_hash[constant_key] = {}
    constants_hash[constant_key][c.constant_value] = c.constant_name  
  return constants_hash

@Profiler
def option_list(request):
  ''' 
  |  Return a list of all available configuration options.
  |  Accepts the *data* parameter with a JSON object containing:

  1. *section* [1, 2, 3, 4] (see *constants* table for value meaning)
  2. *name* filter options by matching the start of their name with this value

  |  Example call:
  |  `curl -k --compressed 'https://techu/option/list/?pretty=1' --data-urlencode data='{ "section" : 4, "name" : "sql_attr" }'
  |  Returns all options belonging to datasources starting with "sql_attr".
  '''
  r = request_data(request)
  constant_list = constants()['sp_options_section']
  constant_list['0'] = '-'
  conditions = filter_list(r, { 'name' : 'startswith', 'section' : None })
  options = Option.objects.filter(**conditions).order_by('name')
  option_list = [ { 'id' : o.id, 'name' : o.name, 'section' : constant_list[unicode(o.section)] } for o in options ] 
  return R(option_list, request)

@Profiler
def option(request, section, section_instance_id):
  ''' 
  |  Connect options with searchd, indexes & sources and store their values.
  |  Receives a JSON object with the *data* parameter containing options (keys) and their values. 
  |  You can group parameters and assign values with a list.
  `curl -k --compressed 'https://techu/option/searchd/6/' --data-urlencode data='{
    "listen" : [ 
      "9312", 
      "9306:mysql41" 
      ], 
    "workers" : "threads", 
    "pid_file" : "/var/run/stackoverfow_searchd.pid", 
    "max_matches" : 1000 
  }'`
  '''
  section = section.lower()
  data = request_data(request)
  options = Option.objects.filter(name__in = data.keys())
  options_stored = []
  options_created = 0  
  options_found = 0
  for option in options:
    if not isinstance(data[option.name], list):
      values = [data[option.name]]
    else:
      values = data[option.name]
    for value in values:      
      value = unicode(value)
      value_hash = md5(value).hexdigest()
      if section == 'searchd':      
        o = SearchdOption.objects.get_or_create(
              sp_searchd_id = section_instance_id, 
              sp_option_id = option.id, 
              value = value,
              value_hash = value_hash)
      elif section == 'index':
        o = IndexOption.objects.get_or_create(
              sp_index_id = section_instance_id,
              sp_option_id = option.id,
              value = value,
              value_hash = value_hash)
      elif section == 'source':
        o = SourceOption.objects.get_or_create(
              sp_source_id = section_instance_id,
              sp_option_id = option.id,
              value = value,
              value_hash = value_hash)
      if o[1]:
        options_created += 1
      else:
        options_found += 1
      options_stored.append(o[0].id)
  if section == 'searchd':    
    options_stored = SearchdOption.objects.filter(id__in = options_stored)
  elif section == 'index':    
    options_stored = IndexOption.objects.filter(id__in = options_stored) 
  elif section == 'source':    
    options_stored = SourceOption.objects.filter(id__in = options_stored)
  options_stored = { 'created' : options_created, 'found' : options_found, 'options' : options_stored }
  return R(options_stored, request)

@Profiler
def index(request, index_id = 0):
  ''' 
  |  Add or modify information for an index.
  |  It can be associated with a configuration entity with the *configuration_id* parameter.
  `curl -k --compressed 'https://techu/index/' --data-urlencode name='so_posts_rt' --data-urlencode configuration_id='25'`
  '''
  data = request_data(request)
  fields = model_fields(Index, data)
  ci = None
  if index_id == 0:
    try:
      index = Index.objects.create(**fields)
      if 'configuration_id' in r:
        ci = ConfigurationIndex.objects.create(sp_index_id = i.id, 
                                               sp_configuration_id = int(r['configuration_id']), 
                                               is_active = 1)
      index = Index.objects.filter(pk = i.id)
    except IntegrityError as e:
      index = Index.objects.filter(name = fields['name']).update(**fields)
      index = Index.objects.filter(pk = index.id)
  else:
    try:
      index = Index.objects.filter(pk = index_id)
    except:
      return E(message = 'Error while retrieving object with primary key "%d"' % index_id)
  return R({ 'index' : index, 'configurations' : ci }, request)

@Profiler
def index_list(request):
  ''' 
  Return a JSON Array with all indexes 
  '''
  return R(Index.objects.all(), request)

@Profiler
def configuration_list(request):
  ''' 
  Return a list of all configurations.
  '''
  return R(Configuration.objects.all(), request)

@Profiler
def searchd(request, searchd_id = 0):
  ''' 
  Store a new searchd 
  '''
  data = request_data(request)
  fields = model_fields(Searchd, data)
  if searchd_id > 0:
    s = Searchd.objects.filter(pk = searchd_id).update(**fields)
  else:
    s = Searchd.objects.create(**fields)
  cs = None
  if 'configuration_id' in r:
    cs = ConfigurationSearchd.objects.create(sp_configuration_id = int(r['configuration_id']), sp_searchd_id = searchd_id)
  return R({ 'searchd' : s, 'configurations' : cs }, request)

@Profiler
def configuration(request, configuration_id = 0):
  ''' 
  Get or update information for a configuration 
  '''
  data = request_data(request)
  fields = model_fields(Configuration, data)
  if configuration_id > 0:
    configuration = Configuration.objects.get(pk = conf_id)
  else:
    if not regex_check(r['name']):
      return E(message = 'Illegal configuration name "%s"' % r['name'])
    try:
      c = Configuration.objects.create(**fields)
      c.hash = md5(str(c.id) + c.name).hexdigest()
      c.save(update_fields = ['hash'])
      configuration = Configuration.objects.filter(pk = c.id)
    except Exception as e:
      return E(message = str(e))
    except IntegrityError as e:
      return E('IntegrityError: ' + str(e))
  return R(configuration, request)

@Profiler
def batch_indexer(request, action, index_id):
  '''
  Bulk indexing 
  '''
  action = action.lower()
  data = request_data(request)
  queue = is_queued(request)  
  if not isinstance(data, list):
    data = [ data ]
  responses = []
  if action == 'insert':
    values = []
    fields = data[0].keys()
    for document in data:
      values.append(document.values())
    responses.append( insert(index_id, fields, values, queue) )
  elif action == 'update':
    fields = data[0].keys()
    fields.remove('id')
    for document in data:
      responses.append( update(index_id, document['id'], fields, [ document[field] for field in fields ], queue) )
  elif action == 'delete':
    for document in data:
      responses.append(delete(index_id, document['id'], queue))
  else:
    return E(message = 'Unknown action. Valid types are [ insert, update, delete ]')
  return R(responses)    

@Profiler
def indexer(request, action, index_id, doc_id = 0):
  ''' Add, delete, update documents '''
  action = action.lower()
  data = request_data(request)
  if 'id' in data and doc_id == 0:
    doc_id = int(data['id'])
  queue = is_queued(request)  
  if action == 'insert':
    response = insert(index_id, data.keys(), [ data.values() ], queue)
  elif action == 'update':
    response = update(index_id, doc_id, data.keys(), data.values(), queue) 
  elif action == 'delete':
    response = delete(index_id, doc_id, queue) 
  else:
    return E(message = 'Unknown action. Valid types are [ insert, update, delete ]')
  return R(response)

def insert(index_id, fields, values, queue = True):
  ''' 
  Build INSERT statement. 
  Supports multiple VALUES sets for batch inserts.
  '''
  index = fetch_index_name(index_id)
  sql  = "INSERT INTO %s(%s) VALUES" % (index, ',' . join(fields))
  sql += '(' + ','.join([ '%s' for v in values[0] ]) + ')'
  return modify_index(index_id, sql, queue, values)

def delete(index_id, doc_id, queue = True):
  ''' Build DELETE statement '''
  index = fetch_index_name(index_id)
  sql = 'DELETE FROM ' + identq(index) + ' WHERE id = %d' % (int(doc_id),)
  return modify_index(index_id, sql, queue)

def update(index_id, doc_id, fields, values, queue = True):
  ''' Build UPDATE statement '''
  index = fetch_index_name(index_id)
  sql = 'UPDATE %s SET ' % (identq(index),)
  for n, v in enumerate(values):
    sql += fields[n] + ' = %s,'
  sql = sql.rstrip(',') + ' WHERE id = ' + str(int(doc_id))
  return modify_index(index_id, sql, queue, values)

def modify_index(index_id, sql, queue, values = None, retries = 0):
  ''' 
  Either adds to index directly or queues statements 
  for async execution by storing them in Redis 
  If either Redis or searchd is unresponsive MAX_RETRIES attempts will be performed 
  in order to store the request to the alternative
  '''
  if retries > settings.MAX_RETRIES: 
    return E(message = 'Maximum retries %d exceeded' % retries)
  queue_action = None
  if sql.find('INSERT') == 0:
    queue_action = 'insert'
  elif sql.find('UPDATE') == 0:
    queue_action = 'update'
  elif sql.find('DELETE') == 0:
    queue_action = 'delete'
  response = None
  cache = Cache()
  if not queue:
    try:
      c = connections['sphinx:' + str(index_id)]
      cursor = c.cursor()
      if queue_action == 'delete':
        cursor.execute( sql )
      elif queue_action == 'update':
        cursor.execute(sql, values)
      elif queue_action == 'insert':
        cursor.executemany(sql, values)
      cache.dirty(index_id)
      response = { 'searchd' : 'ok' }
    except Exception as e:
      return str(e)
      response = modify_index(index_id, sql, True, values, retries + 1)
  else:
    try:
      rkey = rqueue(queue_action, index_id, sql, values)
      response = { 'redis' : rkey }
    except Exception as e:
      response = modify_index(index_id, sql, False, values, retries + 1)
  return response

@Profiler
def fetch_index_name(index_id):
  ''' Fetch index name by id '''
  try:
    c = Cache()
    if not c.exists('structures:indexes'):
      for index in Index.objects.all():
        if index_id == index.id:
          index_name = index.name
        c.hset('structures:indexes', str(index.id), index.name, True)
    else:
      indexes = c.hget('structures:indexes')
      index_id = str(index_id)
      if index_id in indexes:
        index_name = indexes[index_id]
      else:
        return E(message = 'No such index')
    return index_name
  except Exception as e:
    return E(message = 'Error while retrieving index')

def rqueue(queue, index_id, sql, values):
  '''
  Redis queue for incoming requests
  Applier daemon continuously reads from this queue 
  and executes asynchronously 
  TODO: check if it works better with Pub/Sub
  '''
  r = redis_client()
  c = r.incr(settings.TECHU_COUNTER)
  request_time = int(time.time()*10**6)
  key = ':' . join(map(str, [ queue, index_id, request_time, c ]))
  if queue == 'delete':
    data = { 'sql' : sql, 'values' : [] }
  else:
    data = { 'sql' : sql, 'values' : values }
  ''' marshal serialization is much faster than JSON '''
  data = marshal.dumps(data)
  ''' Transaction '''
  p = r.pipeline()
  p.rpush('queue:' + str(index_id), key)
  p.set(key, data)
  p.execute()
  return key

@Scripting
@Profiler
def search(request, index_id):
  cache = Cache()
  index = fetch_index_name(index_id)
  ''' Search wrapper with SphinxQL '''
  r = request_data(request)
  if settings.SEARCH_CACHE:
    cache_key = md5(index + request.REQUEST['data']).hexdigest()
    lock_key = 'lock:' + cache_key
    version = cache.version(index_id)
    cache_key = 'cache:search:%s:%d:%s' % (cache_key, index_id, version)
    try:   
      response = cache.get(cache_key) 
      if not response is None:
        return R(response, 200, False)
      else:
        ''' lock this key for re-caching '''
        start = time.time()
        lock = cache.get(lock_key)
        while ( not lock is None ):
          lock = cache.get(lock_key)
          if (time.time() - start) > settings.CACHE_LOCK_TIMEOUT:
            return E(message = 'Cache lock wait timeout exceeded')
        ''' check if key now exists in cache '''
        response = cache.get(cache_key)
        if not response is None:
          return R(response, 200, False)
        ''' otherwise acquire lock for this session '''
        cache.set(lock_key, 1, True, settings.CACHE_LOCK_TIMEOUT) # expire in 10sec        
    except:
      pass    
  
  option_mapping = {
    'mode' : {
        'extended' : SPH_MATCH_EXTENDED2,
        'boolean'  : SPH_MATCH_BOOLEAN,
        'all'      : SPH_MATCH_ALL,
        'phrase'   : SPH_MATCH_PHRASE,
        'fullscan' : SPH_MATCH_FULLSCAN,
        'any'      : SPH_MATCH_ANY,
      }
  }
  options = {
      'sortby'      : '',
      'mode'        : 'extended',
      'groupby'     : '',
      'groupsort'   : '',
      'offset'      : 0,
      'limit'       : 1000,
      'max_matches' : 0,
      'cutoff'      : 0,
      'fields'      : '*',
    }
  
  sphinxql_list_options = {
    'ranker' : [ 'proximity_bm25', 'bm25', 'none', 'wordcount', 'proximity',
                 'matchany', 'fieldmask', 'sph04', 'expr', 'export' ],
    'idf' : [ 'normalized', 'plain'],
    'sort_method'  : ['pq', 'kbuffer' ]
  }
  sphinxql_options = { 
    'agent_query_timeout' : 10000,
    'boolean_simplify' : 0,
    'comment' : '',
    'cutoff'  : 0,
    'field_weights' : '',
    'global_idf' : '',
    'idf' : 'normalized',
    'index_weights'  : '',
    'max_matches' : 10000,
    'max_query_time' : 10000,
    'ranker' : 'proximity_bm25',
    'retry_count' : 2,
    'retry_delay' : 100,
    'reverse_scan' : 0,
    'sort_method'  : 'pq'
  }
  order_direction = {
    '-1'   : 'DESC',
    'DESC' : 'DESC',
    '1'    : 'ASC',
    'ASC'  : 'ASC',
  }

  try:
    ''' Check attributes from request with stored options (sp_index_option) '''
    ''' Preload host and ports per index '''
    '''
    SELECT
    select_expr [, select_expr ...]
    FROM index [, index2 ...]
    [WHERE where_condition]
    [GROUP BY {col_name | expr_alias}]
    [WITHIN GROUP ORDER BY {col_name | expr_alias} {ASC | DESC}]
    [ORDER BY {col_name | expr_alias} {ASC | DESC} [, ...]]
    [LIMIT [offset,] row_count]
    [OPTION opt_name = opt_value [, ...]]
    '''
    sql_sequence = [ ('SELECT', 'fields'), ('FROM', 'indexes'), ('WHERE', 'where'), 
                     ('GROUP BY', 'group_by'), ('WITHIN GROUP ORDER BY', 'order_within_group'), 
                     ('ORDER BY', 'order_by'), ('LIMIT', 'limit'), ('OPTION', 'option') ]
    sql = {}
    for sql_clause, key in sql_sequence:
      sql[key] = ''
      if not key in r:
        r[key] = ''
    sql['indexes'] = index + ','.join( r['indexes'] )
    if isinstance(r['fields'], list):
      sql['fields'] = ',' . join(r['fields'])
    else:
      sql['fields'] = options['fields']
    if r['group_by'] != '':
      sql['group_by'] = r['groupby']
    if not isinstance(r['limit'], dict):
      r['limit'] = { 'offset' : '0', 'count' : options['limit'] }
    r['limit'] = '%(offset)s, %(count)s' % r['limit']
    sql['order_by'] = ',' . join([ '%s %s' % (order[0], order_direction(order[1].upper())) for order in r['order_by'] ])
    if r['order_within_group'] != '':
      sql['order_within_group'] = ',' . join([ '%s %s' % (order[0], order_direction(order[1].upper())) for order in r['order_within_group'] ])
    sql['where'] = [] #dictionary e.g. { 'date_from' : [[ '>' , 13445454350] ] } 
    value_list = []
    if isinstance(r['where'], dict):
      for field, conditions in r['where'].iteritems():
        for condition in conditions:
          operator, value = condition
          value_list.append(value)
          sql['where'].append('%s%s%%s' % (field, operator,))
    value_list.append(r['q'])
    sql['where'].append('MATCH(%%s)')
    sql['where'] = ' ' . join(sql['where'])
    if isinstance(r['option'], dict):
      sql['option'] = []
      for option_name, option_value in r['option'].iteritems():
        if isinstance(option_value, dict): 
          option_value = '(' + (','. join([ '%s = %s' % (k, option_value[k]) for k in option_value.keys() ])) + ')'
          sql['option'].append('%s = %s' % (option_name, option_value))
      sql['option'] = ',' . join(sql['option'])
    response = { 'results' : None, 'meta' : None }
    try:    
      cursor = connections['sphinx:' + index].cursor()
      sql =  ' ' . join([ clause[0] + ' ' + sql[clause[1]] for clause in sql_sequence if sql[clause[1]] != '' ]) 
      cursor.execute(sql, value_list)
      response['results'] = cursorfetchall(cursor)
    except Exception as e:
      error_message = 'Sphinx Search Query failed with error "%s"' % str(e)
      return E(message = error_message)
    try:
      cursor.execute('SHOW META')
      response['meta'] = cursorfetchall(cursor)
    except:
      pass
    if settings.SEARCH_CACHE:
      cache.set(cache_key, response, True, SEARCH_CACHE_EXPIRE, lock_key)
  except Exception as e:
    return E(message = str(e))
  return R(response)

@Scripting
@Profiler
def excerpts(request, index_id):
  cache = Cache()
  ''' 
  Returns highlighted snippets 
  Caches responses in Redis
  '''
  index_id = int(index_id)
  index = fetch_index_name(index_id)
  r = request_data(request)
  cache_key = md5(index + json.dumps(r)).hexdigest()
  lock_key = 'lock:' + cache_key
  version = cache.version(index_id)
  cache_key = 'cache:excerpts:%s:%d:%s' % (cache_key, index_id, version)
  if not 'docs' in r:
    return R({})
  if settings.EXCERPTS_CACHE:
    try:   
      response = cache.get(cache_key) 
      if not response is None:
        return R(response, request, code = 200, serialize = False) 
      ''' lock this key for re-caching '''
      start = time.time()
      lock = cache.get(lock_key)
      while ( not lock is None ):
        lock = cache.get(lock_key)
        if (time.time() - start) > settings.CACHE_LOCK_TIMEOUT:
          return E(message = 'Cache lock wait timeout exceeded')
      ''' check if key now exists in cache '''
      response = cache.get(cache_key)
      if not response is None:
        return R(response, request, code = 200, serialize = False)
      ''' otherwise acquire lock for this session '''
      cache.set(lock_key, 1, True, settings.CACHE_LOCK_TIMEOUT) # expire in 10sec         
    except:
      return E(message = 'Error while examining excerpts cache')    

  options = {
      "before_match"      : '<b>',
      "after_match"       : '</b>',
      "chunk_separator"   : '...',
      "limit"             : 256,
      "around"            : 5,    
      "exact_phrase"      : False,
      "use_boundaries"    : False,
      "query_mode"        : True,
      "weight_order"      : False,
      "force_all_words"   : False,
      "limit_passages"    : 0,
      "limit_words"       : 0,
      "start_passage_id"  : 1,
      "html_strip_mode"   : 'index',
      "allow_empty"       : False,
      "passage_boundary"  : 'paragraph',
      "emit_zones"        : False
  }
  for k, v in options.iteritems():
    if k in r:
      if isinstance(v, int):
        options[k] = int(r[k])
      elif isinstance(v, bool):
        options[k] = bool(r[k])
      else:
        options[k] = r[k]
  if 'ttl' in r:      
    cache_expiration = int(r['ttl'])
  else:
    cache_expiration = settings.EXCERPTS_CACHE_EXPIRE
  if isinstance(r['docs'], dict):
    document_ids = r['docs'].keys()
    documents = r['docs'].values()
  elif isinstance(r['docs'], list):
    document_ids = range(len(r['docs'])) # get a list of numeric indexes from the list
    documents = r['docs']
  else:
    return E(message = 'Documents are passed as a list or dictionary structure')
  del r['docs'] # free up some memory
  '''
  docs = { 838393 : 'a document with lots of text', 119996 : 'another document with text' }
  '''
  ci = ConfigurationIndex.objects.filter(sp_index_id = index_id)[0]
  searchd_id = ConfigurationSearchd.objects.filter(sp_configuration_id = ci.sp_configuration_id)[0].sp_searchd_id
  ''' TODO: convert hard coded option ids to constants '''
  so = SearchdOption.objects.filter(sp_searchd_id = searchd_id, sp_option_id = 138,).exclude(value__endswith = ':mysql41')
  sphinx_port = int(so[0].value)
  try:
    so = SearchdOption.objects.filter(sp_searchd_id = searchd_id, sp_option_id = 188,)
    if so:
      sphinx_host = so[0].value
    else:
      sphinx_host = 'localhost'
  except:
    sphinx_host = 'localhost'
  try:
    cl = SphinxClient()
    cl.SetServer(host = sphinx_host, port = sphinx_port)
    excerpts = cl.BuildExcerpts( documents, index, r['q'], options )
    del documents
    if not excerpts:
      return E(message = 'Sphinx Excerpts Error: ' + cl.GetLastError())
    else:      
      if settings.EXCERPTS_CACHE:
        cache.set(cache_key, excerpts, True, cache_expiration, lock_key)
      excerpts = { 
        'excerpts' : dict(zip(document_ids, excerpts)), 
        'cache-key' : cache_key,        
        }
      return R(json.dumps(excerpts), request)
  except Exception as e:
    return E(message = 'Error while building excerpts ' + str(e))

@Profiler
def generate(request, configuration_id):
  import codecs
  ''' 
  |  Generate configuration file and restart searchd instances. 
  |  Response contains a dictionary with the configuration file contents, 
  |  the stop/start commands and the current status.
  
  **Parameters**
  *dryrun*
      |  Whether to store/overwrite the generated configuration and restart searchd.
      |  Useful in cases when you want to inspect a configuration file.
      |  Values [0,1]

      Example:
      `curl -k 'https://techu/generate/25/?pretty=1' --data-urlencode data='{ "dryrun" : 1 }'`
  '''
  r = request_data(request)
  searchd_start = 'searchd --config %(config)s %(switches)s'
  searchd_stop  = 'searchd --config %(config)s --stopwait'
  params = {}
  params['switches'] = ' '.join([ '--iostats', '--cpustats' ])
  c = Configuration.objects.get(pk = configuration_id)
  params['config'] = os.path.join(settings.PROJECT_ROOT, settings.SPHINX_CONFIGURATION_DIR, c.name) + '.conf'
  ci = ConfigurationIndex.objects.filter(sp_configuration_id = configuration_id).exclude(is_active = 0)
  si = ConfigurationSearchd.objects.filter(sp_configuration_id = configuration_id)
  searchd_options = SearchdOption.objects.filter(sp_searchd_id = si[0].sp_searchd_id)
  option_list = [ option.sp_option_id for option in searchd_options ]  
  indexes = Index.objects.filter(id__in = [ index.sp_index_id for index in ci ]).exclude(is_active = 0)
  parent_indexes = Index.objects.filter(id__in = [ index.parent_id for index in indexes ])
  index_options = IndexOption.objects.filter(sp_index_id__in = [ index.id for index in indexes ] + [index.id for index in parent_indexes ] )
  option_list += [ option.sp_option_id for option in index_options ]
  options = Option.objects.filter(id__in = option_list).values()
  option_names = {}
  for o in options:
    option_names[o['id']] = o['name']
  configuration = []
  for index in indexes:
    parent_name = ''
    if index.parent_id > 0:
      for pi in parent_indexes:
        if pi.id == index.parent_id:
          parent_name = ':' + pi.name
    index_name = index.name + parent_name
    configuration.append('index ' + index_name + ' {')
    for option in index_options:
      if option.sp_index_id == index.parent_id:
        configuration.append('  %s = %s' % ( unicode(option_names[option.sp_option_id]).ljust(30), unicode(option.value)))
      if option.sp_index_id == index.id:
        configuration.append('  %s = %s' % ( unicode(option_names[option.sp_option_id]).ljust(30), unicode(option.value)))
    configuration.append('}')  
  configuration.append('searchd {')
  for option in searchd_options:    
    configuration.append('  %s = %s' % ( unicode(option_names[option.sp_option_id].ljust(30)), unicode(option.value)))
  configuration.append('}')
  configuration.append("")
  configuration = "\n" . join(configuration)
  if 'dryrun' in r and int(r['dryrun']) != 1:
    f = codecs.open(params['config'], mode = 'w', encoding = 'utf-8')
    f.write(configuration)
    f.close()
    try:
      stopped = os.system(searchd_stop % params)
      started = os.system(searchd_start % params)
    except Exception as e:
      return E(message = 'Error while restarting searchd ' + str(e))
  else:
    stopped = 1
    started = 1
  response = { 
    'configuration' : configuration, 
    'stopped' : { 'command' : searchd_stop % params,  'status' : not bool(stopped) }, 
    'started' : { 'command' : searchd_start % params, 'status' : not bool(started) },
    }
  return R(response, request)


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for techu project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "techu.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techu.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = _settings
# Django settings for techu project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CONN_MAX_AGE = None
ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'techu',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '3306',                      # Set to empty string for default.
    },
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Athens'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/admin/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    '/home/techu-search-server/techu/admin/static/'
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!3klksdfo$*#@)kdsd;lds;0bfn&!jd$rof8aq_!n76$@&-8vcwrc-'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'techu.libraries.middleware.ConnectionMiddleware',
    )

ROOT_URLCONF = 'techu.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'techu.wsgi.application'

TEMPLATE_DIRS = (
    '/home/techu-search-server/techu/admin/templates/'
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_graceful',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


import os, sys
''' 
    Techu Project Settings 
    Version 0.1beta
'''
PROFILER = True
SCRIPTING = True
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PROJECT_ROOT)
TECHU_COUNTER = '84920c64c98c9cf2a7ab4af756c84b33'
MAX_RETRIES = 10
SEARCH_FAIL_ERROR = 1
SEARCH_FAIL_WARNING = 2
SEARCH_FAILURE_LEVEL = SEARCH_FAIL_WARNING
SEARCH_CACHE = True
EXCERPTS_CACHE = True
EXCERPTS_CACHE_EXPIRE = 10 # Cache expiration in seconds
APPHOST = 'techu'
CACHE_LOCK_TIMEOUT = 10
SEARCH_CACHE_EXPIRE = 120.
''' Redis '''
REDIS_PORT = 6379
REDIS_HOST = 'localhost'
REDIS_PASSWORD = None
''' Graceful restart (thanks to https://github.com/andreiko/django_graceful) '''
GRACEFUL_STATEDIR = '/home/techu-search-server/run/'
SPHINX_CONFIGURATION_DIR = '/home/techu-search-server/techu/sphinx.conf'

########NEW FILE########
