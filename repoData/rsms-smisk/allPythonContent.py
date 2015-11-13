__FILENAME__ = controllers
# encoding: utf-8
import sys, os, logging, time
from smisk.mvc.control import Controller
from models import *

log = logging.getLogger(__name__)

class root(Controller):
  def __call__(self, *args, **kwargs):
    log.debug('root.__call__: got args: %s  kwargs: %s', repr(args), repr(kwargs))
    return dict(
      title = "This is a title",
      message = "This message was created at %f" % time.time(),
      aset = {
        "crazy<nyckel": "mos",
        "en annan nyckel": [123, 45.72401, "You", u"Uniyou", ("A", "B", r'C')]
      }
    )
  
  def posts(self, *args, **kwargs):
    pass
    # this will never be called from the outside, as class posts shadows this.


class posts(root):
  def __call__(self, *args, **kwargs):
    session.begin()
    post = Post(title='the title', body='das bothy')
    session.commit()
    return {
      #"post": post,
      "Post.query.all()": repr(Post.query.all()),
      "Method called": "%s.__call__()\n" % repr(self),
      "Request args": repr(args),
      "params": repr(kwargs)
    }
  
  def show(self, post_id=0, *args, **kwargs):
    return {'message': "from root > %s.show(post_id=%s)" % (repr(self), str(post_id))}
  
  class edit(root):
    def __call__(self, *args, **kwargs):
      return {'message': "from root > posts.%s.__call__()" % repr(self)}
    
    def save(self, *args, **kwargs):
      return {'message': "from root > posts.%s.save()" % repr(self)}
    
  

########NEW FILE########
__FILENAME__ = models
# encoding: utf-8
from smisk.mvc.model import *

# Database
metadata.bind = 'sqlite:///'
#metadata.bind.echo = True

class Post(Entity):
  title = Field(Unicode())
  body = Field(Unicode())

########NEW FILE########
__FILENAME__ = controllers
# encoding: utf-8
import sys, os, logging, time
from smisk.mvc.control import Controller
from models import *

log = logging.getLogger(__name__)

class root(Controller):
  def __call__(self, *args, **kwargs):
    log.debug('root.__call__: got args: %s  kwargs: %s', repr(args), repr(kwargs))
    return dict(
      title = "This is a title",
      message = "This message was created at %f" % time.time(),
      aset = {
        "crazy<nyckel": "mos",
        "en annan nyckel": [123, 45.72401, "You", u"Uniyou", ("A", "B", r'C')]
      }
    )
  
  def posts(self, *args, **kwargs):
    pass


class posts(root):
  def __call__(self, named_arg=None, *args, **kwargs):
    session.begin()
    post = Post(title='the title', body='das bothy')
    session.commit()
    # dir(Post) ['__class__', '__delattr__', '__dict__', '__doc__', '__getattribute__', '__hash__', '__init__', '__metaclass__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__str__', '__weakref__', '_caller', '_class_state', '_descriptor', '_global_session', '_setup_done', 'body', 'c', 'count', 'count_by', 'delete', 'expire', 'expunge', 'filter', 'filter_by', 'flush', 'get', 'get_by', 'id', 'instances', 'join_to', 'join_via', 'mapper', 'merge', 'options', 'query', 'refresh', 'save', 'save_or_update', 'select', 'select_by', 'selectfirst', 'selectfirst_by', 'selectone', 'selectone_by', 'set', 'table', 'title', 'update']
    # dir(session) ['__call__', '__class__', '__contains__', '__delattr__', '__dict__', '__doc__', '__getattribute__', '__hash__', '__init__', '__iter__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__str__', '__weakref__', 'begin', 'begin_nested', 'bind', 'clear', 'close', 'close_all', 'commit', 'configure', 'connection', 'delete', 'deleted', 'dirty', 'execute', 'expire', 'expunge', 'extension', 'flush', 'get', 'get_bind', 'identity_key', 'identity_map', 'is_modified', 'load', 'mapper', 'merge', 'new', 'object_session', 'query', 'query_property', 'refresh', 'registry', 'remove', 'rollback', 'save', 'save_or_update', 'scalar', 'session_factory', 'update']
    response.headers.append('Content-Type: text/xml')
    return [
      "newly created post = %s\n" % post,
      "Post.query.all() = %s\n" % repr(Post.query.all()),
      "from root > %s.__call__()\n" % repr(self),
      "  named_arg = %s\n" % repr(named_arg),
      "  args      = %s\n" % repr(args),
      "  kwargs    = %s\n" % repr(kwargs)
    ]
  
  def show(self, post_id=0, *args, **kwargs):
    response("from root > %s.show(post_id=%s)\n" % (repr(self), post_id))
  
  class edit(root):
    def __call__(self, *args, **kwargs):
      response("from root > posts.%s.__call__()\n" % repr(self))
    
    def save(self, *args, **kwargs):
      response("from root > posts.%s.save()\n" % repr(self))
    
  

########NEW FILE########
__FILENAME__ = models
# encoding: utf-8
from smisk.mvc.model import *

# Database
metadata.bind = 'sqlite:///'
metadata.bind.echo = True

class Post(Entity):
  title = Field(Unicode())
  body = Field(Unicode())

########NEW FILE########
__FILENAME__ = mvc_process
#!/usr/bin/env python
# encoding: utf-8
import os
from smisk.mvc import Application

if __name__ == '__main__':
  Application.main(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = application
# encoding: utf-8

# If a template is added with the key 0 (zero), it will be used for any HTTP
# error which does _not_ have a explicit error template configured.
templates.errors = {
  404: 'errors/404.html'
}

# Routes
# The earlier it is specified, the higher the priority.
router.map(r'^/(favicon.ico$|res)', controller='files', action='send')
router.map('/', controller='posts', action='index')
router.map('/:controller/:action/:id')

# Database
model.metadata.bind = "mysql://hal_http_log:secret@hal.hunch.se/hal_http_log"
model.metadata.bind.echo = True

# Logging
logging.basicConfig(
  level = logging.DEBUG,
  stream = sys.stdout,
  #filename = os.path.join(appdir, 'log', 'application.log'),
  format = '%(asctime)s.%(msecs)d %(levelname)-8s %(name)-7s %(message)s',
  datefmt = '%d %b %H:%M:%S',
)

########NEW FILE########
__FILENAME__ = development
# encoding: utf-8

# Short session life time
app.sessions.ttl = 10

########NEW FILE########
__FILENAME__ = production
# encoding: utf-8
templates.autoreload = False
templates.show_traceback = False
app.autoreload = False

########NEW FILE########
__FILENAME__ = resources
# encoding: utf-8
from smisk.mvc.control import *

print __file__

class ResourcesController(Application):
  def index(self, **args):
    return dict(resources=Resource.query.all())
  

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
import sys, os, platform
from smisk import Application, Request, Response, request

class MyRequest(Request):
  def accepts_charsets(self):
    '''Return a list of charsets which the client can handle, ordered by priority and appearing order.'''
    vv = []
    if not 'HTTP_ACCEPT_CHARSET' in self.env:
      return vv
    for cs in self.env['HTTP_ACCEPT_CHARSET'].split(','):
      p = cs.find(';')
      if p != -1:
        pp = cs.find('q=', p)
        if pp != -1:
          vv.append([cs[:p], int(float(cs[pp+2:])*100)])
          continue
      vv.append([cs, 100])
    vv.sort(lambda a,b: b[1] - a[1])
    return [v[0] for v in vv]
  

class MyResponse(Response):
  def redirect_to_path(self, path):
    url = request.url
    include_port = True
    if url.port == 80:
      include_port = False
    url = url.to_s(port=include_port, path=False, query=False, fragment=False)
    self.headers += ['Status: 302 Found', 'Location: %s%s' % (url, path)]
  

class MyApp(Application):
  
  chunk = '.'*8000
  
  def __init__(self):
    self.request_class = MyRequest
    self.response_class = MyResponse
    Application.__init__(self)
  
  def service(self):
    # Test sending alot of data with content length
    #self.response.out.write("Content-Length: 8000\r\n\r\n")
    #self.response.out.write(self.chunk)
    
    # Test sending alot of data with chunked content
    #self.response.write(self.chunk)
    
    if self.request.url.path == "/go-away":
      self.response.redirect_to_path("/redirected/away")
      return
    
    if 'CONTENT_LENGTH' in self.request.env:
      # Test smisk_Request___iter__
      for line in self.request:
        self.response.write(line)
    
    self.response.headers = ["Content-Type: text/plain"]
    self.response.write("self.request.url = %s\n" % self.request.url)
    self.response.write("self.request.env.get('HTTP_ACCEPT_CHARSET') => %s\n" % self.request.env.get('HTTP_ACCEPT_CHARSET'))
    self.response.write("self.request.acceptsCharsets() = %s\n" % self.request.accepts_charsets())
    
    # Test smisk_Response___call__
    self.response(
      "__call__ Line1\n",
      "__call__ Line2\n",
      "__call__ Line3\n",
      "__call__ Line4\n",
    )
    
    # Test smisk_Response_writelines and at the same time test smisk_Stream_perform_writelines
    self.response.writelines((
      "writelines Line1\n",
      "writelines Line2\n",
      "writelines Line3\n",
      "writelines Line4\n",
    ))
    
    #self.response.write(self.chunk)
    
    #self.response.write("<h1>Hello World!</h1>"
    #  "request.env = <tt>%s</tt>\n" % self.request.env)
    #self.response.headers = ["Content-Type: text/html"]
    #err1()
  

# test exception response
def err1(): err2()
def err2(): err3()
def err3(): err4()
def err4(): err5()
def err5(): raise IOError("Kabooom!")

try:
  MyApp().run()
except KeyboardInterrupt:
  pass
except:
  import traceback
  traceback.print_exc(1000, open(os.path.abspath(os.path.dirname(__file__)) + "/process-error.log", "a"))


########NEW FILE########
__FILENAME__ = server_envs
# Lighttpd 1.4, http
'CONTENT_LENGTH': '359',
'CONTENT_TYPE': 'multipart/form-data; boundary=----WebKitFormBoundarymKzNHjDXLFHAxJ54',
'DOCUMENT_ROOT': '/Users/rasmus/src/smisk/examples/core/input/',
'FCGI_ROLE': 'RESPONDER',
'GATEWAY_INTERFACE': 'CGI/1.1',
'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
'HTTP_ACCEPT_ENCODING': 'gzip, deflate'
'HTTP_ACCEPT_LANGUAGE': 'en-us',
'HTTP_CONNECTION': 'keep-alive',
'HTTP_CONTENT_LENGTH': '359',
'HTTP_COOKIE': 'SID=dm5impd1pijgu143ng6p985cnoba4dg5',
'HTTP_HOST': 'localhost:8080',
'HTTP_REFERER': 'http://localhost:8080/',
'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_5; en-us) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1',
'PATH_INFO': '',
'QUERY_STRING': '',
'REDIRECT_STATUS': '200',
'REMOTE_ADDR': '::1',
'REMOTE_PORT': '50012',
'REQUEST_METHOD': 'POST',
'REQUEST_URI': '/receive',
'SCRIPT_FILENAME': '/Users/rasmus/src/smisk/examples/core/input/receive',
'SCRIPT_NAME': '/receive',
'SERVER_ADDR': '::1',
'SERVER_NAME': 'localhost:8080',
'SERVER_PORT': '8080',
'SERVER_PROTOCOL': 'HTTP/1.1',
'SERVER_SOFTWARE': 'lighttpd/1.4.19 smisk/1.1.0',

# Lighttpd 1.4, https
'CONTENT_LENGTH': '51',
'CONTENT_TYPE': 'application/x-www-form-urlencoded',
'DOCUMENT_ROOT': '/Users/rasmus/src/smisk/examples/core/input/',
'FCGI_ROLE': 'RESPONDER',
'GATEWAY_INTERFACE': 'CGI/1.1',
'HTTPS': 'on',
'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
'HTTP_ACCEPT_ENCODING': 'gzip, deflate'
'HTTP_ACCEPT_LANGUAGE': 'en-us',
'HTTP_CONNECTION': 'keep-alive',
'HTTP_CONTENT_LENGTH': '51',
'HTTP_COOKIE': 'SID=qrmslneg5t8uek1486sbeck1g01f46em',
'HTTP_HOST': 'localhost:8443',
'HTTP_REFERER': 'https://localhost:8443/',
'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_5; en-us) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1',
'PATH_INFO': '',
'QUERY_STRING': '',
'REDIRECT_STATUS': '200',
'REMOTE_ADDR': '127.0.0.1',
'REMOTE_PORT': '49336',
'REQUEST_METHOD': 'POST',
'REQUEST_URI': '/receive',
'SCRIPT_FILENAME': '/Users/rasmus/src/smisk/examples/core/input/receive',
'SCRIPT_NAME': '/receive',
'SERVER_ADDR': '127.0.0.1',
'SERVER_NAME': 'localhost:8443',
'SERVER_PORT': '8443',
'SERVER_PROTOCOL': 'http/1.1',
'SERVER_SOFTWARE': 'lighttpd/1.4.19 smisk/1.1.0',


# Nginx 0.6, http:
'CONTENT_LENGTH': '',
'CONTENT_TYPE': '',
'DOCUMENT_ROOT': '/opt/local/html',
'DOCUMENT_URI': '/',
'FCGI_ROLE': 'RESPONDER',
'GATEWAY_INTERFACE': 'CGI/1.1',
'HTTP_ACCEPT': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
'HTTP_ACCEPT_ENCODING': 'gzip, deflate'
'HTTP_ACCEPT_LANGUAGE': 'en-us',
'HTTP_CACHE_CONTROL': 'max-age=0',
'HTTP_CONNECTION': 'keep-alive',
'HTTP_COOKIE': 'SID=onqrdc4vtj2s22tp7di0m5bugr55n9ac',
'HTTP_HOST': 'localhost:8081',
'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_5; en-us) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1',
'QUERY_STRING': '',
'REMOTE_ADDR': '127.0.0.1',
'REMOTE_PORT': '49711',
'REQUEST_METHOD': 'GET',
'REQUEST_URI': '/',
'SCRIPT_FILENAME': '/dev/null',
'SCRIPT_NAME': '/',
'SERVER_ADDR': '127.0.0.1',
'SERVER_NAME': 'localhost',
'SERVER_PORT': '8081',
'SERVER_PROTOCOL': 'HTTP/1.1',
'SERVER_SOFTWARE': 'nginx/0.6.32 smisk/1.1.0',

########NEW FILE########
__FILENAME__ = serialization_test_matter
# encoding: utf-8

'''
GET /handler?x=2&y=A
'''

'''
POST /handler
Content-Type: application/x-www-form-urlencoded

x=2&y=A
'''

'''
POST /handler&x=2
Content-Type: application/x-www-form-urlencoded

y=A
'''

'''
POST /handler&x=2
Content-Type: application/json

{"y":"A"}
'''

# Resultat
{'x': 2, 'y': 'A'}

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Smisk documentation build configuration file, created by
# sphinx-quickstart on Sun Oct 26 20:24:33 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path[0:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))]
import smisk.release

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Smisk'
copyright = smisk.release.copyright[smisk.release.copyright.index(' '):].lstrip()

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '%d.%d' % smisk.release.version_info[0:2]
# The full version, including alpha/beta/rc tags.
release = smisk.release.version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

#todo_include_todos = True


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'screen.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Smiskdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Smisk.tex', 'Smisk Documentation',
   'Rasmus Andersson', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
import sys, os, socket
from datetime import datetime
from smisk.core import *

class MyApp(Application):
  # This is used to simulate processes dying for testing failover.
  # Set to -1 to disable
  die_after_num_requests = 4
  
  def __init__(self):
    Application.__init__(self)
    self.time_started = datetime.now()
  
  def service(self):
    self.response.headers = ["Content-Type: text/plain"]
    
    response(
      "This comes from a separately running process.\n\n",
      "Host:          %s\n" % socket.getfqdn(),
      "Listening on:  %s\n" % listening(),
      "Process id:    %d\n" % os.getpid(),
      "Process owner: %s\n" % os.getenv('USER'),
      "Time started:  %s\n" % self.time_started.strftime('%Y-%m-%d %H:%M:%S'),
      "\n",
      "self.request.url: %r\n" % self.request.url,
      "self.request.env: %r\n" % self.request.env
    )
    
    if self.die_after_num_requests != -1:
      self.die_after_num_requests -= 1
      if self.die_after_num_requests == 0:
        self.exit()
  

if __name__ == '__main__':
  from smisk.util.main import main
  main(MyApp)

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
import sys, os
from smisk.core import *

class MyApp(Application):
  def __init__(self, *args, **kwargs):
    super(MyApp, self).__init__(*args, **kwargs)
    # Set a very low session TTL for easy demonstration
    self.sessions.ttl = 10
    self.charset = 'iso-8859-1'
  
  def application_will_start(self):
    # Apply request input limits (reaaaally low, for testing purposes)
    self.request.max_multipart_size = 1024*1024 # 1 MB
    self.request.max_formdata_size = 51 # 51 bytes is exactly the amount of the default values in index.html
  
  def service(self):
    self.response.headers = ["Content-Type: text/plain;charset=" + self.charset]
    
    # Dump raw input?
    if 'dump' in self.request.get:
      while 1:
        chunk = self.request.input.read(8192)
        self.response.out.write(repr(chunk).strip("'").replace(r'\n', "\\n\n"))
        if len(chunk) < 8192:
          break
      return
    
    # Set a cookie
    if self.request.get.has_key('set_cookie'):
      self.response.set_cookie('a_cookie', self.request.get['set_cookie'], max_age=20)
    
    # Add some session data
    if self.request.get.has_key('set_session'):
      if self.request.get['set_session'] == '':
        self.request.session = None
      else:
        self.request.session = self.request.get['set_session']
    elif self.request.session is None:
      self.request.session = 'mos'
    
    # Reconstruct headers
    headers = []
    for k,v in self.request.env.items():
      if k.startswith('HTTP_'):
        headers.append('%s%s: %s' % (k[5],k[6:].lower(),v))
    
    # Print alot of information
    self.response(
      "self. %s\n" % repr(self),
      " request_class:       %s\n" % repr(self.request_class),
      " response_class       %s\n" % repr(self.response_class),
      " sessions_class: %s\n" % repr(self.sessions_class),
      " sessions.       %s\n" % repr(self.sessions),
      "  name:                %s\n" % repr(self.sessions.name),
      "  ttl:                 %d\n" % self.sessions.ttl,
      "\n",
      "self.request.\n",
      " env         %s\n" % repr(self.request.env),
      " get         %s\n" % repr(self.request.get),
      " post        %s\n" % repr(self.request.post),
      " files       %s\n" % repr(self.request.files),
      " cookies     %s\n" % repr(self.request.cookies),
      " input       %s\n" % repr(self.request.input.read()),
      " url         %s\n" % self.request.url,
      " session_id: %s\n" % repr(self.request.session_id),
      " session:    %s\n" % repr(self.request.session),
      " reconstructed headers:\n%s\n" % '\n'.join(headers),
      "\n",
      "self.response.\n",
      " custom headers:\n%s\n" % '\n'.join(self.response.headers),
      "\n",
      "Query parameters (GET):\n"
    )
    
    # More info
    w = self.response.write
    for k,v in self.request.get.items():
      w(k)
      w(" = ")
      try:
        w(v)
      except:
        w(repr(v))
      w("\n")
    w("\n")
    w("Form data (POST):\n")
    for k,v in self.request.post.items():
      w(k.encode(self.charset))
      w(" = ")
      try:
        w(v)
      except:
        w(repr(v))
      w("\n")
    w("\n")
    w("Cookies:\n")
    try:
      for k,v in self.request.cookies.items():
        w(k.encode(self.charset))
        w(" = ")
        try:
          w(v)
        except:
          w(repr(v))
        w("\n")
    except:
      w(repr(self.request.cookies))
    w("\n")
  

if __name__ == '__main__':
  from smisk.util.main import main
  main(MyApp)

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
import os
from smisk.core import Application
from smisk.ipc.bsddb import shared_dict
from smisk.serialization.json import json_encode, json_decode

class KeyValueStore(Application):
  '''A very simple key-value store using shared memory
  '''
  
  def __init__(self, *va, **kw):
    '''Setup the application
    '''
    Application.__init__(self, *va, **kw)
    
    # Use a shared dict, mapped in shared memory and shared between processes
    self.entries = shared_dict(homedir=os.path.join(os.path.dirname(__file__), 'store'),
      persistent=True)
  
  
  def service(self):
    '''Handle a request
    '''
    # The key is the request path
    key = self.request.url.path.strip('/')
    
    # Set content-type
    self.response.headers = ['Content-Type: application/json']
    
    # Standard reply
    rsp = '{"status": "OK"}'
    
    if not key:
      # Empty key means list all avilable keys
      if self.request.method == 'GET':
        rsp = json_encode({'keys': self.entries.keys()})
      else:
        rsp = self.method_not_allowed()
    else:
      # Non-empty key means manipulate the store
      # HTTP method defines the action
      if self.request.method == 'GET':
        # Read an entry
        try:
          rsp = json_encode(self.entries[key])
        except KeyError:
          rsp = self.not_found(key)
      elif self.request.method in ('PUT', 'POST'):
        # Set an antry
        self.entries[key] = json_decode(self.request.input.read(1024*1024))
      elif self.request.method == 'DELETE':
        # Delete an entry
        try:
          del self.entries[key]
        except KeyError:
          rsp = self.not_found(key)
      else:
        rsp = self.method_not_allowed()
    
    # Respond
    self.response.headers.append('Content-Length: %d' % (len(rsp)+1) )
    self.response(rsp, '\n')
  
  
  def not_found(self, key):
    '''Create a 404 Not Found response
    '''
    self.response.headers.append('Status: 404 Not Found')
    return '{"status": "No such key %r"}' % key
  
  
  def method_not_allowed(self):
    '''Create a 405 Method Not Allowed response
    '''
    self.response.headers.append('Status: 405 Method Not Allowed')
    return '{"status": "Method Not Allowed"}'

try:
  KeyValueStore().run()
except KeyboardInterrupt:
  pass

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
from smisk.core import Application

class MyApp(Application):
  def service(self):
    self.response("Hello World!")

MyApp().run()

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
import sys, os
from smisk.core import *

class MyApp(Application):
  def service(self):
    if self.request.url.path[-4:] == '.jpg':
      path = os.path.abspath(self.request.url.path.replace('..', '').lstrip('/'))
      sys.stderr.write("Sending file %s\n" % path)
      self.response.send_file(path)
    else:
      self.response.headers = ["Content-Type: text/html"]
      self.response.write("An image which will be sent using X-Sendfile if supported:<br/>")
      self.response.write('<img src="image.jpg" alt="" />')
  

try:
  MyApp().run()
except KeyboardInterrupt:
  pass
########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *
from smisk.serialization import data
import datetime, time

# Importing the serializers causes them to be registered
import my_xml_serializer
import my_text_serializer

# Some demo data
DEMO_STRUCT = dict(
  string = "Doodah",
  items = ["A", "B", 12, 32.1, [1, 2, 3]],
  float = 0.1,
  integer = 728,
  dict = dict(
    str = "<hello & hi there!>",
    unicode = u'M\xe4ssig, Ma\xdf',
    true_value = True,
    false_value = False,
  ),
  data = data("<binary gunk>"),
  more_data = data("<lots of binary gunk>" * 10),
  date = datetime.datetime.fromtimestamp(time.mktime(time.gmtime())),
)

# Our controller tree
class root(Controller):
  def __call__(self, *args, **params):
    '''Return some data
    '''
    return DEMO_STRUCT

  def echo(self, *va, **kw):
    '''Returns the structure received
    '''
    if not kw and va:
      kw['arguments'] = va
    return kw
  

if __name__ == '__main__':
  from smisk.config import config
  config.loads('"logging": {"levels":{"":DEBUG}}')
  main()

########NEW FILE########
__FILENAME__ = my_text_serializer
# encoding: utf-8
'''Example of a very simple "bare bones" text serializer
'''
from smisk.serialization import Serializer, serializers

class MyTextSerializer(Serializer):
  '''My simple text format
  '''
  # See the code in my_xml_serializer.py for explanation of the following
  # attributes:
  name = 'My text'
  extensions = ('mytext',)
  media_types = ('text/x-mytext',)
  charset = 'utf-8'
  can_serialize = True
  
  @classmethod
  def serialize(cls, params, charset):
    s = u'This is the response:\n'
    for kv in params.items():
      s += u'  %s: %s\n' % kv
    # This method must return a tuple of ( str<charset actually used>, str<data> )
    return (charset, s.encode(charset))
  

serializers.register(MyTextSerializer)

########NEW FILE########
__FILENAME__ = my_xml_serializer
# encoding: utf-8
'''Example of custom XML serialization
'''
from smisk.serialization.xmlbase import *
from datetime import datetime
from smisk.util.DateTime import DateTime
from smisk.util.type import *
from smisk.inflection import inflection
try:
  from elixir import Entity
except ImportError:
  class Undef(object):
    pass
  Entity = Undef()

__all__ = ['MyXMLSerializer']

class MyXMLSerializer(XMLSerializer):
  '''My custom XML format
  
  Maps a Python structure to a similar XML structure, about the same way YQL do
  http://developer.yahoo.com/yql/console/
  '''
  
  # This is the short name of our serializer. It shows up in reflection, etc.
  name = 'My XML'
  
  # A list of filename extensions we take care of.
  extensions = ('xml',)
  
  # A list of media types we take care of.
  media_types = ('text/xml',)
  
  # The preferred character encoding for responses without any particular
  # requirements.
  charset = 'utf-8'
  
  # This tells Smisk our serializer is able to write, or encode or serialize,
  # data.
  can_serialize = True
  
  # This is an extension of XMLSerializer, defining the name of the root
  # element.
  xml_root_name = 'rsp'
  
  @classmethod
  def build_object(cls, parent, name, value):
    e = ET.Element(name)
    if isinstance(value, datetime):
      e.text = DateTime(value).as_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
    elif isinstance(value, StringTypes):
      e.text = value
    elif isinstance(value, data):
      e.text = value.encode()
    elif isinstance(value, (int, float, long)):
      parent.set(name, unicode(value))
      return
    elif isinstance(value, DictType):
      for k in value:
        cls.build_object(e, k, value[k])
    elif isinstance(value, Entity):
      value = value.to_dict()
      for k in value:
        cls.build_object(e, k, value[k])
    elif isinstance(value, (list, tuple)):
      item_name = inflection.singularize(name)
      for v in value:
        if isinstance(v, (int, float, long)):
          v = unicode(v)
        elif isinstance(v, bool):
          v = unicode(v).lower()
        cls.build_object(parent, item_name, v)
      return
    elif value is not None:
      e.text = unicode(value)
    parent.append(e)
  
  @classmethod
  def build_document(cls, d):
    root = ET.Element(cls.xml_root_name, status=u'ok')
    for k in d:
      cls.build_object(root, k, d[k])
    return root
  

# Only register if an element tree impl is available
if ET is not None:
  # This registers the serializer and enables Smisk and other code to make use
  # of this serializer.
  serializers.register(MyXMLSerializer)

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *
from smisk.ipc.bsddb import shared_dict
from smisk.config import config

class root(Controller):
  def __init__(self):
    # If persistent evaluates to True, the contents of the shared 
    # dict will be flushed to disk on shutdown and read from disk 
    # on startup, thus providing a persistent set of data.
    self.entries = shared_dict(persistent=config.get('persistent'))
  
  def __call__(self):
    pass
  
  @expose(methods='GET')
  def entry(self):
    '''List available keys.
    '''
    return {'keys': self.entries.keys()}
  
  @expose(methods=('POST', 'PUT'))
  def set(self, key, value):
    '''Create or modify an entry.
    '''
    self.entries[key.encode('utf-8')] = value
  
  @expose(methods='GET')
  def get(self, key):
    '''Get value for key.
    '''
    try:
      return {'value': self.entries[key.encode('utf-8')]}
    except KeyError:
      raise http.NotFound('no value associated with key %r' % key)
  
  @expose(methods='DELETE')
  def delete(self, key):
    '''Remove entry.
    '''
    utf8_key = key.encode('utf-8')
    if utf8_key not in self.entries:
      raise http.NotFound(u'no such entry %r' % key)
    del self.entries[utf8_key]
  

if __name__ == '__main__':
  # Load the configuration file key-value-store.conf while assembling
  # the application
  main(config='key-value-store')

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *
from smisk.mvc.model import *
from smisk.serialization import xmlgeneric
import logging

log = logging.getLogger(__name__)

class Kitten(Entity):
  name = Field(Unicode(255), primary_key=True)
  color = Field(Unicode(30), required=True, default=u'purple')
  year_born = Field(Integer, required=True, default=0)

class root(Controller):
  def __call__(self, *args, **params):
    log.info('listing all kittens')
    return {'kittens': Kitten.query.all()}
  
  def create(self, name, color=None, year_born=None):
    name = name.strip()
    if not name:
      raise http.BadRequest('name attribute must not be empty')
    kitten = Kitten(name=name, color=color, year_born=year_born)
    log.info('created kitten: %r', kitten)
    redirect_to(self.read, kitten)
  
  def read(self, name):
    log.info('reading kitten %r', name)
    kitten = Kitten.get_by(name=name)
    if not kitten:
      raise http.NotFound()
    return {'kitten': kitten}
  
  def update(self, name, original_name=None, **params):
    if original_name and original_name != name:
      kitten = Kitten.get_by(name=original_name)
      kitten.name = name
    else:
      kitten = Kitten.get_by(name=name)
    kitten.from_dict(params)
    log.info('updated kitten %r', kitten)
    redirect_to(self.read, kitten)
  
  def delete(self, name):
    log.info('deleting kitten %r', name)
    kitten = Kitten.get_by(name=name)
    kitten.delete()
    redirect_to(self)

if __name__ == '__main__':
  main(config='kittens')

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *

class root(Controller):
  def __call__(self, **params):
    return {'request parameters': params}

main(autoreload=True)

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *

class root(Controller): pass
class examples(root):
  value = 'Hello World'
  
  def getValue(self):
    return {'value': self.value}
  
  def setValue(self, value):
    self.value = value
  

# Aquire the XML-RPC serializer and replace it's media types definition. 
ser = serializers.find('xmlrpc')
ser.media_types = ('text/xml',)

# Unregister all serializers and re-register the XML-RPC serializer,
# effectively only accepting and providing XML-RPC requests and responses.
# If we want to provide other serializers, simply remove or comment out the
# following two lines.
serializers.unregister()
serializers.register(ser)

if __name__ == '__main__':
  config.load('app.conf')
  main()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *

class root(Controller):
  def __call__(self):
    raise http.Found('/example')
  
  def echo(self, **params):
    return params
  
  def example(self):
    return {
      'title': 'Spellistan frum hell',
      'creator': 'rasmus',
      'trackList': [
        {
          'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'title': 'Go Crazy (feat. Majida)',
          'creator': 'Armand Van Helden',
          'album': 'Ghettoblaster',
          'trackNum': 1,
          'duration': 410000
        },
        {
          'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'title': 'Go Crazy2 (feat. Majida)',
          'creator': 'Armand Van Helden2',
          'album': 'Ghettoblaster2',
          'trackNum': 2,
          'duration': 410002
        },
        {
          'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
          'title': 'Go Crazy3 (feat. Majida)',
          'creator': 'Armand Van Helden3',
          'album': 'Ghettoblaster3',
          'trackNum': 3,
          'duration': 410007
        },
      ]
    }

if __name__ == '__main__':
  config.load('app.conf')
  main()

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
def hello_app(env, start_response):
  start_response("200 OK", [('Content-type', 'text/plain')])
  response = ["Hello, World!\n\n"]
  response.append("Environment:\n\n")
  for k in sorted(env.keys()):
    response.append(" %s: %s\n" % (k, env[k]) )
  return response

# Start the application
from smisk.wsgi import main
main(hello_app)

########NEW FILE########
__FILENAME__ = fcgi_frontend
#!/usr/bin/env python
# encoding: utf-8
#
# Trac FastCGI adapter backed by Smisk
# http://python-smisk.org/ 
#
# Author: Rasmus Andersson <rasmus@flajm.com>

from trac import __version__ as VERSION
from trac.web.main import dispatch_request
from smisk.wsgi import Gateway

def main():
  Gateway(dispatch_request).run()

if __name__ == '__main__':
  import pkg_resources
  pkg_resources.require('Trac==%s' % VERSION)
  main()

########NEW FILE########
__FILENAME__ = autoreload
# encoding: utf-8
'''Automatically reload processes when components are updated.
'''
import sys, os, logging, re
from smisk.util.threads import Monitor
from smisk.config import config

log = logging.getLogger(__name__)


class Autoreloader(Monitor):
  '''Reloads application when files change'''
  
  frequency = 1
  match = None
  
  def __init__(self, frequency=1, match=None):
    '''
    :param frequency: How often to perform file modification checks
    :type  frequency: int
    :param match:     Only check modules matching this regular expression.
                      Matches anything if None.
    :type  match:     re.RegExp
    '''
    self.config_files = set()
    self.mtimes = {}
    self.log = None # in runner thread -- should not be set manually
    self.match = match
    Monitor.__init__(self, self.run, self.setup, frequency)
  
  def start(self):
    '''Start our own perpetual timer thread for self.run.'''
    if self.thread is None:
      self.mtimes = {}
    self._update_config_files_list()
    Monitor.start(self)
  start.priority = 70 
  
  def _update_config_files_list(self):
    config_files = set()
    if config.get('smisk.autoreload.config', config.get('smisk.autoreload')):
      for path,conf in config.sources:
        if path[0] != '<':
          config_files.add(path)
    self.config_files = config_files
  
  def setup(self):
    self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
  
  def on_module_modified(self, path):
    # The file has been deleted or modified.
    self.log.info("%s was modified", path)
    self.thread.cancel()
    self.log.debug("Stopped autoreload monitor (thread %r)", self.thread.getName())
    import smisk.core
    smisk.core.app.exit()
  
  def on_config_modified(self, path):
    config.reload()
    self._update_config_files_list()
      
  def run(self):
    '''Reload the process if registered files have been modified.'''
    sysfiles = set()
    
    if config.get('smisk.autoreload.modules', config.get('smisk.autoreload')):
      for k, m in sys.modules.items():
        if self.match is None or self.match.match(k):
          if hasattr(m, '__loader__'):
            if hasattr(m.__loader__, 'archive'):
              k = m.__loader__.archive
          k = getattr(m, '__file__', None)
          sysfiles.add(k)
    
    for path in sysfiles | self.config_files:
      if path:
        if path.endswith('.pyc') or path.endswith('.pyo'):
          path = path[:-1]
        
        oldtime = self.mtimes.get(path, 0)
        if oldtime is None:
          # Module with no .py file. Skip it.
          continue
        
        #self.log.info('Checking %r' % sysfiles)
        
        try:
          mtime = os.stat(path).st_mtime
        except OSError:
          # Either a module with no .py file, or it's been deleted.
          mtime = None
        
        if path not in self.mtimes:
          # If a module has no .py file, this will be None.
          self.mtimes[path] = mtime
        else:
          #self.log.info("checking %s", path)
          if mtime is None or mtime > oldtime:
            if path.endswith(config.filename_ext) and path in [k for k,d in config.sources]:
              self.on_config_modified(path)
              self.mtimes[path] = mtime
            else:
              self.on_module_modified(path)
            return
  

if __name__ == '__main__':
  logging.basicConfig(
    level=logging.DEBUG,
    format = '%(levelname)-8s %(name)-20s %(message)s',
    datefmt = '%d %b %H:%M:%S'
  )
  
  import time, smisk.core
  ar = Autoreloader()
  ar.start()
  time.sleep(4)
  print 'Stopping'
  ar.stop()
  

########NEW FILE########
__FILENAME__ = charsets
# encoding: utf-8
'''Character encodings
'''

charsets = {
ur'ascii': {ur'alias':ur'646, us-ascii',ur'language':ur'English'},
ur'big5': {ur'alias':ur'big5-tw, csbig5',ur'language':ur'Traditional Chinese'},
ur'big5hkscs': {ur'alias':ur'big5-hkscs, hkscs',ur'language':ur'Traditional Chinese'},
ur'cp037': {ur'alias':ur'IBM037, IBM039',ur'language':ur'English'},
ur'cp424': {ur'alias':ur'EBCDIC-CP-HE, IBM424',ur'language':ur'Hebrew'},
ur'cp437': {ur'alias':ur'437, IBM437',ur'language':ur'English'},
ur'cp500': {ur'alias':ur'EBCDIC-CP-BE, EBCDIC-CP-CH, IBM500',ur'language':ur'Western Europe'},
ur'cp737': {ur'language':ur'Greek'},
ur'cp775': {ur'alias':ur'IBM775',ur'language':ur'Baltic languages'},
ur'cp850': {ur'alias':ur'850, IBM850',ur'language':ur'Western Europe'},
ur'cp852': {ur'alias':ur'852, IBM852',ur'language':ur'Central and Eastern Europe'},
ur'cp855': {ur'alias':ur'855, IBM855',ur'language':ur'Bulgarian, Byelorussian, Macedonian, Russian, Serbian'},
ur'cp856': {ur'language':ur'Hebrew'},
ur'cp857': {ur'alias':ur'857, IBM857',ur'language':ur'Turkish'},
ur'cp860': {ur'alias':ur'860, IBM860',ur'language':ur'Portuguese'},
ur'cp861': {ur'alias':ur'861, CP-IS, IBM861',ur'language':ur'Icelandic'},
ur'cp862': {ur'alias':ur'862, IBM862',ur'language':ur'Hebrew'},
ur'cp863': {ur'alias':ur'863, IBM863',ur'language':ur'Canadian'},
ur'cp864': {ur'alias':ur'IBM864',ur'language':ur'Arabic'},
ur'cp865': {ur'alias':ur'865, IBM865',ur'language':ur'Danish, Norwegian'},
ur'cp866': {ur'alias':ur'866, IBM866',ur'language':ur'Russian'},
ur'cp869': {ur'alias':ur'869, CP-GR, IBM869',ur'language':ur'Greek'},
ur'cp874': {ur'language':ur'Thai'},
ur'cp875': {ur'language':ur'Greek'},
ur'cp932': {ur'alias':ur'932, ms932, mskanji, ms-kanji',ur'language':ur'Japanese'},
ur'cp949': {ur'alias':ur'949, ms949, uhc',ur'language':ur'Korean'},
ur'cp950': {ur'alias':ur'950, ms950',ur'language':ur'Traditional Chinese'},
ur'cp1006': {ur'language':ur'Urdu'},
ur'cp1026': {ur'alias':ur'ibm1026',ur'language':ur'Turkish'},
ur'cp1140': {ur'alias':ur'ibm1140',ur'language':ur'Western Europe'},
ur'cp1250': {ur'alias':ur'windows-1250',ur'language':ur'Central and Eastern Europe'},
ur'cp1251': {ur'alias':ur'windows-1251',ur'language':ur'Bulgarian, Byelorussian, Macedonian, Russian, Serbian'},
ur'cp1252': {ur'alias':ur'windows-1252',ur'language':ur'Western Europe'},
ur'cp1253': {ur'alias':ur'windows-1253',ur'language':ur'Greek'},
ur'cp1254': {ur'alias':ur'windows-1254',ur'language':ur'Turkish'},
ur'cp1255': {ur'alias':ur'windows-1255',ur'language':ur'Hebrew'},
ur'cp1256': {ur'alias':ur'windows1256',ur'language':ur'Arabic'},
ur'cp1257': {ur'alias':ur'windows-1257',ur'language':ur'Baltic languages'},
ur'cp1258': {ur'alias':ur'windows-1258',ur'language':ur'Vietnamese'},
ur'euc_jp': {ur'alias':ur'eucjp, ujis, u-jis',ur'language':ur'Japanese'},
ur'euc_jis_2004': {ur'alias':ur'jisx0213, eucjis2004',ur'language':ur'Japanese'},
ur'euc_jisx0213': {ur'alias':ur'eucjisx0213',ur'language':ur'Japanese'},
ur'euc_kr': {ur'alias':ur'euckr, korean, ksc5601, ks_c-5601, ks_c-5601-1987, ksx1001, ks_x-1001',ur'language':ur'Korean'},
ur'gb2312': {ur'alias':ur'chinese, csiso58gb231280, euc-cn, euccn, eucgb2312-cn, gb2312-1980, gb2312-80, iso-ir-58',ur'language':ur'Simplified Chinese'},
ur'gbk': {ur'alias':ur'936, cp936, ms936',ur'language':ur'Unified Chinese'},
ur'gb18030': {ur'alias':ur'gb18030-2000',ur'language':ur'Unified Chinese'},
ur'hz': {ur'alias':ur'hzgb, hz-gb, hz-gb-2312',ur'language':ur'Simplified Chinese'},
ur'iso2022_jp': {ur'alias':ur'csiso2022jp, iso2022jp, iso-2022-jp',ur'language':ur'Japanese'},
ur'iso2022_jp_1': {ur'alias':ur'iso2022jp-1, iso-2022-jp-1',ur'language':ur'Japanese'},
ur'iso2022_jp_2': {ur'alias':ur'iso2022jp-2, iso-2022-jp-2',ur'language':ur'Japanese, Korean, Simplified Chinese, Western Europe, Greek'},
ur'iso2022_jp_2004': {ur'alias':ur'iso2022jp-2004, iso-2022-jp-2004',ur'language':ur'Japanese'},
ur'iso2022_jp_3': {ur'alias':ur'iso2022jp-3, iso-2022-jp-3',ur'language':ur'Japanese'},
ur'iso2022_jp_ext': {ur'alias':ur'iso2022jp-ext, iso-2022-jp-ext',ur'language':ur'Japanese'},
ur'iso2022_kr': {ur'alias':ur'csiso2022kr, iso2022kr, iso-2022-kr',ur'language':ur'Korean'},
ur'latin_1': {ur'alias':ur'iso-8859-1, iso8859-1, 8859, cp819, latin, latin1, L1',ur'language':ur'West Europe'},
ur'iso8859_2': {ur'alias':ur'iso-8859-2, latin2, L2',ur'language':ur'Central and Eastern Europe'},
ur'iso8859_3': {ur'alias':ur'iso-8859-3, latin3, L3',ur'language':ur'Esperanto, Maltese'},
ur'iso8859_4': {ur'alias':ur'iso-8859-4, latin4, L4',ur'language':ur'Baltic languagues'},
ur'iso8859_5': {ur'alias':ur'iso-8859-5, cyrillic',ur'language':ur'Bulgarian, Byelorussian, Macedonian, Russian, Serbian'},
ur'iso8859_6': {ur'alias':ur'iso-8859-6, arabic',ur'language':ur'Arabic'},
ur'iso8859_7': {ur'alias':ur'iso-8859-7, greek, greek8',ur'language':ur'Greek'},
ur'iso8859_8': {ur'alias':ur'iso-8859-8, hebrew',ur'language':ur'Hebrew'},
ur'iso8859_9': {ur'alias':ur'iso-8859-9, latin5, L5',ur'language':ur'Turkish'},
ur'iso8859_10': {ur'alias':ur'iso-8859-10, latin6, L6',ur'language':ur'Nordic languages'},
ur'iso8859_13': {ur'alias':ur'iso-8859-13',ur'language':ur'Baltic languages'},
ur'iso8859_14': {ur'alias':ur'iso-8859-14, latin8, L8',ur'language':ur'Celtic languages'},
ur'iso8859_15': {ur'alias':ur'iso-8859-15',ur'language':ur'Western Europe'},
ur'johab': {ur'alias':ur'cp1361, ms1361',ur'language':ur'Korean'},
ur'koi8_r': {ur'language':ur'Russian'},
ur'koi8_u': {ur'language':ur'Ukrainian'},
ur'mac_cyrillic': {ur'alias':ur'maccyrillic',ur'language':ur'Bulgarian, Byelorussian, Macedonian, Russian, Serbian'},
ur'mac_greek': {ur'alias':ur'macgreek',ur'language':ur'Greek'},
ur'mac_iceland': {ur'alias':ur'maciceland',ur'language':ur'Icelandic'},
ur'mac_latin2': {ur'alias':ur'maclatin2, maccentraleurope',ur'language':ur'Central and Eastern Europe'},
ur'mac_roman': {ur'alias':ur'macroman',ur'language':ur'Western Europe'},
ur'mac_turkish': {ur'alias':ur'macturkish',ur'language':ur'Turkish'},
ur'ptcp154': {ur'alias':ur'csptcp154, pt154, cp154, cyrillic-asian',ur'language':ur'Kazakh'},
ur'shift_jis': {ur'alias':ur'csshiftjis, shiftjis, sjis, s_jis',ur'language':ur'Japanese'},
ur'shift_jis_2004': {ur'alias':ur'shiftjis2004, sjis_2004, sjis2004',ur'language':ur'Japanese'},
ur'shift_jisx0213': {ur'alias':ur'shiftjisx0213, sjisx0213, s_jisx0213',ur'language':ur'Japanese'},
ur'utf_16': {ur'alias':ur'U16, utf16',ur'language':ur'all'},
ur'utf_16_be': {ur'alias':ur'UTF-16BE',ur'language':ur'all (BMP only)'},
ur'utf_16_le': {ur'alias':ur'UTF-16LE',ur'language':ur'all (BMP only)'},
ur'utf_7': {ur'alias':ur'U7, unicode-1-1-utf-7',ur'language':ur'all'},
ur'utf_8': {ur'alias':ur'U8, UTF, utf8',ur'language':ur'all'},
ur'utf_8_sig': {ur'language':ur'all'},
# Specials
ur'idna': {ur'description':ur'Implements RFC 3490.'},
ur'palmos': {ur'description':ur'Encoding of PalmOS 3.5'},
ur'punycode': {ur'description':ur'RFC 3492'},
ur'raw_unicode_escape': {ur'description':ur'Produce a string that is suitable as raw Unicode literal in source code'},
ur'rot_13': {ur'alias':ur'rot13',ur'description':ur'Returns the Caesar-cypher encryption of the operand'},
ur'unicode_escape': {ur'description':ur'Produce a string that is suitable as Unicode literal in source code'},
ur'unicode_internal': {ur'description':ur'Return the internal representation of the operand'},
}
'''Available character encodings.
'''

import codecs
for k in charsets.keys():
  try:
    codecs.lookup(k)
  except LookupError:
    del charsets[k]
del k
########NEW FILE########
__FILENAME__ = config
# encoding: utf-8
'''User configuration.
'''
import sys, os, logging, glob, codecs, re
import logging.handlers
from smisk.util.collections import merge_dict
log = logging.getLogger(__name__)

__all__ = ['config', 'config_locations', 'Configuration',
           'configure_logging', 'LOGGING_FORMAT']

# setup check_dirs
if sys.platform == 'win32':
  from win32com.shell import shell, shellcon
  sysconfdir = shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_APPDATA)
else:
  sysconfdir = '/etc'

config_locations = [os.path.join(sysconfdir, 'default'), sysconfdir]
'''Default directories in which to look for configurations files, effective
when using Configuration.load().
'''

GLOB_RE = re.compile(r'.*(?:[\*\?]|\[[^\]]+\]).*')
'''For checking if a string might be a glob pattern.
'''
# *	matches everything
# ?	matches any single character
# [seq]	matches any character in seq
# [!seq]

def _strip_comments(s):
  while 1:
    a = s.find('/*')
    if a == -1:
      break
    b = s.find('*/', a+2)
    if b == -1:
      break
    s = s[:a] + s[b+2:]
  return s

def _preprocess_input(s):
  s = s.strip()
  if s:
    s = _strip_comments(s)
    if s and s[0] != '{':
      s = '{' + s + '}'
  return s


class Configuration(dict):
  '''Configuration dictionary.
  '''
  
  sources = []
  '''Ordered list of sources used to create this dict.
  '''
  
  default_symbols = {
    'true': True, 'false': False,
    'null': None
  }
  
  filename_ext = '.conf'
  '''Filename extension of configuration files
  '''
  
  logging_key = 'logging'
  '''Name of logging key
  '''
  
  input_encoding = 'utf-8'
  '''Character encoding used for reading configuration files.
  '''
  
  max_include_depth = 7
  '''How deep to search for (and load) files from @include or @inherit.
  Set to 0 to disable includes.
  '''
  
  for k in 'CRITICAL FATAL ERROR WARN WARNING INFO NOTSET DEBUG'.split():
    v = getattr(logging, k)
    default_symbols[k] = v
    default_symbols[k.lower()] = v
  
  def __init__(self, *args, **defaults):
    dict.__init__(self, *args, **defaults)
    self.sources = []
    self.filters = []
    self._defaults = defaults
    self._include_depth = 0
  
  def _get_defaults(self):
    return self._defaults
  
  def _set_defaults(self, d):
    if not isinstance(d, dict):
      raise TypeError('defaults must be a dict')
    self._defaults = d
    self.reload()
  
  defaults = property(_get_defaults, _set_defaults, 'Default values')
  
  def set_default(self, k, v):
    self._defaults[k] = v
    self.reload()
  
  def g(self, *keys, **kw):
    v = self
    default = kw.get('default', None)
    try:
      for k in keys:
        v = v[k]
      return v
    except KeyError:
      return default
  
  def __call__(self, name, defaults=None, locations=[], symbols={}, logging_key=None):
    '''Load configuration files from a series of pre-defined locations.
    Returns a list of files that was loaded.
    
      /etc/default/<name>.conf
      /etc/<name>.conf
      /etc/<name>/<name>.conf
      ./<name>.conf
      ./<name>-user.conf
      ~/<name>.conf
    '''
    log.info('loading named configuration %r', name)
    if isinstance(defaults, dict):
      self.defaults = defaults
    fn = name+self.filename_ext
    paths = []
    files_loaded = []
    for dirname in config_locations:
      paths.append(os.path.join(dirname, fn))
    if sysconfdir in config_locations:
      # /etc/<name>/<name>.conf
      paths.append(os.path.join(sysconfdir, name, fn))
    paths.extend([
      os.path.join('.', fn),
      os.path.join('.', name+'-user'+self.filename_ext),
      os.path.join(os.path.expanduser('~'), fn),
    ])
    if locations:
      for dirname in locations:
        paths.append(os.path.join(dirname, fn))
    for path in paths:
      log.debug('load: trying %s', path)
      if os.path.isfile(path):
        self.load(path, symbols, post_process=False)
        files_loaded.append(path)
    if logging_key is not None:
      self.logging_key = logging_key
    if files_loaded:
      self._post_process()
    else:
      logging.basicConfig()
      log.warn('no configuration named %r was found', name)
    return files_loaded
  
  def load(self, path, symbols={}, post_process=True):
    '''Load configuration from file denoted by *path*.
    Returns the dict loaded.
    '''
    load_key = path
    f = codecs.open(path, 'r', encoding=self.input_encoding, errors='strict')
    try:
      conf, includes, inherit = self._loads(load_key, f.read(), symbols)
    finally:
      f.close()
    if conf or includes:
      if self.max_include_depth > 0 and includes:
        self._handle_includes(path, includes, symbols)
        if inherit:
          self._apply_loads(conf, load_key)
      if post_process:
        self._post_process()
    return conf
  
  def loads(self, string, symbols={}, post_process=True):
    '''Load configuration from string.
    Returns the dict loaded.
    '''
    load_key = '<string#0x%x>' % hash(string)
    conf, includes, inherit = self._loads(load_key, string, symbols)
    if post_process:
      self._post_process()
    return conf
  
  def reload(self):
    '''Reload configuration
    '''
    log.info('reloading configuration')
    reload_paths = []
    self.clear()
    self.update(self._defaults)
    for k,conf in self.sources:
      log.debug('reloading: applying %r', k)
      if k[0] == '<':
        # initially loaded from a string
        self.update(conf)
      else:
        self.load(k, post_process=False)
    self._post_process()
    log.info('reloaded configuration')
  
  def update(self, b):
    log.debug('update: merging %r --into--> %r', b, self)
    merge_dict(self, b, merge_lists=False)
  
  def reset(self, reset_defaults=True):
    self.clear()
    self.sources = []
    self.filters = []
    if reset_defaults:
      self._defaults = {}
  
  def add_filter(self, filter):
    '''Add a filter
    '''
    if filter not in self.filters:
      self.filters.append(filter)
  
  def apply_filters(self):
    '''Apply filters.
    '''
    if self.filters:
      log.debug('applying filters %r', self.filters)
      for filter in self.filters:
        filter(self)
  
  def _handle_includes(self, source_path, includes, symbols):
    '''Loads any files (possibly glob'ed) denoted by the key @include.
    Returns a list of paths included.
    '''
    try:
      self._include_depth += 1
      if self._include_depth > self.max_include_depth:
        raise RuntimeError('maximum include depth exceeded')
      if isinstance(includes, tuple):
        includes = list(includes)
      elif not isinstance(includes, list):
        includes = [includes]
      dirname = os.path.dirname(source_path)
      # preprocess paths
      v = includes
      includes = []
      for path in v:
        if not path:
          continue
        # note: not windows-safe
        if path[0] != '/':
          path = os.path.join(dirname, path)
        if GLOB_RE.match(path):
          v = glob.glob(path)
          log.debug('include/inherit: expanding glob pattern %r --> %r', path, v)
          if v:
            v.sort()
            includes.extend(v)
        else:
          includes.append(path)
      # load paths
      for path in includes:
        log.debug('include/inherit: loading %r', path)
        self.load(path, symbols, post_process=False)
      return includes
    finally:
      self._include_depth -= 1
  
  def _post_process(self):
    if self.logging_key:
      log.debug('post processing: looking for logging key %r', self.logging_key)
      self._configure_logging()
    self.apply_filters()
    log.info('active configuration: %r', self)
  
  def _configure_logging(self):
    try:
      conf = self[self.logging_key]
      if not isinstance(conf, dict):
        log.warn('logging configuration exists but is not a dict -- skipping')
        return
    except KeyError:
      log.debug('no logging configuration found')
      return
    log.debug('using logging configuration %r', conf)
    configure_logging(conf)
  
  def _loads(self, load_key, string, symbols):
    conf = None
    includes = None
    inherit = False
    load_key = intern(load_key)
    syms = self.default_symbols.copy()
    syms.update(symbols)
    string = _preprocess_input(string)
    if string:
      log.info('loading %s', load_key)
      try:
        conf = eval(compile(string, load_key, 'eval'), syms)
      except SyntaxError, e:
        e.args = (str(e), e.args[1])
        raise e
      if not isinstance(conf, dict):
        raise TypeError('configuration %r does not represent a dictionary' % path)
      if conf:
        includes = conf.get('@include')
        if includes is None:
          includes = conf.get('@inherit')
          if includes is not None:
            inherit = True
            del conf['@inherit'] # or else reload() will mess things up
        else:
          del conf['@include'] # or else reload() will mess things up
        if includes is not None:
          if load_key[0] == '<':
            # when loading a string, simply remove include key
            includes = None
        if includes is None or not inherit:
          # only _apply_loads if no includes, since includes need to be
          # applied prior to _apply_loads (in order to have the includes
          # act as a base config rather than a dominant config)
          self._apply_loads(conf, load_key)
    if conf is None:
      log.debug('skipping empty configuration %s', load_key)
    return conf, includes, inherit
  
  def _apply_loads(self, conf, load_key):
    self.update(conf)
    try:
      for i,v in enumerate(self.sources):
        if v[0] == load_key:
          self.sources[i] = (load_key, conf)
          raise NotImplementedError() # trick
      self.sources.append((load_key, conf))
    except NotImplementedError:
      pass
  

config = Configuration()



#---------------------------------------------------------------------------
# Logging configuration routines

LOGGING_DATEFMT = '%Y-%m-%d %H:%M:%S'
LOGGING_FORMAT = '%(asctime)s.%(msecs)03d [%(process)d] %(name)s %(levelname)s: %(message)s'

def configure_logging(conf):
  '''Configure the logging module based on *conf*.
  '''
  setup_root = len(logging.root.handlers) == 0
  # critical section
  logging._acquireLock()
  try:
    if setup_root or 'filename' in conf or 'stream' in conf or 'format' in conf or 'datefmt' in conf:
      _configure_logging_root_handlers(conf)
      _configure_logging_root_formatter(conf)
    if 'levels' in conf:
      _configure_logging_levels(conf['levels'])
  finally:
    logging._releaseLock()

def _configure_logging_root_handlers(conf):
  logging.root.handlers = []
  
  if 'filename' in conf and conf['filename']:
    # Add a file handler
    handler = logging.FileHandler(conf['filename'], conf.get('filemode', 'a'))
    logging.root.handlers.append(handler)
  
  if 'syslog' in conf and conf['syslog']:
    # Add a syslog handler
    syslog = conf['syslog']
    params = {}
    if isinstance(syslog, dict):
      if 'host' in syslog or 'port' in syslog:
        params['address'] = (syslog.get('host', 'localhost'), int(syslog.get('port', 514)))
      elif 'socket' in syslog:
        params['address'] = syslog['socket']
      if 'facility' in syslog:
        params['facility'] = syslog['facility']
    handler = logging.handlers.SysLogHandler(**params)
    logging.root.handlers.append(handler)
  
  if 'stream' in conf and conf['stream']:
    # Add a stream handler (default)
    stream = conf['stream']
    if not hasattr(stream, 'write'):
      # Will raise KeyError for anything else than the two allowed streams
      stream = {'stdout':sys.stdout, 'stderr':sys.stderr}[stream]
    handler = logging.StreamHandler(stream)
    logging.root.handlers.append(handler)
  
  if not logging.root.handlers:
    # Add a default (stream) handler if no handlers was explicitly specified.
    handler = logging.StreamHandler(sys.stderr)
    logging.root.handlers.append(handler)

def _configure_logging_root_formatter(conf):
  for handler in logging.root.handlers:
    format = conf.get('format', LOGGING_FORMAT)
    datefmt = conf.get('datefmt', LOGGING_DATEFMT)
    handler.setFormatter(logging.Formatter(format, datefmt))

def _configure_logging_levels(levels):
  # reset all loggers level to NOTSET
  for name, logger in logging.Logger.manager.loggerDict.items():
    try:
      logger.setLevel(logging.NOTSET)
    except AttributeError:
      pass
  # assign new levels to specified loggers
  for logger_name, level_name in levels.items():
    if isinstance(level_name, int):
      level = level_name
    else:
      level = logging.getLevelName(level_name.upper())
      if not isinstance(level, int):
        log.warn('unknown logging level %r for logger %r -- skipping', level_name, logger_name)
        continue
    logging.getLogger(logger_name).setLevel(level)


if __name__ == '__main__':
  a = '''
  'logging': {'levels':{'':DEBUG}}
  '''
  b = '''
  "some_key": 456,
  "logging": { /* js comment 1 */
    'format': '%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    'datefmt': '%H:%M:%S',
    /*
     * js comment 2
     */
    'levels': {
      '': 'INFO',
    }
  }
  '''
  config('config')
  config.loads(a)
  config.loads(b)
  config.reload()

########NEW FILE########
__FILENAME__ = en
#!/usr/bin/env python
# encoding: utf-8
'''English
'''
import re
from smisk.inflection import Inflector

__all__ = ['inflection']

inflection = Inflector('en', 'en_EN', 'eng')

inflection.plural(re.compile(ur"$"), u's')
inflection.plural(re.compile(ur"s$", re.I), u's')
inflection.plural(re.compile(ur"(ax|test)is$", re.I), ur'\1es')
inflection.plural(re.compile(ur"(octop|vir)us$", re.I), ur'\1i')
inflection.plural(re.compile(ur"(alias|status)$", re.I), ur'\1es')
inflection.plural(re.compile(ur"(bu)s$", re.I), ur'\1ses')
inflection.plural(re.compile(ur"(buffal|tomat)o$", re.I), ur'\1oes')
inflection.plural(re.compile(ur"([ti])um$", re.I), ur'\1a')
inflection.plural(re.compile(ur"sis$", re.I), u'ses')
inflection.plural(re.compile(ur"(?:([^f])fe|([lr])f)$", re.I), ur'\1\2ves')
inflection.plural(re.compile(ur"(hive)$", re.I), ur'\1s')
inflection.plural(re.compile(ur"([^aeiouy]|qu)y$", re.I), ur'\1ies')
inflection.plural(re.compile(ur"(x|ch|ss|sh)$", re.I), ur'\1es')
inflection.plural(re.compile(ur"(matr|vert|ind)(?:ix|ex)$", re.I), ur'\1ices')
inflection.plural(re.compile(ur"([m|l])ouse$", re.I), ur'\1ice')
inflection.plural(re.compile(ur"^(ox)$", re.I), ur'\1en')
inflection.plural(re.compile(ur"(quiz)$", re.I), ur'\1zes')

inflection.singular(re.compile(ur"s$", re.I), u'')
inflection.singular(re.compile(ur"(n)ews$", re.I), ur'\1ews')
inflection.singular(re.compile(ur"([ti])a$", re.I), ur'\1um')
inflection.singular(re.compile(ur"((a)naly|(b)a|(d)iagno|(p)arenthe|(p)rogno|(s)ynop|(t)he)ses$", re.I), ur'\1\2sis')
inflection.singular(re.compile(ur"(^analy)ses$", re.I), ur'\1sis')
inflection.singular(re.compile(ur"([^f])ves$", re.I), ur'\1fe')
inflection.singular(re.compile(ur"(hive)s$", re.I), ur'\1')
inflection.singular(re.compile(ur"(tive)s$", re.I), ur'\1')
inflection.singular(re.compile(ur"([lr])ves$", re.I), ur'\1f')
inflection.singular(re.compile(ur"([^aeiouy]|qu)ies$", re.I), ur'\1y')
inflection.singular(re.compile(ur"(s)eries$", re.I), ur'\1eries')
inflection.singular(re.compile(ur"(m)ovies$", re.I), ur'\1ovie')
inflection.singular(re.compile(ur"(x|ch|ss|sh)es$", re.I), ur'\1')
inflection.singular(re.compile(ur"([m|l])ice$", re.I), ur'\1ouse')
inflection.singular(re.compile(ur"(bus)es$", re.I), ur'\1')
inflection.singular(re.compile(ur"(o)es$", re.I), ur'\1')
inflection.singular(re.compile(ur"(shoe)s$", re.I), ur'\1')
inflection.singular(re.compile(ur"(cris|ax|test)es$", re.I), ur'\1is')
inflection.singular(re.compile(ur"(octop|vir)i$", re.I), ur'\1us')
inflection.singular(re.compile(ur"(alias|status)es$", re.I), ur'\1')
inflection.singular(re.compile(ur"^(ox)en", re.I), ur'\1')
inflection.singular(re.compile(ur"(vert|ind)ices$", re.I), ur'\1ex')
inflection.singular(re.compile(ur"(matr)ices$", re.I), ur'\1ix')
inflection.singular(re.compile(ur"(quiz)zes$", re.I), ur'\1')

inflection.irregular(u'person', u'people')
inflection.irregular(u'man', u'men')
inflection.irregular(u'child', u'children')
inflection.irregular(u'sex', u'sexes')
inflection.irregular(u'move', u'moves')

inflection.uncountable(u'equipment',u'information',u'rice',u'money',u'species',u'series',
u'fish',u'sheep',u'commotion')

########NEW FILE########
__FILENAME__ = sv
#!/usr/bin/env python
# encoding: utf-8
'''Swedish
'''

import re
from smisk.inflection import Inflector

__all__ = ['inflection']

class SVInflector(Inflector):
  def ordinalize(self, number):
    i = int(number)
    if i % 10 in [1,2]:
      return u"%d:a" % i
    else:
      return u"%d:e" % i
  

def rc(pat, ignore_case=1):
  if ignore_case:
    return re.compile(pat, re.I)
  else:
    return re.compile(pat)

# Rules based on http://en.wiktionary.org/wiki/Wiktionary:Swedish_inflection_templates
inflection = SVInflector('sv', 'sv_SV')

inflection.regular(ur"$", 'a', ur"a$") # svensk -a, vanlig -a, stor -a
inflection.regular(ur'a$', ur'our', ur'or$', ur'a') # kvinn a-or, mors a-or, flick a-or
inflection.regular(ur"e$", 'aur', ur"ar$", ur'e') # ...
inflection.regular(ur"([st]t|o?n)$", ur'\1eur', ur"er$") # katt -er, ven -er, person -er
inflection.regular(ur"(ng|il|åt)$", ur'\1aur', ur"ar$") # peng -ar, bil -ar, båt -ar
inflection.regular(ur"(um)$", ur'\1ma', ur"ma$") # stum -ma, dum -ma
inflection.regular(ur"(un)$", ur'\1naur', ur"nar$") # mun -nar
inflection.regular(ur"(ud)$", ur'\1en', ur"en$") # huvud -en
inflection.regular(ur"(ne)$", ur'\1n', ur"(ne)n$", ur'\1') # vittne -n
inflection.regular(ur"(iv)en$", ur'\1na', ur"(iv)na$", ur'\1en') # giv en-na
inflection.regular(ur"(os)$", ur'\1our', ur"(os)or$", ur'\1') # ros -or
inflection.regular(ur"us$", ur'öss', ur"öss$", ur'us') # l us-öss, m us-öss
inflection.regular(ur"and$", ur'ändeur', ur"änder$", ur'and') # h and-änder, l and-änder
inflection.regular(ur"(k)el$", ur'\1laur', ur"(k)lar$", ur'\1el') # snork el-lar

inflection.irregular(u'manu', u'mänu')
inflection.irregular(u'faderu', u'fädraru')
inflection.irregular(u'moderu', u'mödraru')
inflection.irregular(u'lustu', u'lustaru')
inflection.irregular(u'pojku', u'pojkaru')
inflection.irregular(u'pojkeu', u'pojkaru')
inflection.irregular(u'usu', u'össu', False) # l us-öss, m us-öss
inflection.irregular(u'andu', u'änderu', False) # h and-änder, l and-änder, str and-änder
inflection.irregular(u'kornu', u'kornu') # riskorn, majskorn, korn, etc...
inflection.irregular(u'litenu', u'småu', False)

inflection.uncountable(u'folku',u'risu',u'fåru',u'sexu',u'lokomotivu',u'loku',u'rumu',
u'barnu',u'förtjusandeu',u'brevu',u'husu',u'giftu')

if __name__ == '__main__':
  import unittest
  from smisk.test.inflection import Swedish
  unittest.TextTestRunner().run(unittest.makeSuite(Swedish))

########NEW FILE########
__FILENAME__ = bsddb
# encoding: utf-8
import os, atexit, shutil
from smisk.util._bsddb import db, dbshelve
from smisk.util.cache import app_shared_key
from tempfile import gettempdir

_dicts = {}

def shared_dict(filename=None, homedir=None, name=None, mode=0600, dbenv=None, 
								type=db.DB_HASH, flags=db.DB_CREATE, persistent=False):
	orig_name = name
	is_tempdir = False
	
	if filename:
		filename = os.path.abspath(filename)
		homedir = os.path.dirname(filename)
		name = os.path.basename(filename)
	else:
		if name is None:
			name = app_shared_key()
		if homedir is None:
			is_tempdir = True
			homedir = os.path.join(gettempdir(), '%s.ipc' % name)
		filename = os.path.abspath(os.path.join(homedir, name))
	
	try:
		return _dicts[filename]
	except KeyError:
		pass
	
	if not persistent and os.path.isdir(homedir):
		try:
			shutil.rmtree(homedir, True)
			os.mkdir(homedir)
		except:
			pass
	
	if not os.path.isdir(homedir):
		if os.path.exists(homedir):
			os.remove(homedir)
		os.mkdir(homedir)	# if this fail w errno 17, the homedir or it's parent is not writeable
	
	if not dbenv:
		dbenv = db.DBEnv()
		dbenv.open(homedir, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_CDB)
	
	d = DBDict(dbenv, sync=persistent)
	d.open(filename, name, type, flags, mode)
	_dicts[filename] = d
	
	if not persistent and is_tempdir:
		atexit.register(shutil.rmtree, homedir, True)
	
	return d


class DBDict(dbshelve.DBShelf):
	def __init__(self, dbenv, sync=False, *va, **kw):
		dbshelve.DBShelf.__init__(self, dbenv, *va, **kw)
		self.sync = sync
		self._closed = True
	
	def __del__(self):
		self.close()
		dbshelve.DBShelf.__del__(self)
	
	def open(self, *args, **kwargs):
		self.db.open(*args, **kwargs)
		self._closed = False
	
	def close(self, *args, **kwargs):
		try:
			if self.sync:
				self.db.sync()
			self.db.close(*args, **kwargs)
		except db.DBError:
			pass
		self._closed = True
	

########NEW FILE########
__FILENAME__ = memcached
# encoding: utf-8
try:
  import cmemcached as memcache
except ImportError:
  try:
    import memcache
  except ImportError:
    raise ImportError('neither cmemcached nor memcache module is available')

from smisk.util.cache import app_shared_key
from smisk.util.type import MutableMapping
from smisk.core import object_hash

_dicts = {}

def shared_dict(name=None, nodes=['127.0.0.1:11211'], memcached_debug=0):
  '''Shared memcached-based dictionary.
  '''
  if name is None:
    name = app_shared_key()
  name = str(name)
  dicts_ck = name + str(object_hash(nodes))
  try:
    return _dicts[dicts_ck]
  except KeyError:
    pass
  client = memcache.Client(nodes, debug=memcached_debug)
  d = MCDict(client, name)
  _dicts[dicts_ck] = d
  return d


class MCDict(dict, MutableMapping):
  def __init__(self, client, key_prefix=None):
    self.client = client
    self.key_prefix = str(key_prefix)
  
  def __getitem__(self, key):
    key = str(key)
    if self.key_prefix:
      key = self.key_prefix + key
    obj = self.client.get(key)
    if obj is None:
      raise KeyError(key)
    return obj
  
  def __contains__(self, key):
    key = str(key)
    if self.key_prefix:
      key = self.key_prefix + key
    if self.client.get(key):
      return True
    return False
  
  def __setitem__(self, key, value):
    key = str(key)
    if self.key_prefix:
      key = self.key_prefix + key
    self.client.set(key, value)
  
  def __delitem__(self, key):
    key = str(key)
    if self.key_prefix:
      key = self.key_prefix + key
    self.client.delete(key)
  
  def __len__(self): raise NotImplementedError('__len__')
  def __iter__(self): raise NotImplementedError('__iter__')
  def keys(self): raise NotImplementedError('keys')
  def items(self): raise NotImplementedError('items')
  def iteritems(self): raise NotImplementedError('iteritems')
  def values(self): raise NotImplementedError('values')
  
  def __repr__(self):
    return '<%s.%s @ 0x%x %s>' % (
      self.__module__, self.__class__.__name__, id(self), self.client)
  

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/env python
# encoding: utf-8
'''Interactive console aiding in development and management.

Start the console by importing and running its `main()` from a file in your
application top module::

  #!/usr/bin/env python
  from smisk.mvc.console import main
  if __name__ == '__main__':
    main()

The console can also be run directly from the module::

  python -m smisk.mvc.console

'''

import sys, os, time, logging, __builtin__
import code, readline, atexit
from smisk.release import version
from smisk.core import *
from smisk.mvc.control import *
from smisk.mvc.model import *
from smisk.util.python import format_exc
from smisk.util.introspect import introspect
from smisk.util.type import *

class Console(code.InteractiveConsole):
  def __init__(self, locals=None, filename="<console>",
               histfile=os.path.expanduser("~/.console-history")):
    code.InteractiveConsole.__init__(self, locals=locals, filename=filename)
    self.init_history(histfile)
  
  def init_history(self, histfile):
    try:
      import rlcompleter
      readline.parse_and_bind("tab: complete")
      if hasattr(readline, "read_history_file"):
        try:
          readline.read_history_file(histfile)
        except:
          pass
        atexit.register(self.save_history, histfile)
    except ImportError:
      log.info("readline not available")
  
  def save_history(self, histfile):
    readline.set_history_length(1000)
    readline.write_history_file(histfile)
  


def export(obj):
  '''Export members of obj to __builtin__ global namespace
  '''
  if not obj:
    return
  if isinstance(obj, DictType):
    for k,v in obj.items():
      try:
        setattr(__builtin__, k, v)
      except:
        pass
  else:
    for k in dir(obj):
      try:
        setattr(__builtin__, k, getattr(obj, k))
      except:
        pass


def main(app=None,
         chdir=None,
         appdir=None,
         log_format='\033[1;33m%(levelname)-8s \033[1;31m%(name)-20s\033[0m %(message)s',
         intro_eval=None,
         *args, **kwargs):
  '''Console entry point.
  
  Excessive arguments and keyword arguments are passed to `mvc.Application.__init__()`.
  If `app` is already an instance, these extra arguments and keyword arguments
  have no effect.
  
  :Parameters:
    app : Application
      An application type or instance.
    appdir : string
      Application directory. If not defined and running this module directly, the
      current working directory will be used. If not defined and calling this function
      from another module, ``dirname(<__main__ module>.__file__)`` will be used.
    log_format : string
      Custom logging format.
  :rtype: None
  '''
  appdir_defaults_to = ''
  
  if appdir:
    appdir_defaults_to = ' Defaults to "%s".' % appdir
  
  from optparse import OptionParser
  parser = OptionParser(usage="usage: %prog [options]")
  
  parser.add_option("-d", "--appdir",
                    dest="appdir",
                    help='Set the application directory.%s' % appdir_defaults_to,
                    action="store",
                    type="string",
                    metavar="PATH",
                    default=appdir)
  
  parser.add_option("-e", "--environment",
                    dest="environment",
                    help='Set the SMISK_ENVIRONMENT environment variable.',
                    action="store",
                    type="string",
                    metavar="VALUE",
                    default=None)
  
  opts, args = parser.parse_args()
  
  if opts.environment:
    os.environ['SMISK_ENVIRONMENT'] = opts.environment
  
  appdir = opts.appdir
  
  if appdir is None:
    if 'SMISK_APP_DIR' in os.environ and os.environ['SMISK_APP_DIR']:
      appdir = os.environ['SMISK_APP_DIR']
    else:
      if __name__ == '__main__':
        appdir = os.getcwd()
      else:
        appdir = os.path.dirname(sys.modules['__main__'].__file__)
      appdir = os.path.abspath(appdir)
  appname = os.path.basename(appdir)
  
  # Load application
  if root_controller() is None:
    try:
      try:
        sys.path[0:0] = [os.path.dirname(appdir)]
        m = __import__(appname, globals(), {}, ['*'])
        for k in dir(m):
          try:
            setattr(__builtin__, k, getattr(m, k))
          except:
            pass
      except ImportError, e:
        raise EnvironmentError('Unable to automatically load application. Try to load it '\
          'yourself or provide an absolute appdir with your call to console.main(): %s' %\
          format_exc(as_string=1))
    finally:
      del sys.path[0]
  
  if chdir:
    os.chdir(chdir)
  
  try:
    from smisk.mvc import setup
    app = setup(app=app, appdir=appdir, log_format=log_format, *args, **kwargs)
    del setup
    del log_format
  except:
    sys.stderr.write(format_exc(as_string=True))
    sys.exit(1)
  
  class _ls(object):
    def __call__(self, obj):
      print introspect.format_members(obj, colorize=True)
    def __repr__(self):
      return introspect.format_members(globals(), colorize=True)
    
  
  class _Helper(object):
    def __repr__(self):
      readline_info = ''
      if readline:
        readline_info = 'Readline is active, thus you can use TAB to '\
          'browse and complete Python statements.'
      return '''Interactive Python console.

Your application has been loaded and set up. You can now interact with any
component. %(readline)s

Examples:

  ls(object)      List all members and values of any object.

  help(something) Display help for something. For example help(re) to read the
                  manual on the Regular Expressions module.

  run([bind])     Starts your application. Note that if you are not binding to
                  an address but try to run the application as if in a FastCGI
                  environment, this will fail (because this is not a FastCGI
                  environment).

  controllers()   List of installed controllers.

  root_controller()
                  The root controller. You can for example ask it for all
                  available methods by typing: root_controller()()._methods()

  uri_for(node)   Return the URI for any node on the controller tree.
  
  

Type help() for interactive help, or help(object) for help about object.
^D to exit the console.''' % {
    'readline':readline_info
  }
    def __call__(self, *args, **kwargs):
      import pydoc
      return pydoc.help(*args, **kwargs)
  
  # Export locals and globals
  for k,v in locals().items():
    setattr(__builtin__, k, v)
  for k,v in globals().items():
    setattr(__builtin__, k, v)
  
  __builtin__.help = _Helper()
  __builtin__.ls = _ls()
  
  histfile = os.path.expanduser(os.path.join('~', '.%s_console_history' % appname))
  console = Console(locals={}, histfile=histfile)
  __builtin__.console = console
  import platform
  console.push("print 'Smisk v%s interactive console. Python v%s'" %\
    (version, platform.python_version()))
  if intro_eval:
    console.push(intro_eval)
  console.interact('')


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = control
# encoding: utf-8
'''Control in MVC – Base Controller and helpers like function-to-URL conversion.
'''
import re, logging, smisk.core
from types import *
from smisk.inflection import inflection
from smisk.util.string import tokenize_path
from smisk.util.python import classmethods
from smisk.util.introspect import introspect
from smisk.util.type import Undefined
from smisk.util.cache import callable_cache_key
from smisk.mvc.decorators import expose
from smisk.mvc import http

__all__ = ['root_controller', 'controllers', 'node_name', 'uri_for', 'path_to', 'template_for', 'method_origin', 'leaf_is_visible', 'Controller', 'enable_reflection']

_root_controller = False
_path_to_cache = {}
_template_for_cache = {}
_uri_for_cache = {}

log = logging.getLogger(__name__)

enable_reflection = True
'''Controls if smisk:-methods and OPTIONS requests are allowed
in order to provide API reflection.
'''

def root_controller():
  '''Returns the root controller.
  
  :rtype: Controller'''
  global _root_controller
  if _root_controller is not False:
    return _root_controller
  for c in Controller.__subclasses__():
    if c.__name__.lower() == 'root':
      _root_controller = c
      return _root_controller


def controllers():
  '''Available controllers as a list, incuding the root.
  
  :returns: List of controller instances in an undefined order.
  :rtype: list
  '''
  root = root_controller()
  if root is None:
    return []
  _controllers = [root()]
  def _r(baseclass, v):
    for subclass in baseclass.__subclasses__():
      v.append(subclass())
      _r(subclass, v)
  _r(root, _controllers)
  return _controllers


def node_name(node):
  '''Name of an exposed node.
  
  :param node:
  :type  node: callable
  :returns: The name of `node` or ``None`` if node is not exposed. Note that
            this function returns the empty string ("") if `node` is the root
            controller.
  :rtype: string
  '''
  path = path_to(node)
  if path is not None:
    try:
      return path_to(node)[-1]
    except IndexError:
      return ''


def uri_for(node):
  '''Returns the canonical exposed URI of a node.
  
  If node is a controller or a __call__, the uri always ends in a slash.
  Otherwise it never ends in a slash. 
  
  :param node:
  :type  node: callable
  :rtype: string
  '''
  cache_key = callable_cache_key(node)
  try:
    return _uri_for_cache[cache_key]
  except KeyError:
    path = path_to(node)
    if path is None:
      uri = None
    else:
      uri = '/'+'/'.join(path)
      if len(path) > 0 and \
        (not isinstance(node, (MethodType, FunctionType)) or node.__name__ == '__call__'):
        uri += '/'
    _uri_for_cache[cache_key] = uri
    return uri


def path_to(node):
  '''Returns the canonical path to node.
  
  :param node: Something on the controller tree. (method, class, instance, etc)
  :type  node: object
  :rtype: list'''
  global _path_to_cache
  return _cached_path_to(callable_cache_key(node), node, _path_to_cache, False)


def template_for(node):
  '''Returns the template uri for node.
  
  :param node: Something on the controller tree. (method, class, instance, etc)
  :type  node: object
  :rtype: list'''
  global _template_for_cache
  return _cached_path_to(callable_cache_key(node), node, _template_for_cache, True)


def method_origin(method):
  '''Return the class on which `method` was originally defined.
  
  .. code-block:: python
  
    >>> from smisk.mvc.control import method_origin
    >>> class Animal(object):
    >>>   def name(self):
    >>>     pass
    >>> 
    >>> class Fish(Animal):
    >>>   def color(self):
    >>>     pass
    >>> 
    >>> o = Fish()
    >>> print method_origin(o.name)
    <class '__main__.Animal'>
    >>> print method_origin(o.color)
    <class '__main__.Fish'>
  
  :param    method:
  :type     method: callable
  :returns: Class on which `method` was originally defined or None if no
            parent could be deduced.
  :rtype:   object
  '''
  try:
    return _method_origin_r(method.im_func, method.im_class)
  except AttributeError:
    return None


def _method_origin_r(func, baseclass):
  for subclass in baseclass.__bases__:
    member = getattr(subclass, func.__name__, None)
    if member is not None and isinstance(member, MethodType) \
        and member.im_func.func_code == func.func_code:
      return _method_origin_r(func, subclass)
  return baseclass


def leaf_is_visible(node, cls=None):
  '''Return True if `node` defined on class `cls` is visible.
  
  :param  cls:
  :type   cls: class
  :param  node:
  :type   node: object
  :rtype: bool
  '''
  if not isinstance(node, (MethodType, FunctionType)):
    try:
      node = node.__call__
    except AttributeError:
      return False
  if getattr(node, 'hidden', False):
    return False
  try:
    delegates = node.delegates
  except AttributeError:
    delegates = False
  if cls is None:
    try: cls = node.im_class
    except AttributeError: pass
  if cls is None:
    if not delegates:
      return False
  elif not delegates:
    origin = method_origin(node)
    if origin is Controller \
        and enable_reflection \
        and cls is root_controller() \
        and node.__name__.startswith('smisk_'):
      # the special methods on the root controller
      return True
    elif origin != cls:
      return False
  return True


# -------------------


def _cached_path_to(cache_key, node, cache, resolve_template):
  try:
    return cache[cache_key]
  except TypeError:
    return None
  except KeyError:
    path = _path_to(node, resolve_template)
    if path:
      if not resolve_template and path[0] == '__call__':
        path = path[1:]
      path.reverse()
    cache[cache_key] = path
    return path


def _node_name(node, fallback):
  '''Name of node
  
  :rtype: unicode
  '''
  try:
    slug = node.slug
    if slug is not None:
      return unicode(slug)
  except AttributeError:
    pass
  return fallback


def _get_template(node):
  tpl = getattr(node, 'template', None)
  if tpl is not None:
    if not isinstance(tpl, list):
      tpl = tokenize_path(str(tpl))
    return tpl


def _path_to(node, resolve_template):
  if isinstance(node, (MethodType, FunctionType)):
    # Leaf is Method or Function.
    from smisk.mvc.routing import _find_canonical_leaf
    node = _find_canonical_leaf(node, node)
    # Function supported because methods might be wrapped in functions
    # which in those cases should have an im_class attribute.
    if getattr(node, 'im_class', None) is None \
        or getattr(node, 'im_func', None) is None \
        or not issubclass(node.im_class, root_controller()):
      return None
    
    if not leaf_is_visible(node):
      return None
    
    if resolve_template:
      tpl = _get_template(node)
      if tpl is not None:
        return tpl
    
    path = [_node_name(node, node.im_func.__name__)]
    path = _path_to_class(node.im_class, path)
  else:
    # Leaf is Class
    if not isinstance(node, TypeType):
      node = node.__class__
    
    assert isinstance(node, TypeType)
    
    try:
      node_callable = node.__call__
    except AttributeError:
      return None
    
    if not leaf_is_visible(node_callable, node):
      return None
    
    if resolve_template:
      tpl = _get_template(node)
      if tpl is not None:
        return tpl
    
    name = _node_name(node_callable, None)
    if name is None and resolve_template:
      path = [u'__call__']
    else:
      path = []
    
    path = _path_to_class(node, path)
  
  if path is not None and None in path:
    return None
  
  return path


def _path_to_class(node, path):
  root = root_controller()
  if getattr(node, 'hidden', False) or not issubclass(node, root):
    return None
  if node is root:
    return path
  path.append(_node_name(node, node.controller_name()))
  try:
    return _path_to_class(node.__bases__[0], path)
  except IndexError:
    return path


def _filter_dict(d, rex):
  if rex is not None:
    rex = unicode(rex).strip()
    if rex:
      dd = {}
      try:
        rex = re.compile('.*%s.*' % rex, re.I)
        for k in d:
          if rex.match(k):
            dd[k] = d[k]
        return dd
      except re.error:
        pass
  return d


def _doc_intro(entity):
  s = []
  if not entity.__doc__:
    return u''
  for ln in unicode(entity.__doc__).strip().split('\n'):
    ln = ln.strip()
    if not ln:
      break
    s.append(ln)
  return u'\n'.join(s).rstrip(u'.')


def leaf_reflection(leaf):
  '''Structured info for leaf.
  Returns a dict or None if leaf is not exposed or not on the controller tree.
  '''
  if not isinstance(leaf, (MethodType, FunctionType, ClassType, TypeType)):
    return None
  
  if path_to(leaf) is None:
    return None
  
  info = introspect.callable_info(leaf)
  
  params = {}
  for k,v in info['args']:
    param_info = {
      'description': None,
      'required': v is Undefined
    }
    params[k] = param_info
  
  try:
    formats = leaf.formats
  except AttributeError:
    # Any serializer
    formats = [serializer.extensions[0] for serializer in smisk.serialization.serializers]
  
  try:
    http_methods = leaf.methods
    # Some special rules:
    if 'OPTIONS' not in http_methods:
      # Need to make a copy here, or we'll change the actual setting on the leaf.
      # Note: We set OPTIONS implicitly, because we want flexibility. See note in 
      #       decorators.expose for more information.
      http_methods = http_methods + ['OPTIONS']
    if 'HEAD' not in http_methods  and  'GET' in http_methods:
      # HEAD is a GET but without the actual body
      http_methods = http_methods + ['HEAD']
  except AttributeError:
    http_methods = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE']
  
  if leaf.__doc__:
    descr = _doc_intro(leaf)
  else:
    descr = ''
  
  return {
    'params': params,
    'description': descr,
    'formats': formats,
    'methods': http_methods,
  }


class Controller(object):
  '''The base controller from which the controller tree is grown.
  
  To grow a controller tree, you need to set a root first. This is done by defining a subclass of `Controller` with the special name 'root' (case-insensitive).
  
  Here is a very simple, but valid, controller tree::
  
    class root(Controller):
      def hello(self):
        return {'message': 'Hello'}
  
  '''
  
  smisk_enable_specials = True
  ''':Deprecated: Use :attr:`enable_reflection` instead
  :type: bool
  '''
  
  def __new__(typ):
    if not '_instance' in typ.__dict__:
      o = object.__new__(typ)
      class_meths = classmethods(typ)
      for k in dir(o):
        v = getattr(o, k)
        if (k[0] != '_' or getattr(v, 'slug', False)) and k not in class_meths:
          o.__dict__[k] = v
      typ._instance = o
    return typ._instance
  
  @classmethod
  def controller_name(cls):
    '''Returns the canonical name of this controller.
    
    :rtype: string'''
    try:
      return cls.slug
    except AttributeError:
      return inflection.underscore(cls.__name__.replace('Controller',''))
  
  @classmethod
  def controller_path(cls):
    '''Returns the canonical path to this controller.
    
    :returns: path as token list or None if no path to this controller.
    :rtype: list'''
    return path_to(cls)
  
  @classmethod
  def controller_uri(cls):
    '''Returns the canonical URI for this controller.
    
    :rtype: string'''
    return uri_for(cls)
  
  @classmethod
  def special_methods(cls):
    '''Returns a dictionary of available special methods, keyed by exposed name.
    
    :see: :attr:`enable_reflection`
    :rtype: list
    '''
    specials = {}
    for k in dir(Controller):
      if k.startswith('smisk_'):
        v = getattr(Controller, k)
        if isinstance(v, (MethodType, FunctionType)):
          node_name = k
          try:
            slug = v.slug
            if slug is not None:
              node_name = unicode(slug)
          except AttributeError:
            pass
          specials[node_name] = v
    return specials
  
  @expose('smisk:methods', methods=('OPTIONS', 'GET', 'HEAD'))
  def smisk_methods(self, filter=None, *args, **params):
    '''List available methods.
    
    :param filter: Only list methods which URI matches this regular expression.
    :type filter:  string
    :returns: Methods keyed by URI
    '''
    try:
      methods = self._methods_cached
    except AttributeError:
      methods = {}
      for controller in controllers():
        leafs = controller.__dict__.values()
        leafs.append(controller)
        for leaf in leafs:
          m = leaf_reflection(leaf)
          if m is not None:
            methods[uri_for(leaf)] = m
      self._methods_cached = methods
    return _filter_dict(methods, filter)
  
  
  @expose('smisk:charsets', methods=('OPTIONS', 'GET', 'HEAD'))
  def smisk_charsets(self, filter=None, *args, **params):
    '''List available character sets.
    
    :param filter: Only list charsets matching this regular expression.
    :type filter:  string
    :returns: Character sets keyed by name
    '''
    from smisk.charsets import charsets
    return _filter_dict(charsets, filter)
  
  
  @expose('smisk:serializers', methods=('OPTIONS', 'GET', 'HEAD'))
  def smisk_serializers(self, filter=None, *args, **params):
    '''List available content serializers.
    
    :param filter: Only list serializers which name matches this regular expression.
    :type filter:  string
    :returns: Serializers keyed by name
    '''
    import smisk.serialization
    serializers = {}
    for serializer in smisk.serialization.serializers:
      serializers[serializer.name] = {
        'extensions': serializer.extensions,
        'media_types': serializer.media_types,
        'preferred_charset': serializer.charset,
        'description': _doc_intro(serializer),
        'directions': serializer.directions()
      }
    return _filter_dict(serializers, filter)
  
  def redirect_to_referrer(self, fallback='/'):
    raise http.Found(smisk.core.Application.current.request.env.get('HTTP_REFERER', fallback))
  
  def __repr__(self):
    uri = self.controller_uri()
    if uri is None:
      uri = ''
    return '<Controller %s uri=%r>' % (self.__class__.__name__, uri)
  

########NEW FILE########
__FILENAME__ = decorators
# encoding: utf-8
'''Controller tree function decorators.
'''
import types

__all__ = ['expose', 'hide', 'leaf_filter']

def expose(slug=None, template=None, formats=None, delegates=False, methods=None):
	'''Explicitly expose a function, optionally configure how it is exposed.
	'''
	def entangle(func):
		# Note: We do not add default values (i.e. methods = None) because we can not gurantee
		#			 that every leaf called has been @expose'd, so we need to check for attribute
		#			 existance anyway outside of this scope.
		
		# Slug
		if slug is not None:
			# Slug might be the function if decorator called without ()
			if isinstance(slug, basestring):
				func.slug = unicode(slug)
			elif isinstance(slug, unicode):
				func.slug = slug
		
		# Delegates to other leafs up the class hierarchy?
		if delegates is not None:
			func.delegates = bool(delegates)
		
		# Template
		if template is not None:
			func.template = unicode(template)
		
		# Formats
		if formats is not None:
			if isinstance(formats, (list, tuple)):
				func.formats = formats
			else:
				func.formats = (formats,)
			for s in func.formats:
				if not isinstance(s, basestring):
					raise TypeError('formats must be a tuple or list of strings, alternatively a single string')
		
		# Methods
		if methods is not None:
			if isinstance(methods, (list, tuple)):
				func.methods = methods
			else:
				func.methods = (methods,)
			for s in func.methods:
				if not isinstance(s, basestring):
					raise TypeError('methods must be a tuple or list of strings, alternatively a single string')
			func.methods = [s.upper() for s in func.methods]
		
		return func
	
	if isinstance(slug, (types.FunctionType, types.MethodType)):
		return entangle(slug)
	return entangle


def hide(func=None):
	def entangle(func):
		func.hidden = True
		return func
	if isinstance(func, (types.FunctionType, types.MethodType)):
		return entangle(func)
	return entangle


def leaf_filter(filter):
	def entangle(leaf, *va, **kw):
		def f(*va, **kw):
			return filter(leaf, *va, **kw)
		f.parent_leaf = leaf
		return f
	entangle.__name__ = filter.__name__+'_leaf_filter'
	return entangle

class LeafFilter(object):
	'''Leaf filter factory baseclass
	
	Used like this:
	
		myf = MySubclass()
		...
		@myf
		def some_leaf...
	
	'''
	def filter_proxy(self, leaf, filter):
		def f(*va, **kw):
			return filter(leaf, *va, **kw)
		f.parent_leaf = leaf
		f.__name__ = leaf.__name__+'_with_'+self.__class__.__name__+'_'+filter.__name__
		return f
	
	def __call__(self, leaf):
		return self.filter_proxy(leaf, self.filter)
	
	def filter(self):
		raise NotImplementedError('filter')
	

	

########NEW FILE########
__FILENAME__ = filters
# encoding: utf-8
'''Leaf filters
'''
import smisk.core
import smisk.mvc.http as http
from smisk.core import Application as App
from smisk.mvc.decorators import leaf_filter, LeafFilter
from smisk.mvc.helpers import redirect_to
from smisk.mvc.model import sql
from time import time
try:
	from hashlib import md5
except ImportError:
	from md5 import md5

__all__ = ['confirm']


@leaf_filter
def confirm(leaf, *va, **params):
	'''Requires the client to resend the request, passing a one-time
	valid token as confirmation.
	'''
	req = App.current.request
	
	# Validate confirmation if available
	params['confirmed'] = False
	try:
		if params['confirm_token'] == req.session['confirm_token']:
			params['confirmed'] = True
	except (KeyError, TypeError):
		pass
	
	# Make sure we don't keep confirm_token in params
	try: del params['confirm_token']
	except: pass
	
	# Call leaf
	rsp = leaf(*va, **params)
	
	# Add confirmation token if still unconfirmed
	if not params['confirmed']:
		if not isinstance(req.session, dict):
			req.session = {}
		confirm_token = smisk.core.uid()
		req.session['confirm_token'] = confirm_token
		if not isinstance(rsp, dict):
			rsp = {}
		rsp['confirm_token'] = confirm_token
	else:
		# Remove confirmation tokens
		try: del req.session['confirm_token']
		except: pass
		try: del rsp['confirm_token']
		except: pass
	
	# Return response
	return rsp


class AuthFilter(LeafFilter):
	authorized_param = 'authorized_user'
	create_leaf = None
	
	def __init__(self, create_leaf=None, authorized_param=None):
		if create_leaf:
			self.create_leaf = create_leaf
		if authorized_param:
			self.authorized_param = authorized_param
	
	@property
	def authorized(self):
		raise NotImplementedError('authorized')
	
	@property
	def have_valid_create_leaf(self):
		return self.create_leaf and (isinstance(self.create_leaf, basestring) or control.uri_for(self.create_leaf) is not None)
	
	def will_authorize(self, *va, **kw):
		pass
	
	def did_authorize(self, user, rsp, exc):
		pass
	
	def did_fail(self):
		if not self.have_valid_create_leaf:
			raise http.Unauthorized()
		redirect_to(self.create_leaf)
	
	def create(self, leaf):
		return self.filter_proxy(leaf, self._create)
	
	def _create(self, leaf, *va, **kw):
		exc = None
		rsp = None
		self.will_authorize(va, kw)
		try:
			rsp = leaf(*va, **kw)
		except http.HTTPExc, e:
			exc = e
		if rsp and isinstance(rsp, dict) and self.authorized_param in rsp and rsp[self.authorized_param]:
			self.did_authorize(rsp[self.authorized_param], rsp, exc)
		if exc:
			raise exc
		return rsp
	
	def require(self, leaf):
		return self.filter_proxy(leaf, self._require)
	
	__call__ = require
	
	def _require(self, leaf, *va, **kw):
		if not self.authorized:
			self.did_fail()
		return leaf(*va, **kw)
	
	def destroy(self, leaf):
		return self.filter_proxy(leaf, self._destroy)
	
	def _destroy(self, leaf, *va, **kw):
		App.current.request.session = None
		return leaf(*va, **kw)
	

class SessionAuthFilter(AuthFilter):
	referrer_param = 'auth_referrer'
	
	@property
	def session(self):
		if not isinstance(App.current.request.session, dict):
			App.current.request.session = {}
		return App.current.request.session
	
	@property
	def authorized(self):
		if isinstance(App.current.request.session, dict):
			return App.current.request.session.get(self.authorized_param)
	
	def will_authorize(self, va, kw):
		if self.referrer_param in kw:
			self.session[self.referrer_param] = kw[self.referrer_param]
			del kw[self.referrer_param]
	
	def did_authorize(self, user, rsp, exc):
		self.session[self.authorized_param] = user
		if self.referrer_param in self.session:
			referrer = self.session[self.referrer_param]
			del self.session[self.referrer_param]
			redirect_to(referrer)
	
	def did_fail(self):
		if not self.have_valid_create_leaf:
			raise http.Unauthorized()
		redirect_to(self.create_leaf, **{self.referrer_param: App.current.request.url})
	

class DigestAuthFilter(LeafFilter):
	'''HTTP Digest authorization filter.
	'''
	required = ['username', 'realm', 'nonce', 'uri', 'response']
	users = {}
	
	def __init__(self, realm, users=None, require_authentication=True):
		self.realm = realm
		if users is not None:
			self.users = users
		self.require_authentication = require_authentication
		self.leaf = None
	
	def respond_unauthorized(self, send401=True, *va, **kw):
		if not send401:
			kw['authorized_user'] = None
			return self.leaf(*va, **kw)
		# send response
		App.current.response.headers.append(
			'WWW-Authenticate: Digest realm="%s", nonce="%s", algorithm="MD5", qop="auth"'
				% (self.realm, self.create_nonce())
		)
		raise http.Unauthorized()
	
	def respond_authorized(self, user, *va, **kw):
		kw['authorized_user'] = user
		return self.leaf(*va, **kw)
	
	def get_authorized(self, username):
		# subclasses can return an alternative object which will be propagated 
		return username
	
	def create_nonce(self):
		return md5('%d:%s' % (time(), self.realm)).hexdigest()
	
	def H(self, data):
		return md5(data).hexdigest()
	
	def KD(self, secret, data):
		return self.H(secret + ':' + data)
	
	def filter(self, *va, **kw):
		# did the client even try to authenticate?
		if 'HTTP_AUTHORIZATION' not in App.current.request.env:
			return self.respond_unauthorized(self.require_authentication, *va, **kw)
		
		# not digest auth?
		if not App.current.request.env['HTTP_AUTHORIZATION'].startswith('Digest '):
			raise http.BadRequest('only Digest authorization is allowed')
		
		# parse
		params = {}
		required = len(self.required)
		for k, v in [i.split("=", 1) for i in App.current.request.env['HTTP_AUTHORIZATION'][7:].strip().split(',')]:
			k = k.strip()
			params[k] = v.strip().replace('"', '')
			if k in self.required:
				required -= 1
		
		# missing required parameters?
		if required > 0:
			raise http.BadRequest('insufficient authorization parameters')
		
		# user exists?
		if params['username'] not in self.users:
			return self.respond_unauthorized(True, *va, **kw)
		
		# build A1 and A2
		A1 = '%s:%s:%s' % (params['username'], self.realm, self.users[params['username']])
		A2 = App.current.request.method + ':' + App.current.request.url.uri
		
		# build expected response
		expected_response = None
		if 'qop' in params:
			# if qop is sent then cnonce and nc MUST be present
			if not 'cnonce' in params or not 'nc' in params:
				raise http.BadRequest('cnonce and/or nc authorization parameters missing')
			
			# only auth type is supported
			if params['qop'] != 'auth':
				raise http.BadRequest('unsupported qop ' + params['qop'])
			
			# build
			expected_response = self.KD(self.H(A1), '%s:%s:%s:%s:%s' % (
				params['nonce'], params['nc'], params['cnonce'], params['qop'], self.H(A2)))
		else:
			# qop not present (compatibility with RFC 2069)
			expected_response = self.KD(self.H(A1), params['nonce'] + ':' + self.H(A2))
		
		# 401 on realm mismatch
		if params['realm'] != self.realm:
			log.debug('auth failure: unexpected realm')
			return self.respond_unauthorized(True, *va, **kw)
		
		# 401 on unexpected response
		if params['response'] != expected_response:
			log.debug('auth failure: unexpected digest response')
			return self.respond_unauthorized(True, *va, **kw)
		
		# authorized -- delegate further down the filter chain
		return self.respond_authorized(params['username'], *va, **kw)
	

class sortable_entities(LeafFilter):
	'''Sort sets of Elixir entities
	
	Usage:
	
		@sortable_entities(UserAccount, 'users', 'created')
		def users(self):
			return {'users': UserAccount.query}
	
	'''
	def __init__(self, entity, parameter, sortdefault, orderdefault='desc', kwprefix=''):
		self.entity = entity
		self.parameter = parameter
		self.sortdefault = sortdefault
		self.orderdefault = orderdefault
		self.kwprefix = kwprefix
	
	def filter(self, leaf, *va, **kw):
		rsp = leaf(*va, **kw)
		if self.parameter in rsp:
			q = rsp[self.parameter]
		else:
			q = self.entity.query
		if not q:
			return rsp
		sort = kw.get(self.kwprefix+'sort', self.sortdefault)
		order = kw.get(self.kwprefix+'order', self.orderdefault)
		if sort:
			sort_key = getattr(self.entity, sort)
			if order == 'desc':
				q = q.order_by(sql.desc(sort_key))
			else:
				q = q.order_by(sort_key)
		rsp.update({
			self.parameter: q.all(),
			self.kwprefix+'sort': sort,
			self.kwprefix+'order': order,
			self.kwprefix+'inverse_order': ('desc','asc')[int(order=='desc')]
		})
		return rsp
	

########NEW FILE########
__FILENAME__ = helpers
# encoding: utf-8
'''Helpers
'''
from smisk.core import URL, Application
from smisk.mvc import control, http
from smisk.mvc.model import Entity
import urllib

__all__ = ['compose_query', 'redirect_to']


def compose_query(params):
  '''Convert a mapping object to a URL encoded query string.
  The opposite can be found in smisk.core.URL.decompose_query().
  '''
  return urllib.urlencode(params, doseq=1)


def redirect_to(url, entity=None, status=http.Found, **params):
  '''Redirect the requesting client to someplace else.
  '''
  # If one or more entities are defined, add primary keys to params
  if entity is not None:
    if not isinstance(entity, (list, tuple)):
      entity = [entity]
    for ent in entity:
      for pk in ent.table.primary_key.keys():
        params[pk] = getattr(ent, pk)
  
  # The url might be a URL or leaf
  if not isinstance(url, basestring):
    if not url:
      url = '/'
    elif isinstance(url, URL):
      url = str(url)
    else:
      # url is probably an leaf
      url = control.uri_for(url)
      # Add filename extension if the initial request used it
      try:
        ext = Application.current.request.url.path.rsplit('.', 1)[1]
        url = url + '.' + ext
      except:
        pass
  
  # Append any params to url
  if params and url:
    if not url.endswith('?'):
      if '?' in url:
        url = url + '&'
      else:
        url = url + '?'
    url = url + compose_query(params)
  
  # Status3xx.service() will perform further work on this url or 
  # path (absolutize it, etc)
  raise status(url)

########NEW FILE########
__FILENAME__ = http
# encoding: utf-8
'''HTTP support (status codes, etc)
'''
from smisk.util.string import normalize_url, strip_filename_extension
from smisk.core import URL
from smisk.core.xml import escape as xmlesc

__all__ = ['STATUS', 'HTTPExc', 'Status', 'Status3xx', 'Status300', 'Status404', 'Continue', 'SwitchingProtocols', 'OK', 'Created', 'Accepted', 'NonAuthoritativeInformation', 'NoContent', 'ResetContent', 'PartialContent', 'MultipleChoices', 'MovedPermanently', 'Found', 'SeeOther', 'NotModified', 'UseProxy', 'TemporaryRedirect', 'BadRequest', 'Unauthorized', 'PaymentRequired', 'Forbidden', 'NotFound', 'ControllerNotFound', 'MethodNotFound', 'TemplateNotFound', 'MethodNotAllowed', 'NotAcceptable', 'ProxyAuthenticationRequired', 'RequestTimeout', 'Conflict', 'Gone', 'LengthRequired', 'PreconditionFailed', 'RequestEntityTooLarge', 'RequestURITooLarge', 'UnsupportedMediaType', 'RequestedRangeNotSatisfiable', 'ExpectationFailed', 'InternalServerError', 'NotImplemented', 'BadGateway', 'ServiceUnavailable', 'GatewayTimeout', 'HTTPVersionNotSupported']

STATUS = {}
'''Mapping HTTP status codes to `Status` objects.

:type: dict
'''

class HTTPExc(Exception):
  '''Wraps a HTTP status.
  '''
  def __init__(self, status, *args, **kwargs):
    Exception.__init__(self)
    self.status = status
    self.args = args
    self.kwargs = kwargs
  
  def __call__(self, app):
    return self.status.service(app, *self.args, **self.kwargs)
  
  def __str__(self):
    return '%s %s %s' % (self.status, self.args, self.kwargs)
  

class Status(object):
  '''Represents a HTTP status.
  '''
  def __init__(self, code, name, has_body=True, uses_template=True):
    self.code = code
    self.name = name
    self.has_body = has_body
    self.uses_template = uses_template
    STATUS[code] = self
  
  def __call__(self, *args, **kwargs):
    '''Return a `HTTPExc` wrapping this status.
    
    ``*args`` and ``**kwargs`` will be passed unmodified to `service()` 
    when someone ``call`` the returned `HTTPExc` object.
    
    :rtype: HTTPExc
    '''
    return HTTPExc(self, *args, **kwargs)
  
  def service(self, app, *args, **kwargs):
    '''Called when someone calls a `HTTPExc` object, wrapping this status.
    
    This interface is compatible with the callables returned by routers.
    Mainly used by `mvc.Application.error()`
    
    :Parameters:
      app : mvc.Application
        The calling application
    :rtype: dict
    '''
    app.response.status = self
    if self.has_body:
      desc = self.name
      if args:
        desc = ', '.join(args)
      return {'description': desc}
  
  @property
  def is_error(self):
    return self.code % 500 < 100
  
  def __str__(self):
    return '%d %s' % (self.code, self.name)
  
  def __unicode__(self):
    return u'%d %s' % (self.code, self.name.decode('ascii'))
  
  def __repr__(self):
    return 'Status(%r, %r)' % (self.code, self.name)
  

class Status3xx(Status):
  '''Represents HTTP status 301-307.
  '''
  def service(self, app, url=None, *args, **kwargs):
    if url is None:
      raise Exception('http.Status3xx requires a 3:rd argument "url"')
    rsp = Status.service(self, app)
    url = normalize_url(url)
    url = url.to_s(port=url.port not in (80,443), fragment=0, user=0, password=0)
    app.response.replace_header('Location: ' + url)
    rsp['description'] = 'The resource has moved to %s' % url
    return rsp
  

class Status300(Status):
  '''Represents HTTP status 300, related to Content Negotiation.
  '''
  
  charset = 'iso-8859-1'
  '''Latin-1 is defined as the default fallback for HTTP 1.1 responses,
  thus maximizing compatibility.
  
  :type: string
  '''
  
  HTML_TEMPLATE = ur'''<html>
  <head>
    <title>Multiple Choices</title>
    <style type="text/css">body{font-family:sans-serif;}</style>
  </head>
  <body>
    <ul>
%s
    </ul>
  </body>
</html>
  '''
  ''':type: string
  '''
  
  def service(self, app, url=None, *args, **kwargs):
    from smisk.serialization import serializers
    rsp = Status.service(self, app)
    if url is None:
      url = app.request.cn_url
    elif not isinstance(url, URL):
      url = URL(url)
    path = url.path
    query = ''
    if url.query:
      query = '?' + url.query
    
    header = []
    html = []
    for serializer in serializers:
      alt_path = '%s.%s' % (path, serializer.extensions[0] + query)
      header_s = '"%s" 1.0 {type %s}' % (alt_path, serializer.media_types[0])
      header.append('{%s}' % header_s)
      html.append('<li><a href="%s">%s (%s)</a></li>' % \
        (xmlesc(alt_path), xmlesc(serializer.name), xmlesc(serializer.media_types[0])))
    
    app.response.replace_header('TCN: list')
    app.response.replace_header('Alternates: '+','.join(header))
    app.response.replace_header('Content-Type: text/html; charset=%s' % self.charset)
    return (self.HTML_TEMPLATE % u'\n'.join(html)).encode(self.charset, 'replace')
  

class Status404(Status):
  '''Represents HTTP status 404.
  '''
  def service(self, app, description=None, *args, **kwargs):
    rsp = Status.service(self, app)
    if description is not None:
      rsp['description'] = description
    else:
      rsp['description'] = 'No resource exists at %s' % \
        app.request.url.to_s(scheme=0, user=0, host=0, port=0)
    return rsp
  

Continue                     = Status(100, "Continue")
SwitchingProtocols           = Status(101, "Switching Protocols")

OK                           = Status(200, "OK")
Created                      = Status(201, "Created")
Accepted                     = Status(202, "Accepted")
NonAuthoritativeInformation  = Status(203, "Non-Authoritative Information")
NoContent                    = Status(204, "No Content")
ResetContent                 = Status(205, "Reset Content")
PartialContent               = Status(206, "Partial Content")

MultipleChoices              = Status300(300, "Multiple Choices", uses_template=False)
MovedPermanently             = Status3xx(301, "Moved Permanently")
Found                        = Status3xx(302, "Found")
SeeOther                     = Status3xx(303, "See Other")
NotModified                  = Status(304, "Not Modified", False)
UseProxy                     = Status3xx(305, "Use Proxy")
TemporaryRedirect            = Status3xx(307, "Temporary Redirect")

BadRequest                   = Status(400, "Bad Request")
Unauthorized                 = Status(401, "Unauthorized")
PaymentRequired              = Status(402, "Payment Required", False)
Forbidden                    = Status(403, "Forbidden")
NotFound                     = Status404(404, "Not Found")

ControllerNotFound           = Status404(404, "Not Found")
MethodNotFound               = Status404(404, "Not Found")
TemplateNotFound             = Status404(404, "Not Found")

MethodNotAllowed             = Status(405, "Method Not Allowed", False)
NotAcceptable                = Status(406, "Not Acceptable")
ProxyAuthenticationRequired  = Status(407, "Proxy Authentication Required", False)
RequestTimeout               = Status(408, "Request Time-out", False)
Conflict                     = Status(409, "Conflict", False)
Gone                         = Status(410, "Gone", False)
LengthRequired               = Status(411, "Length Required")
PreconditionFailed           = Status(412, "Precondition Failed")
RequestEntityTooLarge        = Status(413, "Request Entity Too Large")
RequestURITooLarge           = Status(414, "Request-URI Too Large")
UnsupportedMediaType         = Status(415, "Unsupported Media Type", False)
RequestedRangeNotSatisfiable = Status(416, "Requested range not satisfiable")
ExpectationFailed            = Status(417, "Expectation Failed")

InternalServerError          = Status(500, "Internal Server Error")
NotImplemented               = Status(501, "Not Implemented")
BadGateway                   = Status(502, "Bad Gateway")
ServiceUnavailable           = Status(503, "Service Unavailable")
GatewayTimeout               = Status(504, "Gateway Time-out")
HTTPVersionNotSupported      = Status(505, "HTTP Version not supported")

########NEW FILE########
__FILENAME__ = model
# encoding: utf-8
'''Model in MVC
'''
from warnings import filterwarnings, warn
import logging

log = logging.getLogger(__name__)

default_engine_opts = {}

try:
  # Ignore the SA string type depr warning
  from sqlalchemy.exceptions import SADeprecationWarning
  filterwarnings('ignore', 'Using String type with no length for CREATE TABLE',
                 SADeprecationWarning)
  
  # Import Elixir & SQLAlchemy
  from sqlalchemy import func
  import elixir, sqlalchemy as sql
  from sqlalchemy.pool import StaticPool
  import sqlalchemy.orm
  
  # Replace Elixir default session (evens out difference between Elixir 0.5 - 0.6)
  elixir.session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
    autoflush=True, transactional=True))
  
  # Import Elixir
  from elixir import *
  
  # Disable autosetup since we call setup_all() in mvc.Application.setup()
  options_defaults['autosetup'] = False
  
  # Includes module name in table names if False.
  # If True, project.fruits.Apple -> table apple.
  # If False, project.fruits.Apple -> table project_fruits_apple.
  options_defaults['shortnames'] = True
  
  # Extended entity class
  def Entity_field_names(cls):
    for col in cls.c:
      yield col.key
  Entity.field_names = classmethod(Entity_field_names)
  
  def Entity__iter__(self):
    return self.to_dict().__iter__()
  Entity.__iter__ = Entity__iter__
  
  
  # Add Entity.to_dict for old Elixir versions
  __ev = elixir.__version__.split('.')
  if __ev[0] == '0' and int(__ev[1]) < 6:
    def Entity_to_dict(self, deep={}, exclude=[]):
      """Generate a JSON-style nested dict/list structure from an object."""
      col_prop_names = [p.key for p in self.c]
      data = dict([(name, getattr(self, name))
                   for name in col_prop_names if name not in exclude])
      for rname, rdeep in deep.items():
        # This code is borrowed from Elixir 0.7 and fairly untested with <=0.5
        dbdata = getattr(self, rname)
        #FIXME: use attribute names (ie coltoprop) instead of column names
        fks = self.mapper.get_property(rname).remote_side
        exclude = [c.name for c in fks]
        if isinstance(dbdata, list):
          data[rname] = [o.to_dict(rdeep, exclude) for o in dbdata]
        else:
          data[rname] = dbdata.to_dict(rdeep, exclude)
      return data
    Entity.to_dict = Entity_to_dict
  del __ev
  
  
  # A static pool, since Smisk is not multi-threaded
  class SingleProcessPool(StaticPool):
    def __init__(self, *va, **kw):
      StaticPool.__init__(self, *va, **kw)
      self._init_va = va
      self._init_kw = kw
      logger_name = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
      self.logger = logging.getLogger(logger_name)
      if self.echo == 'debug':
        self.logger.setLevel(logging.DEBUG)
      elif self.echo is True:
        self.logger.setLevel(logging.INFO)
      elif self.echo is False:
        self.logger.setLevel(logging.NOTSET)
    
    def recreate(self):
      self.log("recreating")
      o = self.__class__(*self._init_va, **self._init_kw)
      o.logger = self.logger
      return o
    
  
  # MySQL-specific pool, handling dropped connections.
  # We derive from the StaticPool, only using one connection per process.
  class MySQLConnectionPool(SingleProcessPool):
    def do_get(self):
      # This works with MySQL-python >=1.2.2 and sets reconnect in the MySQL client
      # library for the current connection, and automatically reconnects if needed.
      self._conn.ping(True)
      return self.connection
    
  
  # Metadata configuration bind filter
  from smisk.config import config
  def smisk_mvc_metadata(conf):
    '''This config filter configures the underlying Elixir 
    and SQLAlchemy modules.
    '''
    global log
    conf = conf.get('smisk.mvc.model')
    if not conf:
      return
    
    # Aquire required parameter "url"
    try:
      url = conf['url']
    except KeyError:
      log.warn('missing required "url" parameter in "smisk.mvc.model" config')
      return
    
    # Parse url into an accessible structure
    from smisk.core import URL, Application
    url_st = URL(url)
    
    # Make a copy of the default options
    engine_opts = default_engine_opts.copy()
    
    # MySQL
    if url_st.scheme.lower() == 'mysql':
      if 'poolclass' not in conf:
        conf['poolclass'] = MySQLConnectionPool
        log.debug('MySQL: setting poolclass=%r', conf['poolclass'])
        if 'pool_size' in conf:
          log.debug('MySQL: disabling pool_size')
          del conf['pool_size']
        if 'pool_size' in engine_opts:
          del engine_opts['pool_size']
      elif 'pool_recycle' not in conf and 'pool_recycle' not in engine_opts:
        # In case of user-configured custom pool_class
        conf['pool_recycle'] = 3600
        log.debug('MySQL: setting pool_recycle=%r', conf['pool_recycle'])
    elif 'poolclass' not in conf:
      # Others than MySQL should also use a kind of static pool
      conf['poolclass'] = SingleProcessPool
    
    # Demux configuration
    elixir_opts = {}
    for k,v in conf.items():
      if k.startswith('elixir.'):
        elixir_opts[k[7:]] = v
      elif k != 'url':
        engine_opts[k] = v
    
    # Apply Elixir default options
    if elixir_opts:
      log.info('applying Elixir default options %r', elixir_opts)
      # We apply by iteration since options_defaults is not 
      # guaranteed to be a real dict.
      for k,v in elixir_opts.items():
        options_defaults[k] = v
    
    # Mask out password, since we're logging this
    if url_st.password:
      url_st.password = '***'
    
    def rebind_model_metadata():
      # Dispose any previous connection
      if metadata.bind and hasattr(metadata.bind, 'dispose'):
        log.debug('disposing old connection %r', metadata.bind)
        try:
          metadata.bind.dispose()
        except Exception, e:
          if e.args and e.args[0] and 'SQLite objects created in a thread' in e.args[0]:
            log.debug('SQLite connections can not be disposed from other threads'\
              ' -- simply leaving it to the GC')
          else:
            log.warn('failed to properly dispose the connection', exc_info=True)
    
      # Create, configure and bind engine
      if engine_opts:
        log.info('binding to %r with options %r', str(url_st), engine_opts)
      else:
        log.info('binding to %r', str(url_st))
      metadata.bind = sql.create_engine(url, **engine_opts)
    
    # Queue action or call it directly
    if hasattr(Application.current, '_pending_rebind_model_metadata'):
      log.info('queued pending metadata rebind')
      Application.current._pending_rebind_model_metadata = rebind_model_metadata
    else:
      # Run in this thread -- might cause problems with thread-local stored connections
      rebind_model_metadata()
  
  config.add_filter(smisk_mvc_metadata)
  # dont export these
  del smisk_mvc_metadata
  del config
  

except ImportError, e:
  warn('Elixir and/or SQLAlchemy is not installed -- smisk.mvc.model is not '\
       'available. (%s)' % e)
  
  # So mvc.Application can do "if model.metadata.bind: ..."
  class metadata(object):
    bind = None
  
  session = None
  Entity = None


def _perform_if_dirty(sess, call_if_dirty, logprefix, check_modified=False):
  if sess:
    if sess.transaction and sess.transaction.session and sess.transaction._active:
      log.debug('%s model session because of a started transaction', logprefix)
      call_if_dirty()
    elif check_modified:
      modified = [ent for ent in sess if sess.is_modified(ent, passive=True)]
      if modified:
        log.debug('%s model session because of modified entities: %r', logprefix, modified)
        call_if_dirty()
    if sess.transaction:
      # remove session in order to avoid keeping open sessions between requests
      sess.transaction = None

def commit_if_needed(check_modified=True):
  '''
  session.registry() => a orm.session.Sess, subclass of orm.session.Session
  session.commit() == session.registry().commit()
  '''
  sess = session.registry()
  return _perform_if_dirty(sess, sess.commit, 'committing', check_modified)

def rollback_if_needed(check_modified=False):
  sess = session.registry()
  return _perform_if_dirty(sess, sess.rollback, 'rolling back', check_modified)


########NEW FILE########
__FILENAME__ = routing
#!/usr/bin/env python
# encoding: utf-8
'''URL-to-function routing.
'''
import sys, re, logging, new
from smisk.mvc import http
from smisk.mvc import control
from smisk.core import URL
from smisk.config import config
from smisk.util.type import *
from smisk.util.python import wrap_exc_in_callable
from smisk.util.string import tokenize_path
from smisk.util.introspect import introspect

__all__ = ['Destination', 'Filter', 'Router']
log = logging.getLogger(__name__)

def _prep_path(path):
	return unicode(path).rstrip(u'/').lower()

def _node_name(node, fallback):
	n = getattr(node, 'slug', None)
	if n is None:
		return fallback
	return n

def _find_canonical_leaf(leaf, rel_im_leaf):
	canonical_leaf = leaf
	try:
		while 1:
			canonical_leaf = canonical_leaf.parent_leaf
	except AttributeError:
		pass
	if isinstance(canonical_leaf, FunctionType) \
	and canonical_leaf.__name__ not in ('va_kwa_wrapper', 'exc_wrapper'):
		# In this case, the leaf has been decorated and thus need to be bound into
		# a proper instance method.
		canonical_leaf = new.instancemethod(canonical_leaf, rel_im_leaf.im_self, rel_im_leaf.im_class)
	return canonical_leaf


class Destination(object):
	'''A callable destination.
	'''
	
	leaf = None
	''':type: callable
	'''
	
	def __init__(self, leaf):
		self.leaf = leaf
		self.formats = None
		try:
			self.formats = self.leaf.formats
		except AttributeError:
			pass
	
	def _call_leaf(self, *args, **params):
		return self.leaf(*args, **params)
	
	def __call__(self, *args, **params):
		'''Call leaf
		'''
		try:
			return self._call_leaf(*args, **params)
		except TypeError, e:
			desc = e.args[0]
			
			# Find out if the problem was caused in self._call_leaf or originates someplace else
			tb = sys.exc_info()[2]
			if not tb:
				raise
			while 1:
				if tb.tb_next:
					tb = tb.tb_next
				else:
					break
			if tb.tb_lineno != self._call_leaf.im_func.func_code.co_firstlineno+1:
				raise
			
			GOT_MUL = ' got multiple values for keyword argument '
			
			def req_args():
				info = introspect.callable_info(self.leaf)
				args = []
				for k,v in info['args']:
					if v is Undefined:
						args.append(k)
				return ', '.join(args)
			
			if (desc.find(' takes at least ') > 0 and desc.find(' arguments ') > 0) or (desc.find(' takes exactly ') > 0):
				log.debug('TypeError', exc_info=1)
				raise http.BadRequest('Missing required parameters: %r (Received %r, %r)' % \
					(req_args(), params, args))
			else:
				p = desc.find(GOT_MUL)
				if p > 0:
					raise http.BadRequest('%s got multiple values for keyword argument %s'\
						' -- received args %r and params %r' % \
						(self.uri, desc[p+len(GOT_MUL):], args, params))
			raise
			
	
	@property
	# compatibility -- remove when we remove support for deprecated name "action"
	def action(self):
		return self.leaf
	
	
	_canonical_leaf = None
	@property
	def canonical_leaf(self):
		if self._canonical_leaf is None:
			self._canonical_leaf = _find_canonical_leaf(self.leaf, self.leaf)
			log.debug('%r.canonical_leaf = %r', self, self._canonical_leaf)
		return self._canonical_leaf
	
	
	@property
	def path(self):
		'''Canonical exposed path.
		
		:rtype: list
		'''
		return control.path_to(self.canonical_leaf)
	
	@property
	def uri(self):
		'''Canonical exposed URI.
		
		:rtype: string
		'''
		return control.uri_for(self.canonical_leaf)
	
	@property
	def template_path(self):
		'''Template path.
		
		:rtype: list
		'''
		return control.template_for(self.canonical_leaf)
	
	def __str__(self):
		if self.path:
			return '/'+'/'.join(self.path)
		else:
			return self.__repr__()
	
	def __repr__(self):
		return '%s(canonical_leaf=%r, uri=%r)' \
			% (self.__class__.__name__, self.canonical_leaf, self.uri)
	

class Filter(object):
	def match(self, method, url):
		'''Test this filter against *method* and *url*.
		
		:returns: (list args, dict params) or None if no match
		:rtype: tuple
		'''
		return None2
	

class RegExpFilter(Filter):
	def __init__(self, pattern, destination_path, regexp_flags=re.I, match_on_full_url=False, 
							 methods=None, params={}):
		'''Create a new regular expressions-based filter.
		
		:param pattern:					 Pattern
		:type	pattern:					 string or re.Regex
		
		:param destination_path:	Path to leaf, expressed in internal canonical form.
															i.e. "/controller/leaf".
		:type	destination_path:	string
		
		:param regexp_flags:			Defaults to ``re.I`` (case-insensitive)
		:type	regexp_flags:			int
		
		:param match_on_full_url: Where there or not to perform matches on complete
															URL (i.e. "https://foo.tld/bar?question=2").
															Defauts to False (i.e.matches on path only. "/bar")
		:type	match_on_full_url: bool
		
		:param params:						Parameters are saved and later included in every call to
															leafs taking this route.
		:type	params:						dict
		'''
		if not isinstance(regexp_flags, int):
			regexp_flags = 0
		
		if isinstance(pattern, RegexType):
			self.pattern = pattern
		elif not isinstance(pattern, basestring):
			raise ValueError('first argument "pattern" must be a Regex object or a string, not %s'\
				% type(pattern).__name__)
		else:
			self.pattern = re.compile(pattern, regexp_flags)
		
		if not isinstance(destination_path, (basestring, URL)):
			raise ValueError('second argument "destination_path" must be a string or URL, not %s'\
				% type(destination_path).__name__)
		
		self.destination_path = _prep_path(destination_path)
		self.match_on_full_url = match_on_full_url
		self.params = params
		
		if isinstance(methods, (list, tuple)):
			self.methods = methods
		elif methods is not None:
			if not isinstance(methods, basestring):
				raise TypeError('methods must be a tuple or list of strings, '\
					'alternatively a string, not a %s.' % type(methods))
			self.methods = (methods,)
		else:
			self.methods = None
	
	def match(self, method, url):
		'''Test this filter against *method* and *url*.
		
		:returns: (list args, dict params) or None if no match
		:rtype: tuple
		'''
		if method	and	self.methods is not None	and	method not in self.methods\
		and	(not control.enable_reflection	or	method != 'OPTIONS'):
			return None2
		
		if self.match_on_full_url:
			m = self.pattern.match(unicode(url))
		else:
			m = self.pattern.match(unicode(url.path))
		if m is not None:
			if self.params:
				params = self.params.copy()
			else:
				params = {}
			for k,v in m.groupdict().items():
				if isinstance(k, unicode):
					k = k.encode('utf-8')
				params[k] = v
			return [], params
		
		return None2
	
	def __repr__(self):
		return '<%s.%s(%r, %r, %r) @0x%x>' %\
			(self.__module__, self.__class__.__name__, \
			self.methods, self.pattern.pattern, self.destination_path, id(self))
	


class Router(object):
	'''
	Default router handling both RegExp mappings and class tree mappings.
	
	Consider the following tree of controllers::
	
		class root(Controller):
			def __call__(self, *args, **params):
				return 'Welcome!'
		
		class employees(root):
			def __call__(self, *args, **params):
				return {'employees': Employee.query.all()}
			
			def show(self, name, *args, **params):
				return {'employee': Employee.get_by(name=name)}
			
			class edit(employees):
				def save(self, employee_id, *args, **params):
					Employee.get_by(id=employee_id).save_or_update(**params)
	
	
	Now, this list shows what URIs would map to what begin called::
	
		/												 => root().__call__()
		/employees								=> employees().__call__()
		/employees/							 => employees().__call__()
		/employees/show					 => employees().show()
		/employees/show?name=foo	=> employees().show(name='foo')
		/employees/show/123			 => None
		/employees/edit/save			=> employees.edit().save()
	
	See source of ``smisk.test.routing`` for more examples.
	'''
	
	def __init__(self):
		self.cache = {}
		self.filters = []
	
	def configure(self, config_key='smisk.mvc.routes'):
		filters = config.get(config_key, [])
		if not isinstance(filters, (list, tuple)):
			raise TypeError('configuration parameter %r must be a list' % config_key)
		for filter in filters:
			try:
				# Convert a list or tuple mapping
				if isinstance(filter, (tuple, list)):
					if len(filter) > 2:
						filter = {'methods':filter[0], 'pattern': filter[1], 'destination': filter[2]}
					else:
						filter = {'pattern': filter[0], 'destination': filter[1]}
				# Create a filter from the mapping
				dest = URL(filter['destination'])
				self.filter(filter['pattern'], dest, match_on_full_url=dest.scheme,
										methods=filter.get('methods', None))
			except TypeError, e:
				e.args = ('configuration parameter %r must contain dictionaries or lists' % config_key,)
				raise
			except IndexError, e:
				e.args = ('%r in configuration parameter %r' % (e.message, config_key),)
				raise
			except KeyError, e:
				e.args = ('%r in configuration parameter %r' % (e.message, config_key),)
				raise
	
	def filter(self, pattern, destination_path, regexp_flags=re.I, match_on_full_url=False, 
						 params={}, methods=None):
		'''Explicitly map an leaf to paths or urls matching regular expression `pattern`.
		
		:param pattern:					 Pattern
		:type	pattern:					 string or re.Regex
		
		:param destination_path:	Path to leaf, expressed in internal canonical form.
															i.e. "/controller/leaf".
		:type	destination_path:	string
		
		:param regexp_flags:			Defaults to ``re.I`` (case-insensitive)
		:type	regexp_flags:			int
		
		:param match_on_full_url: Where there or not to perform matches on complete
															URL (i.e. "https://foo.tld/bar?question=2").
															Defauts to False (i.e.matches on path only. "/bar")
		:type	match_on_full_url: bool
		
		:param params:						Parameters are saved and later included in every call to
															leafs taking this route.
		:type	params:						dict
		
		:rtype: RegExpFilter
		'''
		filter = RegExpFilter(pattern, destination_path, regexp_flags, match_on_full_url, methods)
		# already exists?
		for i in range(len(self.filters)):
			f = self.filters[i]
			if isinstance(f, RegExpFilter) and f.pattern.pattern == pattern and f.methods == methods:
				# replace
				self.filters[i] = filter
				log.debug('updated filter %r', filter)
				return filter
		self.filters.append(filter)
		log.debug('added filter %r', filter)
		return filter
	
	
	def __call__(self, method, url, args, params):
		'''
		Find destination for route `url`.
		
		:param method: HTTP method
		:type	method: str
		:param url: The URL to consider
		:type	url: smisk.core.URL
		:return: ('Destionation' ``dest``, list ``args``, dict ``params``).
						 ``dest`` might be none if no route to destination.
		:rtype: tuple
		'''
		# Explicit mapping? (never cached)
		for filter in self.filters:
			dargs, dparams = filter.match(method, url)
			if dargs != None:
				dargs.extend(args)
				dparams.update(params)
				return self._resolve_cached(filter.destination_path), dargs, dparams
		
		return self._resolve_cached(_prep_path(url.path)), args, params
	
	def _resolve_cached(self, raw_path):
		try:
			return self.cache[raw_path]
		except KeyError:
			dest = introspect.ensure_va_kwa(self._resolve(raw_path))
			if dest is not None:
				dest = Destination(dest)
			self.cache[raw_path] = dest
			return dest
	
	def _resolve(self, raw_path):
		# Tokenize path
		path = tokenize_path(raw_path)
		node = control.root_controller()
		cls = node
		
		log.debug('resolving %s (%r) on tree %r', raw_path, path, node)
		
		# Check root
		if node is None:
			return wrap_exc_in_callable(http.ControllerNotFound('No root controller exists'))
		
		# Special case: empty path == root.__call__
		if not path:
			try:
				node = node().__call__
				log.debug('found leaf: %s', node)
				return node
			except AttributeError:
				return wrap_exc_in_callable(http.MethodNotFound('/'))
		
		# Traverse tree
		for part in path:
			log.debug('looking at part %r', part)
			found = None
			
			# 1. Search subclasses first
			log.debug('matching %r to subclasses of %r', part, node)
			try:
				subclasses = node.__subclasses__()
			except AttributeError:
				log.debug('node %r does not have subclasses -- returning MethodNotFound')
				return wrap_exc_in_callable(http.MethodNotFound(raw_path))
			for subclass in node.__subclasses__():
				if _node_name(subclass, subclass.controller_name()) == part:
					if getattr(subclass, 'hidden', False):
						continue
					found = subclass
					break
			if found is not None:
				node = found
				cls = node
				continue
			
			# 2. Search methods
			log.debug('matching %r to methods of %r', part, node)
			# Aquire instance
			if type(node) is type:
				node = node()
			for k,v in node.__dict__.items():
				if _node_name(v, k.lower()) == part:
					# If the leaf is hidden, we skip it
					if getattr(v, 'hidden', False):
						continue
					# If the leaf is not defined directly on parent node node, and
					# node.delegate evaluates to False, we bail out
					if not control.leaf_is_visible(v, cls):
						node = None
					else:
						found = v
					break
			
			# Check found node
			if found is not None:
				node = found
				node_type = type(node)
				# The following two lines enables accepting prefix routes:
				#if node_type is MethodType or node_type is FunctionType:
				#	break
			else:
				# Not found
				return wrap_exc_in_callable(http.MethodNotFound(raw_path))
		
		# Did we hit a class/type at the end? If so, get its instance.
		if type(node) is type:
			try:
				cls = node
				node = cls().__call__
				if not control.leaf_is_visible(node, cls):
					node = None
			except AttributeError:
				# Uncallable leaf
				node = None
		
		# Not callable?
		if node is None or not callable(node):
			return wrap_exc_in_callable(http.MethodNotFound(raw_path))
		
		log.debug('found leaf: %s', node)
		return node
	

########NEW FILE########
__FILENAME__ = filters
# encoding: utf-8
'''Template filters
'''

def j(s):
  """Escape for JavaScript or encode as JSON"""
  pass

try:
  from cjson import encode as _json
except ImportError:
  try:
    from minjson import write as _json
  except ImportError:
    import re
    _RE = re.compile(r'(["\'\\])')
    def _json(s):
      return repr(_RE.sub(r'\\\1', s)).replace('\\\\','\\')
j = _json

########NEW FILE########
__FILENAME__ = release
'''Release information.
'''
__all__ = ['version','author','email','copyright','license','version_info']

version = "1.1.7" # Major.Minor.Build (see tag_build in setup.cfg)
author = "Rasmus Andersson"
email = "rasmus@flajm.com"
copyright = "Copyright 2007-2009 Rasmus Andersson"
license = r'''Copyright (c) 2007-2009 Rasmus Andersson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.'''

version_info = tuple([int(s) for s in version.split('.')])

########NEW FILE########
__FILENAME__ = all
# encoding: utf-8
# Load as many built-in serializers as possible
import smisk.serialization.json, \
       smisk.serialization.php_serial, \
       smisk.serialization.plain_text, \
       smisk.serialization.plist, \
       smisk.serialization.python_pickle, \
       smisk.serialization.python_py, \
       smisk.serialization.xhtml, \
       smisk.serialization.xmlgeneric, \
       smisk.serialization.xmlrpc, \
       smisk.serialization.xspf, \
       smisk.serialization.yaml_serial

########NEW FILE########
__FILENAME__ = json
# encoding: utf-8
'''
JSON: JavaScript Object Notation

:see: `RFC 4627 <http://tools.ietf.org/html/rfc4627>`__
:requires: `cjson <http://pypi.python.org/pypi/python-cjson>`__ | minjson
'''
from smisk.core import request
from smisk.serialization import serializers, Serializer
try:
  from cjson import \
              encode as json_encode,\
              decode as json_decode,\
              DecodeError,\
              EncodeError
except ImportError:
  try:
    from json import dumps as json_encode, loads as json_decode
  except ImportError:
    try:
      from minjson import \
                 write as json_encode,\
                  read as json_decode,\
         ReadException as DecodeError,\
        WriteException as EncodeError
    except ImportError:
      json_encode = None

class JSONSerializer(Serializer):
  '''JavaScript Object Notation
  '''
  name = 'JSON'
  extensions = ('json',)
  media_types = ('application/json',)
  charset = 'utf-8'
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def serialize(cls, params, charset):
    return (cls.charset, json_encode(params))
  
  @classmethod
  def serialize_error(cls, status, params, charset):
    return cls.serialize(params, charset)
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (list args, dict params)
    if not charset:
      charset = cls.charset
    st = json_decode(file.read(length).decode(charset))
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, list):
      return (st, None)
    else:
      return ((st,), None)
  

class JSONPSerializer(JSONSerializer):
  '''JavaScript Object Notation with Padding
  
  JSONP support through passing the special ``callback`` query string parameter.
  '''
  name = 'JSONP'
  extensions = ('js','jsonp')
  media_types = ('text/javascript',)
  
  @classmethod
  def serialize(cls, params, charset):
    callback = u'jsonp_callback'
    if request:
      callback = request.get.get('callback', callback)
    s = '%s(%s);' % (callback.encode(cls.charset), json_encode(params))
    return (cls.charset, s)
  

# Don't register if we did not find a json implementation
if json_encode is not None:
  serializers.register(JSONSerializer)
  serializers.register(JSONPSerializer)

if __name__ == '__main__':
  s = JSONSerializer.serialize({
    'message': 'Hello worlds',
    'internets': [
      'interesting',
      'lolz',
      42.0,
      {
        'tubes': [1,3,16,18,24],
        'persons': True,
        'me agåain': {
          'message': 'Hello worlds',
          'internets': [
            'interesting',
            'lolz',
            42.0,
            {
              'tubes': [1,3,16,18,24],
              'persons': True
            }
          ]
        }
      }
    ]
  }, None)
  print s

########NEW FILE########
__FILENAME__ = php_serial
# encoding: utf-8
'''PHP serial serialization
'''
from smisk.serialization import *
from types import *
try:
  from cStringIO import StringIO
except:
  from StringIO import StringIO

class PHPSerialSerializationError(SerializationError):
  pass

class PHPSerialSerializer(Serializer):
  '''PHP serial serializer.'''
  name = 'PHP serial'
  extensions = ('sphp', 'phpser')
  media_types = ('application/vnd.php.serialized', 'application/x-php-serialized')
  can_serialize = True
  
  @classmethod
  def encode_key(cls, obj, f):
    if isinstance(obj, (IntType, FloatType, LongType, BooleanType)):
      f.write('i:%d;' % int(obj))
    elif isinstance(obj, basestring):
      try:
        f.write('i:%d;' % int(obj))
      except ValueError:
        f.write('s:%d:"%s";' % (len(obj), obj))
    elif isinstance(obj, NoneType):
      f.write('s:0:"";')
    else:
      raise PHPSerialSerializationError('Unsupported type: %s' % type(obj).__name__)
  
  @classmethod
  def encode_object(cls, obj, f):
    if isinstance(obj, BooleanType):
      f.write('b:%d;' % obj)
    elif isinstance(obj, (FloatType, LongType)):
      f.write('d:%s;' % obj)
    elif isinstance(obj, IntType):
      f.write('i:%d;' % obj)
    elif isinstance(obj, data):
      f.write('s:%d:"%s";' % (len(obj), obj))
    elif isinstance(obj, basestring):
      try:
        f.write('i:%d;' % int(obj))
      except ValueError:
        f.write('s:%d:"%s";' % (len(obj), obj))
    elif isinstance(obj, NoneType):
      f.write('N;')
    elif isinstance(obj, (ListType, TupleType)):
      f.write('a:%i:{' % len(obj))
      for k,v in enumerate(obj):
        f.write('i:%d;' % k)
        cls.encode_object(v, f)
      f.write('}')
    elif isinstance(obj, DictType):
      f.write('a:%i:{' % len(obj))
      for k,v in obj.items():
        cls.encode_key(k, f)
        cls.encode_object(v, f)
      f.write('}')
    else:
      raise PHPSerialSerializationError('Unsupported type: %s' % type(obj).__name__)
  
  @classmethod
  def serialize(cls, params, charset):
    f = StringIO()
    cls.encode_object(params, f)
    return (None, f.getvalue())
  

serializers.register(PHPSerialSerializer)

if __name__ == '__main__':
  from datetime import datetime
  print PHPSerialSerializer.serialize({
    'message': 'Hello worlds',
    'internets': [
      'interesting',
      'lolz',
      42.0,
      {
        'tubes': [1,3,16,18,24],
        'persons': True,
        'me again': {
          'message': 'Hello worlds',
          'internets': [
            'interesting',
            'lolz',
            42.0,
            {
              'tubes': [1,3,16,18,24],
              'persons': True
            }
          ],
          'today': str(datetime.now())
        }
      }
    ],
    'today': str(datetime.now())
  }, 'whatever')[1]
########NEW FILE########
__FILENAME__ = plain_text
# encoding: utf-8
'''Plain text serialization.
'''
from smisk.serialization import serializers, Serializer
from smisk.serialization.yaml_serial import yaml, YAMLSerializer

if not yaml:
  def _encode_value(v, buf, level):
    if isinstance(v, bool):
      if v:
        buf.append(u'true')
      else:
        buf.append(u'false')
    elif isinstance(v, int):
      buf.append(u'%d' % v)
    elif isinstance(v, float):
      buf.append(u'%f' % v)
    elif isinstance(v, basestring):
      buf.append(unicode(v))
    elif isinstance(v, list) or isinstance(v, tuple):
      _encode_sequence(v, buf, level)
    elif isinstance(v, dict):
      _encode_map(v, buf, level)
    else:
      buf.append(unicode(v))
    return buf

  def _encode_map(d, buf, level=0):
    indent = u'  '*level
    #buf.append(u'\n')
    ln = len(d)
    i = 1
    items = d.items()
    items.sort()
    for k,v in items:
      buf.append(u'\n')
      buf.append(u'%s' % indent)
      buf.append(u'%s: ' % k)
      _encode_value(v, buf, level+1)
      i += 1
    return buf

  def _encode_sequence(l, buf, level):
    indent = u'  '*level
    #buf.append(u'\n')
    ln = len(l)
    i = 1
    for v in l:
      buf.append(u'\n%s' % indent)
      _encode_value(v, buf, level+1)
      i += 1
    return buf


class PlainTextSerializer(Serializer):
  '''Human-readable plain text'''
  name = 'Plain text'
  extensions = ('txt',)
  media_types = ('text/plain',)
  charset = 'utf-8'
  can_serialize = True
  
  if yaml:
    # If we have YAML-capabilities we use YAML for plain text output
    @classmethod
    def serialize(cls, params, charset):
      return YAMLSerializer.serialize(params, charset)
  else:
    @classmethod
    def serialize(cls, params, charset):
      s = u'%s\n' % u''.join(_encode_map(params, [])).strip()
      return (charset, s.encode(charset, cls.unicode_errors))
    
  

serializers.register(PlainTextSerializer)

########NEW FILE########
__FILENAME__ = plist
# encoding: utf-8
'''Apple/NeXT Property List serialization.
'''
from smisk.serialization.xmlbase import *
from datetime import datetime
from types import *
import smisk.serialization.plistlib_ as plistlib

__all__ = ['XMLPlistSerializer']

class XMLPlistSerializer(XMLSerializer):
  '''XML Property List serializer
  '''
  name = 'XML Property List'
  extensions = ('plist',)
  media_types = ('application/plist+xml',)
  charset = 'utf-8'
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def serialize(cls, params, charset):
    return (cls.charset, plistlib.writePlistToString(params))
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (list args, dict params)
    st = plistlib.readPlistFromString(file.read(length))
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, (list, tuple)):
      return (st, None)
    else:
      return ((st,), None)
  

serializers.register(XMLPlistSerializer)

if __name__ == '__main__':
  charset, xmlstr = XMLPlistSerializer.serialize(dict(
      string = "Doodah",
      items = ["A", "B", 12, 32.1, [1, 2, 3]],
      float = 0.1,
      integer = 728,
      dict = {
        "str": "<hello & hi there!>",
        "unicode": u'M\xe4ssig, Ma\xdf',
        "true value": True,
        "false value": False,
      },
      data = data("<binary gunk>"),
      more_data = data("<lots of binary gunk>" * 10),
      date = datetime.now(),
    ), None)
  print xmlstr
  from StringIO import StringIO
  print repr(XMLPlistSerializer.unserialize(StringIO(xmlstr)))

########NEW FILE########
__FILENAME__ = plistlib_
"""plistlib.py -- a tool to generate and parse MacOSX .plist files.

The PropertyList (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the writePlist(rootObject, pathOrFile)
function. 'rootObject' is the top level object, 'pathOrFile' is a
filename or a (writable) file object.

To parse a plist from a file, use the readPlist(pathOrFile) function,
with a file name or a (readable) file object as the only argument. It
returns the top level object (again, usually a dictionary).

To work with plist data in strings, you can use readPlistFromString()
and writePlistToString().

Values can be strings, integers, floats, booleans, tuples, lists,
dictionaries, Data or datetime.datetime objects. String values (including
dictionary keys) may be unicode strings -- they will be written out as
UTF-8.

The <data> plist type is supported through the Data class. This is a
thin wrapper around a Python string.

Generate Plist example:

  pl = dict(
    aString="Doodah",
    aList=["A", "B", 12, 32.1, [1, 2, 3]],
    aFloat=0.1,
    anInt=728,
    aDict=dict(
      anotherString="<hello & hi there!>",
      aUnicodeValue=u'M\xe4ssig, Ma\xdf',
      aTrueValue=True,
      aFalseValue=False,
    ),
    someData=Data("<binary gunk>"),
    someMoreData=Data("<lots of binary gunk>" * 10),
    aDate=datetime.datetime.fromtimestamp(time.mktime(time.gmtime())),
  )
  # unicode keys are possible, but a little awkward to use:
  pl[u'\xc5benraa'] = "That was a unicode key."
  writePlist(pl, fileName)

Parse Plist example:

  pl = readPlist(pathOrFile)
  print pl["aKey"]
"""


__all__ = [
  "readPlist", "writePlist", "readPlistFromString", "writePlistToString",
  "Data"
]

import binascii
import datetime
from cStringIO import StringIO
import re
import warnings

try:
  from elixir import Entity
except ImportError:
  class Undef(object):
    pass
  Entity = Undef()


def readPlist(pathOrFile):
  """Read a .plist file. 'pathOrFile' may either be a file name or a
  (readable) file object. Return the unpacked root object (which
  usually is a dictionary).
  """
  didOpen = 0
  if isinstance(pathOrFile, (str, unicode)):
    pathOrFile = open(pathOrFile)
    didOpen = 1
  p = PlistParser()
  rootObject = p.parse(pathOrFile)
  if didOpen:
    pathOrFile.close()
  return rootObject


def writePlist(rootObject, pathOrFile):
  """Write 'rootObject' to a .plist file. 'pathOrFile' may either be a
  file name or a (writable) file object.
  """
  didOpen = 0
  if isinstance(pathOrFile, (str, unicode)):
    pathOrFile = open(pathOrFile, "w")
    didOpen = 1
  writer = PlistWriter(pathOrFile)
  writer.writeln("<plist version=\"1.0\">")
  writer.writeValue(rootObject)
  writer.writeln("</plist>")
  if didOpen:
    pathOrFile.close()


def readPlistFromString(data):
  """Read a plist data from a string. Return the root object.
  """
  return readPlist(StringIO(data))


def writePlistToString(rootObject):
  """Return 'rootObject' as a plist-formatted string.
  """
  f = StringIO()
  writePlist(rootObject, f)
  return f.getvalue()


class DumbXMLWriter:

  def __init__(self, file, indentLevel=0, indent="\t"):
    self.file = file
    self.stack = []
    self.indentLevel = indentLevel
    self.indent = indent

  def beginElement(self, element):
    self.stack.append(element)
    self.writeln("<%s>" % element)
    self.indentLevel += 1

  def endElement(self, element):
    assert self.indentLevel > 0
    assert self.stack.pop() == element
    self.indentLevel -= 1
    self.writeln("</%s>" % element)

  def simpleElement(self, element, value=None):
    if value is not None:
      value = _escapeAndEncode(value)
      self.writeln("<%s>%s</%s>" % (element, value, element))
    else:
      self.writeln("<%s/>" % element)

  def writeln(self, line):
    if line:
      self.file.write(self.indentLevel * self.indent + line + "\n")
    else:
      self.file.write("\n")


# Contents should conform to a subset of ISO 8601
# (in particular, YYYY '-' MM '-' DD 'T' HH ':' MM ':' SS 'Z'.  Smaller units may be omitted with
#  a loss of precision)
_dateParser = re.compile(r"(?P<year>\d\d\d\d)(?:-(?P<month>\d\d)(?:-(?P<day>\d\d)(?:T(?P<hour>\d\d)(?::(?P<minute>\d\d)(?::(?P<second>\d\d))?)?)?)?)?Z")

def _dateFromString(s):
  order = ('year', 'month', 'day', 'hour', 'minute', 'second')
  gd = _dateParser.match(s).groupdict()
  lst = []
  for key in order:
    val = gd[key]
    if val is None:
      break
    lst.append(int(val))
  return datetime.datetime(*lst)

def _dateToString(d):
  return '%04d-%02d-%02dT%02d:%02d:%02dZ' % (
    d.year, d.month, d.day,
    d.hour, d.minute, d.second
  )


# Regex to find any control chars, except for \t \n and \r
_controlCharPat = re.compile(
  r"[\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
  r"\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f]")

def _escapeAndEncode(text):
  m = _controlCharPat.search(text)
  if m is not None:
    raise ValueError("strings can't contains control characters; "
             "use plistlib.Data instead")
  text = text.replace("\r\n", "\n")     # convert DOS line endings
  text = text.replace("\r", "\n")     # convert Mac line endings
  text = text.replace("&", "&amp;")     # escape '&'
  text = text.replace("<", "&lt;")    # escape '<'
  text = text.replace(">", "&gt;")    # escape '>'
  return text.encode("utf-8")       # encode as UTF-8


PLISTHEADER = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
"""

class PlistWriter(DumbXMLWriter):

  def __init__(self, file, indentLevel=0, indent="\t", writeHeader=1):
    if writeHeader:
      file.write(PLISTHEADER)
    DumbXMLWriter.__init__(self, file, indentLevel, indent)

  def writeValue(self, value):
    if isinstance(value, (str, unicode)):
      self.simpleElement("string", value)
    elif isinstance(value, bool):
      # must switch for bool before int, as bool is a
      # subclass of int...
      if value:
        self.simpleElement("true")
      else:
        self.simpleElement("false")
    elif isinstance(value, (int, long)):
      self.simpleElement("integer", "%d" % value)
    elif isinstance(value, float):
      self.simpleElement("real", repr(value))
    elif isinstance(value, dict):
      self.writeDict(value)
    elif isinstance(value, Entity):
      self.writeDict(value.to_dict())
    elif isinstance(value, Data):
      self.writeData(value)
    elif isinstance(value, datetime.datetime):
      self.simpleElement("date", _dateToString(value))
    elif isinstance(value, (tuple, list)):
      self.writeArray(value)
    else:
      raise TypeError("unsuported type: %s" % type(value))

  def writeData(self, data):
    self.beginElement("data")
    self.indentLevel -= 1
    maxlinelength = 76 - len(self.indent.replace("\t", " " * 8) *
                 self.indentLevel)
    for line in data.asBase64(maxlinelength).split("\n"):
      if line:
        self.writeln(line)
    self.indentLevel += 1
    self.endElement("data")

  def writeDict(self, d):
    self.beginElement("dict")
    items = d.items()
    items.sort()
    for key, value in items:
      if not isinstance(key, (str, unicode)):
        raise TypeError("keys must be strings")
      self.simpleElement("key", key)
      self.writeValue(value)
    self.endElement("dict")

  def writeArray(self, array):
    self.beginElement("array")
    for value in array:
      self.writeValue(value)
    self.endElement("array")


def _encodeBase64(s, maxlinelength=76):
  # copied from base64.encodestring(), with added maxlinelength argument
  maxbinsize = (maxlinelength//4)*3
  pieces = []
  for i in range(0, len(s), maxbinsize):
    chunk = s[i : i + maxbinsize]
    pieces.append(binascii.b2a_base64(chunk))
  return "".join(pieces)

class Data:

  """Wrapper for binary data."""

  def __init__(self, data):
    self.data = data

  def fromBase64(cls, data):
    # base64.decodestring just calls binascii.a2b_base64;
    # it seems overkill to use both base64 and binascii.
    return cls(binascii.a2b_base64(data))
  fromBase64 = classmethod(fromBase64)

  def asBase64(self, maxlinelength=76):
    return _encodeBase64(self.data, maxlinelength)

  def __cmp__(self, other):
    if isinstance(other, self.__class__):
      return cmp(self.data, other.data)
    elif isinstance(other, str):
      return cmp(self.data, other)
    else:
      return cmp(id(self), id(other))

  def __repr__(self):
    return "%s(%s)" % (self.__class__.__name__, repr(self.data))


class PlistParser:

  def __init__(self):
    self.stack = []
    self.currentKey = None
    self.root = None

  def parse(self, fileobj):
    from xml.parsers.expat import ParserCreate
    parser = ParserCreate()
    parser.StartElementHandler = self.handleBeginElement
    parser.EndElementHandler = self.handleEndElement
    parser.CharacterDataHandler = self.handleData
    parser.ParseFile(fileobj)
    return self.root

  def handleBeginElement(self, element, attrs):
    self.data = []
    handler = getattr(self, "begin_" + element, None)
    if handler is not None:
      handler(attrs)

  def handleEndElement(self, element):
    handler = getattr(self, "end_" + element, None)
    if handler is not None:
      handler()

  def handleData(self, data):
    self.data.append(data)

  def addObject(self, value):
    if self.currentKey is not None:
      self.stack[-1][self.currentKey] = value
      self.currentKey = None
    elif not self.stack:
      # this is the root object
      self.root = value
    else:
      self.stack[-1].append(value)

  def getData(self):
    data = "".join(self.data)
    try:
      data = data.encode("ascii")
    except UnicodeError:
      pass
    self.data = []
    return data

  # element handlers

  def begin_dict(self, attrs):
    d = dict()
    self.addObject(d)
    self.stack.append(d)
  def end_dict(self):
    self.stack.pop()

  def end_key(self):
    self.currentKey = self.getData()

  def begin_array(self, attrs):
    a = []
    self.addObject(a)
    self.stack.append(a)
  def end_array(self):
    self.stack.pop()

  def end_true(self):
    self.addObject(True)
  def end_false(self):
    self.addObject(False)
  def end_integer(self):
    self.addObject(int(self.getData()))
  def end_real(self):
    self.addObject(float(self.getData()))
  def end_string(self):
    self.addObject(self.getData())
  def end_data(self):
    self.addObject(Data.fromBase64(self.getData()))
  def end_date(self):
    self.addObject(_dateFromString(self.getData()))

########NEW FILE########
__FILENAME__ = python_pickle
# encoding: utf-8
'''
Python pickle serialization
'''
from smisk.serialization import serializers, Serializer
import logging
try:
  from cPickle import dumps, load, loads, HIGHEST_PROTOCOL
except ImportError:
  from pickle import dumps, load, loads, HIGHEST_PROTOCOL

log = logging.getLogger(__name__)


class PythonPickleSerializer(Serializer):
  '''
  Python Pickle binary protocol.
  
  Example client for interacting with a smisk service::
  
    >>> import pickle, urllib
    >>> print pickle.load(urllib.urlopen("http://localhost:8080/.pickle?hello=123"))
  '''
  name = 'Python pickle'
  extensions = ('pickle',)
  media_types = ('application/x-python-pickle', 'application/x-pickle')
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def serialize(cls, params, charset=None):
    return (None, dumps(params, HIGHEST_PROTOCOL))
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (list args, dict params)
    if length == 0:
      return (None, None)
    elif length > 0 and length < 1024:
      st = loads(file.read(length))
    else:
      st = load(file)
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, list):
      return (st, None)
    else:
      return ((st,), None)
  

serializers.register(PythonPickleSerializer)

########NEW FILE########
__FILENAME__ = python_py
# encoding: utf-8
'''Python repr serialization.
'''
from smisk.serialization import serializers, Serializer

class PythonPySerializer(Serializer):
  '''Plain Python code
  '''
  name = 'Python repr'
  extensions = ('py',)
  media_types = ('text/x-python',)
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def serialize(cls, params, charset):
    return (None, repr(params))
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (list args, dict params)
    st = eval(file.read(length), {}, {})
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, list):
      return (st, None)
    else:
      return ((st,), None)
  

serializers.register(PythonPySerializer)

if __name__ == '__main__':
  from datetime import datetime
  print PythonPySerializer.encode({
    'message': 'Hello worlds',
    'internets': [
      'interesting',
      'lolz',
      42.0,
      {
        'tubes': [1,3,16,18,24],
        'persons': True,
        'me again': {
          'message': 'Hello worlds',
          'internets': [
            'interesting',
            'lolz',
            42.0,
            {
              'tubes': [1,3,16,18,24],
              'persons': True
            }
          ],
          'today': datetime.now()
        }
      }
    ],
    'today': datetime.now()
  })

########NEW FILE########
__FILENAME__ = xhtml
# encoding: utf-8
'''XHTML generic serialization
'''
from smisk.serialization import serializers, Serializer
from smisk.mvc import http
from smisk.core.xml import escape as xml_escape
from smisk.core import app, request

def encode_value(v, buf, value_wraptag='tt'):
  if isinstance(v, bool):
    if v:
      buf.append(u'<%s>True</%s>' % (value_wraptag, value_wraptag))
    else:
      buf.append(u'<%s>False</%s>' % (value_wraptag, value_wraptag))
  elif isinstance(v, list) or isinstance(v, tuple):
    encode_sequence(v, buf, value_wraptag)
  elif isinstance(v, dict):
    encode_map(v, buf, value_wraptag)
  else:
    buf.append(u'<%s>%s</%s>' % (value_wraptag, xml_escape(unicode(v)), value_wraptag) )
  return buf

def encode_map(d, buf, value_wraptag='tt'):
  buf.append(u'<ul>')
  items = d.items()
  items.sort()
  for k,v in items:
    buf.append(u'<li>%s: ' % xml_escape(unicode(k)) )
    encode_value(v, buf, value_wraptag)
    buf.append(u'</li>')
  buf.append(u'</ul>')
  return buf

def encode_sequence(l, buf, value_wraptag='tt'):
  buf.append(u'<ol>')
  for v in l:
    buf.append(u'<li>')
    encode_value(v, buf, value_wraptag)
    buf.append(u'</li>')
  buf.append(u'</ol>')
  return buf


class XHTMLSerializer(Serializer):
  '''eXtensible Hypertext Markup Language'''
  name = 'XHTML'
  extensions = ('html',)
  media_types = ('text/html', 'application/xhtml+xml')
  charset = 'utf-8'
  can_serialize = True
  
  @classmethod
  def serialize(cls, params, charset):
    title = u'Response'
    server = u''
    if app and app.destination is not None:
      title = u'/%s.html' % u'/'.join(app.destination.path)
      server = request.env['SERVER_SOFTWARE']
    d = [u'<?xml version="1.0" encoding="%s" ?>' % charset]
    d.append(u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '\
             u'"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
    d.append(u'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">')
    d.append(u'<head><title>%s</title>'\
      u'<style type="text/css">'\
        u'body{font-family:sans-serif;}'\
        u'ul,ol{margin-bottom:1em}'\
        u'</style>'\
      u'</head>' % xml_escape(title))
    d.append(u'<body>')
    d.append(u'<h1>%s</h1>' % xml_escape(title))
    encode_map(params, d)
    if server:
      d.append(u'<hr/><address>%s</address>' % server)
    d.append(u'</body></html>')
    return (charset, u''.join(d).encode(charset, cls.unicode_errors))
  
  @classmethod
  def serialize_error(cls, status, params, charset):
    xp = {'charset':charset}
    for k,v in params.items():
      if k == 'traceback':
        if v and status.is_error:
          v = u'<pre class="traceback">%s</pre>' % xml_escape(''.join(v))
        else:
          v = u''
      elif k == 'description':
        v = u''.join(encode_value(v, [], 'p'))
      else:
        v = xml_escape(unicode(v))
      xp[k] = v
    # Override if description_html is set
    if 'description_html' in params:
      xp['description'] = params['description_html']
    if 'traceback' not in xp:
      xp['traceback'] = ''
    s = ERROR_TEMPLATE % xp
    return (charset, s.encode(charset, cls.unicode_errors))
  

serializers.register(XHTMLSerializer)

ERROR_TEMPLATE = ur'''<?xml version="1.0" encoding="%(charset)s" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <title>%(name)s</title>
    <style type="text/css">
      body,html { padding:0; margin:0; background:#666; }
      h1 { padding:25pt 10pt 10pt 15pt; background:#ffb2bf; color:#560c00; font-family:arial,helvetica,sans-serif; margin:0; }
      address, p { font-family:'lucida grande',verdana,arial,sans-serif; }
      body > p, body > ul, body > ol { padding:10pt 16pt; background:#fff; color:#222; margin:0; font-size:.9em; }
      pre.traceback { padding:10pt 15pt 25pt 15pt; line-height:1.4; background:#f2f2ca; color:#52523b; margin:0; border-top:1px solid #e3e3ba; border-bottom:1px solid #555; }
      hr { display:none; }
      address { padding:10pt 15pt; color:#333; font-size:11px; }
    </style>
  </head>
  <body>
    <h1>%(name)s</h1>
    %(description)s
    %(traceback)s
    <hr/>
    <address>%(server)s</address>
  </body>
</html>
'''

if __name__ == '__main__':
  from datetime import datetime
  s = XHTMLSerializer.serialize({
    'message': 'Hello worlds',
    'internets': [
      'interesting',
      'lolz',
      42.0,
      {
        'tubes': [1,3,16,18,24],
        'persons': True,
        'me again': {
          'message': 'Hello worlds',
          'internets': [
            'interesting',
            'lolz',
            42.0,
            {
              'tubes': [1,3,16,18,24],
              'persons': True
            }
          ],
          'today': datetime.now()
        }
      }
    ],
    'today': datetime.now()
  }, XHTMLSerializer.charset)
  print s

########NEW FILE########
__FILENAME__ = xmlbase
# encoding: utf-8
'''XML support.
'''
import logging
from smisk.serialization import serializers, data, Serializer, SerializationError, UnserializationError
from smisk.core import Application

try: import xml.etree.cElementTree as ET
except ImportError:
  try: import xml.etree.ElementTree as ET
  except ImportError:
    try: import cElementTree as ET
    except ImportError:
      try: import elementtree.ElementTree as ET
      except ImportError:
        try: import lxml.etree as ET
        except ImportError:
          ET = None

log = logging.getLogger(__name__)

__all__ = ['ET', 'serializers', 'data',
  'XMLSerializer', 'XMLSerializationError', 'XMLUnserializationError']

class XMLSerializationError(SerializationError):
  pass

class XMLUnserializationError(UnserializationError):
  pass

class XMLSerializer(Serializer):
  '''XML serializer baseclass.
  
  Baseclass for XML serializers.
  '''
  name = 'XML'
  charset = 'utf-8'
  
  xml_declaration = '<?xml version="1.0" encoding="%s"?>\n'
  ''':type: string
  '''
  
  xml_doctype = None
  '''Document type (Doctype) specifier.
  
  :type: string
  '''
  
  xml_default_ns = None
  ''':type: string
  '''
  
  xml_root_name = None
  '''Name of root element, if any.
  
  :type: string
  '''
  
  xml_root_attrs = {}
  ''':type: dict
  '''
  
  @classmethod
  def parse_object(cls, elem):
    '''Parse an Element, potentially representing a Python object.
    
    You must implement this method in order to enable decoding.
    
    :Parameters:
      elem : xml.etree.Element
        Element
    :rtype: object
    '''
    raise NotImplementedError('%s.parse_object()' % cls.__name__)
  
  @classmethod
  def build_object(cls, obj):
    '''Parse an object, potentially representing an element in a XML document.
    
    You must implement this method in order to enable encoding.
    
    :Parameters:
      obj : object
        Python object
    :rtype: xml.etree.Element
    '''
    raise NotImplementedError('%s.build_object()' % cls.__name__)
  
  @classmethod
  def parse_document(cls, elem):
    '''Parse an element tree.
    
    :Parameters:
      elem : xml.etree.Element
        Document root element
    :rtype: object
    '''
    if cls.xml_root_name:
      elem = elem.getchildren()[0]
    return cls.parse_object(elem)
  
  @classmethod
  def build_document(cls, obj):
    '''Build an element tree.
    
    :Parameters:
      obj : object
        Python object
    :rtype: xml.etree.Element
    '''
    if not cls.xml_root_name:
      return cls.build_object(obj)
    else:
      if cls.xml_default_ns is not None:
        root = ET.Element(cls.xml_root_name, xmlns=cls.xml_default_ns, **cls.xml_root_attrs)
      else:
        root = ET.Element(cls.xml_root_name, **cls.xml_root_attrs)
      if obj is not None:
        root.append(cls.build_object(obj))
      return root
  
  @classmethod
  def serialize(cls, params, charset):
    doc = cls.build_document(params)
    if cls.xml_declaration:
      string = (cls.xml_declaration % charset)
    else:
      string = ''
    if cls.xml_doctype:
      string += cls.xml_doctype
    string += ET.tostring(doc, charset).encode(charset, cls.unicode_errors)
    return (charset, string)
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (list args, dict params)
    st = cls.parse_document(ET.fromstring(file.read(length)))
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, list):
      return (st, None)
    else:
      return ((st,), None)
  
  @classmethod
  def xml_tag(cls, elem):
    '''Returns the tag name and namespace, if any.
    
    :Parameters:
      elem : xml.etree.Element
        The element
    :returns: A tuple of (string name, string namespace or None)
    :rtype: tuple
    '''
    name = elem.tag
    ns = None
    p = name.find('}')
    if p != -1:
      ns = name[1:p]
      name = name[p+1:]
    return name, ns
  
  @classmethod
  def xml_mktext(cls, name, text, **attributes):
    '''Helper to create an element with text value.
    
    :Parameters:
      name : string
        Element name
      text : string
        Text value
    :rtype: xml.etree.Element
    '''
    e = ET.Element(name, **attributes)
    e.text = text
    return e
  

########NEW FILE########
__FILENAME__ = xmlgeneric
# encoding: utf-8
'''Generic XML serializer.

Inspired by http://msdn.microsoft.com/en-us/library/bb924435.aspx
'''
from smisk.serialization.xmlbase import *
from datetime import datetime
from smisk.util.DateTime import DateTime
from smisk.util.type import *
from smisk.inflection import inflection
try:
  from elixir import Entity
except ImportError:
  class Undef(object):
    pass
  Entity = Undef()

__all__ = ['GenericXMLSerializer', 'GenericXMLUnserializationError']

T_DATE    = 'date'
T_DATA    = 'data'
T_FLOAT   = 'real'
T_INT     = 'int'
T_DICT    = 'dict'
T_ARRAY   = 'array'
T_STRING  = 'string'
T_NULL    = 'null'
T_TRUE    = 'true'
T_FALSE   = 'false'

class GenericXMLUnserializationError(XMLUnserializationError):
  pass

class GenericXMLSerializer(XMLSerializer):
  '''Generic XML format
  '''
  name = 'Generic XML'
  extensions = ('xml',)
  media_types = ('text/xml',)
  charset = 'utf-8'
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def build_object(cls, parent, name, value, set_key=True):
    e = ET.Element(name)
    if isinstance(value, datetime):
      e = ET.Element(T_DATE)
      e.text = DateTime(value).as_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
    elif isinstance(value, data):
      e = ET.Element(T_DATA)
      e.text = value.encode()
    elif isinstance(value, float):
      e = ET.Element(T_FLOAT)
      e.text = unicode(value)
    elif isinstance(value, bool):
      if value:
        e = ET.Element(T_TRUE)
      else:
        e = ET.Element(T_FALSE)
    elif isinstance(value, (int, long)):
      e = ET.Element(T_INT)
      e.text = unicode(value)
    elif value is None:
      e = ET.Element(T_NULL)
    elif isinstance(value, DictType):
      e = ET.Element(T_DICT)
      for k in value:
        cls.build_object(e, k, value[k])
    elif isinstance(value, Entity):
      e = ET.Element(T_DICT)
      value = value.to_dict()
      for k in value:
        cls.build_object(e, k, value[k])
    elif isinstance(value, (list, tuple)):
      e = ET.Element(T_ARRAY)
      item_tag = inflection.singularize(name)
      for v in value:
        cls.build_object(e, item_tag, v, False)
    else:
      e = ET.Element(T_STRING)
      e.text = unicode(value)
    if set_key:
      e.set('k', name)
    parent.append(e)
  
  @classmethod
  def parse_object(cls, elem):
    typ = elem.tag
    if typ == T_DATE:
      return DateTime(DateTime.strptime(elem.text, '%Y-%m-%dT%H:%M:%SZ'))
    elif typ == T_DATA:
      return data.decode(elem.text)
    elif typ == T_FLOAT:
      return float(elem.text)
    elif typ == T_INT:
      return int(elem.text)
    elif typ == T_TRUE:
      return True
    elif typ == T_FALSE:
      return False
    elif typ == T_DICT:
      v = {}
      for cn in elem.getchildren():
        k = cn.get('k')
        if not k:
          raise GenericXMLUnserializationError('malformed document -- '\
            'missing "key" attribute for node %r' % elem)
        v[k] = cls.parse_object(cn)
      return v
    elif typ == T_ARRAY:
      v = []
      for cn in elem.getchildren():
        v.append(cls.parse_object(cn))
      return v
    elif typ == T_STRING:
      return elem.text.decode('utf-8')
    elif typ == T_NULL:
      return None
    else:
      raise GenericXMLUnserializationError('invalid document -- unknown type %r' % typ)
  
  @classmethod
  def build_document(cls, d):
    root = ET.Element(T_DICT)
    for k in d:
      cls.build_object(root, k, d[k])
    return root
  
  @classmethod
  def parse_document(cls, elem):
    return cls.parse_object(elem)
  

# Only register if xml.etree is available
if ET is not None:
  serializers.register(GenericXMLSerializer)

if __name__ == '__main__':
  if 0:
    try:
      raise Exception('Mosmaster!')
    except:
      from smisk.mvc.http import InternalServerError
      print GenericXMLSerializer.serialize_error(InternalServerError, {
        'code': 123,
        'description': u'something really bad just went down'
      }, 'utf-8')
      import sys
      sys.exit(0)
  charset, xmlstr = GenericXMLSerializer.serialize(dict(
      string = "Doodah",
      items = ["A", "B", 12, 32.1, [1, 2, 3, None]],
      float = 0.1,
      integer = 728,
      dict = {
        "str": "<hello & hi there!>",
        "unicode": u'M\xe4ssig, Ma\xdf',
        "true value": True,
        "false value": False,
      },
      data = data("<binary gunk>"),
      more_data = data("<lots of binary gunk>" * 10),
      date = datetime.now(),
    ), 'utf-8')
  print xmlstr
  from StringIO import StringIO
  print repr(GenericXMLSerializer.unserialize(StringIO(xmlstr)))

########NEW FILE########
__FILENAME__ = xmlrpc
# encoding: utf-8
'''
XML-RPC serialization
'''
from smisk.core import Application
from smisk.mvc import http
from smisk.serialization import serializers, Serializer
from xmlrpclib import dumps, loads, Fault

class XMLRPCSerializer(Serializer):
  '''XML-based Remote Procedure Call
  '''
  
  name = 'XML-RPC'
  extensions = ('xmlrpc',)
  media_types = ('application/rpc+xml', 'application/xml-rpc+xml')
  charset = 'utf-8'
  handles_empty_response = True
  can_serialize = True
  can_unserialize = True
  
  respect_method_name = True
  '''Enable translating <methodName> tag into request path
  '''
  
  @classmethod
  def serialize(cls, params, charset):
    return (charset, dumps((params,), methodresponse=True, encoding=charset, allow_none=True))
  
  @classmethod
  def serialize_error(cls, status, params, charset=None):
    msg = u'%s: %s' % (params['name'], params['description'])
    return (charset, dumps(Fault(params['code'], msg), encoding=charset))
  
  @classmethod
  def unserialize(cls, file, length=-1, encoding=None):
    # return (list args, dict params)
    params, method_name = loads(file.read(length))
    
    # Override request path with mathodName. i.e. method.name -> /method/name
    if cls.respect_method_name:
      if method_name is None:
        raise http.InternalServerError(
          'respect_method_name is enabled but request did not include methodName')
      Application.current.request.url.path = '/'+'/'.join(method_name.split('.'))
    
    args = []
    kwargs = {}
    if len(params) > 0:
      for o in params:
        if isinstance(o, dict):
          kwargs.update(o)
        else:
          args.append(o)
    
    return (args, kwargs)
  

serializers.register(XMLRPCSerializer)

########NEW FILE########
__FILENAME__ = xspf
# encoding: utf-8
'''XSPF v1.0 serialization.

:see: `XSPF v1.0 <http://xspf.org/xspf-v1.html>`__
'''
import base64
from smisk.serialization.xmlbase import *
from datetime import datetime
from smisk.util.DateTime import DateTime
from types import *

__all__ = [
  'XSPFSerializationError',
  'XSPFUnserializationError',
  'XSPFSerializer']

class XSPFSerializationError(XMLSerializationError):
  pass

class XSPFUnserializationError(XMLUnserializationError):
  pass

class XSPFSerializer(XMLSerializer):
  '''XML Shareable Playlist Format
  '''
  name = 'XSPF'
  extensions = ('xspf',)
  media_types = ('application/xspf+xml',)
  charset = 'utf-8'
  can_serialize = True
  can_unserialize = True
  
  xml_default_ns = 'http://xspf.org/ns/0/'
  xml_root_name = 'playlist'
  xml_root_attrs = {'version':'1.0'}
  
  BASE_TAGS = (
    'title',
    'creator',
    'annotation',
    'info',
    'location',
    'identifier',
    'image',
    'date',
    'license',
    'attribution',
    'link',
    'meta',
    'extension',
    'trackList',
  )
  TRACK_TEXT_TAGS = (
    'location',
    'identifier',
    'title',
    'creator',
    'annotation',
    'info',
    'image',
    'album',
  )
  TRACK_INT_TAGS = (
    'trackNum',
    'duration',
  )
  TRACK_XML_TAGS = (
    'extension',
  )
  TRACK_META_TAGS = (
    'link',
    'content',
  )
  
  # Reading
  
  @classmethod
  def parse_document(cls, elem):
    playlist = {}
    for child in elem.getchildren():
      k,ns = cls.xml_tag(child)
      if k == 'trackList':
        v = cls.parse_trackList(child)
      elif k == 'date':
        v = DateTime.parse_xml_schema_dateTime(child.text)
      elif k in cls.BASE_TAGS:
        v = child.text
      playlist[k] = v
    return playlist
  
  @classmethod
  def parse_trackList(cls, elem):
    tracks = []
    for child in elem.getchildren():
      if cls.xml_tag(child)[0] == 'track':
        tracks.append(cls.parse_track(child))
    return tracks
  
  @classmethod
  def parse_track(cls, elem):
    track = {}
    for child in elem.getchildren():
      k,ns = cls.xml_tag(child)
      if k in cls.TRACK_TEXT_TAGS:
        track[k] = child.text
      elif k in cls.TRACK_INT_TAGS:
        track[k] = int(child.text)
      elif k in cls.TRACK_META_TAGS:
        track[k] = cls.prase_track_meta(child)
      elif k in cls.TRACK_XML_TAGS:
        track[k] = child
    return track
  
  @classmethod
  def parse_track_meta(cls, elem):
    return {
      'rel':elem.get('rel'),
      'content':elem.text
    }
  
  # Writing
  
  @classmethod
  def build_document(cls, obj):
    root = ET.Element(cls.xml_root_name, **cls.xml_root_attrs)
    for k,v in obj.items():
      if k == 'trackList':
        root.append(cls.build_trackList(v))
      else:
        if isinstance(v, datetime):
          v = DateTime(v).as_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
        elif not isinstance(v, basestring):
          v = str(v)
        root.append(cls.xml_mktext(k, v))
    return root
  
  @classmethod
  def build_trackList(cls, iterable):
    e = ET.Element('trackList')
    if iterable:
      for track in iterable:
        e.append(cls.build_track(track))
    return e
  
  @classmethod
  def build_track(cls, track):
    e = ET.Element('track')
    for k,v in track.items():
      if not isinstance(v, basestring):
        v = str(v)
      e.append(cls.xml_mktext(k, v))
    return e
  
  # Encoding errors
  
  @classmethod
  def serialize_error(cls, status, params, charset):
    from smisk.core import request
    if request:
      identifier = unicode(request.url) + u'#'
    else:
      identifier = u'smisk:'
    identifier += u'error:%d' % status.code
    return cls.serialize({
      u'title':      params['name'],
      u'annotation': params['description'],
      u'identifier': identifier,
      u'trackList':  None
    }, charset)
  

# Only register if xml.etree is available
if ET is not None:
  serializers.register(XSPFSerializer)

if __name__ == '__main__':
  if 0:
    try:
      raise Exception('Mosmaster!')
    except:
      import sys
      from smisk.mvc.http import InternalServerError
      print XSPFSerializer.serialize_error(InternalServerError, {}, 'utf-8')
  charset, xmlstr = XSPFSerializer.serialize({
    'title': 'Spellistan frum hell',
    'creator': 'rasmus',
    'date': DateTime.now(),
    'trackList': (
      {
        'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'title': 'Go Crazy (feat. Majida)',
        'creator': 'Armand Van Helden',
        'album': 'Ghettoblaster',
        'trackNum': 1,
        'duration': 410000
      },
      {
        'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'title': 'Go Crazy2 (feat. Majida)',
        'creator': 'Armand Van Helden2',
        'album': 'Ghettoblaster2',
        'trackNum': 2,
        'duration': 410002
      },
      {
        'location': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'identifier': 'spotify:track:0yR57jH25o1jXGP4T6vNGR',
        'title': 'Go Crazy3 (feat. Majida)',
        'creator': 'Armand Van Helden3',
        'album': 'Ghettoblaster3',
        'trackNum': 3,
        'duration': 410007
      },
    )
  }, 'utf-8')
  print xmlstr
  from StringIO import StringIO
  print repr(XSPFSerializer.unserialize(StringIO(xmlstr)))

########NEW FILE########
__FILENAME__ = yaml_serial
# encoding: utf-8
'''
YAML: Human-readable data serialization

:see: `YAML 1.1 <http://yaml.org/spec/1.1/>`__
:requires: `PyYAML <http://pyyaml.org/wiki/PyYAML>`__
'''
import sys, logging
log = logging.getLogger(__name__)
from smisk.serialization import serializers, Serializer, data as opaque_data
__all__ = ['YAMLSerializer', 'yaml']
try:
  import yaml
  try:
    from yaml import CSafeLoader as Loader, CSafeDumper as Dumper
  except ImportError:
    from yaml import SafeLoader as Loader, SafeDumper as Dumper
  __all__.extend(['Loader', 'Dumper'])
except ImportError:
  yaml = None

class YAMLSerializer(Serializer):
  '''Human-readable data serialization
  '''
  name = 'YAML'
  extensions = ('yaml',)
  media_types = ('application/x-yaml', 'text/yaml', 'text/x-yaml')
  charset = 'utf-8'
  supported_charsets = ('utf-8', 'utf-16-be', 'utf-16-le', None) # None == unicode
  can_serialize = True
  can_unserialize = True
  
  @classmethod
  def serialize(cls, params, charset=None):
    if charset not in cls.supported_charsets:
      charset = cls.charset
    return (charset, yaml.dump(params, encoding=charset, Dumper=Dumper, allow_unicode=True))
  
  @classmethod
  def unserialize(cls, file, length=-1, charset=None):
    # return (collection args, dict params)
    s = file.read(length)
    if charset:
      s = s.decode(charset, cls.unicode_errors)
    st = yaml.load(s, Loader=Loader)
    if isinstance(st, dict):
      return (None, st)
    elif isinstance(st, list):
      return (st, None)
    else:
      return ((st,), None)
  

# Register if we have a backing YAML implementation
if yaml is not None:
  serializers.register(YAMLSerializer)
  
  # support for serializing Entities:
  from smisk.mvc.model import Entity
  def entity_serializer(dumper, entity):
    return dumper.represent_data(entity.to_dict())
  
  log.debug('registering smisk.mvc.model.Entity YAML serializer (W)')
  Dumper.add_multi_representer(Entity, entity_serializer)
  
  # support for serializing data:
  def data_serializer(dumper, dat):
    return dumper.represent_scalar(u'!data', dat.encode())
  
  def data_unserializer(loader, datatype, node):
    return opaque_data.decode(node.value)
  
  log.debug('registering smisk.serialization.data YAML serializer (RW)')
  Dumper.add_multi_representer(opaque_data, data_serializer)
  Loader.add_multi_constructor(u'!data', data_unserializer)


if __name__ == '__main__':
  data = {
    'message': 'Hello worlds',
    'internets': [
      'interesting',
      'lolz',
      42.0,
      {
        'abcdata': opaque_data('xyz detta överförs binärt'),
        'tubes': [1,3,16,18,24],
        'persons': True,
        u'me agåain': {
          'message': 'Hello worlds',
          'internets': [
            'interesting',
            'lolz',
            42.0,
            {
              'tubes': [1,3,16,18,24],
              'persons': True
            }
          ]
        }
      }
    ]
  }
  s = YAMLSerializer.serialize(data)[1]
  print s
  from StringIO import StringIO
  print repr(YAMLSerializer.unserialize(StringIO(s)))

########NEW FILE########
__FILENAME__ = session
# encoding: utf-8
'''HTTP session store protocol.
'''

class Store:
  '''
  Session store interface definition.
  
  :type ttl:  int
  :type name: string
  '''
  
  ttl = 900
  name = 'SID'
  
  def read(self, session_id):
    '''
    Return the data associated with a session id.
    
    Called maximum once per *HTTP transaction*.
    
    If there is no session associated with ``session_id``, this method is
    responsible for and session initialization required by the underyling
    storage model.
    
    In the case where there is no data previously associated with the session
    id, this method should return None.
    
    :param  session_id: Session ID
    :type   session_id: string
    :rtype: object
    '''
    raise NotImplementedError
  
  def write(self, session_id, data):
    '''
    Associate data with a session id.
    
    Called at least once per *HTTP transaction* which has an active session.
    
    Normally, this will be called once, at the end of the *HTTP transaction*.
    This method should associate ``data`` with ``session_id``.
    
    :param  session_id:  Session ID
    :type   session_id:  string
    :param  data:        Data to be associated with ``session_id``
    :type   data:        object
    :rtype: None
    '''
    raise NotImplementedError
  
  def refresh(self, session_id):
    '''
    Refresh session.
    
    Called when a session is known to be in active use but has not been
    modified.
    
    For example, the built-in file-based session stores implementation
    uses ``touch session-file`` in order to refresh the sessions modified time,
    which is later used in the garbage collector-based model to detect dead
    sessions.
    
    :param  session_id:  Session ID
    :type   session_id:  string
    :rtype: None
    '''
    raise NotImplementedError
  
  def destroy(self, session_id):
    '''
    Destroy/delete/invalidate any session associated with ``session_id``.
    
    May be called any number of times during a *HTTP transaction*.
    
    :param  session_id: Session ID
    :type   session_id: string
    :rtype: None
    '''
    raise NotImplementedError
  


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.config import *
import logging
log = logging.getLogger(__name__)
FILESDIR = os.path.join(os.path.dirname(__file__), 'config-support')

class ConfigTests(TestCase):
  def test1_basics(self):
    log.info('--RESET--')
    config.reset()
    self.assertTrue(isinstance(config, dict))
    self.assertTrue(isinstance(config.sources, list))
    self.assertTrue(isinstance(config.default_symbols, dict))
    self.assertTrue(isinstance(config.defaults, dict))
    self.assertEquals(config.get('sdg', None), None)
  
  def _load_simple(self):
    config.loads('''
    "some_key": 456,
    "logging": {
      "": "INFO",
      'foo.bar': INFO
    }
    ''')
  
  def test2_simple_loads_and_get(self):
    log.info('--RESET--')
    config.reset()
    self._load_simple()
    self.assertEquals(config['some_key'], 456)
    self.assertEquals(config['logging'], {'foo.bar': logging.INFO, '':'INFO'})
    self.assertRaises(KeyError, lambda: config['not_here'])
  
  def _load_simple_overload(self):
    config.loads('''
    "some_key": 123,
    "logging": {
      'foo.bar': ERROR
    }''')
  
  def test03_overload(self):
    log.info('--RESET--')
    config.reset()
    self._load_simple()
    self._load_simple_overload()
    self.assertEquals(config['some_key'], 123)
    self.assertEquals(config['logging'], {'foo.bar': logging.ERROR, '':'INFO'})
    self.assertEquals(config['logging']['foo.bar'], logging.ERROR)
  
  def test04_defaults(self):
    log.info('--RESET--')
    config.reset()
    self._load_simple()
    self._load_simple_overload()
    self.assertEquals(config.defaults, {})
    config.defaults = {'my_key': 'internets'}
    self.assertEquals(config.defaults, {'my_key': 'internets'})
    self.assertTrue('my_key' in config)
    self.assertEquals(config['my_key'], 'internets')
    config.loads('"my_key": 123')
    self.assertEquals(config['my_key'], 123)
    config.reload()
    self.assertEquals(config['my_key'], 123)
  
  def test05_file_basics(self):
    log.info('--RESET--')
    config.reset()
    config.load(os.path.join(FILESDIR, 'simple.conf'))
    self.assertContains(config.keys(), ['key1', 'key2', 'key3'])
    self.assertEquals(config['key1'], 'value1')
    self.assertEquals(config['key2'], 12345.6789)
    self.assertEquals(config['key3'], [1,2,3,'4','5'])
  
  def test06_file_include(self):
    log.info('--RESET--')
    config.reset()
    config.load(os.path.join(FILESDIR, 'include.conf'))
    self.assertEquals(config['key1'], 'value1')
    self.assertEquals(config['key2'], 12345.6789)
    self.assertEquals(config['key3'], [1,2,3,'4','5'])
    self.assertEquals(config['key4'], 'Hello')
  
  def test07_file_include_max(self):
    log.info('--RESET--')
    config.reset()
    config.max_include_depth = 5
    path = os.path.join(FILESDIR, 'include-recursive.conf')
    # should raise RuntimeError: maximum include depth exceeded
    self.assertRaises(RuntimeError, lambda: config.load(path))
  
  def test08_file_include_deep(self):
    log.info('--RESET--')
    config.reset()
    config.max_include_depth = 5
    config.load(os.path.join(FILESDIR, 'include-deep1.conf'))
    self.assertEquals(config['key1'], 1)
    self.assertEquals(config['key2'], 22)
    self.assertEquals(config['key3'], 333)
    self.assertEquals(config['key4'], 4444)
    self.assertEquals(config['key5'], 55555)
  
  def test09_file_inherit(self):
    log.info('--RESET--')
    config.reset()
    config.load(os.path.join(FILESDIR, 'inherit.conf'))
    self.assertEquals(config['key1'], 'value1')
    self.assertEquals(config['key2'], 987654) # difference from test6_file_include
    self.assertEquals(config['key3'], [1,2,3,'4','5'])
    self.assertEquals(config['key4'], 'Hello')
  
  def test10_file_inherit_deep(self):
    log.info('--RESET--')
    config.reset()
    config.max_include_depth = 5
    config.load(os.path.join(FILESDIR, 'inherit-deep5.conf'))
    self.assertEquals(config['key1'], 1)
    self.assertEquals(config['key2'], 22)
    self.assertEquals(config['key3'], 333)
    self.assertEquals(config['key4'], 4444)
    self.assertEquals(config['key5'], 55555)
  
  def test11_file_include_glob(self):
    log.info('--RESET--')
    config.reset()
    config.load(os.path.join(FILESDIR, 'include-glob.conf'))
    self.assertEquals(config['key1'], 1)
    self.assertEquals(config['key2'], 22)
    self.assertEquals(config['key3'], 333)
    self.assertEquals(config['key4'], 4444)
    self.assertEquals(config['key5'], 55555)
  
  def test12_file_inherit_glob(self):
    log.info('--RESET--')
    config.reset()
    config.max_include_depth = 5
    config.load(os.path.join(FILESDIR, 'inherit-glob.conf'))
    self.assertEquals(config['key1'], 1)
    self.assertEquals(config['key2'], 22)
    self.assertEquals(config['key3'], 333)
    self.assertEquals(config['key4'], 4444)
    self.assertEquals(config['key5'], 55555)
  


#logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def suite():
  suites = []
  if os.path.isdir(FILESDIR):
    suites = [unittest.makeSuite(ConfigTests)]
  return unittest.TestSuite(suites)

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = url
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.core import URL

class URLTests(TestCase):
  def test_encode_decode(self):
    raw = "http://abc.se:12/mos/jäger/grek land/hej.html?mos=japp&öland=nej#ge-mig/då";
    escaped = URL.escape(raw)
    self.assertEquals(escaped,
      'http%3A//abc.se%3A12/mos/j%C3%A4ger/grek%20land/hej.html'\
      '?mos=japp&%C3%B6land=nej%23ge-mig/d%C3%A5')
    encoded = URL.encode(raw)
    self.assertEquals(encoded,
      'http%3A%2F%2Fabc.se%3A12%2Fmos%2Fj%C3%A4ger%2Fgrek%20land%2Fhej.html%3Fmos%3Djapp'\
      '%26%C3%B6land%3Dnej%23ge-mig%2Fd%C3%A5')
    self.assertEquals(URL.decode(escaped), raw)
    self.assertEquals(URL.decode(encoded), raw)
    self.assertEquals(URL.unescape(escaped), URL.decode(escaped))
    self.assertEquals(URL.decode("foo%2Bbar@internets.com"), "foo+bar@internets.com")
  
  
  def test_encode_decode_string_type(self):
    self.assertEquals(type(URL.encode(u"foo+bar@internets.com")), type(u"foo%2Bbar@internets.com"))
    self.assertEquals(type(URL.encode("foo+bar@internets.com")), type("foo%2Bbar@internets.com"))
    self.assertEquals(type(URL.escape(u"foo+bar@internets.com")), type(u"foo%2Bbar@internets.com"))
    self.assertEquals(type(URL.escape("foo+bar@internets.com")), type("foo%2Bbar@internets.com"))
    self.assertEquals(type(URL.decode(u"foo%2Bbar@internets.com")), type(u"foo+bar@internets.com"))
    self.assertEquals(type(URL.decode("foo%2Bbar@internets.com")), type("foo+bar@internets.com"))
  
  
  def test_clean_strings(self):
    # Should be unmodified and retain pointers
    raw = 'hello/john'
    escaped = URL.escape(raw)
    self.assertEquals(escaped, raw)
    self.assertEquals(id(escaped), id(raw))
    
    raw = 'hello_john'
    encoded = URL.encode(raw)
    self.assertEquals(encoded, raw)
    self.assertEquals(id(encoded), id(raw))
  
  
  def test_parse(self):
    u = URL('http://john:secret@www.mos.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.scheme, 'http')
    self.assertEquals(u.user, 'john')
    self.assertEquals(u.password, 'secret')
    self.assertEquals(u.host, 'www.mos.tld')
    self.assertEquals(u.path, '/some/path.ext')
    self.assertEquals(u.query, 'arg1=245&arg2=hej%20du')
    self.assertEquals(u.fragment, 'chapter5')
    
    u = URL('https://john@www.mos.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.scheme, 'https')
    self.assertEquals(u.user, 'john')
    self.assertEquals(u.password, None)
    self.assertEquals(u.host, 'www.mos.tld')
    self.assertEquals(u.path, '/some/path.ext')
    self.assertEquals(u.query, 'arg1=245&arg2=hej%20du')
    self.assertEquals(u.fragment, 'chapter5')
    
    u = URL('http://www.mos.tld/some/path.ext?arg1=245&arg2=hej%20du-chapter5')
    self.assertEquals(u.query, 'arg1=245&arg2=hej%20du-chapter5')
    self.assertEquals(u.fragment, None)
    
    u = URL('http://www.mos.tld/some/path.ext?arg1=245&arg2=hej%20du?chapter5')
    self.assertEquals(u.query, 'arg1=245&arg2=hej%20du?chapter5')
    self.assertEquals(u.fragment, None)
    
    u = URL('http://www.mos.tld/some/path.ext?')
    self.assertEquals(u.query, '')
    self.assertEquals(u.fragment, None)
    
    u = URL('http://www.mos.tld/some/path.ext#arg1=245&arg2=hej%20du-chapter5')
    self.assertEquals(u.query, None)
    self.assertEquals(u.fragment, 'arg1=245&arg2=hej%20du-chapter5')
    
    u = URL('http://www.mos.tld/some/path.ext#arg1=245&arg2=hej%20du?chapter5')
    self.assertEquals(u.query, None)
    self.assertEquals(u.fragment, 'arg1=245&arg2=hej%20du?chapter5')
    
    u = URL('http://www.mos.tld/some/path.ext#')
    self.assertEquals(u.query, None)
    self.assertEquals(u.fragment, '')
  
  
  def test_decompose_query(self):
    u = URL('http://a/?email=foo%2Bbar@internets.com&&stale_key&&mos=abc&mos=123&&&')
    q = URL.decompose_query(u.query)
    self.assertEquals(q['email'], "foo+bar@internets.com")
    self.assertEquals(q['stale_key'], None)
    self.assertEquals(q['mos'], ['abc', '123'])
    self.assertContains(q.keys(), ['email', 'stale_key', 'mos'])
  
  
  def test_decompose_query_decode(self):
    # explicitly decode iso-8859-1 text:
    u = URL('http://a/?name=%E5%E4%F6')
    q = URL.decompose_query(u.query, charset='latin_1', tolerant=False)
    self.assertTrue(isinstance(q['name'], unicode))
    self.assertEquals(q['name'], u'\xe5\xe4\xf6')
    
    # explicitly decode utf-8 text:
    u = URL('http://a/?name=%C3%A5%C3%A4%C3%B6%EF%A3%BF')
    q = URL.decompose_query(u.query, charset='utf-8')
    self.assertTrue(isinstance(q['name'], unicode))
    self.assertEquals(q['name'], u'\xe5\xe4\xf6\uf8ff')
    
    # fail to decode iso-8859-1 as utf-8 (tolerant=False):
    u = URL('http://a/?name=%E5%E4%F6')
    self.assertRaises(UnicodeDecodeError, 
      lambda: URL.decompose_query(u.query, charset='utf-8', tolerant=False))
    # repeating the above with tolerant=True (default value) should implicitly 
    # use the latin-1 charset:
    q = URL.decompose_query(u.query, charset='utf-8')
    self.assertTrue(isinstance(q['name'], unicode))
    self.assertEquals(q['name'], u'\xe5\xe4\xf6')
  
  
  def test_to_s_1(self):
    raw = 'http://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5'
    u = URL(raw)
    self.assertEquals(u.to_s(), raw)
    self.assertEquals(str(u), raw)
    self.assertEquals(unicode(u), unicode(raw))
  
  
  def test_to_s_2_port(self):
    u = URL('http://fisk.tld:1983/some/path')
    self.assertEquals(u.to_s(port=0), 'http://fisk.tld/some/path')
    self.assertEquals(u.to_s(port80=0), 'http://fisk.tld:1983/some/path')
    self.assertEquals(u.to_s(port=0, port80=1), 'http://fisk.tld/some/path')
    u = URL('http://fisk.tld:80/some/path')
    self.assertEquals(u.to_s(port=0), 'http://fisk.tld/some/path')
    self.assertEquals(u.to_s(port80=0), 'http://fisk.tld/some/path')
    self.assertEquals(u.to_s(port=0, port80=1), 'http://fisk.tld/some/path')
  
  
  def test_to_s_3(self):
    u = URL('http://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    
    # meet and greet
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=1, port=1, path=1, query=1, fragment=1),
      'john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=1, port=1, path=1, query=1, fragment=1),
      'http://fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=1, port=1, path=1, query=1, fragment=1),
      'http://john@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=0, port=1, path=1, query=1, fragment=1),
      'http://john:secret@:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=0, path=1, query=1, fragment=1),
      'http://john:secret@fisk.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=0, query=1, fragment=1),
      'http://john:secret@fisk.tld:1983?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=1, query=0, fragment=1),
      'http://john:secret@fisk.tld:1983/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=1, query=1, fragment=0), 
      'http://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no scheme
    self.assertEquals(u.to_s(scheme=0, user=0, password=1, host=1, port=1, path=1, query=1, fragment=1),
      'fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=0, host=1, port=1, path=1, query=1, fragment=1),
      'john@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=0, port=1, path=1, query=1, fragment=1),
      'john:secret@:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=1, port=0, path=1, query=1, fragment=1),
      'john:secret@fisk.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=1, port=1, path=0, query=1, fragment=1),
      'john:secret@fisk.tld:1983?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=1, port=1, path=1, query=0, fragment=1),
      'john:secret@fisk.tld:1983/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=0, user=1, password=1, host=1, port=1, path=1, query=1, fragment=0),
      'john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no user
    self.assertEquals(u.to_s(scheme=1, user=0, password=0, host=1, port=1, path=1, query=1, fragment=1),
      'http://fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=0, port=1, path=1, query=1, fragment=1),
      'http://:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=1, port=0, path=1, query=1, fragment=1),
      'http://fisk.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=1, port=1, path=0, query=1, fragment=1),
      'http://fisk.tld:1983?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=1, port=1, path=1, query=0, fragment=1),
      'http://fisk.tld:1983/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=0, password=1, host=1, port=1, path=1, query=1, fragment=0),
      'http://fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no password
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=0, port=1, path=1, query=1, fragment=1),
      'http://john@:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=1, port=0, path=1, query=1, fragment=1),
      'http://john@fisk.tld/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=1, port=1, path=0, query=1, fragment=1),
      'http://john@fisk.tld:1983?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=1, port=1, path=1, query=0, fragment=1),
      'http://john@fisk.tld:1983/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=0, host=1, port=1, path=1, query=1, fragment=0),
      'http://john@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no host
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=0, port=0, path=1, query=1, fragment=1),
      'http://john:secret@/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=0, port=1, path=0, query=1, fragment=1),
      'http://john:secret@:1983?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=0, port=1, path=1, query=0, fragment=1),
      'http://john:secret@:1983/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=0, port=1, path=1, query=1, fragment=0),
      'http://john:secret@:1983/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no port
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=0, path=0, query=1, fragment=1),
      'http://john:secret@fisk.tld?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=0, path=1, query=0, fragment=1),
      'http://john:secret@fisk.tld/some/path.ext#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=0, path=1, query=1, fragment=0),
      'http://john:secret@fisk.tld/some/path.ext?arg1=245&arg2=hej%20du')
    
    # no path
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=0, query=0, fragment=1),
      'http://john:secret@fisk.tld:1983#chapter5')
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=0, query=1, fragment=0),
      'http://john:secret@fisk.tld:1983?arg1=245&arg2=hej%20du')
    
    # no query
    self.assertEquals(u.to_s(scheme=1, user=1, password=1, host=1, port=1, path=1, query=0, fragment=0),
      'http://john:secret@fisk.tld:1983/some/path.ext')
  
  
  def test_to_s_4(self):
    u = URL('http://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(scheme='ftp'), 
      'ftp://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(user='bob'),
      'http://bob:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(password='bob'),
      'http://john:bob@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(host='bob'),
      'http://john:secret@bob:1983/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(port=123),
      'http://john:secret@fisk.tld:123/some/path.ext?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(user=0, path='/internets'),
      'http://fisk.tld:1983/internets?arg1=245&arg2=hej%20du#chapter5')
    self.assertEquals(u.to_s(query='grekisk_afton=yes'),
      'http://john:secret@fisk.tld:1983/some/path.ext?grekisk_afton=yes#chapter5')
    self.assertEquals(u.to_s(fragment='m0'),
      'http://john:secret@fisk.tld:1983/some/path.ext?arg1=245&arg2=hej%20du#m0')
  


def suite():
  return unittest.TestSuite([
    unittest.makeSuite(URLTests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = xml
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
import smisk.core.xml as xml

class XMLTests(TestCase):
  def setUp(self):
    pass
  
  def test_encode(self):
    #Encode/escape unsafe character in XML
    encoded = xml.escape('Some <document> with strings & characters which should be "escaped"')
    expected = 'Some &lt;document&gt; with strings &amp; characters which should be &quot;escaped&quot;'
    self.assertEquals(encoded, expected)
  
  
  def test_decode(self):
    #Decode/unescape entities in XML
    decoded = xml.unescape('Some &lt;document&gt; with strings &amp; characters which should be'\
      ' &quot;escaped&quot;')
    expected = 'Some <document> with strings & characters which should be "escaped"'
    self.assertEquals(decoded, expected)
  
  
  def test_string_type_integrity(self):
    #Assure the same string type (bytes or unicode) is output as was input
    self.assertEquals(type(xml.escape(u'foo<bar>"baz"&')), type(u"foo&lt;bar&gt;&quot;baz&quot;&amp;"))
    self.assertEquals(type(xml.escape('foo<bar>"baz"&')), type("foo&lt;bar&gt;&quot;baz&quot;&amp;"))
    self.assertEquals(type(xml.escape(u"foo&lt;bar&gt;&quot;baz&quot;&amp;")), type(u'foo<bar>"baz"&'))
    self.assertEquals(type(xml.escape("foo&lt;bar&gt;&quot;baz&quot;&amp;")), type('foo<bar>"baz"&'))
  

def suite():
  return unittest.TestSuite([
    unittest.makeSuite(XMLTests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = inflection
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.inflection import inflection as en

class English(TestCase):
  def test_plural(self):
    assert en.pluralize(u'mouse') == u'mice'
    assert en.pluralize(u'train') == u'trains'
    assert en.pluralize(u'commotion') == u'commotion'
    assert en.pluralize(u'cat') == u'cats'
  def test_camel(self):
    assert en.camelize(u'moder_controller/barn') == u'ModerController.Barn'
  def test_human(self):
    assert en.humanize(u'employee_salary') == u'Employee salary'
    assert en.humanize(u'author_id') == u'Author'
  def test_demodule(self):
    assert en.demodulize(u'ActiveRecord.CoreExtensions.String.Inflection') == u'Inflection'
    assert en.demodulize(u'Inflection') == u'Inflection'
  def test_table(self):
    assert en.tableize(u'RawScaledScorer') == u'raw_scaled_scorers'
    assert en.tableize(u'egg_and_ham') == u'egg_and_hams'
    assert en.tableize(u'fancyCategory') == u'fancy_categories'
  def test_class(self):
    assert en.classify(u'egg_and_hams') == u'EggAndHam'
    assert en.classify(u'post') == u'Post'
    assert en.classify(u'categories') == u'Category'
  def test_foreignKey(self):
    assert en.foreignKey(u'Message') == u'message_id'
    assert en.foreignKey(u'Message', False) == u'messageid'
    assert en.foreignKey(u'admin.Post') == u'post_id'
  def test_ordinal(self):
    assert en.ordinalize(1) == u"1st"
    assert en.ordinalize(2) == u"2nd"
    assert en.ordinalize(3) == u"3rd"
    assert en.ordinalize(8) == u"8th"
    assert en.ordinalize(12) == u"12th"
    assert en.ordinalize(1002) == u"1002nd"
    assert en.ordinalize(9876) == u"9876th"
  def test_misc(self):
    assert en.underscore(u'ModerController.Barn') == u'moder_controller/barn'
  

#from smisk.inflection.sv import inflection as sv
#class Swedish(TestCase):
#  def test_plural(self):
#    assert sv.pluralize(u'mus') == u'möss'
#    assert sv.pluralize(u'train') == u'trainer'
#    assert sv.pluralize(u'post') == u'poster'
#    assert sv.pluralize(u'person') == u'personer'
#  
#  def test_dual(self):
#    def t(singular, plural):
#      #print singular, u"->", sv.pluralize(singular) + u',', plural, u'->', sv.singularize(plural)
#      assert sv.pluralize(singular) == plural
#      assert sv.singularize(plural) == singular
#    t(u"bil", u"bilar")
#    t(u"båt", u"båtar")
#    t(u"katt", u"katter")
#    t(u"peng", u"pengar")
#    t(u"man", u"män")
#    t(u"person", u"personer")
#    t(u"huvud", u"huvuden")
#    t(u"folk", u"folk")
#    t(u"vittne", u"vittnen")
#    t(u"morsa", u"morsor")
#    t(u"liten", u"små")
#    t(u"stor", u"stora")
#    t(u"ny", u"nya")
#    t(u"rik", u"rika")
#    t(u"dum", u"dumma")
#    t(u"stum", u"stumma")
#    t(u"kvinna", u"kvinnor")
#    t(u"intressant", u"intressanta")
#    t(u"given", u"givna")
#    t(u"ven", u"vener")
#    t(u"hand", u"händer")
#    t(u"land", u"länder")
#    t(u"kviga", u"kvigor")
#    t(u"mun", u"munnar")
#    t(u"ros", u"rosor")
#    t(u"lus", u"löss")
#    t(u"mus", u"möss")
#    t(u"kust", u"kuster")
#    t(u"lust", u"lustar")
#    t(u"pojke", u"pojkar")
#    t(u"flicka", u"flickor")
#    t(u"snorkel", u"snorklar")
#  
#  def test_ordinal(self):
#    assert sv.ordinalize(1) == u"1:a"
#    assert sv.ordinalize(2) == u"2:a"
#    assert sv.ordinalize(3) == u"3:e"
#    assert sv.ordinalize(921.3) == u"921:a"
#    assert sv.ordinalize(500) == u"500:e"
#  

def suite():
  return unittest.TestSuite([
    unittest.makeSuite(English),
    #unittest.makeSuite(Swedish),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *
from smisk.mvc.model import *
from smisk.ipc.bsddb import shared_dict
from smisk.config import config

class root(Controller):
  def __init__(self):
    self.entries = shared_dict(persistent=False)
  
  @expose(methods='GET')
  def __call__(self):
    '''List available entries.
    '''
    response.headers.append('X-Pid: %d' % os.getpid())
    return {'entries': self.entries}
  
  @expose(methods=('POST', 'PUT'))
  def set(self, key, value):
    '''Create or modify an entry.
    '''
    response.headers.append('X-Pid: %d' % os.getpid())
    self.entries[key] = value
  
  @expose(methods='GET')
  def get(self, key):
    '''Get value for key.
    '''
    response.headers.append('X-Pid: %d' % os.getpid())
    try:
      return {'value': self.entries[key]}
    except KeyError:
      raise http.NotFound('no value associated with key %r' % key)
  
  @expose(methods='DELETE')
  def delete(self, key):
    '''Remove entry.
    '''
    response.headers.append('X-Pid: %d' % os.getpid())
    if key not in self.entries:
      raise http.NotFound('no such entry %r' % key)
    del self.entries[key]
  

if __name__ == '__main__':
  config.load(os.path.join(os.path.dirname(__file__), 'app.conf'))
  main()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# encoding: utf-8
from smisk.mvc import *

class root(Controller):
  def __call__(self, **params):
    return {'request parameters': params}

main()

########NEW FILE########
__FILENAME__ = control
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from test_matter import *
from smisk.mvc.control import *

class misc_tests(TestCase):
  def test1_root_controller(self):
    self.assertEquals(root_controller(), root)
  
  def test2_controllers(self):
    self.assertContains(controllers(), (
      root(), level2(), level3(), level3B(), PostsController()
    ))
  
  def test3_method_origin(self):
    o = SpanishBass()
    self.assertEquals(method_origin(o.name), Animal)
    self.assertEquals(method_origin(o.color), Fish)
    self.assertEquals(method_origin(o.eats), Bass)
    self.assertEquals(method_origin(o.on_fiesta), SpanishBass)
    self.assertEquals(method_origin(o.sleeps), SpanishBass)
    o = EnglishBass()
    self.assertEquals(method_origin(o.cheese), EnglishBass)
    self.assertEquals(method_origin(o.on_fiesta), EnglishBass)
  
  def test4_leaf_visibility(self):
    # Visible:
    self.assertTrue(leaf_is_visible(root))
    self.assertTrue(leaf_is_visible(root.__call__))
    self.assertTrue(leaf_is_visible(root.func_on_root))
    self.assertTrue(leaf_is_visible(root.delegating_func_on_root))
    self.assertTrue(leaf_is_visible(level2))
    self.assertTrue(leaf_is_visible(level2.__call__))
    self.assertTrue(leaf_is_visible(level2.func_on_level2))
    self.assertTrue(leaf_is_visible(level2.level3)) # maybe should be False
    self.assertTrue(leaf_is_visible(level3))
    self.assertTrue(leaf_is_visible(level3.__call__))
    self.assertTrue(leaf_is_visible(level3.func_on_level3))
    self.assertTrue(leaf_is_visible(level3.func_on_level3_wonlykwa))
    self.assertTrue(leaf_is_visible(level2.delegating_func_on_root))
    self.assertTrue(leaf_is_visible(level3.delegating_func_on_root))
    self.assertTrue(leaf_is_visible(PostsController.delegating_func_on_root))
    self.assertTrue(leaf_is_visible(level2.foo_bar))
    # Invisible:
    self.assertFalse(leaf_is_visible(level2.func_on_root))
    self.assertFalse(leaf_is_visible(level3.func_on_level2))
    self.assertFalse(leaf_is_visible(level3B))
    self.assertFalse(leaf_is_visible(level3B.__call__))
    self.assertFalse(leaf_is_visible(level3.hidden_method_on_level3))
  
  def test5_controller_name(self):
    self.assertEquals(root.controller_name(), u'root')
    self.assertEquals(level2.controller_name(), u'level2')
    self.assertEquals(level3.controller_name(), u'level3')
    self.assertEquals(level3B.controller_name(), u'level-3-b')
    self.assertEquals(PostsController.controller_name(), u'posts')

class node_name_tests(TestCase):
  def test1_basic(self):
    self.assertEquals(node_name(root), u'')
    self.assertEquals(node_name(root.__call__), u'')
    self.assertEquals(node_name(root.func_on_root), u'func_on_root')
    self.assertEquals(node_name(root.delegating_func_on_root), u'delegating_func_on_root')
    self.assertEquals(node_name(level2), u'level2')
    self.assertEquals(node_name(level2.__call__), u'level2')
    self.assertEquals(node_name(level2.func_on_level2), u'func_on_level2')
    self.assertEquals(node_name(level2.level3), u'level3') # shadowed with purpose
    self.assertEquals(node_name(level3), u'level3')
    self.assertEquals(node_name(level3.__call__), u'level3')
    self.assertEquals(node_name(level3.func_on_level3), u'func_on_level3')
    self.assertEquals(node_name(level3.func_on_level3_wonlykwa), u'func_on_level3_wonlykwa')
  
  def test2_non_delegating(self):
    self.assertEquals(node_name(level2.func_on_root), None)
    self.assertEquals(node_name(level3.func_on_level2), None)
    self.assertEquals(node_name(level3B), None)
    self.assertEquals(node_name(level3B.__call__), None)
  
  def test3_delegating(self):
    self.assertEquals(node_name(level2.delegating_func_on_root), u'delegating_func_on_root')
    self.assertEquals(node_name(level3.delegating_func_on_root), u'delegating_func_on_root')
    self.assertEquals(node_name(PostsController.delegating_func_on_root), u'delegating_func_on_root')
  
  def test4_renamed(self):
    self.assertEquals(node_name(level2.foo_bar), u'foo-bar')
    self.assertNotEquals(node_name(level2.foo_bar), u'foo_bar')
  
  def test5_hidden(self):
    self.assertEquals(node_name(level3.hidden_method_on_level3), None)
    self.assertEquals(node_name(root.controller_name), None)
    self.assertEquals(node_name(Controller.controller_name), None)
    self.assertEquals(node_name(level2.special_methods), None)
  

class path_to_tests(TestCase):
  def test1_basic(self):
    self.assertEquals(path_to(root), [])
    self.assertEquals(path_to(root.__call__), [])
    self.assertEquals(path_to(root.func_on_root), [u'func_on_root'])
    self.assertEquals(path_to(root.delegating_func_on_root), [u'delegating_func_on_root'])
    self.assertEquals(path_to(level2), [u'level2'])
    self.assertEquals(path_to(level2.__call__), [u'level2'])
    self.assertEquals(path_to(level2.func_on_level2), [u'level2',u'func_on_level2'])
    self.assertEquals(path_to(level2.level3), [u'level2',u'level3']) # shadowed with purpose
    self.assertEquals(path_to(level3), [u'level2',u'level3'])
    self.assertEquals(path_to(level3.__call__), [u'level2',u'level3'])
    self.assertEquals(path_to(level3.func_on_level3), [u'level2',u'level3',u'func_on_level3'])
    self.assertEquals(path_to(level3.func_on_level3_wonlykwa), [u'level2',u'level3',u'func_on_level3_wonlykwa'])
  
  def test2_non_delegating(self):
    self.assertEquals(path_to(level2.func_on_root), None)
    self.assertEquals(path_to(level3.func_on_level2), None)
    self.assertEquals(path_to(level3B), None)
    self.assertEquals(path_to(level3B.__call__), None)
  
  def test3_delegating(self):
    self.assertEquals(path_to(level2.delegating_func_on_root),[u'level2',u'delegating_func_on_root'])
    self.assertEquals(path_to(level3.delegating_func_on_root),[u'level2',u'level3',u'delegating_func_on_root'])
    self.assertEquals(path_to(PostsController.delegating_func_on_root), [u'level2',u'level3',u'posts',u'delegating_func_on_root'])
  
  def test4_renamed(self):
    self.assertEquals(path_to(level2.foo_bar), [u'level2',u'foo-bar'])
    self.assertNotEquals(path_to(level2.foo_bar), [u'level2',u'foo_bar'])
  
  def test5_hidden(self):
    self.assertEquals(path_to(level3.hidden_method_on_level3), None)
  

class uri_for_tests(TestCase):
  def test1_basic(self):
    self.assertEquals(uri_for(root), u'/')
    self.assertEquals(uri_for(root.__call__), u'/')
    self.assertEquals(uri_for(root.func_on_root), u'/func_on_root')
    self.assertEquals(uri_for(root.delegating_func_on_root), u'/delegating_func_on_root')
    self.assertEquals(uri_for(level2), u'/level2/')
    self.assertEquals(uri_for(level2.__call__), u'/level2/')
    self.assertEquals(uri_for(level2.func_on_level2), u'/level2/func_on_level2')
    self.assertEquals(uri_for(level2.level3), u'/level2/level3') # shadowed with purpose
    self.assertEquals(uri_for(level3), u'/level2/level3/')
    self.assertEquals(uri_for(level3.__call__), u'/level2/level3/')
    self.assertEquals(uri_for(level3.func_on_level3), u'/level2/level3/func_on_level3')
    self.assertEquals(uri_for(level3.func_on_level3_wonlykwa), u'/level2/level3/func_on_level3_wonlykwa')
  
  def test2_non_delegating(self):
    self.assertEquals(uri_for(level2.func_on_root), None)
    self.assertEquals(uri_for(level3.func_on_level2), None)
    self.assertEquals(uri_for(level3B), None)
    self.assertEquals(uri_for(level3B.__call__), None)
  
  def test3_delegating(self):
    self.assertEquals(uri_for(level2.delegating_func_on_root), u'/level2/delegating_func_on_root')
    self.assertEquals(uri_for(level3.delegating_func_on_root), u'/level2/level3/delegating_func_on_root')
    self.assertEquals(uri_for(PostsController.delegating_func_on_root), u'/level2/level3/posts/delegating_func_on_root')
  
  def test4_renamed(self):
    self.assertEquals(uri_for(level2.foo_bar), u'/level2/foo-bar')
    self.assertNotEquals(uri_for(level2.foo_bar), u'/level2/foo_bar')
  
  def test5_hidden(self):
    self.assertEquals(uri_for(level3.hidden_method_on_level3), None)
  

class template_for_tests(TestCase):
  def test1_basic(self):
    self.assertEquals(template_for(root), [u'__call__'])
    self.assertEquals(template_for(root.__call__), [u'__call__'])
    self.assertEquals(template_for(root.func_on_root), [u'func_on_root'])
    self.assertEquals(template_for(root.delegating_func_on_root), [u'delegating_func_on_root'])
    self.assertEquals(template_for(level2), [u'level2',u'__call__'])
    self.assertEquals(template_for(level2.__call__), [u'level2',u'__call__'])
    self.assertEquals(template_for(level2.func_on_level2), [u'level2',u'func_on_level2'])
    self.assertEquals(template_for(level2.level3), [u'level2',u'level3']) # shadowed with purpose
    self.assertEquals(template_for(level3), [u'level2',u'level3',u'__call__'])
    self.assertEquals(template_for(level3.__call__), [u'level2',u'level3',u'__call__'])
    self.assertEquals(template_for(level3.func_on_level3), [u'level2',u'level3',u'func_on_level3'])
  
  def test2_non_delegating(self):
    self.assertEquals(template_for(level2.func_on_root), None)
    self.assertEquals(template_for(level3.func_on_level2), None)
    self.assertEquals(template_for(level3B), None)
    self.assertEquals(template_for(level3B.__call__), None)
  
  def test3_delegating(self):
    self.assertEquals(template_for(level2.delegating_func_on_root), [u'level2',u'delegating_func_on_root'])
    self.assertEquals(template_for(level3.delegating_func_on_root), [u'level2',u'level3',u'delegating_func_on_root'])
    self.assertEquals(template_for(PostsController.delegating_func_on_root), [u'level2',u'level3',u'posts',u'delegating_func_on_root'])
  
  def test4_renamed(self):
    self.assertEquals(template_for(level2.foo_bar), [u'level2',u'foo-bar'])
    self.assertNotEquals(template_for(level2.foo_bar), [u'level2',u'foo_bar'])
  
  def test5_hidden(self):
    self.assertEquals(template_for(level3.hidden_method_on_level3), None)
  


def suite():
  return unittest.TestSuite([
    unittest.makeSuite(misc_tests),
    unittest.makeSuite(node_name_tests),
    unittest.makeSuite(path_to_tests),
    unittest.makeSuite(uri_for_tests),
    unittest.makeSuite(template_for_tests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = routing
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.mvc import *
from smisk.mvc.routing import *
from smisk.mvc.control import *
import smisk.mvc.http as http

from test_matter import *

echo = False
if __name__ == '__main__':
  #echo = True
  print 'Printing out loud because __name__ == __main__ --> self.echo = True'

class RoutingTests(TestCase):
  '''Tests covering the `smisk.mvc.routing` module.
  '''
  def setUp(self):
    self.router = Router()
    self.router.filter(r'^/user/(?P<user>[^/]+)', '/level2/show_user')
    self.router.filter(r'^/archive/(\d{4})/(\d{2})/(\d{2})', '/level2/level3', regexp_flags=0)
    self.router.filter(r'^/three-named-args/(?P<one>.+)', '/three_named_args')
  
  def test1_basic(self):
    self.assertRoute('/', '/')
    self.assertRoute('/func_on_root', '/func_on_root')
    self.assertRoute('/level2', '/level2')
    self.assertRoute('/level2/func_on_level2', '/level2/func_on_level2')
    self.assertRoute('/level2/func_on_level2/nothing/here', http.NotFound)
    self.assertRoute('/level2/nothing/here', http.NotFound)
    self.assertRoute('/level2/level3', '/level2/level3')
    self.assertRoute('/level2/LEVEL3', '/level2/level3')
    self.assertRoute('/level2/level3/__call__', http.NotFound)
    self.assertRoute('/level3', http.NotFound)
    self.assertRoute('/level2/level3/func_on_level3', '/level2/level3/func_on_level3')
  
  def test2_filtered(self):
    self.assertRoute('/user/rasmus/photos', '/level2/show_user')
    self.assertRoute('/user/rasmus', '/level2/show_user')
    self.assertRoute('/USER/rasmus', '/level2/show_user')
    self.assertRoute('/user', http.NotFound)
    self.assertRoute('/archive/2008/01/15', '/level2/level3')
    self.assertRoute('/ARCHIVE/2009/10/21/foo', http.NotFound)
    self.assertRoute('/level2/level3/posts/list', '/level2/level3/posts/list')
  
  def test3_non_delegating(self):
    """Trying to access inherited leafs which does not delegate calls"""
    self.assertRoute('/level2/level3/func_on_level2', http.NotFound)
    self.assertRoute('/level2/level3/posts/func_on_level2', http.NotFound)
    self.assertRoute('/level2/level3/posts/', http.NotFound)
  
  def test4_delegating(self):
    """Access inherited leafs which do delegate calls"""
    self.assertRoute('/level2/delegating_func_on_root', '/delegating_func_on_root')
    self.assertRoute('/level2/level3/delegating_func_on_root', '/delegating_func_on_root')
    self.assertRoute('/level2/level3/posts/delegating_func_on_root', '/delegating_func_on_root')
  
  def test5_renamed(self):
    """Access renamed nodes, for example by @expose(name=)"""
    self.assertRoute('/level2/foo-bar', '/level2/foo-bar')
    self.assertRoute('/level2/foo_bar', http.NotFound)
    self.assertRoute('/level2/level-3-b/func_on_level3B', '/level2/level-3-b/func_on_level3B')
    self.assertRoute('/level2/level3B/func_on_level3B', http.NotFound)
  
  def test6_hidden(self):
    self.assertRoute('/level2/level3/hidden_method_on_level3', http.NotFound)
  
  def test7_protected_on_Controller(self):
    self.assertRoute('/controller_name', http.NotFound)
    self.assertRoute('/controller_path', http.NotFound)
    self.assertRoute('/controller_uri', http.NotFound)
    self.assertRoute('/special_methods', http.NotFound)
    self.assertRoute('/__new__', http.NotFound)
  
  def test8_explicitly_named_args(self):
    self.assertRoute('/one_named_arg1', '/one_named_arg1?foo=bar', {'foo':'bar'})
    self.assertRoute('/one_named_arg2', '/one_named_arg2?foo=bar', {'foo':'bar'})
    self.assertRoute('/one_named_arg3', '/one_named_arg3?foo=bar', {'foo':'bar'})
    self.assertRoute('/one_named_arg4', '/one_named_arg4?foo=bar', {'foo':'bar'})
  
  def test9_special_builtins(self):
    # These should succeed
    special_names = Controller.special_methods().keys()
    not_found_tests = []
    for name in special_names:
      not_found_tests.append(('/level2/%s' % name, http.NotFound))
      dest, args, params = self.router('GET', URL('/%s' % name), [], {})
      self.assertTrue(dest())
    # These should fail
    self.assertRoutes(*not_found_tests)
  
  def test10_params(self):
    self.assertRoute('/level2/show_user', http.BadRequest)
    self.assertRoute('/level2/show_user', '/level2/show_user', {'user':'john'})
    self.assertRoute('/three-named-args/john', '/three_named_args?one=john&two=doe&three=3', {'two':'doe'})
    self.assertRoute('/three-named-args/john', '/three_named_args?one=john&two=2&three=doe', {'three':'doe'})
    self.assertRoute('/three-named-args/john', '/three_named_args?one=john&two=homer&three=doe', {'two':'homer','three':'doe'})
    self.assertRoute('/three-named-args/john', '/three_named_args?one=john&two=2&three=3')
    self.assertRoute('/three-named-args', http.NotFound)
  
  def assertRoutes(self, router=None, *urls):
    for t in urls:
      self.assertRoute(*t)
  
  def assertRoute(self, url, expected_return, params={}, router=None, method='GET'):
    if router is None:
      r = self.router
    else:
      r = router
    url = URL(url)
    if echo:
      print '\nRouting \'%s\' expected to return %r (params=%s)' % (url, expected_return, params)
    dest, args, params = r(method, url, [], params)
    if isinstance(expected_return, http.Status):
      try:
        dest_returned = dest()
        assert r == 0, 'should raise %r but did not raise any exception '\
          'at all. dest() returned %r' % (expected_return, dest_returned)
      except http.HTTPExc, e:
        self.assertEquals(e.status.__class__, expected_return.__class__, '%r (%x) != %r (%x)' %\
          (expected_return, id(expected_return), e.status, id(e.status)))
      except AssertionError:
        raise
      except Exception, e:
        assert 0, 'should have raised %r, but instead %r was raised' %\
          (expected_return, e)
    else:
      if dest is not None:
        if echo:
          print 'Calling %r(*%s, **%s)' % (dest, args, params)
        returned = dest(*args, **params)
      else:
        returned = Nothing
      assert returned == expected_return, '%s != %s' % (returned, expected_return)
  

def suite():
  return unittest.TestSuite([
    unittest.makeSuite(RoutingTests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = test_matter
# encoding: utf-8
'''MVC test matter
'''
from smisk.mvc import *

# A controller tree

class root(Controller):
  def func_on_root(self): return '/func_on_root'
  @expose(delegates=True)
  def delegating_func_on_root(self): return '/delegating_func_on_root'
  def __call__(self, *va, **kw): return '/'
  def one_named_arg1(self, foo=None, *args, **kwargs): return '/one_named_arg1?foo=%s' % foo
  def one_named_arg2(self, foo=None, **kwargs): return '/one_named_arg2?foo=%s' % foo
  def one_named_arg3(self, foo=None, *args): return '/one_named_arg3?foo=%s' % foo
  def one_named_arg4(self, foo=None): return '/one_named_arg4?foo=%s' % foo
  def three_named_args(self, one=1, two=2, three=3):
    return '/three_named_args?one=%s&two=%s&three=%s' % (one, two, three)

class level2(root):
  def __call__(self): return '/level2'
  #func_on_level2 = root
  def func_on_level2(self, *va, **kw): return '/level2/func_on_level2'
  def show_user(self, user, *va, **kw): return '/level2/show_user'
  def level3(self):
    '''never reached from outside, because it's shadowed by subclass level3.
    However, it can still be reaced internally, through for example
    control.path_to().
    '''
    return 'shadowed'
  @expose('foo-bar')
  def foo_bar(self): return '/level2/foo-bar'

class level3(level2):
  def __call__(self): return '/level2/level3'
  @hide
  def hidden_method_on_level3(self): pass
  def func_on_level3(self, *va): return '/level2/level3/func_on_level3'
  def func_on_level3_wonlykwa(self, **kva): return '/level2/level3/func_on_level3_wonlykwa'

class level3B(level2):
  slug = 'level-3-b'
  def func_on_level3B(self): return '/level2/level-3-b/func_on_level3B'

class PostsController(level3):
  def list(self, *va, **kw): return '/level2/level3/posts/list'


# For testing method_origin and alike:

class Animal(object):
  def name(self): pass

class Fish(Animal):
  def color(self): pass

class Bass(Fish):
  def eats(self): pass
  def sleeps(self): pass

class SpanishBass(Bass):
  def on_fiesta(self): pass
  def sleeps(self): pass

class EnglishBass(Bass):
  def on_fiesta(self): return False
  def cheese(self): pass

########NEW FILE########
__FILENAME__ = serialization
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *

class SerializationTest(TestCase):
  pass

def suite():
  return unittest.TestSuite([ unittest.makeSuite(SerializationTest) ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = introspect
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.util.introspect import *
from smisk.util.type import Undefined

class A(object):
  def __call__(self):
    pass
  def hello(self, one, two, three=None, four=123, five='internets'):
    foo = 'oof'
    bar = 'rab'
    two = 14
    for baz in foo:
      pass
    return locals()
  def ping(self, filter=None, *argz, **kwargz):
    pass
  def none(self):
    pass

class B(object):
  def foo(self):
    pass

class IntrospectTests(TestCase):
  def setUp(self):
    self.expect_hello_info = {
      'name': 'hello', 
      'args': (
        ('one', Undefined),
        ('two', Undefined),
        ('three', None),
        ('four', 123),
        ('five', 'internets')
      ),
      'varargs': False,
      'varkw': False,
      'method': True
    }
    
  def test_2_info_methods(self):
    a = A()
    expected = self.expect_hello_info
    returned = introspect.callable_info(a.hello)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
    returned = introspect.callable_info(A.hello)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
    
    b = B()
    expected = {
      'name':'foo',
      'args': (),
      'method':True,
      'varargs': False,
      'varkw': False
    }
    returned = introspect.callable_info(b.foo)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
    returned = introspect.callable_info(B.foo)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
  
  def test_2_info_function(self):
    def plain():
      pass
    expected = {
      'name':'plain',
      'method':False,
      'varargs': False,
      'varkw': False,
      'args': (),
    }
    returned = introspect.callable_info(plain)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
  
  def test_2_info_function_varargs(self):
    def varargs(a, b=1, *args):
      pass
    expected = {
      'name':'varargs',
      'method':False,
      'varargs': True,
      'varkw': False,
      'args':(
        ('a',Undefined),
        ('b',1)
      ),
    }
    returned = introspect.callable_info(varargs)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
  
  def test_2_info_function_varkw(self):
    def foobar(a=[], b=1, **xyz):
      pass
    expected = {
      'name':'foobar',
      'method':False,
      'varargs': False,
      'varkw': True,
      'args':(
        ('a',[]),
        ('b',1)
      ),
    }
    returned = introspect.callable_info(foobar)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
  
  def test_3_ensure_va_kwa(self):
    a = A()
    try:
      assert a.hello(1,2,3,4,5,*('extra va1','extra va2')) == 0, 'should throw TypeError'
    except TypeError:
      pass
    a.hello = introspect.ensure_va_kwa(a.hello)
    expected = self.expect_hello_info.copy()
    expected['varargs'] = True
    expected['varkw'] = True
    returned = introspect.callable_info(a.hello)
    assert returned == expected, '%s\n!=\n%s' % (returned, expected)
    assert a.hello(1,2,3,4,5, *('va1','va2'), **{'kw1':1, 'kw2':2}) == {
      'self': a,
      'one': 1,
      'two': 14,
      'three': 3,
      'four': 4,
      'five': 5,
      'foo':'oof',
      'bar':'rab',
      'baz':'f'
    }
    assert a.hello('ett', 'tva') == {
      'self': a,
      'one': 'ett',
      'two': 14,
      'three': None,
      'four': 123,
      'five': 'internets',
      'foo':'oof',
      'bar':'rab',
      'baz':'f'
    }
    # This should not raise an exception
    a.none = introspect.ensure_va_kwa(a.none)
    a.none()
    a.none(1,2)
    a.none(1,2,3,4)
    a.none(1,2,3,4,foo=12)
  

def suite():
  return unittest.TestSuite([
    unittest.makeSuite(IntrospectTests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = string_
#!/usr/bin/env python
# encoding: utf-8
from smisk.test import *
from smisk.util.string import *
from smisk.core import URL

class StringUtilTests(TestCase):
  def test1_normalize_url(self):
    abs_url = URL('http://www.foo.tld/bar/?arg=12&baz=abc')
    self.assertEquals(normalize_url('/mos', abs_url).__str__(), 'http://www.foo.tld/mos')
    self.assertEquals(normalize_url('mos.html', abs_url).__str__(), 'http://www.foo.tld/bar/mos.html')
    self.assertEquals(normalize_url('mos.html?xyz=987&abc=123', abs_url).__str__(), 'http://www.foo.tld/bar/mos.html?xyz=987&abc=123')
    self.assertEquals(normalize_url('mos.html').__str__(), '/mos.html')
    self.assertEquals(normalize_url('/mos').__str__(), '/mos')
  

def suite():
  return unittest.TestSuite([
    unittest.makeSuite(StringUtilTests),
  ])

def test():
  runner = unittest.TextTestRunner()
  return runner.run(suite())

if __name__ == "__main__":
  test()

########NEW FILE########
__FILENAME__ = benchmark
# encoding: utf-8
import itertools, gc, sys, resource, time

__all__ = ['benchmark']

def benchmark(name='benchmark', iterations=1000000, outfp=sys.stderr, it_subtractor=0.0):
  '''Measure raw performance.
  '''
  def fmt(sec):
    return "%3.0f sec  %3.0f ms  %4.0f us" % (sec, (sec*1000)%1000, (sec*1000000)%1000)
  gcold = gc.isenabled()
  gc.disable()
  it = itertools.repeat(None, iterations)
  u0 = resource.getrusage(resource.RUSAGE_SELF)
  real = time.time()
  exc = None
  try:
    for x in it:
      yield x
  except Exception, e:
    exc = e
  real = time.time() - real
  u1 = resource.getrusage(resource.RUSAGE_SELF)
  if gcold:
    gc.enable()
  if it_subtractor > 0.0:
    real -= it_subtractor * float(iterations)
  outfp.flush()
  print >> outfp, '\n%s:  %6.1f calls/sec' % (name, iterations/real)
  print >> outfp, '-----------------------------------'
  print >> outfp, 'avg. call ', fmt(real/iterations)
  print >> outfp, '-----------------------------------'
  print >> outfp, 'real      ', fmt(real)
  print >> outfp, 'user      ', fmt(u1.ru_utime - u0.ru_utime)
  print >> outfp, 'system    ', fmt(u1.ru_stime - u0.ru_stime)
  outfp.flush()
  if exc:
    raise exc


########NEW FILE########
__FILENAME__ = cache
# encoding: utf-8
'''Cache-related utilities.
'''
from types import *
import sys, os

__all__ = ['callable_cache_key', 'app_shared_key']

def callable_cache_key(node):
  '''Calculate key unique enought to be used for caching callables.
  '''
  if not isinstance(node, (MethodType, FunctionType)):
    return hash(node.__call__)^hash(node)
  elif isinstance(node, MethodType):
    return hash(node)^hash(node.im_class)
  return node

def app_shared_key():
  fn = sys.modules['__main__'].__file__
  h = hash(fn)
  if h < 0:
    h = 'a%lx' % -h
  else:
    h = 'b%lx' % h
  name = os.path.splitext(os.path.basename(fn))[0]
  if name == '__init__':
    name = os.path.basename(os.path.dirname(os.path.abspath(fn)))
  return '%s_%s' % (name, h)

########NEW FILE########
__FILENAME__ = collections
# encoding: utf-8
'''Collection utilities
'''

__all__ = ['unique_wild', 'unique']

def unique_wild(seq):
  '''
  :param seq:
  :type  seq: collection
  :rtype: list
  '''
  # Not order preserving but faster than list_unique
  return list(set(seq))


def unique(seq):
  '''Return a list of the elements in `seq`, but without duplicates.
  
  For example, ``unique([1,2,3,1,2,3])`` is some permutation of ``[1,2,3]``,
  ``unique("abcabc")`` some permutation of ``["a", "b", "c"]``, and
  ``unique(([1, 2], [2, 3], [1, 2]))`` some permutation of
  ``[[2, 3], [1, 2]]``.
  
  For best speed, all sequence elements should be hashable. Then
  ``unique()`` will usually work in linear time.
  
  If not possible, the sequence elements should enjoy a total
  ordering, and if ``list(s).sort()`` doesn't raise ``TypeError`` it's
  assumed that they do enjoy a total ordering. Then ``unique()`` will
  usually work in ``O(N*log2(N))`` time.
  
  If that's not possible either, the sequence elements must support
  equality-testing. Then ``unique()`` will usually work in quadratic
  time.
  
  :param seq:
  :type  seq: collection
  :rtype: list
  '''
  n = len(seq)
  if n == 0:
    return []
  # Try using a dict first, as that's the fastest and will usually
  # work.  If it doesn't work, it will usually fail quickly, so it
  # usually doesn't cost much to *try* it.  It requires that all the
  # sequence elements be hashable, and support equality comparison.
  u = {}
  try:
    for x in seq:
      u[x] = 1
  except TypeError:
    del u  # move on to the next method
  else:
    return u.keys()
  # We can't hash all the elements.  Second fastest is to sort,
  # which brings the equal elements together; then duplicates are
  # easy to weed out in a single pass.
  # NOTE:  Python's list.sort() was designed to be efficient in the
  # presence of many duplicate elements.  This isn't true of all
  # sort functions in all languages or libraries, so this approach
  # is more effective in Python than it may be elsewhere.
  try:
    t = list(seq)
    t.sort()
  except TypeError:
    del t  # move on to the next method
  else:
    assert n > 0
    last = t[0]
    lasti = i = 1
    while i < n:
      if t[i] != last:
        t[lasti] = last = t[i]
        lasti += 1
      i += 1
    return t[:lasti]
  
  # Brute force is all that's left.
  u = []
  for x in seq:
    if x not in u:
      u.append(x)
  return u

def merge(a, b):
  '''Updates collection `a` with contents of collection `b`, recursively
  merging any lists and dictionaries.
  
  Lists are merged through a.extend(b), dictionaries are merged by replacing
  and non-list or dict key with the value from collection b. In other words,
  collection b takes precedence.
  '''
  if isinstance(a, list):
    a.extend(b)
    return a
  elif isinstance(a, dict):
    return merge_dict(a, b)
  else:
    raise TypeError('first argument must be a list or a dict')

def merge_dict(a, b, merge_lists=True):
  '''Updates dictionary `a` with contents of dictionary `b`, recursively
  merging any lists and dictionaries.
  
  Lists are merged through a.extend(b), dictionaries are merged by replacing
  and non-list or dict key with the value from collection b. In other words,
  collection b takes precedence.
  '''
  for bk,bv in b.items():
    if a.has_key(bk) and hasattr(bv, 'has_key') and hasattr(a[bk], 'has_key'):
      merge_dict(a[bk], bv, merge_lists)
    elif merge_lists and hasattr(bv, 'extend') and hasattr(a.get(bk), 'extend'):
      a[bk].extend(bv)
    else:
      a[bk] = bv
  return a

def merged(a, b):
  '''Like merge but does not modify *a*
  '''
  if isinstance(a, (list,tuple)):
    return a + b
  elif isinstance(a, dict):
    return merged_dict(a, b)
  else:
    raise TypeError('first argument must be a list or a dict')

def merged_dict(a, b, merge_lists=True):
  '''Like merge_dict but does not modify *a*
  '''
  a = a.copy()
  for bk,bv in b.items():
    if a.has_key(bk) and hasattr(bv, 'has_key') and hasattr(a[bk], 'has_key'):
      a[bk] = merged_dict(a[bk], bv, merge_lists)
    elif merge_lists and hasattr(bv, 'extend') and hasattr(a.get(bk), 'extend'):
      a[bk] = a[bk] + bv
    else:
      a[bk] = bv
  return a

########NEW FILE########
__FILENAME__ = DateTime
# encoding: utf-8
'''Date and Time utilities
'''
import re, time
from datetime import datetime, timedelta, tzinfo
ZERO_TIMEDELTA = timedelta(0)

__all__ = ['UTCTimeZone', 'OffsetTimeZone', 'DateTime']

class UTCTimeZone(tzinfo):
  '''UTC
  '''
  def __new__(cls):
    try:
      return cls._instance
    except AttributeError:
      cls._instance = tzinfo.__new__(UTCTimeZone)
    return cls._instance
  
  def utcoffset(self, dt):
    return ZERO_TIMEDELTA
  
  def tzname(self, dt):
    return "UTC"
  
  def dst(self, dt):
    return ZERO_TIMEDELTA
  
  def __repr__(self):
    return 'UTCTimeZone()'
  

class OffsetTimeZone(tzinfo):
  '''Fixed offset in minutes east from UTC.
  '''
  def __init__(self, tzstr_or_minutes):
    if isinstance(tzstr_or_minutes, basestring):
      minutes = (int(tzstr_or_minutes[1:3]) * 60) + int(tzstr_or_minutes[4:6])
      if tzstr_or_minutes[0] == '-':
        minutes = -minutes
    else:
      minutes = tzstr_or_minutes
    self.__minute_offset = minutes
    self.__offset = timedelta(minutes=minutes)
  
  def utcoffset(self, dt):
    return self.__offset
  
  def dst(self, dt):
    return ZERO_TIMEDELTA
  
  def __repr__(self):
    return 'OffsetTimeZone(%d)' % self.__minute_offset
  

class DateTime(datetime):
  '''Time zone aware version of datetime with additional parsers.
  '''
  XML_SCHEMA_DATETIME_RE = re.compile(r'((?#year)-?\d{4})-((?#month)\d{2})-((?#day)\d{2})T'\
    r'((?#hour)\d{2}):((?#minute)\d{2}):((?#second)\d{2})((?#millis)\.\d+|)((?#tz)[+-]\d{2}:\d{2}|Z?)')
  '''XML schema dateTime regexp.
  
  :type: RegexType
  '''
  
  def __new__(cls, dt=None, *args, **kwargs):
    if isinstance(dt, datetime):
      if type(dt) is cls:
        return dt
      return datetime.__new__(cls, 
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
    return datetime.__new__(cls, dt, *args, **kwargs)
  
  def as_utc(self):
    '''Return this date in Universal Time Coordinate
    '''
    if self.tzinfo is UTCTimeZone():
      return self
    offset = self.utcoffset()
    if offset is None:
      dt = self.replace(tzinfo=UTCTimeZone())
    else:
      dt = (self - offset).replace(tzinfo=UTCTimeZone())
    return DateTime(dt)
  
  @classmethod
  def now(self):
    if time.timezone == 0 and time.daylight == 0:
      tz = UTCTimeZone()
    else:
      tz = OffsetTimeZone(((-time.timezone)/60) + (time.daylight * 60))
    return datetime.now().replace(tzinfo=tz)
  
  @classmethod
  def parse_xml_schema_dateTime(cls, string):
    '''Parse a XML Schema dateTime value.
    
    :see: `XML Schema Part 2: Datatypes Second Edition, 3.2.7 dateTime
          <http://www.w3.org/TR/xmlschema-2/#dateTime>`__
    '''
    m = cls.XML_SCHEMA_DATETIME_RE.match(string).groups()
    if m[7] and m[7] != 'Z':
      tz = OffsetTimeZone(m[7])
    else:
      tz = UTCTimeZone()
    microsecond = 0
    if m[6]:
      microsecond = int(float(m[6]) * 1000000.0)
    dt = DateTime(int(m[0]), int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), microsecond, tz)
    return dt
  

########NEW FILE########
__FILENAME__ = fcgiproto
# encoding: utf-8

class FastCGIError(Exception):
  pass

# Values for type component of FCGI_Header

FCGI_BEGIN_REQUEST     = 1
FCGI_ABORT_REQUEST     = 2
FCGI_END_REQUEST     = 3
FCGI_PARAMS        = 4
FCGI_STDIN         = 5
FCGI_STDOUT        = 6
FCGI_STDERR        = 7
FCGI_DATA        = 8
FCGI_GET_VALUES      = 9
FCGI_GET_VALUES_RESULT   = 10
FCGI_UNKNOWN_TYPE    = 11

typeNames = {
  FCGI_BEGIN_REQUEST  : 'fcgi_begin_request',
  FCGI_ABORT_REQUEST  : 'fcgi_abort_request',
  FCGI_END_REQUEST    : 'fcgi_end_request',
  FCGI_PARAMS       : 'fcgi_params',
  FCGI_STDIN      : 'fcgi_stdin',
  FCGI_STDOUT       : 'fcgi_stdout',
  FCGI_STDERR       : 'fcgi_stderr',
  FCGI_DATA       : 'fcgi_data',
  FCGI_GET_VALUES     : 'fcgi_get_values',
  FCGI_GET_VALUES_RESULT: 'fcgi_get_values_result',
  FCGI_UNKNOWN_TYPE   : 'fcgi_unknown_type'}

# Mask for flags component of FCGI_BeginRequestBody
FCGI_KEEP_CONN = 1

# Values for role component of FCGI_BeginRequestBody
FCGI_RESPONDER  = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER   = 3

# Values for protocolStatus component of FCGI_EndRequestBody

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN  = 1
FCGI_OVERLOADED     = 2
FCGI_UNKNOWN_ROLE   = 3

FCGI_MAX_PACKET_LEN = 0xFFFF

class Record(object):
  def __init__(self, type, reqId, content='', version=1):
    self.version = version
    self.type = type
    self.reqId = reqId
    self.content = content
    self.length = len(content)
    if self.length > FCGI_MAX_PACKET_LEN:
      raise ValueError("Record length too long: %d > %d" %
               (self.length, FCGI_MAX_PACKET_LEN))
    if self.length % 8 != 0:
      self.padding = 8 - (self.length & 7)
    else:
      self.padding = 0
    self.reserved = 0
    
  def fromHeaderString(clz, rec):
    self = object.__new__(clz)
    self.version = ord(rec[0])
    self.type = ord(rec[1])
    self.reqId = (ord(rec[2])<<8)|ord(rec[3])
    self.length = (ord(rec[4])<<8)|ord(rec[5])
    self.padding = ord(rec[6])
    self.reserved = ord(rec[7])
    self.content = None
    return self
  
  fromHeaderString = classmethod(fromHeaderString)

  def toOutputString(self):
    return "%c%c%c%c%c%c%c%c" % (
      self.version, self.type,
      (self.reqId&0xFF00)>>8, self.reqId&0xFF,
      (self.length&0xFF00)>>8, self.length & 0xFF,
      self.padding, self.reserved) + self.content + '\0'*self.padding
    
  def totalLength(self):
    return 8 + self.length + self.padding

  def __repr__(self):
    return "<FastCGIRecord version=%d type=%d(%s) reqId=%d>" % (
      self.version, self.type, typeNames.get(self.type), self.reqId)
  
def parseNameValues(s):
  '''
  @param s: String containing valid name/value data, of the form:
        'namelength + valuelength + name + value' repeated 0 or more
        times. See C{fastcgi.writeNameValue} for how to create this
        string.
  @return: Generator of tuples of the form (name, value)
  '''
  off = 0
  while off < len(s):
    nameLen = ord(s[off])
    off += 1
    if nameLen&0x80:
      nameLen=(nameLen&0x7F)<<24 | ord(s[off])<<16 | ord(s[off+1])<<8 | ord(s[off+2])
      off += 3
    valueLen=ord(s[off])
    off += 1
    if valueLen&0x80:
      valueLen=(valueLen&0x7F)<<24 | ord(s[off])<<16 | ord(s[off+1])<<8 | ord(s[off+2])
      off += 3
    yield (s[off:off+nameLen], s[off+nameLen:off+nameLen+valueLen])
    off += nameLen + valueLen

def getLenBytes(length):
  if length<0x80:
    return chr(length)
  elif 0 < length <= 0x7FFFFFFF:
    return (chr(0x80|(length>>24)&0x7F) + chr((length>>16)&0xFF) + 
        chr((length>>8)&0xFF) + chr(length&0xFF))
  else:
    raise ValueError("Name length too long.")

def writeNameValue(name, value):
  return getLenBytes(len(name)) + getLenBytes(len(value)) + name + value

class Channel(object):
  maxConnections = 100
  reqId = 0
  request = None
  
  ## High level protocol
  def packetReceived(self, packet):
    '''
    @param packet: instance of C{fastcgi.Record}.
    @raise: FastCGIError on invalid version or where the type does not exist
        in funName
    '''
    if packet.version != 1:
      raise FastCGIError("FastCGI packet received with version != 1")
    
    funName = typeNames.get(packet.type)
    if funName is None:
      raise FastCGIError("Unknown FastCGI packet type: %d" % packet.type)
    getattr(self, funName)(packet)

  def fcgi_get_values(self, packet):
    if packet.reqId != 0:
      raise ValueError("Should be 0!")
    
    content = ""
    for name,value in parseNameValues(packet.content):
      outval = None
      if name == "FCGI_MAX_CONNS":
        outval = str(self.maxConnections)
      elif name == "FCGI_MAX_REQS":
        outval = str(self.maxConnections)
      elif name == "FCGI_MPXS_CONNS":
        outval = "0"
      if outval:
        content += writeNameValue(name, outval)
    self.writePacket(Record(FCGI_GET_VALUES_RESULT, 0, content))
  
  def fcgi_unknown_type(self, packet):
    # Unused, reserved for future expansion
    pass

  def fcgi_begin_request(self, packet):
    role = ord(packet.content[0])<<8 | ord(packet.content[1])
    flags = ord(packet.content[2])
    if packet.reqId == 0:
      raise ValueError("ReqId shouldn't be 0!")
    if self.reqId != 0:
      self.writePacket(Record(FCGI_END_REQUEST, self.reqId,
                  "\0\0\0\0"+chr(FCGI_CANT_MPX_CONN)+"\0\0\0"))
    if role != FCGI_RESPONDER:
      self.writePacket(Record(FCGI_END_REQUEST, self.reqId,
                  "\0\0\0\0"+chr(FCGI_UNKNOWN_ROLE)+"\0\0\0"))
    
    self.reqId = packet.reqId
    self.keepalive = flags & FCGI_KEEP_CONN
    self.params = ""
    
  def fcgi_abort_request(self, packet):
    if packet.reqId != self.reqId:
      return

    self.request.connectionLost()
    
  def fcgi_params(self, packet):
    if packet.reqId != self.reqId:
      return
    
    # I don't feel like doing the work to incrementally parse this stupid
    # protocol, so we'll just buffer all the params data before parsing.
    if not packet.content:
      self.makeRequest(dict(parseNameValues(self.params)))
      self.request.process()
    self.params += packet.content
    
  def fcgi_stdin(self, packet):
    if packet.reqId != self.reqId:
      return
    
    if not packet.content:
      self.request.handleContentComplete()
    else:
      self.request.handleContentChunk(packet.content)
    
  def fcgi_data(self, packet):
    # For filter roles only, which is currently unsupported.
    pass

  def write(self, data):
    if len(data) > FCGI_MAX_PACKET_LEN:
      n = 0
      while 1:
        d = data[n*FCGI_MAX_PACKET_LEN:(n+1)*FCGI_MAX_PACKET_LEN]
        if not d:
          break
        self.write(d)
      return
    
    self.writePacket(Record(FCGI_STDOUT, self.reqId, data))
    
  def writeHeaders(self, code, headers):
    l = []
    code_message = responsecode.RESPONSES.get(code, "Unknown Status")
    
    l.append("Status: %s %s\n" % (code, code_message))
    if headers is not None:
      for name, valuelist in headers.getAllRawHeaders():
        for value in valuelist:
          l.append("%s: %s\n" % (name, value))
    l.append('\n')
    self.write(''.join(l))

  def finish(self):
    if self.request is None:
      raise RuntimeError("Request.finish called when no request was outstanding.")
    self.writePacket(Record(FCGI_END_REQUEST, self.reqId,
                "\0\0\0\0"+chr(FCGI_REQUEST_COMPLETE)+"\0\0\0"))
    del self.reqId, self.request
    if not self.keepalive:
      self.transport.loseConnection()
    
## Low level protocol
  paused = False
  _lastRecord = None
  recvd = ""
  
  def writePacket(self, packet):
    data = packet.toOutputString()
    #print "Writing record", packet, repr(data)
    self.sock.sendall(data)
  
  def read(self, length):
    s = ''
    while len(s) < length:
      s = self.sock.recv(length-len(s))
    return s
  
  def readPacket(self, tryrecv=False):
    if tryrecv:
      try:
        self.sock.setblocking(0)
        s = self.sock.recv(8)
      finally:
        self.sock.setblocking(1)
      if len(s) < 8:
        s += self.read(8-len(s))
    else:
      s = self.read(8)
    record = Record.fromHeaderString(s)
    if record.length:
      record.content = self.read(record.length)
    if record.padding:
      self.read(record.padding)
    return record
  
  def dataReceived(self, recd):
    self.recvd = self.recvd + recd
    record = self._lastRecord
    self._lastRecord = None
    while len(self.recvd) >= 8 and not self.paused:
      if record is None:
        record = Record.fromHeaderString(self.recvd[:8])
      if len(self.recvd) < record.totalLength():
        self._lastRecord = record
        break
      record.content = self.recvd[8:record.length+8]
      self.recvd = self.recvd[record.totalLength():]
      self.packetReceived(record)
      record = None

  def pauseProducing(self):
    self.paused = True
    self.transport.pauseProducing()

  def resumeProducing(self):
    self.paused = False
    self.transport.resumeProducing()
    self.dataReceived('')

  def stopProducing(self):
    self.paused = True
    self.transport.stopProducing()


########NEW FILE########
__FILENAME__ = frozen
# encoding: utf-8
'''Immutable types
'''

__all__ = ['frozendict']

class frozendict(dict):
  '''Immutable dictionary.
  '''
  def __setitem__(self, *args, **kwargs):
    raise TypeError("frozendict object does not support item assignment")
  
  setdefault = __delitem__ = clear = pop = popitem = __setitem__
  
  def update(self, *args):
    '''Update a mutable copy with key/value pairs from b, replacing existing keys.
    
    :returns: A mutable copy with updated pairs.
    :rtype: dict
    '''
    d = self.copy()
    d.update(*args)
    return d
  
  copy = dict.copy
  '''Returns a mutable copy.
  '''
  
  def __hash__(self):
    items = self.items()
    res = hash(items[0])
    for item in items[1:]:
      res ^= hash(item)
    return res
  

########NEW FILE########
__FILENAME__ = httpd
# encoding: utf-8
import logging
import BaseHTTPServer
import smisk.util.fcgiproto as fcgi
import socket
import os
import mimetools
import time
from smisk import __version__ as smisk_version
from cStringIO import StringIO

log = logging.getLogger(__name__)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def __init__(self, *va, **kw):
		log.debug('handler init')
		self.server_version = 'smiskhttpd/%s' % smisk_version
		#self.protocol_version = 'HTTP/1.1' # todo 1.1 support, like chunked enc.
		BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *va, **kw)
	
	def handle_one_request(self):
		self.raw_requestline = self.rfile.readline()
		if not self.raw_requestline:
			self.close_connection = 1
			return
		if not self.parse_request(): # An error code has been sent, just exit
			return
		try:
			ch = self.server.get_fcgi_backend()
			if not ch:
				log.error('fastcgi error: backend unavailable')
				try:
					self.send_response(503, 'Service Unavailable')
					self.wfile.write('\r\n503 Service Unavailable (FastCGI backend unavailable)\n')
				except:
					pass
			else:
				try:
					self.handle_fcgi_request(ch)
				finally:
					self.server.put_fcgi_backend(ch)
		except socket.error, e:
			log.error('fastcgi channel error: %s', e, exc_info=1)
		except:
			log.error('server error while handing request:', exc_info=1)
	
	def send_response(self, code, message=None):
		self.log_request(code)
		if message is None:
			if code in self.responses:
				message = self.responses[code][0]
			else:
				message = ''
		if self.request_version != 'HTTP/0.9':
			self.wfile.write("%s %d %s\r\n" %
							 (self.protocol_version, code, message))
	
	def handle_fcgi_request(self, ch):
		rid = 1
		content_length = 0
		query_string = ''
		if '?' in self.path:
			query_string = self.path[self.path.index('?')+1:]
		params = {
			'GATEWAY_INTERFACE': 'CGI/1.1',
			'PATH_INFO': '',
			'QUERY_STRING': query_string,
			'REMOTE_ADDR': self.client_address[0],
			'REMOTE_HOST': self.server.fqdn,
			'REQUEST_METHOD': self.command,
			'SCRIPT_NAME': '/' + self.path.lstrip('/'),
			'SERVER_NAME': '%s:%d' % (self.server.fqdn, self.server.naddr[1]),
			'SERVER_PORT': '%d' % self.server.naddr[1],
			'SERVER_PROTOCOL': self.request_version,
			'SERVER_SOFTWARE': self.server_version,
			
			# Following are not part of CGI 1.1:
			'DOCUMENT_ROOT': self.server.document_root,
			'REMOTE_PORT': '%d' % self.client_address[1],
			'REQUEST_URI': self.path,
			'SCRIPT_FILENAME': self.server.document_root + '/' + self.path.lstrip('/'),
			'SERVER_ADDR': self.server.naddr[0],
		}
		
		# read http headers and transfer to params
		for k in self.headers:
			v = self.headers.get(k)
			params['HTTP_'+k.replace('-','_').upper()] = v
			if k == 'content-length':
				content_length = int(v)
			elif k == 'content-type':
				params['CONTENT_TYPE'] = v
		if content_length:
			params['CONTENT_LENGTH'] = str(content_length)
		
		# begin
		role = fcgi.FCGI_RESPONDER
		flags = 0
		content = '%c%c%c\000\000\000\000\000' % ((role&0xFF00)>>8, role&0xFF, flags)
		ch.writePacket(fcgi.Record(fcgi.FCGI_BEGIN_REQUEST, rid, content))
		
		# params
		content = ''
		for k,v in params.items():
			s = fcgi.writeNameValue(k,v)
			if len(content)+len(s) > fcgi.FCGI_MAX_PACKET_LEN:
				ch.writePacket(fcgi.Record(fcgi.FCGI_PARAMS, rid, content))
				content = s
			else:
				content += s
		ch.writePacket(fcgi.Record(fcgi.FCGI_PARAMS, rid, content))
		ch.writePacket(fcgi.Record(fcgi.FCGI_PARAMS, rid))
		
		# EOF on stdin
		if content_length == 0:
			ch.writePacket(fcgi.Record(fcgi.FCGI_STDIN, rid, ''))
		
		# read reply
		started = False
		wrote_stdin_eof = content_length
		indata = ''
		outbuf = ''
		transfer_encoding = None
		skipout = False
		while 1:
			if content_length:
				try:
					r = ch.readPacket(True)
				except socket.error, e:
					if e.args[0] == 35: # "Resource temporarily unavailable"
						# probably waiting for stdin
						n = content_length
						if n > fcgi.FCGI_MAX_PACKET_LEN:
							n = fcgi.FCGI_MAX_PACKET_LEN
							content_length -= n
						else:
							content_length = 0
						
						indata = self.rfile.read(n)
						
						if not indata:
							log.warn('client sent EOF on stdin even though not all bytes indicated by '\
											 'content-length have been read -- aborting request')
							ch.writePacket(fcgi.Record(fcgi.FCGI_ABORT_REQUEST, rid))
							break
						
						log.info('got %d bytes on http stdin -- forwarding on FCGI channel', len(indata))
						
						ch.writePacket(fcgi.Record(fcgi.FCGI_STDIN, rid, indata))
						
						if content_length == 0:
							# write EOF
							ch.writePacket(fcgi.Record(fcgi.FCGI_STDIN, rid))
							wrote_stdin_eof = True
						
						continue
					else:
						raise
			else:
				r = ch.readPacket()
			log.debug('received packet %r', r)
			if r.type == fcgi.FCGI_STDOUT:
				if not started:
					outbuf += r.content
					r.content = ''
					p = outbuf.find('\r\n\r\n')
					if p != -1:
						sf = StringIO(outbuf[:p])
						r.content = outbuf[p+4:]
						headers = mimetools.Message(sf, True)
						
						# status
						status = headers.get('status', None)
						if status:
							status = status.split(' ',1)
							status[0] = int(status[0])
							self.send_response(*status)
						else:
							self.send_response(200)
						
						# required headers
						skipk = ['server', 'date', 'transfer-encoding']
						self.send_header('Server', headers.getheader('server', self.version_string()))
						self.send_header('Date', headers.getheader('date', self.date_time_string()))
						
						# content length
						if not headers.getheader('content-length', False):
							if self.protocol_version == 'HTTP/1.1':
								transfer_encoding = headers.getheader('server', 'chunked').lower()
								self.send_header('Transfer-Encoding', transfer_encoding)
							else:
								self.close_connection = 1
						
						# send other headers
						for k in headers:
							if k not in skipk:
								self.send_header(k.capitalize(), headers.getheader(k))
						
						self.wfile.write('\r\n')
						started = True
				if r.content and not skipout:
					self.wfile.write(r.content)
			elif r.type == fcgi.FCGI_STDERR:
				log.error('%s: %s', ch, r.content)
			elif r.type == fcgi.FCGI_END_REQUEST:
				if transfer_encoding == 'chunked':
					self.wfile.write('')
				break
		
		# EOF on stdin
		if not wrote_stdin_eof:
			ch.writePacket(fcgi.Record(fcgi.FCGI_STDIN, rid))
	

class Server(BaseHTTPServer.HTTPServer):
	fcgichannel = None
	document_root = '/tmp'
	
	def __init__(self, address, fcgi_address=('127.0.0.1', 5000), request_handler=RequestHandler, *va, **kw):
		self.document_root = os.path.realpath('.')
		self.fcgi_address = fcgi_address
		BaseHTTPServer.HTTPServer.__init__(self, address, request_handler)
	
	def server_bind(self):
		x = BaseHTTPServer.HTTPServer.server_bind(self)
		self.fqdn = socket.getfqdn(self.server_address[0])
		self.naddr = list(self.server_address)
		if self.naddr[0] == '0.0.0.0':
			self.naddr[0] = '127.0.0.1'
		elif self.naddr[0] == '::0':
			self.naddr[0] = '::1'
		self.naddr = tuple(self.naddr)
		return x
	
	def fcgi_connect(self, addr):
		channel = fcgi.Channel()
		channel.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		channel.sock.connect(addr)
		return channel
	
	def get_fcgi_backend(self, addr=None, max_connect_retries=10):
		if addr == None:
			addr = self.fcgi_address
		while True:
			try:
				return self.fcgi_connect(addr)
			except socket.error, e:
				if e.args[0] == 61:
					# connection refused
					if max_connect_retries == -1 or max_connect_retries > 0:
						try:
							log.warn('fcgi backend %s refused connection -- reconnecting...', addr)
							time.sleep(1)
							if max_connect_retries > 0:
								max_connect_retries -= 1
							continue
						except:
							pass
					log.error('fcgi backend %s refused connection', addr)
					break
				raise
	
	def put_fcgi_backend(self, ch):
		try:
			ch.sock.close()
		except:
			pass
	

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	server = Server(('localhost', 8080))
	#server.handle_request()
	server.serve_forever()

########NEW FILE########
__FILENAME__ = introspect
# encoding: utf-8
'''Introspection
'''
import inspect
try:
  import reprlib
except ImportError:
  import repr as reprlib
from smisk.util.type import *
from smisk.util.cache import callable_cache_key
from smisk.util.frozen import frozendict

__all__ = ['introspect', 'repr2']

class introspect(object):    
  VARARGS = 4
  KWARGS = 8
  
  _repr = reprlib.Repr()
  _repr.maxlong = 100
  _repr.maxstring = 200
  _repr.maxother = 200
  
  _info_cache = {}
  
  @classmethod
  def callable_info(cls, f):
    '''Info about a callable.
    
    The results are cached for efficiency.
    
    :param f:
    :type  f: callable
    :rtype: frozendict
    '''
    if not callable(f):
      return None
    
    if isinstance(f, FunctionType):
      # in case of ensure_va_kwa
      try:
        f = f.wrapped_func
      except AttributeError:
        pass
    
    cache_key = callable_cache_key(f)
    
    try:
      return cls._info_cache[cache_key]
    except KeyError:
      pass
    
    is_method, args, varargs, varkw, defaults = cls.getargspec(f)
    
    _args = []
    args_len = len(args)
    defaults_len = 0
    
    if defaults is not None:
      defaults_len = len(defaults)
    
    for i,n in enumerate(args):
      default_index = i-(args_len-defaults_len)
      v = Undefined
      if default_index > -1:
        v = defaults[default_index]
      _args.append((n, v))
    
    info = frozendict({
      'name':f.func_name,
      'args':tuple(_args),
      'varargs':bool(varargs),
      'varkw':bool(varkw),
      'method':is_method
    })
    
    cls._info_cache[cache_key] = info
    return info
  
  @classmethod
  def getargspec(cls, f):
    '''Returns a tuple of 5 objects: bool is_method, list args, string varargs, 
    string varkw, list defaults
    
    :rtype: tuple
    '''
    if not isinstance(f, (MethodType, FunctionType)):
      f = f.__call__
    
    is_method = False
    args, varargs, varkw, defaults = inspect.getargspec(f)
    
    if isinstance(f, MethodType):
      # Remove self
      args = args[1:]
      is_method = True
    
    return is_method, args, varargs, varkw, defaults
  
  @classmethod
  def format_members(cls, o, colorize=False):
    s = []
    items = []
    longest_k = 0
    types = {}
    type_i = 0
    color = 0
    
    for k in dir(o):
      v = getattr(o,k)
      if len(k) > longest_k:
        longest_k = len(k)
      if colorize:
        t = str(type(v))
        if t not in types:
          types[t] = type_i
          type_i += 1
        color = 31 + (types[t] % 5)
      items.append((k,v,color))
    
    if colorize:
      pat = '\033[1;%%dm%%-%ds\033[m = \033[1;%%dm%%s\033[m' % longest_k
    else:
      pat = '%%-%ds = %%s' % longest_k
    
    for k,v,color in items:
      v = cls._repr.repr(v)
      if colorize:
        s.append(pat % (color, k, color, v))
      else:
        s.append(pat % (k, v))
    
    return '\n'.join(s)
  
  
  @classmethod
  def ensure_va_kwa(cls, f, parent=None):
    '''Ensures `f` accepts both ``*varargs`` and ``**kwargs``.
    
    If `f` does not support ``*args``, it will be wrapped with a
    function which cuts away extra arguments in ``*args``.
    
    If `f` does not support ``*args``, it will be wrapped with a
    function which discards the ``**kwargs``.
    
    :param f:
    :type  f:       callable
    :param parent:  The parent on which `f` is defined. If specified, we will perform
                    ``parent.<name of f> = wrapper`` in the case we needed to wrap `f`.
    :type  parent:  object
    :returns: A callable which is guaranteed to accept both ``*args`` and ``**kwargs``.
    :rtype: callable
    '''
    is_method, args, varargs, varkw, defaults = cls.getargspec(f)
    va_kwa_wrapper = None
    
    if varargs is None and varkw is None:
      if args:
        def va_kwa_wrapper(*va, **kw):
          kws = kw.copy()
          for k in kw:
            if k not in args:
              del kws[k]
          return f(*va[:len(args)], **kws)
      else:
        def va_kwa_wrapper(*va, **kw):
          return f()
    elif varargs is None:
      if args:
        def va_kwa_wrapper(*va, **kw):
          return f(*va[:len(args)], **kw)
      else:
        def va_kwa_wrapper(*va, **kw):
          return f(**kw)
    elif varkw is None:
      if args:
        def va_kwa_wrapper(*va, **kw):
          kws = kw.copy()
          for k in kw:
            if k not in args:
              del kws[k]
          return f(*va, **kw)
      else:
        def va_kwa_wrapper(*va, **kw):
          return f(*va)
    
    if va_kwa_wrapper:
      va_kwa_wrapper.info = frozendict(cls.callable_info(f).update({
        'varargs': True,
        'varkw': True
      }))
      cls._info_cache[callable_cache_key(f)] = va_kwa_wrapper.info
      va_kwa_wrapper.wrapped_func = f
      va_kwa_wrapper.im_func = f
      va_kwa_wrapper.__name__ = f.__name__
      try:
        va_kwa_wrapper.im_class = f.im_class
      except AttributeError:
        pass
      for k in dir(f):
        if k[0] != '_' or k in ('__name__'):
          setattr(va_kwa_wrapper, k, getattr(f, k))
      if parent is not None:
        setattr(parent, info['name'], va_kwa_wrapper)
      return va_kwa_wrapper
    return f
  


repr2 = introspect._repr.repr
'''Limited ``repr``, only printing up to 4-6 levels and 100 chars per entry.

:type: repr.Repr
'''

########NEW FILE########
__FILENAME__ = main
# encoding: utf-8
'''Program main routine helpers.
'''
import sys, os, logging, signal, smisk.core
from smisk.config import config as _config

__all__ = ['setup_appdir', 'main_cli_filter', 'handle_errors_wrapper']
log = logging.getLogger(__name__)

def absapp(application, default_app_type=smisk.core.Application, *args, **kwargs):
	'''Returns an application instance or raises an exception if not possible.
	'''
	if not application:
		application = smisk.core.Application.current
		if not application:
			application = default_app_type(*args, **kwargs)
	elif type(application) is type:
		if not issubclass(application, smisk.core.Application):
			raise ValueError('application is not a subclass of smisk.core.Application')
		return application(*args, **kwargs)
	elif not isinstance(application, smisk.core.Application):
		raise ValueError('%r is not an instance of smisk.core.Application' % application)
	return application


def setup_appdir(appdir=None):
	if 'SMISK_APP_DIR' not in os.environ:
		if appdir is None:
			try:
				appdir = os.path.dirname(sys.modules['__main__'].__file__)
			except:
				raise EnvironmentError('unable to calculate SMISK_APP_DIR because: %s' % sys.exc_info())
	if appdir is not None:
		os.environ['SMISK_APP_DIR'] = os.path.abspath(appdir)
	return os.environ['SMISK_APP_DIR']


def main_cli_filter(appdir=None, bind=None, forks=None):
	'''Command Line Interface parser used by `main()`.
	'''
	forks_defaults_to = bind_defaults_to = appdir_defaults_to = ' Not set by default.'
	
	if appdir:
		appdir_defaults_to = ' Defaults to "%s".' % appdir
	
	if isinstance(bind, basestring):
		bind_defaults_to = ' Defaults to "%s".' % bind
	else:
		bind = None
	
	if forks:
		forks_defaults_to = ' Defaults to "%s".' % forks
	
	from optparse import OptionParser
	parser = OptionParser(usage="usage: %prog [options]")
	
	parser.add_option("-d", "--appdir",
	                  dest="appdir",
	                  help='Set the application directory.%s' % appdir_defaults_to,
	                  action="store",
	                  type="string",
	                  metavar="<path>",
	                  default=appdir)
	
	parser.add_option("-b", "--bind",
	                  dest="bind",
	                  help='Start a stand-alone process, listening for FastCGI connection on '\
	                       '<addr>, which can be a TCP/IP address with out without host or a UNIX '\
	                       'socket (named pipe on Windows). For example "localhost:5000", '\
	                       '"/tmp/my_process.sock" or ":5000".%s' % bind_defaults_to,
	                  metavar="<addr>",
	                  action="store",
	                  type="string",
	                  default=bind)
	
	parser.add_option("-c", "--forks",
	                  dest="forks",
	                  help='Set number of childs to fork.%s' % forks_defaults_to,
	                  metavar="<count>",
	                  type="int",
	                  default=forks)
	
	parser.add_option("-s", "--spawn",
	                  dest="spawn",
	                  help='Spawn <count> number of instances based on --bind. If --bind specifies '\
	                       'a TCP address, each instance will increase the port number. If --bind '\
	                       'is a UNIX socket, a incremental number is added as a suffix to the '\
	                       'sockets filename.',
	                  metavar="<count>",
	                  type="int",
	                  default=0)
	
	parser.add_option("", "--chdir",
	                  dest="chdir",
	                  help='Change directory to <path> before starting application.',
	                  metavar="<path>",
	                  type="string",
	                  default=None)
	
	parser.add_option("", "--umask",
	                  dest="umask",
	                  help='Change umask to <mask> before starting application.',
	                  metavar="<mask>",
	                  type="int",
	                  default=None)
	
	parser.add_option("", "--stdout",
	                  dest="stdout",
	                  help='Redirect stdout to <path> before spawning application. Recommended: /dev/null',
	                  metavar="<path>",
	                  type="string",
	                  default=None)
	
	parser.add_option("", "--stderr",
	                  dest="stderr",
	                  help='Redirect stderr to <path> before spawning application. Recommended: /dev/null',
	                  metavar="<path>",
	                  type="string",
	                  default=None)
	
	parser.add_option("", "--pidfile",
	                  dest="pidfile",
	                  help='Write process identifier to <path>. Multiple PIDs are separated by LF.',
	                  metavar="<path>",
	                  type="string",
	                  default=None)
	
	parser.add_option("", "--debug",
	                  dest="debug",
	                  help="sets log level to DEBUG",
	                  action="store_true",
	                  default=False)
	
	parser.add_option("-H", "--http",
	                  dest="http_",
	                  help='Run this application through a built-in HTTP server. Shorthand for --http-port 8080.',
	                  action="store_true",
	                  default=False)
	
	parser.add_option("", "--http-port",
	                  dest="http_port",
	                  help='Run this application through a built-in HTTP server listening on port <port>.',
	                  metavar="<port>",
	                  type="int",
	                  default=0)
	
	parser.add_option("", "--http-addr",
	                  dest="http_addr",
	                  help='Run this application through a built-in HTTP server bound to <host>.',
	                  metavar="<host>",
	                  type="string",
	                  default=None)
	
	opts, args = parser.parse_args()
	
	# Make sure empty values are None
	if not opts.bind:
		opts.bind = None
	if not opts.appdir:
		opts.appdir = None
	if not opts.forks:
		opts.forks = None
	
	if opts.http_:
		opts.http_port = 8080
	
	return opts.appdir, opts.bind, opts.forks, opts.spawn, opts.chdir, \
	       opts.umask, opts.stdout, opts.stderr, opts.pidfile, opts.http_port, \
	       opts.http_addr, opts.debug


def handle_errors_wrapper(fnc, error_cb=sys.exit, abort_cb=None, *args, **kwargs):
	'''Call `fnc` catching any errors and writing information to ``error.log``.
	
	``error.log`` will be written to, or appended to if it aldready exists,
	``ENV["SMISK_LOG_DIR"]/error.log``. If ``SMISK_LOG_DIR`` is not set,
	the file will be written to ``ENV["SMISK_APP_DIR"]/error.log``.
	
	* ``KeyboardInterrupt`` is discarded/passed, causing a call to `abort_cb`,
		if set, without any arguments.
	
	* ``SystemExit`` is passed on to Python and in normal cases causes a program
		termination, thus this function will not return.
	
	* Any other exception causes ``error.log`` to be written to and finally
		a call to `error_cb` with a single argument; exit status code.
	
	:param	error_cb:	 Called after an exception was caught and info 
	                   has been written to ``error.log``. Receives a
	                   single argument: Status code as an integer.
	                   Defaults to ``sys.exit`` causing normal program
	                   termination. The returned value of this callable
	                   will be returned by `handle_errors_wrapper` itself.
	:type	 error_cb:	 callable
	:param	abort_cb:	 Like `error_cb` but instead called when
											``KeyboardInterrupt`` was raised.
	:type	 abort_cb:	 callable
	:rtype: object
	'''
	try:
		# Run the wrapped callable
		return fnc(*args, **kwargs)
	except KeyboardInterrupt:
		if abort_cb:
			return abort_cb()
	except SystemExit:
		raise
	except:
		# Write to error.log
		try:
			logfile = os.environ.get('SMISK_LOG_DIR', os.environ.get(os.environ['SMISK_APP_DIR'], '.'))
			logfile = os.path.join(logfile, 'error.log')
			logfile = os.path.abspath(_config.get('smisk.emergency_logfile', logfile))
			f = open(logfile, 'a')
			try:
				from traceback import print_exc
				from datetime import datetime
				f.write(datetime.now().isoformat())
				f.write(" [%d] " % os.getpid())
				print_exc(1000, f)
			finally:
				f.close()
				try:
					print_exc(1000, sys.stderr)
				except:
					pass
				sys.stderr.write('Wrote emergency log to %s\n' % logfile)
		except Exception, e:
			try:
				sys.stderr.write('Failed to write emergency log to %s: %s\n' % (logfile, e))
			except:
				pass
		# Call error callback
		if error_cb:
			return error_cb(1)


class Main(object):
	default_app_type = smisk.core.Application
	_is_set_up = False
	pidfile = None
	
	def __call__(self, application=None, appdir=None, bind=None, forks=None, 
	             handle_errors=True, cli=True, config=None, pidfile=None, 
	             chdir=None, umask=None, spawn=None,
	             *args, **kwargs):
		'''Helper for setting up and running an application.
		
		If several servers are spawned a list of PIDs is returned, otherwise
		whatever returned by application.run() is returned.
		'''
		stdout = stderr = http_addr = None
		debug = False
		http_port = 0
		if cli:
			appdir, bind, forks, spawn, chdir, umask, stdout, stderr, pidfile, http_port, http_addr, debug \
			 = main_cli_filter(appdir=appdir, bind=bind, forks=forks)
		
		# Setup
		if handle_errors:
			application = handle_errors_wrapper(self.setup, application=application, 
			                                    appdir=appdir, config=config, *args, **kwargs)
		else:
			application = self.setup(application=application, appdir=appdir, config=config, *args, **kwargs)
		
		if debug:
			_config.loads("'logging': {'levels':{'':'DEBUG'}}")
		
		# Pidfile?
		if pidfile:
			self.pidfile = pidfile
			try:
				open(self.pidfile, 'w').close()
			except:
				pass
		
		# Run method kewyords
		run_kwargs = dict(bind=bind, application=application, forks=forks, handle_errors=handle_errors)
		
		# Spawn?
		if spawn:
			def childfunc(childno, bindarg):
				_chdir = chdir # ref workaround
				print 'server %d starting at %s' % (os.getpid(), bindarg)
				if _chdir is None:
					_chdir = '/'
				daemonize(chdir, umask, '/dev/null', stdout, stderr)
				run_kwargs['bind'] = bindarg
				self.run(**run_kwargs)
			socket, startport, address, args = parse_bind_arg(bind)
			childs = fork_binds(spawn, childfunc, socket=socket, startport=startport, address=address)
			return childs
		else:
			_prepare_env(chdir=chdir, umask=umask)
			if http_port or http_addr != None:
				# start the http server
				from smisk.util.httpd import Server
				if http_addr == None:
					http_addr = 'localhost'
				elif http_addr == '*':
					http_addr = ''
				if not http_port:
					http_port = 8080
				http_addr = (http_addr, http_port)
				fcgi_addr = ('127.0.0.1', 5990)
				server = Server(http_addr, fcgi_addr)
				orig_sighandlers = {}
				
				def kill_app_sighandler(signum, frame):
					try:
						print 'sending SIGKILL to application %d...' % app_pid
						log.debug('sending SIGKILL to application %d...', app_pid)
						os.kill(app_pid, 9)
					except:
						pass
				
				def sighandler(signum, frame):
					try:
						print 'sending signal %d to application %d...' % ( signum, app_pid)
						log.debug('sending signal %d to application %d...', signum, app_pid)
						os.kill(app_pid, signum)
					except:
						pass
					try:
						orig_alarm_handler = signal.signal(signal.SIGALRM, kill_app_sighandler)
						signal.alarm(2) # 2 sec delay until SIGKILLing
						os.waitpid(-1, 0)
						signal.alarm(0) # cancel SIGKILL
						signal.signal(signal.SIGALRM, orig_alarm_handler)
					except:
						pass
					try:
						orig_sighandlers[signum](signum, frame)
					except:
						pass
					signal.signal(signal.SIGALRM, lambda x,y: os._exit(0))
					signal.alarm(2) # 2 sec time limit for cleanup functions
					sys.exit(0)
				
				log_level = logging.INFO
				if debug:
					log_level = logging.DEBUG
				logging.basicConfig(level=log_level)
				orig_sighandlers[signal.SIGINT] = signal.signal(signal.SIGINT, sighandler)
				orig_sighandlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, sighandler)
				orig_sighandlers[signal.SIGHUP] = signal.signal(signal.SIGHUP, sighandler)
				# fork off the app
				run_kwargs['bind'] = '127.0.0.1:5990'
				app_pid = self.run_deferred(**run_kwargs)
				# start the web server
				print 'httpd listening on %s:%d backed by application %d' % (http_addr[0], http_addr[1], app_pid)
				server.serve_forever()
				os.kill(os.getpid(), 2)
				os.kill(os.getpid(), 15)
			else:
				# Run
				return self.run(**run_kwargs)
	
	def setup(self, application=None, appdir=None, config=None, *args, **kwargs):
		'''Helper for setting up an application.
		Returns the application instance.
		
		Only the first call is effective.
		'''
		if self._is_set_up:
			return smisk.core.Application.current
		self._is_set_up = True
		
		setup_appdir(appdir)
		
		# Load config
		if config:
			prev_cwd = os.getcwd()
			os.chdir(os.environ['SMISK_APP_DIR'])
			try:
				_config(config)
			finally:
				os.chdir(prev_cwd)
		
		return absapp(application, self.default_app_type, *args, **kwargs)
	
	
	
	def run_deferred(self, signal_parent_after_exit=signal.SIGTERM, keepalive=False, *va, **kw):
		pid = _fork()
		if pid == -1:
			log.error('fork() failed')
		if pid == 0:
			try:
				while True:
					self.run(*va, **kw)
					if not keepalive:
						break
				try:
					if signal_parent_after_exit:
						os.kill(os.getppid(), signal_parent_after_exit)
				except:
					pass
			finally:
				os._exit(0)
		else:
			return pid
	
	def run(self, bind=None, application=None, forks=None, handle_errors=False):
		'''Helper for running an application.
		'''
		# Write PID
		if self.pidfile:
			flags = os.O_WRONLY | os.O_APPEND
			if hasattr(os, 'O_EXLOCK'):
				flags = flags | os.O_EXLOCK
			fd = os.open(self.pidfile, flags)
			try:
				os.write(fd, '%d\n' % os.getpid())
			finally:
				os.close(fd)
		
		# Make sure we have an application
		application = absapp(application)
		
		# Bind
		if bind is not None:
			os.environ['SMISK_BIND'] = bind
		if 'SMISK_BIND' in os.environ:
			smisk.core.bind(os.environ['SMISK_BIND'])
			log.info('Listening on %s', smisk.core.listening())
		
		# Enable auto-reloading if any of these are True:
		if _config.get('smisk.autoreload.modules') \
		or _config.get('smisk.autoreload.config', _config.get('smisk.autoreload')):
			from smisk.autoreload import Autoreloader
			ar = Autoreloader()
			ar.start()
		
		# Forks
		if isinstance(forks, int):
			application.forks = forks
		
		# Call app.run()
		if handle_errors:
			return handle_errors_wrapper(application.run)
		else:
			return application.run()
	

main = Main()


#-------------------------------------------------------------------------
# Forking utilities

def _prepare_env(chdir=None, umask=None):
	if isinstance(chdir, basestring):
		os.chdir(chdir)
		log.debug('changed directory to %r', chdir)
	if isinstance(umask, int):
		os.umask(umask)
		log.debug('changed umask to %d', umask)

def daemonize(chdir='/', umask=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
	'''This forks the current process into a daemon.
	The stdin, stdout, and stderr arguments are file names that
	will be opened and be used to replace the standard file descriptors
	in sys.stdin, sys.stdout, and sys.stderr.
	These arguments are optional and default to /dev/null.
	Note that stderr is opened unbuffered, so
	if it shares a file with stdout then interleaved output
	may not appear in the order that you expect.
	'''
	# Do first fork.
	try:
		pid = os.fork()
		if pid > 0:
			os._exit(0) # Exit parent without calling cleanup handlers, flushing stdio buffers, etc.
	except OSError, e:
		log.critical('daemonize(): fork #1 failed: (%d) %s', e.errno, e.strerror)
		sys.exit(1)
	
	# Decouple from parent environment.
	_prepare_env(chdir, umask)
	os.setsid()
	
	# Do second fork.
	try:
		pid = os.fork()
		if pid > 0:
			os._exit(0) # Exit second parent.
	except OSError, e:
		log.critical('daemonize(): fork #2 failed: (%d) %s', e.errno, e.strerror)
		sys.exit(1)
	
	# Now I am a daemon
	
	# Redirect standard file descriptors.
	if stdin:
		if not isinstance(stdin, file):
			stdin = file(stdin, 'r')
		os.dup2(stdin.fileno(),	sys.stdin.fileno())
	
	if stdout:
		if not isinstance(stdout, file):
			stdout = file(stdout, 'a+')
		os.dup2(stdout.fileno(), sys.stdout.fileno())
	
	if stderr:
		if not isinstance(stderr, file):
			stderr = file(stderr, 'a+', 0)
		os.dup2(stderr.fileno(), sys.stderr.fileno())


def wait_for_child_processes(options=0):
	while 1:
		try:
			pid, status = os.waitpid(-1, options)
			log.debug('process %d exited with status %d', pid, status)
		except OSError, e:
			if e.errno in (4, 10):
				# Mute "Interrupted system call" and "No child processes"
				break
			# Otherwise: delegate
			raise


def control_process_runloop(pids, signals=(signal.SIGINT, signal.SIGQUIT, signal.SIGTERM), cleanup=None):
	def signal_children(signum):
		for pid in pids:
			try:
				os.kill(pid, signum)
			except OSError, e:
				# 3: No such process
				if e.errno != 3:
					raise
	
	def ctrl_proc_finalize(signum, frame):
		try:
			signal_children(signum)
			wait_for_child_processes()
		except:
			signal_children(signal.SIGKILL)
		if cleanup and callable(cleanup):
			try:
				cleanup(signum, frame)
			except:
				log.error('cleanup function failed:', exc_info=1)
	
	for signum in signals:
		signal.signal(signum, ctrl_proc_finalize)
	
	wait_for_child_processes()


def find_program_path(file, env=None, default=None, check_access=os.X_OK):
	if env is None:
		env = os.environ
	
	head, tail = os.path.split(file)
	if head and os.access(file, check_access):
		return file
	if 'PATH' in env:
		envpath = env['PATH']
	else:
		envpath = os.path.defpath
	PATH = envpath.split(os.path.pathsep)
	saved_exc = None
	saved_tb = None
	for dir in PATH:
		path = os.path.join(dir, file)
		if os.access(path, check_access):
			return path
	return default



def parse_bind_arg(args):
	'''Parse --bind argument into tuple (str socket, int port, str address, list argswithoutbind)
	'''
	socket = port = address = None
	nargs = []
	bargs = []
	
	if isinstance(args, basestring):
		bargs.append(args)
	elif args != None:
		n = False
		for arg in args:
			if n == True and arg and arg[0] != '-':
				bargs.append(arg)
				n = False
			elif arg == '--bind' or arg == '-b':
				n = True
			else:
				nargs.append(arg)
	
	if bargs:
		dst = bargs[0]
		if dst[0] == ':':
			port = int(dst[1:])
		elif ':' in dst:
			p = dst.index(':')
			port = int(dst[p+1:])
			address = dst[:p]
		else:
			socket = dst
	
	return (socket, port, address, nargs)

def extrapolate_binds(count, socket=None, port=5000, address=None):
	args = []
	if socket:
		if '%d' not in socket:
			socket += '%d'
		for n in range(count):
			args.append(socket % n)
	else:
		if not address:
			address = '127.0.0.1'
		if not port:
			port = 5000
		else:
			port = int(port)
		for n in range(count):
			args.append('%s:%s' % (address, port + n))
	return args

def _fork():
	sys.stdout.flush()
	sys.stderr.flush()
	try:
		os.fsync(sys.stdout.fileno())
		os.fsync(sys.stderr.fileno())
	except:
		pass
	return os.fork()

def fork_binds(count, childfunc, socket=None, startport=None, address=None, include_calling_thread=False):
	'''Spawn <count> number of forked <childfunc>s and return list of PIDs.
	
	Childfunc prototype:
	
		def childfunc(int childno, str bindarg):
			pass
	
	'''
	childs = []
	if not callable(childfunc):
		raise ValueError('childfunc must be a callable')
	
	binds = extrapolate_binds(count, socket, startport, address)
	
	for i in range(count):
		if include_calling_thread and i == count-1:
			log.info('child spawned successfully. PID: %d' % os.getpid())
			childs.append(os.getpid())
			childfunc(i, binds[i])
			return childs
		
		pid = _fork()
		if pid == -1:
			log.error('fork() failed')
			break
		if pid == 0:
			childfunc(i, binds[i])
			os._exit(0)
		else:
			log.info('child spawned successfully. PID: %d' % pid)
			childs.append(pid)
	
	return childs
	

########NEW FILE########
__FILENAME__ = objectproxy
# encoding: utf-8
# This module is based on paste.registry (c) 2005 Ben Bangert, released under
# the MIT license.
'''Object proxy
'''

class ObjectProxy(object):
  '''Proxy an arbitrary object, making it possible to change values that are
  passed around.
  '''
  def __new__(cls, obj=None):
    '''Create a new ObjectProxy
    '''
    self = object.__new__(cls)
    self.__dict__['__object__'] = obj
    return self
  
  def _object(self):
    return self.__dict__['__object__']
  
  def _set_object(self, obj):
    self.__dict__['__object__'] = obj
  
  def __getattr__(self, attr):
    return getattr(self._object(), attr)
  
  def __setattr__(self, attr, value):
    setattr(self._object(), attr, value)
  
  def __delattr__(self, name):
    delattr(self._object(), name)
  
  def __getitem__(self, key):
    return self._object()[key]
  
  def __setitem__(self, key, value):
    self._object()[key] = value
  
  def __delitem__(self, key):
    del self._object()[key]
  
  def __call__(self, *args, **kw):
    return self._object()(*args, **kw)
  
  def __repr__(self):
    try:
      return repr(self._object())
    except (TypeError, AttributeError):
      return '<%s.%s object at 0x%x>' %\
        (self.__class__.__module__, self.__class__.__name__, id(self))
  
  def __iter__(self):
    return iter(self._object())
  
  def __len__(self):
    return len(self._object())
  
  def __contains__(self, key):
    return key in self._object()
  
  def __hash__(self):
    return hash(self._object())
  
  def __nonzero__(self):
    return bool(self._object())
  
  def __eq__(self, b):
    return self._object() == b
  
  def __cmp__(self, b):
    return cmp(self._object(), b)
  

########NEW FILE########
__FILENAME__ = python
# encoding: utf-8
'''Python utilities, like finding and loading modules
'''
import sys, os, imp
from smisk.util.collections import unique_wild
from smisk.util.string import strip_filename_extension
from smisk.util.type import None2

__all__ = ['format_exc', 'wrap_exc_in_callable', 'classmethods', 'unique_sorted_modules_of_items', 'list_python_filenames_in_dir', 'find_modules_for_classtree', 'load_modules']

def format_exc(exc=None, as_string=False):
  ''':rtype: string
  '''
  if exc is None:
    exc = sys.exc_info()
  if exc == (None, None, None):
    return ''
  import traceback
  if as_string:
    return ''.join(traceback.format_exception(*exc))
  else:
    return traceback.format_exception(*exc)


def wrap_exc_in_callable(exc):
  '''Wrap exc in a anonymous function, for later raising.
  
  :rtype: callable
  '''
  def exc_wrapper(*args, **kwargs):
    raise exc
  return exc_wrapper


def classmethods(cls):
  '''List names of all class methods in class `cls`.
  
  :rtype: list
  '''
  return [k for k in dir(cls) \
    if (k[0] != '_' and getattr(getattr(cls, k), 'im_class', None) == type)]


def unique_sorted_modules_of_items(v):
  ''':rtype: list
  '''
  s = []
  for t in v:
    s.append(t.__module__)
  s = unique_wild(s)
  s.sort()
  return s


def list_python_filenames_in_dir(path, only_py=True):
  ''':rtype: list
  '''
  names = []
  for fn in os.listdir(path):
    if fn[-3:] == '.py':
      names.append(fn[:-3])
    elif not only_py:
      fn4 = fn[-4:]
      if fn4 == '.pyc' or fn4 == '.pyo':
        names.append(fn[:-4])
  if names:
    if not only_py:
      names = unique_wild(names)
    names.sort()
  return names


def find_modules_for_classtree(cls, exclude_root=True, unique=True):
  '''Returns a list of all modules in which cls and any subclasses are defined.
  
  :rtype: list
  '''
  if exclude_root:
    modules = []
  else:
    try:
      modules = [sys.modules[cls.__module__]]
    except KeyError:
      modules = [__import__(cls.__module__, globals(), locals())]
  for subcls in cls.__subclasses__():
    modules.extend(find_modules_for_classtree(subcls, False, False))
  if unique:
    modules = list_unique(modules)
  return modules


def find_closest_syspath(path, namebuf):
  '''TODO
  '''
  namebuf.append(os.path.basename(path))
  if path in sys.path:
    del namebuf[-1]
    return '.'.join(reversed(namebuf)), path
  path = os.path.dirname(path)
  if not path or len(path) == 1:
    return None2
  return find_closest_syspath(path, namebuf)


def load_modules(path, deep=False, skip_first_init=True, libdir=None, parent_name=None):
  '''Import all modules in a directory.
  
  .. deprecated:: 1.1.1
    This function will be removed in future versions.
  
  :param path: Path of a directory
  :type  path: string
  
  :param deep: Search subdirectories
  :type  deep: bool
  
  :param skip_first_init: Do not load any __init__ directly under `path`.
                          Note that if `deep` is ``True``, 
                          subdirectory/__init__ will still be loaded, 
                          even if `skip_first_init` is ``True``.
  :type  skip_first_init: bool
  
  :returns: A dictionary of modules imported, keyed by name.
  :rtype:   dict'''
  # DEPRECATED 1.1.1
  loaded = sys.modules.copy()
  path = os.path.abspath(path)
  if libdir and parent_name:
    top_path = os.path.abspath(libdir)
    parent_name = parent_name
  else:
    parent_name, top_path = find_closest_syspath(path, [])
  sys.path[0:0] = [top_path]
  loaded_paths = {}
  for name,mod in sys.modules.items():
    if mod:
      try:
        loaded_paths[strip_filename_extension(mod.__file__)] = mod
      except AttributeError:
        pass
  try:
    _load_modules(path, deep, skip_first_init, parent_name, loaded, loaded_paths)
  finally:
    if sys.path[0] == top_path:
      sys.path = sys.path[1:]
  return loaded

def _load_modules(path, deep, skip_init, parent_name, loaded, loaded_paths):
  # DEPRECATED 1.1.1
  for f in os.listdir(path):
    fpath = os.path.join(path, f)
    
    if strip_filename_extension(fpath) in loaded_paths:
      #print >> sys.stderr, 'AVOIDED reloading '+fpath
      continue
    
    if os.path.isdir(fpath):
      if deep and ( os.path.isfile(os.path.join(fpath, '__init__.py')) 
                    or os.path.isfile(os.path.join(fpath, '__init__.pyc'))
                    or os.path.isfile(os.path.join(fpath, '__init__.pyo')) ):
          # skip_init is False because this method is a slave and the
          # master argument is skip_first_init.
          if parent_name:
            parent_name = '%s.%s' % (parent_name, f)
          else:
            parent_name = f
          _load_modules(fpath, deep, False, parent_name, loaded, loaded_paths)
      continue
    
    if not os.path.splitext(f)[1].startswith('.py'):
      continue
    
    name = strip_filename_extension(f)
    if skip_init and name == '__init__':
      continue
    if parent_name:
      if name == '__init__':
        name = parent_name
      else:
        name = '%s.%s' % (parent_name, name)
    elif name == '__init__':
      # in the case where skip_init is False
      name = os.path.basename(path)
    
    if name not in loaded:
      findpath = path
      mod = None
      load_namev = []
      load_name = ''
      namev = name.split('.')
      findpathv = findpath.strip('/').split('/')
      for i, name_part in enumerate(namev):
        load_namev.append(name_part)
        load_name = '.'.join(load_namev)
        
        findpathv_offset = len(namev)-i-1
        if findpathv_offset > 0:
          mfindpath = ['/'+os.path.join(*findpathv[:-findpathv_offset])]
          #print >> sys.stderr, 'A findpathv=%r, findpathv_offset=%r, mfindpath=%r' % (findpathv, findpathv_offset, mfindpath)
        else:
          mfindpath = ['/'+os.path.join(*findpathv)]
        
        try:
          mfile, mpath, mdesc = imp.find_module(name_part, mfindpath)
        except ImportError, e:
          #print >> sys.stderr, 'FAIL name_part=%r, mfindpath=%r' % (name_part, mfindpath)
          raise e
        
        if mfile is None:
          mpath += '/__init__.py'
        
        mpathn = strip_filename_extension(mpath)
        modn = loaded_paths.get(mpathn, None)
        
        if modn:
          mod = modn
          continue
        
        mod = imp.load_module(load_name, mfile, mpath, mdesc)
        loaded[load_name] = mod
        loaded_paths[strip_filename_extension(mpath)] = mod
      
      assert load_name == name
  
  return loaded

########NEW FILE########
__FILENAME__ = string
# encoding: utf-8
'''String parsing, formatting, etc.
'''
import sys, os
from smisk.core import URL, Application

__all__ = ['parse_qvalue_header', 'tokenize_path', 'strip_filename_extension', 'normalize_url']

def parse_qvalue_header(s, accept_any_equals='*/*', partial_endswith='/*', return_true_if_accepts_charset=None):
  '''Parse a qvalue HTTP header'''
  vqs = []
  highqs = []
  partials = []
  accept_any = False
  
  if not partial_endswith:
    partial_endswith = None
  
  for part in s.split(','):
    part = part.strip(' ')
    p = part.find(';')
    if p != -1:
      # todo Find out what the undocumented, but revealed, level= tags in HTTP 1.1 
      #      really mean and if they exists in reality. As they are not documented,
      #      we will not implement support for it. [RFC 2616, chapter 14.1 "Accept"]
      pp = part.find('q=', p)
      if pp != -1:
        q = int(float(part[pp+2:])*100.0)
        part = part[:p]
        if return_true_if_accepts_charset is not None and part == return_true_if_accepts_charset:
          return (True, True, True, True)
        vqs.append([part, q])
        if q == 100:
          highqs.append(part)
        if part == accept_any_equals:
          accept_any = True
        continue
    # No qvalue; we use three classes: any (q=0), partial (q=50) and complete (q=100)
    if return_true_if_accepts_charset is not None and part == return_true_if_accepts_charset:
      return (True, True, True, True)
    qual = 100
    if part == accept_any_equals:
      qual = 0
      accept_any = True
    else:
      if partial_endswith is not None and part.endswith('/*'):
        partial = part[:-2]
        if not partial:
          continue
        qual = 50
        partials.append(partial) # remove last char '*'
      else:
        highqs.append(part)
    vqs.append([part, qual])
  # Order by qvalue
  vqs.sort(lambda a,b: b[1] - a[1])
  return vqs, highqs, partials, accept_any


def tokenize_path(path):
  '''Deconstruct a URI path into standardized tokens.
  
  :param path: A pathname
  :type  path: string
  :rtype: list'''
  tokens = []
  for tok in strip_filename_extension(path).split('/'):
    tok = URL.decode(tok)
    if len(tok):
      tokens.append(tok)
  return tokens

def strip_filename_extension(fn):
  '''Remove any file extension from filename.
  
  :rtype: string
  '''
  try:
    return fn[:fn.rindex('.')]
  except:
    return fn

def normalize_url(url, ref_base_url=None):
  '''
  :param url:
    An absolute URL, absolute path or relative path.
  :type  url:
    URL | string
  :param ref_base_url:
    Default absolute URL used to expand a path to a full URL.
    Uses ``smisk.core.request.url`` if not set.
  :type  ref_base_url:
    URL
  :rtype:
    URL
  '''
  is_relative_uri = False
  if '/' not in url:
    is_relative_uri = True
    u = URL()
    u.path = url
    url = u
  else:
    url = URL(url) # make a copy so we don't modify the original
  
  if not ref_base_url:
    if Application.current and Application.current.request:
      ref_base_url = Application.current.request.url
    else:
      ref_base_url = URL()
  
  if url.scheme is None:
    url.scheme = ref_base_url.scheme
  if url.user is None:
    url.user = ref_base_url.user
    if url.user is not None and url.password is None:
      url.password = ref_base_url.password
  if url.host is None:
    url.host = ref_base_url.host
  if url.port == 0:
    url.port = ref_base_url.port
  if is_relative_uri:
    base_path = ref_base_url.path
    if not base_path:
      base_path = '/'
    elif not base_path.endswith('/'):
      base_path = base_path + '/'
    url.path = base_path + url.path
  
  return url

########NEW FILE########
__FILENAME__ = threads
# encoding: utf-8
'''thread
'''
import threading, thread, logging

__all__ = ['PerpetualTimer', 'Monitor']
log = logging.getLogger(__name__)

class PerpetualTimer(threading._Timer):
  '''A subclass of threading._Timer whose run() method repeats.'''
  ident = None
  ''':type: int'''
  
  def __init__(self, frequency, callback, setup_callback=None, *args, **kwargs):
    threading._Timer.__init__(self, frequency, callback, *args, **kwargs)
    self.setup_callback = setup_callback
  
  def run(self):
    self.ident = thread.get_ident()
    if self.setup_callback is not None:
      self.setup_callback()
    while True:
      self.finished.wait(self.interval)
      if self.finished.isSet():
        return
      self.function(*self.args, **self.kwargs)
  


class Monitor(object):
  '''Periodically run a callback in its own thread.'''
  frequency = 60.0
  ''':type: float'''
  
  def __init__(self, callback, setup_callback=None, frequency=60.0):
    self.callback = callback
    self.setup_callback = setup_callback
    self.frequency = frequency
    self.thread = None
  
  def start(self):
    '''Start our callback in its own perpetual timer thread.'''
    if self.frequency > 0:
      threadname = "Monitor:%s" % self.__class__.__name__
      if self.thread is None:
        self.thread = PerpetualTimer(self.frequency, self.callback, self.setup_callback)
        self.thread.setName(threadname)
        self.thread.start()
        log.debug("Started thread %r", threadname)
      else:
        log.debug("Thread %r already started", threadname)
  start.priority = 70
  
  def stop(self):
    '''Stop our callback's perpetual timer thread.'''
    if self.thread is None:
      log.warn("No thread running for %s", self)
    else:
      # Note: For some reason threading._active dict freezes in some conditions
      # here, so we compare thread ids rather than comparing using threading.currentThread.
      if self.thread.ident != thread.get_ident():
        self.thread.cancel()
        self.thread.join()
        log.debug("Stopped thread %r", self.thread.getName())
      self.thread = None
  
  def restart(self):
    '''Stop the callback's perpetual timer thread and restart it.'''
    self.stop()
    self.start()
  

########NEW FILE########
__FILENAME__ = timing
# encoding: utf-8
'''timing
'''
import time

__all__ = ['Timer']

class Timer(object):
  '''A simple universal timer.'''
  def __init__(self, start=True):
    self.t0 = 0.0
    self.t1 = 0.0
    self.seconds = self.time
    if start:
      self.start()
  
  def start(self):
    self.t0 = time.time()
  
  def stop(self):
    '''alias of :func:`finish`
    '''
    return self.finish()
  
  def finish(self):
    self.t1 = time.time()
    return "%.0fs %.0fms %.0fus" % (self.seconds(), self.milli(), self.micro())
  
  def time(self):
    return self.t1 - self.t0
  
  def seconds(self): # alias for time
    return self.time()
  
  def milli(self):
    return (self.time() * 1000) % 1000
  
  def micro(self):
    return (self.time() * 1000000) % 1000
  

########NEW FILE########
__FILENAME__ = type
# encoding: utf-8
'''Types
'''
import sys, re
from types import *

if sys.version_info[0:2] <= (2, 5):
  try:
    from UserDict import DictMixin
  except ImportError:
    # DictMixin is new in Python 2.3
    class DictMixin: pass
  MutableMapping = DictMixin
else:
  from smisk import _MutableMapping as MutableMapping


class Symbol:
  '''General purpose named object.
  '''
  def __init__(self,name):
    self.name = name
  
  def __repr__(self):
    return self.name
  

Undefined = Symbol('Undefined')
'''Indicates an undefined value.
'''

None2 = (None, None)
''':type: tuple
'''

RegexType = type(re.compile('.'))
''':type: type
'''

########NEW FILE########
__FILENAME__ = _bsddb
# encoding: utf-8
'''Compatibility loader for Python <2.5
'''
# when we drop support for 2.4 we can do absolute imports and do no longer
# need this ugly hack.
from bsddb import *
import bsddb.dbshelve as dbshelve

########NEW FILE########
__FILENAME__ = wsgi
# encoding: utf-8
# Copyright (c) 2008, Eric Moritz <eric@themoritzfamily.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#   * Redistributions of source code must retain the above copyright
#   * notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#   * copyright notice, this list of conditions and the following
#   * disclaimer in the documentation and/or other materials provided
#   * with the distribution.  Neither the name of the <ORGANIZATION>
#   * nor the names of its contributors may be used to endorse or
#   * promote products derived from this software without specific
#   * prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
This module provides a way to use Smisk as a WSGI backend.

Conforms to :pep:`333`

Example::

  def hello_app(env, start_response):
    start_response("200 OK", [])
    return ["Hello, World"]
  from smisk.wsgi import main
  main(hello_app)

:author: Eric Moritz
:author: Rasmus Andersson
'''
import os, sys, smisk.core, logging
from smisk.util.main import *
from smisk.config import LOGGING_FORMAT, LOGGING_DATEFMT

__all__ = ['__version__', 'Request', 'Gateway', 'main']
__version__ = (0,1,0)
_hop_headers = {
  'connection':1, 'keep-alive':1, 'proxy-authenticate':1,
  'proxy-authorization':1, 'te':1, 'trailers':1, 'transfer-encoding':1,
  'upgrade':1
}

def is_hop_by_hop(header_name):
  '''Return true if 'header_name' is an HTTP/1.1 "Hop-by-Hop" header'''
  return header_name.lower() in _hop_headers

class Request(smisk.core.Request):
  '''WSGI request'''
  def prepare(self, app):
    '''Set up the environment for one request'''
    self.env['wsgi.input']        = self.input
    self.env['wsgi.errors']       = self.errors
    self.env['wsgi.version']      = app.wsgi_version
    self.env['wsgi.run_once']     = app.wsgi_run_once
    self.env['wsgi.url_scheme']   = app.request.url.scheme
    self.env['wsgi.multithread']  = app.wsgi_multithread
    self.env['wsgi.multiprocess'] = app.wsgi_multiprocess
    
    # Put a reference of ourselves in the environment so that the user
    # might reference other parts of the framework and discover if they
    # are running in Smisk or not.
    self.env['smisk.app'] = app
    
    # Rebind our send_file to the real send_file
    self.send_file = app.response.send_file
  
  def send_file(self, path):
    raise NotImplementedError('unprepared request does not have a valid send_file method')
  

class Gateway(smisk.core.Application):
  '''WSGI adapter
  '''
  # Configuration parameters; can override per-subclass or per-instance
  wsgi_version = (1,0)
  wsgi_multithread = False
  wsgi_multiprocess = True
  wsgi_run_once = False
  
  def __init__(self, wsgi_app):
    super(Gateway, self).__init__()
    self.request_class = Request
    self.wsgi_app = wsgi_app
  
  def start_response(self, status, headers, exc_info=None):
    '''`start_response()` callable as specified by 
    `PEP 333 <http://www.python.org/dev/peps/pep-0333/>`__'''
    if exc_info:
      try:
        if self.response.has_begun:
          raise exc_info[0],exc_info[1],exc_info[2]
        else:
          # In this case of response not being initiated yet, this will replace 
          # both headers and any buffered body.
          self.error(exc_info[0], exc_info[1], exc_info[2])
      finally:
        exc_info = None # Avoid circular ref.
    elif len(self.response.headers) != 0:
      raise AssertionError("Headers already set!")
    
    assert isinstance(status, str),"Status must be a string"
    assert len(status)>=4,"Status must be at least 4 characters"
    assert int(status[:3]),"Status message must begin w/3-digit code"
    assert status[3]==" ", "Status message must have a space after code"
    
    if __debug__:
      for name,val in headers:
        assert isinstance(name, str),"Header names must be strings"
        assert isinstance(val, str),"Header values must be strings"
        assert not is_hop_by_hop(name),"Hop-by-hop headers not allowed"
    
    # Construct the headers
    # Add the status to the headers
    self.response.headers = ['Status: '+status]
    # Append each of the headers provided by wsgi
    self.response.headers += [": ".join(header) for header in headers]
    # Add the X-Powered-By header to show off this extension
    self.response.headers.append("X-Powered-By: smisk+wsgi/%d.%d.%d" % __version__)
    # Return the write function as required by the WSGI spec
    return self.response.write
  
  def service(self):
    self.request.prepare(self)
    output = self.wsgi_app(self.request.env, self.start_response)
    # Discussion about Content-Length:
    #  Output might be an iterable in which case we can not trust len()
    #  but in a perfect world, we did know how many parts we got and if
    #  we only got _one_ we could also add a Content-length. But no.
    #  Instead, we rely on the host server splitting up things in nice
    #  chunks, using chunked transfer encoding, (If the server complies
    #  to HTTP/1.1 it is required to do so, so we are pretty safe) or
    #  simply rely on the host server setting the Content-Length header.
    for data in output:
      self.response.write(data)
  

# XXX TODO replace this main function with the stuff from smisk.util.main
def main(wsgi_app, appdir=None, bind=None, forks=None, handle_errors=True, cli=True):
  '''Helper for setting up and running an application.
  
  This is normally what you do in your top module ``__init__``::
  
    from smisk.wsgi import main
    from your.app import wsgi_app
    main(wsgi_app)
  
  Your module is now a runnable program which automatically configures and
  runs your application. There is also a Command Line Interface if `cli` 
  evaluates to ``True``.
  
  :Parameters:
    wsgi_app : callable
      A WSGI application
    appdir : string
      Path to the applications base directory.
    bind : string
      Bind to address (and port). Note that this overrides ``SMISK_BIND``.
    forks : int
      Number of child processes to spawn.
    handle_errors : bool
      Handle any errors by wrapping calls in `handle_errors_wrapper()`
    cli : bool
      Act as a *Command Line Interface*, parsing command line arguments and
      options.
  
  :rtype: None
  '''
  if cli:
    appdir, bind, forks = main_cli_filter(appdir=appdir, bind=bind, forks=forks)
  
  # Setup logging
  # Calling basicConfig has no effect if logging is already configured.
  
  logging.basicConfig(format=LOGGING_FORMAT, datefmt=LOGGING_DATEFMT)
  
  # Bind
  if bind is not None:
    os.environ['SMISK_BIND'] = bind
  if 'SMISK_BIND' in os.environ:
    smisk.core.bind(os.environ['SMISK_BIND'])
    log.info('Listening on %s', smisk.core.listening())
  
  # Configure appdir
  setup_appdir(appdir)
  
  # Create the application
  application = Gateway(wsgi_app=wsgi_app)
  
  # Forks
  if isinstance(forks, int) and forks > -1:
    application.forks = forks
  
  # Runloop
  if handle_errors:
    return handle_errors_wrapper(application.run)
  else:
    return application.run()



if __name__ == '__main__':
  from wsgiref.validate import validator # Import the wsgi validator app

  def hello_app(env, start_response):
    start_response("200 OK", [('Content-Type', 'text/plain')])
    return ["Hello, World"]
  
  if len(sys.argv) != 2:
    print "Usage: %s hostname:port" % (sys.argv[0])
    print "This runs a sample fastcgi server under the hostname and"
    print "port given in argv[1]"

  smisk.core.bind(sys.argv[1])

  app = validator(hello_app)
  Gateway(app).run()

########NEW FILE########
__FILENAME__ = benchmark_core_xml_escape
#!/usr/bin/env python
# encoding: utf-8
import smisk.core.xml as xml
from smisk.util.benchmark import benchmark
#
# Recorded performance:
# 
# 2009-03-05, Rasmus Andersson
# On iMac 24, Intel Core 2 duo 2.8GHz (using one full core):
#
# FUNCTION  TYPE    PERFORMANCE
# --------- ------- -----------
# escape    bytes    122.7 MB/s
# escape    unicode   60.0 MB/s
# unescape  bytes    104.6 MB/s
# unescape  unicode   49.8 MB/s
#

DOCUMENT_BYTES = 'Some <document> with strings & characters which should be "escaped"' * 1024
DOCUMENT_UNICODE = u'Some <document> with strings & characters which should be "escaped"' * 1024

if __name__ == "__main__":
  
  iterations = 10000
  print 'test data is %d characters long' % len(DOCUMENT_BYTES)
  
  for x in benchmark('escape bytes', iterations):
    xml.escape(DOCUMENT_BYTES)
  
  for x in benchmark('escape unicode', iterations):
    xml.escape(DOCUMENT_UNICODE)
  
  escaped_bytes = xml.escape(DOCUMENT_BYTES)
  escaped_unicode = xml.escape(DOCUMENT_UNICODE)
  
  for x in benchmark('unescape bytes', iterations):
    xml.escape(escaped_bytes)
  
  for x in benchmark('unescape unicode', iterations):
    xml.escape(escaped_unicode)

########NEW FILE########
__FILENAME__ = benchmark
#!/usr/bin/env python
# encoding: utf-8
import sys, os, time, random
from smisk.util.benchmark import benchmark
import smisk.ipc.bsddb

def main():
  from optparse import OptionParser
  parser = OptionParser()
  
  parser.add_option("-t", "--sync-time", dest="sync_time",
                  help="Start benchmark at specified time, formatted HH:MM[:SS]. Disabled by default.", 
                  metavar="TIME", default=None)
  
  parser.add_option("-i", "--iterations", dest="iterations",
                  help="Number of iterations to perform. Defaults to 100 000", 
                  metavar="N", default=100000, type='int')
  
  parser.add_option("-d", "--idle", dest="idle",
                  help="Milliseconds to idle between operations. Defaults to 0 (disabled).", 
                  metavar="MS", default=0, type='int')
  
  parser.add_option("-r", "--read",
                  action="store_true", dest="read", default=False,
                  help="Perform reading")
  
  parser.add_option("-w", "--write",
                  action="store_true", dest="write", default=False,
                  help="Perform writing")
  
  parser.add_option("-c", "--cdb",
                  action="store_true", dest="cdb", default=False,
                  help="Use lock-free CDB (one writer/multiple readers).")
  
  (options, args) = parser.parse_args()
  
  if not options.read and not options.write:
    print >> sys.stderr, 'Neither --write nor --read was specified'\
      ' -- automatically enabling both'
    options.read = True
    options.write = True
  
  store = smisk.ipc.bsddb.shared_dict()
  idle_sec = float(options.idle) / 1000.0
  
  if options.sync_time:
    timestr = time.strftime('%Y%d%m') + options.sync_time
    try:
      options.sync_time = time.strptime(timestr, '%Y%d%m%H:%M:%S')
    except ValueError:
      try:
        options.sync_time = time.strptime(timestr, '%Y%d%m%H:%M')
      except ValueError:
        raise ValueError('time does not match format: HH:MM[:SS]')
    sync_t = time.mktime(options.sync_time)
    
    if sync_t > time.time():
      print 'Waiting for time sync %s' % time.strftime('%H:%M:%S', options.sync_time)
      last_printed_second = 0
      while 1:
        t = time.time()
        if sync_t <= t:
          break
        ti = int(sync_t - t)
        if ti and ti != last_printed_second:
          last_printed_second = ti
          sys.stdout.write('%d ' % ti)
          sys.stdout.flush()
        time.sleep(0.01)
      sys.stdout.write('\n')
      sys.stdout.flush()
  
  rw = 'write'
  if options.read and options.write:
    rw = 'write+read'
  elif options.read:
    rw = 'read'
  
  pid = os.getpid()
  time.sleep(0.1 * random.random())
  
  idle_msg = ''
  if idle_sec > 0.0:
    idle_msg = ' with a per-iteration idle time of %.0f ms' % (idle_sec * 1000.0)
  print 'Benchmarking %d iterations of %s#%d%s' % (options.iterations, rw, pid, idle_msg)
  
  if options.read and options.write:
    for x in benchmark('%s#%d' % (rw, pid), options.iterations, it_subtractor=idle_sec):
      store['pid'] = pid
      time.sleep(idle_sec)
      pid_found = store['pid']
  elif options.read:
    for x in benchmark('%s#%d' % (rw, pid), options.iterations, it_subtractor=idle_sec):
      time.sleep(idle_sec)
      pid_found = store['pid']
  else:
    for x in benchmark('%s#%d' % (rw, pid), options.iterations, it_subtractor=idle_sec):
      time.sleep(idle_sec)
      store['pid'] = pid


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = concurrency
#!/usr/bin/env python
# encoding: utf-8
# 
# Concurrent Data Store test app
# 
# http://www.oracle.com/technology/documentation/berkeley-db/db/ref/cam/intro.html
# 

import sys, os, time, random
import smisk.ipc.bsddb

def main():
  from optparse import OptionParser
  parser = OptionParser()
  
  parser.add_option("-i", "--random-idle", dest="idle",
                  help="Milliseconds to idle between operations, randomized 0-1. Defaults to 100.",
                  metavar="MS", default=100, type='int')
  
  parser.add_option("-r", "--read",
                  action="store_true", dest="read", default=False,
                  help="Perform reading")
  
  parser.add_option("-w", "--write",
                  action="store_true", dest="write", default=False,
                  help="Perform writing")
  
  parser.add_option("-d", "--detect",
                  action="store_true", dest="detect_concurrance", default=False,
                  help="When concurrance is detected, print info to stdout. Implies -r and -w")
  
  (options, args) = parser.parse_args()
  
  if not options.read and not options.write:
    options.read = True
  
  store = smisk.ipc.bsddb.shared_dict()
  idle_sec = float(options.idle) / 1000.0
  
  if options.detect_concurrance:
    options.write = True
    options.read = True
  
  rw = 'write'
  if options.read and options.write:
    rw = 'write+read'
  elif options.read:
    rw = 'read'
  
  pid = os.getpid()
  
  idle_msg = ''
  if idle_sec > 0.0:
    idle_msg = ' with randomized iteration idle time: 0.0-%.0f ms' % (idle_sec * 1000.0)
  print '[%d] Running %s%s' % (pid, rw, idle_msg)
  
  while 1:
    if options.write:
      time.sleep(random.random()*idle_sec)
      store['pid'] = pid
    if options.read:
      time.sleep(random.random()*idle_sec)
      try:
        pid_found = store['pid']
      except KeyError:
        pass
    if options.detect_concurrance and pid_found != pid:
      print '[%d] Concurrance detected -- #%d wrote in between' % (pid, pid_found)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = test_POST
'''This module exposes the post bug that Eric Moritz is experiences

where smisk segfaults

:See: Fixed in 77188bce80d5 <http://hg.hunch.se/smisk/diff/77188bce80d5/src/Stream.c>
'''
from smisk import wsgi
import smisk.core
from StringIO import StringIO

def safe_copyfileobj(fsrc, fdst, length=16*1024, size=0):
    '''
    A version of shutil.copyfileobj that will not read more than 'size' bytes.
    This makes it safe from clients sending more than CONTENT_LENGTH bytes of
    data in the body.
    '''
    if not size:
        return
    while size > 0:
        buf = fsrc.read(min(length, size))
        if not buf:
            break
        fdst.write(buf)
        size -= len(buf)


# I think this is the offender, taken from Django's WSGIRequest object in 
# django.core.handlers.wsgi
def _get_raw_post_data(environ):
    buf = StringIO()
    try:
        # CONTENT_LENGTH might be absent if POST doesn't have content at all (lighttpd)
        content_length = int(environ.get('CONTENT_LENGTH', 0))
    except ValueError: # if CONTENT_LENGTH was empty string or not an integer
        content_length = 0
    if content_length > 0:
        safe_copyfileobj(environ['wsgi.input'], buf,
                         size=content_length)
    _raw_post_data = buf.getvalue()
    buf.close()
    return _raw_post_data


def WSGIPostTest(environ, start_request):

    if environ['REQUEST_METHOD'] == 'GET':
        fh = file("./html/test_POST.html")
        lines = fh.readlines()
        fh.close()
        start_request("200 OK", [])
        return lines
    elif environ['REQUEST_METHOD'] == 'POST':
        raw_post_data = _get_raw_post_data(environ)
        start_request("200 OK", [])
        return [raw_post_data]

smisk.core.bind("127.0.0.1:3030")
wsgi.Application(WSGIPostTest).run()

########NEW FILE########
