__FILENAME__ = myadapter
from pyamf.adapters import register_adapter


def when_imported(mod):
    """
    This function is called immediately after mymodule has been imported.
    It configures PyAMF to encode a list when an instance of mymodule.CustomClass
    is encountered.
    """
    import pyamf

    pyamf.add_type(mod.CustomClass, lambda obj: list(obj))


register_adapter('mymodule', when_imported)
########NEW FILE########
__FILENAME__ = mymodule
# mymodule.py

class CustomClass(object):
    def __iter__(self):
        return iter([1, 2, 3])
########NEW FILE########
__FILENAME__ = iexternalizable
import pyamf

class Person(object):
    class __amf__:
        external = True

    def __writeamf__(self, output):
        # Implement the encoding here
        pass

    def __readamf__(self, input):
        # Implement the decoding here
        pass

pyamf.register_class(Person, 'com.acme.app.Person')
########NEW FILE########
__FILENAME__ = models1
# models.py

from google.appengine.ext import db

import pyamf


class User(db.Model):
    username = db.StringProperty()
    password = db.StringProperty()

    name = db.StringProperty()
    dob = db.DateProperty()


pyamf.register_class(User, 'com.acme.app.User')
########NEW FILE########
__FILENAME__ = models2
# models.py

from google.appengine.ext import db

import pyamf


class User(db.Model):
    class __amf__:
        exclude = ('password',)

    username = db.StringProperty()
    password = db.StringProperty()

    name = db.StringProperty()
    dob = db.DateProperty()


pyamf.register_class(User, 'com.acme.app.User')
########NEW FILE########
__FILENAME__ = models3
# models.py

from google.appengine.ext import db

import pyamf


class User(db.Model):
    class __amf__:
        exclude = ('password',)
        readonly = ('username',)

    username = db.StringProperty()
    password = db.StringProperty()

    name = db.StringProperty()
    dob = db.DateProperty()


pyamf.register_class(User, 'com.acme.app.User')
########NEW FILE########
__FILENAME__ = proxied-attr
import pyamf

class Person(object):
    class __amf__:
        proxy = ('address',)

pyamf.register_class(Person, 'com.acme.app.Person')
########NEW FILE########
__FILENAME__ = server
import logging

from google.appengine.ext import db

from pyamf.remoting.gateway.wsgi import WSGIGateway

from models import User


class UserService(object):
    def saveUser(self, user):
        user.put()

    def getUsers(self):
        return User.all()


services = {
    'user': UserService
}

gw = WSGIGateway(services, logger=logging)
########NEW FILE########
__FILENAME__ = static-attr
import pyamf

class Person(object):
    class __amf__:
        static = ('gender', 'dob')

pyamf.register_class(Person, 'com.acme.app.Person')
########NEW FILE########
__FILENAME__ = synonym
import pyamf

class UserProfile(object):
    class __amf__:
        synonym = {'public': '_public'}

pyamf.register_class(Person, 'com.acme.app.UserProfile')
########NEW FILE########
__FILENAME__ = whitelist
# models.py

from google.appengine.ext import db

import pyamf


class User(db.Model):
    class __amf__:
        dynamic = False
        exclude = ('password',)
        readonly = ('username',)

    username = db.StringProperty()
    password = db.StringProperty()

    name = db.StringProperty()
    dob = db.DateProperty()


pyamf.register_class(User, 'com.acme.app.User')
########NEW FILE########
__FILENAME__ = alias-decorator
import pyamf

@RemoteClass(alias="model.MyClass")
class MyClass:
    def __init__(self, *args, **kwargs):
        self.a = args[0]
        self.b = args[1]

class RemoteClass(object):
    def __init__(self, alias):
        self.alias = alias

    def __call__(self, klass):
        pyamf.register_class(klass, self.alias)
        return klass


########NEW FILE########
__FILENAME__ = example-classes
class User(object):
    def __init__(self, name, pass):
        self.name = name
        self.pass = pass

class Permission(object):
    def __init__(self, type):
        self.type = type

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.
#
# Documentation build configuration file.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this file.
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os, time
from shutil import copyfile

from docutils.core import publish_parts

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute.
sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('html'))

def rst2html(input, output):
    """
    Create html file from rst file.
    
    :param input: Path to rst source file
    :type: `str`
    :param output: Path to html output file
    :type: `str`
    """
    file = os.path.abspath(input)
    rst = open(file, 'r').read()
    html = publish_parts(rst, writer_name='html')
    body = html['html_body']

    tmp = open(output, 'w')
    tmp.write(body)
    tmp.close()
    
    return body

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
# 
# Make sure to install the following Sphinx extension module as well:
# - http://packages.python.org/sphinxcontrib-epydoc
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.extlinks',
              'sphinxcontrib.epydoc']

# Paths that contain additional templates, relative to this directory.
templates_path = ['html']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# create content template for the homepage
readme = rst2html('../README.txt', 'html/intro.html')
readme = copyfile('../CHANGES.txt', 'changelog.rst')

# General substitutions.
project = 'PyAMF'
url = 'http://pyamf.org'
description = 'AMF for Python'
copyright = "Copyright &#169; 2007-%s The <a href='%s'>%s</a> Project. All rights reserved." % (
            time.strftime('%Y'), url, project)

# We look for the __init__.py file in the current PyAMF source tree
# and replace the values accordingly.
import pyamf

# The full version, including alpha/beta/rc tags.
version = str(pyamf.version)

# The short X.Y version.
release = version[:3]

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['build', 'tutorials/examples']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
#pygments_style = 'pygments'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# Note: you can download the 'beam' theme from:
# http://github.com/collab-project/sphinx-themes
# and place it in a 'themes' directory relative to this config file.
html_theme = 'beam'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = '%s - %s' % (project, description)

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['html/static']

# The name of an image file (.ico) that is the favicon of the docs.
html_favicon = 'html/static/pyamf.ico'

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {
    'index': 'defindex.html',
    'tutorials/index': 'tutorials.html',
}

# If false, no module index is generated.
html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

# Output an OpenSearch description file.
html_use_opensearch = 'http://pyamf.org'

# Output file base name for HTML help builder.
htmlhelp_basename = 'pyamf' + release.replace('.', '')

# Split the index
html_split_index = True


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PyAMF.tex', html_title,
   copyright, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = 'html/static/logo.png'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# -- Options for external links --------------------------------------------------

# A dictionary mapping URIs to a list of regular expression.
#
# Each key of this dictionary is a base url of an epydoc-generated
# documentation. Each value is a list of regular expressions, the reference
# target must match (see re.match()) to be cross-referenced with the base url.
epydoc_mapping = {
   # TODO: don't harcode version nr
   'http://api.pyamf.org/0.6.1/': [r'pyamf\.'],
}

# refer to the Python standard library.
intersphinx_mapping = {'python': ('http://docs.python.org', None)}

# A list of regular expressions that match URIs that should
# not be checked when doing a 'make linkcheck' build (since Sphinx 1.1)
linkcheck_ignore = [r'http://localhost:\d+/']

# The base url of the Trac instance you want to create links to
trac_url = 'http://dev.pyamf.org'

# Trac url mapping
extlinks = {'ticket': (trac_url + '/ticket/%s', '#')}


########NEW FILE########
__FILENAME__ = client
#!/usr/bin/python
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Client for the SQLAlchemy Addressbook example.

@see: U{AddressBookExample<http://pyamf.org/wiki/AddressBookExample>} wiki page.
@since: 0.5
"""


import logging
from optparse import OptionParser

from server import host, port, namespace

from pyamf.remoting.client import RemotingService


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=port,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default=host,
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)

service = client.getService('ExampleService')
ns = namespace + '.'

print service.insertDefaultData()

print 'Load users:'
for user in service.loadAll(ns + 'User'):
    print '\t%s. %s (%s)' % (user.id, user.first_name, user.created)


########NEW FILE########
__FILENAME__ = controller
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Controller for SQLAlchemy Addressbook example.

@since: 0.4.1
"""

from datetime import datetime

import pyamf

import models
from persistent import Schema


class SAObject(object):
    """
    Handles common operations for persistent objects.
    """
    
    def load(self, class_alias, key):
        klass = pyamf.load_class(class_alias).klass
        session = Schema().session
        return session.query(klass).get(key)

    def loadAll(self, class_alias):
        klass = pyamf.load_class(class_alias).klass
        session = Schema().session
        return session.query(klass).all()

    def loadAttr(self, class_alias, key, attr):
        obj = self.load(class_alias, key)
        return getattr(obj, attr)

    def save(self, obj):
        session = Schema().session
        merged_obj = session.merge(obj)
        session.commit()

    def saveList(self, objs):
        for obj in objs:
            self.save(obj)

    def remove(self, class_alias, key):
        klass = pyamf.load_class(class_alias).klass
        session = Schema().session
        obj = session.query(klass).get(key)
        session.delete(obj)
        session.commit()

    def removeList(self, class_alias, keys):
        for key in keys:
            self.remove(class_alias, key)

    def insertDefaultData(self):
        user = models.User()
        user.first_name = 'Bill'
        user.last_name = 'Lumbergh'
        user.created = datetime.utcnow()
        for label, email in {'personal': 'bill@yahoo.com', 'work': 'bill@initech.com'}.iteritems():
            email_obj = models.Email()
            email_obj.label = label
            email_obj.email = email
            user.emails.append(email_obj)

        for label, number in {'personal': '1-800-555-5555', 'work': '1-555-555-5555'}.iteritems():
            phone_obj = models.PhoneNumber()
            phone_obj.label = label
            phone_obj.number = number
            user.phone_numbers.append(phone_obj)

        session = Schema().session
        session.add(user)
        session.commit()
        
        return 'Added user: %s %s' % (user.first_name, user.last_name)

########NEW FILE########
__FILENAME__ = models
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


"""
Model classes for the SQLAlchemy Addressbook example.

@since: 0.4.1
"""


class User(object):
    def __init__(self):
        self.first_name = None
        self.last_name = None
        self.emails = []
        self.phone_numbers = []
        self.created = None


class PhoneNumber(object):
    def __init__(self):
        self.label = None
        self.number = None


class Email(object):
    def __init__(self):
        self.label = None
        self.email = None

########NEW FILE########
__FILENAME__ = persistent
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Schema for SQLAlchemy Addressbook example.

@since: 0.4.1
"""


import sqlalchemy as sa
from sqlalchemy import orm

import models


class Schema(object):
    """
    Describes the schema and mappers used by the SQLAlchemy example.
    """
    engine = sa.create_engine('sqlite:///sqlalchemy_example.db', echo=False)

    def _get_session(self):
        return orm.scoped_session(orm.sessionmaker(bind=self.engine))

    session = property(_get_session)

    def createSchema(self):
        metadata = sa.MetaData()

        metadata = sa.MetaData()
        self.users_table = sa.Table('users_table', metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('first_name', sa.String(50)),
            sa.Column('last_name', sa.String(50)),
            sa.Column('created', sa.TIMESTAMP, nullable=False,
                                 server_default="2001-01-01 01:01:01"))

        self.phone_numbers_table = sa.Table('phone_numbers_table', metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('users_table.id')),
            sa.Column('label', sa.String(50)),
            sa.Column('number', sa.String(50)))

        self.emails_table = sa.Table('emails_table', metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('users_table.id')),
            sa.Column('label', sa.String(50)),
            sa.Column('email', sa.String(50)))

        metadata.create_all(self.engine)

    def createMappers(self):
        orm.clear_mappers()

        orm.mapper(models.User, self.users_table, properties={
            'emails': orm.relation(models.Email, lazy=False),
            'phone_numbers': orm.relation(models.PhoneNumber, lazy=True)})
        orm.mapper(models.Email, self.emails_table)
        orm.mapper(models.PhoneNumber, self.phone_numbers_table)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
#
# Copyright (c) PyAMF Project.
# See LICENSE.txt for details.

"""
Simple WSGI server for SQLAlchemy Addressbook example.

@since: 0.4.1
"""


import pyamf
from pyamf import amf3

import persistent
import controller
import models

# Server defaults
port = 8000
host = 'localhost'

# Setup database
schema = persistent.Schema()
schema.createSchema()
schema.createMappers()

# Set this to True so that returned objects and arrays are bindable
amf3.use_proxies_default = True

# Map class aliases
# These same aliases must be registered in the Flash Player client
# with the registerClassAlias function.
namespace = 'org.pyamf.examples.addressbook.models'
pyamf.register_package(models, namespace)

# Map controller methods
sa_obj = controller.SAObject()
mapped_services = {
    'ExampleService': sa_obj
}


if __name__ == '__main__':
    import optparse
    import logging
    import os, sys

    from wsgiref import simple_server
    from pyamf.remoting.gateway.wsgi import WSGIGateway
	
    usage = """usage: %s [options]""" % os.path.basename(sys.argv[0])
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--port", default=port,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default=host,
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG,
           format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')

    host = options.host
    port = int(options.port)

    # Start server
    print "Running SQLAlchemy AMF gateway on http://%s:%d" % (host, port)
    print "Press Ctrl-c to stop server."
	
    server = simple_server.WSGIServer((host, port),
                                simple_server.WSGIRequestHandler)
    gateway = WSGIGateway(mapped_services, logger=logging)
    
    def app(environ, start_response):
        if environ['PATH_INFO'] == '/crossdomain.xml':
            fn = os.path.join(os.getcwd(), os.path.dirname(__file__),
               'crossdomain.xml')

            fp = open(fn, 'rt')
            buffer = fp.readlines()
            fp.close()

            start_response('200 OK', [
                ('Content-Type', 'application/xml'),
                ('Content-Length', str(len(''.join(buffer))))
            ])

            return buffer

        return gateway(environ, start_response)
        
    server.set_app(app)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
Python ByteArray example.

@since: 0.5
""" 

import os
from optparse import OptionParser

from gateway import images_root

from pyamf.amf3 import ByteArray
from pyamf.remoting.client import RemotingService


# parse commandline options
parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="127.0.0.1",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


# define gateway
url = 'http://%s:%d' % (options.host, int(options.port))
server = RemotingService(url)
service = server.getService('getSnapshots')()

# get list of snapshots
base_path = service[0]
types = service[1]
snapshots = service[2]

print "Found %d snapshot(s):" % (len(snapshots))

for snapshot in snapshots:
    print "\t%s%s" % (base_path, snapshot['name'])    

# save snapshot
path = 'django-logo.jpg'
image = os.path.join(images_root, path)
file = open(image, 'r').read()

snapshot = ByteArray()
snapshot.write(file)

save_snapshot = server.getService('ByteArray.saveSnapshot')
saved = save_snapshot(snapshot, 'jpg')

print "Saved snapshot:\n\t%s:\t%s" % (saved['name'], saved['url'])

########NEW FILE########
__FILENAME__ = gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import logging

from pyamf.remoting.gateway.django import DjangoGateway

import python.gateway.views as views
from python.settings import DEBUG


services = {
    'ByteArray.saveSnapshot': views.save_snapshot,
    'getSnapshots': views.get_snapshots
}

gw = DjangoGateway(services, logger=logging, debug=DEBUG)

########NEW FILE########
__FILENAME__ = models
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = views
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import glob
import os.path
import tempfile

from django.http import HttpResponse, get_host
from pyamf.flex import ArrayCollection

from python import gateway


max_result = 50
file_types = 'jpg,png'
base_url = 'http://%s/images/'


def get_snapshots(http_request):
    """
    Gets a list of snapshots in the images dir.

    @return: list with 3 elements: URL of image folder, allowed filetypes and
        the L{ArrayCollection} of snapshots
    """
    url = base_url % get_host(http_request)
    extensions = file_types.split(',')
    l = []

    for type in extensions:
        location = os.path.join(gateway.images_root, '*.' + type.strip())
        for img in glob.glob(location):
            name = img[len(gateway.images_root) + 1:]
            obj = {
                'name': name
            }

            l.append(obj)

    l.reverse()

    return [url, extensions, ArrayCollection(l[:max_result])]


def save_snapshot(http_request, image, type):
    """
    Saves an image to the static image dir.

    @param image: A L{pyamf.amf3.ByteArray} instance
    """
    fp = tempfile.mkstemp(dir=gateway.images_root, prefix='snapshot_',
                          suffix='.' + type)

    fp = open(fp[1], 'wb+')
    fp.write(image.getvalue())
    fp.close()

    url = base_url % get_host(http_request)
    name = fp.name[len(gateway.images_root) + 1:]

    return {
        'url': url + name,
        'name': name
    }


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for python project.

DEBUG = True

import logging
LOG_LEVEL = logging.INFO

if DEBUG:
    LOG_LEVEL = logging.DEBUG

logging.basicConfig(
    level = LOG_LEVEL,
    format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
)

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!q2sh7ue8^=bu&wj9tb9&4fx^dayk=wnxo^mtd)xmw1y2)6$w$'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'python.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import os.path

from django.conf.urls.defaults import *

import python.gateway

urlpatterns = patterns('',
    # Example:
    # (r'^python/', include('python.foo.urls')),

    (r'^images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': python.gateway.images_root}),
    (r'^$', 'python.gateway.gateway.gw'),
    (r'^crossdomain.xml$', 'django.views.static.serve',
     {'document_root': os.path.abspath(os.path.dirname(__file__)), 'path': 'crossdomain.xml'}),
    # Uncomment this for admin:
    # (r'^admin/', include('django.contrib.admin.urls')),
)

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/python
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
GeoIP example client.

@see: U{GeoipExample<http://pyamf.org/wiki/GeoipExample>} wiki page.
@since: 0.1
"""


import logging
from optparse import OptionParser

import server

from pyamf.remoting.client import RemotingService


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)

service = client.getService('geoip')
print service.getGeoInfo()

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


"""
GeoIP example server.

@since: 0.1
"""                                                             


try:
    import GeoIP
    
    gi = GeoIP.new(GeoIP.GEOIP_STANDARD)
except ImportError:
    raise ImportError('This example requires the Maxmind GeoIP Python API package')

import pyamf
from pyamf.remoting.gateway import expose_request


class GeoInfo(object):
    def __init__(self):
        self.country = {}
        self.ip = ''

    def __repr__(self):
        return '<%s country=%s ip=%s>' % (GeoInfo.__name__, self.country, self.ip)

pyamf.register_class(GeoInfo, 'org.pyamf.examples.geoip.GeoInfo')


class GeoService(object):
    def __init__(self, engine):
        self.engine = engine

    def getCountryName(self, by, target):
        if by == 'name':
            return self.engine.country_name_by_name(target)

        return self.engine.country_name_by_addr(target)

    def getCountryCode(self, by, target):
        if by == 'name':
            return self.engine.country_code_by_name(target)

        return self.engine.country_code_by_addr(target)

    def getOrganization(self, by, target):
        if by == 'name':
            return self.engine.org_by_name(target)

        return self.engine.org_by_addr(target)

    def getRegion(self, by, target):
        if by == 'name':
            return self.engine.region_by_name(target)

        return self.engine.region_by_addr(target)

    def getRecord(self, by, target):
        if by == 'name':
            return self.engine.record_by_name(target)

        return self.engine.record_by_addr(target)

    @expose_request
    def getGeoInfo(self, environ, target=None):
        if target is None:
            target = environ['REMOTE_ADDR']

        gi = GeoInfo()
        gi.country = {
            'name': self.getCountryName('addr', target),
            'code': self.getCountryCode('addr', target)
        }
        gi.ip = target

        return gi

   
services = {
    'geoip': GeoService(gi)
}


if __name__ == '__main__':
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", default=8000,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default="localhost",
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    gw = WSGIGateway(services)

    httpd = simple_server.WSGIServer(
        (options.host, int(options.port)),
        simple_server.WSGIRequestHandler,
    )

    httpd.set_app(gw)

    print "Running GeoIP AMF gateway on http://%s:%d" % (options.host,
                                                         int(options.port))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import logging
from optparse import OptionParser

import guestbook
from server import port

from pyamf.remoting.client import RemotingService


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


parser = OptionParser()
parser.add_option("-p", "--port", default=port,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d/gateway' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)

service = client.getService('guestbook')

# print service.addMessage('Nick', 'http://boxdesign.co.uk',
#                          'nick@pyamf.org', 'Hello World!')
print service.getMessages()

########NEW FILE########
__FILENAME__ = guestbook
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Guestbook remoting service.

@since: 0.3
"""


from datetime import datetime
from urlparse import urlparse
import re

try:
    from genshi.input import HTML
    from genshi.filters import HTMLSanitizer
except ImportError:
    import sys
    print >> sys.stderr, "Genshi is required for this example"
    raise

from twisted.internet import defer
from twisted.internet.task import LoopingCall

import pyamf 
from pyamf.flex import ArrayCollection, ObjectProxy
from pyamf.remoting.gateway import expose_request


EMAIL_RE = r"^.+\@(\[?)[a-zA-Z0-9\-\.]+\.([a-zA-Z]{2,3}|[0-9]{1,3})(\]?)$"

# This is MySQL specific, make sure that if you use a different database server
# this is updated to ensure sql injection attacks don't occur 
def sql_safe(value):
    if isinstance(value, basestring):
        return value.replace("'", "\\'")
    elif isinstance(type(value), (int, float)):
        return value

    raise TypeError, 'basestring, int or float expected' 


def is_valid_url(url):
    o = urlparse(url)

    # scheme
    if o[0] == '':
        return (False, 'Scheme required')

    if o[1] == '':
        return (False, 'Hostname required')

    return (True, None)


def is_valid_email(email):
    """
    A very basic email address format validator
    """
    if re.match(EMAIL_RE, email) != None:
        return True

    return False


def strip_message(message):
    markup = HTML(message) | HTMLSanitizer()

    return markup.render('xhtml')


def build_message(row):
    m = Message()

    m.name = row[0]
    m.url = row[1]
    #m.email = row[2]
    m.created = row[3]
    m.message = row[4]

    return m


class Message:
    pass

pyamf.register_class(Message, 'org.pyamf.examples.guestbook.Message')


class GuestBookService(object):
    def __init__(self, pool):
        self.conn_pool = pool
        LoopingCall(self._keepAlive).start(3600, False)
        
    def _keepAlive():
        print 'Running Keep Alive...'
        self.conn_pool.runOperation('SELECT 1')

    def getMessages(self):
        """
        Gets all approved messages.
        """
        def cb(rs):
            ret = [ObjectProxy(build_message(row)) for row in rs]

            return ArrayCollection(ret)

        def eb(failure):
            # TODO nick: logging
            return ArrayCollection()

        d = self.conn_pool.runQuery("SELECT name, url, email, created, message FROM " + \
            "message WHERE approved = 1 ORDER BY id DESC").addErrback(eb).addCallback(cb)

        return d

    def getMessageById(self, id):
        def cb(rs):
            return build_message(rs[0])

        return self.conn_pool.runQuery("SELECT name, url, email, created, message FROM " + \
            "message WHERE id = %d" % int(id)).addCallback(cb)

    @expose_request
    def addMessage(self, request, msg):
        """
        Adds a message to the guestbook

        @param request: The underlying HTTP request.
        @type msg: L{Message}
        """
        name = msg._amf_object.name
        url = msg._amf_object.url
        email = msg._amf_object.email
        message = msg._amf_object.message
 
        if not isinstance(name, basestring):
            name = str(name)

        if len(name) > 50:
            raise IOError, "Name exceeds maximum length (50 chars max)"

        if not isinstance(url, basestring):
            url = str(url)

        if len(url) > 255:
            raise IOError, "Website url exceeds maximum length (255 chars max)"

        if len(url) > 0:
            valid_url, reason = is_valid_url(url)

            if not valid_url:
                raise ValueError, "Website url not valid"

        if not isinstance(email, basestring):
            email = str(email)

        if not is_valid_email(email):
            raise ValueError, "Email address is not valid"

        if not isinstance(message, basestring):
            message = str(message)

        if len(message) == 0:
            raise ValueError, "Message is required"

        message = strip_message(message)
        response_deferred = defer.Deferred()

        def cb(rs):
            # rs contains the last inserted id of the message
            def cb2(msg):
                response_deferred.callback(msg)

            self.getMessageById(rs[0][0]).addCallback(cb2).addErrback(eb)

        def eb(failure):
            response_deferred.errback(failure)

        d = self.conn_pool.runQuery("INSERT INTO message (name, url, email, created, ip_address, message, approved)" + \
            " VALUES ('%s', '%s', '%s', NOW(), '%s', '%s', 1);" % (
                sql_safe(name),
                sql_safe(url),
                sql_safe(email),
                sql_safe(request.getClientIP()),
                sql_safe(message)
            )).addCallback(lambda x: self.conn_pool.runQuery("SELECT id FROM message ORDER BY id DESC LIMIT 0, 1"))

        d.addCallback(cb).addErrback(eb)

        return response_deferred

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Guestbook example server.

@since: 0.3
"""   


import os.path
import logging
import ConfigParser

from twisted.internet import reactor
from twisted.web import server as _server, static, resource
from twisted.enterprise import adbapi

from pyamf.remoting.gateway.twisted import TwistedGateway

from guestbook import GuestBookService


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

port = 8080

cfg = ConfigParser.SafeConfigParser()
cfg.read('settings.cfg')

root = resource.Resource()
gw = TwistedGateway({'guestbook': GuestBookService(adbapi.ConnectionPool('MySQLdb',
                    host=cfg.get('db','host'), user=cfg.get('db','user'),
                    passwd=cfg.get('db','password'), db=cfg.get('db','database'),
                    cp_reconnect=True))}, expose_request=False, debug=True,
                    logger=logging)

root.putChild('gateway', gw)
root.putChild('crossdomain.xml', static.File(os.path.join(os.getcwd(),
    os.path.dirname(__file__), 'crossdomain.xml'), defaultType='application/xml'))

server = _server.Site(root)

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/python
#
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
This is an example of using the Ohloh API from a Python client.

Detailed information can be found at the Ohloh website:

     http://www.ohloh.net/api

This example uses the ElementTree library for XML parsing
(included in Python 2.5 and newer):

     http://effbot.org/zone/element-index.htm

This example retrieves basic Ohloh account information
and outputs it as simple name: value pairs.

Pass your Ohloh API key as the first parameter to this script.
Ohloh API keys are free. If you do not have one, you can obtain
one at the Ohloh website:

     http://www.ohloh.net/api_keys/new

Pass the email address of the account as the second parameter
to this script.
"""


import sys
import ohloh


if len(sys.argv) == 3:
    api_key = sys.argv[1]
    email = sys.argv[2]
else:
    print "Usage: client.py <api-key> <email-address>"
    sys.exit()
    
elem = ohloh.getAccount(email, api_key)

# Output all the immediate child properties of an Account
for node in elem.find("result/account"):
    if node.tag == "kudo_score":
        print "%s:" % node.tag
        for score in elem.find("result/account/kudo_score"):
            print "\t%s:\t%s" % (score.tag, score.text)
    else:
        print "%s:\t%s" % (node.tag, node.text)

########NEW FILE########
__FILENAME__ = ohloh
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Ohloh API example to retrieve account info.

@since: 0.3.1
"""

import urllib, hashlib

try:
    import xml.etree.ElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
        ET._ElementInterface = ET.ElementTree
    except ImportError:
       import elementtree.ElementTree as ET


class UserAccount(object):
    def __init__(self, api_key):
        self.api_key = api_key

    def getAccount(self, email):
        # We pass the MD5 hash of the email address
        emailhash = hashlib.md5()
        emailhash.update(email)

        # Connect to the Ohloh website and retrieve the account data.
        params = urllib.urlencode({'api_key': self.api_key, 'v': 1})
        url = "http://www.ohloh.net/accounts/%s.xml?%s" % (emailhash.hexdigest(), params)
        f = urllib.urlopen(url)
        
        # Parse the response into a structured XML object
        tree = ET.parse(f)
        
        # Did Ohloh return an error?
        elem = tree.getroot()
        error = elem.find("error")
        if error != None:
            raise Exception(ET.tostring(error))
        
        # Return raw XML data
        return elem

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Ohloh API example server for Flash.

@since: 0.3.1
"""

import logging
from optparse import OptionParser
from wsgiref import simple_server

from pyamf.remoting.gateway.wsgi import WSGIGateway

from ohloh import UserAccount


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
parser.add_option("--api-key", default="123456789",
    dest="api_key", help="Ohloh API key [default: %default]")
(options, args) = parser.parse_args()

ohloh = UserAccount(options.api_key)
services = {
    'ohloh.account': ohloh.getAccount
}

host = options.host
port = int(options.port)
gw = WSGIGateway(services, logger=logging)

httpd = simple_server.WSGIServer((host, port),
    simple_server.WSGIRequestHandler,
)

httpd.set_app(gw)

print "Running Ohloh API AMF gateway on http://%s:%d" % (host, port)

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import logging
from optparse import OptionParser

from pyamf.remoting.client import RemotingService


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)
service = client.getService('service')
result = service.getLanguages()

print "Result:", result

########NEW FILE########
__FILENAME__ = db
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Defines the database schema.

@since: 0.1.0
"""

import os, datetime

from sqlalchemy import *


metadata = MetaData()

# Note: use absolute path when using mod_wsgi
dsn = 'sqlite:///temp.db'

if 'RECORDSET_DSN' in os.environ:
    dsn = os.environ['RECORDSET_DSN']

language = Table('languages', metadata,
    Column('ID', String(10), primary_key=True),
    Column('Description', String(255), nullable=True, default=None),
    Column('Name', String(50), nullable=True, default=None),
)

software = Table('SoftwareInfo', metadata,
    Column('ID', Integer, primary_key=True, autoincrement=True),
    Column('Name', Text),
    Column('Active', Boolean, default=True),
    Column('Details', String(255), nullable=True, default=None),
    Column('CategoryID', String(50), nullable=True, default=None),
    Column('Url', String(255), nullable=True, default=None)
)


def get_engine():
    return create_engine(dsn)


def create(engine):
    print "Creating tables..."
    metadata.create_all(bind=engine)

########NEW FILE########
__FILENAME__ = gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Gateway for RecordSet remoting service.

@since: 0.1.0
"""

from sqlalchemy.sql import select

from pyamf import register_class, amf0

import db


def as_recordset(result):
    keys = None

    if hasattr(result, 'keys'):
        keys = result.keys()
    elif hasattr(result, '_ResultProxy__keys'):
        keys = result._ResultProxy__keys

    if keys is None:
        raise AttributeError('Unknown keys for result')

    return amf0.RecordSet(keys, [list(x) for x in result])


class SoftwareService(object):
    def __init__(self, engine):
        self.engine = engine

    def getLanguages(self):
        """
        Returns all the languages.
        """
        return as_recordset(self.engine.execute(
            select([db.language]).order_by(db.language.c.Name.desc())
        ))

    def getSoftware(self, lang):
        """
        Returns all the software projects for the selected language.
        """
        return as_recordset(self.engine.execute(
            select([db.software], db.software.c.CategoryID == lang)
        ))


def parse_args(args):
    """
    Parse commandline options.
    """
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('--host', dest='host', default='localhost',
                      help='The host address for the AMF gateway')
    parser.add_option('-p', '--port', dest='port', default=8000,
                      help='The port number the server uses')

    return parser.parse_args(args)


if __name__ == '__main__':
    import sys, logging
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server

    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')

    options = parse_args(sys.argv[1:])[0]
    service = {'service': SoftwareService(db.get_engine())}

    host = options.host
    port = int(options.port)

    gw = WSGIGateway(service, debug=True, logger=logging)

    httpd = simple_server.WSGIServer(
        (host, port),
        simple_server.WSGIRequestHandler,
    )

    httpd.set_app(gw)

    logging.info('Started RecordSet example server on http://%s:%s' % (host, str(port)))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = init
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Creates the database for the RecordSet example.

@since: 0.1.0
"""

import db

def init_data(engine):
    languages = [
        (".java", "Sun Java programming language", "Java",),
        (".py", "Python programming language", "Python",),
        (".php", "PHP programming language", "PHP",),
    ]
    
    software_info = [
        ("Red5", True, "Red5 is an open source Flash media server with RTMP/AMF/FLV support.", ".java", "http://osflash.org/red5",),
        ("RTMPy", True, "RTMPy is an RTMP protocol for the Twisted framework.", ".py", "http://rtmpy.org",),
        ("SabreAMF", True, "SabreAMF is an AMF library for PHP5.", ".php", "http://osflash.org/sabreamf",),
        ("Django", True, "Django is a high-level Python Web framework.", ".py", "http://djangoproject.com",),
        ("Zend", True, "Zend is an open source PHP framework.", ".php", "http://framework.zend.com",),
    ]

    for language in languages:
        ins = db.language.insert(values=dict(ID=language[0],
            Description=language[1], Name=language[2]))

        engine.execute(ins)

    for software in software_info:
        name, active, details, cat_id, url = software
 
        ins = db.software.insert(values={
            'Name': name, 'Active': active, 'Details': details,
            'CategoryID': cat_id, 'Url': url})

        engine.execute(ins)

def main():
    engine = db.get_engine()

    print "Creating database..."
    db.create(engine)

    init_data(engine)
    print "Successfully set up."

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


"""
AMF client for Local Shared Object example.
"""


import logging
from optparse import OptionParser

from pyamf.remoting.client import RemotingService

from service import SharedObject


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)
service = client.getService('lso')

result = service.getApps()

path = result[0]
apps = result[1]

t = 0
for app in apps:
    t += 1
    print
    print '%d. %s - %s (%s files)' % (t, app.domain, app.name,
                                len(app.files))
    for sol in app.files:
        print ' - %s  (%s bytes) - $PATH%s' % (sol.filename, sol.size,
                                              sol.path[len(path):])
        
print
print 'Path:', path
print 'Total apps:', len(apps)

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


"""
Local Shared Object example.

@see: U{http://pyamf.org/wiki/LocalSharedObjectHowto}
"""


import os
import logging

from pyamf.remoting.gateway.wsgi import WSGIGateway

import service


# get platform specific shared object folder
path = service.default_folder()
filetype = "*.sol"

services = {
    'lso': service.SharedObjectService(path, filetype)
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

application = WSGIGateway(services, logger=logging)


if __name__ == '__main__':
    from optparse import OptionParser
    from wsgiref import simple_server

    
    parser = OptionParser()
    parser.add_option("-p", "--port", default=8000,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default="localhost",
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    port = int(options.port)

    httpd = simple_server.WSGIServer(
        (options.host, port),
        simple_server.WSGIRequestHandler,
    )
    
    
    def app(environ, start_response):
        if environ['PATH_INFO'] == '/crossdomain.xml':
            fn = os.path.join(os.getcwd(), os.path.dirname(__file__),
                'crossdomain.xml')

            fp = open(fn, 'rt')
            buffer = fp.readlines()
            fp.close()

            start_response('200 OK', [
                ('Content-Type', 'application/xml'),
                ('Content-Length', str(len(''.join(buffer))))
            ])

            return buffer

        return application(environ, start_response)

    httpd.set_app(app)

    print "Running AMF gateway on http://%s:%d" % (options.host, port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


########NEW FILE########
__FILENAME__ = service
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

import sys, os.path, operator
import logging

import pyamf
from pyamf import sol


def default_folder():
    """
    Return default platform specific Shared Objects folder.

    @rtype: str
    """
    if sys.platform.startswith('linux'):
        folder = "~/.macromedia/Flash_Player/#SharedObjects"
    elif sys.platform.startswith('win'):
        folder = '~\\AppData\\Roaming\Macromedia\\Flash Player\\#SharedObjects'
    elif sys.platform.startswith('darwin'):
        folder = "~/Library/Preferences/Macromedia/Flash Player/#SharedObjects"
    else:
        import warnings

        warnings.warn("Could not find a platform specific folder " \
            "function for '%s'" % sys.platform, RuntimeWarning)

    return os.path.expanduser(folder)
    
class SharedObjectService:
    """
    AMF service for Local Shared Object example.
    """
    
    def __init__(self, path, pattern):
        self.logger = logging
        self.path = path
        self.pattern = pattern
        
    def getApps(self):
        """
        Get list of applications, containing one or more .sol files,
        sorted by domain.
        """
        extList = []
        apps = []
        
        # convert pattern string to file extensions
        for ext in self.pattern.split(';'):
            extList.append(ext.lstrip('*'))

        self.logger.debug('Path: %s' % self.path)
        self.logger.debug('File extension(s): %s' % extList)
        
        # walk the tree to get apps
        for directory in os.walk(self.path):
            files = self._soDirectory(directory, extList)
            
            if len(files) > 0:
                dup = False
                for app in apps:
                    if files[0].domain == app.domain:
                        dup = True
                        break
                    
                if dup == False:
                    newapp = App()
                    newapp.path = directory[0]
                    newapp.name = os.path.basename(newapp.path)
                    newapp.files = files
                    newapp.domain = files[0].domain
                    apps.append(newapp)               
                else:
                    app.files.extend(files)
                    
        # sort apps by domain
        apps.sort(key=operator.attrgetter('domain'))

        self.logger.debug('Total apps: %d' % len(apps))
        
        return (self.path, apps)

    def getDetails(self, path):
        """
        Read and return Shared Object.
        """
        lso = sol.load(path)
        
        return lso
    
    def _soFiles(self, dirList, typeList):
        """
        Return files that match to file extension(s).
        """
        files = []
        
        for lso in dirList[2]:
            file_info = os.path.splitext(lso)
            
            for ext in typeList:
                if file_info[1] == ext:
                    so = SharedObject()
                    so.name = file_info[0]
                    so.filename = lso
                    so.path = os.path.abspath(os.path.join(dirList[0], lso))
                    so.app = os.path.basename(dirList[0])
                    so.size = os.path.getsize(so.path)
                    so.domain = so.path[len(self.path)+1:].rsplit(os.sep)[1]
                    files.append(so)
                    
                    self.logger.debug(' -- '.rjust(5) + repr(so))
                    break
                
        return files
    
    def _soDirectory(self, dirEntry, typeList):
        """
        Return each sub-directory.
        """        
        return self._soFiles(dirEntry, typeList)

class App(object):
    def __init__(self):
        self.name = ''
        self.path = ''
        self.domain = ''
        self.files = []
        
    def __repr__(self):
        return '<%s name=%s files=%s path=%s>' % (App.__name__, self.name, len(self.files), self.path)

pyamf.register_class(App, 'org.pyamf.examples.sharedobject.vo.App')

class SharedObject(object):
    def __init__(self):
        self.name = ''
        self.app = ''
        self.path = ''
        self.domain = ''
        self.size = 0
        
    def __repr__(self):
        return '<%s app=%s size=%s filename=%s>' % (SharedObject.__name__, self.app, self.size, self.filename)

pyamf.register_class(SharedObject, 'org.pyamf.examples.sharedobject.vo.SharedObject')

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
Client for shell example.

@since: 0.5
"""


import sys
from optparse import OptionParser

from pyamf.remoting.client import RemotingService


parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d/gateway/shell/' % (options.host, int(options.port))
server = RemotingService(url)
print 'Connecting to %s\n' % url
    
# call service to fetch intro text
intro = server.getService('shell.startup')
print intro()

# call service to evalute script and return result
evaluate = server.getService('shell.evalCode')

# start the shell
while 1:
    input = raw_input('>>> ')
    print evaluate(input)
########NEW FILE########
__FILENAME__ = gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Shell example.

@since: 0.3
"""

import sys, logging, types, new
import traceback, pickle
import StringIO

import pyamf
from pyamf.remoting.gateway.django import DjangoGateway


# Types that can't be pickled.
UNPICKLABLE_TYPES = (
  types.ModuleType,
  types.TypeType,
  types.ClassType,
  types.FunctionType,
)

# Unpicklable statements to seed new sessions with.
INITIAL_UNPICKLABLES = [
  'import logging',
  'import os',
  'import sys'
  ]


class ShellSession(object):
  global_names = []
  globals = []
  unpicklable_names = []
  unpicklables = []

  def set_global(self, name, value):
    """Adds a global, or updates it if it already exists.

    Also removes the global from the list of unpicklable names.

    Args:
      name: the name of the global to remove
      value: any picklable value
    """
    blob = pickle.dumps(value)

    if name in self.global_names:
      index = self.global_names.index(name)
      self.globals[index] = blob
    else:
      self.global_names.append(name)
      self.globals.append(blob)

    self.remove_unpicklable_name(name)

  def remove_global(self, name):
    """Removes a global, if it exists.

    Args:
      name: string, the name of the global to remove
    """
    if name in self.global_names:
      index = self.global_names.index(name)
      del self.global_names[index]
      del self.globals[index]

  def globals_dict(self):
    """Returns a dictionary view of the globals.
    """
    return dict((name, pickle.loads(val))
                for name, val in zip(self.global_names, self.globals))

  def add_unpicklable(self, statement, names):
    """Adds a statement and list of names to the unpicklables.

    Also removes the names from the globals.

    Args:
      statement: string, the statement that created new unpicklable global(s).
      names: list of strings; the names of the globals created by the statement.
    """
    self.unpicklables.append(statement)

    for name in names:
      self.remove_global(name)
      if name not in self.unpicklable_names:
        self.unpicklable_names.append(name)

  def remove_unpicklable_name(self, name):
    """Removes a name from the list of unpicklable names, if it exists.

    Args:
      name: string, the name of the unpicklable global to remove
    """
    if name in self.unpicklable_names:
      self.unpicklable_names.remove(name)

class ShellService:
  def _evalCode(self, statement, session):
    if not statement:
      return

    # add a couple newlines at the end of the statement. this makes
    # single-line expressions such as 'class Foo: pass' evaluate happily.
    statement += '\n\n'

    # log and compile the statement up front
    logging.info('Compiling and evaluating:\n%r' % statement)
    compiled = compile(statement, '<string>', 'single')

    # create a dedicated module to be used as this statement's __main__
    statement_module = new.module('__main__')

    # use this request's __builtin__, since it changes on each request.
    # this is needed for import statements, among other things.
    import __builtin__
    statement_module.__builtins__ = __builtin__

    # swap in our custom module for __main__. then unpickle the session
    # globals, run the statement, and re-pickle the session globals, all
    # inside it.
    old_main = sys.modules.get('__main__')
    try:
      sys.modules['__main__'] = statement_module
      statement_module.__name__ = '__main__'

      # re-evaluate the unpicklables
      for code in session.unpicklables:
        exec code in statement_module.__dict__

      # re-initialize the globals
      for name, val in session.globals_dict().items():
        try:
          statement_module.__dict__[name] = val
        except:
          msg = 'Dropping %s since it could not be unpickled.\n' % name
          logging.warning(msg + traceback.format_exc())
          session.remove_global(name)
          buffer.write(msg)

      # run!
      old_globals = dict(statement_module.__dict__)
      exec compiled in statement_module.__dict__

      # extract the new globals that this statement added
      new_globals = {}
      for name, val in statement_module.__dict__.items():
        if name not in old_globals or val != old_globals[name]:
          new_globals[name] = val

      if True in [isinstance(val, UNPICKLABLE_TYPES)
                  for val in new_globals.values()]:
        # this statement added an unpicklable global. store the statement and
        # the names of all of the globals it added in the unpicklables.
        session.add_unpicklable(statement, new_globals.keys())
        logging.debug('Storing this statement as an unpicklable.')

      else:
        # this statement didn't add any unpicklables. pickle and store the
        # new globals back into the datastore.
        for name, val in new_globals.items():
          if not name.startswith('__'):
            session.set_global(name, val)

    finally:
      sys.modules['__main__'] = old_main

  def evalCode(self, request, statement):
    statement = statement.strip().replace('\r\n', '\n').replace('\r', '\n')
    buffer = StringIO.StringIO()

    try:
        session = request.session['shell_session']
    except KeyError:
        session = request.session['shell_session'] = ShellSession()

    try:
      old_stdout = sys.stdout
      old_stderr = sys.stderr
      try:
        sys.stdout = buffer
        sys.stderr = buffer

        self._evalCode(statement, session)
      finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    except:
      buffer.write(traceback.format_exc())

    return buffer.getvalue()

  def startup(self, request):
    pyamf_version = '.'.join([str(x) for x in pyamf.__version__])

    header = 'Welcome to the PyAMF %s Shell Demo!\n' \
           'Python %s on %s\n' \
           'Type "help", "copyright", "credits" or "license" for more information.\n' % \
           (pyamf_version, sys.version, sys.platform)

    return header


services = {
    'shell': ShellService()
}

gateway = DjangoGateway(services, debug=True, logger=logging)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for shell project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'    # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'shell-example.db'     # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Amsterdam'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$_*a5$9eh4&50jpw@@(zl==(s==^&cpc!g79xzbmed8q#q&-46'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'python.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^python/', include('python.foo.urls')),

    # Uncomment this for admin:
    # (r'^admin/', include('django.contrib.admin.urls')),
    
    (r'^gateway/shell/', 'python.gateway.gateway'),
)

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


"""
Simple PyAMF client.

@see: U{Simple Example<http://pyamf.org/tutorials/actionscript/simple.html>} documentation.
@since: 0.5
"""


import logging
from server import AMF_NAMESPACE, host_info

import pyamf
from pyamf.remoting.client import RemotingService


logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')


class UserDataTransferObject(object):
    """
    Models information associated with a simple user object.
    """
    # a default paren-paren constructor is needed for classes
    # that will be passed via AMF
    def __init__(self, username=None, password=None, email=None):
        """
        Create an instance of a user object.
        """
        self.username = username
        self.password = password
        self.email = email


def main():
    """
    Entry point for this client script.
    """
    url = 'http://%s:%d' % (host_info[0], host_info[1])
    client = RemotingService(url, logger=logging)
    print "Client running - pointing to server at %s" % url

    # at this point, calling the service gets us a dict of values
    user_service = client.getService('user')
    lenards = user_service.get_user('lenards')

    # in case you don't believe me - this shows I'm not lying
    logging.debug("isinstance(lenards, dict): %s" % isinstance(lenards, dict))

    # the User class attributes are not present at this point
    logging.debug("not hasattr(lenards, 'username'): %s" %
                  (not hasattr(lenards, 'username')))
    logging.debug("not hasattr(lenards, 'email'): %s" %
                  (not hasattr(lenards, 'email')))
    logging.debug("not hasattr(lenards, 'password'): %s" %
                  (not hasattr(lenards, 'password')))

    # but the values are there
    logging.debug("lenards['username'] == 'lenards': %s" %
                  (lenards['username'] == 'lenards'))
    logging.debug("lenards['email'] == 'lenards@ndy.net': %s" %
                  (lenards['email'] == 'lenards@ndy.net'))

    logging.debug("Output 'lenards': %s" % lenards)

    # if we register the class and the namespace, we get an object ref
    # (complete with attributes and such)
    logging.debug("Register UserDataTransferObject class...")
    pyamf.register_class(UserDataTransferObject, '%s.User' % AMF_NAMESPACE)

    logging.debug("Get a user from the server...")
    usr = user_service.get_user('lisa')

    # ensure it's the class we expect
    logging.debug("Ensure the class we got is our DTO, " +
                  "isinstance(usr, UserDataTransferObject): %s" %
                  isinstance(usr, UserDataTransferObject))

    # verify it has expected attributes
    logging.debug("Verify attributes present...")
    logging.debug("usr.username: %s" % usr.username)
    logging.debug("usr.email == 'lisa@pwns.net': %s" %
                  (usr.email == 'lisa@pwns.net'))
    logging.debug("usr.password == 'h1k3r': %s" %
                  (usr.password == 'h1k3r'))

    logging.debug("Output user returned: %s" % usr)

    # request an unknown user
    logging.debug("Try to get a user that does not exist...")
    george = user_service.get_user('george')

    logging.debug("Output returned: %s" % george)


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--host", default=host_info[0],
        dest="host", help="host address [default: %default]")
    parser.add_option("-p", "--port", default=host_info[1],
        dest="port", help="port number [default: %default]")
    (options, args) = parser.parse_args()

    host_info[0] = options.host
    host_info[1] = int(options.port)

    # now we rock the code
    main()

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Simple PyAMF server.

@see: U{Simple Example<http://pyamf.org/tutorials/actionscript/simple.html>} documentation.
@since: 0.5
"""

import logging
from wsgiref import simple_server

import pyamf
from pyamf import amf3
from pyamf.remoting.gateway.wsgi import WSGIGateway


#: namespace used in the Adobe Flash Player client's [RemoteClass] mapping
AMF_NAMESPACE = 'org.pyamf.examples.simple'

#: Host and port to run the server on
host_info = ('localhost', 8000)

logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')


def create_user(username, password, email):
    """
    Create a user object setting attributes to values passed as
    arguments.
    """
    user = User(username, password, email)
    return user


class User(object):
    """
    Models information associated with a simple user object.
    """
    # we need a default constructor (e.g. a paren-paren constructor)
    def __init__(self, username=None, password=None, email=None):
        """
        Create an instance of a user object.
        """
        self.username = username
        self.password = password
        self.email = email


class UserService(object):
    """
    Provide user related services.
    """
    def __init__(self, users):
        """
        Create an instance of the user service.
        """
        self.users = users

    def get_user(self, username):
        """
        Fetch a user object by C{username}.
        """
        try:
            return self.users[username]
        except KeyError:
            return "Username '%s' not found" % username


class EchoService(object):
    """
    Provide a simple server for testing.
    """
    def echo(self, data):
        """
        Return data with chevrons surrounding it.
        """
        return '<<%s>>' % data


def register_classes():
    """
    Register domain objects with PyAMF.
    """
    # set this so returned objects and arrays are bindable
    amf3.use_proxies_default = True

    # register domain objects that will be used with PyAMF
    pyamf.register_class(User, '%s.User' % AMF_NAMESPACE)


def main():
    """
    Create a WSGIGateway application and serve it.
    """
    # register class on the AMF namespace so that it is passed marshaled
    register_classes()

    # use a dict in leiu of sqlite or an actual database to store users
    # re passwords: plain-text in a production would be bad
    users = {
        'lenards': User('lenards', 'f00f00', 'lenards@ndy.net'),
        'lisa': User('lisa', 'h1k3r', 'lisa@pwns.net'),
    }

    # our gateway will have two services
    services = {
        'echo': EchoService,
        'user': UserService(users)
    }

    # setup our server
    application = WSGIGateway(services, logger=logging)
    httpd = simple_server.WSGIServer(host_info,
                simple_server.WSGIRequestHandler)
    httpd.set_app(application)
    
    try:
        # open for business
        print "Running Simple PyAMF gateway on http://%s:%d" % (
            host_info[0], host_info[1])
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", default=host_info[1],
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default=host_info[0],
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    host_info = (options.host, options.port)

    # now we rock the code
    main()

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
Python client for socket example.

@since: 0.5
"""


import socket
import pyamf

from server import appPort, host


class AmfSocketClient(object):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, host, port):
        print "Connecting to socket server on %s:%d" % (host, port)
        try:
            self.sock.connect((host, port))
            print "Connected to server.\n"
        except socket.error, e:
            raise Exception("Can't connect: %s" % e[1])

    def start(self):
        msg = ''

        # tell server we started listening
        print "send request: start"
        try:
            self.sock.send('start')
        except socket.error, e:
            raise Exception("Can't connect: %s" % e[1])

        while len(msg) < 1024:
            # read from server
            amf = self.sock.recv(1024)

            if amf == '':
                print "Connection closed."

            msg = msg + amf

            for obj in pyamf.decode(amf):
                print obj

        return msg

    def stop(self):
        print "send request: stop"
        self.sock.send('stop')


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", default=appPort,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default=host,
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    host = options.host
    port = int(options.port)

    client = AmfSocketClient()
    client.connect(host, port)

    try:
        client.start()
    except KeyboardInterrupt:
        client.stop()   

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Example socket server using Twisted.

@see: U{Documentation for this example<http://pyamf.org/tutorials/actionscript/socket.html>}

@since: 0.1
"""


try:
    import twisted
except ImportError:
    print "This examples requires the Twisted framework. Download it from http://twistedmatrix.com"
    raise SystemExit

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from datetime import datetime
import pyamf


class TimerProtocol(Protocol):
    interval = 1.0 # interval in seconds to send the time
    encoding = pyamf.AMF3
    timeout = 300 

    def __init__(self):
        self.started = False
        self.encoder = pyamf.get_encoder(self.encoding)
        self.stream = self.encoder.stream

    def connectionLost(self, reason):
        Protocol.connectionLost(self, reason)

        self.factory.number_of_connections -= 1

    def connectionMade(self):
        if self.factory.number_of_connections >= self.factory.max_connections:
            self.transport.write('Too many connections, try again later')
            self.transport.loseConnection()

            return

        self.factory.number_of_connections += 1
        self.timeout_deferred = reactor.callLater(TimerProtocol.timeout, self.transport.loseConnection)

    def dataReceived(self, data):
        data = data.strip()
        if data == 'start':
            # start sending a date object that contains the current time
            if not self.started:
                self.start()
        elif data == 'stop':
            self.stop()

        if self.timeout_deferred:
            self.timeout_deferred.cancel()
            self.timeout_deferred = reactor.callLater(TimerProtocol.timeout, self.transport.loseConnection)

    def start(self):
        self.started = True
        self.sendTime()

    def stop(self):
        self.started = False

    def sendTime(self):
        if self.started:
            self.encoder.writeElement(datetime.now())
            self.transport.write(self.stream.getvalue())
            self.stream.truncate()

            reactor.callLater(self.interval, self.sendTime)


class TimerFactory(Factory):
    protocol = TimerProtocol
    max_connections = 1000

    def __init__(self):
        self.number_of_connections = 0


class SocketPolicyProtocol(Protocol):
    """
    Serves strict policy file for Flash Player >= 9,0,124.
    
    @see: U{http://adobe.com/go/strict_policy_files}
    """
    def connectionMade(self):
        self.buffer = ''

    def dataReceived(self, data):
        self.buffer += data

        if self.buffer.startswith('<policy-file-request/>'):
            self.transport.write(self.factory.getPolicyFile(self))
            self.transport.loseConnection()


class SocketPolicyFactory(Factory):
    protocol = SocketPolicyProtocol

    def __init__(self, policy_file):
        """
        @param policy_file: Path to the policy file definition
        """
        self.policy_file = policy_file

    def getPolicyFile(self, protocol):
        return open(self.policy_file, 'rt').read()


host = 'localhost'
appPort = 8000
policyPort = 843
policyFile = 'socket-policy.xml'


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--host", default=host,
        dest="host", help="host address [default: %default]")
    parser.add_option("-a", "--app-port", default=appPort,
        dest="app_port", help="Application port number [default: %default]")
    parser.add_option("-p", "--policy-port", default=policyPort,
        dest="policy_port", help="Socket policy port number [default: %default]")
    parser.add_option("-f", "--policy-file", default=policyFile,
        dest="policy_file", help="Location of socket policy file [default: %default]")
    (opt, args) = parser.parse_args()

    print "Running Socket AMF gateway on %s:%s" % (opt.host, opt.app_port)
    print "Running Policy file server on %s:%s" % (opt.host, opt.policy_port)
    
    reactor.listenTCP(int(opt.app_port), TimerFactory(), interface=opt.host)
    reactor.listenTCP(int(opt.policy_port), SocketPolicyFactory(opt.policy_file),
                      interface=opt.host)
    reactor.run()

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Test Twisted server for Adobe AIR 2.0's UDP support.

Based on examples from http://twistedmatrix.com/documents/current/core/howto/udp.html
"""

from pyamf import register_class
from pyamf.amf3 import ByteArray

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor


class HelloWorld(object):

    def __repr__(self):
        return "<%s msg='%s' time=%s />" % (self.__class__.__name__, self.msg,
                                          self.time)


class EchoUDPServer(DatagramProtocol):

    def datagramReceived(self, data, (host, port)):
        ba = ByteArray(data)
        result = ba.readObject()
        print " received %s from %s:%d" % (result, host, port)

        self.transport.write(data, (host, port))


if __name__ == "__main__":
    alias = "org.pyamf.examples.air.udp.vo.HelloWorld"
    register_class(HelloWorld, alias)
    print "Registered alias '%s' for class '%s'" % (alias, HelloWorld.__name__)

    port = 55555
    print 'Server started listening on port', port

    server = EchoUDPServer()
    reactor.listenUDP(port, server)
    reactor.run()

########NEW FILE########
__FILENAME__ = client
import logging
	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

from pyamf.remoting.client import RemotingService

url = 'http://192.168.1.108/flashservices/gateway'
gw = RemotingService(url, logger=logging)
service = gw.getService('echo')

print service('Hello World!')

########NEW FILE########
__FILENAME__ = mod_python
from pyamf.remoting.gateway.wsgi import WSGIGateway

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


def echo(data):
   return data

services = {
   'echo': echo,
   # Add other exposed functions here
}

application = WSGIGateway(services, logger=logging, debug=True)

########NEW FILE########
__FILENAME__ = mod_wsgi
from pyamf.remoting.gateway.wsgi import WSGIGateway

def echo(data):
   return data

services = {
   'echo': echo,
   # Add other exposed functions here
}

gateway = WSGIGateway(services)

########NEW FILE########
__FILENAME__ = client
import logging

from pyamf.remoting.client import RemotingService

	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


path = 'http://localhost:8080/'
gw = RemotingService(path, logger=logging, debug=True)
service = gw.getService('myservice')

print service.echo('Hello World!')

########NEW FILE########
__FILENAME__ = gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Remoting gateway for Google App Engine.

@since: 0.3.0
"""

from pyamf.remoting.gateway.wsgi import WSGIGateway
from google.appengine.ext.webapp import util

from echo import echo

services = {
    'echo': echo,
    'echo.echo': echo
}

def main():
    gateway = WSGIGateway(services)

    util.run_wsgi_app(gateway)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = index
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Index page for GAE echo example.

@since: 0.3.0
"""

from google.appengine.ext.webapp import template

print "Content-Type: text/html"
print
print template.render('../templates/swf.html', {
    'swf_url': '/static/echo_test.swf',
    'width': '900px',
    'height': '700px',
    'flash_ver': '9.0.0'
})

########NEW FILE########
__FILENAME__ = index
# Google App Engine imports.
import logging, os.path, sys
from google.appengine.ext.webapp import util

# Force Django to reload its settings.
from django.conf import settings
settings._target = None

# Must set this env var before importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def log_exception(*args, **kwds):
    logging.exception('Exception in request:')

# Log errors.
django.dispatch.dispatcher.connect(
    log_exception, django.core.signals.got_request_exception)

# Unregister the rollback event handler.
django.dispatch.dispatcher.disconnect(
    django.db._rollback_on_exception,
    django.core.signals.got_request_exception)

def main():
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()

    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for google_appengine project.

import os, sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hv3c-_#z*tibii%0u@7^@be7c=-#!8$+td%$blvuzscgs4^ey%'

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    PROJECT_ROOT + '/templates'
)

TEMPLATE_CONTEXT_PROCESSORS = ('django.core.context_processors.debug', 'django.core.context_processors.i18n')

INSTALLED_APPS = (
#    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.sites',
)
########NEW FILE########
__FILENAME__ = gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Interactive Python shell for Flex example.

@since: 0.3
"""

import sys, logging, types, new
import traceback, pickle
import StringIO

from google.appengine.ext import webapp
from google.appengine.ext import db
import wsgiref.handlers

from pyamf.remoting.gateway.django import DjangoGateway
from pyamf.remoting.gateway import expose_request

# Types that can't be pickled.
UNPICKLABLE_TYPES = (
  types.ModuleType,
  types.TypeType,
  types.ClassType,
  types.FunctionType,
)

# Unpicklable statements to seed new sessions with.
INITIAL_UNPICKLABLES = [
  'import logging',
  'import os',
  'import sys',
  'from google.appengine.ext import db',
  'from google.appengine.api import users',
  ]

class Session(db.Model):
  """A shell session. Stores the session's globals.

  Each session globals is stored in one of two places:

  If the global is picklable, it's stored in the parallel globals and
  global_names list properties. (They're parallel lists to work around the
  unfortunate fact that the datastore can't store dictionaries natively.)

  If the global is not picklable (e.g. modules, classes, and functions), or if
  it was created by the same statement that created an unpicklable global,
  it's not stored directly. Instead, the statement is stored in the
  unpicklables list property. On each request, before executing the current
  statement, the unpicklable statements are evaluated to recreate the
  unpicklable globals.

  The unpicklable_names property stores all of the names of globals that were
  added by unpicklable statements. When we pickle and store the globals after
  executing a statement, we skip the ones in unpicklable_names.

  Using Text instead of string is an optimization. We don't query on any of
  these properties, so they don't need to be indexed.
  """
  global_names = db.ListProperty(db.Text)
  globals = db.ListProperty(db.Blob)
  unpicklable_names = db.ListProperty(db.Text)
  unpicklables = db.ListProperty(db.Text)

  def set_global(self, name, value):
    """Adds a global, or updates it if it already exists.

    Also removes the global from the list of unpicklable names.

    Args:
      name: the name of the global to remove
      value: any picklable value
    """
    blob = db.Blob(pickle.dumps(value))

    if name in self.global_names:
      index = self.global_names.index(name)
      self.globals[index] = blob
    else:
      self.global_names.append(db.Text(name))
      self.globals.append(blob)

    self.remove_unpicklable_name(name)

  def remove_global(self, name):
    """Removes a global, if it exists.

    Args:
      name: string, the name of the global to remove
    """
    if name in self.global_names:
      index = self.global_names.index(name)
      del self.global_names[index]
      del self.globals[index]

  def globals_dict(self):
    """Returns a dictionary view of the globals.
    """
    return dict((name, pickle.loads(val))
                for name, val in zip(self.global_names, self.globals))

  def add_unpicklable(self, statement, names):
    """Adds a statement and list of names to the unpicklables.

    Also removes the names from the globals.

    Args:
      statement: string, the statement that created new unpicklable global(s).
      names: list of strings; the names of the globals created by the statement.
    """
    self.unpicklables.append(db.Text(statement))

    for name in names:
      self.remove_global(name)
      if name not in self.unpicklable_names:
        self.unpicklable_names.append(db.Text(name))

  def remove_unpicklable_name(self, name):
    """Removes a name from the list of unpicklable names, if it exists.

    Args:
      name: string, the name of the unpicklable global to remove
    """
    if name in self.unpicklable_names:
      self.unpicklable_names.remove(name)

class ShellService:
  
  def _evalCode(self, statement, session):
    if not statement:
      return

    # add a couple newlines at the end of the statement. this makes
    # single-line expressions such as 'class Foo: pass' evaluate happily.
    statement += '\n\n'

    # log and compile the statement up front
    logging.info('Compiling and evaluating:\n%r' % statement)
    compiled = compile(statement, '<string>', 'single')

    # create a dedicated module to be used as this statement's __main__
    statement_module = new.module('__main__')

    # use this request's __builtin__, since it changes on each request.
    # this is needed for import statements, among other things.
    import __builtin__
    statement_module.__builtins__ = __builtin__

    # swap in our custom module for __main__. then unpickle the session
    # globals, run the statement, and re-pickle the session globals, all
    # inside it.
    old_main = sys.modules.get('__main__')
    try:
      sys.modules['__main__'] = statement_module
      statement_module.__name__ = '__main__'

      # re-evaluate the unpicklables
      for code in session.unpicklables:
        exec code in statement_module.__dict__

      # re-initialize the globals
      for name, val in session.globals_dict().items():
        try:
          statement_module.__dict__[name] = val
        except:
          msg = 'Dropping %s since it could not be unpickled.\n' % name
          logging.warning(msg + traceback.format_exc())
          session.remove_global(name)
          buffer.write(msg)

      # run!
      old_globals = dict(statement_module.__dict__)
      exec compiled in statement_module.__dict__

      # extract the new globals that this statement added
      new_globals = {}
      for name, val in statement_module.__dict__.items():
        if name not in old_globals or val != old_globals[name]:
          new_globals[name] = val

      if True in [isinstance(val, UNPICKLABLE_TYPES)
                  for val in new_globals.values()]:
        # this statement added an unpicklable global. store the statement and
        # the names of all of the globals it added in the unpicklables.
        session.add_unpicklable(statement, new_globals.keys())
        logging.debug('Storing this statement as an unpicklable.')

      else:
        # this statement didn't add any unpicklables. pickle and store the
        # new globals back into the datastore.
        for name, val in new_globals.items():
          if not name.startswith('__'):
            session.set_global(name, val)

    finally:
      sys.modules['__main__'] = old_main

  def evalCode(self, request, statement):
    statement = statement.strip().replace('\r\n', '\n').replace('\r', '\n')
    buffer = StringIO.StringIO()

    buffer.write(statement + '\n')

    session = request.session

    try:
      old_stdout = sys.stdout
      old_stderr = sys.stderr
      try:
        sys.stdout = buffer
        sys.stderr = buffer

        self._evalCode(statement, session)
      finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        session.put()
    except:
      buffer.write(traceback.format_exc())
    
    buffer.write('>>> ')

    return buffer.getvalue()

  def startup(self, request):
    return "Welcome to the PyAMF Python Shell Demo!\n\n>>> "


class SessionExposingAppGateway(DjangoGateway):
    def __call__(self, http_request):
        new = False

        try:
            key = http_request.COOKIES['SESSION_KEY']
            http_request.session = Session.get(key)
        except KeyError:
            new = True
            http_request.session = Session()
            http_request.session.put()

        try:
            http_response = DjangoGateway.__call__(self, http_request)
        finally:
            if new:
                http_response.set_cookie('SESSION_KEY', http_request.session.key())

        return http_response

services = {
    'shell': ShellService
}

gateway = SessionExposingAppGateway(services)
########NEW FILE########
__FILENAME__ = index
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

from google.appengine.ext.webapp import template

print "Content-Type: text/html"
print
print template.render('../templates/swf.html', {
    'swf_url': '/assets/swf/shell.swf',
    'width': '900px',
    'height': '650px',
    'flash_ver': '9.0.0'
})
########NEW FILE########
__FILENAME__ = decoder
"""
Implementation of JSONDecoder
"""
import re
import sys

from simplejson.scanner import Scanner, pattern
try:
    from simplejson import _speedups
except:
    _speedups = None

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    import struct
    import sys
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()

def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno

def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)

_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
    'true': True,
    'false': False,
    'null': None,
}

def JSONConstant(match, context, c=_CONSTANTS):
    s = match.group(0)
    fn = getattr(context, 'parse_constant', None)
    if fn is None:
        rval = c[s]
    else:
        rval = fn(s)
    return rval, None
pattern('(-?Infinity|NaN|true|false|null)')(JSONConstant)

def JSONNumber(match, context):
    match = JSONNumber.regex.match(match.string, *match.span())
    integer, frac, exp = match.groups()
    if frac or exp:
        fn = getattr(context, 'parse_float', None) or float
        res = fn(integer + (frac or '') + (exp or ''))
    else:
        fn = getattr(context, 'parse_int', None) or int
        res = fn(integer)
    return res, None
pattern(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(JSONNumber)

STRINGCHUNK = re.compile(r'(.*?)(["\\])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def scanstring(s, end, encoding=None, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end

# Use speedup
if _speedups is not None:
    scanstring = _speedups.scanstring

def JSONString(match, context):
    encoding = getattr(context, 'encoding', None)
    return scanstring(match.string, match.end(), encoding)
pattern(r'"')(JSONString)

WHITESPACE = re.compile(r'\s*', FLAGS)

def JSONObject(match, context, _w=WHITESPACE.match):
    pairs = {}
    s = match.string
    end = _w(s, match.end()).end()
    nextchar = s[end:end + 1]
    # trivial empty object
    if nextchar == '}':
        return pairs, end + 1
    if nextchar != '"':
        raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    encoding = getattr(context, 'encoding', None)
    iterscan = JSONScanner.iterscan
    while True:
        key, end = scanstring(s, end, encoding)
        end = _w(s, end).end()
        if s[end:end + 1] != ':':
            raise ValueError(errmsg("Expecting : delimiter", s, end))
        end = _w(s, end + 1).end()
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == '}':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))
    object_hook = getattr(context, 'object_hook', None)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end
pattern(r'{')(JSONObject)
            
def JSONArray(match, context, _w=WHITESPACE.match):
    values = []
    s = match.string
    end = _w(s, match.end()).end()
    # look-ahead for trivial empty array
    nextchar = s[end:end + 1]
    if nextchar == ']':
        return values, end + 1
    iterscan = JSONScanner.iterscan
    while True:
        try:
            value, end = iterscan(s, idx=end, context=context).next()
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        values.append(value)
        end = _w(s, end).end()
        nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        if nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))
        end = _w(s, end).end()
    return values, end
pattern(r'\[')(JSONArray)
 
ANYTHING = [
    JSONObject,
    JSONArray,
    JSONString,
    JSONConstant,
    JSONNumber,
]

JSONScanner = Scanner(ANYTHING)

class JSONDecoder(object):
    """
    Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:
    
    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.
    """

    _scanner = Scanner(ANYTHING)
    __all__ = ['__init__', 'decode', 'raw_decode']

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None):
        """
        ``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.
        
        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN, null, true, false.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.
        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.parse_constant = parse_constant

    def decode(self, s, _w=WHITESPACE.match):
        """
        Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)
        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, **kw):
        """
        Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.
        """
        kw.setdefault('context', self)
        try:
            obj, end = self._scanner.iterscan(s, **kw).next()
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

__all__ = ['JSONDecoder']

########NEW FILE########
__FILENAME__ = encoder
"""
Implementation of JSONEncoder
"""
import re
try:
    from simplejson import _speedups
except ImportError:
    _speedups = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"/]|[^\ -~])')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def floatstr(o, allow_nan=True):
    # Check for specials.  Note that this type of test is processor- and/or
    # platform-specific, so do tests which don't depend on the internals.

    if o != o:
        text = 'NaN'
    elif o == INFINITY:
        text = 'Infinity'
    elif o == -INFINITY:
        text = '-Infinity'
    else:
        return FLOAT_REPR(o)

    if not allow_nan:
        raise ValueError("Out of range float values are not JSON compliant: %r"
            % (o,))

    return text


def encode_basestring(s):
    """
    Return a JSON representation of a Python string
    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'

def encode_basestring_ascii(s):
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'
        
try:
    encode_basestring_ascii = _speedups.encode_basestring_ascii
    _need_utf8 = True
except AttributeError:
    _need_utf8 = False

class JSONEncoder(object):
    """
    Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:
    
    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).
    """
    __all__ = ['__init__', 'default', 'encode', 'iterencode']
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """
        Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple. The default is (', ', ': '). To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized. It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding. 
        The default is UTF-8.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.current_indent_level = 0
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def _newline_indent(self):
        return '\n' + (' ' * (self.indent * self.current_indent_level))

    def _iterencode_list(self, lst, markers=None):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        yield '['
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            separator = self.item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                yield separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(self, dct, markers=None):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        key_separator = self.key_separator
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            item_separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = self.item_separator
        first = True
        if self.ensure_ascii:
            encoder = encode_basestring_ascii
        else:
            encoder = encode_basestring
        allow_nan = self.allow_nan
        if self.sort_keys:
            keys = dct.keys()
            keys.sort()
            items = [(k, dct[k]) for k in keys]
        else:
            items = dct.iteritems()
        _encoding = self.encoding
        _do_decode = (_encoding is not None
            and not (_need_utf8 and _encoding == 'utf-8'))
        for key, value in items:
            if isinstance(key, str):
                if _do_decode:
                    key = key.decode(_encoding)
            elif isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = floatstr(key, allow_nan)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif self.skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield encoder(key)
            yield key_separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(self, o, markers=None):
        if isinstance(o, basestring):
            if self.ensure_ascii:
                encoder = encode_basestring_ascii
            else:
                encoder = encode_basestring
            _encoding = self.encoding
            if (_encoding is not None and isinstance(o, str)
                    and not (_need_utf8 and _encoding == 'utf-8')):
                o = o.decode(_encoding)
            yield encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield floatstr(o, self.allow_nan)
        elif isinstance(o, (list, tuple)):
            for chunk in self._iterencode_list(o, markers):
                yield chunk
        elif isinstance(o, dict):
            for chunk in self._iterencode_dict(o, markers):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            for chunk in self._iterencode_default(o, markers):
                yield chunk
            if markers is not None:
                del markers[markerid]

    def _iterencode_default(self, o, markers=None):
        newobj = self.default(o)
        return self._iterencode(newobj, markers)

    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::
            
            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """
        Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo":["bar", "baz"]}'
        """
        # This is for extremely simple cases and benchmarks...
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None 
                        and not (_encoding == 'utf-8' and _need_utf8)):
                    o = o.decode(_encoding)
            return encode_basestring_ascii(o)
        # This doesn't pass the iterator directly to ''.join() because it
        # sucks at reporting exceptions.  It's going to do this internally
        # anyway because it uses PySequence_Fast or similar.
        chunks = list(self.iterencode(o))
        return ''.join(chunks)

    def iterencode(self, o):
        """
        Encode the given object and yield each string
        representation as available.
        
        For example::
            
            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        return self._iterencode(o, markers)

__all__ = ['JSONEncoder']

########NEW FILE########
__FILENAME__ = jsonfilter
import simplejson
import cgi

class JSONFilter(object):
    def __init__(self, app, mime_type='text/x-json'):
        self.app = app
        self.mime_type = mime_type

    def __call__(self, environ, start_response):
        # Read JSON POST input to jsonfilter.json if matching mime type
        response = {'status': '200 OK', 'headers': []}
        def json_start_response(status, headers):
            response['status'] = status
            response['headers'].extend(headers)
        environ['jsonfilter.mime_type'] = self.mime_type
        if environ.get('REQUEST_METHOD', '') == 'POST':
            if environ.get('CONTENT_TYPE', '') == self.mime_type:
                args = [_ for _ in [environ.get('CONTENT_LENGTH')] if _]
                data = environ['wsgi.input'].read(*map(int, args))
                environ['jsonfilter.json'] = simplejson.loads(data)
        res = simplejson.dumps(self.app(environ, json_start_response))
        jsonp = cgi.parse_qs(environ.get('QUERY_STRING', '')).get('jsonp')
        if jsonp:
            content_type = 'text/javascript'
            res = ''.join(jsonp + ['(', res, ')'])
        elif 'Opera' in environ.get('HTTP_USER_AGENT', ''):
            # Opera has bunk XMLHttpRequest support for most mime types
            content_type = 'text/plain'
        else:
            content_type = self.mime_type
        headers = [
            ('Content-type', content_type),
            ('Content-length', len(res)),
        ]
        headers.extend(response['headers'])
        start_response(response['status'], headers)
        return [res]

def factory(app, global_conf, **kw):
    return JSONFilter(app, **kw)

########NEW FILE########
__FILENAME__ = scanner
"""
Iterator based sre token scanner
"""
import sre_parse, sre_compile, sre_constants
from sre_constants import BRANCH, SUBPATTERN
from re import VERBOSE, MULTILINE, DOTALL
import re

__all__ = ['Scanner', 'pattern']

FLAGS = (VERBOSE | MULTILINE | DOTALL)
class Scanner(object):
    def __init__(self, lexicon, flags=FLAGS):
        self.actions = [None]
        # combine phrases into a compound pattern
        s = sre_parse.Pattern()
        s.flags = flags
        p = []
        for idx, token in enumerate(lexicon):
            phrase = token.pattern
            try:
                subpattern = sre_parse.SubPattern(s,
                    [(SUBPATTERN, (idx + 1, sre_parse.parse(phrase, flags)))])
            except sre_constants.error:
                raise
            p.append(subpattern)
            self.actions.append(token)

        s.groups = len(p)+1  # NOTE(guido): Added to make SRE validation work
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)


    def iterscan(self, string, idx=0, context=None):
        """
        Yield match, end_idx for each match
        """
        match = self.scanner.scanner(string, idx).match
        actions = self.actions
        lastend = idx
        end = len(string)
        while True:
            m = match()
            if m is None:
                break
            matchbegin, matchend = m.span()
            if lastend == matchend:
                break
            action = actions[m.lastindex]
            if action is not None:
                rval, next_pos = action(m, context)
                if next_pos is not None and next_pos != matchend:
                    # "fast forward" the scanner
                    matchend = next_pos
                    match = self.scanner.scanner(string, matchend).match
                yield rval, matchend
            lastend = matchend
            
def pattern(pattern, flags=FLAGS):
    def decorator(fn):
        fn.pattern = pattern
        fn.regex = re.compile(pattern, flags)
        return fn
    return decorator

########NEW FILE########
__FILENAME__ = test_decode
import simplejson as S
import decimal
def test_decimal():
    rval = S.loads('1.1', parse_float=decimal.Decimal)
    assert isinstance(rval, decimal.Decimal)
    assert rval == decimal.Decimal('1.1')

def test_float():
    rval = S.loads('1', parse_int=float)
    assert isinstance(rval, float)
    assert rval == 1.0

########NEW FILE########
__FILENAME__ = test_default
import simplejson
def test_default():
    assert simplejson.dumps(type, default=repr) == simplejson.dumps(repr(type))

########NEW FILE########
__FILENAME__ = test_dump
from cStringIO import StringIO
import simplejson as S

def test_dump():
    sio = StringIO()
    S.dump({}, sio)
    assert sio.getvalue() == '{}'
    
def test_dumps():
    assert S.dumps({}) == '{}'

########NEW FILE########
__FILENAME__ = test_fail
# Fri Dec 30 18:57:26 2005
JSONDOCS = [
    # http://json.org/JSON_checker/test/fail1.json
    '"A JSON payload should be an object or array, not a string."',
    # http://json.org/JSON_checker/test/fail2.json
    '["Unclosed array"',
    # http://json.org/JSON_checker/test/fail3.json
    '{unquoted_key: "keys must be quoted}',
    # http://json.org/JSON_checker/test/fail4.json
    '["extra comma",]',
    # http://json.org/JSON_checker/test/fail5.json
    '["double extra comma",,]',
    # http://json.org/JSON_checker/test/fail6.json
    '[   , "<-- missing value"]',
    # http://json.org/JSON_checker/test/fail7.json
    '["Comma after the close"],',
    # http://json.org/JSON_checker/test/fail8.json
    '["Extra close"]]',
    # http://json.org/JSON_checker/test/fail9.json
    '{"Extra comma": true,}',
    # http://json.org/JSON_checker/test/fail10.json
    '{"Extra value after close": true} "misplaced quoted value"',
    # http://json.org/JSON_checker/test/fail11.json
    '{"Illegal expression": 1 + 2}',
    # http://json.org/JSON_checker/test/fail12.json
    '{"Illegal invocation": alert()}',
    # http://json.org/JSON_checker/test/fail13.json
    '{"Numbers cannot have leading zeroes": 013}',
    # http://json.org/JSON_checker/test/fail14.json
    '{"Numbers cannot be hex": 0x14}',
    # http://json.org/JSON_checker/test/fail15.json
    '["Illegal backslash escape: \\x15"]',
    # http://json.org/JSON_checker/test/fail16.json
    '["Illegal backslash escape: \\\'"]',
    # http://json.org/JSON_checker/test/fail17.json
    '["Illegal backslash escape: \\017"]',
    # http://json.org/JSON_checker/test/fail18.json
    '[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]',
    # http://json.org/JSON_checker/test/fail19.json
    '{"Missing colon" null}',
    # http://json.org/JSON_checker/test/fail20.json
    '{"Double colon":: null}',
    # http://json.org/JSON_checker/test/fail21.json
    '{"Comma instead of colon", null}',
    # http://json.org/JSON_checker/test/fail22.json
    '["Colon instead of comma": false]',
    # http://json.org/JSON_checker/test/fail23.json
    '["Bad value", truth]',
    # http://json.org/JSON_checker/test/fail24.json
    "['single quote']",
]

SKIPS = {
    1: "why not have a string payload?",
    18: "spec doesn't specify any nesting limitations",
}

def test_failures():
    import simplejson
    for idx, doc in enumerate(JSONDOCS):
        idx = idx + 1
        if idx in SKIPS:
            simplejson.loads(doc)
            continue
        try:
            simplejson.loads(doc)
        except ValueError:
            pass
        else:
            assert False, "Expected failure for fail%d.json: %r" % (idx, doc)

########NEW FILE########
__FILENAME__ = test_float
import simplejson
import math

def test_floats():
    for num in [1617161771.7650001, math.pi, math.pi**100, math.pi**-100]:
        assert float(simplejson.dumps(num)) == num

########NEW FILE########
__FILENAME__ = test_indent



def test_indent():
    import simplejson
    import textwrap
    
    h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
         {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

    expect = textwrap.dedent("""\
    [
      [
        "blorpie"
      ],
      [
        "whoops"
      ],
      [],
      "d-shtaeou",
      "d-nthiouh",
      "i-vhbjkhnth",
      {
        "nifty": 87
      },
      {
        "field": "yes",
        "morefield": false
      }
    ]""")


    d1 = simplejson.dumps(h)
    d2 = simplejson.dumps(h, indent=2, sort_keys=True, separators=(',', ': '))

    h1 = simplejson.loads(d1)
    h2 = simplejson.loads(d2)

    assert h1 == h
    assert h2 == h
    assert d2 == expect

########NEW FILE########
__FILENAME__ = test_pass1
# from http://json.org/JSON_checker/test/pass1.json
JSON = r'''
[
    "JSON Test Pattern pass1",
    {"object with 1 member":["array with 1 element"]},
    {},
    [],
    -42,
    true,
    false,
    null,
    {
        "integer": 1234567890,
        "real": -9876.543210,
        "e": 0.123456789e-12,
        "E": 1.234567890E+34,
        "":  23456789012E666,
        "zero": 0,
        "one": 1,
        "space": " ",
        "quote": "\"",
        "backslash": "\\",
        "controls": "\b\f\n\r\t",
        "slash": "/ & \/",
        "alpha": "abcdefghijklmnopqrstuvwyz",
        "ALPHA": "ABCDEFGHIJKLMNOPQRSTUVWYZ",
        "digit": "0123456789",
        "special": "`1~!@#$%^&*()_+-={':[,]}|;.</>?",
        "hex": "\u0123\u4567\u89AB\uCDEF\uabcd\uef4A",
        "true": true,
        "false": false,
        "null": null,
        "array":[  ],
        "object":{  },
        "address": "50 St. James Street",
        "url": "http://www.JSON.org/",
        "comment": "// /* <!-- --",
        "# -- --> */": " ",
        " s p a c e d " :[1,2 , 3

,

4 , 5        ,          6           ,7        ],
        "compact": [1,2,3,4,5,6,7],
        "jsontext": "{\"object with 1 member\":[\"array with 1 element\"]}",
        "quotes": "&#34; \u0022 %22 0x22 034 &#x22;",
        "\/\\\"\uCAFE\uBABE\uAB98\uFCDE\ubcda\uef4A\b\f\n\r\t`1~!@#$%^&*()_+-=[]{}|;:',./<>?"
: "A key can be any string"
    },
    0.5 ,98.6
,
99.44
,

1066


,"rosebud"]
'''

def test_parse():
    # test in/out equivalence and parsing
    import simplejson
    res = simplejson.loads(JSON)
    out = simplejson.dumps(res)
    assert res == simplejson.loads(out)
    try:
        simplejson.dumps(res, allow_nan=False)
    except ValueError:
        pass
    else:
        assert False, "23456789012E666 should be out of range"

########NEW FILE########
__FILENAME__ = test_pass2
# from http://json.org/JSON_checker/test/pass2.json
JSON = r'''
[[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]
'''

def test_parse():
    # test in/out equivalence and parsing
    import simplejson
    res = simplejson.loads(JSON)
    out = simplejson.dumps(res)
    assert res == simplejson.loads(out)

########NEW FILE########
__FILENAME__ = test_pass3
# from http://json.org/JSON_checker/test/pass3.json
JSON = r'''
{
    "JSON Test Pattern pass3": {
        "The outermost value": "must be an object or array.",
        "In this test": "It is an object."
    }
}
'''

def test_parse():
    # test in/out equivalence and parsing
    import simplejson
    res = simplejson.loads(JSON)
    out = simplejson.dumps(res)
    assert res == simplejson.loads(out)

########NEW FILE########
__FILENAME__ = test_recursion
import simplejson

def test_listrecursion():
    x = []
    x.append(x)
    try:
        simplejson.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on list recursion"
    x = []
    y = [x]
    x.append(y)
    try:
        simplejson.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on alternating list recursion"
    y = []
    x = [y, y]
    # ensure that the marker is cleared
    simplejson.dumps(x)

def test_dictrecursion():
    x = {}
    x["test"] = x
    try:
        simplejson.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on dict recursion"
    x = {}
    y = {"a": x, "b": x}
    # ensure that the marker is cleared
    simplejson.dumps(x)

class TestObject:
    pass

class RecursiveJSONEncoder(simplejson.JSONEncoder):
    recurse = False
    def default(self, o):
        if o is TestObject:
            if self.recurse:
                return [TestObject]
            else:
                return 'TestObject'
        simplejson.JSONEncoder.default(o)

def test_defaultrecursion():
    enc = RecursiveJSONEncoder()
    assert enc.encode(TestObject) == '"TestObject"'
    enc.recurse = True
    try:
        enc.encode(TestObject)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on default recursion"

########NEW FILE########
__FILENAME__ = test_separators



def test_separators():
    import simplejson
    import textwrap
    
    h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
         {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

    expect = textwrap.dedent("""\
    [
      [
        "blorpie"
      ] ,
      [
        "whoops"
      ] ,
      [] ,
      "d-shtaeou" ,
      "d-nthiouh" ,
      "i-vhbjkhnth" ,
      {
        "nifty" : 87
      } ,
      {
        "field" : "yes" ,
        "morefield" : false
      }
    ]""")


    d1 = simplejson.dumps(h)
    d2 = simplejson.dumps(h, indent=2, sort_keys=True, separators=(' ,', ' : '))

    h1 = simplejson.loads(d1)
    h2 = simplejson.loads(d2)

    assert h1 == h
    assert h2 == h
    assert d2 == expect

########NEW FILE########
__FILENAME__ = test_unicode
import simplejson as S

def test_encoding1():
    encoder = S.JSONEncoder(encoding='utf-8')
    u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
    s = u.encode('utf-8')
    ju = encoder.encode(u)
    js = encoder.encode(s)
    assert ju == js
    
def test_encoding2():
    u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
    s = u.encode('utf-8')
    ju = S.dumps(u, encoding='utf-8')
    js = S.dumps(s, encoding='utf-8')
    assert ju == js

def test_big_unicode_encode():
    u = u'\U0001d120'
    assert S.dumps(u) == '"\\ud834\\udd20"'
    assert S.dumps(u, ensure_ascii=False) == '"\\ud834\\udd20"'

def test_big_unicode_decode():
    u = u'z\U0001d120x'
    assert S.loads('"' + u + '"') == u
    assert S.loads('"z\\ud834\\udd20x"') == u

def test_unicode_decode():
    for i in range(0, 0xd7ff):
        u = unichr(i)
        json = '"\\u%04x"' % (i,)
        res = S.loads(json)
        assert res == u, 'S.loads(%r) != %r got %r' % (json, u, res)

if __name__ == '__main__':
    test_unicode_decode()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('django.views.generic.simple',
    (r'^$', 'direct_to_template', {'template': 'index.html'}),
)

# ByteArray demo urls
urlpatterns += patterns('django.views.generic.simple',
    (r'^bytearray/$', 'direct_to_template', {'template': 'swf.html', 'extra_context': {
        'swf_url': '/assets/swf/bytearray.swf',
        'width': '500px',
        'height': '600px',
        'flash_ver': '9.0.0',
        'title': 'PyAMF ByteArray Demo'
    }}),
)

urlpatterns += patterns('',
    (r'^gateway/bytearray/', 'bytearray.gateway.gateway'),
)

# Shell example

urlpatterns += patterns('django.views.generic.simple',
    (r'^shell/$', 'direct_to_template', {'template': 'swf.html', 'extra_context': {
        'swf_url': '/assets/swf/shell.swf',
        'width': '800px',
        'height': '600px',
        'flash_ver': '9.0.0',
        'title': 'PyAMF Python Shell Demo'
    }}),
)

urlpatterns += patterns('',
    (r'^gateway/shell/', 'shell.gateway.gateway'),
)

# EchoTest example

urlpatterns += patterns('django.views.generic.simple',
    (r'^echo/$', 'direct_to_template', {'template': 'swf.html', 'extra_context': {
        'swf_url': '/assets/swf/echo_test.swf',
        'width': '800px',
        'height': '600px',
        'flash_ver': '9.0.0',
        'title': 'PyAMF Echo Test Demo'
    }}),
)

urlpatterns += patterns('',
    (r'^gateway/echo/', 'echo.gateway.gateway'),
)


########NEW FILE########
__FILENAME__ = webapp
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from pyamf.remoting.gateway.google import WebAppGateway


class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello, webapp World!')


def echo(data):
    return data


def main():
    debug_enabled = True

    services = {
        'myservice.echo': echo,
    }

    gateway = WebAppGateway(services, logger=logging, debug=debug_enabled)

    application_paths = [('/', gateway), ('/helloworld', MainPage)]
    application = webapp.WSGIApplication(application_paths, debug=debug_enabled)

    run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = wsgi
import logging
import wsgiref.handlers

from pyamf.remoting.gateway.wsgi import WSGIGateway


def echo(data):
    return data


def main():
    services = {
        'myservice.echo': echo,
    }

    gateway = WSGIGateway(services, logger=logging, debug=True)
    wsgiref.handlers.CGIHandler().run(gateway)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client
import logging

from pyamf.remoting.client import RemotingService

	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


path = 'http://localhost:8080/gateway/'
gw = RemotingService(path, logger=logging)
service = gw.getService('myservice')

print service.echo('Hello World!')
########NEW FILE########
__FILENAME__ = gateway
import logging

import cherrypy

from pyamf.remoting.gateway.wsgi import WSGIGateway

	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


def echo(data):
   """
   This is a function that we will expose.
   """
   return data


class Root(object):
    """
    This is the root controller for the rest of the website.
    """
    def index(self):
        return "This is your main website"
    index.exposed = True


config = {
    '/crossdomain.xml': {
        'tools.staticfile.on': True,
        'tools.staticfile.filename': '/path/to/crossdomain.xml'
    }
}

services = {
   'myservice.echo': echo,
   # Add other exposed functions here
}

gateway = WSGIGateway(services, logger=logging, debug=True)

# This is where we hook in the WSGIGateway
cherrypy.tree.graft(gateway, "/gateway/")
cherrypy.quickstart(Root(), config=config)

########NEW FILE########
__FILENAME__ = amfgateway
# yourproject/yourapp/amfgateway.py

from pyamf.remoting.gateway.django import DjangoGateway

def echo(request, data):
    return data

services = {
    'myservice.echo': echo
    # could include other functions as well
}

echoGateway = DjangoGateway(services)
########NEW FILE########
__FILENAME__ = client
import logging
	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

from pyamf.remoting.client import RemotingService

url = 'http://127.0.0.1:8000/gateway/'
gw = RemotingService(url, logger=logging)
service = gw.getService('myservice')

print service.echo('Hello World!')

########NEW FILE########
__FILENAME__ = pylons_client
import logging
	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

from pyamf.remoting.client import RemotingService

url = 'http://127.0.0.1:5000/gateway'
client = RemotingService(url, logger=logging)
service = client.getService('myservice')
echo = service.echo('Hello World!')

logging.debug(echo) 

########NEW FILE########
__FILENAME__ = pylons_gateway
import logging

from testproject.lib import helpers as h

log = logging.getLogger(__name__)

def echo(data):
    """
    This is a function that we will expose.
    """
    # print data to the console
    log.debug('Echo: %s', data)
    # echo data back to the client
    return data

services = {
    'myservice.echo': echo,
    # Add other exposed functions and classes here
}

GatewayController = h.WSGIGateway(services, logger=log, debug=True)
########NEW FILE########
__FILENAME__ = pyramid_client
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

from pyamf.remoting.client import RemotingService

url = 'http://127.0.0.1:6543/gateway'
client = RemotingService(url, logger=logging)
service = client.getService('myservice')
echo = service.echo('Hello World!')

logging.debug(echo)

########NEW FILE########
__FILENAME__ = pyramid_gateway
from pyramid_rpc.amfgateway import PyramidGateway


def my_view(request):
    return {'project':'pyamf_tutorial'}

def echo(request, data):
    """
    This is a function that we will expose.
    """
    # echo data back to the client
    return data


services = {
    'myservice.echo': echo,
    # Add other exposed functions and classes here
}

echoGateway = PyramidGateway(services, debug=True)


########NEW FILE########
__FILENAME__ = mygateway
import logging

from pyamf.remoting.gateway.wsgi import WSGIGateway


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


class Services(object):

    def echo(self, data):
        return "Turbogears gateway says:" + str(data)

    def sum(self, a, b):
        return a + b

    def scramble(self, text):
        from random import shuffle
        s = [x for x in text]
        shuffle(s)
        return ''.join(s)


# Expose our services
services = {"Services" : Services()}

GatewayController = WSGIGateway(services, logger=logging, debug=True)
########NEW FILE########
__FILENAME__ = classic
from twisted.internet import reactor, defer
from twisted.web import server, static, resource

from pyamf.remoting.gateway.twisted import TwistedGateway
from pyamf.remoting.gateway import expose_request

import logging
        
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

class example:
    """
    An example class that can be used as a PyAMF service.
    """
    def test1(self):
        return "Test 1 Success!"
    
    @expose_request
    def testn(self, request, n):
        """
        This function is decorated to expose the underlying HTTP request,
        which provides access to things such as the requesting client's IP.
        """
        ip = request.getClientIP()

        return "%s said %s!" % (ip, n)

# A standalone function that can be bound to a service.
def add(a, b):
    return a + b

# Create a dictionary mapping the service namespaces to a function
# or class instance
services = {
    'example': example(),
    'myadd': add
}

# Place the namespace mapping into a TwistedGateway
gateway = TwistedGateway(services, logger=logging, expose_request=False,
                         debug=True)

# A base root resource for the twisted.web server
root = resource.Resource()

# Publish the PyAMF gateway at the root URL
root.putChild('', gateway)

# Start the twisted reactor and listen on HTTP port 8080
print 'Running AMF gateway on http://localhost:8080'

reactor.listenTCP(8080, server.Site(root))
reactor.run()
########NEW FILE########
__FILENAME__ = client
from pyamf.remoting.client import RemotingService

import logging
        
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


url = 'http://localhost:8080'
client = RemotingService(url, logger=logging)

service1 = client.getService('example')
print service1.testn('Hello World')

service2 = client.getService('myadd')
print service2(1,2)
########NEW FILE########
__FILENAME__ = preferred
from twisted.web import resource, server
from twisted.application import service, strports

from pyamf.remoting.gateway.twisted import TwistedGateway
from pyamf.remoting.gateway import expose_request

import logging
        
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

class example:
    """
    An example class that can be used as a PyAMF service.
    """
    def test1(self, n):
        return "Test 1 Success!"

    @expose_request
    def testn(self, request, n):
        """
        This function is decorated to expose the underlying HTTP request,
        which provides access to things such as the requesting client's IP.
        """
        ip = request.getClientIP()

        return "%s said %s!" % (ip, n)

# A standalone function that can be bound to a service.
def add(a, b): 
    return a + b 

# Create a dictionary mapping the service namespaces to a function
# or class instance
services = { 
    'example': example(),
    'myadd': add 
}

# Ideally, just the imports and the code below this comment would be
# in the .tac file; the AMF service would be defined in a module of
# your making

# Place the namespace mapping into a TwistedGateway
gateway = TwistedGateway(services, logger=logging, expose_request=False,
                         debug=True)

# A base root resource for the twisted.web server
root = resource.Resource()

# Publish the PyAMF gateway at the root URL
root.putChild('', gateway)

print 'Running AMF gateway on http://localhost:8080'

application = service.Application('PyAMF Sample Remoting Server')
server = strports.service('tcp:8080', server.Site(root))
server.setServiceParent(application)
########NEW FILE########
__FILENAME__ = stackless
import stackless

from   twisted.web import resource, http, server, error
from   twisted.internet import reactor
from   twisted.python import log

from   pyamf import remoting
from   pyamf.remoting.gateway.twisted import TwistedGateway
from   twisted.internet import defer
from   twisted.internet import task


class EchoServer(TwistedGateway):

   def __init__(self):
       super(EchoServer, self).__init__()
       self.request = None
       return

   def __echo__(self, request, deferred, y):
       deferred.callback(y)

   def echo(self, request, y):
       deferred = defer.Deferred()
       stackless.tasklet(self.__echo__)(request, deferred, y)

       return deferred


if __name__== "__main__":
   gw = EchoServer()
   gw.addService(gw.echo, "echo", "echo")

   root = resource.Resource()
   root.putChild('gwplayer', gw)
   reactor.listenTCP(8080, server.Site(root))
   print "server running on localhost:8080"

   task.LoopingCall(stackless.schedule).start(.01)
   stackless.tasklet(reactor.run)()
   stackless.run()
########NEW FILE########
__FILENAME__ = wsgi
import logging

from pyamf.remoting.gateway.wsgi import WSGIGateway
from pyamf.remoting.gateway import expose_request

from twisted.web import server
from twisted.web.wsgi import WSGIResource
from twisted.python.threadpool import ThreadPool
from twisted.internet import reactor
from twisted.application import service, strports

        
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


class example:
    """
    An example class that can be used as a PyAMF service.
    """
    def test1(self, n):
        return "Test 1 Success!"

    @expose_request
    def testn(self, request, n):
        """
        This function is decorated to expose the underlying HTTP request,
        which provides access to things such as the requesting client's IP.
        """
        ip = request['REMOTE_ADDR']

        return "%s said %s!" % (ip, n)


# A standalone function that can be bound to a service.
def add(a, b): 
    return a + b 


# Create a dictionary mapping the service namespaces to a function
# or class instance
services = { 
    'example': example(),
    'myadd': add 
}

# Create and start a thread pool,
wsgiThreadPool = ThreadPool()
wsgiThreadPool.start()

# ensuring that it will be stopped when the reactor shuts down
reactor.addSystemEventTrigger('after', 'shutdown', wsgiThreadPool.stop)

# PyAMF gateway
gateway = WSGIGateway(services, logger=logging, expose_request=False,
                      debug=True)

# Create the WSGI resource
wsgiAppAsResource = WSGIResource(reactor, wsgiThreadPool, gateway)
site = server.Site(wsgiAppAsResource)
server = strports.service('tcp:8080', site)

# Hooks for twistd
application = service.Application('PyAMF Sample Remoting Server')
server.setServiceParent(application)
########NEW FILE########
__FILENAME__ = client
from pyamf.remoting.client import RemotingService

import logging
        
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

url = 'http://localhost:8080'
client = RemotingService(url, logger=logging)
service = client.getService('echo')
echo = service('Hello World!')

logging.debug(echo)
########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from werkzeug import run_simple

from pyamf.remoting.gateway.wsgi import WSGIGateway

import logging
        

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


def echo(data):
    return data

services = {'echo': echo}
gw = WSGIGateway(services, logger=logging, debug=True)

run_simple('localhost', 8080, gw, use_reloader=True)
########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.


import logging
from optparse import OptionParser

from pyamf.remoting.client import RemotingService


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

parser = OptionParser()
parser.add_option("-p", "--port", default=8000,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default="localhost",
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()


url = 'http://%s:%d' % (options.host, int(options.port))
client = RemotingService(url, logger=logging)
client.setCredentials('jane', 'doe')

calc_service = client.getService('calc')
print calc_service.sum(85, 115) # should print 200.0

client.setCredentials('abc', 'def')
print calc_service.sum(85, 115).description # should print Authentication Failed

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Authentication example server.

@since: 0.1
"""


from pyamf.remoting.gateway.wsgi import WSGIGateway


class CalcService:
    def sum(self, a, b):
         return a + b


def auth(username, password):
    if username == 'jane' and password == 'doe':
        return True

    return False


gateway = WSGIGateway({'calc': CalcService}, authenticator=auth)


if __name__ == '__main__':
    from optparse import OptionParser
    from wsgiref import simple_server

    parser = OptionParser()
    parser.add_option("-p", "--port", default=8000,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default="localhost",
        dest="host", help="host address [default: %default]")
    (options, args) = parser.parse_args()

    host = options.host
    port = int(options.port)

    httpd = simple_server.WSGIServer((host, port), simple_server.WSGIRequestHandler)
    httpd.set_app(gateway)

    print "Running Authentication AMF gateway on http://%s:%d" % (host, port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = amf_version
from pyamf import AMF0, AMF3
from pyamf.remoting.client import RemotingService

gateway = 'http://demo.pyamf.org/gateway/helloworld'
client = RemotingService(gateway, amf_version=AMF3)
service = client.getService('echo')

print service("Hello AMF3 world!")

########NEW FILE########
__FILENAME__ = authentication
from pyamf.remoting.client import RemotingService

client = RemotingService('https://demo.pyamf.org/gateway/authentication')
client.setCredentials('jane', 'doe')

service = client.getService('calc')
print service.sum(85, 115) # should print 200.0

client.setCredentials('abc', 'def')
print service.sum(85, 115).description # should print Authentication Failed
########NEW FILE########
__FILENAME__ = basic
from pyamf.remoting.client import RemotingService

client = RemotingService('http://demo.pyamf.org/gateway/recordset')
service = client.getService('service')

print service.getLanguages()
########NEW FILE########
__FILENAME__ = exception
>>> from pyamf.remoting.client import RemotingService
>>> gateway = RemotingService('http://example.org/gw')
>>> service = gateway.getService('type_error')
>>> service()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/nick/projects/pyamf/pyamf/remoting/client/__init__.py", line 121, in __call__
    return self._call(ServiceMethodProxy(self, None), *args)
  File "/Users/nick/projects/pyamf/pyamf/remoting/client/__init__.py", line 107, in _call
    response.body.raiseException()
  File "/Users/nick/projects/pyamf/pyamf/remoting/__init__.py", line 335, in raiseException
    raise get_exception_from_fault(self), self.description, None
TypeError: some useful message here

########NEW FILE########
__FILENAME__ = headers
from pyamf.remoting.client import RemotingService

gw = RemotingService('http://demo.pyamf.org/gateway/recordset')

gw.addHTTPHeader("Accept-encoding", "gzip")
gw.addHTTPHeader('Set-Cookie', 'sessionid=QT3cUmACNeKQo5oPeM0')
gw.removeHTTPHeader('Set-Cookie')

username = 'admin'
password = 'admin'
auth = ('%s:%s' % (username, password)).encode('base64')[:-1]

gw.addHTTPHeader("Authorization", "Basic %s" % auth)

service = gw.getService('service')
print service.getLanguages()

########NEW FILE########
__FILENAME__ = logger
from pyamf.remoting.client import RemotingService

import logging
logging.basicConfig(level=logging.DEBUG,
           format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')

gateway = 'http://demo.pyamf.org/gateway/recordset'
client = RemotingService(gateway, logger=logging)
service = client.getService('service')

print service.getLanguages()
########NEW FILE########
__FILENAME__ = referer
from pyamf.remoting.client import RemotingService

appReferer = 'client.py'
gateway = 'http://demo.pyamf.org/gateway/helloworld'
client = RemotingService(gateway, referer=appReferer)
service = client.getService('echo')

print service.echo('Hello World!')

########NEW FILE########
__FILENAME__ = user_agent
from pyamf.remoting.client import RemotingService

appName = 'MyApp/0.1.0'
gateway = 'http://demo.pyamf.org/gateway/helloworld'
client = RemotingService(gateway, user_agent=appName)
service = client.getService('echo')

print service.echo('Hello World!')

########NEW FILE########
__FILENAME__ = client
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Hello world example client.

@see: U{HelloWorld<http://pyamf.org/tutorials/general/helloworld/index.html>} documentation.

@since: 0.1.0
"""

from pyamf.remoting.client import RemotingService

gateway = RemotingService('http://demo.pyamf.org/gateway/helloworld')

echo_service = gateway.getService('echo.echo')

print echo_service('Hello world!')

########NEW FILE########
__FILENAME__ = server
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Hello world example server.

@see: U{HelloWorld<http://pyamf.org/tutorials/general/helloworld/index.html>} wiki page.

@since: 0.1.0
"""

def echo(data):
    """
    Just return data back to the client.
    """
    return data

services = {
    'echo': echo,
    'echo.echo': echo
}

if __name__ == '__main__':
    import os
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server

    gw = WSGIGateway(services)

    httpd = simple_server.WSGIServer(
        ('localhost', 8000),
        simple_server.WSGIRequestHandler,
    )

    def app(environ, start_response):
        if environ['PATH_INFO'] == '/crossdomain.xml':
            fn = os.path.join(os.getcwd(), os.path.dirname(__file__),
               'crossdomain.xml')

            fp = open(fn, 'rt')
            buffer = fp.readlines()
            fp.close()

            start_response('200 OK', [
                ('Content-Type', 'application/xml'),
                ('Content-Length', str(len(''.join(buffer))))
            ])

            return buffer

        return gw(environ, start_response)

    httpd.set_app(app)

    print "Running Hello World AMF gateway on http://localhost:8000"

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


########NEW FILE########
__FILENAME__ = client
"""
Hello world example client for Apache Ant.
"""

import logging
logging.basicConfig(level=logging.INFO,
           format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')


from pyamf.remoting.client import RemotingService

url = 'http://localhost:8000'
gateway = RemotingService(url, logger=logging, debug=True)

echo_service = gateway.getService('echo.echo')
result = echo_service('Hello world!')

logging.info(result)

########NEW FILE########
__FILENAME__ = server
"""
Hello world example server for Apache Ant.
"""

def echo(data):
    """
    Just return data back to the client.
    """
    return data


if __name__ == '__main__':
    import os
    import logging
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server

    logging.basicConfig(level=logging.DEBUG,
           format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')

    services = {
        'echo.echo': echo
    }

    gw = WSGIGateway(services, logger=logging, debug=True)

    httpd = simple_server.WSGIServer(
        ('localhost', 8000),
        simple_server.WSGIRequestHandler,
    )

    httpd.set_app(gw)

    print "Running AMF gateway on http://localhost:8000"

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


########NEW FILE########
__FILENAME__ = client
import logging
	
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


from pyamf.remoting.client import RemotingService
from pyamf.remoting import RemotingError

url = 'http://localhost:8080/pyamf'
client = RemotingService(url, logger=logging)
service = client.getService('my_service')

try:
    print service.echo('Hello World!')
except RemotingError, e:
    print e

########NEW FILE########
__FILENAME__ = demo_app
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)


def echo(data):
    return data


def handler(environ, start_response):
    from pyamf.remoting.gateway.wsgi import WSGIGateway

    services = {'my_service.echo': echo}
    gw = WSGIGateway(services, logger=logging, debug=True)

    return gw(environ, start_response)

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env jython
#
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
Jython AMF client example.

@since: 0.5
"""


import gui

from optparse import OptionParser

from pyamf.remoting.client import RemotingService


# parse commandline options
parser = OptionParser()
parser.add_option("-p", "--port", default=gui.port,
    dest="port", help="port number [default: %default]")
parser.add_option("--host", default=gui.host,
    dest="host", help="host address [default: %default]")
(options, args) = parser.parse_args()

# define gateway
url = 'http://%s:%d' % (options.host, int(options.port))
server = RemotingService(url)

# echo data
service = server.getService(gui.service_name)

print service('Hello World!')
########NEW FILE########
__FILENAME__ = gui
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Jython example AMF server and client with Swing interface.

@see: U{Jython<http://pyamf.org/wiki/JythonExample>} wiki page.
@since: 0.5
"""


import logging

from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
from pyamf.remoting.gateway.wsgi import WSGIGateway
from pyamf.remoting.client import RemotingService

import java.lang as lang
import javax.swing as swing
import java.awt as awt


class AppGUI(object):
    """
    Swing graphical user interface.
    """
    def __init__(self, title, host, port, service):
        # create window
        win = swing.JFrame(title, size=(800, 480))
        win.setDefaultCloseOperation(swing.JFrame.EXIT_ON_CLOSE)
        win.contentPane.layout = awt.BorderLayout(10, 10)

        # add scrollable textfield
        status = swing.JTextPane(preferredSize=(780, 400))
        status.setAutoscrolls(True)
        status.setEditable(False)
        status.setBorder(swing.BorderFactory.createEmptyBorder(20, 20, 20, 20))
        paneScrollPane = swing.JScrollPane(status)
        paneScrollPane.setVerticalScrollBarPolicy(
                        swing.JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED)
        win.contentPane.add(paneScrollPane, awt.BorderLayout.CENTER)

        # add server button
        self.started = "Start Server"
        self.stopped = "Stop Server"
        self.serverButton = swing.JButton(self.started, preferredSize=(150, 20),
                                          actionPerformed=self.controlServer)

        # add client button
        self.clientButton = swing.JButton("Invoke Method", preferredSize=(150, 20),
                                          actionPerformed=self.runClient)
        self.clientButton.enabled = False

        # position buttons
        buttonPane = swing.JPanel()
        buttonPane.setLayout(swing.BoxLayout(buttonPane, swing.BoxLayout.X_AXIS))
        buttonPane.setBorder(swing.BorderFactory.createEmptyBorder(0, 10, 10, 10))
        buttonPane.add(swing.Box.createHorizontalGlue())
        buttonPane.add(self.serverButton)
        buttonPane.add(swing.Box.createRigidArea(awt.Dimension(10, 0)))
        buttonPane.add(self.clientButton)
        win.contentPane.add(buttonPane, awt.BorderLayout.SOUTH)

        # add handler that writes log messages to the status textfield
        txtHandler = TextFieldLogger(status)
        logger = logging.getLogger("")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        txtHandler.setFormatter(formatter)
        logger.addHandler(txtHandler)

        # setup server
        self.service_name = service
        self.url = "http://%s:%d" % (host, port)
        self.server = ThreadedAmfServer(host, port, self.service_name)

        # center and display window on the screen
        win.pack()
        us = win.getSize()
        them = awt.Toolkit.getDefaultToolkit().getScreenSize()
        newX = (them.width - us.width) / 2
        newY = (them.height - us.height) / 2
        win.setLocation(newX, newY)
        win.show()

    def controlServer(self, event):
        """
        Handler for server button clicks.
        """
        if event.source.text == self.started:
            logging.info("Created AMF gateway at %s" % self.url)
            event.source.text = self.stopped
            self.clientButton.enabled = True
            self.server.start()
        else:
            logging.info("Terminated AMF gateway at %s\n" % self.url)
            event.source.text = self.started
            self.clientButton.enabled = False
            self.server.stop()

    def runClient(self, event):
        """
        Invoke a method on the server using an AMF client.
        """
        self.client = ThreadedAmfClient(self.url, self.service_name)
        self.client.invokeMethod("Hello World!")


class ThreadedAmfClient(object):
    """
    Threaded AMF client that doesn't block the Swing GUI.
    """
    def __init__(self, url, serviceName):
        self.gateway = RemotingService(url, logger=logging)
        self.service = self.gateway.getService(serviceName)

    def invokeMethod(self, param):
        """
        Invoke a method on the AMF server.
        """
        class ClientThread(lang.Runnable):
            """
            Create a thread for the client.
            """
            def run(this):
                try:
                    self.service(param)
                except lang.InterruptedException:
                    return

        swing.SwingUtilities.invokeLater(ClientThread())


class ThreadedAmfServer(object):
    """
    Threaded WSGI server that doesn't block the Swing GUI.
    """
    def __init__(self, host, port, serviceName):      
        services = {serviceName: self.echo}
        gw = WSGIGateway(services, logger=logging)
        self.httpd = WSGIServer((host, port),
                     ServerRequestLogger)
        self.httpd.set_app(gw)

    def start(self):
        """
        Start the server.
        """
        class WSGIThread(lang.Runnable):
            """
            Create a thread for the server.
            """
            def run(this):
                try:
                    self.httpd.serve_forever()
                except lang.InterruptedException:
                    return

        self.thread = lang.Thread(WSGIThread())
        self.thread.start()

    def stop(self):
        """
        Stop the server.
        """
        self.thread = None

    def echo(self, data):
        """
        Just return data back to the client.
        """
        return data


class ServerRequestLogger(WSGIRequestHandler):
    """
    Request handler that logs WSGI server messages.
    """
    def log_message(self, format, *args):
        """
        Log message with debug level.
        """
        logging.debug("%s - %s" % (self.address_string(), format % args))


class TextFieldLogger(logging.Handler):
    """
    Logging handler that displays PyAMF log messages in the status text field.
    """
    def __init__(self, textfield, *args, **kwargs):
        self.status = textfield
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        msg = '%s\n' % self.format(record)
        doc = self.status.getStyledDocument()
        doc.insertString(doc.getLength(), msg, doc.getStyle('regular'))
        self.status.setCaretPosition(self.status.getStyledDocument().getLength())


host = "localhost"
port = 8000
service_name = "echo"
title = "PyAMF server/client using Jython with Swing"


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", default=port,
        dest="port", help="port number [default: %default]")
    parser.add_option("--host", default=host,
        dest="host", help="host address [default: %default]")
    (opt, args) = parser.parse_args()

    app = AppGUI(title, opt.host, int(opt.port), service_name)

########NEW FILE########
__FILENAME__ = build_ext
build_ext = "this setuptools bug has been around for a *very* long time ..."


########NEW FILE########
__FILENAME__ = util
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Useful helpers for adapters.

@since: 0.4
"""

import __builtin__

if not hasattr(__builtin__, 'set'):
    from sets import Set as set


def to_list(obj, encoder):
    """
    Converts an arbitrary object C{obj} to a C{list}.
    """
    return list(obj)


def to_dict(obj, encoder):
    """
    Converts an arbitrary object C{obj} to a C{dict}.
    """
    return dict(obj)


def to_set(obj, encoder):
    """
    Converts an arbitrary object C{obj} to a C{set}.
    """
    return set(obj)


def to_tuple(x, encoder):
    """
    Converts an arbitrary object C{obj} to a C{tuple}.
    """
    return tuple(x)


def to_string(x, encoder):
    """
    Converts an arbitrary object C{obj} to a string.

    @since: 0.5
    """
    return str(x)

########NEW FILE########
__FILENAME__ = _array
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
U{array<http://docs.python.org/library/array.html>} adapter module.

Will convert all array.array instances to a python list before encoding. All
type information is lost (but degrades nicely).

@since: 0.5
"""

import array

import pyamf
from pyamf.adapters import util


if hasattr(array, 'ArrayType'):
    pyamf.add_type(array.ArrayType, util.to_list)

########NEW FILE########
__FILENAME__ = _collections
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
U{collections<http://docs.python.org/library/collections.html>} adapter module.

@since: 0.5
"""

import collections

import pyamf
from pyamf.adapters import util


if hasattr(collections, 'deque'):
    pyamf.add_type(collections.deque, util.to_list)

if hasattr(collections, 'defaultdict'):
    pyamf.add_type(collections.defaultdict, util.to_dict)

if hasattr(collections, 'Counter'):
    pyamf.add_type(collections.Counter, util.to_dict)

if hasattr(collections, 'OrderedDict'):
    pyamf.add_type(collections.OrderedDict, util.to_dict)

########NEW FILE########
__FILENAME__ = _decimal
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Adapter for the U{decimal<http://docs.python.org/library/decimal.html>} module.

@since: 0.4
"""

import decimal

import pyamf


def convert_Decimal(x, encoder):
    """
    Called when an instance of U{decimal.Decimal<http://
    docs.python.org/library/decimal.html#decimal-objects>} is about to be
    encoded to an AMF stream.

    @return: If the encoder is in 'strict' mode then C{x} will be converted to
        a float. Otherwise an L{pyamf.EncodeError} with a friendly message is
        raised.
    """
    if encoder.strict is False:
        return float(x)

    raise pyamf.EncodeError('Unable to encode decimal.Decimal instances as '
        'there is no way to guarantee exact conversion. Use strict=False to '
        'convert to a float.')


if hasattr(decimal, 'Decimal'):
    pyamf.add_type(decimal.Decimal, convert_Decimal)

########NEW FILE########
__FILENAME__ = _django_contrib_auth_models
"""
"""

from django.contrib.auth import models

import pyamf.adapters


models.User.__amf__ = {
    'exclude': ('message_set', 'password'),
    'readonly': ('username',)
}

# ensure that the adapter that we depend on is loaded ..
pyamf.adapters.get_adapter('django.db.models.base')

pyamf.register_package(models, models.__name__)
########NEW FILE########
__FILENAME__ = _django_db_models_base
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
C{django.db.models} adapter module.

@see: U{Django Project<http://www.djangoproject.com>}
@since: 0.4.1
"""

from django.db.models.base import Model
from django.db.models import fields
from django.db.models.fields import related, files

import datetime

import pyamf


class DjangoReferenceCollection(dict):
    """
    This helper class holds a dict of klass to pk/objects loaded from the
    underlying db.

    @since: 0.5
    """

    def _getClass(self, klass):
        if klass not in self.keys():
            self[klass] = {}

        return self[klass]

    def getClassKey(self, klass, key):
        """
        Return an instance based on klass/key.

        If an instance cannot be found then C{KeyError} is raised.

        @param klass: The class of the instance.
        @param key: The primary_key of the instance.
        @return: The instance linked to the C{klass}/C{key}.
        @rtype: Instance of C{klass}.
        """
        d = self._getClass(klass)

        return d[key]

    def addClassKey(self, klass, key, obj):
        """
        Adds an object to the collection, based on klass and key.

        @param klass: The class of the object.
        @param key: The datastore key of the object.
        @param obj: The loaded instance from the datastore.
        """
        d = self._getClass(klass)

        d[key] = obj


class DjangoClassAlias(pyamf.ClassAlias):

    def getCustomProperties(self):
        self.fields = {}
        self.relations = {}
        self.columns = []

        self.meta = self.klass._meta

        for name in self.meta.get_all_field_names():
            x = self.meta.get_field_by_name(name)[0]

            if isinstance(x, files.FileField):
                self.readonly_attrs.update([name])

            if isinstance(x, related.RelatedObject):
                continue

            if isinstance(x, related.ManyToManyField):
                self.relations[name] = x
            elif not isinstance(x, related.ForeignKey):
                self.fields[name] = x
            else:
                self.relations[name] = x

        parent_fields = []

        for field in self.meta.parents.values():
            parent_fields.append(field.attname)
            del self.relations[field.name]

        self.exclude_attrs.update(parent_fields)

        props = self.fields.keys()

        self.encodable_properties.update(props)
        self.decodable_properties.update(props)

        self.exclude_attrs.update(['_state'])

    def _compile_base_class(self, klass):
        if klass is Model:
            return

        pyamf.ClassAlias._compile_base_class(self, klass)

    def _encodeValue(self, field, value):
        if value is fields.NOT_PROVIDED:
            return pyamf.Undefined

        if value is None:
            return value

        # deal with dates ..
        if isinstance(field, fields.DateTimeField):
            return value
        elif isinstance(field, fields.DateField):
            return datetime.datetime(value.year, value.month, value.day, 0, 0, 0)
        elif isinstance(field, fields.TimeField):
            return datetime.datetime(1970, 1, 1,
                value.hour, value.minute, value.second, value.microsecond)
        elif isinstance(value, files.FieldFile):
            return value.name

        return value

    def _decodeValue(self, field, value):
        if value is pyamf.Undefined:
            return fields.NOT_PROVIDED

        if isinstance(field, fields.AutoField) and value == 0:
            return None
        elif isinstance(field, fields.DateTimeField):
            # deal with dates
            return value
        elif isinstance(field, fields.DateField):
            if not value:
                return None

            return datetime.date(value.year, value.month, value.day)
        elif isinstance(field, fields.TimeField):
            if not value:
                return None

            return datetime.time(value.hour, value.minute, value.second, value.microsecond)

        return value

    def getEncodableAttributes(self, obj, **kwargs):
        attrs = pyamf.ClassAlias.getEncodableAttributes(self, obj, **kwargs)

        if not attrs:
            attrs = {}

        for name, prop in self.fields.iteritems():
            if name not in attrs.keys():
                continue

            attrs[name] = self._encodeValue(prop, getattr(obj, name))

        keys = attrs.keys()

        for key in keys:
            if key.startswith('_'):
                del attrs[key]

        for name, relation in self.relations.iteritems():
            if '_%s_cache' % name in obj.__dict__:
                attrs[name] = getattr(obj, name)

            if isinstance(relation, related.ManyToManyField):
                attrs[name] = [x for x in getattr(obj, name).all()]
            else:
                del attrs[relation.attname]

        return attrs

    def getDecodableAttributes(self, obj, attrs, **kwargs):
        attrs = pyamf.ClassAlias.getDecodableAttributes(self, obj, attrs, **kwargs)

        for n in self.decodable_properties:
            if n in self.relations:
                continue

            try:
                f = self.fields[n]
            except KeyError:
                continue

            attrs[f.attname] = self._decodeValue(f, attrs[n])

        # primary key of django object must always be set first for
        # relationships with other model objects to work properly
        # and dict.iteritems() does not guarantee order
        #
        # django also forces the use only one attribute as primary key, so
        # our obj._meta.pk.attname check is sufficient)
        pk_attr = obj._meta.pk.attname
        pk = attrs.pop(pk_attr, None)

        if pk:
            if pk is fields.NOT_PROVIDED:
                attrs[pk_attr] = pk
            else:
                # load the object from the database
                try:
                    loaded_instance = self.klass.objects.filter(pk=pk)[0]
                    obj.__dict__ = loaded_instance.__dict__
                except IndexError:
                    pass

        if not getattr(obj, pk_attr):
            for name, relation in self.relations.iteritems():
                if isinstance(relation, related.ManyToManyField):
                    try:
                        if len(attrs[name]) == 0:
                            del attrs[name]
                    except KeyError:
                        pass

        return attrs


def getDjangoObjects(context):
    """
    Returns a reference to the C{django_objects} on the context. If it doesn't
    exist then it is created.

    @rtype: Instance of L{DjangoReferenceCollection}
    @since: 0.5
    """
    c = context.extra
    k = 'django_objects'

    try:
        return c[k]
    except KeyError:
        c[k] = DjangoReferenceCollection()

    return c[k]


def writeDjangoObject(obj, encoder=None):
    """
    The Django ORM creates new instances of objects for each db request.
    This is a problem for PyAMF as it uses the C{id(obj)} of the object to do
    reference checking.

    We could just ignore the problem, but the objects are conceptually the
    same so the effort should be made to attempt to resolve references for a
    given object graph.

    We create a new map on the encoder context object which contains a dict of
    C{object.__class__: {key1: object1, key2: object2, .., keyn: objectn}}. We
    use the primary key to do the reference checking.

    @since: 0.5
    """
    s = obj.pk

    if s is None:
        encoder.writeObject(obj)

        return

    django_objects = getDjangoObjects(encoder.context)
    kls = obj.__class__

    try:
        referenced_object = django_objects.getClassKey(kls, s)
    except KeyError:
        referenced_object = obj
        django_objects.addClassKey(kls, s, obj)

    encoder.writeObject(referenced_object)


# initialise the module here: hook into pyamf
pyamf.register_alias_type(DjangoClassAlias, Model)
pyamf.add_type(Model, writeDjangoObject)

########NEW FILE########
__FILENAME__ = _django_db_models_fields
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
C{django.db.models.fields} adapter module.

@see: U{Django Project<http://www.djangoproject.com>}
@since: 0.4
"""

from django.db.models import fields

import pyamf


def convert_NOT_PROVIDED(x, encoder):
    """
    @rtype: L{Undefined<pyamf.Undefined>}
    """
    return pyamf.Undefined


pyamf.add_type(lambda x: x is fields.NOT_PROVIDED, convert_NOT_PROVIDED)

########NEW FILE########
__FILENAME__ = _django_db_models_query
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Django query adapter module.

Sets up basic type mapping and class mappings for a
Django models.

@see: U{Django Project<http://www.djangoproject.com>}
@since: 0.1b
"""

from django.db.models import query

import pyamf
from pyamf.adapters import util


pyamf.add_type(query.QuerySet, util.to_list)

########NEW FILE########
__FILENAME__ = _django_utils_translation
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
C{django.utils.translation} adapter module.

@see: U{Django Project<http://www.djangoproject.com>}
@since: 0.4.2
"""

from django.utils.translation import ugettext_lazy

import pyamf


def convert_lazy(l, encoder=None):
    if l.__class__._delegate_unicode:
        return unicode(l)

    if l.__class__._delegate_str:
        return str(l)

    raise ValueError('Don\'t know how to convert lazy value %s' % (repr(l),))


pyamf.add_type(type(ugettext_lazy('foo')), convert_lazy)

########NEW FILE########
__FILENAME__ = _elixir
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
Elixir adapter module. Elixir adds a number of properties to the mapped instances.

@see: U{Elixir homepage<http://elixir.ematia.de>}
@since: 0.6
"""

import elixir.entity

import pyamf
from pyamf import adapters

adapter = adapters.get_adapter('sqlalchemy.orm')

adapter.class_checkers.append(elixir.entity.is_entity)


class ElixirAdapter(adapter.SaMappedClassAlias):

    EXCLUDED_ATTRS = adapter.SaMappedClassAlias.EXCLUDED_ATTRS + [
        '_global_session']

    def getCustomProperties(self):
        adapter.SaMappedClassAlias.getCustomProperties(self)

        self.descriptor = self.klass._descriptor
        self.parent_descriptor = None

        if self.descriptor.parent:
            self.parent_descriptor = self.descriptor.parent._descriptor

        foreign_constraints = []

        for constraint in self.descriptor.constraints:
            for col in constraint.columns:
                col = str(col)

                if adapter.__version__.startswith('0.6'):
                    foreign_constraints.append(col)
                else:
                    if col.startswith(self.descriptor.tablename + '.'):
                        foreign_constraints.append(col[len(self.descriptor.tablename) + 1:])

        if self.descriptor.polymorphic:
            self.exclude_attrs.update([self.descriptor.polymorphic])

        self.exclude_attrs.update(foreign_constraints)

    def _compile_base_class(self, klass):
        if klass is elixir.EntityBase or klass is elixir.Entity:
            return

        pyamf.ClassAlias._compile_base_class(self, klass)


pyamf.register_alias_type(ElixirAdapter, elixir.entity.is_entity)
########NEW FILE########
__FILENAME__ = _google_appengine_ext_blobstore
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Adapter module for U{google.appengine.ext.blobstore<http://
code.google.com/appengine/docs/python/blobstore/>}.

@since: 0.6
"""

from google.appengine.ext import blobstore

import pyamf


bi = blobstore.BlobInfo


class BlobInfoStub(object):
    """
    Since C{blobstore.BlobInfo} requires __init__ args, we stub the object until
    C{applyAttributes} is called which then magically converts it to the correct
    type.
    """


class BlobInfoClassAlias(pyamf.ClassAlias):
    """
    Fine grain control over C{blobstore.BlobInfo} instances. Required to encode
    the C{key} attribute correctly.
    """

    def createInstance(self, *args, **kwargs):
        return BlobInfoStub()

    def getEncodableAttributes(self, obj, codec=None):
        """
        Returns a dict of kay/value pairs for PyAMF to encode.
        """
        attrs = {
            'content_type': obj.content_type,
            'filename': obj.filename,
            'size': obj.size,
            'creation': obj.creation,
            'key': str(obj.key())
        }

        return attrs

    def applyAttributes(self, obj, attrs, **kwargs):
        """
        Applies C{attrs} to C{obj}. Since C{blobstore.BlobInfo} objects are
        read-only entities, we only care about the C{key} attribute.
        """
        assert type(obj) is BlobInfoStub

        key = attrs.pop('key', None)

        if not key:
            raise pyamf.DecodeError("Unable to build blobstore.BlobInfo "
                "instance. Missing 'key' attribute.")

        try:
            key = blobstore.BlobKey(key)
        except:
            raise pyamf.DecodeError("Unable to build a valid blobstore.BlobKey "
                "instance. Key supplied was %r" % (key,))

        obj.__class__ = blobstore.BlobInfo

        obj.__init__(key)


pyamf.register_alias_type(BlobInfoClassAlias, bi)
pyamf.register_class(bi, '.'.join([blobstore.__name__, bi.__name__]))

del bi

########NEW FILE########
__FILENAME__ = _google_appengine_ext_db
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Google App Engine adapter module.

Sets up basic type mapping and class mappings for using the Datastore API
in Google App Engine.

@see: U{Datastore API on Google App Engine<http://
    code.google.com/appengine/docs/python/datastore>}
@since: 0.3.1
"""

from google.appengine.ext import db
from google.appengine.ext.db import polymodel
import datetime

import pyamf
from pyamf.adapters import util


class ModelStub(object):
    """
    This class represents a C{db.Model} or C{db.Expando} class as the typed
    object is being read from the AMF stream. Once the attributes have been
    read from the stream and through the magic of Python, the instance of this
    class will be converted into the correct type.

    @ivar klass: The referenced class either C{db.Model} or C{db.Expando}.
        This is used so we can proxy some of the method calls during decoding.
    @type klass: C{db.Model} or C{db.Expando}
    @see: L{DataStoreClassAlias.applyAttributes}
    """

    def __init__(self, klass):
        self.klass = klass

    def properties(self):
        return self.klass.properties()

    def dynamic_properties(self):
        return []


class GAEReferenceCollection(dict):
    """
    This helper class holds a dict of klass to key/objects loaded from the
    Datastore.

    @since: 0.4.1
    """

    def _getClass(self, klass):
        if not issubclass(klass, (db.Model, db.Expando)):
            raise TypeError('expected db.Model/db.Expando class, got %s' % (klass,))

        return self.setdefault(klass, {})

    def getClassKey(self, klass, key):
        """
        Return an instance based on klass/key.

        If an instance cannot be found then C{KeyError} is raised.

        @param klass: The class of the instance.
        @param key: The key of the instance.
        @return: The instance linked to the C{klass}/C{key}.
        @rtype: Instance of L{klass}.
        """
        d = self._getClass(klass)

        return d[key]

    def addClassKey(self, klass, key, obj):
        """
        Adds an object to the collection, based on klass and key.

        @param klass: The class of the object.
        @param key: The datastore key of the object.
        @param obj: The loaded instance from the datastore.
        """
        d = self._getClass(klass)

        d[key] = obj


class DataStoreClassAlias(pyamf.ClassAlias):
    """
    This class contains all the business logic to interact with Google's
    Datastore API's. Any C{db.Model} or C{db.Expando} classes will use this
    class alias for encoding/decoding.

    We also add a number of indexes to the encoder context to aggressively
    decrease the number of Datastore API's that we need to complete.
    """

    # The name of the attribute used to represent the key
    KEY_ATTR = '_key'

    def _compile_base_class(self, klass):
        if klass in (db.Model, polymodel.PolyModel):
            return

        pyamf.ClassAlias._compile_base_class(self, klass)

    def getCustomProperties(self):
        props = [self.KEY_ATTR]
        self.reference_properties = {}
        self.properties = {}
        reverse_props = []

        for name, prop in self.klass.properties().iteritems():
            self.properties[name] = prop

            props.append(name)

            if isinstance(prop, db.ReferenceProperty):
                self.reference_properties[name] = prop

        if issubclass(self.klass, polymodel.PolyModel):
            del self.properties['_class']
            props.remove('_class')

        # check if the property is a defined as a collection_name. These types
        # of properties are read-only and the datastore freaks out if you
        # attempt to meddle with it. We delete the attribute entirely ..
        for name, value in self.klass.__dict__.iteritems():
            if isinstance(value, db._ReverseReferenceProperty):
                reverse_props.append(name)

        self.encodable_properties.update(self.properties.keys())
        self.decodable_properties.update(self.properties.keys())
        self.readonly_attrs.update(reverse_props)

        if not self.reference_properties:
            self.reference_properties = None

        if not self.properties:
            self.properties = None

        self.no_key_attr = self.KEY_ATTR in self.exclude_attrs

    def getEncodableAttributes(self, obj, codec=None):
        attrs = pyamf.ClassAlias.getEncodableAttributes(self, obj, codec=codec)

        gae_objects = getGAEObjects(codec.context) if codec else None

        if self.reference_properties and gae_objects:
            for name, prop in self.reference_properties.iteritems():
                klass = prop.reference_class
                key = prop.get_value_for_datastore(obj)

                if not key:
                    continue

                try:
                    attrs[name] = gae_objects.getClassKey(klass, key)
                except KeyError:
                    ref_obj = getattr(obj, name)
                    gae_objects.addClassKey(klass, key, ref_obj)
                    attrs[name] = ref_obj

        for k in attrs.keys()[:]:
            if k.startswith('_'):
                del attrs[k]

        for attr in obj.dynamic_properties():
            attrs[attr] = getattr(obj, attr)

        if not self.no_key_attr:
            attrs[self.KEY_ATTR] = str(obj.key()) if obj.is_saved() else None

        return attrs

    def createInstance(self, codec=None):
        return ModelStub(self.klass)

    def getDecodableAttributes(self, obj, attrs, codec=None):
        key = attrs.setdefault(self.KEY_ATTR, None)
        attrs = pyamf.ClassAlias.getDecodableAttributes(self, obj, attrs, codec=codec)

        del attrs[self.KEY_ATTR]
        new_obj = None

        # attempt to load the object from the datastore if KEY_ATTR exists.
        if key and codec:
            new_obj = loadInstanceFromDatastore(self.klass, key, codec)

        # clean up the stub
        if isinstance(obj, ModelStub) and hasattr(obj, 'klass'):
            del obj.klass

        if new_obj:
            obj.__dict__ = new_obj.__dict__.copy()

        obj.__class__ = self.klass
        apply_init = True

        if self.properties:
            for k in [k for k in attrs.keys() if k in self.properties.keys()]:
                prop = self.properties[k]
                v = attrs[k]

                if isinstance(prop, db.FloatProperty) and isinstance(v, (int, long)):
                    attrs[k] = float(v)
                elif isinstance(prop, db.IntegerProperty) and isinstance(v, float):
                    x = long(v)

                    # only convert the type if there is no mantissa - otherwise
                    # let the chips fall where they may
                    if x == v:
                        attrs[k] = x
                elif isinstance(prop, db.ListProperty) and v is None:
                    attrs[k] = []
                elif isinstance(v, datetime.datetime):
                    # Date/Time Property fields expect specific types of data
                    # whereas PyAMF only decodes into datetime.datetime objects.
                    if isinstance(prop, db.DateProperty):
                        attrs[k] = v.date()
                    elif isinstance(prop, db.TimeProperty):
                        attrs[k] = v.time()

                if new_obj is None and isinstance(v, ModelStub) and prop.required and k in self.reference_properties:
                    apply_init = False
                    del attrs[k]

        # If the object does not exist in the datastore, we must fire the
        # class constructor. This sets internal attributes that pyamf has
        # no business messing with ..
        if new_obj is None and apply_init is True:
            obj.__init__(**attrs)

        return attrs


def getGAEObjects(context):
    """
    Returns a reference to the C{gae_objects} on the context. If it doesn't
    exist then it is created.

    @param context: The context to load the C{gae_objects} index from.
    @return: The C{gae_objects} index reference.
    @rtype: Instance of L{GAEReferenceCollection}
    @since: 0.4.1
    """
    return context.extra.setdefault('gae_objects', GAEReferenceCollection())


def loadInstanceFromDatastore(klass, key, codec=None):
    """
    Attempt to load an instance from the datastore, based on C{klass}
    and C{key}. We create an index on the codec's context (if it exists)
    so we can check that first before accessing the datastore.

    @param klass: The class that will be loaded from the datastore.
    @type klass: Sub-class of C{db.Model} or C{db.Expando}
    @param key: The key which is used to uniquely identify the instance in the
        datastore.
    @type key: C{str}
    @param codec: The codec to reference the C{gae_objects} index. If
        supplied,The codec must have have a context attribute.
    @return: The loaded instance from the datastore.
    @rtype: Instance of C{klass}.
    @since: 0.4.1
    """
    if not issubclass(klass, (db.Model, db.Expando)):
        raise TypeError('expected db.Model/db.Expando class, got %s' % (klass,))

    if not isinstance(key, basestring):
        raise TypeError('string expected for key, got %s', (repr(key),))

    key = str(key)

    if codec is None:
        return klass.get(key)

    gae_objects = getGAEObjects(codec.context)

    try:
        return gae_objects.getClassKey(klass, key)
    except KeyError:
        pass

    obj = klass.get(key)
    gae_objects.addClassKey(klass, key, obj)

    return obj


def writeGAEObject(obj, encoder=None):
    """
    The GAE Datastore creates new instances of objects for each get request.
    This is a problem for PyAMF as it uses the id(obj) of the object to do
    reference checking.

    We could just ignore the problem, but the objects are conceptually the
    same so the effort should be made to attempt to resolve references for a
    given object graph.

    We create a new map on the encoder context object which contains a dict of
    C{object.__class__: {key1: object1, key2: object2, .., keyn: objectn}}. We
    use the datastore key to do the reference checking.

    @since: 0.4.1
    """
    if not obj.is_saved():
        encoder.writeObject(obj)

        return

    context = encoder.context
    kls = obj.__class__
    s = obj.key()

    gae_objects = getGAEObjects(context)

    try:
        referenced_object = gae_objects.getClassKey(kls, s)
    except KeyError:
        referenced_object = obj
        gae_objects.addClassKey(kls, s, obj)

    encoder.writeObject(referenced_object)


# initialise the module here: hook into pyamf

pyamf.register_alias_type(DataStoreClassAlias, db.Model)
pyamf.add_type(db.Query, util.to_list)
pyamf.add_type(db.Model, writeGAEObject)

########NEW FILE########
__FILENAME__ = _sets
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Adapter for the stdlib C{sets} module.

@since: 0.4
"""

import sets

import pyamf
from pyamf.adapters import util


if hasattr(sets, 'ImmutableSet'):
    pyamf.add_type(sets.ImmutableSet, util.to_tuple)

if hasattr(sets, 'Set'):
    pyamf.add_type(sets.Set, util.to_tuple)

########NEW FILE########
__FILENAME__ = _sqlalchemy_orm
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
SQLAlchemy adapter module.

@see: U{SQLAlchemy homepage<http://www.sqlalchemy.org>}

@since: 0.4
"""

from sqlalchemy import orm, __version__

try:
    from sqlalchemy.orm import class_mapper
except ImportError:
    from sqlalchemy.orm.util import class_mapper

import pyamf

UnmappedInstanceError = None

try:
    class_mapper(dict)
except Exception, e:
    UnmappedInstanceError = e.__class__


class_checkers = []


class SaMappedClassAlias(pyamf.ClassAlias):
    KEY_ATTR = 'sa_key'
    LAZY_ATTR = 'sa_lazy'
    EXCLUDED_ATTRS = [
        '_entity_name', '_instance_key', '_sa_adapter', '_sa_appender',
        '_sa_class_manager', '_sa_initiator', '_sa_instance_state',
        '_sa_instrumented', '_sa_iterator', '_sa_remover', '_sa_session_id',
        '_state'
    ]

    STATE_ATTR = '_sa_instance_state'

    if __version__.startswith('0.4'):
        STATE_ATTR = '_state'

    def getCustomProperties(self):
        self.mapper = class_mapper(self.klass)
        self.exclude_attrs.update(self.EXCLUDED_ATTRS)

        self.properties = []

        for prop in self.mapper.iterate_properties:
            self.properties.append(prop.key)

        self.encodable_properties.update(self.properties)
        self.decodable_properties.update(self.properties)

        self.exclude_sa_key = self.KEY_ATTR in self.exclude_attrs
        self.exclude_sa_lazy = self.LAZY_ATTR in self.exclude_attrs

    def getEncodableAttributes(self, obj, **kwargs):
        """
        Returns a C{tuple} containing a dict of static and dynamic attributes
        for C{obj}.
        """
        attrs = pyamf.ClassAlias.getEncodableAttributes(self, obj, **kwargs)

        if not self.exclude_sa_key:
            # primary_key_from_instance actually changes obj.__dict__ if
            # primary key properties do not already exist in obj.__dict__
            attrs[self.KEY_ATTR] = self.mapper.primary_key_from_instance(obj)

        if not self.exclude_sa_lazy:
            lazy_attrs = []

            for attr in self.properties:
                if attr not in obj.__dict__:
                    lazy_attrs.append(attr)

            attrs[self.LAZY_ATTR] = lazy_attrs

        return attrs

    def getDecodableAttributes(self, obj, attrs, **kwargs):
        """
        """
        attrs = pyamf.ClassAlias.getDecodableAttributes(self, obj, attrs, **kwargs)

        # Delete lazy-loaded attrs.
        #
        # Doing it this way ensures that lazy-loaded attributes are not
        # attached to the object, even if there is a default value specified
        # in the __init__ method.
        #
        # This is the correct behavior, because SQLAlchemy ignores __init__.
        # So, an object retreived from a DB with SQLAlchemy will not have a
        # lazy-loaded value, even if __init__ specifies a default value.
        if self.LAZY_ATTR in attrs:
            obj_state = None

            if hasattr(orm.attributes, 'instance_state'):
                obj_state = orm.attributes.instance_state(obj)

            for lazy_attr in attrs[self.LAZY_ATTR]:
                if lazy_attr in obj.__dict__:
                    # Delete directly from the dict, so
                    # SA callbacks are not triggered.
                    del obj.__dict__[lazy_attr]

                # Delete from committed_state so SA thinks this attribute was
                # never modified.
                #
                # If the attribute was set in the __init__ method,
                # SA will think it is modified and will try to update
                # it in the database.
                if obj_state is not None:
                    if lazy_attr in obj_state.committed_state:
                        del obj_state.committed_state[lazy_attr]
                    if lazy_attr in obj_state.dict:
                        del obj_state.dict[lazy_attr]

                if lazy_attr in attrs:
                    del attrs[lazy_attr]

            del attrs[self.LAZY_ATTR]

        if self.KEY_ATTR in attrs:
            del attrs[self.KEY_ATTR]

        return attrs

    def createInstance(self, *args, **kwargs):
        self.compile()

        return self.mapper.class_manager.new_instance()


def is_class_sa_mapped(klass):
    """
    @rtype: C{bool}
    """
    if not isinstance(klass, type):
        klass = type(klass)

    for c in class_checkers:
        if c(klass):
            return False

    try:
        class_mapper(klass)
    except UnmappedInstanceError:
        return False

    return True

pyamf.register_alias_type(SaMappedClassAlias, is_class_sa_mapped)

########NEW FILE########
__FILENAME__ = _sqlalchemy_orm_collections
# Copyright (c) The PyAMF Project.
# See LICENSE for details.

"""
SQLAlchemy adapter module.

@see: U{SQLAlchemy homepage<http://www.sqlalchemy.org>}

@since: 0.4
"""

from sqlalchemy.orm import collections

import pyamf
from pyamf.adapters import util


pyamf.add_type(collections.InstrumentedList, util.to_list)
pyamf.add_type(collections.InstrumentedDict, util.to_dict)
pyamf.add_type(collections.InstrumentedSet, util.to_set)


if hasattr(collections, 'CollectionAdapter'):
    pyamf.add_type(collections.CollectionAdapter, util.to_list)

########NEW FILE########
__FILENAME__ = _weakref
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
C{weakref} support.

@since: 0.6.2
"""

import weakref

import pyamf
from pyamf.adapters import util



class Foo(object):
    pass


weakref_type = type(weakref.ref(Foo()))


def get_referent(reference, **kwargs):
    return reference()


pyamf.add_type(weakref_type, get_referent)


if hasattr(weakref, 'WeakValueDictionary'):
    pyamf.add_type(weakref.WeakValueDictionary, util.to_dict)


if hasattr(weakref, 'WeakSet'):
    pyamf.add_type(weakref.WeakSet, util.to_list)

########NEW FILE########
__FILENAME__ = alias
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Class alias base functionality.

@since: 0.6
"""

import inspect

import pyamf
from pyamf import python, util


class UnknownClassAlias(Exception):
    """
    Raised if the AMF stream specifies an Actionscript class that does not
    have a Python class alias.

    @see: L{register_class}
    """


class ClassAlias(object):
    """
    Class alias. Provides class/instance meta data to the En/Decoder to allow
    fine grain control and some performance increases.
    """

    def __init__(self, klass, alias=None, **kwargs):
        if not isinstance(klass, python.class_types):
            raise TypeError('klass must be a class type, got %r' % type(klass))

        self.checkClass(klass)

        self.klass = klass
        self.alias = alias

        if hasattr(self.alias, 'decode'):
            self.alias = self.alias.decode('utf-8')

        self.static_attrs = kwargs.pop('static_attrs', None)
        self.exclude_attrs = kwargs.pop('exclude_attrs', None)
        self.readonly_attrs = kwargs.pop('readonly_attrs', None)
        self.proxy_attrs = kwargs.pop('proxy_attrs', None)
        self.amf3 = kwargs.pop('amf3', None)
        self.external = kwargs.pop('external', None)
        self.dynamic = kwargs.pop('dynamic', None)
        self.synonym_attrs = kwargs.pop('synonym_attrs', {})

        self._compiled = False
        self.anonymous = False
        self.sealed = None
        self.bases = None

        if self.alias is None:
            self.anonymous = True
            # we don't set this to None because AMF3 untyped objects have a
            # class name of ''
            self.alias = ''
        else:
            if self.alias == '':
                raise ValueError('Cannot set class alias as \'\'')

        if not kwargs.pop('defer', False):
            self.compile()

        if kwargs:
            raise TypeError('Unexpected keyword arguments %r' % (kwargs,))

    def _checkExternal(self):
        k = self.klass

        if not hasattr(k, '__readamf__'):
            raise AttributeError("An externalised class was specified, but"
                " no __readamf__ attribute was found for %r" % (k,))

        if not hasattr(k, '__writeamf__'):
            raise AttributeError("An externalised class was specified, but"
                " no __writeamf__ attribute was found for %r" % (k,))

        if not hasattr(k.__readamf__, '__call__'):
            raise TypeError("%s.__readamf__ must be callable" % (k.__name__,))

        if not hasattr(k.__writeamf__, '__call__'):
            raise TypeError("%s.__writeamf__ must be callable" % (k.__name__,))

    def compile(self):
        """
        This compiles the alias into a form that can be of most benefit to the
        en/decoder.
        """
        if self._compiled:
            return

        self.decodable_properties = set()
        self.encodable_properties = set()
        self.inherited_dynamic = None
        self.inherited_sealed = None
        self.bases = []

        self.exclude_attrs = set(self.exclude_attrs or [])
        self.readonly_attrs = set(self.readonly_attrs or [])
        self.static_attrs = list(self.static_attrs or [])
        self.static_attrs_set = set(self.static_attrs)
        self.proxy_attrs = set(self.proxy_attrs or [])

        self.sealed = util.is_class_sealed(self.klass)

        if self.external:
            self._checkExternal()
            self._finalise_compile()

            # this class is external so no more compiling is necessary
            return

        if hasattr(self.klass, '__slots__'):
            self.decodable_properties.update(self.klass.__slots__)
            self.encodable_properties.update(self.klass.__slots__)

        for k, v in self.klass.__dict__.iteritems():
            if not isinstance(v, property):
                continue

            if v.fget:
                self.encodable_properties.update([k])

            if v.fset:
                self.decodable_properties.update([k])
            else:
                self.readonly_attrs.update([k])

        mro = inspect.getmro(self.klass)[1:]

        for c in mro:
            self._compile_base_class(c)

        self.getCustomProperties()

        self._finalise_compile()

    def _compile_base_class(self, klass):
        if klass is object:
            return

        try:
            alias = pyamf.get_class_alias(klass)
        except UnknownClassAlias:
            alias = pyamf.register_class(klass)

        alias.compile()

        self.bases.append((klass, alias))

        if alias.exclude_attrs:
            self.exclude_attrs.update(alias.exclude_attrs)

        if alias.readonly_attrs:
            self.readonly_attrs.update(alias.readonly_attrs)

        if alias.static_attrs:
            self.static_attrs_set.update(alias.static_attrs)

            for a in alias.static_attrs:
                if a not in self.static_attrs:
                    self.static_attrs.insert(0, a)

        if alias.proxy_attrs:
            self.proxy_attrs.update(alias.proxy_attrs)

        if alias.encodable_properties:
            self.encodable_properties.update(alias.encodable_properties)

        if alias.decodable_properties:
            self.decodable_properties.update(alias.decodable_properties)

        if self.amf3 is None and alias.amf3:
            self.amf3 = alias.amf3

        if self.dynamic is None and alias.dynamic is not None:
            self.inherited_dynamic = alias.dynamic

        if alias.sealed is not None:
            self.inherited_sealed = alias.sealed

        if alias.synonym_attrs:
            self.synonym_attrs, x = alias.synonym_attrs.copy(), self.synonym_attrs
            self.synonym_attrs.update(x)

    def _finalise_compile(self):
        if self.dynamic is None:
            self.dynamic = True

            if self.inherited_dynamic is not None:
                if self.inherited_dynamic is False and not self.sealed and self.inherited_sealed:
                    self.dynamic = True
                else:
                    self.dynamic = self.inherited_dynamic

        if self.sealed:
            self.dynamic = False

        if self.amf3 is None:
            self.amf3 = False

        if self.external is None:
            self.external = False

        if self.static_attrs:
            self.encodable_properties.update(self.static_attrs)
            self.decodable_properties.update(self.static_attrs)

        if self.static_attrs:
            if self.exclude_attrs:
                self.static_attrs_set.difference_update(self.exclude_attrs)

            for a in self.static_attrs_set:
                if a not in self.static_attrs:
                    self.static_attrs.remove(a)

        if not self.exclude_attrs:
            self.exclude_attrs = None
        else:
            self.encodable_properties.difference_update(self.exclude_attrs)
            self.decodable_properties.difference_update(self.exclude_attrs)

        if self.exclude_attrs is not None:
            self.exclude_attrs = list(self.exclude_attrs)
            self.exclude_attrs.sort()

        if not self.readonly_attrs:
            self.readonly_attrs = None
        else:
            self.decodable_properties.difference_update(self.readonly_attrs)

        if self.readonly_attrs is not None:
            self.readonly_attrs = list(self.readonly_attrs)
            self.readonly_attrs.sort()

        if not self.proxy_attrs:
            self.proxy_attrs = None
        else:
            self.proxy_attrs = list(self.proxy_attrs)
            self.proxy_attrs.sort()

        if len(self.decodable_properties) == 0:
            self.decodable_properties = None
        else:
            self.decodable_properties = list(self.decodable_properties)
            self.decodable_properties.sort()

        if len(self.encodable_properties) == 0:
            self.encodable_properties = None
        else:
            self.encodable_properties = list(self.encodable_properties)
            self.encodable_properties.sort()

        self.non_static_encodable_properties = None

        if self.encodable_properties:
            self.non_static_encodable_properties = set(self.encodable_properties)

            if self.static_attrs:
                self.non_static_encodable_properties.difference_update(self.static_attrs)

        self.shortcut_encode = True
        self.shortcut_decode = True

        if (self.encodable_properties or self.static_attrs or
                self.exclude_attrs or self.proxy_attrs or self.external or
                self.synonym_attrs):
            self.shortcut_encode = False

        if (self.decodable_properties or self.static_attrs or
                self.exclude_attrs or self.readonly_attrs or
                not self.dynamic or self.external or self.synonym_attrs):
            self.shortcut_decode = False

        self.is_dict = False

        if issubclass(self.klass, dict) or self.klass is dict:
            self.is_dict = True

        self._compiled = True

    def is_compiled(self):
        return self._compiled

    def __str__(self):
        return self.alias

    def __repr__(self):
        k = self.__class__

        return '<%s.%s alias=%r class=%r @ 0x%x>' % (k.__module__, k.__name__,
            self.alias, self.klass, id(self))

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.alias == other
        elif isinstance(other, self.__class__):
            return self.klass == other.klass
        elif isinstance(other, python.class_types):
            return self.klass == other
        else:
            return False

    def __hash__(self):
        return id(self)

    def checkClass(self, klass):
        """
        This function is used to check if the class being aliased fits certain
        criteria. The default is to check that C{__new__} is available or the
        C{__init__} constructor does not need additional arguments. If this is
        the case then L{TypeError} will be raised.

        @since: 0.4
        """
        # Check for __new__ support.
        if hasattr(klass, '__new__') and hasattr(klass.__new__, '__call__'):
            # Should be good to go.
            return

        # Check that the constructor of the class doesn't require any additonal
        # arguments.
        if not (hasattr(klass, '__init__') and hasattr(klass.__init__, '__call__')):
            return

        klass_func = klass.__init__.im_func

        if not hasattr(klass_func, 'func_code'):
            # Can't examine it, assume it's OK.
            return

        if klass_func.func_defaults:
            available_arguments = len(klass_func.func_defaults) + 1
        else:
            available_arguments = 1

        needed_arguments = klass_func.func_code.co_argcount

        if available_arguments >= needed_arguments:
            # Looks good to me.
            return

        spec = inspect.getargspec(klass_func)

        raise TypeError("__init__ doesn't support additional arguments: %s"
            % inspect.formatargspec(*spec))

    def getEncodableAttributes(self, obj, codec=None):
        """
        Must return a C{dict} of attributes to be encoded, even if its empty.

        @param codec: An optional argument that will contain the encoder
            instance calling this function.
        @since: 0.5
        """
        if not self._compiled:
            self.compile()

        if self.is_dict:
            return dict(obj)

        if self.shortcut_encode and self.dynamic:
            return obj.__dict__.copy()

        attrs = {}

        if self.static_attrs:
            for attr in self.static_attrs:
                attrs[attr] = getattr(obj, attr, pyamf.Undefined)

        if not self.dynamic:
            if self.non_static_encodable_properties:
                for attr in self.non_static_encodable_properties:
                    attrs[attr] = getattr(obj, attr)

            return attrs

        dynamic_props = util.get_properties(obj)

        if not self.shortcut_encode:
            dynamic_props = set(dynamic_props)

            if self.encodable_properties:
                dynamic_props.update(self.encodable_properties)

            if self.static_attrs:
                dynamic_props.difference_update(self.static_attrs)

            if self.exclude_attrs:
                dynamic_props.difference_update(self.exclude_attrs)

        for attr in dynamic_props:
            attrs[attr] = getattr(obj, attr)

        if self.proxy_attrs is not None and attrs and codec:
            context = codec.context

            for k, v in attrs.copy().iteritems():
                if k in self.proxy_attrs:
                    attrs[k] = context.getProxyForObject(v)

        if self.synonym_attrs:
            missing = object()

            for k, v in self.synonym_attrs.iteritems():
                value = attrs.pop(k, missing)

                if value is missing:
                    continue

                attrs[v] = value

        return attrs

    def getDecodableAttributes(self, obj, attrs, codec=None):
        """
        Returns a dictionary of attributes for C{obj} that has been filtered,
        based on the supplied C{attrs}. This allows for fine grain control
        over what will finally end up on the object or not.

        @param obj: The object that will recieve the attributes.
        @param attrs: The C{attrs} dictionary that has been decoded.
        @param codec: An optional argument that will contain the decoder
            instance calling this function.
        @return: A dictionary of attributes that can be applied to C{obj}
        @since: 0.5
        """
        if not self._compiled:
            self.compile()

        changed = False

        props = set(attrs.keys())

        if self.static_attrs:
            missing_attrs = self.static_attrs_set.difference(props)

            if missing_attrs:
                raise AttributeError('Static attributes %r expected '
                    'when decoding %r' % (missing_attrs, self.klass))

            props.difference_update(self.static_attrs)

        if not props:
            return attrs

        if not self.dynamic:
            if not self.decodable_properties:
                props = set()
            else:
                props.intersection_update(self.decodable_properties)

            changed = True

        if self.readonly_attrs:
            props.difference_update(self.readonly_attrs)
            changed = True

        if self.exclude_attrs:
            props.difference_update(self.exclude_attrs)
            changed = True

        if self.proxy_attrs is not None and codec:
            context = codec.context

            for k in self.proxy_attrs:
                try:
                    v = attrs[k]
                except KeyError:
                    continue

                attrs[k] = context.getObjectForProxy(v)

        if self.synonym_attrs:
            missing = object()

            for k, v in self.synonym_attrs.iteritems():
                value = attrs.pop(k, missing)

                if value is missing:
                    continue

                attrs[v] = value

        if not changed:
            return attrs

        a = {}

        [a.__setitem__(p, attrs[p]) for p in props]

        return a

    def applyAttributes(self, obj, attrs, codec=None):
        """
        Applies the collection of attributes C{attrs} to aliased object C{obj}.
        Called when decoding reading aliased objects from an AMF byte stream.

        Override this to provide fine grain control of application of
        attributes to C{obj}.

        @param codec: An optional argument that will contain the en/decoder
            instance calling this function.
        """
        if not self._compiled:
            self.compile()

        if self.shortcut_decode:
            if self.is_dict:
                obj.update(attrs)

                return

            if not self.sealed:
                obj.__dict__.update(attrs)

                return

        else:
            attrs = self.getDecodableAttributes(obj, attrs, codec=codec)

        util.set_attrs(obj, attrs)

    def getCustomProperties(self):
        """
        Overrride this to provide known static properties based on the aliased
        class.

        @since: 0.5
        """

    def createInstance(self, codec=None):
        """
        Creates an instance of the klass.

        @return: Instance of C{self.klass}.
        """
        if type(self.klass) is type:
            return self.klass.__new__(self.klass)

        return self.klass()

########NEW FILE########
__FILENAME__ = amf0
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
AMF0 implementation.

C{AMF0} supports the basic data types used for the NetConnection, NetStream,
LocalConnection, SharedObjects and other classes in the Adobe Flash Player.

@since: 0.1
@see: U{Official AMF0 Specification in English (external)
    <http://opensource.adobe.com/wiki/download/attachments/1114283/amf0_spec_121207.pdf>}
@see: U{Official AMF0 Specification in Japanese (external)
    <http://opensource.adobe.com/wiki/download/attachments/1114283/JP_amf0_spec_121207.pdf>}
@see: U{AMF documentation on OSFlash (external)
    <http://osflash.org/documentation/amf>}
"""

import datetime

import pyamf
from pyamf import util, codec, xml, python


#: Represented as 9 bytes: 1 byte for C{0x00} and 8 bytes a double
#: representing the value of the number.
TYPE_NUMBER      = '\x00'
#: Represented as 2 bytes: 1 byte for C{0x01} and a second, C{0x00}
#: for C{False}, C{0x01} for C{True}.
TYPE_BOOL        = '\x01'
#: Represented as 3 bytes + len(String): 1 byte C{0x02}, then a UTF8 string,
#: including the top two bytes representing string length as a C{int}.
TYPE_STRING      = '\x02'
#: Represented as 1 byte, C{0x03}, then pairs of UTF8 string, the key, and
#: an AMF element, ended by three bytes, C{0x00} C{0x00} C{0x09}.
TYPE_OBJECT      = '\x03'
#: MovieClip does not seem to be supported by Remoting.
#: It may be used by other AMF clients such as SharedObjects.
TYPE_MOVIECLIP   = '\x04'
#: 1 single byte, C{0x05} indicates null.
TYPE_NULL        = '\x05'
#: 1 single byte, C{0x06} indicates null.
TYPE_UNDEFINED   = '\x06'
#: When an ActionScript object refers to itself, such C{this.self = this},
#: or when objects are repeated within the same scope (for example, as the
#: two parameters of the same function called), a code of C{0x07} and an
#: C{int}, the reference number, are written.
TYPE_REFERENCE   = '\x07'
#: A MixedArray is indicated by code C{0x08}, then a Long representing the
#: highest numeric index in the array, or 0 if there are none or they are
#: all negative. After that follow the elements in key : value pairs.
TYPE_MIXEDARRAY  = '\x08'
#: @see: L{TYPE_OBJECT}
TYPE_OBJECTTERM  = '\x09'
#: An array is indicated by C{0x0A}, then a Long for array length, then the
#: array elements themselves. Arrays are always sparse; values for
#: inexistant keys are set to null (C{0x06}) to maintain sparsity.
TYPE_ARRAY       = '\x0A'
#: Date is represented as C{0x0B}, then a double, then an C{int}. The double
#: represents the number of milliseconds since 01/01/1970. The C{int} represents
#: the timezone offset in minutes between GMT. Note for the latter than values
#: greater than 720 (12 hours) are represented as M{2^16} - the value. Thus GMT+1
#: is 60 while GMT-5 is 65236.
TYPE_DATE        = '\x0B'
#: LongString is reserved for strings larger then M{2^16} characters long. It
#: is represented as C{0x0C} then a LongUTF.
TYPE_LONGSTRING  = '\x0C'
#: Trying to send values which don't make sense, such as prototypes, functions,
#: built-in objects, etc. will be indicated by a single C{00x0D} byte.
TYPE_UNSUPPORTED = '\x0D'
#: Remoting Server -> Client only.
#: @see: L{RecordSet}
#: @see: U{RecordSet structure on OSFlash
#: <http://osflash.org/documentation/amf/recordset>}
TYPE_RECORDSET   = '\x0E'
#: The XML element is indicated by C{0x0F} and followed by a LongUTF containing
#: the string representation of the XML object. The receiving gateway may which
#: to wrap this string inside a language-specific standard XML object, or simply
#: pass as a string.
TYPE_XML         = '\x0F'
#: A typed object is indicated by C{0x10}, then a UTF string indicating class
#: name, and then the same structure as a normal C{0x03} Object. The receiving
#: gateway may use a mapping scheme, or send back as a vanilla object or
#: associative array.
TYPE_TYPEDOBJECT = '\x10'
#: An AMF message sent from an AVM+ client such as the Flash Player 9 may break
#: out into L{AMF3<pyamf.amf3>} mode. In this case the next byte will be the
#: AMF3 type code and the data will be in AMF3 format until the decoded object
#: reaches it's logical conclusion (for example, an object has no more keys).
TYPE_AMF3        = '\x11'


class Context(codec.Context):
    """
    """

    def clear(self):
        codec.Context.clear(self)

        encoder = self.extra.get('amf3_encoder', None)

        if encoder:
            encoder.context.clear()

        decoder = self.extra.get('amf3_decoder', None)

        if decoder:
            decoder.context.clear()

    def getAMF3Encoder(self, amf0_encoder):
        encoder = self.extra.get('amf3_encoder', None)

        if encoder:
            return encoder

        encoder = pyamf.get_encoder(pyamf.AMF3, stream=amf0_encoder.stream,
            timezone_offset=amf0_encoder.timezone_offset)
        self.extra['amf3_encoder'] = encoder

        return encoder

    def getAMF3Decoder(self, amf0_decoder):
        decoder = self.extra.get('amf3_decoder', None)

        if decoder:
            return decoder

        decoder = pyamf.get_decoder(pyamf.AMF3, stream=amf0_decoder.stream,
            timezone_offset=amf0_decoder.timezone_offset)
        self.extra['amf3_decoder'] = decoder

        return decoder

class Decoder(codec.Decoder):
    """
    Decodes an AMF0 stream.
    """

    def buildContext(self):
        return Context()

    def getTypeFunc(self, data):
        # great for coverage, sucks for readability
        if data == TYPE_NUMBER:
            return self.readNumber
        elif data == TYPE_BOOL:
            return self.readBoolean
        elif data == TYPE_STRING:
            return self.readString
        elif data == TYPE_OBJECT:
            return self.readObject
        elif data == TYPE_NULL:
            return self.readNull
        elif data == TYPE_UNDEFINED:
            return self.readUndefined
        elif data == TYPE_REFERENCE:
            return self.readReference
        elif data == TYPE_MIXEDARRAY:
            return self.readMixedArray
        elif data == TYPE_ARRAY:
            return self.readList
        elif data == TYPE_DATE:
            return self.readDate
        elif data == TYPE_LONGSTRING:
            return self.readLongString
        elif data == TYPE_UNSUPPORTED:
            return self.readNull
        elif data == TYPE_XML:
            return self.readXML
        elif data == TYPE_TYPEDOBJECT:
            return self.readTypedObject
        elif data == TYPE_AMF3:
            return self.readAMF3

    def readNumber(self):
        """
        Reads a ActionScript C{Number} value.

        In ActionScript 1 and 2 the C{NumberASTypes} type represents all numbers,
        both floats and integers.

        @rtype: C{int} or C{float}
        """
        return _check_for_int(self.stream.read_double())

    def readBoolean(self):
        """
        Reads a ActionScript C{Boolean} value.

        @rtype: C{bool}
        @return: Boolean.
        """
        return bool(self.stream.read_uchar())

    def readString(self, bytes=False):
        """
        Reads a C{string} from the stream. If bytes is C{True} then you will get
        the raw data read from the stream, otherwise a string that has been
        B{utf-8} decoded.
        """
        l = self.stream.read_ushort()
        b = self.stream.read(l)

        if bytes:
            return b

        return self.context.getStringForBytes(b)

    def readNull(self):
        """
        Reads a ActionScript C{null} value.
        """
        return None

    def readUndefined(self):
        """
        Reads an ActionScript C{undefined} value.

        @return: L{Undefined<pyamf.Undefined>}
        """
        return pyamf.Undefined

    def readMixedArray(self):
        """
        Read mixed array.

        @rtype: L{pyamf.MixedArray}
        """
        # TODO: something with the length/strict
        self.stream.read_ulong() # length

        obj = pyamf.MixedArray()
        self.context.addObject(obj)

        attrs = self.readObjectAttributes(obj)

        for key, value in attrs.iteritems():
            try:
                key = int(key)
            except ValueError:
                pass

            obj[key] = value

        return obj

    def readList(self):
        """
        Read a C{list} from the data stream.
        """
        obj = []
        self.context.addObject(obj)
        l = self.stream.read_ulong()

        for i in xrange(l):
            obj.append(self.readElement())

        return obj

    def readTypedObject(self):
        """
        Reads an aliased ActionScript object from the stream and attempts to
        'cast' it into a python class.

        @see: L{pyamf.register_class}
        """
        class_alias = self.readString()

        try:
            alias = self.context.getClassAlias(class_alias)
        except pyamf.UnknownClassAlias:
            if self.strict:
                raise

            alias = pyamf.TypedObjectClassAlias(class_alias)

        obj = alias.createInstance(codec=self)
        self.context.addObject(obj)

        attrs = self.readObjectAttributes(obj)
        alias.applyAttributes(obj, attrs, codec=self)

        return obj

    def readAMF3(self):
        """
        Read AMF3 elements from the data stream.

        @return: The AMF3 element read from the stream
        """
        return self.context.getAMF3Decoder(self).readElement()

    def readObjectAttributes(self, obj):
        obj_attrs = {}

        key = self.readString(True)

        while self.stream.peek() != TYPE_OBJECTTERM:
            obj_attrs[key] = self.readElement()
            key = self.readString(True)

        # discard the end marker (TYPE_OBJECTTERM)
        self.stream.read(1)

        return obj_attrs

    def readObject(self):
        """
        Reads an anonymous object from the data stream.

        @rtype: L{ASObject<pyamf.ASObject>}
        """
        obj = pyamf.ASObject()
        self.context.addObject(obj)

        obj.update(self.readObjectAttributes(obj))

        return obj

    def readReference(self):
        """
        Reads a reference from the data stream.

        @raise pyamf.ReferenceError: Unknown reference.
        """
        idx = self.stream.read_ushort()
        o = self.context.getObject(idx)

        if o is None:
            raise pyamf.ReferenceError('Unknown reference %d' % (idx,))

        return o

    def readDate(self):
        """
        Reads a UTC date from the data stream. Client and servers are
        responsible for applying their own timezones.

        Date: C{0x0B T7 T6} .. C{T0 Z1 Z2 T7} to C{T0} form a 64 bit
        Big Endian number that specifies the number of nanoseconds
        that have passed since 1/1/1970 0:00 to the specified time.
        This format is UTC 1970. C{Z1} and C{Z0} for a 16 bit Big
        Endian number indicating the indicated time's timezone in
        minutes.
        """
        ms = self.stream.read_double() / 1000.0
        self.stream.read_short() # tz

        # Timezones are ignored
        d = util.get_datetime(ms)

        if self.timezone_offset:
            d = d + self.timezone_offset

        self.context.addObject(d)

        return d

    def readLongString(self):
        """
        Read UTF8 string.
        """
        l = self.stream.read_ulong()

        bytes = self.stream.read(l)

        return self.context.getStringForBytes(bytes)

    def readXML(self):
        """
        Read XML.
        """
        data = self.readLongString()
        root = xml.fromstring(data)

        self.context.addObject(root)

        return root


class Encoder(codec.Encoder):
    """
    Encodes an AMF0 stream.

    @ivar use_amf3: A flag to determine whether this encoder should default to
        using AMF3. Defaults to C{False}
    @type use_amf3: C{bool}
    """

    def __init__(self, *args, **kwargs):
        codec.Encoder.__init__(self, *args, **kwargs)

        self.use_amf3 = kwargs.pop('use_amf3', False)

    def buildContext(self):
        return Context()

    def getTypeFunc(self, data):
        if self.use_amf3:
            return self.writeAMF3

        t = type(data)

        if t is pyamf.MixedArray:
            return self.writeMixedArray

        return codec.Encoder.getTypeFunc(self, data)

    def writeType(self, t):
        """
        Writes the type to the stream.

        @type   t: C{str}
        @param  t: ActionScript type.
        """
        self.stream.write(t)

    def writeUndefined(self, data):
        """
        Writes the L{undefined<TYPE_UNDEFINED>} data type to the stream.

        @param data: Ignored, here for the sake of interface.
        """
        self.writeType(TYPE_UNDEFINED)

    def writeNull(self, n):
        """
        Write null type to data stream.
        """
        self.writeType(TYPE_NULL)

    def writeList(self, a):
        """
        Write array to the stream.

        @param a: The array data to be encoded to the AMF0 data stream.
        """
        if self.writeReference(a) != -1:
            return

        self.context.addObject(a)

        self.writeType(TYPE_ARRAY)
        self.stream.write_ulong(len(a))

        for data in a:
            self.writeElement(data)

    def writeNumber(self, n):
        """
        Write number to the data stream .

        @param  n: The number data to be encoded to the AMF0 data stream.
        """
        self.writeType(TYPE_NUMBER)
        self.stream.write_double(float(n))

    def writeBoolean(self, b):
        """
        Write boolean to the data stream.

        @param b: The boolean data to be encoded to the AMF0 data stream.
        """
        self.writeType(TYPE_BOOL)

        if b:
            self.stream.write_uchar(1)
        else:
            self.stream.write_uchar(0)

    def serialiseString(self, s):
        """
        Similar to L{writeString} but does not encode a type byte.
        """
        if type(s) is unicode:
            s = self.context.getBytesForString(s)

        l = len(s)

        if l > 0xffff:
            self.stream.write_ulong(l)
        else:
            self.stream.write_ushort(l)

        self.stream.write(s)

    def writeBytes(self, s):
        """
        Write a string of bytes to the data stream.
        """
        l = len(s)

        if l > 0xffff:
            self.writeType(TYPE_LONGSTRING)
        else:
            self.writeType(TYPE_STRING)

        if l > 0xffff:
            self.stream.write_ulong(l)
        else:
            self.stream.write_ushort(l)

        self.stream.write(s)

    def writeString(self, u):
        """
        Write a unicode to the data stream.
        """
        s = self.context.getBytesForString(u)

        self.writeBytes(s)

    def writeReference(self, o):
        """
        Write reference to the data stream.

        @param o: The reference data to be encoded to the AMF0 datastream.
        """
        idx = self.context.getObjectReference(o)

        if idx == -1 or idx > 65535:
            return -1

        self.writeType(TYPE_REFERENCE)
        self.stream.write_ushort(idx)

        return idx

    def _writeDict(self, o):
        """
        Write C{dict} to the data stream.

        @param o: The C{dict} data to be encoded to the AMF0 data stream.
        """
        for key, val in o.iteritems():
            if type(key) in python.int_types:
                key = str(key)

            self.serialiseString(key)
            self.writeElement(val)

    def writeMixedArray(self, o):
        """
        Write mixed array to the data stream.

        @type o: L{pyamf.MixedArray}
        """
        if self.writeReference(o) != -1:
            return

        self.context.addObject(o)
        self.writeType(TYPE_MIXEDARRAY)

        # TODO: optimise this
        # work out the highest integer index
        try:
            # list comprehensions to save the day
            max_index = max([y[0] for y in o.items()
                if isinstance(y[0], (int, long))])

            if max_index < 0:
                max_index = 0
        except ValueError:
            max_index = 0

        self.stream.write_ulong(max_index)

        self._writeDict(o)
        self._writeEndObject()

    def _writeEndObject(self):
        self.stream.write('\x00\x00' + TYPE_OBJECTTERM)

    def writeObject(self, o):
        """
        Write a Python object to the stream.

        @param o: The object data to be encoded to the AMF0 data stream.
        """
        if self.writeReference(o) != -1:
            return

        self.context.addObject(o)
        alias = self.context.getClassAlias(o.__class__)

        alias.compile()

        if alias.amf3:
            self.writeAMF3(o)

            return

        if alias.anonymous:
            self.writeType(TYPE_OBJECT)
        else:
            self.writeType(TYPE_TYPEDOBJECT)
            self.serialiseString(alias.alias)

        attrs = alias.getEncodableAttributes(o, codec=self)

        if alias.static_attrs and attrs:
            for key in alias.static_attrs:
                value = attrs.pop(key)

                self.serialiseString(key)
                self.writeElement(value)

        if attrs:
            self._writeDict(attrs)

        self._writeEndObject()

    def writeDate(self, d):
        """
        Writes a date to the data stream.

        @type d: Instance of C{datetime.datetime}
        @param d: The date to be encoded to the AMF0 data stream.
        """
        if isinstance(d, datetime.time):
            raise pyamf.EncodeError('A datetime.time instance was found but '
                'AMF0 has no way to encode time objects. Please use '
                'datetime.datetime instead (got:%r)' % (d,))

        # According to the Red5 implementation of AMF0, dates references are
        # created, but not used.
        if self.timezone_offset is not None:
            d -= self.timezone_offset

        secs = util.get_timestamp(d)
        tz = 0

        self.writeType(TYPE_DATE)
        self.stream.write_double(secs * 1000.0)
        self.stream.write_short(tz)

    def writeXML(self, e):
        """
        Writes an XML instance.
        """
        self.writeType(TYPE_XML)

        data = xml.tostring(e)

        if isinstance(data, unicode):
            data = data.encode('utf-8')

        self.stream.write_ulong(len(data))
        self.stream.write(data)

    def writeAMF3(self, data):
        """
        Writes an element in L{AMF3<pyamf.amf3>} format.
        """
        self.writeType(TYPE_AMF3)

        self.context.getAMF3Encoder(self).writeElement(data)


class RecordSet(object):
    """
    I represent the C{RecordSet} class used in Adobe Flash Remoting to hold
    (amongst other things) SQL records.

    @ivar columns: The columns to send.
    @type columns: List of strings.
    @ivar items: The C{RecordSet} data.
    @type items: List of lists, the order of the data corresponds to the order
        of the columns.
    @ivar service: Service linked to the C{RecordSet}.
    @type service:
    @ivar id: The id of the C{RecordSet}.
    @type id: C{str}

    @see: U{RecordSet on OSFlash (external)
        <http://osflash.org/documentation/amf/recordset>}
    """

    class __amf__:
        alias = 'RecordSet'
        static = ('serverInfo',)
        dynamic = False

    def __init__(self, columns=[], items=[], service=None, id=None):
        self.columns = columns
        self.items = items
        self.service = service
        self.id = id

    def _get_server_info(self):
        ret = pyamf.ASObject(totalCount=len(self.items), cursor=1, version=1,
            initialData=self.items, columnNames=self.columns)

        if self.service is not None:
            ret.update({'serviceName': str(self.service['name'])})

        if self.id is not None:
            ret.update({'id':str(self.id)})

        return ret

    def _set_server_info(self, val):
        self.columns = val['columnNames']
        self.items = val['initialData']

        try:
            # TODO nick: find relevant service and link in here.
            self.service = dict(name=val['serviceName'])
        except KeyError:
            self.service = None

        try:
            self.id = val['id']
        except KeyError:
            self.id = None

    serverInfo = property(_get_server_info, _set_server_info)

    def __repr__(self):
        ret = '<%s.%s' % (self.__module__, self.__class__.__name__)

        if self.id is not None:
            ret += ' id=%s' % self.id

        if self.service is not None:
            ret += ' service=%s' % self.service

        ret += ' at 0x%x>' % id(self)

        return ret

pyamf.register_class(RecordSet)


def _check_for_int(x):
    """
    This is a compatibility function that takes a C{float} and converts it to an
    C{int} if the values are equal.
    """
    try:
        y = int(x)
    except (OverflowError, ValueError):
        pass
    else:
        # There is no way in AMF0 to distinguish between integers and floats
        if x == x and y == x:
            return y

    return x

########NEW FILE########
__FILENAME__ = amf3
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
AMF3 implementation.

C{AMF3} is the default serialization for
U{ActionScript<http://en.wikipedia.org/wiki/ActionScript>} 3.0 and provides
various advantages over L{AMF0<pyamf.amf0>}, which is used for ActionScript 1.0
and 2.0. It adds support for sending C{int} and C{uint} objects as integers and
supports data types that are available only in ActionScript 3.0, such as
L{ByteArray} and L{ArrayCollection}.

@see: U{Official AMF3 Specification in English
    <http://opensource.adobe.com/wiki/download/attachments/1114283/amf3_spec_05_05_08.pdf>}
@see: U{Official AMF3 Specification in Japanese
    <http://opensource.adobe.com/wiki/download/attachments/1114283/JP_amf3_spec_121207.pdf>}
@see: U{AMF3 documentation on OSFlash
    <http://osflash.org/documentation/amf3>}

@since: 0.1
"""

import datetime
import zlib

import pyamf
from pyamf import codec, util, xml, python


__all__ = [
    'ByteArray',
    'Context',
    'Encoder',
    'Decoder',
    'use_proxies_default',
]


#: If True encode/decode lists/tuples to L{ArrayCollection
#: <pyamf.flex.ArrayCollection>} and dicts to L{ObjectProxy
#: <pyamf.flex.ObjectProxy>}
use_proxies_default = False

#: The undefined type is represented by the undefined type marker. No further
#: information is encoded for this value.
TYPE_UNDEFINED = '\x00'
#: The null type is represented by the null type marker. No further
#: information is encoded for this value.
TYPE_NULL = '\x01'
#: The false type is represented by the false type marker and is used to
#: encode a Boolean value of C{false}. No further information is encoded for
#: this value.
TYPE_BOOL_FALSE = '\x02'
#: The true type is represented by the true type marker and is used to encode
#: a Boolean value of C{true}. No further information is encoded for this
#: value.
TYPE_BOOL_TRUE = '\x03'
#: In AMF 3 integers are serialized using a variable length signed 29-bit
#: integer.
#: @see: U{Parsing Integers on OSFlash (external)
#: <http://osflash.org/documentation/amf3/parsing_integers>}
TYPE_INTEGER = '\x04'
#: This type is used to encode an ActionScript Number or an ActionScript
#: C{int} of value greater than or equal to 2^28 or an ActionScript uint of
#: value greater than or equal to 2^29. The encoded value is is always an 8
#: byte IEEE-754 double precision floating point value in network byte order
#: (sign bit in low memory). The AMF 3 number type is encoded in the same
#: manner as the AMF 0 L{Number<pyamf.amf0.TYPE_NUMBER>} type.
TYPE_NUMBER = '\x05'
#: ActionScript String values are represented using a single string type in
#: AMF 3 - the concept of string and long string types from AMF 0 is not used.
#: Strings can be sent as a reference to a previously occurring String by
#: using an index to the implicit string reference table. Strings are encoding
#: using UTF-8 - however the header may either describe a string literal or a
#: string reference.
TYPE_STRING = '\x06'
#: ActionScript 3.0 introduced a new XML type however the legacy C{XMLDocument}
#: type from ActionScript 1.0 and 2.0.is retained in the language as
#: C{flash.xml.XMLDocument}. Similar to AMF 0, the structure of an
#: C{XMLDocument} needs to be flattened into a string representation for
#: serialization. As with other strings in AMF, the content is encoded in
#: UTF-8. XMLDocuments can be sent as a reference to a previously occurring
#: C{XMLDocument} instance by using an index to the implicit object reference
#: table.
#: @see: U{OSFlash documentation (external)
#: <http://osflash.org/documentation/amf3#x07_-_xml_legacy_flashxmlxmldocument_class>}
TYPE_XML = '\x07'
#: In AMF 3 an ActionScript Date is serialized as the number of
#: milliseconds elapsed since the epoch of midnight, 1st Jan 1970 in the
#: UTC time zone. Local time zone information is not sent.
TYPE_DATE = '\x08'
#: ActionScript Arrays are described based on the nature of their indices,
#: i.e. their type and how they are positioned in the Array.
TYPE_ARRAY = '\x09'
#: A single AMF 3 type handles ActionScript Objects and custom user classes.
TYPE_OBJECT = '\x0A'
#: ActionScript 3.0 introduces a new top-level XML class that supports
#: U{E4X<http://en.wikipedia.org/wiki/E4X>} syntax.
#: For serialization purposes the XML type needs to be flattened into a
#: string representation. As with other strings in AMF, the content is
#: encoded using UTF-8.
TYPE_XMLSTRING = '\x0B'
#: ActionScript 3.0 introduces the L{ByteArray} type to hold an Array
#: of bytes. AMF 3 serializes this type using a variable length encoding
#: 29-bit integer for the byte-length prefix followed by the raw bytes
#: of the L{ByteArray}.
#: @see: U{Parsing ByteArrays on OSFlash (external)
#: <http://osflash.org/documentation/amf3/parsing_byte_arrays>}
TYPE_BYTEARRAY = '\x0C'

#: Reference bit.
REFERENCE_BIT = 0x01

#: The maximum value for an int that will avoid promotion to an
#: ActionScript Number when sent via AMF 3 is represented by a
#: signed 29 bit integer: 2^28 - 1.
MAX_29B_INT = 0x0FFFFFFF

#: The minimum that can be represented by a signed 29 bit integer.
MIN_29B_INT = -0x10000000

ENCODED_INT_CACHE = {}


class ObjectEncoding:
    """
    AMF object encodings.
    """
    #: Property list encoding.
    #: The remaining integer-data represents the number of class members that
    #: exist. The property names are read as string-data. The values are then
    #: read as AMF3-data.
    STATIC = 0x00

    #: Externalizable object.
    #: What follows is the value of the "inner" object, including type code.
    #: This value appears for objects that implement IExternalizable, such as
    #: L{ArrayCollection} and L{ObjectProxy}.
    EXTERNAL = 0x01

    #: Name-value encoding.
    #: The property names and values are encoded as string-data followed by
    #: AMF3-data until there is an empty string property name. If there is a
    #: class-def reference there are no property names and the number of values
    #: is equal to the number of properties in the class-def.
    DYNAMIC = 0x02

    #: Proxy object.
    PROXY = 0x03


class DataOutput(object):
    """
    I am a C{StringIO} type object containing byte data from the AMF stream.
    I provide a set of methods for writing binary data with ActionScript 3.0.

    This class is the I/O counterpart to the L{DataInput} class, which reads
    binary data.

    @see: U{IDataOutput on Adobe Help (external)
    <http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/utils/IDataOutput.html>}
    """

    def __init__(self, encoder):
        """
        @param encoder: Encoder containing the stream.
        @type encoder: L{amf3.Encoder<pyamf.amf3.Encoder>}
        """
        self.encoder = encoder
        self.stream = encoder.stream

    def writeBoolean(self, value):
        """
        Writes a Boolean value.

        @type value: C{bool}
        @param value: A C{Boolean} value determining which byte is written.
        If the parameter is C{True}, C{1} is written; if C{False}, C{0} is
        written.

        @raise ValueError: Non-boolean value found.
        """
        if not isinstance(value, bool):
            raise ValueError("Non-boolean value found")

        if value is True:
            self.stream.write_uchar(1)
        else:
            self.stream.write_uchar(0)

    def writeByte(self, value):
        """
        Writes a byte.

        @type value: C{int}
        """
        self.stream.write_char(value)

    def writeUnsignedByte(self, value):
        """
        Writes an unsigned byte.

        @type value: C{int}
        @since: 0.5
        """
        return self.stream.write_uchar(value)

    def writeDouble(self, value):
        """
        Writes an IEEE 754 double-precision (64-bit) floating
        point number.

        @type value: C{number}
        """
        self.stream.write_double(value)

    def writeFloat(self, value):
        """
        Writes an IEEE 754 single-precision (32-bit) floating
        point number.

        @type value: C{float}
        """
        self.stream.write_float(value)

    def writeInt(self, value):
        """
        Writes a 32-bit signed integer.

        @type value: C{int}
        """
        self.stream.write_long(value)

    def writeMultiByte(self, value, charset):
        """
        Writes a multibyte string to the datastream using the
        specified character set.

        @type value: C{str}
        @param value: The string value to be written.
        @type charset: C{str}
        @param charset: The string denoting the character set to use. Possible
            character set strings include C{shift-jis}, C{cn-gb},
            C{iso-8859-1} and others.
        @see: U{Supported character sets on Adobe Help (external)
            <http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/charset-codes.html>}
        """
        if type(value) is unicode:
            value = value.encode(charset)

        self.stream.write(value)

    def writeObject(self, value):
        """
        Writes an object to data stream in AMF serialized format.

        @param value: The object to be serialized.
        """
        self.encoder.writeElement(value)

    def writeShort(self, value):
        """
        Writes a 16-bit integer.

        @type value: C{int}
        @param value: A byte value as an integer.
        """
        self.stream.write_short(value)

    def writeUnsignedShort(self, value):
        """
        Writes a 16-bit unsigned integer.

        @type value: C{int}
        @param value: A byte value as an integer.
        @since: 0.5
        """
        self.stream.write_ushort(value)

    def writeUnsignedInt(self, value):
        """
        Writes a 32-bit unsigned integer.

        @type value: C{int}
        @param value: A byte value as an unsigned integer.
        """
        self.stream.write_ulong(value)

    def writeUTF(self, value):
        """
        Writes a UTF-8 string to the data stream.

        The length of the UTF-8 string in bytes is written first,
        as a 16-bit integer, followed by the bytes representing the
        characters of the string.

        @type value: C{str}
        @param value: The string value to be written.
        """
        buf = util.BufferedByteStream()
        buf.write_utf8_string(value)
        bytes = buf.getvalue()

        self.stream.write_ushort(len(bytes))
        self.stream.write(bytes)

    def writeUTFBytes(self, value):
        """
        Writes a UTF-8 string. Similar to L{writeUTF}, but does
        not prefix the string with a 16-bit length word.

        @type value: C{str}
        @param value: The string value to be written.
        """
        val = None

        if isinstance(value, unicode):
            val = value
        else:
            val = unicode(value, 'utf8')

        self.stream.write_utf8_string(val)


class DataInput(object):
    """
    I provide a set of methods for reading binary data with ActionScript 3.0.

    This class is the I/O counterpart to the L{DataOutput} class, which writes
    binary data.

    @see: U{IDataInput on Adobe Help (external)
    <http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/utils/IDataInput.html>}
    """

    def __init__(self, decoder=None):
        """
        @param decoder: AMF3 decoder containing the stream.
        @type decoder: L{amf3.Decoder<pyamf.amf3.Decoder>}
        """
        self.decoder = decoder
        self.stream = decoder.stream

    def readBoolean(self):
        """
        Read C{Boolean}.

        @raise ValueError: Error reading Boolean.
        @rtype: C{bool}
        @return: A Boolean value, C{True} if the byte
        is nonzero, C{False} otherwise.
        """
        byte = self.stream.read(1)

        if byte == '\x00':
            return False
        elif byte == '\x01':
            return True
        else:
            raise ValueError("Error reading boolean")

    def readByte(self):
        """
        Reads a signed byte.

        @rtype: C{int}
        @return: The returned value is in the range -128 to 127.
        """
        return self.stream.read_char()

    def readDouble(self):
        """
        Reads an IEEE 754 double-precision floating point number from the
        data stream.

        @rtype: C{number}
        @return: An IEEE 754 double-precision floating point number.
        """
        return self.stream.read_double()

    def readFloat(self):
        """
        Reads an IEEE 754 single-precision floating point number from the
        data stream.

        @rtype: C{number}
        @return: An IEEE 754 single-precision floating point number.
        """
        return self.stream.read_float()

    def readInt(self):
        """
        Reads a signed 32-bit integer from the data stream.

        @rtype: C{int}
        @return: The returned value is in the range -2147483648 to 2147483647.
        """
        return self.stream.read_long()

    def readMultiByte(self, length, charset):
        """
        Reads a multibyte string of specified length from the data stream
        using the specified character set.

        @type length: C{int}
        @param length: The number of bytes from the data stream to read.
        @type charset: C{str}
        @param charset: The string denoting the character set to use.

        @rtype: C{str}
        @return: UTF-8 encoded string.
        """
        #FIXME nick: how to work out the code point byte size (on the fly)?
        bytes = self.stream.read(length)

        return unicode(bytes, charset)

    def readObject(self):
        """
        Reads an object from the data stream.

        @return: The deserialized object.
        """
        return self.decoder.readElement()

    def readShort(self):
        """
        Reads a signed 16-bit integer from the data stream.

        @rtype: C{uint}
        @return: The returned value is in the range -32768 to 32767.
        """
        return self.stream.read_short()

    def readUnsignedByte(self):
        """
        Reads an unsigned byte from the data stream.

        @rtype: C{uint}
        @return: The returned value is in the range 0 to 255.
        """
        return self.stream.read_uchar()

    def readUnsignedInt(self):
        """
        Reads an unsigned 32-bit integer from the data stream.

        @rtype: C{uint}
        @return: The returned value is in the range 0 to 4294967295.
        """
        return self.stream.read_ulong()

    def readUnsignedShort(self):
        """
        Reads an unsigned 16-bit integer from the data stream.

        @rtype: C{uint}
        @return: The returned value is in the range 0 to 65535.
        """
        return self.stream.read_ushort()

    def readUTF(self):
        """
        Reads a UTF-8 string from the data stream.

        The string is assumed to be prefixed with an unsigned
        short indicating the length in bytes.

        @rtype: C{str}
        @return: A UTF-8 string produced by the byte
        representation of characters.
        """
        length = self.stream.read_ushort()
        return self.stream.read_utf8_string(length)

    def readUTFBytes(self, length):
        """
        Reads a sequence of C{length} UTF-8 bytes from the data
        stream and returns a string.

        @type length: C{int}
        @param length: The number of bytes from the data stream to read.
        @rtype: C{str}
        @return: A UTF-8 string produced by the byte representation of
        characters of specified C{length}.
        """
        return self.readMultiByte(length, 'utf-8')


class ByteArray(util.BufferedByteStream, DataInput, DataOutput):
    """
    I am a C{StringIO} type object containing byte data from the AMF stream.
    ActionScript 3.0 introduced the C{flash.utils.ByteArray} class to support
    the manipulation of raw data in the form of an Array of bytes.

    Supports C{zlib} compression.

    Possible uses of the C{ByteArray} class:
     - Creating a custom protocol to connect to a client.
     - Writing your own AMF/Remoting packet.
     - Optimizing the size of your data by using custom data types.

    @see: U{ByteArray on Adobe Help (external)
    <http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/utils/ByteArray.html>}
    """

    _zlib_header = '\x78\x9c'

    class __amf__:
        amf3 = True

    def __init__(self, buf=None):
        self.context = Context()

        util.BufferedByteStream.__init__(self, buf)
        DataInput.__init__(self, Decoder(self, self.context))
        DataOutput.__init__(self, Encoder(self, self.context))

        self.compressed = self.peek(2) == ByteArray._zlib_header

    def readObject(self):
        self.context.clear()

        return super(ByteArray, self).readObject()

    def writeObject(self, obj):
        self.context.clear()

        return super(ByteArray, self).writeObject(obj)

    def __cmp__(self, other):
        if isinstance(other, ByteArray):
            return cmp(self.getvalue(), other.getvalue())

        return cmp(self.getvalue(), other)

    def __str__(self):
        buf = self.getvalue()

        if not self.compressed:
            return buf

        buf = zlib.compress(buf)
        #FIXME nick: hacked
        return buf[0] + '\xda' + buf[2:]

    def compress(self):
        """
        Forces compression of the underlying stream.
        """
        self.compressed = True


class ClassDefinition(object):
    """
    This is an internal class used by L{Encoder}/L{Decoder} to hold details
    about transient class trait definitions.
    """

    def __init__(self, alias):
        self.alias = alias
        self.reference = None

        alias.compile()

        self.attr_len = 0

        if alias.static_attrs:
            self.attr_len = len(alias.static_attrs)

        self.encoding = ObjectEncoding.DYNAMIC

        if alias.external:
            self.encoding = ObjectEncoding.EXTERNAL
        elif not alias.dynamic:
            if alias.encodable_properties is not None:
                if len(alias.static_attrs) == len(alias.encodable_properties):
                    self.encoding = ObjectEncoding.STATIC
            else:
                self.encoding = ObjectEncoding.STATIC

    def __repr__(self):
        return '<%s.ClassDefinition reference=%r encoding=%r alias=%r at 0x%x>' % (
            self.__class__.__module__, self.reference, self.encoding, self.alias, id(self))


class Context(codec.Context):
    """
    I hold the AMF3 context for en/decoding streams.

    @ivar strings: A list of string references.
    @type strings: C{list}
    @ivar classes: A list of L{ClassDefinition}.
    @type classes: C{list}
    """

    def __init__(self):
        self.strings = codec.IndexedCollection(use_hash=True)
        self.classes = {}
        self.class_ref = {}

        self.class_idx = 0

        codec.Context.__init__(self)

    def clear(self):
        """
        Clears the context.
        """
        codec.Context.clear(self)

        self.strings.clear()
        self.proxied_objects = {}
        self.classes = {}
        self.class_ref = {}

        self.class_idx = 0

    def getString(self, ref):
        """
        Gets a string based on a reference C{ref}.

        @param ref: The reference index.
        @type ref: C{str}

        @rtype: C{str} or C{None}
        @return: The referenced string.
        """
        return self.strings.getByReference(ref)

    def getStringReference(self, s):
        """
        Return string reference.

        @type s: C{str}
        @param s: The referenced string.
        @return: The reference index to the string.
        @rtype: C{int} or C{None}
        """
        return self.strings.getReferenceTo(s)

    def addString(self, s):
        """
        Creates a reference to C{s}. If the reference already exists, that
        reference is returned.

        @type s: C{str}
        @param s: The string to be referenced.
        @rtype: C{int}
        @return: The reference index.

        @raise TypeError: The parameter C{s} is not of C{basestring} type.
        """
        if not isinstance(s, basestring):
            raise TypeError

        if len(s) == 0:
            return -1

        return self.strings.append(s)

    def getClassByReference(self, ref):
        """
        Return class reference.

        @return: Class reference.
        """
        return self.class_ref.get(ref)

    def getClass(self, klass):
        """
        Returns a class reference.

        @return: Class reference.
        """
        return self.classes.get(klass)

    def addClass(self, alias, klass):
        """
        Creates a reference to C{class_def}.

        @param alias: C{ClassDefinition} instance.
        @type alias: C{ClassDefinition}
        """
        ref = self.class_idx

        self.class_ref[ref] = alias
        cd = self.classes[klass] = alias

        cd.reference = ref

        self.class_idx += 1

        return ref

    def getObjectForProxy(self, proxy):
        """
        Returns the unproxied version of C{proxy} as stored in the context, or
        unproxies the proxy and returns that 'raw' object.

        @see: L{pyamf.flex.unproxy_object}
        @since: 0.6
        """
        obj = self.proxied_objects.get(id(proxy))

        if obj is None:
            from pyamf import flex

            obj = flex.unproxy_object(proxy)

            self.addProxyObject(obj, proxy)

        return obj

    def addProxyObject(self, obj, proxied):
        """
        Stores a reference to the unproxied and proxied versions of C{obj} for
        later retrieval.

        @since: 0.6
        """
        self.proxied_objects[id(obj)] = proxied
        self.proxied_objects[id(proxied)] = obj

    def getProxyForObject(self, obj):
        """
        Returns the proxied version of C{obj} as stored in the context, or
        creates a new proxied object and returns that.

        @see: L{pyamf.flex.proxy_object}
        @since: 0.6
        """
        proxied = self.proxied_objects.get(id(obj))

        if proxied is None:
            from pyamf import flex

            proxied = flex.proxy_object(obj)

            self.addProxyObject(obj, proxied)

        return proxied


class Decoder(codec.Decoder):
    """
    Decodes an AMF3 data stream.
    """

    def __init__(self, *args, **kwargs):
        self.use_proxies = kwargs.pop('use_proxies', use_proxies_default)

        codec.Decoder.__init__(self, *args, **kwargs)

    def buildContext(self):
        return Context()

    def getTypeFunc(self, data):
        if data == TYPE_UNDEFINED:
            return self.readUndefined
        elif data == TYPE_NULL:
            return self.readNull
        elif data == TYPE_BOOL_FALSE:
            return self.readBoolFalse
        elif data == TYPE_BOOL_TRUE:
            return self.readBoolTrue
        elif data == TYPE_INTEGER:
            return self.readInteger
        elif data == TYPE_NUMBER:
            return self.readNumber
        elif data == TYPE_STRING:
            return self.readString
        elif data == TYPE_XML:
            return self.readXML
        elif data == TYPE_DATE:
            return self.readDate
        elif data == TYPE_ARRAY:
            return self.readArray
        elif data == TYPE_OBJECT:
            return self.readObject
        elif data == TYPE_XMLSTRING:
            return self.readXMLString
        elif data == TYPE_BYTEARRAY:
            return self.readByteArray

    def readProxy(self, obj):
        """
        Decodes a proxied object from the stream.

        @since: 0.6
        """
        return self.context.getObjectForProxy(obj)

    def readUndefined(self):
        """
        Read undefined.
        """
        return pyamf.Undefined

    def readNull(self):
        """
        Read null.

        @return: C{None}
        @rtype: C{None}
        """
        return None

    def readBoolFalse(self):
        """
        Returns C{False}.

        @return: C{False}
        @rtype: C{bool}
        """
        return False

    def readBoolTrue(self):
        """
        Returns C{True}.

        @return: C{True}
        @rtype: C{bool}
        """
        return True

    def readNumber(self):
        """
        Read number.
        """
        return self.stream.read_double()

    def readInteger(self, signed=True):
        """
        Reads and returns an integer from the stream.

        @type signed: C{bool}
        @see: U{Parsing integers on OSFlash
        <http://osflash.org/documentation/amf3/parsing_integers>} for the AMF3
        integer data format.
        """
        return decode_int(self.stream, signed)

    def _readLength(self):
        x = decode_int(self.stream, False)

        return (x >> 1, x & REFERENCE_BIT == 0)

    def readBytes(self):
        """
        Reads and returns a utf-8 encoded byte array.
        """
        length, is_reference = self._readLength()

        if is_reference:
            return self.context.getString(length)

        if length == 0:
            return ''

        result = self.stream.read(length)
        self.context.addString(result)

        return result

    def readString(self):
        """
        Reads and returns a string from the stream.
        """
        length, is_reference = self._readLength()

        if is_reference:
            result = self.context.getString(length)

            return self.context.getStringForBytes(result)

        if length == 0:
            return ''

        result = self.stream.read(length)
        self.context.addString(result)

        return self.context.getStringForBytes(result)

    def readDate(self):
        """
        Read date from the stream.

        The timezone is ignored as the date is always in UTC.
        """
        ref = self.readInteger(False)

        if ref & REFERENCE_BIT == 0:
            return self.context.getObject(ref >> 1)

        ms = self.stream.read_double()
        result = util.get_datetime(ms / 1000.0)

        if self.timezone_offset is not None:
            result += self.timezone_offset

        self.context.addObject(result)

        return result

    def readArray(self):
        """
        Reads an array from the stream.

        @warning: There is a very specific problem with AMF3 where the first
        three bytes of an encoded empty C{dict} will mirror that of an encoded
        C{{'': 1, '2': 2}}
        """
        size = self.readInteger(False)

        if size & REFERENCE_BIT == 0:
            return self.context.getObject(size >> 1)

        size >>= 1

        key = self.readBytes()

        if key == '':
            # integer indexes only -> python list
            result = []
            self.context.addObject(result)

            for i in xrange(size):
                result.append(self.readElement())

            return result

        result = pyamf.MixedArray()
        self.context.addObject(result)

        while key:
            result[key] = self.readElement()
            key = self.readBytes()

        for i in xrange(size):
            el = self.readElement()
            result[i] = el

        return result

    def _getClassDefinition(self, ref):
        """
        Reads class definition from the stream.
        """
        is_ref = ref & REFERENCE_BIT == 0
        ref >>= 1

        if is_ref:
            class_def = self.context.getClassByReference(ref)

            return class_def

        name = self.readBytes()
        alias = None

        if name == '':
            name = pyamf.ASObject

        try:
            alias = pyamf.get_class_alias(name)
        except pyamf.UnknownClassAlias:
            if self.strict:
                raise

            alias = pyamf.TypedObjectClassAlias(name)

        class_def = ClassDefinition(alias)

        class_def.encoding = ref & 0x03
        class_def.attr_len = ref >> 2
        class_def.static_properties = []

        if class_def.attr_len > 0:
            for i in xrange(class_def.attr_len):
                key = self.readBytes()

                class_def.static_properties.append(key)

        self.context.addClass(class_def, alias.klass)

        return class_def

    def _readStatic(self, class_def, obj):
        for attr in class_def.static_properties:
            obj[attr] = self.readElement()

    def _readDynamic(self, class_def, obj):
        attr = self.readBytes()

        while attr:
            obj[attr] = self.readElement()
            attr = self.readBytes()

    def readObject(self):
        """
        Reads an object from the stream.

        @raise ReferenceError: Unknown reference found.
        @raise DecodeError: Unknown object encoding detected.
        """
        ref = self.readInteger(False)

        if ref & REFERENCE_BIT == 0:
            obj = self.context.getObject(ref >> 1)

            if obj is None:
                raise pyamf.ReferenceError('Unknown reference %d' % (ref >> 1,))

            if self.use_proxies is True:
                obj = self.readProxy(obj)

            return obj

        ref >>= 1

        class_def = self._getClassDefinition(ref)
        alias = class_def.alias

        obj = alias.createInstance(codec=self)
        obj_attrs = dict()

        self.context.addObject(obj)

        if class_def.encoding in (ObjectEncoding.EXTERNAL, ObjectEncoding.PROXY):
            obj.__readamf__(DataInput(self))

            if self.use_proxies is True:
                obj = self.readProxy(obj)

            return obj
        elif class_def.encoding == ObjectEncoding.DYNAMIC:
            self._readStatic(class_def, obj_attrs)
            self._readDynamic(class_def, obj_attrs)
        elif class_def.encoding == ObjectEncoding.STATIC:
            self._readStatic(class_def, obj_attrs)
        else:
            raise pyamf.DecodeError("Unknown object encoding")

        alias.applyAttributes(obj, obj_attrs, codec=self)

        if self.use_proxies is True:
            obj = self.readProxy(obj)

        return obj

    def readXML(self):
        """
        Reads an xml object from the stream.

        @return: An etree interface compatible object
        @see: L{xml.set_default_interface}
        """
        ref = self.readInteger(False)

        if ref & REFERENCE_BIT == 0:
            return self.context.getObject(ref >> 1)

        xmlstring = self.stream.read(ref >> 1)

        x = xml.fromstring(xmlstring)
        self.context.addObject(x)

        return x

    def readXMLString(self):
        """
        Reads a string from the data stream and converts it into
        an XML Tree.

        @see: L{readXML}
        """
        return self.readXML()

    def readByteArray(self):
        """
        Reads a string of data from the stream.

        Detects if the L{ByteArray} was compressed using C{zlib}.

        @see: L{ByteArray}
        @note: This is not supported in ActionScript 1.0 and 2.0.
        """
        ref = self.readInteger(False)

        if ref & REFERENCE_BIT == 0:
            return self.context.getObject(ref >> 1)

        buffer = self.stream.read(ref >> 1)

        if buffer[0:2] == ByteArray._zlib_header:
            try:
                buffer = zlib.decompress(buffer)
            except zlib.error:
                pass

        obj = ByteArray(buffer)

        self.context.addObject(obj)

        return obj


class Encoder(codec.Encoder):
    """
    Encodes an AMF3 data stream.
    """

    def __init__(self, *args, **kwargs):
        self.use_proxies = kwargs.pop('use_proxies', use_proxies_default)
        self.string_references = kwargs.pop('string_references', True)

        codec.Encoder.__init__(self, *args, **kwargs)

    def buildContext(self):
        return Context()

    def getTypeFunc(self, data):
        """
        @see: L{codec.Encoder.getTypeFunc}
        """
        t = type(data)

        if t in python.int_types:
            return self.writeInteger
        elif t is ByteArray:
            return self.writeByteArray
        elif t is pyamf.MixedArray:
            return self.writeDict

        return codec.Encoder.getTypeFunc(self, data)

    def writeUndefined(self, n):
        """
        Writes an C{pyamf.Undefined} value to the stream.
        """
        self.stream.write(TYPE_UNDEFINED)

    def writeNull(self, n):
        """
        Writes a C{null} value to the stream.
        """
        self.stream.write(TYPE_NULL)

    def writeBoolean(self, n):
        """
        Writes a Boolean to the stream.
        """
        t = TYPE_BOOL_TRUE

        if n is False:
            t = TYPE_BOOL_FALSE

        self.stream.write(t)

    def _writeInteger(self, n):
        """
        AMF3 integers are encoded.

        @param n: The integer data to be encoded to the AMF3 data stream.
        @type n: integer data

        @see: U{Parsing Integers on OSFlash
        <http://osflash.org/documentation/amf3/parsing_integers>}
        for more info.
        """
        self.stream.write(encode_int(n))

    def writeInteger(self, n):
        """
        Writes an integer to the stream.

        @type   n: integer data
        @param  n: The integer data to be encoded to the AMF3 data stream.
        """
        if n < MIN_29B_INT or n > MAX_29B_INT:
            self.writeNumber(float(n))

            return

        self.stream.write(TYPE_INTEGER)
        self.stream.write(encode_int(n))

    def writeNumber(self, n):
        """
        Writes a float to the stream.

        @type n: C{float}
        """
        self.stream.write(TYPE_NUMBER)
        self.stream.write_double(n)

    def serialiseBytes(self, b):
        if len(b) == 0:
            self.stream.write_uchar(REFERENCE_BIT)

            return

        if self.string_references:
            ref = self.context.getStringReference(b)

            if ref != -1:
                self._writeInteger(ref << 1)

                return

            self.context.addString(b)

        self._writeInteger((len(b) << 1) | REFERENCE_BIT)
        self.stream.write(b)

    def serialiseString(self, s):
        """
        Writes a raw string to the stream.

        @type   s: C{str}
        @param  s: The string data to be encoded to the AMF3 data stream.
        """
        if type(s) is unicode:
            s = self.context.getBytesForString(s)

        self.serialiseBytes(s)

    def writeBytes(self, b):
        """
        Writes a raw string to the stream.
        """
        self.stream.write(TYPE_STRING)

        self.serialiseBytes(b)

    def writeString(self, s):
        """
        Writes a string to the stream. It will be B{UTF-8} encoded.
        """
        s = self.context.getBytesForString(s)

        self.writeBytes(s)

    def writeDate(self, n):
        """
        Writes a C{datetime} instance to the stream.

        Does not support C{datetime.time} instances because AMF3 has
        no way to encode time objects, so please use C{datetime.datetime}
        instead.

        @type n: L{datetime}
        @param n: The C{Date} data to be encoded to the AMF3 data stream.
        @raise EncodeError: A datetime.time instance was found
        """
        if isinstance(n, datetime.time):
            raise pyamf.EncodeError('A datetime.time instance was found but '
                'AMF3 has no way to encode time objects. Please use '
                'datetime.datetime instead (got:%r)' % (n,))

        self.stream.write(TYPE_DATE)

        ref = self.context.getObjectReference(n)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(n)

        self.stream.write_uchar(REFERENCE_BIT)

        if self.timezone_offset is not None:
            n -= self.timezone_offset

        ms = util.get_timestamp(n)
        self.stream.write_double(ms * 1000.0)

    def writeList(self, n, is_proxy=False):
        """
        Writes a C{tuple}, C{set} or C{list} to the stream.

        @type n: One of C{__builtin__.tuple}, C{__builtin__.set}
            or C{__builtin__.list}
        @param n: The C{list} data to be encoded to the AMF3 data stream.
        """
        if self.use_proxies and not is_proxy:
            self.writeProxy(n)

            return

        self.stream.write(TYPE_ARRAY)

        ref = self.context.getObjectReference(n)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(n)

        self._writeInteger((len(n) << 1) | REFERENCE_BIT)
        self.stream.write('\x01')

        [self.writeElement(x) for x in n]

    def writeDict(self, n):
        """
        Writes a C{dict} to the stream.

        @type n: C{__builtin__.dict}
        @param n: The C{dict} data to be encoded to the AMF3 data stream.
        @raise ValueError: Non C{int}/C{str} key value found in the C{dict}
        @raise EncodeError: C{dict} contains empty string keys.
        """
        # Design bug in AMF3 that cannot read/write empty key strings
        # for more info
        if '' in n:
            raise pyamf.EncodeError("dicts cannot contain empty string keys")

        if self.use_proxies:
            self.writeProxy(n)

            return

        self.stream.write(TYPE_ARRAY)

        ref = self.context.getObjectReference(n)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(n)

        # The AMF3 spec demands that all str based indicies be listed first
        keys = n.keys()
        int_keys = []
        str_keys = []

        for x in keys:
            if isinstance(x, python.int_types):
                int_keys.append(x)
            elif isinstance(x, python.str_types):
                str_keys.append(x)
            else:
                raise ValueError("Non int/str key value found in dict")

        # Make sure the integer keys are within range
        l = len(int_keys)

        for x in int_keys:
            if l < x <= 0:
                # treat as a string key
                str_keys.append(x)
                del int_keys[int_keys.index(x)]

        int_keys.sort()

        # If integer keys don't start at 0, they will be treated as strings
        if len(int_keys) > 0 and int_keys[0] != 0:
            for x in int_keys:
                str_keys.append(str(x))
                del int_keys[int_keys.index(x)]

        self._writeInteger(len(int_keys) << 1 | REFERENCE_BIT)

        for x in str_keys:
            self.serialiseString(x)
            self.writeElement(n[x])

        self.stream.write_uchar(0x01)

        for k in int_keys:
            self.writeElement(n[k])

    def writeProxy(self, obj):
        """
        Encodes a proxied object to the stream.

        @since: 0.6
        """
        proxy = self.context.getProxyForObject(obj)

        self.writeObject(proxy, is_proxy=True)

    def writeObject(self, obj, is_proxy=False):
        """
        Writes an object to the stream.
        """
        if self.use_proxies and not is_proxy:
            self.writeProxy(obj)

            return

        self.stream.write(TYPE_OBJECT)

        ref = self.context.getObjectReference(obj)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(obj)

        # object is not referenced, serialise it
        kls = obj.__class__
        definition = self.context.getClass(kls)
        alias = None
        class_ref = False # if the class definition is a reference

        if definition:
            class_ref = True
            alias = definition.alias
        else:
            alias = self.context.getClassAlias(kls)
            definition = ClassDefinition(alias)

            self.context.addClass(definition, alias.klass)

        if class_ref:
            self.stream.write(definition.reference)
        else:
            ref = 0

            if definition.encoding != ObjectEncoding.EXTERNAL:
                ref += definition.attr_len << 4

            final_reference = encode_int(ref | definition.encoding << 2 |
                REFERENCE_BIT << 1 | REFERENCE_BIT)

            self.stream.write(final_reference)

            definition.reference = encode_int(
                definition.reference << 2 | REFERENCE_BIT)

            if alias.anonymous:
                self.stream.write('\x01')
            else:
                self.serialiseString(alias.alias)

            # work out what the final reference for the class will be.
            # this is okay because the next time an object of the same
            # class is encoded, class_ref will be True and never get here
            # again.

        if alias.external:
            obj.__writeamf__(DataOutput(self))

            return

        attrs = alias.getEncodableAttributes(obj, codec=self)

        if alias.static_attrs:
            if not class_ref:
                [self.serialiseString(attr) for attr in alias.static_attrs]

            for attr in alias.static_attrs:
                value = attrs.pop(attr)

                self.writeElement(value)

            if definition.encoding == ObjectEncoding.STATIC:
                return

        if definition.encoding == ObjectEncoding.DYNAMIC:
            if attrs:
                for attr, value in attrs.iteritems():
                    if type(attr) in python.int_types:
                        attr = str(attr)

                    self.serialiseString(attr)
                    self.writeElement(value)

            self.stream.write('\x01')

    def writeByteArray(self, n):
        """
        Writes a L{ByteArray} to the data stream.

        @param n: The L{ByteArray} data to be encoded to the AMF3 data stream.
        @type n: L{ByteArray}
        """
        self.stream.write(TYPE_BYTEARRAY)

        ref = self.context.getObjectReference(n)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(n)

        buf = str(n)
        l = len(buf)
        self._writeInteger(l << 1 | REFERENCE_BIT)
        self.stream.write(buf)

    def writeXML(self, n):
        """
        Writes a XML string to the data stream.

        @type   n: L{ET<xml.ET>}
        @param  n: The XML Document to be encoded to the AMF3 data stream.
        """
        self.stream.write(TYPE_XMLSTRING)
        ref = self.context.getObjectReference(n)

        if ref != -1:
            self._writeInteger(ref << 1)

            return

        self.context.addObject(n)

        self.serialiseString(xml.tostring(n).encode('utf-8'))


def encode_int(n):
    """
    Encodes an int as a variable length signed 29-bit integer as defined by
    the spec.

    @param n: The integer to be encoded
    @return: The encoded string
    @rtype: C{str}
    @raise OverflowError: C{c} is out of range.
    """
    global ENCODED_INT_CACHE

    try:
        return ENCODED_INT_CACHE[n]
    except KeyError:
        pass

    if n < MIN_29B_INT or n > MAX_29B_INT:
        raise OverflowError("Out of range")

    if n < 0:
        n += 0x20000000

    bytes = ''
    real_value = None

    if n > 0x1fffff:
        real_value = n
        n >>= 1
        bytes += chr(0x80 | ((n >> 21) & 0xff))

    if n > 0x3fff:
        bytes += chr(0x80 | ((n >> 14) & 0xff))

    if n > 0x7f:
        bytes += chr(0x80 | ((n >> 7) & 0xff))

    if real_value is not None:
        n = real_value

    if n > 0x1fffff:
        bytes += chr(n & 0xff)
    else:
        bytes += chr(n & 0x7f)

    ENCODED_INT_CACHE[n] = bytes

    return bytes


def decode_int(stream, signed=False):
    """
    Decode C{int}.
    """
    n = result = 0
    b = stream.read_uchar()

    while b & 0x80 != 0 and n < 3:
        result <<= 7
        result |= b & 0x7f
        b = stream.read_uchar()
        n += 1

    if n < 3:
        result <<= 7
        result |= b
    else:
        result <<= 8
        result |= b

        if result & 0x10000000 != 0:
            if signed:
                result -= 0x20000000
            else:
                result <<= 1
                result += 1

    return result


pyamf.register_class(ByteArray)

########NEW FILE########
__FILENAME__ = codec
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Provides basic functionality for all pyamf.amf?.[De|E]ncoder classes.
"""

import types
import datetime

import pyamf
from pyamf import util, python, xml

__all__ = [
    'IndexedCollection',
    'Context',
    'Decoder',
    'Encoder'
]

try:
    unicode
except NameError:
    # py3k support
    unicode = str
    str = bytes


class IndexedCollection(object):
    """
    Store references to objects and provides an api to query references.

    All reference checks are done using the builtin C{id} function unless
    C{use_hash} is specified as C{True} where the slower but more flexible
    C{hash} builtin is used.

    @note: All attributes on the instance are private, use the apis only.
    """

    def __init__(self, use_hash=False):
        if use_hash is True:
            self.func = hash
        else:
            self.func = id

        self.clear()

    def clear(self):
        """
        Clears the collection.
        """
        self.list = []
        self.dict = {}

    def getByReference(self, ref):
        """
        Returns an object based on the supplied reference. The C{ref} should
        be an C{int}.

        If the reference is not found, C{None} will be returned.
        """
        try:
            return self.list[ref]
        except IndexError:
            return None

    def getReferenceTo(self, obj):
        """
        Returns a reference to C{obj} if it is contained within this index.

        If the object is not contained within the collection, C{-1} will be
        returned.

        @param obj: The object to find the reference to.
        @return: An C{int} representing the reference or C{-1} is the object
            is not contained within the collection.
        """
        return self.dict.get(self.func(obj), -1)

    def append(self, obj):
        """
        Appends C{obj} to this index.

        @note: Uniqueness is not checked
        @return: The reference to C{obj} in this index.
        """
        h = self.func(obj)

        self.list.append(obj)
        idx = len(self.list) - 1
        self.dict[h] = idx

        return idx

    def __eq__(self, other):
        if isinstance(other, list):
            return self.list == other

        raise NotImplementedError("cannot compare %s to %r" % (
            type(other), self))

    def __len__(self):
        return len(self.list)

    def __getitem__(self, idx):
        return self.getByReference(idx)

    def __contains__(self, obj):
        r = self.getReferenceTo(obj)

        return r != -1

    def __repr__(self):
        t = self.__class__

        return '<%s.%s size=%d 0x%x>' % (
            t.__module__,
            t.__name__,
            len(self.list),
            id(self))


class Context(object):
    """
    The base context for all AMF [de|en]coding.

    @ivar extra: The only public attribute. This is a placeholder for any extra
        contextual data that required for different adapters.
    @type extra: C{dict}
    @ivar _objects: A collection of stored references to objects that have
        already been visited by this context.
    @type _objects: L{IndexedCollection}
    @ivar _class_aliases: Lookup of C{class} -> L{pyamf.ClassAlias} as
        determined by L{pyamf.get_class_alias}
    @ivar _unicodes: Lookup of utf-8 encoded byte strings -> string objects
        (aka strings/unicodes).
    """

    def __init__(self):
        self._objects = IndexedCollection()

        self.clear()

    def clear(self):
        """
        Clears the context.
        """
        self._objects.clear()
        self._class_aliases = {}
        self._unicodes = {}
        self.extra = {}

    def getObject(self, ref):
        """
        Gets an object based on a reference.

        @type ref: C{int}
        @return: The referenced object or C{None} if not found.
        """
        return self._objects.getByReference(ref)

    def getObjectReference(self, obj):
        """
        Gets a reference for an already referenced object.

        @return: The reference to the object or C{-1} if the object is not in
            the context.
        """
        return self._objects.getReferenceTo(obj)

    def addObject(self, obj):
        """
        Adds a reference to C{obj}.

        @return: Reference to C{obj}.
        @rtype: C{int}
        """
        return self._objects.append(obj)

    def getClassAlias(self, klass):
        """
        Gets a class alias based on the supplied C{klass}. If one is not found
        in the global context, one is created locally.

        If you supply a string alias and the class is not registered,
        L{pyamf.UnknownClassAlias} will be raised.

        @param klass: A class object or string alias.
        @return: The L{pyamf.ClassAlias} instance that describes C{klass}
        """
        try:
            return self._class_aliases[klass]
        except KeyError:
            pass

        try:
            alias = self._class_aliases[klass] = pyamf.get_class_alias(klass)
        except pyamf.UnknownClassAlias:
            if isinstance(klass, python.str_types):
                raise

            # no alias has been found yet .. check subclasses
            alias = util.get_class_alias(klass) or pyamf.ClassAlias
            meta = util.get_class_meta(klass)
            alias = alias(klass, defer=True, **meta)

            self._class_aliases[klass] = alias

        return alias

    def getStringForBytes(self, s):
        """
        Returns the corresponding string for the supplied utf-8 encoded bytes.
        If there is no string object, one is created.

        @since: 0.6
        """
        h = hash(s)
        u = self._unicodes.get(h, None)

        if u is not None:
            return u

        u = self._unicodes[h] = s.decode('utf-8')

        return u

    def getBytesForString(self, u):
        """
        Returns the corresponding utf-8 encoded string for a given unicode
        object. If there is no string, one is encoded.

        @since: 0.6
        """
        h = hash(u)
        s = self._unicodes.get(h, None)

        if s is not None:
            return s

        s = self._unicodes[h] = u.encode('utf-8')

        return s


class _Codec(object):
    """
    Base codec.

    @ivar stream: The underlying data stream.
    @type stream: L{util.BufferedByteStream}
    @ivar context: The context for the encoding.
    @ivar strict: Whether the codec should operate in I{strict} mode.
    @type strict: C{bool}, default is C{False}.
    @ivar timezone_offset: The offset from I{UTC} for any C{datetime} objects
        being encoded. Default to C{None} means no offset.
    @type timezone_offset: C{datetime.timedelta} or C{int} or C{None}
    """

    def __init__(self, stream=None, context=None, strict=False,
                 timezone_offset=None):
        if isinstance(stream, basestring) or stream is None:
            stream = util.BufferedByteStream(stream)

        self.stream = stream
        self.context = context or self.buildContext()
        self.strict = strict
        self.timezone_offset = timezone_offset

        self._func_cache = {}

    def buildContext(self):
        """
        A context factory.
        """
        raise NotImplementedError

    def getTypeFunc(self, data):
        """
        Returns a callable based on C{data}. If no such callable can be found,
        the default must be to return C{None}.
        """
        raise NotImplementedError


class Decoder(_Codec):
    """
    Base AMF decoder.

    Supports an generator interface. Feed the decoder data using L{send} and get
    Python objects out by using L{next}.

    @ivar strict: Defines how strict the decoding should be. For the time
        being this relates to typed objects in the stream that do not have a
        registered alias. Introduced in 0.4.
    @type strict: C{bool}
    """

    def send(self, data):
        """
        Add data for the decoder to work on.
        """
        self.stream.append(data)

    def next(self):
        """
        Part of the iterator protocol.
        """
        try:
            return self.readElement()
        except pyamf.EOStream:
            # all data was successfully decoded from the stream
            raise StopIteration

    def readElement(self):
        """
        Reads an AMF3 element from the data stream.

        @raise DecodeError: The ActionScript type is unsupported.
        @raise EOStream: No more data left to decode.
        """
        pos = self.stream.tell()

        try:
            t = self.stream.read(1)
        except IOError:
            raise pyamf.EOStream

        try:
            func = self._func_cache[t]
        except KeyError:
            func = self.getTypeFunc(t)

            if not func:
                raise pyamf.DecodeError("Unsupported ActionScript type %s" % (
                    hex(ord(t)),))

            self._func_cache[t] = func

        try:
            return func()
        except IOError:
            self.stream.seek(pos)

            raise

    def __iter__(self):
        return self


class _CustomTypeFunc(object):
    """
    Support for custom type mappings when encoding.
    """

    def __init__(self, encoder, func):
        self.encoder = encoder
        self.func = func

    def __call__(self, data, **kwargs):
        ret = self.func(data, encoder=self.encoder)

        if ret is not None:
            self.encoder.writeElement(ret)


class Encoder(_Codec):
    """
    Base AMF encoder.

    When using this to encode arbitrary object, the only 'public' method is
    C{writeElement} all others are private and are subject to change in future
    versions.

    The encoder also supports an generator interface. Feed the encoder Python
    object using L{send} and get AMF bytes out using L{next}.
    """

    def __init__(self, *args, **kwargs):
        _Codec.__init__(self, *args, **kwargs)

        self.bucket = []

    def _write_type(self, obj, **kwargs):
        """
        Subclasses should override this and all write[type] functions
        """
        raise NotImplementedError

    writeNull = _write_type
    writeBytes = _write_type
    writeString = _write_type
    writeBoolean = _write_type
    writeNumber = _write_type
    writeList = _write_type
    writeUndefined = _write_type
    writeDate = _write_type
    writeXML = _write_type
    writeObject = _write_type

    def writeSequence(self, iterable):
        """
        Encodes an iterable. The default is to write If the iterable has an al
        """
        try:
            alias = self.context.getClassAlias(iterable.__class__)
        except (AttributeError, pyamf.UnknownClassAlias):
            self.writeList(list(iterable))

            return

        if alias.external:
            # a is a subclassed list with a registered alias - push to the
            # correct method
            self.writeObject(iterable)

            return

        self.writeList(list(iterable))

    def writeGenerator(self, gen):
        """
        Iterates over a generator object and encodes all that is returned.
        """
        n = getattr(gen, 'next')

        while True:
            try:
                self.writeElement(n())
            except StopIteration:
                break

    def getTypeFunc(self, data):
        """
        Returns a callable that will encode C{data} to C{self.stream}. If
        C{data} is unencodable, then C{None} is returned.
        """
        if data is None:
            return self.writeNull

        t = type(data)

        # try types that we know will work
        if t is str or issubclass(t, str):
            return self.writeBytes
        if t is unicode or issubclass(t, unicode):
            return self.writeString
        elif t is bool:
            return self.writeBoolean
        elif t is float:
            return self.writeNumber
        elif t in python.int_types:
            return self.writeNumber
        elif t in (list, tuple):
            return self.writeList
        elif t is types.GeneratorType:
            return self.writeGenerator
        elif t is pyamf.UndefinedType:
            return self.writeUndefined
        elif t in (datetime.date, datetime.datetime, datetime.time):
            return self.writeDate
        elif xml.is_xml(data):
            return self.writeXML

        # check for any overridden types
        for type_, func in pyamf.TYPE_MAP.iteritems():
            try:
                if isinstance(data, type_):
                    return _CustomTypeFunc(self, func)
            except TypeError:
                if python.callable(type_) and type_(data):
                    return _CustomTypeFunc(self, func)

        if isinstance(data, (list, tuple)):
            return self.writeSequence

        # now try some types that won't encode
        if t in python.class_types:
            # can't encode classes
            return None
        elif isinstance(data, python.func_types):
            # can't encode code objects
            return None
        elif isinstance(t, types.ModuleType):
            # cannot encode module objects
            return None

        # well, we tried ..
        return self.writeObject

    def writeElement(self, data):
        """
        Encodes C{data} to AMF. If the data is not able to be matched to an AMF
        type, then L{pyamf.EncodeError} will be raised.
        """
        key = type(data)
        func = None

        try:
            func = self._func_cache[key]
        except KeyError:
            func = self.getTypeFunc(data)

            if func is None:
                raise pyamf.EncodeError('Unable to encode %r (type %r)' % (
                    data, key))

            self._func_cache[key] = func

        func(data)

    def send(self, element):
        self.bucket.append(element)

    def next(self):
        try:
            element = self.bucket.pop(0)
        except IndexError:
            raise StopIteration

        start_pos = self.stream.tell()

        self.writeElement(element)

        end_pos = self.stream.tell()

        self.stream.seek(start_pos)

        return self.stream.read(end_pos - start_pos)

    def __iter__(self):
        return self

########NEW FILE########
__FILENAME__ = data
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Flex Data Management Service implementation.

This module contains the message classes used with Flex Data Management
Service.

@since: 0.1.0
"""

import pyamf
from pyamf.flex.messaging import AsyncMessage, AcknowledgeMessage, ErrorMessage

#: Namespace for C{flex.data} messages.
NAMESPACE = 'flex.data.messages'


__all__ = [
    'DataMessage',
    'SequencedMessage',
    'PagedMessage',
    'DataErrorMessage'
]


class DataMessage(AsyncMessage):
    """
    I am used to transport an operation that occured on a managed object
    or collection.

    This class of message is transmitted between clients subscribed to a
    remote destination as well as between server nodes within a cluster.
    The payload of this message describes all of the relevant details of
    the operation. This information is used to replicate updates and detect
    conflicts.

    @see: U{DataMessage on Livedocs<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/data/messages/DataMessage.html>}
    """

    def __init__(self):
        AsyncMessage.__init__(self)
        #: Provides access to the identity map which defines the
        #: unique identity of the item affected by this DataMessage
        #: (relevant for create/update/delete but not fill operations).
        self.identity = None
        #: Provides access to the operation/command of this DataMessage.
        #:
        #: Operations indicate how the remote destination should process
        #: this message.
        self.operation = None


class SequencedMessage(AcknowledgeMessage):
    """
    Response to L{DataMessage} requests.

    @see: U{SequencedMessage on Livedocs<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/data/messages/SequencedMessage.html>}
    """

    def __init__(self):
        AcknowledgeMessage.__init__(self)
        #: Provides access to the sequence id for this message.
        #:
        #: The sequence id is a unique identifier for a sequence
        #: within a remote destination. This value is only unique for
        #: the endpoint and destination contacted.
        self.sequenceId = None
        #:
        self.sequenceProxies = None
        #: Provides access to the sequence size for this message.
        #:
        #: The sequence size indicates how many items reside in the
        #: remote sequence.
        self.sequenceSize = None
        #:
        self.dataMessage = None


class PagedMessage(SequencedMessage):
    """
    This messsage provides information about a partial sequence result.

    @see: U{PagedMessage on Livedocs<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/data/messages/PagedMessage.html>}
    """

    def __init__(self):
        SequencedMessage.__init__(self)
        #: Provides access to the number of total pages in a sequence
        #: based on the current page size.
        self.pageCount = None
        #: Provides access to the index of the current page in a sequence.
        self.pageIndex = None


class DataErrorMessage(ErrorMessage):
    """
    Special cases of ErrorMessage will be sent when a data conflict
    occurs.

    This message provides the conflict information in addition to
    the L{ErrorMessage<pyamf.flex.messaging.ErrorMessage>} information.

    @see: U{DataErrorMessage on Livedocs<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/data/messages/DataErrorMessage.html>}
    """

    def __init__(self):
        ErrorMessage.__init__(self)
        #: The client oringinated message which caused the conflict.
        self.cause = None
        #: An array of properties that were found to be conflicting
        #: between the client and server objects.
        self.propertyNames = None
        #: The value that the server had for the object with the
        #: conflicting properties.
        self.serverObject = None


pyamf.register_package(globals(), NAMESPACE)

########NEW FILE########
__FILENAME__ = messaging
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Flex Messaging implementation.

This module contains the message classes used with Flex Data Services.

@see: U{RemoteObject on OSFlash (external)
<http://osflash.org/documentation/amf3#remoteobject>}

@since: 0.1
"""

import uuid

import pyamf.util
from pyamf import amf3


__all__ = [
    'RemotingMessage',
    'CommandMessage',
    'AcknowledgeMessage',
    'ErrorMessage',
    'AbstractMessage',
    'AsyncMessage'
]

NAMESPACE = 'flex.messaging.messages'

SMALL_FLAG_MORE = 0x80


class AbstractMessage(object):
    """
    Abstract base class for all Flex messages.

    Messages have two customizable sections; headers and data. The headers
    property provides access to specialized meta information for a specific
    message instance. The data property contains the instance specific data
    that needs to be delivered and processed by the decoder.

    @see: U{AbstractMessage on Livedocs<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/AbstractMessage.html>}

    @ivar body: Specific data that needs to be delivered to the remote
        destination.
    @type body: C{mixed}
    @ivar clientId: Indicates which client sent the message.
    @type clientId: C{str}
    @ivar destination: Message destination.
    @type destination: C{str}
    @ivar headers: Message headers. Core header names start with C{DS}.
    @type headers: C{dict}
    @ivar messageId: Unique Message ID.
    @type messageId: C{str}
    @ivar timeToLive: How long the message should be considered valid and
        deliverable.
    @type timeToLive: C{int}
    @ivar timestamp: Timestamp when the message was generated.
    @type timestamp: C{int}
    """

    class __amf__:
        amf3 = True
        static = ('body', 'clientId', 'destination', 'headers', 'messageId',
            'timestamp', 'timeToLive')

    #: Each message pushed from the server will contain this header identifying
    #: the client that will receive the message.
    DESTINATION_CLIENT_ID_HEADER = "DSDstClientId"
    #: Messages are tagged with the endpoint id for the channel they are sent
    #: over.
    ENDPOINT_HEADER = "DSEndpoint"
    #: Messages that need to set remote credentials for a destination carry the
    #: C{Base64} encoded credentials in this header.
    REMOTE_CREDENTIALS_HEADER = "DSRemoteCredentials"
    #: The request timeout value is set on outbound messages by services or
    #: channels and the value controls how long the responder will wait for an
    #: acknowledgement, result or fault response for the message before timing
    #: out the request.
    REQUEST_TIMEOUT_HEADER = "DSRequestTimeout"

    SMALL_ATTRIBUTE_FLAGS = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40]
    SMALL_ATTRIBUTES = dict(zip(
        SMALL_ATTRIBUTE_FLAGS,
        __amf__.static
    ))

    SMALL_UUID_FLAGS = [0x01, 0x02]
    SMALL_UUIDS = dict(zip(
        SMALL_UUID_FLAGS,
        ['clientId', 'messageId']
    ))

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)

        obj.__init__(*args, **kwargs)

        return obj

    def __init__(self, *args, **kwargs):
        self.body = kwargs.get('body', None)
        self.clientId = kwargs.get('clientId', None)
        self.destination = kwargs.get('destination', None)
        self.headers = kwargs.get('headers', {})
        self.messageId = kwargs.get('messageId', None)
        self.timestamp = kwargs.get('timestamp', None)
        self.timeToLive = kwargs.get('timeToLive', None)

    def __repr__(self):
        m = '<%s ' % self.__class__.__name__

        for k in self.__dict__:
            m += ' %s=%r' % (k, getattr(self, k))

        return m + " />"

    def decodeSmallAttribute(self, attr, input):
        """
        @since: 0.5
        """
        obj = input.readObject()

        if attr in ['timestamp', 'timeToLive']:
            return pyamf.util.get_datetime(obj / 1000.0)

        return obj

    def encodeSmallAttribute(self, attr):
        """
        @since: 0.5
        """
        obj = getattr(self, attr)

        if not obj:
            return obj

        if attr in ['timestamp', 'timeToLive']:
            return pyamf.util.get_timestamp(obj) * 1000.0
        elif attr in ['clientId', 'messageId']:
            if isinstance(obj, uuid.UUID):
                return None

        return obj

    def __readamf__(self, input):
        flags = read_flags(input)

        if len(flags) > 2:
            raise pyamf.DecodeError('Expected <=2 (got %d) flags for the '
                'AbstractMessage portion of the small message for %r' % (
                    len(flags), self.__class__))

        for index, byte in enumerate(flags):
            if index == 0:
                for flag in self.SMALL_ATTRIBUTE_FLAGS:
                    if flag & byte:
                        attr = self.SMALL_ATTRIBUTES[flag]
                        setattr(self, attr, self.decodeSmallAttribute(attr, input))
            elif index == 1:
                for flag in self.SMALL_UUID_FLAGS:
                    if flag & byte:
                        attr = self.SMALL_UUIDS[flag]
                        setattr(self, attr, decode_uuid(input.readObject()))

    def __writeamf__(self, output):
        flag_attrs = []
        uuid_attrs = []
        byte = 0

        for flag in self.SMALL_ATTRIBUTE_FLAGS:
            value = self.encodeSmallAttribute(self.SMALL_ATTRIBUTES[flag])

            if value:
                byte |= flag
                flag_attrs.append(value)

        flags = byte
        byte = 0

        for flag in self.SMALL_UUID_FLAGS:
            attr = self.SMALL_UUIDS[flag]
            value = getattr(self, attr)

            if not value:
                continue

            byte |= flag
            uuid_attrs.append(amf3.ByteArray(value.bytes))

        if not byte:
            output.writeUnsignedByte(flags)
        else:
            output.writeUnsignedByte(flags | SMALL_FLAG_MORE)
            output.writeUnsignedByte(byte)

        [output.writeObject(attr) for attr in flag_attrs]
        [output.writeObject(attr) for attr in uuid_attrs]

    def getSmallMessage(self):
        """
        Return a C{ISmallMessage} representation of this object. If one is not
        available, C{NotImplementedError} will be raised.

        @since: 0.5
        @see: U{ISmallMessage on Adobe Help (external)<http://
            help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/ISmallMessage.html>}
        """
        raise NotImplementedError


class AsyncMessage(AbstractMessage):
    """
    I am the base class for all asynchronous Flex messages.

    @see: U{AsyncMessage on Adobe Help<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/AsyncMessage.html>}

    @ivar correlationId: Correlation id of the message.
    @type correlationId: C{str}
    """

    #: Messages that were sent with a defined subtopic property indicate their
    #: target subtopic in this header.
    SUBTOPIC_HEADER = "DSSubtopic"

    class __amf__:
        static = ('correlationId',)

    def __init__(self, *args, **kwargs):
        AbstractMessage.__init__(self, *args, **kwargs)

        self.correlationId = kwargs.get('correlationId', None)

    def __readamf__(self, input):
        AbstractMessage.__readamf__(self, input)

        flags = read_flags(input)

        if len(flags) > 1:
            raise pyamf.DecodeError('Expected <=1 (got %d) flags for the '
                'AsyncMessage portion of the small message for %r' % (
                    len(flags), self.__class__))

        byte = flags[0]

        if byte & 0x01:
            self.correlationId = input.readObject()

        if byte & 0x02:
            self.correlationId = decode_uuid(input.readObject())

    def __writeamf__(self, output):
        AbstractMessage.__writeamf__(self, output)

        if not isinstance(self.correlationId, uuid.UUID):
            output.writeUnsignedByte(0x01)
            output.writeObject(self.correlationId)
        else:
            output.writeUnsignedByte(0x02)
            output.writeObject(pyamf.amf3.ByteArray(self.correlationId.bytes))

    def getSmallMessage(self):
        """
        Return a C{ISmallMessage} representation of this async message.

        @since: 0.5
        """
        return AsyncMessageExt(**self.__dict__)


class AcknowledgeMessage(AsyncMessage):
    """
    I acknowledge the receipt of a message that was sent previously.

    Every message sent within the messaging system must receive an
    acknowledgement.

    @see: U{AcknowledgeMessage on Adobe Help (external)<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/AcknowledgeMessage.html>}
    """

    #: Used to indicate that the acknowledgement is for a message that
    #: generated an error.
    ERROR_HINT_HEADER = "DSErrorHint"

    def __readamf__(self, input):
        AsyncMessage.__readamf__(self, input)

        flags = read_flags(input)

        if len(flags) > 1:
            raise pyamf.DecodeError('Expected <=1 (got %d) flags for the '
                'AcknowledgeMessage portion of the small message for %r' % (
                    len(flags), self.__class__))

    def __writeamf__(self, output):
        AsyncMessage.__writeamf__(self, output)

        output.writeUnsignedByte(0)

    def getSmallMessage(self):
        """
        Return a C{ISmallMessage} representation of this acknowledge message.

        @since: 0.5
        """
        return AcknowledgeMessageExt(**self.__dict__)


class CommandMessage(AsyncMessage):
    """
    Provides a mechanism for sending commands related to publish/subscribe
    messaging, ping, and cluster operations.

    @see: U{CommandMessage on Adobe Help (external)<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/CommandMessage.html>}

    @ivar operation: The command
    @type operation: C{int}
    @ivar messageRefType: hmm, not sure about this one.
    @type messageRefType: C{str}
    """

    #: The server message type for authentication commands.
    AUTHENTICATION_MESSAGE_REF_TYPE = "flex.messaging.messages.AuthenticationMessage"
    #: This is used to test connectivity over the current channel to the remote
    #: endpoint.
    PING_OPERATION = 5
    #: This is used by a remote destination to sync missed or cached messages
    #: back to a client as a result of a client issued poll command.
    SYNC_OPERATION = 4
    #: This is used to request a list of failover endpoint URIs for the remote
    #: destination based on cluster membership.
    CLUSTER_REQUEST_OPERATION = 7
    #: This is used to send credentials to the endpoint so that the user can be
    #: logged in over the current channel. The credentials need to be C{Base64}
    #: encoded and stored in the body of the message.
    LOGIN_OPERATION = 8
    #: This is used to log the user out of the current channel, and will
    #: invalidate the server session if the channel is HTTP based.
    LOGOUT_OPERATION = 9
    #: This is used to poll a remote destination for pending, undelivered
    #: messages.
    POLL_OPERATION = 2
    #: Subscribe commands issued by a consumer pass the consumer's C{selector}
    #: expression in this header.
    SELECTOR_HEADER = "DSSelector"
    #: This is used to indicate that the client's session with a remote
    #: destination has timed out.
    SESSION_INVALIDATE_OPERATION = 10
    #: This is used to subscribe to a remote destination.
    SUBSCRIBE_OPERATION = 0
    #: This is the default operation for new L{CommandMessage} instances.
    UNKNOWN_OPERATION = 1000
    #: This is used to unsubscribe from a remote destination.
    UNSUBSCRIBE_OPERATION = 1
    #: This operation is used to indicate that a channel has disconnected.
    DISCONNECT_OPERATION = 12

    class __amf__:
        static = ('operation',)

    def __init__(self, *args, **kwargs):
        AsyncMessage.__init__(self, *args, **kwargs)

        self.operation = kwargs.get('operation', None)

    def __readamf__(self, input):
        AsyncMessage.__readamf__(self, input)

        flags = read_flags(input)

        if not flags:
            return

        if len(flags) > 1:
            raise pyamf.DecodeError('Expected <=1 (got %d) flags for the '
                'CommandMessage portion of the small message for %r' % (
                    len(flags), self.__class__))

        byte = flags[0]

        if byte & 0x01:
            self.operation = input.readObject()

    def __writeamf__(self, output):
        AsyncMessage.__writeamf__(self, output)

        if self.operation:
            output.writeUnsignedByte(0x01)
            output.writeObject(self.operation)
        else:
            output.writeUnsignedByte(0)

    def getSmallMessage(self):
        """
        Return a C{ISmallMessage} representation of this command message.

        @since: 0.5
        """
        return CommandMessageExt(**self.__dict__)


class ErrorMessage(AcknowledgeMessage):
    """
    I am the Flex error message to be returned to the client.

    This class is used to report errors within the messaging system.

    @see: U{ErrorMessage on Adobe Help (external)<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/ErrorMessage.html>}
    """

    #: If a message may not have been delivered, the faultCode will contain
    #: this constant.
    MESSAGE_DELIVERY_IN_DOUBT = "Client.Error.DeliveryInDoubt"
    #: Header name for the retryable hint header.
    #:
    #: This is used to indicate that the operation that generated the error may
    #: be retryable rather than fatal.
    RETRYABLE_HINT_HEADER = "DSRetryableErrorHint"

    class __amf__:
        static = ('extendedData', 'faultCode', 'faultDetail', 'faultString',
            'rootCause')

    def __init__(self, *args, **kwargs):
        AcknowledgeMessage.__init__(self, *args, **kwargs)
        #: Extended data that the remote destination has chosen to associate
        #: with this error to facilitate custom error processing on the client.
        self.extendedData = kwargs.get('extendedData', {})
        #: Fault code for the error.
        self.faultCode = kwargs.get('faultCode', None)
        #: Detailed description of what caused the error.
        self.faultDetail = kwargs.get('faultDetail', None)
        #: A simple description of the error.
        self.faultString = kwargs.get('faultString', None)
        #: Should a traceback exist for the error, this property contains the
        #: message.
        self.rootCause = kwargs.get('rootCause', {})

    def getSmallMessage(self):
        """
        Return a C{ISmallMessage} representation of this error message.

        @since: 0.5
        """
        raise NotImplementedError


class RemotingMessage(AbstractMessage):
    """
    I am used to send RPC requests to a remote endpoint.

    @see: U{RemotingMessage on Adobe Help (external)<http://
        help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/messaging/messages/RemotingMessage.html>}
    """

    class __amf__:
        static = ('operation', 'source')

    def __init__(self, *args, **kwargs):
        AbstractMessage.__init__(self, *args, **kwargs)
        #: Name of the remote method/operation that should be called.
        self.operation = kwargs.get('operation', None)
        #: Name of the service to be called including package name.
        #: This property is provided for backwards compatibility.
        self.source = kwargs.get('source', None)


class AcknowledgeMessageExt(AcknowledgeMessage):
    """
    An L{AcknowledgeMessage}, but implementing C{ISmallMessage}.

    @since: 0.5
    """

    class __amf__:
        external = True


class CommandMessageExt(CommandMessage):
    """
    A L{CommandMessage}, but implementing C{ISmallMessage}.

    @since: 0.5
    """

    class __amf__:
        external = True


class AsyncMessageExt(AsyncMessage):
    """
    A L{AsyncMessage}, but implementing C{ISmallMessage}.

    @since: 0.5
    """

    class __amf__:
        external = True


def read_flags(input):
    """
    @since: 0.5
    """
    flags = []

    done = False

    while not done:
        byte = input.readUnsignedByte()

        if not byte & SMALL_FLAG_MORE:
            done = True
        else:
            byte = byte ^ SMALL_FLAG_MORE

        flags.append(byte)

    return flags


def decode_uuid(obj):
    """
    Decode a L{ByteArray} contents to a C{uuid.UUID} instance.

    @since: 0.5
    """
    return uuid.UUID(bytes=str(obj))


pyamf.register_package(globals(), package=NAMESPACE)
pyamf.register_class(AcknowledgeMessageExt, 'DSK')
pyamf.register_class(CommandMessageExt, 'DSC')
pyamf.register_class(AsyncMessageExt, 'DSA')

########NEW FILE########
__FILENAME__ = python
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Python compatibility values and helpers.
"""

try:
    import __builtin__ as builtins
except ImportError:
    import builtins


import types

func_types = (
    types.BuiltinFunctionType, types.BuiltinMethodType, types.CodeType,
    types.FunctionType, types.GeneratorType, types.LambdaType, types.MethodType)
class_types = [type]
int_types = [int]
str_types = [str]

try:
    int_types.append(long)
except NameError:
    pass

try:
    str_types.append(unicode)
except NameError:
    pass

try:
    class_types.append(types.ClassType)
except:
    pass


int_types = tuple(int_types)
str_types = tuple(str_types)
class_types = tuple(class_types)

PosInf = 1e300000
NegInf = -1e300000
# we do this instead of float('nan') because windows throws a wobbler.
NaN = PosInf / PosInf


def isNaN(val):
    """
    @since: 0.5
    """
    return str(float(val)) == str(NaN)


def isPosInf(val):
    """
    @since: 0.5
    """
    return str(float(val)) == str(PosInf)


def isNegInf(val):
    """
    @since: 0.5
    """
    return str(float(val)) == str(NegInf)



try:
    callable = builtins.callable
except NameError:
    def callable(obj):
        """
        Compatibility function for Python 3.x
        """
        return hasattr(obj, '__call__')

########NEW FILE########
__FILENAME__ = amf0
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
AMF0 Remoting support.

@since: 0.1.0
"""

import traceback
import sys

from pyamf import remoting
from pyamf.remoting import gateway


class RequestProcessor(object):
    def __init__(self, gateway):
        self.gateway = gateway

    def authenticateRequest(self, request, service_request, *args, **kwargs):
        """
        Authenticates the request against the service.

        @param request: The AMF request
        @type request: L{Request<pyamf.remoting.Request>}
        """
        username = password = None

        if 'Credentials' in request.headers:
            cred = request.headers['Credentials']

            username = cred['userid']
            password = cred['password']

        return self.gateway.authenticateRequest(service_request, username,
            password, *args, **kwargs)

    def buildErrorResponse(self, request, error=None):
        """
        Builds an error response.

        @param request: The AMF request
        @type request: L{Request<pyamf.remoting.Request>}
        @return: The AMF response
        @rtype: L{Response<pyamf.remoting.Response>}
        """
        if error is not None:
            cls, e, tb = error
        else:
            cls, e, tb = sys.exc_info()

        return remoting.Response(build_fault(cls, e, tb, self.gateway.debug),
            status=remoting.STATUS_ERROR)

    def _getBody(self, request, response, service_request, **kwargs):
        if 'DescribeService' in request.headers:
            return service_request.service.description

        return self.gateway.callServiceRequest(service_request, *request.body,
            **kwargs)

    def __call__(self, request, *args, **kwargs):
        """
        Processes an AMF0 request.

        @param request: The request to be processed.
        @type request: L{Request<pyamf.remoting.Request>}

        @return: The response to the request.
        @rtype: L{Response<pyamf.remoting.Response>}
        """
        response = remoting.Response(None)

        try:
            service_request = self.gateway.getServiceRequest(request,
                request.target)
        except gateway.UnknownServiceError:
            return self.buildErrorResponse(request)

        # we have a valid service, now attempt authentication
        try:
            authd = self.authenticateRequest(request, service_request, *args,
                **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            return self.buildErrorResponse(request)

        if not authd:
            # authentication failed
            response.status = remoting.STATUS_ERROR
            response.body = remoting.ErrorFault(code='AuthenticationError',
                description='Authentication failed')

            return response

        # authentication succeeded, now fire the preprocessor (if there is one)
        try:
            self.gateway.preprocessRequest(service_request, *args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            return self.buildErrorResponse(request)

        try:
            response.body = self._getBody(request, response, service_request,
                *args, **kwargs)

            return response
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            return self.buildErrorResponse(request)


def build_fault(cls, e, tb, include_traceback=False):
    """
    Builds a L{ErrorFault<pyamf.remoting.ErrorFault>} object based on the last
    exception raised.

    If include_traceback is C{False} then the traceback will not be added to
    the L{remoting.ErrorFault}.
    """
    if hasattr(cls, '_amf_code'):
        code = cls._amf_code
    else:
        code = cls.__name__

    details = None

    if include_traceback:
        details = traceback.format_exception(cls, e, tb)

    return remoting.ErrorFault(code=code, description=unicode(e), details=details)

########NEW FILE########
__FILENAME__ = amf3
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
AMF3 RemoteObject support.

@see: U{RemoteObject on Adobe Help (external)
    <http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/rpc/remoting/RemoteObject.html>}

@since: 0.1
"""

import calendar
import time
import uuid
import sys

import pyamf.python
from pyamf import remoting
from pyamf.flex import messaging


class BaseServerError(pyamf.BaseError):
    """
    Base server error.
    """


class ServerCallFailed(BaseServerError):
    """
    A catchall error.
    """
    _amf_code = 'Server.Call.Failed'


def generate_random_id():
    return str(uuid.uuid4())


def generate_acknowledgement(request=None):
    ack = messaging.AcknowledgeMessage()

    ack.messageId = generate_random_id()
    ack.clientId = generate_random_id()
    ack.timestamp = calendar.timegm(time.gmtime())

    if request:
        ack.correlationId = request.messageId

    return ack


def generate_error(request, cls, e, tb, include_traceback=False):
    """
    Builds an L{ErrorMessage<pyamf.flex.messaging.ErrorMessage>} based on the
    last traceback and the request that was sent.
    """
    import traceback

    if hasattr(cls, '_amf_code'):
        code = cls._amf_code
    else:
        code = cls.__name__

    details = None
    rootCause = None

    if include_traceback:
        details = traceback.format_exception(cls, e, tb)
        rootCause = e

    faultDetail = None
    faultString = None

    if hasattr(e, 'message'):
        faultString = unicode(e.message)
    elif hasattr(e, 'args') and e.args:
        if isinstance(e.args[0], pyamf.python.str_types):
            faultString = unicode(e.args[0])

    if details:
        faultDetail = unicode(details)

    return messaging.ErrorMessage(
        messageId=generate_random_id(),
        clientId=generate_random_id(),
        timestamp=calendar.timegm(time.gmtime()),
        correlationId=request.messageId,
        faultCode=code,
        faultString=faultString,
        faultDetail=faultDetail,
        extendedData=details,
        rootCause=rootCause)


class RequestProcessor(object):
    def __init__(self, gateway):
        self.gateway = gateway

    def buildErrorResponse(self, request, error=None):
        """
        Builds an error response.

        @param request: The AMF request
        @type request: L{Request<pyamf.remoting.Request>}
        @return: The AMF response
        @rtype: L{Response<pyamf.remoting.Response>}
        """
        if error is not None:
            cls, e, tb = error
        else:
            cls, e, tb = sys.exc_info()

        return generate_error(request, cls, e, tb, self.gateway.debug)

    def _getBody(self, amf_request, ro_request, **kwargs):
        """
        @raise ServerCallFailed: Unknown request.
        """
        if isinstance(ro_request, messaging.CommandMessage):
            return self._processCommandMessage(amf_request, ro_request, **kwargs)
        elif isinstance(ro_request, messaging.RemotingMessage):
            return self._processRemotingMessage(amf_request, ro_request, **kwargs)
        elif isinstance(ro_request, messaging.AsyncMessage):
            return self._processAsyncMessage(amf_request, ro_request, **kwargs)
        else:
            raise ServerCallFailed("Unknown request: %s" % ro_request)

    def _processCommandMessage(self, amf_request, ro_request, **kwargs):
        """
        @raise ServerCallFailed: Unknown Command operation.
        @raise ServerCallFailed: Authorization is not supported in RemoteObject.
        """
        ro_response = generate_acknowledgement(ro_request)

        if ro_request.operation == messaging.CommandMessage.PING_OPERATION:
            ro_response.body = True

            return remoting.Response(ro_response)
        elif ro_request.operation == messaging.CommandMessage.LOGIN_OPERATION:
            raise ServerCallFailed("Authorization is not supported in RemoteObject")
        elif ro_request.operation == messaging.CommandMessage.DISCONNECT_OPERATION:
            return remoting.Response(ro_response)
        else:
            raise ServerCallFailed("Unknown Command operation %s" % ro_request.operation)

    def _processAsyncMessage(self, amf_request, ro_request, **kwargs):
        ro_response = generate_acknowledgement(ro_request)
        ro_response.body = True

        return remoting.Response(ro_response)

    def _processRemotingMessage(self, amf_request, ro_request, **kwargs):
        ro_response = generate_acknowledgement(ro_request)

        service_name = ro_request.operation

        if hasattr(ro_request, 'destination') and ro_request.destination:
            service_name = '%s.%s' % (ro_request.destination, service_name)

        service_request = self.gateway.getServiceRequest(amf_request,
                                                         service_name)

        # fire the preprocessor (if there is one)
        self.gateway.preprocessRequest(service_request, *ro_request.body,
                                       **kwargs)

        ro_response.body = self.gateway.callServiceRequest(service_request,
                                                *ro_request.body, **kwargs)

        return remoting.Response(ro_response)

    def __call__(self, amf_request, **kwargs):
        """
        Processes an AMF3 Remote Object request.

        @param amf_request: The request to be processed.
        @type amf_request: L{Request<pyamf.remoting.Request>}

        @return: The response to the request.
        @rtype: L{Response<pyamf.remoting.Response>}
        """
        ro_request = amf_request.body[0]

        try:
            return self._getBody(amf_request, ro_request, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            return remoting.Response(self.buildErrorResponse(ro_request),
                                     status=remoting.STATUS_ERROR)

########NEW FILE########
__FILENAME__ = django
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Gateway for the Django framework.

This gateway allows you to expose functions in Django to AMF clients and
servers.

@see: U{Django homepage<http://djangoproject.com>}
@since: 0.1.0
"""

django = __import__('django.http')
http = django.http
conf = __import__('django.conf')
conf = conf.conf

import pyamf
from pyamf import remoting
from pyamf.remoting import gateway

__all__ = ['DjangoGateway']


class DjangoGateway(gateway.BaseGateway):
    """
    An instance of this class is suitable as a Django view.

    An example usage would be through C{urlconf}::

        from django.conf.urls.defaults import *

        urlpatterns = patterns('',
            (r'^gateway/', 'yourproject.yourapp.gateway.gw_instance'),
        )

    where C{yourproject.yourapp.gateway.gw_instance} refers to an instance of
    this class.

    @ivar expose_request: The standard Django view always has the request
        object as the first parameter. To disable this functionality, set this
        to C{False}.
    """

    csrf_exempt = True

    def __init__(self, *args, **kwargs):
        kwargs['expose_request'] = kwargs.get('expose_request', True)

        try:
            tz = conf.settings.AMF_TIME_OFFSET
        except AttributeError:
            tz = None

        try:
            debug = conf.settings.DEBUG
        except AttributeError:
            debug = False

        kwargs['timezone_offset'] = kwargs.get('timezone_offset', tz)
        kwargs['debug'] = kwargs.get('debug', debug)

        gateway.BaseGateway.__init__(self, *args, **kwargs)

    def getResponse(self, http_request, request):
        """
        Processes the AMF request, returning an AMF response.

        @param http_request: The underlying HTTP Request.
        @type http_request: U{HTTPRequest<http://docs.djangoproject.com
            /en/dev/ref/request-response/#httprequest-objects>}
        @param request: The AMF Request.
        @type request: L{Envelope<pyamf.remoting.Envelope>}
        @rtype: L{Envelope<pyamf.remoting.Envelope>}
        """
        response = remoting.Envelope(request.amfVersion)

        for name, message in request:
            http_request.amf_request = message

            processor = self.getProcessor(message)
            response[name] = processor(message, http_request=http_request)

        return response

    def __call__(self, http_request):
        """
        Processes and dispatches the request.
        """
        if http_request.method != 'POST':
            return http.HttpResponseNotAllowed(['POST'])

        stream = None
        timezone_offset = self._get_timezone_offset()

        # Decode the request
        try:
            request = remoting.decode(http_request.raw_post_data,
                strict=self.strict, logger=self.logger,
                timezone_offset=timezone_offset)
        except AttributeError: # fix to make work with Django 1.6
            request = remoting.decode(http_request.body,
                strict=self.strict, logger=self.logger,
                timezone_offset=timezone_offset)
        except (pyamf.DecodeError, IOError):
            if self.logger:
                self.logger.exception('Error decoding AMF request')

            response = ("400 Bad Request\n\nThe request body was unable to "
                "be successfully decoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            # support for Django 0.96
            http_response = http.HttpResponse(mimetype='text/plain',
                content=response)

            http_response.status_code = 400

            return http_response
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Unexpected error decoding AMF request')

            response = ('500 Internal Server Error\n\n'
                'An unexpected error occurred.')

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            return http.HttpResponseServerError(mimetype='text/plain',
                content=response)

        if self.logger:
            self.logger.debug("AMF Request: %r" % request)

        # Process the request
        try:
            response = self.getResponse(http_request, request)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Error processing AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be successfully processed.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            return http.HttpResponseServerError(mimetype='text/plain',
                content=response)

        if self.logger:
            self.logger.debug("AMF Response: %r" % response)

        # Encode the response
        try:
            stream = remoting.encode(response, strict=self.strict,
                logger=self.logger, timezone_offset=timezone_offset)
        except:
            if self.logger:
                self.logger.exception('Error encoding AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be encoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            return http.HttpResponseServerError(
                mimetype='text/plain', content=response)

        buf = stream.getvalue()

        http_response = http.HttpResponse(mimetype=remoting.CONTENT_TYPE)
        http_response['Server'] = gateway.SERVER_NAME
        http_response['Content-Length'] = str(len(buf))

        http_response.write(buf)

        return http_response

########NEW FILE########
__FILENAME__ = google
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Gateway for Google App Engine.

This gateway allows you to expose functions in Google App Engine web
applications to AMF clients and servers.

@see: U{Google App Engine homepage
    <http://code.google.com/appengine/docs/python/overview.html>}
@since: 0.3.1
"""

import sys
import os.path

try:
    sys.path.remove(os.path.dirname(os.path.abspath(__file__)))
except ValueError:
    pass

google = __import__('google.appengine.ext.webapp')
webapp = google.appengine.ext.webapp

from pyamf import remoting, DecodeError
from pyamf.remoting import gateway

__all__ = ['WebAppGateway']


class WebAppGateway(webapp.RequestHandler, gateway.BaseGateway):
    """
    Google App Engine Remoting Gateway.
    """

    __name__ = None

    def __init__(self, *args, **kwargs):
        gateway.BaseGateway.__init__(self, *args, **kwargs)

    def getResponse(self, request):
        """
        Processes the AMF request, returning an AMF response.

        :param request: The AMF Request.
        :type request: :class:`Envelope<pyamf.remoting.Envelope>`
        :rtype: :class:`Envelope<pyamf.remoting.Envelope>`
        :return: The AMF Response.
        """
        response = remoting.Envelope(request.amfVersion)

        for name, message in request:
            self.request.amf_request = message

            processor = self.getProcessor(message)
            response[name] = processor(message, http_request=self.request)

        return response

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.headers['Server'] = gateway.SERVER_NAME
        self.error(405)
        self.response.out.write("405 Method Not Allowed\n\n"
            "To access this PyAMF gateway you must use POST requests "
            "(%s received)" % self.request.method)

    def post(self):
        body = self.request.body_file.read()
        stream = None
        timezone_offset = self._get_timezone_offset()

        # Decode the request
        try:
            request = remoting.decode(body, strict=self.strict,
                logger=self.logger, timezone_offset=timezone_offset)
        except (DecodeError, IOError):
            if self.logger:
                self.logger.exception('Error decoding AMF request')

            response = ("400 Bad Request\n\nThe request body was unable to "
                "be successfully decoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            self.error(400)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Server'] = gateway.SERVER_NAME
            self.response.out.write(response)

            return
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Unexpected error decoding AMF request')

            response = ('500 Internal Server Error\n\n'
                'An unexpected error occurred.')

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            self.error(500)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Server'] = gateway.SERVER_NAME
            self.response.out.write(response)

            return

        if self.logger:
            self.logger.debug("AMF Request: %r" % request)

        # Process the request
        try:
            response = self.getResponse(request)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Error processing AMF request')

            response = ("500 Internal Server Error\n\nThe request was " \
                "unable to be successfully processed.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            self.error(500)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Server'] = gateway.SERVER_NAME
            self.response.out.write(response)

            return

        if self.logger:
            self.logger.debug("AMF Response: %r" % response)

        # Encode the response
        try:
            stream = remoting.encode(response, strict=self.strict,
                logger=self.logger, timezone_offset=timezone_offset)
        except:
            if self.logger:
                self.logger.exception('Error encoding AMF request')

            response = ("500 Internal Server Error\n\nThe request was " \
                "unable to be encoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            self.error(500)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Server'] = gateway.SERVER_NAME
            self.response.out.write(response)

            return

        response = stream.getvalue()

        self.response.headers['Content-Type'] = remoting.CONTENT_TYPE
        self.response.headers['Content-Length'] = str(len(response))
        self.response.headers['Server'] = gateway.SERVER_NAME

        self.response.out.write(response)

    def __call__(self, *args, **kwargs):
        return self

########NEW FILE########
__FILENAME__ = twisted
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Twisted server implementation.

This gateway allows you to expose functions in Twisted to AMF clients and
servers.

@see: U{Twisted homepage<http://twistedmatrix.com>}
@since: 0.1.0
"""

import sys
import os.path

try:
    sys.path.remove('')
except ValueError:
    pass

try:
    sys.path.remove(os.path.dirname(os.path.abspath(__file__)))
except ValueError:
    pass

twisted = __import__('twisted')
__import__('twisted.internet.defer')
__import__('twisted.internet.threads')
__import__('twisted.web.resource')
__import__('twisted.web.server')

defer = twisted.internet.defer
threads = twisted.internet.threads
resource = twisted.web.resource
server = twisted.web.server

from pyamf import remoting
from pyamf.remoting import gateway, amf0, amf3

__all__ = ['TwistedGateway']


class AMF0RequestProcessor(amf0.RequestProcessor):
    """
    A Twisted friendly implementation of
    L{amf0.RequestProcessor<pyamf.remoting.amf0.RequestProcessor>}
    """

    def __call__(self, request, *args, **kwargs):
        """
        Calls the underlying service method.

        @return: A C{Deferred} that will contain the AMF L{Response}.
        @rtype: C{twisted.internet.defer.Deferred}
        """
        try:
            service_request = self.gateway.getServiceRequest(
                request, request.target)
        except gateway.UnknownServiceError:
            return defer.succeed(self.buildErrorResponse(request))

        response = remoting.Response(None)
        deferred_response = defer.Deferred()

        def eb(failure):
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.gateway.logger:
                self.gateway.logger.error(errMesg)
                self.gateway.logger.info(failure.getTraceback())

            deferred_response.callback(self.buildErrorResponse(
                request, (failure.type, failure.value, failure.tb)))

        def response_cb(result):
            if self.gateway.logger:
                self.gateway.logger.debug("AMF Response: %s" % (result,))

            response.body = result

            deferred_response.callback(response)

        def preprocess_cb(result):
            d = defer.maybeDeferred(self._getBody, request, response,
                service_request, **kwargs)

            d.addCallback(response_cb).addErrback(eb)

        def auth_cb(result):
            if result is not True:
                response.status = remoting.STATUS_ERROR
                response.body = remoting.ErrorFault(code='AuthenticationError',
                    description='Authentication failed')

                deferred_response.callback(response)

                return

            d = defer.maybeDeferred(self.gateway.preprocessRequest,
                service_request, *args, **kwargs)

            d.addCallback(preprocess_cb).addErrback(eb)

        # we have a valid service, now attempt authentication
        d = defer.maybeDeferred(self.authenticateRequest, request,
                                service_request, **kwargs)
        d.addCallback(auth_cb).addErrback(eb)

        return deferred_response


class AMF3RequestProcessor(amf3.RequestProcessor):
    """
    A Twisted friendly implementation of
    L{amf3.RequestProcessor<pyamf.remoting.amf3.RequestProcessor>}
    """

    def _processRemotingMessage(self, amf_request, ro_request, **kwargs):
        ro_response = amf3.generate_acknowledgement(ro_request)

        try:
            service_name = ro_request.operation

            if hasattr(ro_request, 'destination') and ro_request.destination:
                service_name = '%s.%s' % (ro_request.destination, service_name)

            service_request = self.gateway.getServiceRequest(amf_request,
                                                             service_name)
        except gateway.UnknownServiceError:
            return defer.succeed(remoting.Response(
                self.buildErrorResponse(ro_request),
                status=remoting.STATUS_ERROR))

        deferred_response = defer.Deferred()

        def eb(failure):
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.gateway.logger:
                self.gateway.logger.error(errMesg)
                self.gateway.logger.error(failure.getTraceback())

            ro_response = self.buildErrorResponse(ro_request, (failure.type,
                                                  failure.value, failure.tb))
            deferred_response.callback(remoting.Response(ro_response,
                                        status=remoting.STATUS_ERROR))

        def response_cb(result):
            ro_response.body = result
            res = remoting.Response(ro_response)

            if self.gateway.logger:
                self.gateway.logger.debug("AMF Response: %r" % (res,))

            deferred_response.callback(res)

        def process_cb(result):
            d = defer.maybeDeferred(self.gateway.callServiceRequest,
                                    service_request, *ro_request.body, **kwargs)
            d.addCallback(response_cb).addErrback(eb)

        d = defer.maybeDeferred(self.gateway.preprocessRequest, service_request,
                                *ro_request.body, **kwargs)
        d.addCallback(process_cb).addErrback(eb)

        return deferred_response

    def __call__(self, amf_request, **kwargs):
        """
        Calls the underlying service method.

        @return: A C{deferred} that will contain the AMF L{Response}.
        @rtype: C{Deferred<twisted.internet.defer.Deferred>}
        """
        deferred_response = defer.Deferred()
        ro_request = amf_request.body[0]

        def cb(amf_response):
            deferred_response.callback(amf_response)

        def eb(failure):
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.gateway.logger:
                self.gateway.logger.error(errMesg)
                self.gateway.logger.error(failure.getTraceback())

            deferred_response.callback(self.buildErrorResponse(ro_request,
                (failure.type, failure.value, failure.tb)))

        d = defer.maybeDeferred(self._getBody, amf_request, ro_request, **kwargs)
        d.addCallback(cb).addErrback(eb)

        return deferred_response


class TwistedGateway(gateway.BaseGateway, resource.Resource):
    """
    Twisted Remoting gateway for C{twisted.web}.

    @ivar expose_request: Forces the underlying HTTP request to be the first
        argument to any service call.
    @type expose_request: C{bool}
    """

    allowedMethods = ('POST',)

    def __init__(self, *args, **kwargs):
        if 'expose_request' not in kwargs:
            kwargs['expose_request'] = True

        gateway.BaseGateway.__init__(self, *args, **kwargs)
        resource.Resource.__init__(self)

    def _finaliseRequest(self, request, status, content, mimetype='text/plain'):
        """
        Finalises the request.

        @param request: The HTTP Request.
        @type request: C{http.Request}
        @param status: The HTTP status code.
        @type status: C{int}
        @param content: The content of the response.
        @type content: C{str}
        @param mimetype: The MIME type of the request.
        @type mimetype: C{str}
        """
        request.setResponseCode(status)

        request.setHeader("Content-Type", mimetype)
        request.setHeader("Content-Length", str(len(content)))
        request.setHeader("Server", gateway.SERVER_NAME)

        request.write(content)
        request.finish()

    def render_POST(self, request):
        """
        Read remoting request from the client.

        @type request: The HTTP Request.
        @param request: C{twisted.web.http.Request}
        """
        def handleDecodeError(failure):
            """
            Return HTTP 400 Bad Request.
            """
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.logger:
                self.logger.error(errMesg)
                self.logger.error(failure.getTraceback())

            body = "400 Bad Request\n\nThe request body was unable to " \
                "be successfully decoded."

            if self.debug:
                body += "\n\nTraceback:\n\n%s" % failure.getTraceback()

            self._finaliseRequest(request, 400, body)

        request.content.seek(0, 0)
        timezone_offset = self._get_timezone_offset()

        d = threads.deferToThread(remoting.decode, request.content.read(),
            strict=self.strict, logger=self.logger,
            timezone_offset=timezone_offset)

        def cb(amf_request):
            if self.logger:
                self.logger.debug("AMF Request: %r" % amf_request)

            x = self.getResponse(request, amf_request)

            x.addCallback(self.sendResponse, request)

        # Process the request
        d.addCallback(cb).addErrback(handleDecodeError)

        return server.NOT_DONE_YET

    def sendResponse(self, amf_response, request):
        def cb(result):
            self._finaliseRequest(request, 200, result.getvalue(),
                remoting.CONTENT_TYPE)

        def eb(failure):
            """
            Return 500 Internal Server Error.
            """
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.logger:
                self.logger.error(errMesg)
                self.logger.error(failure.getTraceback())

            body = "500 Internal Server Error\n\nThere was an error encoding " \
                "the response."

            if self.debug:
                body += "\n\nTraceback:\n\n%s" % failure.getTraceback()

            self._finaliseRequest(request, 500, body)

        timezone_offset = self._get_timezone_offset()
        d = threads.deferToThread(remoting.encode, amf_response,
            strict=self.strict, logger=self.logger,
            timezone_offset=timezone_offset)

        d.addCallback(cb).addErrback(eb)

    def getProcessor(self, request):
        """
        Determines the request processor, based on the request.

        @param request: The AMF message.
        @type request: L{Request<pyamf.remoting.Request>}
        """
        if request.target == 'null':
            return AMF3RequestProcessor(self)

        return AMF0RequestProcessor(self)

    def getResponse(self, http_request, amf_request):
        """
        Processes the AMF request, returning an AMF L{Response}.

        @param http_request: The underlying HTTP Request
        @type http_request: C{twisted.web.http.Request}
        @param amf_request: The AMF Request.
        @type amf_request: L{Envelope<pyamf.remoting.Envelope>}
        """
        response = remoting.Envelope(amf_request.amfVersion)
        dl = []

        def cb(body, name):
            response[name] = body

        for name, message in amf_request:
            processor = self.getProcessor(message)

            http_request.amf_request = message

            d = defer.maybeDeferred(
                processor, message, http_request=http_request)

            dl.append(d.addCallback(cb, name))

        def cb2(result):
            return response

        def eb(failure):
            """
            Return 500 Internal Server Error.
            """
            errMesg = "%s: %s" % (failure.type, failure.getErrorMessage())

            if self.logger:
                self.logger.error(errMesg)
                self.logger.error(failure.getTraceback())

            body = "500 Internal Server Error\n\nThe request was unable to " \
                "be successfully processed."

            if self.debug:
                body += "\n\nTraceback:\n\n%s" % failure.getTraceback()

            self._finaliseRequest(http_request, 500, body)

        d = defer.DeferredList(dl)

        return d.addCallback(cb2).addErrback(eb)

    def authenticateRequest(self, service_request, username, password, **kwargs):
        """
        Processes an authentication request. If no authenticator is supplied,
        then authentication succeeds.

        @return: C{Deferred}.
        @rtype: C{twisted.internet.defer.Deferred}
        """
        authenticator = self.getAuthenticator(service_request)

        if self.logger:
            self.logger.debug('Authenticator expands to: %r' % authenticator)

        if authenticator is None:
            return defer.succeed(True)

        args = (username, password)

        if hasattr(authenticator, '_pyamf_expose_request'):
            http_request = kwargs.get('http_request', None)
            args = (http_request,) + args

        return defer.maybeDeferred(authenticator, *args)

    def preprocessRequest(self, service_request, *args, **kwargs):
        """
        Preprocesses a request.
        """
        processor = self.getPreprocessor(service_request)

        if self.logger:
            self.logger.debug('Preprocessor expands to: %r' % processor)

        if processor is None:
            return

        args = (service_request,) + args

        if hasattr(processor, '_pyamf_expose_request'):
            http_request = kwargs.get('http_request', None)
            args = (http_request,) + args

        return defer.maybeDeferred(processor, *args)

########NEW FILE########
__FILENAME__ = wsgi
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
WSGI server implementation.

The Python Web Server Gateway Interface (WSGI) is a simple and universal
interface between web servers and web applications or frameworks.

The WSGI interface has two sides: the "server" or "gateway" side, and the
"application" or "framework" side. The server side invokes a callable
object (usually a function or a method) that is provided by the application
side. Additionally WSGI provides middlewares; a WSGI middleware implements
both sides of the API, so that it can be inserted "between" a WSGI server
and a WSGI application -- the middleware will act as an application from
the server's point of view, and as a server from the application's point
of view.

@see: U{WSGI homepage (external)<http://wsgi.org>}
@see: U{PEP-333 (external)<http://www.python.org/peps/pep-0333.html>}

@since: 0.1.0
"""

import pyamf
from pyamf import remoting
from pyamf.remoting import gateway

__all__ = ['WSGIGateway']


class WSGIGateway(gateway.BaseGateway):
    """
    WSGI Remoting Gateway.
    """

    def getResponse(self, request, environ):
        """
        Processes the AMF request, returning an AMF response.

        @param request: The AMF Request.
        @type request: L{Envelope<pyamf.remoting.Envelope>}
        @rtype: L{Envelope<pyamf.remoting.Envelope>}
        @return: The AMF Response.
        """
        response = remoting.Envelope(request.amfVersion)

        for name, message in request:
            processor = self.getProcessor(message)
            environ['pyamf.request'] = message
            response[name] = processor(message, http_request=environ)

        return response

    def badRequestMethod(self, environ, start_response):
        """
        Return HTTP 400 Bad Request.
        """
        response = "400 Bad Request\n\nTo access this PyAMF gateway you " \
            "must use POST requests (%s received)" % environ['REQUEST_METHOD']

        start_response('400 Bad Request', [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(response))),
            ('Server', gateway.SERVER_NAME),
        ])

        return [response]

    def __call__(self, environ, start_response):
        """
        @rtype: C{StringIO}
        @return: File-like object.
        """
        if environ['REQUEST_METHOD'] != 'POST':
            return self.badRequestMethod(environ, start_response)

        body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        stream = None
        timezone_offset = self._get_timezone_offset()

        # Decode the request
        try:
            request = remoting.decode(body, strict=self.strict,
                logger=self.logger, timezone_offset=timezone_offset)
        except (pyamf.DecodeError, IOError):
            if self.logger:
                self.logger.exception('Error decoding AMF request')

            response = "400 Bad Request\n\nThe request body was unable to " \
                "be successfully decoded."

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            start_response('400 Bad Request', [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(response))),
                ('Server', gateway.SERVER_NAME),
            ])

            return [response]
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Unexpected error decoding AMF request')

            response = ("500 Internal Server Error\n\nAn unexpected error "
                "occurred whilst decoding.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(response))),
                ('Server', gateway.SERVER_NAME),
            ])

            return [response]

        if self.logger:
            self.logger.debug("AMF Request: %r" % request)

        # Process the request
        try:
            response = self.getResponse(request, environ)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.logger:
                self.logger.exception('Error processing AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be successfully processed.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(response))),
                ('Server', gateway.SERVER_NAME),
            ])

            return [response]

        if self.logger:
            self.logger.debug("AMF Response: %r" % response)

        # Encode the response
        try:
            stream = remoting.encode(response, strict=self.strict,
                timezone_offset=timezone_offset)
        except:
            if self.logger:
                self.logger.exception('Error encoding AMF request')

            response = ("500 Internal Server Error\n\nThe request was "
                "unable to be encoded.")

            if self.debug:
                response += "\n\nTraceback:\n\n%s" % gateway.format_exception()

            start_response('500 Internal Server Error', [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(response))),
                ('Server', gateway.SERVER_NAME),
            ])

            return [response]

        response = stream.getvalue()

        start_response('200 OK', [
            ('Content-Type', remoting.CONTENT_TYPE),
            ('Content-Length', str(len(response))),
            ('Server', gateway.SERVER_NAME),
        ])

        return [response]

########NEW FILE########
__FILENAME__ = sol
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Local Shared Object implementation.

Local Shared Object (LSO), sometimes known as Adobe Flash cookies, is a
cookie-like data entity used by the Adobe Flash Player and Gnash. The players
allow web content to read and write LSO data to the computer's local drive on
a per-domain basis.

@see: U{Local Shared Object on WikiPedia
    <http://en.wikipedia.org/wiki/Local_Shared_Object>}
@since: 0.1
"""

import pyamf
from pyamf import util

#: Magic Number - 2 bytes
HEADER_VERSION = '\x00\xbf'
#: Marker - 10 bytes
HEADER_SIGNATURE = 'TCSO\x00\x04\x00\x00\x00\x00'
#: Padding - 4 bytes
PADDING_BYTE = '\x00'


def decode(stream, strict=True):
    """
    Decodes a SOL stream. L{strict} mode ensures that the sol stream is as spec
    compatible as possible.

    @return: A C{tuple} containing the C{root_name} and a C{dict} of name,
        value pairs.
    """
    if not isinstance(stream, util.BufferedByteStream):
        stream = util.BufferedByteStream(stream)

    # read the version
    version = stream.read(2)

    if version != HEADER_VERSION:
        raise pyamf.DecodeError('Unknown SOL version in header')

    # read the length
    length = stream.read_ulong()

    if strict and stream.remaining() != length:
        raise pyamf.DecodeError('Inconsistent stream header length')

    # read the signature
    signature = stream.read(10)

    if signature != HEADER_SIGNATURE:
        raise pyamf.DecodeError('Invalid signature')

    length = stream.read_ushort()
    root_name = stream.read_utf8_string(length)

    # read padding
    if stream.read(3) != PADDING_BYTE * 3:
        raise pyamf.DecodeError('Invalid padding read')

    decoder = pyamf.get_decoder(stream.read_uchar())
    decoder.stream = stream

    values = {}

    while 1:
        if stream.at_eof():
            break

        name = decoder.readString()
        value = decoder.readElement()

        # read the padding
        if stream.read(1) != PADDING_BYTE:
            raise pyamf.DecodeError('Missing padding byte')

        values[name] = value

    return (root_name, values)


def encode(name, values, strict=True, encoding=pyamf.AMF0):
    """
    Produces a SharedObject encoded stream based on the name and values.

    @param name: The root name of the SharedObject.
    @param values: A `dict` of name value pairs to be encoded in the stream.
    @param strict: Ensure that the SOL stream is as spec compatible as possible.
    @return: A SharedObject encoded stream.
    @rtype: L{BufferedByteStream<pyamf.util.BufferedByteStream>}, a file like
        object.
    """
    encoder = pyamf.get_encoder(encoding)
    stream = encoder.stream

    # write the header
    stream.write(HEADER_VERSION)

    if strict:
        length_pos = stream.tell()

    stream.write_ulong(0)

    # write the signature
    stream.write(HEADER_SIGNATURE)

    # write the root name
    name = name.encode('utf-8')

    stream.write_ushort(len(name))
    stream.write(name)

    # write the padding
    stream.write(PADDING_BYTE * 3)
    stream.write_uchar(encoding)

    for n, v in values.iteritems():
        encoder.serialiseString(n)
        encoder.writeElement(v)

        # write the padding
        stream.write(PADDING_BYTE)

    if strict:
        stream.seek(length_pos)
        stream.write_ulong(stream.remaining() - 4)

    stream.seek(0)

    return stream


def load(name_or_file):
    """
    Loads a sol file and returns a L{SOL} object.

    @param name_or_file: Name of file, or file-object.
    @type name_or_file: C{string}
    """
    f = name_or_file
    opened = False

    if isinstance(name_or_file, basestring):
        f = open(name_or_file, 'rb')
        opened = True
    elif not hasattr(f, 'read'):
        raise ValueError('Readable stream expected')

    name, values = decode(f.read())
    s = SOL(name)

    for n, v in values.iteritems():
        s[n] = v

    if opened is True:
        f.close()

    return s


def save(sol, name_or_file, encoding=pyamf.AMF0):
    """
    Writes a L{SOL} object to C{name_or_file}.

    @param name_or_file: Name of file or file-object to write to.
    @param encoding: AMF encoding type.
    """
    f = name_or_file
    opened = False

    if isinstance(name_or_file, basestring):
        f = open(name_or_file, 'wb+')
        opened = True
    elif not hasattr(f, 'write'):
        raise ValueError('Writable stream expected')

    f.write(encode(sol.name, sol, encoding=encoding).getvalue())

    if opened:
        f.close()


class SOL(dict):
    """
    Local Shared Object class, allows easy manipulation of the internals of a
    C{sol} file.
    """
    def __init__(self, name):
        self.name = name

    def save(self, name_or_file, encoding=pyamf.AMF0):
        save(self, name_or_file, encoding)

    def __repr__(self):
        return '<%s %s %s at 0x%x>' % (self.__class__.__name__,
            self.name, dict.__repr__(self), id(self))

LSO = SOL

########NEW FILE########
__FILENAME__ = models
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

from django.db import models


class SimplestModel(models.Model):
    """
    The simplest Django model you can have
    """


class TimeClass(models.Model):
    """
    A model with all the time based fields
    """

    t = models.TimeField()
    d = models.DateField()
    dt = models.DateTimeField()


class ParentReference(models.Model):
    """
    Has a foreign key to L{ChildReference}
    """

    name = models.CharField(max_length=100)
    bar = models.ForeignKey('ChildReference', null=True)


class ChildReference(models.Model):
    """
    Has a foreign key relation to L{ParentReference}
    """

    name = models.CharField(max_length=100)
    foo = models.ForeignKey(ParentReference)


class NotSaved(models.Model):
    name = models.CharField(max_length=100)


class Publication(models.Model):
    title = models.CharField(max_length=30)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)
    reporter = models.ForeignKey(Reporter, null=True)

    def __unicode__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)


# concrete inheritance
class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)


class Restaurant(Place):
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()


# abstract inheritance
class CommonInfo(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()

    class Meta:
        abstract = True

class Student(CommonInfo):
    home_group = models.CharField(max_length=5)


# foreign keys
class NullForeignKey(models.Model):
    foobar = models.ForeignKey(SimplestModel, null=True)


class BlankForeignKey(models.Model):
    foobar = models.ForeignKey(SimplestModel, blank=True)


class StaticRelation(models.Model):
    gak = models.ForeignKey(SimplestModel)


class FileModel(models.Model):
    file = models.FileField(upload_to='file_model')
    text = models.CharField(max_length=64)


try:
    import PIL

    class Profile(models.Model):
        file = models.ImageField(upload_to='profile')
        text = models.CharField(max_length=64)
except ImportError:
    pass


class DBColumnModel(models.Model):
    """
    @see: #807
    """
    bar = models.ForeignKey(SimplestModel, db_column='custom')

########NEW FILE########
__FILENAME__ = settings
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

# The simplest Django settings possible

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'

INSTALLED_APPS = ('adapters',)

########NEW FILE########
__FILENAME__ = test_array
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the L{array} L{pyamf.adapters._array} module.

@since: 0.5
"""

try:
    import array
except ImportError:
    array = None

import unittest

import pyamf


class ArrayTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not array:
            self.skipTest("'array' not available")

        self.orig = ['f', 'o', 'o']

        self.obj = array.array('c')

        self.obj.append('f')
        self.obj.append('o')
        self.obj.append('o')

    def encdec(self, encoding):
        return pyamf.decode(pyamf.encode(self.obj, encoding=encoding),
            encoding=encoding).next()

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)

########NEW FILE########
__FILENAME__ = test_collections
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the L{collections} L{pyamf.adapters._collections} module.

@since: 0.5
"""

try:
    import collections
except ImportError:
    collections = None

import unittest

import pyamf


class CollectionsTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not collections:
            self.skipTest("'collections' not available")

    def encdec(self, encoding):
        return pyamf.decode(pyamf.encode(self.obj, encoding=encoding),
            encoding=encoding).next()


class DequeTestCase(CollectionsTestCase):
    """
    Tests for L{collections.deque}
    """

    def setUp(self):
        CollectionsTestCase.setUp(self)

        self.orig = [1, 2, 3]
        self.obj = collections.deque(self.orig)

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)


class DefaultDictTestCase(CollectionsTestCase):
    """
    Tests for L{collections.defaultdict}
    """

    def setUp(self):
        CollectionsTestCase.setUp(self)

        if not hasattr(collections, 'defaultdict'):
            self.skipTest("'collections.defaultdict' not available")

        s = 'mississippi'
        self.obj = collections.defaultdict(int)

        for k in s:
            self.obj[k] += 1

        self.orig = dict(self.obj)

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)


class OrderedDictTestCase(CollectionsTestCase):
    """
    Tests for L{collections.OrderedDict}
    """

    def setUp(self):
        CollectionsTestCase.setUp(self)

        if not hasattr(collections, 'OrderedDict'):
            self.skipTest("'collections.OrderedDict' not available")

        self.obj = collections.OrderedDict([('apple', 4), ('banana', 3), ('orange', 2), ('pear', 1)])
        self.orig = dict(self.obj)


    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)


class CounterTestCase(CollectionsTestCase):
    """
    Tests for L{collections.Counter}
    """

    def setUp(self):
        CollectionsTestCase.setUp(self)

        if not hasattr(collections, 'Counter'):
            self.skipTest("'collections.Counter' not available")

        self.obj = collections.Counter({'blue': 3, 'red': 2, 'green': 1})

        self.orig = dict(self.obj)

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)


class NamedTupleTestCase(CollectionsTestCase):
    """
    Tests for L{collections.namedtuple}
    """

    def setUp(self):
        CollectionsTestCase.setUp(self)

        if not hasattr(collections, 'namedtuple'):
            self.skipTest("'collections.namedtuple' not available")

        user_vo = collections.namedtuple('user_vo', 'id name age')

        pyamf.add_type(user_vo, lambda obj, encoder: obj._asdict())

        self.obj = user_vo(1, 'Hadrien', 30)
        self.orig = self.obj._asdict()

    def test_amf0(self):
        self.assertEqual(self.encdec(pyamf.AMF0), self.orig)

    def test_amf3(self):
        self.assertEqual(self.encdec(pyamf.AMF3), self.orig)

########NEW FILE########
__FILENAME__ = test_django
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF Django adapter tests.

@since: 0.3.1
"""

import unittest
import sys
import os
import datetime
from shutil import rmtree
from tempfile import mkdtemp  

import pyamf
from pyamf.tests import util

try:
    import django
except ImportError:
    django = None

if django and django.VERSION < (1, 0):
    django = None

try:
    reload(settings)
except NameError:
    from pyamf.tests.adapters.django_app import settings


context = None

#: django modules/functions used once bootstrapped
create_test_db = None
destroy_test_db = None
management = None
setup_test_environment = None
teardown_test_environment = None

# test app data
models = None
adapter = None


def init_django():
    """
    Bootstrap Django and initialise this module
    """
    global django, management, create_test_db, destroy_test_db
    global setup_test_environment, teardown_test_environment

    if not django:
        return

    from django.core import management

    project_dir = management.setup_environ(settings)
    sys.path.insert(0, project_dir)

    try:
        from django.test.utils import create_test_db, destroy_test_db
    except ImportError:
        from django.db import connection

        create_test_db = connection.creation.create_test_db
        destroy_test_db = connection.creation.destroy_test_db

    from django.test.utils import setup_test_environment, teardown_test_environment

    return True


def setUpModule():
    """
    Called to set up the module by the test runner
    """
    global context, models, storage, adapter

    context = {
        'sys.path': sys.path[:],
        'sys.modules': sys.modules.copy(),
        'os.environ': os.environ.copy(),
    }

    if init_django():
        from django.core.files.storage import FileSystemStorage
        from pyamf.tests.adapters.django_app.adapters import models
        from pyamf.adapters import _django_db_models_base as adapter

        setup_test_environment()
 
        settings.DATABASE_NAME = create_test_db(verbosity=0, autoclobber=True)
        storage = FileSystemStorage(mkdtemp())


def tearDownModule():
    # remove all the stuff that django installed
    teardown_test_environment()

    sys.path = context['sys.path']
    util.replace_dict(context['sys.modules'], sys.modules)
    util.replace_dict(context['os.environ'], os.environ)

    destroy_test_db(settings.DATABASE_NAME, verbosity=0)

    rmtree(storage.location, ignore_errors=True)


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        if not django:
            self.skipTest("'django' is not available")


class TypeMapTestCase(BaseTestCase):
    """
    Tests for basic encoding functionality
    """

    def test_objects_all(self):
        encoder = pyamf.get_encoder(pyamf.AMF0)

        encoder.writeElement(models.SimplestModel.objects.all())
        self.assertEqual(encoder.stream.getvalue(), '\n\x00\x00\x00\x00')

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(models.SimplestModel.objects.all())
        self.assertEqual(encoder.stream.getvalue(), '\t\x01\x01')

    def test_NOT_PROVIDED(self):
        from django.db.models import fields

        self.assertEqual(pyamf.encode(fields.NOT_PROVIDED, encoding=pyamf.AMF0).getvalue(),
            '\x06')

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(fields.NOT_PROVIDED)
        self.assertEqual(encoder.stream.getvalue(), '\x00')


class ClassAliasTestCase(BaseTestCase):
    def test_time(self):
        x = models.TimeClass()

        x.t = datetime.time(12, 12, 12)
        x.d = datetime.date(2008, 3, 12)
        x.dt = datetime.datetime(2008, 3, 12, 12, 12, 12)

        alias = adapter.DjangoClassAlias(models.TimeClass, None)
        attrs = alias.getEncodableAttributes(x)

        self.assertEqual(attrs, {
            'id': None,
            'd': datetime.datetime(2008, 3, 12, 0, 0),
            'dt': datetime.datetime(2008, 3, 12, 12, 12, 12),
            't': datetime.datetime(1970, 1, 1, 12, 12, 12)
        })

        y = models.TimeClass()

        alias.applyAttributes(y, {
            'id': None,
            'd': datetime.datetime(2008, 3, 12, 0, 0),
            'dt': datetime.datetime(2008, 3, 12, 12, 12, 12),
            't': datetime.datetime(1970, 1, 1, 12, 12, 12)
        })

        self.assertEqual(y.id, None)
        self.assertEqual(y.d, datetime.date(2008, 3, 12))
        self.assertEqual(y.dt, datetime.datetime(2008, 3, 12, 12, 12, 12))
        self.assertEqual(y.t, datetime.time(12, 12, 12))

        y = models.TimeClass()

        alias.applyAttributes(y, {
            'id': None,
            'd': None,
            'dt': None,
            't': None
        })

        self.assertEqual(y.id, None)
        self.assertEqual(y.d, None)
        self.assertEqual(y.dt, None)
        self.assertEqual(y.t, None)

    def test_undefined(self):
        from django.db import models
        from django.db.models import fields

        class UndefinedClass(models.Model):
            pass

        alias = adapter.DjangoClassAlias(UndefinedClass, None)

        x = UndefinedClass()

        alias.applyAttributes(x, {
            'id': pyamf.Undefined
        })

        self.assertEqual(x.id, fields.NOT_PROVIDED)

        x.id = fields.NOT_PROVIDED

        attrs = alias.getEncodableAttributes(x)
        self.assertEqual(attrs, {'id': pyamf.Undefined})

    def test_non_field_prop(self):
        from django.db import models

        class Book(models.Model):
            def _get_number_of_odd_pages(self):
                return 234

            # note the lack of a setter callable ..
            numberOfOddPages = property(_get_number_of_odd_pages)

        alias = adapter.DjangoClassAlias(Book, 'Book')

        x = Book()

        self.assertEqual(alias.getEncodableAttributes(x),
            {'numberOfOddPages': 234, 'id': None})

        # now we test sending the numberOfOddPages attribute
        alias.applyAttributes(x, {'numberOfOddPages': 24, 'id': None})

        # test it hasn't been set
        self.assertEqual(x.numberOfOddPages, 234)

    def test_dynamic(self):
        """
        Test for dynamic property encoding.
        """
        alias = adapter.DjangoClassAlias(models.SimplestModel, 'Book')

        x = models.SimplestModel()
        x.spam = 'eggs'

        self.assertEqual(alias.getEncodableAttributes(x),
            {'spam': 'eggs', 'id': None})

        # now we test sending the numberOfOddPages attribute
        alias.applyAttributes(x, {'spam': 'foo', 'id': None})

        # test it has been set
        self.assertEqual(x.spam, 'foo')

    def test_properties(self):
        """
        See #764
        """
        from django.db import models

        class Foob(models.Model):
            def _get_days(self):
                return 1

            def _set_days(self, val):
                assert 1 == val

            days = property(_get_days, _set_days)

        alias = adapter.DjangoClassAlias(Foob, 'Bar')

        x = Foob()

        self.assertEqual(x.days, 1)

        self.assertEqual(alias.getEncodableAttributes(x),
            {'days': 1, 'id': None})

        # now we test sending the numberOfOddPages attribute
        alias.applyAttributes(x, {'id': None})


class ForeignKeyTestCase(BaseTestCase):
    def test_one_to_many(self):
        # initialise the db ..
        r = models.Reporter(first_name='John', last_name='Smith', email='john@example.com')
        r.save()
        self.addCleanup(r.delete)

        r2 = models.Reporter(first_name='Paul', last_name='Jones', email='paul@example.com')
        r2.save()
        self.addCleanup(r2.delete)

        a = models.Article(headline="This is a test", reporter=r)
        a.save()
        self.addCleanup(a.delete)

        self.assertEqual(a.id, 1)

        del a

        a = models.Article.objects.filter(pk=1)[0]

        self.assertFalse('_reporter_cache' in a.__dict__)
        a.reporter
        self.assertTrue('_reporter_cache' in a.__dict__)

        del a

        a = models.Article.objects.filter(pk=1)[0]
        alias = adapter.DjangoClassAlias(models.Article, defer=True)

        self.assertFalse(hasattr(alias, 'fields'))
        attrs = alias.getEncodableAttributes(a)

        # note that the reporter attribute does not exist.
        self.assertEqual(attrs, {
            'headline': u'This is a test',
            'id': 1,
            'publications': []
        })

        self.assertFalse('_reporter_cache' in a.__dict__)
        self.assertEqual(pyamf.encode(a, encoding=pyamf.AMF3).getvalue(),
            '\n\x0b\x01\x11headline\x06\x1dThis is a test\x05id\x04\x01'
            '\x19publications\t\x01\x01\x01')

        del a

        # now with select_related to pull in the reporter object
        a = models.Article.objects.select_related('reporter').filter(pk=1)[0]

        alias = adapter.DjangoClassAlias(models.Article, defer=True)

        self.assertFalse(hasattr(alias, 'fields'))
        self.assertEqual(alias.getEncodableAttributes(a), {
            'headline': u'This is a test',
            'id': 1,
            'reporter': r,
            'publications': []
        })

        self.assertTrue('_reporter_cache' in a.__dict__)
        self.assertEqual(pyamf.encode(a, encoding=pyamf.AMF3).getvalue(),
            '\n\x0b\x01\x11reporter\n\x0b\x01\x15first_name\x06\tJohn\x13'
            'last_name\x06\x0bSmith\x05id\x04\x01\x0bemail\x06!john'
            '@example.com\x01\x11headline\x06\x1dThis is a test\x19'
            'publications\t\x01\x01\n\x04\x01\x01')

    def test_many_to_many(self):
        # install some test data - taken from
        # http://www.djangoproject.com/documentation/models/many_to_many/
        p1 = models.Publication(id=None, title='The Python Journal')
        p1.save()
        p2 = models.Publication(id=None, title='Science News')
        p2.save()
        p3 = models.Publication(id=None, title='Science Weekly')
        p3.save()

        self.addCleanup(p1.delete)
        self.addCleanup(p2.delete)
        self.addCleanup(p3.delete)

        # Create an Article.
        a1 = models.Article(id=None, headline='Django lets you build Web apps easily')
        a1.save()
        self.addCleanup(a1.delete)
        self.assertEqual(a1.id, 1)

        # Associate the Article with a Publication.
        a1.publications.add(p1)

        pub_alias = adapter.DjangoClassAlias(models.Publication, None)
        art_alias = adapter.DjangoClassAlias(models.Article, None)

        test_publication = models.Publication.objects.filter(pk=1)[0]
        test_article = models.Article.objects.filter(pk=1)[0]

        attrs = pub_alias.getEncodableAttributes(test_publication)
        self.assertEqual(attrs, {'id': 1, 'title': u'The Python Journal'})

        attrs = art_alias.getEncodableAttributes(test_article)
        self.assertEqual(attrs, {
            'headline': u'Django lets you build Web apps easily',
            'id': 1,
            'publications': [p1]
        })

        x = models.Article()

        art_alias.applyAttributes(x, {
            'headline': u'Test',
            'id': 1,
            'publications': [p1]
        })

        self.assertEqual(x.headline, u'Test')
        self.assertEqual(x.id, 1)
        self.assertEqual(list(x.publications.all()), [p1])

        y = models.Article()
        attrs = art_alias.getDecodableAttributes(y, {
            'headline': u'Django lets you build Web apps easily',
            'id': 0,
            'publications': []
        })

        self.assertEqual(attrs, {'headline': u'Django lets you build Web apps easily'})

    def test_nullable_foreign_keys(self):
        x = models.SimplestModel()
        x.save()
        self.addCleanup(x.delete)

        nfk_alias = adapter.DjangoClassAlias(models.NullForeignKey, None)
        bfk_alias = adapter.DjangoClassAlias(models.BlankForeignKey, None)

        nfk = models.NullForeignKey()
        attrs = nfk_alias.getEncodableAttributes(nfk)

        self.assertEqual(attrs, {'id': None})

        bfk = models.BlankForeignKey()
        attrs = bfk_alias.getEncodableAttributes(bfk)

        self.assertEqual(attrs, {'id': None})

    def test_static_relation(self):
        """
        @see: #693
        """
        from pyamf import util

        pyamf.register_class(models.StaticRelation)
        alias = adapter.DjangoClassAlias(models.StaticRelation,
            static_attrs=('gak',))

        alias.compile()

        self.assertTrue('gak' in alias.relations)
        self.assertTrue('gak' in alias.decodable_properties)
        self.assertTrue('gak' in alias.static_attrs)

        x = models.StaticRelation()

        # just run this to ensure that it doesn't blow up
        alias.getDecodableAttributes(x, {'id': None, 'gak': 'foo'})


class I18NTestCase(BaseTestCase):
    def test_encode(self):
        from django.utils.translation import ugettext_lazy

        self.assertEqual(pyamf.encode(ugettext_lazy('Hello')).getvalue(),
            '\x06\x0bHello')


class PKTestCase(BaseTestCase):
    """
    See ticket #599 for this. Check to make sure that django pk fields
    are set first
    """

    def test_behaviour(self):
        p = models.Publication(id=None, title='The Python Journal')
        a = models.Article(id=None, headline='Django lets you build Web apps easily')

        # Associate the Article with a Publication.
        self.assertRaises(ValueError, lambda a, p: a.publications.add(p), a, p)

        p.save()
        a.save()

        self.addCleanup(p.delete)
        self.addCleanup(a.delete)

        self.assertEqual(a.id, 1)

        article_alias = adapter.DjangoClassAlias(models.Article, None)
        x = models.Article()

        article_alias.applyAttributes(x, {
            'headline': 'Foo bar!',
            'id': 1,
            'publications': [p]
        })

        self.assertEqual(x.headline, 'Foo bar!')
        self.assertEqual(x.id, 1)
        self.assertEqual(list(x.publications.all()), [p])

    def test_none(self):
        """
        See #556. Make sure that PK fields with a value of 0 are actually set
        to C{None}.
        """
        alias = adapter.DjangoClassAlias(models.SimplestModel, None)

        x = models.SimplestModel()

        self.assertEqual(x.id, None)

        alias.applyAttributes(x, {
            'id': 0
        })

        self.assertEqual(x.id, None)

    def test_no_pk(self):
        """
        Ensure that Models without a primary key are correctly serialized.
        See #691.
        """
        instances = [models.NotSaved(name="a"), models.NotSaved(name="b")]
        encoded = pyamf.encode(instances, encoding=pyamf.AMF3).getvalue()

        decoded = pyamf.decode(encoded, encoding=pyamf.AMF3).next()
        self.assertEqual(decoded[0]['name'], 'a')
        self.assertEqual(decoded[1]['name'], 'b')


class ModelInheritanceTestCase(BaseTestCase):
    """
    Tests for L{Django model inheritance<http://docs.djangoproject.com/en/dev/topics/db/models/#model-inheritance>}
    """

    def test_abstract(self):
        alias = adapter.DjangoClassAlias(models.Student)

        x = models.Student()

        attrs = alias.getEncodableAttributes(x)

        self.assertEqual(attrs, {
            'age': None,
            'home_group': '',
            'id': None,
            'name': ''
        })

    def test_concrete(self):
        alias = adapter.DjangoClassAlias(models.Place)
        x = models.Place()

        attrs = alias.getEncodableAttributes(x)

        self.assertEqual(attrs, {
            'id': None,
            'name': '',
            'address': ''
        })

        alias = adapter.DjangoClassAlias(models.Restaurant)
        x = models.Restaurant()

        attrs = alias.getEncodableAttributes(x)

        self.assertEqual(attrs, {
            'id': None,
            'name': '',
            'address': '',
            'serves_hot_dogs': False,
            'serves_pizza': False
        })


class MockFile(object):
    """
    mock for L{django.core.files.base.File}
    """

    def chunks(self):
        return []

    def __len__(self):
        return self.size

    def read(self, n):
        return ''

    # support for Django 1.2.5
    @property
    def size(self):
        return 0


class FieldsTestCase(BaseTestCase):
    """
    Tests for L{fields}
    """

    def test_file(self):
        alias = adapter.DjangoClassAlias(models.FileModel)

        i = models.FileModel()
        i.file.storage = storage
        i.file.save('bar', MockFile())
        i.save()

        attrs = alias.getEncodableAttributes(i)

        self.assertEqual(attrs, {'text': '', 'id': 1, 'file': u'file_model/bar'})

        attrs = alias.getDecodableAttributes(i, attrs)

        self.assertEqual(attrs, {'text': ''})


class ImageTestCase(BaseTestCase):
    """
    Tests for L{fields}
    """

    def setUp(self):
        try:
            import PIL
        except ImportError:
            self.skipTest("'PIL' is not available")

        BaseTestCase.setUp(self)

    def test_image(self):
        alias = adapter.DjangoClassAlias(models.Profile)

        i = models.Profile()
        i.file.storage = storage
        i.file.save('bar', MockFile())
        i.save()

        attrs = alias.getEncodableAttributes(i)

        self.assertEqual(attrs, {'text': '', 'id': 1, 'file': u'profile/bar'})

        attrs = alias.getDecodableAttributes(i, attrs)

        self.assertEqual(attrs, {'text': ''})


class ReferenceTestCase(BaseTestCase, util.EncoderMixIn):
    """
    Test case to make sure that the same object from the database is encoded
    by reference.
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        BaseTestCase.setUp(self)
        util.EncoderMixIn.setUp(self)

    def test_not_referenced(self):
        """
        Test to ensure that we observe the correct behaviour in the Django
        ORM.
        """
        f = models.ParentReference()
        f.name = 'foo'

        b = models.ChildReference()
        b.name = 'bar'

        f.save()
        b.foo = f
        b.save()
        f.bar = b
        f.save()

        self.addCleanup(f.delete)
        self.addCleanup(b.delete)

        self.assertEqual(f.id, 1)
        foo = models.ParentReference.objects.select_related().get(id=1)

        self.assertFalse(foo.bar.foo is foo)

    def test_referenced_encode(self):
        f = models.ParentReference()
        f.name = 'foo'

        b = models.ChildReference()
        b.name = 'bar'

        f.save()
        b.foo = f
        b.save()
        f.bar = b
        f.save()

        self.addCleanup(f.delete)
        self.addCleanup(b.delete)

        self.assertEqual(f.id, 1)
        foo = models.ParentReference.objects.select_related().get(id=1)

        # ensure the referenced attribute resolves
        foo.bar.foo

        self.assertEncoded(foo, '\n\x0b\x01\x07bar\n\x0b\x01\x07foo\n\x00\x05'
            'id\x04\x01\tname\x06\x00\x01\x04\x04\x01\x06\x06\x02\x01')


class AuthTestCase(BaseTestCase):
    """
    Tests for L{django.contrib.auth.models}
    """

    def test_user(self):
        from django.contrib.auth import models

        alias = pyamf.get_class_alias(models.User)

        self.assertEqual(alias, 'django.contrib.auth.models.User')
        self.assertEqual(alias.exclude_attrs, ('message_set', 'password'))
        self.assertEqual(alias.readonly_attrs, ('username',))


class DBColumnTestCase(BaseTestCase):
    """
    Tests for #807
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.alias = adapter.DjangoClassAlias(models.DBColumnModel, None)
        self.model = models.DBColumnModel()

    def test_encodable_attrs(self):
        def attrs():
            return self.alias.getEncodableAttributes(self.model)

        self.assertEqual(attrs(), {'id': None})

        x = models.SimplestModel()

        x.save()
        self.addCleanup(x.delete)

        self.model.bar = x

        self.assertEqual(attrs(), {'id': None, 'bar': x})

########NEW FILE########
__FILENAME__ = test_elixir
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF Elixir adapter tests.

@since: 0.6
"""

import unittest

try:
    import elixir as e
    from pyamf.adapters import _elixir as adapter
except ImportError:
    e = None

import pyamf


if e:
    class Genre(e.Entity):
        name = e.Field(e.Unicode(15), primary_key=True)
        movies = e.ManyToMany('Movie')

        def __repr__(self):
            return '<Genre "%s">' % self.name


    class Movie(e.Entity):
        title = e.Field(e.Unicode(30), primary_key=True)
        year = e.Field(e.Integer, primary_key=True)
        description = e.Field(e.UnicodeText, deferred=True)
        director = e.ManyToOne('Director')
        genres = e.ManyToMany('Genre')


    class Person(e.Entity):
        name = e.Field(e.Unicode(60), primary_key=True)


    class Director(Person):
        movies = e.OneToMany('Movie')
        e.using_options(inheritance='multi')


    # set up
    e.metadata.bind = "sqlite://"


class BaseTestCase(unittest.TestCase):
    """
    Initialise up all table/mappers.
    """

    def setUp(self):
        if not e:
            self.skipTest("'elixir' is not available")

        e.setup_all()
        e.create_all()

        self.movie_alias = pyamf.register_class(Movie, 'movie')
        self.genre_alias = pyamf.register_class(Genre, 'genre')
        self.director_alias = pyamf.register_class(Director, 'director')

        self.create_movie_data()

    def tearDown(self):
        e.drop_all()
        e.session.rollback()
        e.session.expunge_all()

        pyamf.unregister_class(Movie)
        pyamf.unregister_class(Genre)
        pyamf.unregister_class(Director)

    def create_movie_data(self):
        scifi = Genre(name=u"Science-Fiction")
        rscott = Director(name=u"Ridley Scott")
        glucas = Director(name=u"George Lucas")
        alien = Movie(title=u"Alien", year=1979, director=rscott, genres=[scifi, Genre(name=u"Horror")])
        brunner = Movie(title=u"Blade Runner", year=1982, director=rscott, genres=[scifi])
        swars = Movie(title=u"Star Wars", year=1977, director=glucas, genres=[scifi])

        e.session.commit()
        e.session.expunge_all()


class ClassAliasTestCase(BaseTestCase):
    def test_type(self):
        self.assertEqual(
            self.movie_alias.__class__, adapter.ElixirAdapter)
        self.assertEqual(
            self.genre_alias.__class__, adapter.ElixirAdapter)
        self.assertEqual(
            self.director_alias.__class__, adapter.ElixirAdapter)

    def test_get_attrs(self):
        m = Movie.query.filter_by(title=u"Blade Runner").one()

        g = m.genres[0]
        d = m.director

        attrs = self.movie_alias.getEncodableAttributes(m)

        self.assertEqual(attrs, {
            'genres': [g],
            'description': None,
            'title': u'Blade Runner',
            'director': d,
            'year': 1982,
            'sa_key': [u'Blade Runner', 1982],
            'sa_lazy': []
        })

    def test_inheritance(self):
        d = Director.query.filter_by(name=u"Ridley Scott").one()

        attrs = self.director_alias.getEncodableAttributes(d)

        self.assertEqual(attrs, {
            'movies': d.movies,
            'sa_key': [u'Ridley Scott'],
            'person_name': u'Ridley Scott',
            'name': u'Ridley Scott',
            'sa_lazy': []
        })

########NEW FILE########
__FILENAME__ = test_google
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF Google adapter tests.

@since: 0.3.1
"""

import unittest
import datetime
import struct
import os

import pyamf
from pyamf import amf3
from pyamf.tests import util

try:
    from google.appengine.ext import db
except ImportError:
    db = None


blobstore = None
polymodel = None
adapter_db = None
adapter_blobstore = None

test_models = None

Spam = util.Spam


def setUpModule():
    """
    """
    global db, blobstore, polymodel, adapter_blobstore, adapter_db, test_models

    if db is None:
        raise unittest.SkipTest("'google.appengine.ext.db' is not available")

    if not os.environ.get('SERVER_SOFTWARE', None):
        # this is an extra check because the AppEngine SDK may be in PYTHONPATH
        raise unittest.SkipTest('Appengine env not bootstrapped correctly')

    # all looks good - we now initialise the imports we require
    from google.appengine.ext import blobstore
    from google.appengine.ext.db import polymodel

    from pyamf.adapters import _google_appengine_ext_db as adapter_db
    from pyamf.adapters import _google_appengine_ext_blobstore as adapter_blobstore

    from pyamf.tests.adapters import _google_models as test_models


class BaseTestCase(util.ClassCacheClearingTestCase):
    """
    """

    def put(self, entity):
        entity.put()
        self.addCleanup(self.deleteEntity, entity)

    def deleteEntity(self, entity):
        if entity.is_saved():
            entity.delete()

    def decode(self, bytes, encoding=pyamf.AMF3):
        decoded = list(pyamf.decode(bytes, encoding=encoding))

        if len(decoded) == 1:
            return decoded[0]

        return decoded

    def encodeKey(self, key, encoding):
        """
        Returns an AMF encoded representation of a L{db.Key} instance.

        @param key: The L{db.Key} to be encoded.
        @type key: L{db.Key}
        @param encoding: The AMF version.
        """
        if hasattr(key, 'key'):
            # we have a db.Model instance
            try:
                key = key.key()
            except db.NotSavedError:
                key = None

        if not key:
            # the AMF representation of None
            if encoding == pyamf.AMF3:
                return '\x01'

            return '\x05'

        k = str(key)

        if encoding == pyamf.AMF3:
            return '\x06%s%s' % (
                amf3.encode_int(len(k) << 1 | amf3.REFERENCE_BIT), k)

        return '\x02%s%s' % (struct.pack('>H', len(k)), k)



class JessicaFactory(object):
    """
    Provides jessica!
    """

    jessica_attrs = {
        'name': 'Jessica',
        'type': 'cat',
        'birthdate': datetime.date(1986, 10, 2),
        'weight_in_pounds': 5,
        'spayed_or_neutered': False
    }

    @classmethod
    def makeJessica(kls, cls, **kwargs):
        j_kwargs = kls.jessica_attrs.copy()

        j_kwargs.update(kwargs)

        return cls(**j_kwargs)


class EncodingModelTestCase(BaseTestCase):
    """
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.jessica = JessicaFactory.makeJessica(test_models.PetModel)

    def test_amf0(self):
        encoded = (
            '\x03', (
                '\x00\x04_key%s' % (self.encodeKey(self.jessica, pyamf.AMF0)),
                '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
                '\x00\x04name\x02\x00\x07Jessica',
                '\x00\x12spayed_or_neutered\x01\x00',
                '\x00\x04type\x02\x00\x03cat',
                '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00'
            ),
            '\x00\x00\t'
        )

        self.assertEncodes(self.jessica, encoded, encoding=pyamf.AMF0)

    def test_amf3(self):
        bytes = (
            '\n\x0b\x01', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % (self.encodeKey(self.jessica, pyamf.AMF3)),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)

    def test_save_amf0(self):
        self.put(self.jessica)

        bytes = ('\x03', (
            '\x00\x04_key%s' % self.encodeKey(self.jessica, pyamf.AMF0),
            '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
            '\x00\x04name\x02\x00\x07Jessica',
            '\x00\x12spayed_or_neutered\x01\x00',
            '\x00\x04type\x02\x00\x03cat',
            '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00'),
            '\x00\x00\t')

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF0)

    def test_save_amf3(self):
        self.put(self.jessica)

        bytes = (
            '\n\x0b\x01', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % self.encodeKey(self.jessica, pyamf.AMF3),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)

    def test_alias_amf0(self):
        pyamf.register_class(test_models.PetModel, 'Pet')

        bytes = (
            '\x10\x00\x03Pet', (
                '\x00\x04_key%s' % self.encodeKey(self.jessica, pyamf.AMF0),
                '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
                '\x00\x04name\x02\x00\x07Jessica',
                '\x00\x12spayed_or_neutered\x01\x00',
                '\x00\x04type\x02\x00\x03cat',
                '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00'
            ),
            '\x00\x00\t'
        )

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF0)

    def test_alias_amf3(self):
        pyamf.register_class(test_models.PetModel, 'Pet')

        bytes = (
            '\n\x0b\x07Pet', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % self.encodeKey(self.jessica, pyamf.AMF3),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\x07foo\x06\x07bar',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)


class EncodingExpandoTestCase(BaseTestCase):
    """
    Tests for encoding L{db.Expando} classes
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.jessica = JessicaFactory.makeJessica(test_models.PetExpando, foo='bar')

        self.addCleanup(self.deleteEntity, self.jessica)

    def test_amf0(self):
        bytes = (
            '\x03', (
                '\x00\x04_key%s' % self.encodeKey(self.jessica, pyamf.AMF0),
                '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
                '\x00\x04name\x02\x00\x07Jessica',
                '\x00\x12spayed_or_neutered\x01\x00',
                '\x00\x04type\x02\x00\x03cat',
                '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00',
                '\x00\x03foo\x02\x00\x03bar'
            ),
            '\x00\x00\t'
        )

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF0)

    def test_amf3(self):
        bytes = (
            '\n\x0b\x01', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % self.encodeKey(self.jessica, pyamf.AMF3),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\x07foo\x06\x07bar',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)

    def test_save_amf0(self):
        self.put(self.jessica)

        bytes = pyamf.encode(self.jessica, encoding=pyamf.AMF0).getvalue()

        self.assertBuffer(bytes, ('\x03', (
            '\x00\x04_key%s' % self.encodeKey(self.jessica, pyamf.AMF0),
            '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
            '\x00\x04name\x02\x00\x07Jessica',
            '\x00\x12spayed_or_neutered\x01\x00',
            '\x00\x04type\x02\x00\x03cat',
            '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00',
            '\x00\x03foo\x02\x00\x03bar'),
            '\x00\x00\t'))

    def test_save_amf3(self):
        self.put(self.jessica)

        bytes = (
            '\n\x0b\x01', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % self.encodeKey(self.jessica, pyamf.AMF3),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\x07foo\x06\x07bar',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)

    def test_alias_amf0(self):
        pyamf.register_class(test_models.PetExpando, 'Pet')
        bytes = pyamf.encode(self.jessica, encoding=pyamf.AMF0).getvalue()

        self.assertBuffer(bytes, ('\x10\x00\x03Pet', (
            '\x00\x04_key%s' % self.encodeKey(self.jessica, pyamf.AMF0),
            '\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00\x00\x00\x00\x00',
            '\x00\x04name\x02\x00\x07Jessica',
            '\x00\x12spayed_or_neutered\x01\x00',
            '\x00\x04type\x02\x00\x03cat',
            '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00',
            '\x00\x03foo\x02\x00\x03bar'),
            '\x00\x00\t'))

    def test_alias_amf3(self):
        pyamf.register_class(test_models.PetExpando, 'Pet')

        bytes = (
            '\n\x0b\x07Pet', (
                '\tname\x06\x0fJessica',
                '\t_key%s' % self.encodeKey(self.jessica, pyamf.AMF3),
                '\x13birthdate\x08\x01B^\xc4\xae\xaa\x00\x00\x00',
                '!weight_in_pounds\x04\x05',
                '\x07foo\x06\x07bar',
                '\ttype\x06\x07cat',
                '%spayed_or_neutered\x02\x01'
            ))

        self.assertEncodes(self.jessica, bytes, encoding=pyamf.AMF3)


class EncodingReferencesTestCase(BaseTestCase):
    """
    This test case refers to L{db.ReferenceProperty<http://code.google.com/app
    engine/docs/datastore/typesandpropertyclasses.html#ReferenceProperty>},
    not AMF references.
    """

    def test_model(self):
        a = test_models.Author(name='Jane Austen')
        self.put(a)
        k = str(a.key())

        amf0_k = self.encodeKey(a, pyamf.AMF0)
        amf3_k = self.encodeKey(a, pyamf.AMF3)

        b = test_models.Novel(title='Sense and Sensibility', author=a)

        self.assertIdentical(b.author, a)

        bytes = (
            '\x03', (
                '\x00\x05title\x02\x00\x15Sense and Sensibility',
                '\x00\x04_key' + amf0_k,
                '\x00\x06author\x03', (
                    '\x00\x04name\x02\x00\x0bJane Austen',
                    '\x00\x04_key\x05'
                ),
                '\x00\x00\t'
            ),
            '\x00\x00\t')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF0)

        bytes = (
            '\n\x0b\x01', ((
                '\rauthor\n\x0b\x01', (
                    '\t_key' + amf3_k,
                    '\tname\x06\x17Jane Austen'
                ), '\x01\x06\x01'),
                '\x0btitle\x06+Sense and Sensibility'
            ),
            '\x01')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF3)

        # now test with aliases ..
        pyamf.register_class(test_models.Author, 'Author')
        pyamf.register_class(test_models.Novel, 'Novel')

        bytes = (
            '\x10\x00\x05Novel', (
                '\x00\x05title\x02\x00\x15Sense and Sensibility',
                '\x00\x04_key' + amf0_k,
                '\x00\x06author\x10\x00\x06Author', (
                    '\x00\x04name\x02\x00\x0bJane Austen',
                    '\x00\x04_key\x05'
                ),
                '\x00\x00\t'
            ),
            '\x00\x00\t')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF0)

        bytes = (
            '\n\x0b\x0bNovel', ((
                '\rauthor\n\x0b\rAuthor', (
                    '\t_key' + amf3_k,
                    '\tname\x06\x17Jane Austen'
                ), '\x01\n\x01'),
                '\x0btitle\x06+Sense and Sensibility'
            ),
            '\x01')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF3)

    def test_expando(self):
        class Author(db.Expando):
            name = db.StringProperty()

        class Novel(db.Expando):
            title = db.StringProperty()
            author = db.ReferenceProperty(Author)

        a = Author(name='Jane Austen')
        self.put(a)
        k = str(a.key())

        amf0_k = struct.pack('>H', len(k)) + k
        amf3_k = amf3.encode_int(len(k) << 1 | amf3.REFERENCE_BIT) + k

        b = Novel(title='Sense and Sensibility', author=a)

        self.assertIdentical(b.author, a)

        bytes = (
            '\x03', (
                '\x00\x05title\x02\x00\x15Sense and Sensibility',
                '\x00\x04_key\x02' + amf0_k,
                '\x00\x06author\x03', (
                    '\x00\x04name\x02\x00\x0bJane Austen',
                    '\x00\x04_key\x05'
                ),
                '\x00\x00\t'
            ),
            '\x00\x00\t')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF0)

        bytes = (
            '\n\x0b\x01', ((
                '\rauthor\n\x0b\x01', (
                    '\t_key\x06' + amf3_k,
                    '\tname\x06\x17Jane Austen\x01'
                ), '\x02\x01'),
                '\x0btitle\x06+Sense and Sensibility'
            ),
            '\x01')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF3)

        # now test with aliases ..
        pyamf.register_class(Author, 'Author')
        pyamf.register_class(Novel, 'Novel')

        bytes = (
            '\x10\x00\x05Novel', (
                '\x00\x05title\x02\x00\x15Sense and Sensibility',
                '\x00\x04_key\x02' + amf0_k,
                '\x00\x06author\x10\x00\x06Author', (
                    '\x00\x04name\x02\x00\x0bJane Austen',
                    '\x00\x04_key\x05'
                ),
                '\x00\x00\t'
            ),
            '\x00\x00\t')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF0)

        bytes = (
            '\n\x0b\x0bNovel', ((
                '\rauthor\n\x0b\rAuthor', (
                    '\t_key\x06' + amf3_k,
                    '\tname\x06\x17Jane Austen\x01'
                ), '\x06\x01'),
                '\x0btitle\x06+Sense and Sensibility'
            ),
            '\x01')

        self.assertEncodes(b, bytes, encoding=pyamf.AMF3)

    def test_dynamic_property_referenced_object(self):
        a = test_models.Author(name='Jane Austen')
        self.put(a)

        b = test_models.Novel(title='Sense and Sensibility', author=a)
        self.put(b)

        x = db.get(b.key())
        foo = [1, 2, 3]

        x.author.bar = foo

        ek = self.encodeKey(x, pyamf.AMF0)
        el = self.encodeKey(a, pyamf.AMF0)

        bytes = (
            '\x03', (
                '\x00\x05title\x02\x00\x15Sense and Sensibility',
                '\x00\x04_key' + ek,
                '\x00\x06author\x03', (
                    '\x00\x03bar\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00\x00'
                    '\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00@\x08\x00'
                    '\x00\x00\x00\x00\x00',
                    '\x00\x04name\x02\x00\x0bJane Austen',
                    '\x00\x04_key' + el
                ),
                '\x00\x00\t'
            ),
            '\x00\x00\t')

        self.assertEncodes(x, bytes, encoding=pyamf.AMF0)


class ListPropertyTestCase(BaseTestCase):
    """
    Tests for L{db.ListProperty} properties.
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.obj = test_models.ListModel()
        self.obj.numbers = [2, 4, 6, 8, 10]

        self.addCleanup(self.deleteEntity, self.obj)

    def test_encode_amf0(self):
        bytes = (
            '\x03', (
                '\x00\x04_key\x05',
                '\x00\x07numbers\n\x00\x00\x00\x05\x00@'
                '\x00\x00\x00\x00\x00\x00\x00\x00@\x10\x00\x00\x00\x00\x00'
                '\x00\x00@\x18\x00\x00\x00\x00\x00\x00\x00@\x20\x00\x00\x00'
                '\x00\x00\x00\x00@$\x00\x00\x00\x00\x00\x00'
            ),
            '\x00\x00\t'
        )

        self.assertEncodes(self.obj, bytes, encoding=pyamf.AMF0)

    def test_encode_amf3(self):
        bytes = (
            '\n\x0b\x01', (
                '\t_key\x01',
                '\x0fnumbers\t\x0b\x01\x04\x02\x04\x04\x04\x06\x04\x08\x04\n'
                    '\x01'
            )
        )

        self.assertEncodes(self.obj, bytes, encoding=pyamf.AMF3)

    def test_encode_amf0_registered(self):
        pyamf.register_class(test_models.ListModel, 'list-model')

        bytes = (
            '\x10\x00\nlist-model', (
                '\x00\x04_key\x05',
                '\x00\x07numbers\n\x00\x00\x00\x05\x00@'
                '\x00\x00\x00\x00\x00\x00\x00\x00@\x10\x00\x00\x00\x00\x00'
                '\x00\x00@\x18\x00\x00\x00\x00\x00\x00\x00@\x20\x00\x00\x00'
                '\x00\x00\x00\x00@$\x00\x00\x00\x00\x00\x00'
            ),
            '\x00\x00\t'
        )

        self.assertEncodes(self.obj, bytes, encoding=pyamf.AMF0)

    def test_encode_amf3_registered(self):
        pyamf.register_class(test_models.ListModel, 'list-model')

        bytes = (
            '\n\x0b\x15list-model', (
                '\t_key\x01',
                '\x0fnumbers\t\x0b\x01\x04\x02\x04\x04\x04\x06\x04\x08\x04\n'
                    '\x01'
            )
        )

        self.assertEncodes(self.obj, bytes, encoding=pyamf.AMF3)

    def _check_list(self, x):
        self.assertTrue(isinstance(x, test_models.ListModel))
        self.assertTrue(hasattr(x, 'numbers'))
        self.assertEqual(x.numbers, [2, 4, 6, 8, 10])

    def test_decode_amf0(self):
        pyamf.register_class(test_models.ListModel, 'list-model')

        bytes = (
            '\x10\x00\nlist-model\x00\x07numbers\n\x00\x00\x00\x05\x00@\x00'
            '\x00\x00\x00\x00\x00\x00\x00@\x10\x00\x00\x00\x00\x00\x00\x00@'
            '\x18\x00\x00\x00\x00\x00\x00\x00@ \x00\x00\x00\x00\x00\x00\x00@'
            '$\x00\x00\x00\x00\x00\x00\x00\x00\t')

        x = self.decode(bytes, encoding=pyamf.AMF0)
        self._check_list(x)

    def test_decode_amf3(self):
        pyamf.register_class(test_models.ListModel, 'list-model')

        bytes = (
            '\n\x0b\x15list-model\x0fnumbers\t\x0b\x01\x04\x02\x04\x04\x04'
            '\x06\x04\x08\x04\n\x01')

        x = self.decode(bytes, encoding=pyamf.AMF3)
        self._check_list(x)

    def test_none(self):
        pyamf.register_class(test_models.ListModel, 'list-model')

        bytes = '\x10\x00\nlist-model\x00\x07numbers\x05\x00\x00\t'

        x = self.decode(bytes, encoding=pyamf.AMF0)

        self.assertEqual(x.numbers, [])


class DecodingModelTestCase(BaseTestCase):
    """
    """

    def getModel(self):
        return test_models.PetModel

    def setUp(self):
        BaseTestCase.setUp(self)
        self.model_class = self.getModel()

        self.jessica = JessicaFactory.makeJessica(self.model_class)

        pyamf.register_class(self.model_class, 'Pet')

        self.put(self.jessica)
        self.key = str(self.jessica.key())

    def _check_model(self, x):
        self.assertTrue(isinstance(x, self.model_class))
        self.assertEqual(x.__class__, self.model_class)

        self.assertEqual(x.type, self.jessica.type)
        self.assertEqual(x.weight_in_pounds, self.jessica.weight_in_pounds)
        self.assertEqual(x.birthdate, self.jessica.birthdate)
        self.assertEqual(x.spayed_or_neutered, self.jessica.spayed_or_neutered)

        # now check db.Model internals
        self.assertEqual(x.key(), self.jessica.key())
        self.assertEqual(x.kind(), self.jessica.kind())
        self.assertEqual(x.parent(), self.jessica.parent())
        self.assertEqual(x.parent_key(), self.jessica.parent_key())
        self.assertTrue(x.is_saved())

    def test_amf0(self):
        bytes = (
            '\x10\x00\x03Pet\x00\x04_key%s\x00\x04type\x02\x00\x03cat'
            '\x00\x10weight_in_pounds\x00@\x14\x00\x00\x00\x00\x00\x00\x00'
            '\x04name\x02\x00\x07Jessica\x00\tbirthdate\x0bB^\xc4\xae\xaa\x00'
            '\x00\x00\x00\x00\x00\x12spayed_or_neutered\x01\x00\x00\x00\t' % (
                self.encodeKey(self.key, pyamf.AMF0),))

        x = self.decode(bytes, encoding=pyamf.AMF0)

        self._check_model(x)

    def test_amf3(self):
        bytes = (
            '\n\x0b\x07Pet\tname\x06\x0fJessica\t_key%s\x13birthdate'
            '\x08\x01B^\xc4\xae\xaa\x00\x00\x00!weight_in_pounds\x04\x05\x07'
            'foo\x06\x07bar\ttype\x06\x07cat%%spayed_or_neutered\x02\x01' % (
                self.encodeKey(self.key, pyamf.AMF3),))

        x = self.decode(bytes, encoding=pyamf.AMF3)

        self._check_model(x)


class DecodingExpandoTestCase(DecodingModelTestCase):
    """
    """

    def getModel(self):
        return test_models.PetExpando


class ClassAliasTestCase(BaseTestCase):
    """
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.alias = adapter_db.DataStoreClassAlias(test_models.PetModel, 'foo.bar')

        self.jessica = test_models.PetModel(name='Jessica', type='cat')
        self.jessica_expando = test_models.PetExpando(name='Jessica', type='cat')
        self.jessica_expando.foo = 'bar'

        self.addCleanup(self.deleteEntity, self.jessica)
        self.addCleanup(self.deleteEntity, self.jessica_expando)

    def test_get_alias(self):
        alias = pyamf.register_class(test_models.PetModel)

        self.assertTrue(isinstance(alias, adapter_db.DataStoreClassAlias))

    def test_alias(self):
        self.alias.compile()

        self.assertEqual(self.alias.decodable_properties, [
            'birthdate',
            'name',
            'spayed_or_neutered',
            'type',
            'weight_in_pounds'
        ])

        self.assertEqual(self.alias.encodable_properties, [
            'birthdate',
            'name',
            'spayed_or_neutered',
            'type',
            'weight_in_pounds'
        ])

        self.assertEqual(self.alias.static_attrs, [])
        self.assertEqual(self.alias.readonly_attrs, None)
        self.assertEqual(self.alias.exclude_attrs, None)
        self.assertEqual(self.alias.reference_properties, None)

    def test_create_instance(self):
        x = self.alias.createInstance()

        self.assertTrue(isinstance(x, adapter_db.ModelStub))

        self.assertTrue(hasattr(x, 'klass'))
        self.assertEqual(x.klass, self.alias.klass)

        # test some stub functions
        self.assertEqual(x.properties(), self.alias.klass.properties())
        self.assertEqual(x.dynamic_properties(), [])

    def test_apply(self):
        x = self.alias.createInstance()

        self.assertTrue(hasattr(x, 'klass'))

        self.alias.applyAttributes(x, {
            adapter_db.DataStoreClassAlias.KEY_ATTR: None,
            'name': 'Jessica',
            'type': 'cat',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None
        })

        self.assertFalse(hasattr(x, 'klass'))

    def test_get_attrs(self):
        attrs = self.alias.getEncodableAttributes(self.jessica)
        self.assertEqual(attrs, {
            '_key': None,
            'type': 'cat',
            'name': 'Jessica',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None
        })

    def test_get_attrs_expando(self):
        attrs = self.alias.getEncodableAttributes(self.jessica_expando)
        self.assertEqual(attrs, {
            '_key': None,
            'type': 'cat',
            'name': 'Jessica',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None,
            'foo': 'bar'
        })

    def test_get_attributes(self):
        attrs = self.alias.getEncodableAttributes(self.jessica)

        self.assertEqual(attrs, {
            '_key': None,
            'type': 'cat',
            'name': 'Jessica',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None
        })

    def test_get_attributes_saved(self):
        self.put(self.jessica)

        attrs = self.alias.getEncodableAttributes(self.jessica)

        self.assertEqual(attrs, {
            'name': 'Jessica',
            '_key': str(self.jessica.key()),
            'type': 'cat',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None
        })

    def test_get_attributes_expando(self):
        attrs = self.alias.getEncodableAttributes(self.jessica_expando)

        self.assertEqual(attrs, {
            'name': 'Jessica',
            '_key': None,
            'type': 'cat',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None,
            'foo': 'bar'
        })

    def test_get_attributes_saved_expando(self):
        self.put(self.jessica_expando)

        attrs = self.alias.getEncodableAttributes(self.jessica_expando)

        self.assertEqual(attrs, {
            'name': 'Jessica',
            '_key': str(self.jessica_expando.key()),
            'type': 'cat',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None,
            'foo': 'bar'
        })

    def test_arbitrary_properties(self):
        self.jessica.foo = 'bar'

        attrs = self.alias.getEncodableAttributes(self.jessica)

        self.assertEqual(attrs, {
            '_key': None,
            'type': 'cat',
            'name': 'Jessica',
            'birthdate': None,
            'weight_in_pounds': None,
            'spayed_or_neutered': None,
            'foo': 'bar'
        })

    def test_property_type(self):
        class PropertyTypeModel(db.Model):
            @property
            def readonly(self):
                return True

            def _get_prop(self):
                return False

            def _set_prop(self, v):
                self.prop = v

            read_write = property(_get_prop, _set_prop)

        alias = adapter_db.DataStoreClassAlias(PropertyTypeModel, 'foo.bar')

        obj = PropertyTypeModel()

        attrs = alias.getEncodableAttributes(obj)
        self.assertEqual(attrs, {
            '_key': None,
            'read_write': False,
            'readonly': True
        })

        self.assertFalse(hasattr(obj, 'prop'))

        alias.applyAttributes(obj, {
            '_key': None,
            'readonly': False,
            'read_write': 'foo'
        })

        self.assertEqual(obj.prop, 'foo')


class ReferencesTestCase(BaseTestCase):
    """
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        self.jessica = test_models.PetModel(name='Jessica', type='cat')
        self.jessica.birthdate = datetime.date(1986, 10, 2)
        self.jessica.weight_in_pounds = 5
        self.jessica.spayed_or_neutered = False

        self.put(self.jessica)

        self.jessica2 = db.get(self.jessica.key())

        self.assertNotIdentical(self.jessica,self.jessica2)
        self.assertEqual(str(self.jessica.key()), str(self.jessica2.key()))

    def failOnGet(self, *args, **kwargs):
        self.fail('Get attempted %r, %r' % (args, kwargs))

    def test_amf0(self):
        encoder = pyamf.get_encoder(pyamf.AMF0)
        stream = encoder.stream

        encoder.writeElement(self.jessica)

        stream.truncate()

        encoder.writeElement(self.jessica2)
        self.assertEqual(stream.getvalue(), '\x07\x00\x00')

    def test_amf3(self):
        encoder = pyamf.get_encoder(pyamf.AMF3)
        stream = encoder.stream

        encoder.writeElement(self.jessica)

        stream.truncate()

        encoder.writeElement(self.jessica2)
        self.assertEqual(stream.getvalue(), '\n\x00')

    def test_nullreference(self):
        c = test_models.Novel(title='Pride and Prejudice', author=None)
        self.put(c)

        encoder = pyamf.get_encoder(encoding=pyamf.AMF3)
        alias = adapter_db.DataStoreClassAlias(test_models.Novel, None)

        attrs = alias.getEncodableAttributes(c, codec=encoder)

        self.assertEqual(attrs, {
            '_key': str(c.key()),
            'title': 'Pride and Prejudice',
            'author': None
        })


class GAEReferenceCollectionTestCase(BaseTestCase):
    """
    """

    def setUp(self):
        BaseTestCase.setUp(self)
        self.klass = adapter_db.GAEReferenceCollection

    def test_init(self):
        x = self.klass()

        self.assertEqual(x, {})

    def test_get(self):
        x = self.klass()

        # not a class type
        self.assertRaises(TypeError, x.getClassKey, chr, '')
        # not a subclass of db.Model/db.Expando
        self.assertRaises(TypeError, x.getClassKey, Spam, '')

        x = self.klass()

        self.assertRaises(KeyError, x.getClassKey, test_models.PetModel, 'foo')
        self.assertEqual(x, {test_models.PetModel: {}})

        obj = object()

        x[test_models.PetModel]['foo'] = obj

        obj2 = x.getClassKey(test_models.PetModel, 'foo')

        self.assertEqual(id(obj), id(obj2))
        self.assertEqual(x, {test_models.PetModel: {'foo': obj}})

    def test_add(self):
        x = self.klass()

        # not a class type
        self.assertRaises(TypeError, x.addClassKey, chr, '')
        # not a subclass of db.Model/db.Expando
        self.assertRaises(TypeError, x.addClassKey, Spam, '')
        # wrong type for key
        self.assertRaises(TypeError, x.addClassKey, test_models.PetModel, 3)

        x = self.klass()
        pm1 = test_models.PetModel(type='cat', name='Jessica')
        pm2 = test_models.PetModel(type='dog', name='Sam')
        pe1 = test_models.PetExpando(type='cat', name='Toby')

        self.assertEqual(x, {})

        x.addClassKey(test_models.PetModel, 'foo', pm1)
        self.assertEqual(x, {test_models.PetModel: {'foo': pm1}})
        x.addClassKey(test_models.PetModel, 'bar', pm2)
        self.assertEqual(x, {test_models.PetModel: {'foo': pm1, 'bar': pm2}})
        x.addClassKey(test_models.PetExpando, 'baz', pe1)
        self.assertEqual(x, {
            test_models.PetModel: {'foo': pm1, 'bar': pm2},
            test_models.PetExpando: {'baz': pe1}
        })


class HelperTestCase(BaseTestCase):
    """
    """

    def test_getGAEObjects(self):
        context = Spam()
        context.extra = {}

        x = adapter_db.getGAEObjects(context)
        self.assertTrue(isinstance(x, adapter_db.GAEReferenceCollection))
        self.assertTrue('gae_objects' in context.extra)
        self.assertEqual(id(x), id(context.extra['gae_objects']))

    def test_Query_type(self):
        """
        L{db.Query} instances get converted to lists ..
        """
        q = test_models.EmptyModel.all()

        self.assertTrue(isinstance(q, db.Query))
        self.assertEncodes(q, '\n\x00\x00\x00\x00', encoding=pyamf.AMF0)
        self.assertEncodes(q, '\t\x01\x01', encoding=pyamf.AMF3)


class FloatPropertyTestCase(BaseTestCase):
    """
    Tests for #609.
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        class FloatModel(db.Model):
            f = db.FloatProperty()

        self.klass = FloatModel
        self.f = FloatModel()
        self.alias = adapter_db.DataStoreClassAlias(self.klass, None)

    def tearDown(self):
        BaseTestCase.tearDown(self)

        if self.f.is_saved():
            self.f.delete()

    def test_behaviour(self):
        """
        Test the behaviour of the Google SDK not handling ints gracefully
        """
        self.assertRaises(db.BadValueError, setattr, self.f, 'f', 3)

        self.f.f = 3.0

        self.assertEqual(self.f.f, 3.0)

    def test_apply_attributes(self):
        self.alias.applyAttributes(self.f, {'f': 3})

        self.assertEqual(self.f.f, 3.0)


class PolyModelTestCase(BaseTestCase):
    """
    Tests for L{db.PolyModel}. See #633
    """

    def setUp(self):
        BaseTestCase.setUp(self)

        class Poly(polymodel.PolyModel):
            s = db.StringProperty()

        self.klass = Poly
        self.p = Poly()
        self.alias = adapter_db.DataStoreClassAlias(self.klass, None)

    def test_encode(self):
        self.p.s = 'foo'

        attrs = self.alias.getEncodableAttributes(self.p)

        self.assertEqual(attrs, {'_key': None, 's': 'foo'})

    def test_deep_inheritance(self):
        class DeepPoly(self.klass):
            d = db.IntegerProperty()

        self.alias = adapter_db.DataStoreClassAlias(DeepPoly, None)
        self.dp = DeepPoly()
        self.dp.s = 'bar'
        self.dp.d = 92

        attrs = self.alias.getEncodableAttributes(self.dp)

        self.assertEqual(attrs, {
            '_key': None,
            's': 'bar',
            'd': 92
        })


class BlobStoreTestCase(BaseTestCase):
    """
    Tests for L{blobstore}
    """

    bytes = (
        '\n\x0bOgoogle.appengine.ext.blobstore.BlobInfo', (
            '\tsize\x04\xcb\xad\x07',
            '\x11creation\x08\x01Br\x9c\x1d\xbeh\x80\x00',
            '\x07key\x06\rfoobar',
            '\x19content_type\x06\x15text/plain',
            '\x11filename\x06\x1fnot-telling.ogg'
        ), '\x01')

    values = {
        'content_type': 'text/plain',
        'size': 1234567,
        'filename': 'not-telling.ogg',
        'creation': datetime.datetime(2010, 07, 11, 14, 15, 01)
    }

    def setUp(self):
        BaseTestCase.setUp(self)

        self.key = blobstore.BlobKey('foobar')

        self.info = blobstore.BlobInfo(self.key, self.values)

    def test_class_alias(self):
        alias_klass = pyamf.get_class_alias(blobstore.BlobInfo)

        self.assertIdentical(alias_klass.__class__, adapter_blobstore.BlobInfoClassAlias)

    def test_encode(self):
        self.assertEncodes(self.info, self.bytes)

    def test_decode(self):
        def check(ret):
            self.assertEqual(ret.key(), self.key)

        self.assertDecodes(self.bytes, check)

########NEW FILE########
__FILENAME__ = test_sqlalchemy
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF SQLAlchemy adapter tests.

@since 0.4
"""

import unittest

try:
    import sqlalchemy
    from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, \
        create_engine
    from sqlalchemy.orm import mapper, relation, sessionmaker, clear_mappers

    from pyamf.adapters import _sqlalchemy_orm as adapter
except ImportError:
    sqlalchemy = None

import pyamf.flex
from pyamf.tests.util import Spam


class BaseObject(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class User(BaseObject):
    def __init__(self, **kwargs):
        BaseObject.__init__(self, **kwargs)

        self.lazy_loaded = [LazyLoaded()]


class Address(BaseObject):
    pass


class LazyLoaded(BaseObject):
    pass


class AnotherLazyLoaded(BaseObject):
    pass


class BaseTestCase(unittest.TestCase):
    """
    Initialise up all table/mappers.
    """

    def setUp(self):
        if not sqlalchemy:
            self.skipTest("'sqlalchemy' is not available")

        # Create DB and map objects
        self.metadata = MetaData()
        self.engine = create_engine('sqlite:///:memory:', echo=False)

        Session = sessionmaker(bind=self.engine)

        self.session = Session()
        self.tables = {}

        self.tables['users'] = Table('users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(64)))

        self.tables['addresses'] = Table('addresses', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id')),
            Column('email_address', String(128)))

        self.tables['lazy_loaded'] = Table('lazy_loaded', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id')))

        self.tables['another_lazy_loaded'] = Table('another_lazy_loaded', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id')))

        self.mappers = {}

        self.mappers['user'] = mapper(User, self.tables['users'], properties={
            'addresses': relation(Address, backref='user', lazy=False),
            'lazy_loaded': relation(LazyLoaded, lazy=True),
            'another_lazy_loaded': relation(AnotherLazyLoaded, lazy=True)
        })

        self.mappers['addresses'] = mapper(Address, self.tables['addresses'])
        self.mappers['lazy_loaded'] = mapper(LazyLoaded,
            self.tables['lazy_loaded'])
        self.mappers['another_lazy_loaded'] = mapper(AnotherLazyLoaded,
            self.tables['another_lazy_loaded'])

        self.metadata.create_all(self.engine)

        pyamf.register_class(User, 'server.User')
        pyamf.register_class(Address, 'server.Address')
        pyamf.register_class(LazyLoaded, 'server.LazyLoaded')

    def tearDown(self):
        clear_mappers()

        pyamf.unregister_class(User)
        pyamf.unregister_class(Address)
        pyamf.unregister_class(LazyLoaded)

    def _build_obj(self):
        user = User()
        user.name = "test_user"
        user.addresses.append(Address(email_address="test@example.org"))

        return user

    def _save(self, obj):
        # this covers deprecation warnings etc.
        if hasattr(self.session, 'add'):
            self.session.add(obj)
        elif hasattr(self.session, 'save'):
            self.session.save(obj)
        else:
            raise AttributeError('Don\'t know how to save an object')

    def _clear(self):
        # this covers deprecation warnings etc.
        if hasattr(self.session, 'expunge_all'):
            self.session.expunge_all()
        elif hasattr(self.session, 'clear'):
            self.session.clear()
        else:
            raise AttributeError('Don\'t know how to clear session')


class SATestCase(BaseTestCase):
    def _test_obj(self, encoded, decoded):
        self.assertEqual(User, decoded.__class__)
        self.assertEqual(encoded.name, decoded.name)
        self.assertEqual(encoded.addresses[0].email_address, decoded.addresses[0].email_address)

    def test_encode_decode_transient(self):
        user = self._build_obj()

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(user)
        encoded = encoder.stream.getvalue()
        decoded = pyamf.get_decoder(pyamf.AMF3, encoded).readElement()

        self._test_obj(user, decoded)

    def test_encode_decode_persistent(self):
        user = self._build_obj()
        self._save(user)
        self.session.commit()
        self.session.refresh(user)

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(user)
        encoded = encoder.stream.getvalue()
        decoded = pyamf.get_decoder(pyamf.AMF3, encoded).readElement()

        self._test_obj(user, decoded)

    def test_encode_decode_list(self):
        max = 5
        for i in range(0, max):
            user = self._build_obj()
            user.name = "%s" % i
            self._save(user)

        self.session.commit()
        users = self.session.query(User).all()

        encoder = pyamf.get_encoder(pyamf.AMF3)

        encoder.writeElement(users)
        encoded = encoder.stream.getvalue()
        decoded = pyamf.get_decoder(pyamf.AMF3, encoded).readElement()
        self.assertEqual([].__class__, decoded.__class__)

        for i in range(0, max):
            self._test_obj(users[i], decoded[i])

    def test_sa_merge(self):
        user = self._build_obj()

        for i, string in enumerate(['one', 'two', 'three']):
            addr = Address(email_address="%s@example.org" % string)
            user.addresses.append(addr)

        self._save(user)
        self.session.commit()
        self.session.refresh(user)

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(user)
        encoded = encoder.stream.getvalue()

        decoded = pyamf.get_decoder(pyamf.AMF3, encoded).readElement()
        del decoded.addresses[0]
        del decoded.addresses[1]

        merged_user = self.session.merge(decoded)
        self.assertEqual(len(merged_user.addresses), 2)

    def test_encode_decode_with_references(self):
        user = self._build_obj()
        self._save(user)
        self.session.commit()
        self.session.refresh(user)

        max = 5
        users = []
        for i in range(0, max):
            users.append(user)

        encoder = pyamf.get_encoder(pyamf.AMF3)
        encoder.writeElement(users)
        encoded = encoder.stream.getvalue()

        decoded = pyamf.get_decoder(pyamf.AMF3, encoded).readElement()

        for i in range(0, max):
            self.assertEqual(id(decoded[0]), id(decoded[i]))


class BaseClassAliasTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.alias = pyamf.get_class_alias(User)


class ClassAliasTestCase(BaseClassAliasTestCase):
    def test_type(self):
        self.assertEqual(self.alias.__class__, adapter.SaMappedClassAlias)

    def test_get_mapper(self):
        self.assertFalse(hasattr(self.alias, 'mapper'))

        self.alias.compile()
        mapper = adapter.class_mapper(User)

        self.assertTrue(hasattr(self.alias, 'mapper'))
        self.assertEqual(id(mapper), id(self.alias.mapper))

        self.assertEqual(self.alias.static_attrs, [])

    def test_get_attrs(self):
        u = self._build_obj()
        attrs = self.alias.getEncodableAttributes(u)

        self.assertEqual(sorted(attrs.keys()), [
            'addresses',
            'another_lazy_loaded',
            'id',
            'lazy_loaded',
            'name',
            'sa_key',
            'sa_lazy'
        ])

        self.assertEqual(attrs['sa_key'], [None])
        self.assertEqual(attrs['sa_lazy'], [])

    def test_get_attributes(self):
        u = self._build_obj()

        self.assertFalse(u in self.session)
        self.assertEqual([None], self.mappers['user'].primary_key_from_instance(u))
        attrs = self.alias.getEncodableAttributes(u)

        self.assertEqual(attrs, {
            'addresses': u.addresses,
            'lazy_loaded': u.lazy_loaded,
            'another_lazy_loaded': [],
            'id': None,
            'name': 'test_user',
            'sa_lazy': [],
            'sa_key': [None]
        })

    def test_property(self):
        class Person(object):
            foo = 'bar'
            baz = 'gak'

            def _get_rw_property(self):
                return self.foo

            def _set_rw_property(self, val):
                self.foo = val

            def _get_ro_property(self):
                return self.baz

            rw = property(_get_rw_property, _set_rw_property)
            ro = property(_get_ro_property)

        self.mappers['person'] = mapper(Person, self.tables['users'])

        alias = adapter.SaMappedClassAlias(Person, 'person')

        obj = Person()

        attrs = alias.getEncodableAttributes(obj)
        self.assertEqual(attrs, {
            'id': None,
            'name': None,
            'sa_key': [None],
            'sa_lazy': [],
            'rw': 'bar',
            'ro': 'gak'})

        self.assertEqual(obj.ro, 'gak')
        alias.applyAttributes(obj, {
            'sa_key': [None],
            'sa_lazy': [],
            'id': None,
            'name': None,
            'rw': 'bar',
            'ro': 'baz'})
        self.assertEqual(obj.ro, 'gak')


class ApplyAttributesTestCase(BaseClassAliasTestCase):
    def test_undefined(self):
        u = self.alias.createInstance()

        attrs = {
            'sa_lazy': ['another_lazy_loaded'],
            'sa_key': [None],
            'addresses': [],
            'lazy_loaded': [],
            'another_lazy_loaded': pyamf.Undefined, # <-- the important bit
            'id': None,
            'name': 'test_user'
        }

        self.alias.applyAttributes(u, attrs)

        d = u.__dict__.copy()

        if sqlalchemy.__version__.startswith('0.4'):
            self.assertTrue('_state' in d)
            del d['_state']
        else:
            self.assertTrue('_sa_instance_state' in d)
            del d['_sa_instance_state']

        self.assertEqual(d, {
            'lazy_loaded': [],
            'addresses': [],
            'name': 'test_user',
            'id': None
        })

    def test_decode_unaliased(self):
        u = self.alias.createInstance()

        attrs = {
            'sa_lazy': [],
            'sa_key': [None],
            'addresses': [],
            'lazy_loaded': [],
            # this is important because we haven't registered AnotherLazyLoaded
            # as an alias and the decoded object for an untyped object is an
            # instance of pyamf.ASObject
            'another_lazy_loaded': [pyamf.ASObject({'id': 1, 'user_id': None})],
            'id': None,
            'name': 'test_user'
        }

        # sqlalchemy can't find any state to work with
        self.assertRaises(AttributeError, self.alias.applyAttributes, u, attrs)


class AdapterTestCase(BaseTestCase):
    """
    Checks to see if the adapter will actually intercept a class correctly.
    """

    def test_mapped(self):
        self.assertNotEquals(None, adapter.class_mapper(User))
        self.assertTrue(adapter.is_class_sa_mapped(User))

    def test_instance(self):
        u = User()

        self.assertTrue(adapter.is_class_sa_mapped(u))

    def test_not_mapped(self):
        self.assertRaises(adapter.UnmappedInstanceError, adapter.class_mapper, Spam)
        self.assertFalse(adapter.is_class_sa_mapped(Spam))


class ExcludableAttrsTestCase(BaseTestCase):
    """
    Tests for #790
    """

    def test_core_attrs(self):
        """
        Ensure that sa_key and sa_lazy can be excluded
        """
        a = adapter.SaMappedClassAlias(Address, exclude_attrs=['sa_lazy', 'sa_key'])
        u = Address()

        attrs = a.getEncodableAttributes(u)

        self.assertFalse('sa_key' in attrs)
        self.assertFalse('sa_lazy' in attrs)
########NEW FILE########
__FILENAME__ = test_weakref
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
PyAMF weakref adapter tests.

@since 0.6.2
"""

import unittest
import weakref

import pyamf



class Foo(object):
    """
    A simple class that weakref can use to do its thing. Builtin types cannot
    be weakref'd.
    """



class BaseTestCase(unittest.TestCase):
    """
    Tests for L{pyamf.adapters.weakref}.
    """


    def getReferent(self):
        return Foo()


    def getReference(self, obj):
        """
        Must return a weakref to L{obj}
        """
        raise NotImplementedError


    def _assertEncoding(self, encoding, obj, ref):
        obj_bytes = pyamf.encode(obj, encoding=encoding).getvalue()
        ref_bytes = pyamf.encode(ref, encoding=encoding).getvalue()

        self.assertEqual(obj_bytes, ref_bytes)


    def test_amf0(self):
        """
        Encoding a weakref must be identical to the referenced object.
        """
        if self.__class__ == BaseTestCase:
            return

        obj = self.getReferent()
        ref = self.getReference(obj)

        self._assertEncoding(pyamf.AMF0, obj, ref)


    def test_amf3(self):
        """
        Encoding a weakref must be identical to the referenced object.
        """
        if self.__class__ == BaseTestCase:
            return

        obj = self.getReferent()
        ref = self.getReference(obj)

        self._assertEncoding(pyamf.AMF3, obj, ref)



class ReferentTestCase(BaseTestCase):
    """
    Tests for L{weakref.ref}
    """

    def getReference(self, obj):
        return weakref.ref(obj)



class ProxyTestCase(BaseTestCase):
    """
    Tests for L{weakref.proxy}
    """

    def getReference(self, obj):
        return weakref.proxy(obj)



class WeakValueDictionaryTestCase(BaseTestCase):
    """
    Tests for L{weakref.WeakValueDictionary}
    """

    def getReferent(self):
        return {'bar': Foo(), 'gak': Foo(), 'spam': Foo()}


    def getReference(self, obj):
        return weakref.WeakValueDictionary(obj)



class WeakSetTestCase(BaseTestCase):
    """
    Tests for L{weakref.WeakSet}
    """

    def getReferent(self):
        return Foo(), Foo(), Foo()


    def getReference(self, obj):
        return weakref.WeakSet(obj)



if not hasattr(weakref, 'WeakSet'):
    # WeakSet is Py2.7+
    WeakSetTestCase = None

########NEW FILE########
__FILENAME__ = _google_models
from google.appengine.ext import db


class PetModel(db.Model):
    """
    """

    # 'borrowed' from http://code.google.com/appengine/docs/datastore/entitiesandmodels.html
    name = db.StringProperty(required=True)
    type = db.StringProperty(required=True, choices=set(["cat", "dog", "bird"]))
    birthdate = db.DateProperty()
    weight_in_pounds = db.IntegerProperty()
    spayed_or_neutered = db.BooleanProperty()


class PetExpando(db.Expando):
    """
    """

    name = db.StringProperty(required=True)
    type = db.StringProperty(required=True, choices=set(["cat", "dog", "bird"]))
    birthdate = db.DateProperty()
    weight_in_pounds = db.IntegerProperty()
    spayed_or_neutered = db.BooleanProperty()


class ListModel(db.Model):
    """
    """
    numbers = db.ListProperty(long)


class GettableModelStub(db.Model):
    """
    """

    gets = []

    @staticmethod
    def get(*args, **kwargs):
        GettableModelStub.gets.append([args, kwargs])


class Author(db.Model):
    name = db.StringProperty()


class Novel(db.Model):
    title = db.StringProperty()
    author = db.ReferenceProperty(Author)


class EmptyModel(db.Model):
    """
    A model that has no properties but also has no entities in the datastore.
    """

########NEW FILE########
__FILENAME__ = test_django
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Django gateway tests.

@since: 0.1.0
"""

import unittest
import sys
import os

try:
    from django import http
    from pyamf.remoting.gateway import django
except ImportError:
    django = None

import pyamf
from pyamf import remoting, util


class BaseTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not django:
            self.skipTest("'django' not available")


class DjangoGatewayTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        import new

        self.mod_name = '%s.%s' % (__name__, 'settings')
        sys.modules[self.mod_name] = new.module(self.mod_name)

        self.old_env = os.environ.get('DJANGO_SETTINGS_MODULE', None)

        os.environ['DJANGO_SETTINGS_MODULE'] = self.mod_name

    def tearDown(self):
        if self.old_env is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = self.old_env

        del sys.modules[self.mod_name]

    def test_csrf(self):
        gw = django.DjangoGateway()

        self.assertTrue(gw.csrf_exempt)

    def test_settings(self):
        from django import conf

        settings_mod = sys.modules[self.mod_name]

        settings_mod.DEBUG = True
        settings_mod.AMF_TIME_OFFSET = 1000

        old_settings = conf.settings
        conf.settings = conf.Settings(self.mod_name)

        gw = django.DjangoGateway()

        try:
            self.assertTrue(gw.debug)
            self.assertEqual(gw.timezone_offset, 1000)
        finally:
            conf.settings = old_settings

    def test_request_method(self):
        gw = django.DjangoGateway()

        http_request = http.HttpRequest()
        http_request.method = 'GET'

        http_response = gw(http_request)
        self.assertEqual(http_response.status_code, 405)

    def test_bad_request(self):
        gw = django.DjangoGateway()

        request = util.BufferedByteStream()
        request.write('Bad request')
        request.seek(0, 0)

        http_request = http.HttpRequest()
        http_request.method = 'POST'
        http_request.raw_post_data = request.getvalue()

        http_response = gw(http_request)
        self.assertEqual(http_response.status_code, 400)

    def test_unknown_request(self):
        gw = django.DjangoGateway()

        request = util.BufferedByteStream()
        request.write('\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00'
            '\x02/1\x00\x00\x00\x14\x0a\x00\x00\x00\x01\x08\x00\x00\x00\x00'
            '\x00\x01\x61\x02\x00\x01\x61\x00\x00\x09')
        request.seek(0, 0)

        http_request = http.HttpRequest()
        http_request.method = 'POST'
        http_request.raw_post_data = request.getvalue()

        http_response = gw(http_request)
        envelope = remoting.decode(http_response.content)

        message = envelope['/1']

        self.assertEqual(message.status, remoting.STATUS_ERROR)
        body = message.body

        self.assertTrue(isinstance(body, remoting.ErrorFault))
        self.assertEqual(body.code, 'Service.ResourceNotFound')

    def test_expose_request(self):
        http_request = http.HttpRequest()
        self.executed = False

        def test(request):
            self.assertEqual(http_request, request)
            self.assertTrue(hasattr(request, 'amf_request'))
            self.executed = True

        gw = django.DjangoGateway({'test.test': test}, expose_request=True)

        request = util.BufferedByteStream()
        request.write('\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00'
            '\x02/1\x00\x00\x00\x05\x0a\x00\x00\x00\x00')
        request.seek(0, 0)

        http_request.method = 'POST'
        http_request.raw_post_data = request.getvalue()

        gw(http_request)

        self.assertTrue(self.executed)

    def _raiseException(self, e, *args, **kwargs):
        raise e()

    def test_really_bad_decode(self):
        self.old_method = remoting.decode
        remoting.decode = lambda *args, **kwargs: self._raiseException(Exception, *args, **kwargs)

        http_request = http.HttpRequest()
        http_request.method = 'POST'
        http_request.raw_post_data = ''

        gw = django.DjangoGateway()

        try:
            http_response = gw(http_request)
        except:
            remoting.decode = self.old_method

            raise

        remoting.decode = self.old_method

        self.assertTrue(isinstance(http_response, http.HttpResponseServerError))
        self.assertEqual(http_response.status_code, 500)
        self.assertEqual(http_response.content, '500 Internal Server Error\n\nAn unexpected error occurred.')

    def test_expected_exceptions_decode(self):
        self.old_method = remoting.decode

        gw = django.DjangoGateway()

        http_request = http.HttpRequest()
        http_request.method = 'POST'
        http_request.raw_post_data = ''

        try:
            for x in (KeyboardInterrupt, SystemExit):
                remoting.decode = lambda *args, **kwargs: self._raiseException(x, *args, **kwargs)
                self.assertRaises(x, gw, http_request)
        except:
            remoting.decode = self.old_method

            raise

        remoting.decode = self.old_method

    def test_timezone(self):
        import datetime

        http_request = http.HttpRequest()
        self.executed = False

        td = datetime.timedelta(hours=-5)
        now = datetime.datetime.utcnow()

        def echo(d):
            self.assertEqual(d, now + td)
            self.executed = True

            return d

        gw = django.DjangoGateway({'test.test': echo}, timezone_offset=-18000,
            expose_request=False)

        msg = remoting.Envelope(amfVersion=pyamf.AMF0)
        msg['/1'] = remoting.Request(target='test.test', body=[now])

        http_request.method = 'POST'
        http_request.raw_post_data = remoting.encode(msg).getvalue()

        res = remoting.decode(gw(http_request).content)
        self.assertTrue(self.executed)

        self.assertEqual(res['/1'].body, now)

########NEW FILE########
__FILENAME__ = test_google
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Google Web App gateway tests.

@since: 0.3.1
"""

import unittest
import os

from StringIO import StringIO

try:
    from google.appengine.ext import webapp
    from pyamf.remoting.gateway import google as google
except ImportError:
    webapp = None

if os.environ.get('SERVER_SOFTWARE', None) is None:
    # we're not being run in appengine environment (at one that we are known to
    # work in)
    webapp = None


import pyamf
from pyamf import remoting


class BaseTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not webapp:
            self.skipTest("'google' is not available")


class WebAppGatewayTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.gw = google.WebAppGateway()

        self.environ = {
            'wsgi.input': StringIO(),
            'wsgi.output': StringIO()
        }

        self.request = webapp.Request(self.environ)
        self.response = webapp.Response()

        self.gw.initialize(self.request, self.response)

    def test_get(self):
        self.gw.get()

        self.assertEqual(self.response.__dict__['_Response__status'][0], 405)

    def test_bad_request(self):
        self.environ['wsgi.input'].write('Bad request')
        self.environ['wsgi.input'].seek(0, 0)

        self.gw.post()
        self.assertEqual(self.response.__dict__['_Response__status'][0], 400)

    def test_unknown_request(self):
        self.environ['wsgi.input'].write(
            '\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00\x02/1\x00\x00\x00'
            '\x14\x0a\x00\x00\x00\x01\x08\x00\x00\x00\x00\x00\x01\x61\x02\x00'
            '\x01\x61\x00\x00\x09')
        self.environ['wsgi.input'].seek(0, 0)

        self.gw.post()

        self.assertEqual(self.response.__dict__['_Response__status'][0], 200)

        envelope = remoting.decode(self.response.out.getvalue())
        message = envelope['/1']

        self.assertEqual(message.status, remoting.STATUS_ERROR)
        body = message.body

        self.assertTrue(isinstance(body, remoting.ErrorFault))
        self.assertEqual(body.code, 'Service.ResourceNotFound')

    def test_expose_request(self):
        self.executed = False

        def test(request):
            self.assertEqual(self.request, request)
            self.assertTrue(hasattr(self.request, 'amf_request'))

            self.executed = True

        self.gw.expose_request = True
        self.gw.addService(test, 'test.test')

        self.environ['wsgi.input'].write('\x00\x00\x00\x00\x00\x01\x00\x09'
            'test.test\x00\x02/1\x00\x00\x00\x05\x0a\x00\x00\x00\x00')
        self.environ['wsgi.input'].seek(0, 0)

        self.gw.post()

        self.assertTrue(self.executed)

    def test_timezone(self):
        import datetime

        self.executed = False

        td = datetime.timedelta(hours=-5)
        now = datetime.datetime.utcnow()

        def echo(d):
            self.assertEqual(d, now + td)
            self.executed = True

            return d

        self.gw.addService(echo)
        self.gw.timezone_offset = -18000

        msg = remoting.Envelope(amfVersion=pyamf.AMF0)
        msg['/1'] = remoting.Request(target='echo', body=[now])

        stream = remoting.encode(msg)
        self.environ['wsgi.input'] = stream
        self.gw.post()

        envelope = remoting.decode(self.response.out.getvalue())
        message = envelope['/1']

        self.assertEqual(message.body, now)
        self.assertTrue(self.executed)

########NEW FILE########
__FILENAME__ = test_twisted
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Twisted gateway tests.

@since: 0.1.0
"""

try:
    from twisted.internet import reactor, defer
    from twisted.python import failure
    from twisted.web import http, server, client, error, resource
    from twisted.trial import unittest

    from pyamf.remoting.gateway import twisted
except ImportError:
    twisted = None

    import unittest

import pyamf
from pyamf import remoting
from pyamf.remoting import gateway
from pyamf.flex import messaging


class TestService(object):
    def spam(self):
        return 'spam'

    def echo(self, x):
        return x


class BaseTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        if not twisted:
            self.skipTest("'twisted' is not available")


class TwistedServerTestCase(BaseTestCase):
    """
    """

    missing = object()

    def setUp(self):
        BaseTestCase.setUp(self)

        self.gw = twisted.TwistedGateway(expose_request=False)
        root = resource.Resource()
        root.putChild('', self.gw)

        self.p = reactor.listenTCP(0, server.Site(root), interface="127.0.0.1")
        self.port = self.p.getHost().port

    def tearDown(self):
        self.p.stopListening()

    def getPage(self, data=None, **kwargs):
        kwargs.setdefault('method', 'POST')
        kwargs['postdata'] = data

        return client.getPage("http://127.0.0.1:%d/" % (self.port,), **kwargs)

    def doRequest(self, service, body=missing, type=pyamf.AMF3, raw=False, decode=True):
        if not raw:
            if body is self.missing:
                body = []
            else:
                body = [body]

            env = remoting.Envelope(type)
            request = remoting.Request(service, body=body)
            env['/1'] = request

            body = remoting.encode(env).getvalue()

        d = self.getPage(body)

        if decode:
            d.addCallback(lambda result: remoting.decode(result))

        return d

    def test_invalid_method(self):
        """
        A classic GET on the xml server should return a NOT_ALLOWED.
        """
        d = self.getPage(method='GET')
        d = self.assertFailure(d, error.Error)
        d.addCallback(
            lambda exc: self.assertEqual(int(exc.args[0]), http.NOT_ALLOWED))

        return d

    def test_bad_content(self):
        d = self.getPage('spamandeggs')
        d = self.assertFailure(d, error.Error)

        d.addCallback(
            lambda exc: self.assertEqual(int(exc.args[0]), http.BAD_REQUEST))

        return d

    def test_process_request(self):
        def echo(data):
            return data

        self.gw.addService(echo)

        d = self.doRequest('echo', 'hello')

        def cb(response):
            self.assertEqual(response.amfVersion, pyamf.AMF3)

            self.assertTrue('/1' in response)
            body_response = response['/1']

            self.assertEqual(body_response.status, remoting.STATUS_OK)
            self.assertEqual(body_response.body, 'hello')

        return d.addCallback(cb)

    def test_deferred_service(self):
        def echo(data):
            x = defer.Deferred()
            reactor.callLater(0, x.callback, data)

            return x

        self.gw.addService(echo)
        d = self.doRequest('echo', 'hello')

        def cb(response):
            self.assertEqual(response.amfVersion, pyamf.AMF3)

            self.assertTrue('/1' in response)
            body_response = response['/1']

            self.assertEqual(body_response.status, remoting.STATUS_OK)
            self.assertEqual(body_response.body, 'hello')

        return d.addCallback(cb)

    def test_unknown_request(self):
        d = self.doRequest('echo', 'hello')

        def cb(response):
            message = response['/1']

            self.assertEqual(message.status, remoting.STATUS_ERROR)
            body = message.body

            self.assertTrue(isinstance(body, remoting.ErrorFault))
            self.assertEqual(body.code, 'Service.ResourceNotFound')

        return d.addCallback(cb)

    def test_expose_request(self):
        self.gw.expose_request = True
        self.executed = False

        def echo(http_request, data):
            self.assertTrue(isinstance(http_request, http.Request))

            self.assertTrue(hasattr(http_request, 'amf_request'))

            amf_request = http_request.amf_request

            self.assertEqual(amf_request.target, 'echo')
            self.assertEqual(amf_request.body, ['hello'])
            self.executed = True

            return data

        self.gw.addService(echo)

        d = self.doRequest('echo', 'hello', type=pyamf.AMF0)

        def check_response(response):
            self.assertTrue(self.executed)

        return d.addCallback(check_response)

    def test_preprocessor(self):
        d = defer.Deferred()

        def pp(sr):
            self.assertIdentical(sr, self.service_request)
            d.callback(None)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, preprocessor=pp)
        self.service_request = gateway.ServiceRequest(None, gw.services['echo'], None)

        gw.preprocessRequest(self.service_request)

        return d

    def test_exposed_preprocessor(self):
        d = defer.Deferred()

        def pp(hr, sr):
            self.assertEqual(hr, 'hello')
            self.assertIdentical(sr, self.service_request)
            d.callback(None)

        pp = gateway.expose_request(pp)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, preprocessor=pp)
        self.service_request = gateway.ServiceRequest(None, gw.services['echo'], None)

        gw.preprocessRequest(self.service_request, http_request='hello')

        return d

    def test_exposed_preprocessor_no_request(self):
        d = defer.Deferred()

        def pp(hr, sr):
            self.assertEqual(hr, None)
            self.assertIdentical(sr, self.service_request)
            d.callback(None)

        pp = gateway.expose_request(pp)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, preprocessor=pp)
        self.service_request = gateway.ServiceRequest(None, gw.services['echo'], None)

        gw.preprocessRequest(self.service_request)

        return d

    def test_authenticate(self):
        d = defer.Deferred()

        def auth(u, p):
            try:
                self.assertEqual(u, 'u')
                self.assertEqual(p, 'p')
            except:
                d.errback(failure.Failure())
            else:
                d.callback(None)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, authenticator=auth)
        self.service_request = gateway.ServiceRequest(None, gw.services['echo'], None)

        gw.authenticateRequest(self.service_request, 'u', 'p')

        return d

    def test_exposed_authenticate(self):
        d = defer.Deferred()

        def auth(request, u, p):
            try:
                self.assertEqual(request, 'foo')
                self.assertEqual(u, 'u')
                self.assertEqual(p, 'p')
            except:
                d.errback(failure.Failure())
            else:
                d.callback(None)

        auth = gateway.expose_request(auth)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, authenticator=auth)
        self.service_request = gateway.ServiceRequest(None, gw.services['echo'], None)

        gw.authenticateRequest(self.service_request, 'u', 'p', http_request='foo')

        return d

    def test_encoding_error(self):
        encode = twisted.remoting.encode

        def force_error(amf_request, context=None):
            raise pyamf.EncodeError

        def echo(request, data):
            return data

        self.gw.addService(echo)

        d = self.doRequest('echo', 'hello')
        twisted.remoting.encode = force_error

        def switch(x):
            twisted.remoting.encode = encode

        d = self.assertFailure(d, error.Error)

        def check(exc):
            self.assertEqual(int(exc.args[0]), http.INTERNAL_SERVER_ERROR)
            self.assertTrue(exc.args[1].startswith('500 Internal Server Error'))

        d.addCallback(check)

        return d.addBoth(switch)

    def test_tuple(self):
        def echo(data):
            return data

        self.gw.addService(echo)
        d = self.doRequest('echo', ('Hi', 'Mom'))

        def cb(response):
            body_response = response['/1']

            self.assertEqual(body_response.status, remoting.STATUS_OK)
            self.assertEqual(body_response.body, ['Hi', 'Mom'])

        return d.addCallback(cb)

    def test_timezone(self):
        import datetime

        self.executed = False

        td = datetime.timedelta(hours=-5)
        now = datetime.datetime.utcnow()

        def echo(d):
            self.assertEqual(d, now + td)
            self.executed = True

            return d

        self.gw.addService(echo)
        self.gw.timezone_offset = -18000

        d = self.doRequest('echo', now)

        def cb(response):
            message = response['/1']

            self.assertEqual(message.status, remoting.STATUS_OK)
            self.assertEqual(message.body, now)

        return d.addCallback(cb)

    def test_double_encode(self):
        """
        See ticket #648
        """
        self.counter = 0

        def service():
            self.counter += 1

        self.gw.addService(service)

        d = self.doRequest('service')

        def cb(result):
            self.assertEqual(self.counter, 1)

        return d.addCallback(cb)


class DummyHTTPRequest:
    def __init__(self):
        self.headers = {}
        self.finished = False

    def setResponseCode(self, status):
        self.status = status

    def setHeader(self, n, v):
        self.headers[n] = v

    def write(self, s):
        self.content = s

    def finish(self):
        self.finished = True


class TwistedGatewayTestCase(BaseTestCase):
    def test_finalise_request(self):
        request = DummyHTTPRequest()
        gw = twisted.TwistedGateway()

        gw._finaliseRequest(request, 200, 'xyz', 'text/plain')

        self.assertEqual(request.status, 200)
        self.assertEqual(request.content, 'xyz')

        self.assertTrue('Content-Type' in request.headers)
        self.assertEqual(request.headers['Content-Type'], 'text/plain')
        self.assertTrue('Content-Length' in request.headers)
        self.assertEqual(request.headers['Content-Length'], '3')

        self.assertTrue(request.finished)

    def test_get_processor(self):
        a3 = pyamf.ASObject({'target': 'null'})
        a0 = pyamf.ASObject({'target': 'foo.bar'})

        gw = twisted.TwistedGateway()

        self.assertTrue(isinstance(gw.getProcessor(a3), twisted.AMF3RequestProcessor))
        self.assertTrue(isinstance(gw.getProcessor(a0), twisted.AMF0RequestProcessor))


class AMF0RequestProcessorTestCase(BaseTestCase):
    """
    """

    def getProcessor(self, *args, **kwargs):
        """
        Return an L{twisted.AMF0RequestProcessor} attached to a gateway.
        Supply the gateway args/kwargs.
        """
        self.gw = twisted.TwistedGateway(*args, **kwargs)
        self.processor = twisted.AMF0RequestProcessor(self.gw)

        return self.processor

    def test_unknown_service_request(self):
        p = self.getProcessor({'echo': lambda x: x})

        request = remoting.Request('sdf')

        d = p(request)

        self.assertTrue(isinstance(d, defer.Deferred))
        response = d.result
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertTrue(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, remoting.ErrorFault))

        self.assertEqual(response.body.code, 'Service.ResourceNotFound')
        self.assertEqual(response.body.description, u'Unknown service sdf')

    def test_error_auth(self):
        def auth(u, p):
            raise IndexError

        p = self.getProcessor({'echo': lambda x: x}, authenticator=auth)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        d = p(request)

        self.assertTrue(isinstance(d, defer.Deferred))

        response = d.result
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertTrue(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, remoting.ErrorFault))
        self.assertEqual(response.body.code, 'IndexError')

    def test_auth_fail(self):
        def auth(u, p):
            return False

        p = self.getProcessor({'echo': lambda x: x}, authenticator=auth)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        d = p(request)

        self.assertTrue(isinstance(d, defer.Deferred))

        def check_response(response):
            self.assertTrue(isinstance(response, remoting.Response))
            self.assertTrue(response.status, remoting.STATUS_ERROR)
            self.assertTrue(isinstance(response.body, remoting.ErrorFault))
            self.assertEqual(response.body.code, 'AuthenticationError')

        d.addCallback(check_response)

        return d

    def test_deferred_auth(self):
        d = defer.Deferred()

        def auth(u, p):
            return reactor.callLater(0, lambda: True)

        p = self.getProcessor({'echo': lambda x: x}, authenticator=auth)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        def cb(result):
            self.assertTrue(result)
            d.callback(None)

        p(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_error_preprocessor(self):
        def preprocessor(service_request):
            raise IndexError

        p = self.getProcessor({'echo': lambda x: x}, preprocessor=preprocessor)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        d = p(request)

        def check_response(response):
            self.assertTrue(isinstance(response, remoting.Response))
            self.assertTrue(response.status, remoting.STATUS_ERROR)
            self.assertTrue(isinstance(response.body, remoting.ErrorFault))
            self.assertEqual(response.body.code, 'IndexError')

        d.addCallback(check_response)

        return d

    def test_deferred_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(u, p):
            return reactor.callLater(0, lambda: True)

        p = self.getProcessor({'echo': lambda x: x}, preprocessor=preprocessor)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        def cb(result):
            self.assertTrue(result)
            d.callback(None)

        p(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(service_request):
            d.callback(None)

        p = self.getProcessor({'echo': lambda x: x}, preprocessor=preprocessor)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        p(request).addErrback(lambda failure: d.errback())

        return d

    def test_exposed_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(http_request, service_request):
            return reactor.callLater(0, lambda: True)

        preprocessor = gateway.expose_request(preprocessor)
        p = self.getProcessor({'echo': lambda x: x}, preprocessor=preprocessor)

        request = remoting.Request('echo', envelope=remoting.Envelope())

        def cb(result):
            self.assertTrue(result)
            d.callback(None)

        p(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_error_body(self):
        def echo(x):
            raise KeyError

        p = self.getProcessor({'echo': echo})
        request = remoting.Request('echo', envelope=remoting.Envelope())

        d = p(request)

        def check_result(response):
            self.assertTrue(isinstance(response, remoting.Response))
            self.assertTrue(response.status, remoting.STATUS_ERROR)
            self.assertTrue(isinstance(response.body, remoting.ErrorFault))
            self.assertEqual(response.body.code, 'KeyError')

        d.addCallback(check_result)

        return d

    def test_error_deferred_body(self):
        d = defer.Deferred()

        def echo(x):
            d2 = defer.Deferred()

            def cb(result):
                raise IndexError

            reactor.callLater(0, lambda: d2.callback(None))

            d2.addCallback(cb)
            return d2

        p = self.getProcessor({'echo': echo}, expose_request=False)

        request = remoting.Request('echo', envelope=remoting.Envelope())
        request.body = ['a']

        def cb(result):
            self.assertTrue(isinstance(result, remoting.Response))
            self.assertTrue(result.status, remoting.STATUS_ERROR)
            self.assertTrue(isinstance(result.body, remoting.ErrorFault))
            self.assertEqual(result.body.code, 'IndexError')

        return p(request).addCallback(cb).addErrback(lambda x: d.errback())


class AMF3RequestProcessorTestCase(BaseTestCase):
    def test_unknown_service_request(self):
        gw = twisted.TwistedGateway({'echo': lambda x: x}, expose_request=False)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='ss')])

        d = proc(request)

        self.assertTrue(isinstance(d, defer.Deferred))
        response = d.result
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertTrue(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, messaging.ErrorMessage))

    def test_error_preprocessor(self):
        def preprocessor(service_request, *args):
            raise IndexError

        gw = twisted.TwistedGateway({'echo': lambda x: x},
            expose_request=False, preprocessor=preprocessor)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        d = proc(request)

        self.assertTrue(isinstance(d, defer.Deferred))
        response = d.result
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertTrue(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, messaging.ErrorMessage))
        self.assertEqual(response.body.faultCode, 'IndexError')

    def test_deferred_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(u, *args):
            d2 = defer.Deferred()
            reactor.callLater(0, lambda: d2.callback(None))

            return d2

        gw = twisted.TwistedGateway({'echo': lambda x: x}, expose_request=False, preprocessor=preprocessor)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        def cb(result):
            self.assertTrue(result)
            d.callback(None)

        proc(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(service_request, *args):
            d.callback(None)

        gw = twisted.TwistedGateway({'echo': lambda x: x}, expose_request=False, preprocessor=preprocessor)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        proc(request).addErrback(lambda failure: d.errback())

        return d

    def test_exposed_preprocessor(self):
        d = defer.Deferred()

        def preprocessor(http_request, service_request):
            return reactor.callLater(0, lambda: True)

        preprocessor = gateway.expose_request(preprocessor)
        gw = twisted.TwistedGateway({'echo': lambda x: x}, expose_request=False, preprocessor=preprocessor)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        def cb(result):
            try:
                self.assertTrue(result)
            except:
                d.errback()
            else:
                d.callback(None)

        proc(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_error_body(self):
        def echo(x):
            raise KeyError

        gw = twisted.TwistedGateway({'echo': echo}, expose_request=False)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        d = proc(request)

        self.assertTrue(isinstance(d, defer.Deferred))
        response = d.result
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertTrue(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, messaging.ErrorMessage))
        self.assertEqual(response.body.faultCode, 'KeyError')

    def test_error_deferred_body(self):
        d = defer.Deferred()

        def echo(x):
            d2 = defer.Deferred()

            def cb(result):
                raise IndexError

            reactor.callLater(0, lambda: d2.callback(None))

            d2.addCallback(cb)
            return d2

        gw = twisted.TwistedGateway({'echo': echo}, expose_request=False)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=['spam.eggs'], operation='echo')])

        def cb(result):
            try:
                self.assertTrue(isinstance(result, remoting.Response))
                self.assertTrue(result.status, remoting.STATUS_ERROR)
                self.assertTrue(isinstance(result.body, messaging.ErrorMessage))
                self.assertEqual(result.body.faultCode, 'IndexError')
            except:
                d.errback()
            else:
                d.callback(None)

        proc(request).addCallback(cb).addErrback(lambda x: d.errback())

        return d

    def test_destination(self):
        d = defer.Deferred()

        gw = twisted.TwistedGateway({'spam.eggs': lambda x: x}, expose_request=False)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.RemotingMessage(body=[None], destination='spam', operation='eggs')])

        def cb(result):
            try:
                self.assertTrue(result)
            except:
                d.errback()
            else:
                d.callback(None)

        proc(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

    def test_async(self):
        d = defer.Deferred()

        gw = twisted.TwistedGateway({'spam.eggs': lambda x: x}, expose_request=False)
        proc = twisted.AMF3RequestProcessor(gw)

        request = remoting.Request('null', body=[messaging.AsyncMessage(body=[None], destination='spam', operation='eggs')])

        def cb(result):
            msg = result.body

            try:
                self.assertTrue(isinstance(msg, messaging.AcknowledgeMessage))
            except:
                d.errback()
            else:
                d.callback(None)

        proc(request).addCallback(cb).addErrback(lambda failure: d.errback())

        return d

########NEW FILE########
__FILENAME__ = test_wsgi
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
WSGI gateway tests.

@since: 0.1.0
"""

import unittest

import pyamf
from pyamf import remoting, util
from pyamf.remoting.gateway.wsgi import WSGIGateway


class WSGIServerTestCase(unittest.TestCase):
    def setUp(self):
        self.gw = WSGIGateway()
        self.executed = False

    def doRequest(self, request, start_response, **kwargs):
        kwargs.setdefault('REQUEST_METHOD', 'POST')
        kwargs.setdefault('CONTENT_LENGTH', str(len(request)))

        kwargs['wsgi.input'] = request

        def sr(status, headers):
            r = None

            if start_response:
                r = start_response(status, headers)

            self.executed = True

            return r

        return self.gw(kwargs, sr)

    def makeRequest(self, service, body, raw=False):
        if not raw:
            body = [body]

        e = remoting.Envelope(pyamf.AMF3)
        e['/1'] = remoting.Request(service, body=body)

        return remoting.encode(e)

    def test_request_method(self):
        def bad_response(status, headers):
            self.assertEqual(status, '400 Bad Request')
            self.executed = True

        self.gw({'REQUEST_METHOD': 'GET'}, bad_response)
        self.assertTrue(self.executed)

        self.assertRaises(KeyError, self.gw, {'REQUEST_METHOD': 'POST'},
            lambda *args: None)

    def test_bad_request(self):
        request = util.BufferedByteStream()
        request.write('Bad request')
        request.seek(0, 0)

        def start_response(status, headers):
            self.assertEqual(status, '400 Bad Request')

        self.doRequest(request, start_response)
        self.assertTrue(self.executed)

    def test_unknown_request(self):
        request = self.makeRequest('test.test', [], raw=True)

        def start_response(status, headers):
            self.executed = True
            self.assertEqual(status, '200 OK')
            self.assertTrue(('Content-Type', 'application/x-amf') in headers)

        response = self.doRequest(request, start_response)

        envelope = remoting.decode(''.join(response))

        message = envelope['/1']

        self.assertEqual(message.status, remoting.STATUS_ERROR)
        body = message.body

        self.assertTrue(isinstance(body, remoting.ErrorFault))
        self.assertEqual(body.code, 'Service.ResourceNotFound')
        self.assertTrue(self.executed)

    def test_eof_decode(self):
        request = util.BufferedByteStream()

        def start_response(status, headers):
            self.assertEqual(status, '400 Bad Request')
            self.assertTrue(('Content-Type', 'text/plain') in headers)

        response = self.doRequest(request, start_response)

        self.assertEqual(response, ['400 Bad Request\n\nThe request body was unable to be successfully decoded.'])
        self.assertTrue(self.executed)

    def _raiseException(self, e, *args, **kwargs):
        raise e()

    def _restoreDecode(self):
        remoting.decode = self.old_method

    def test_really_bad_decode(self):
        self.old_method = remoting.decode
        remoting.decode = lambda *args, **kwargs: self._raiseException(Exception, *args, **kwargs)
        self.addCleanup(self._restoreDecode)

        request = util.BufferedByteStream()

        def start_response(status, headers):
            self.assertEqual(status, '500 Internal Server Error')
            self.assertTrue(('Content-Type', 'text/plain') in headers)

        response = self.doRequest(request, start_response)

        self.assertEqual(response, ['500 Internal Server Error\n\nAn unexpec'
            'ted error occurred whilst decoding.'])
        self.assertTrue(self.executed)

    def test_expected_exceptions_decode(self):
        self.old_method = remoting.decode
        self.addCleanup(self._restoreDecode)
        request = util.BufferedByteStream()

        for x in (KeyboardInterrupt, SystemExit):
            remoting.decode = lambda *args, **kwargs: self._raiseException(x, *args, **kwargs)

            self.assertRaises(x, self.doRequest, request, None)

    def test_expose_request(self):
        self.gw.expose_request = True

        def echo(http_request, data):
            self.assertTrue('pyamf.request' in http_request)
            request = http_request['pyamf.request']

            self.assertTrue(isinstance(request, remoting.Request))

            self.assertEqual(request.target, 'echo')
            self.assertEqual(request.body, ['hello'])

        self.gw.addService(echo)
        self.doRequest(self.makeRequest('echo', 'hello'), None)

        self.assertTrue(self.executed)

    def test_timezone(self):
        import datetime

        td = datetime.timedelta(hours=-5)
        now = datetime.datetime.utcnow()

        def echo(d):
            self.assertEqual(d, now + td)

            return d

        self.gw.addService(echo)
        self.gw.timezone_offset = -18000

        response = self.doRequest(self.makeRequest('echo', now), None)
        envelope = remoting.decode(''.join(response))
        message = envelope['/1']

        self.assertEqual(message.body, now)

########NEW FILE########
__FILENAME__ = spam

########NEW FILE########
__FILENAME__ = test_decimal
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the C{decimal} module integration.
"""

import unittest
import decimal

import pyamf


class DecimalTestCase(unittest.TestCase):
    def test_amf0_encode(self):
        x = decimal.Decimal('1.23456463452345')

        self.assertEqual(pyamf.encode(x, encoding=pyamf.AMF0, strict=False).getvalue(),
            '\x00?\xf3\xc0\xc6\xd8\xa18\xfa')

        self.assertRaises(pyamf.EncodeError, pyamf.encode, x, encoding=pyamf.AMF0, strict=True)

    def test_amf3_encode(self):
        x = decimal.Decimal('1.23456463452345')

        self.assertEqual(pyamf.encode(x, encoding=pyamf.AMF3, strict=False).getvalue(),
            '\x05?\xf3\xc0\xc6\xd8\xa18\xfa')

        self.assertRaises(pyamf.EncodeError, pyamf.encode, x, encoding=pyamf.AMF3, strict=True)

########NEW FILE########
__FILENAME__ = test_sets
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the C{sets} module integration.
"""

import unittest
import sets

import pyamf
from pyamf.tests.util import check_buffer


class ImmutableSetTestCase(unittest.TestCase):
    def test_amf0_encode(self):
        x = sets.ImmutableSet(['1', '2', '3'])

        self.assertTrue(check_buffer(
            pyamf.encode(x, encoding=pyamf.AMF0).getvalue(), (
            '\n\x00\x00\x00\x03', (
                '\x02\x00\x011',
                '\x02\x00\x013',
                '\x02\x00\x012'
            ))
        ))

    def test_amf3_encode(self):
        x = sets.ImmutableSet(['1', '2', '3'])

        self.assertTrue(check_buffer(
            pyamf.encode(x, encoding=pyamf.AMF3).getvalue(), (
            '\t\x07\x01', (
                '\x06\x031',
                '\x06\x033',
                '\x06\x032'
            ))
        ))

########NEW FILE########
__FILENAME__ = test_amf0
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF Remoting AMF0 style.

@since: 0.6
"""

import unittest

from pyamf import remoting
from pyamf.remoting import amf0


class MockGateway(object):
    """
    """

    debug = True


class BaseTestCase(unittest.TestCase):
    """
    Provides a L{processor} attribute.
    """

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.gateway = MockGateway()
        self.processor = amf0.RequestProcessor(self.gateway)


class ExceptionTestCase(BaseTestCase):
    """
    Tests exception handling
    """

    def generate_exception(self):
        try:
            raise NameError('foobar')
        except NameError:
            import sys

            return sys.exc_info()

    def test_debug(self):
        self.assertTrue(self.gateway.debug)

        response = self.processor.buildErrorResponse(None, error=self.generate_exception())

        self.assertEqual(response.status, remoting.STATUS_ERROR)

        error = response.body

        self.assertEqual(error.level, 'error')
        self.assertEqual(error.code, 'NameError')
        self.assertEqual(error.description, 'foobar')
        self.assertTrue(isinstance(error.details, list))

    def test_no_debug(self):
        self.gateway.debug = False

        response = self.processor.buildErrorResponse(None, error=self.generate_exception())

        self.assertEqual(response.status, remoting.STATUS_ERROR)

        error = response.body

        self.assertEqual(error.level, 'error')
        self.assertEqual(error.code, 'NameError')
        self.assertEqual(error.description, 'foobar')
        self.assertEqual(error.details, None)

########NEW FILE########
__FILENAME__ = test_client
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for Remoting client.

@since: 0.1.0
"""

import unittest
import urllib2

import pyamf
from pyamf import remoting, util
from pyamf.remoting import client


class ServiceMethodProxyTestCase(unittest.TestCase):
    def test_create(self):
        x = client.ServiceMethodProxy('a', 'b')

        self.assertEqual(x.service, 'a')
        self.assertEqual(x.name, 'b')

    def test_call(self):
        tc = self

        class TestService(object):
            def __init__(self, s, args):
                self.service = s
                self.args = args

            def _call(self, service, *args):
                tc.assertTrue(self.service, service)
                tc.assertTrue(self.args, args)

        x = client.ServiceMethodProxy(None, None)
        ts = TestService(x, [1, 2, 3])
        x.service = ts

        x(1, 2, 3)

    def test_str(self):
        x = client.ServiceMethodProxy('spam', 'eggs')
        self.assertEqual(str(x), 'spam.eggs')

        x = client.ServiceMethodProxy('spam', None)
        self.assertEqual(str(x), 'spam')


class ServiceProxyTestCase(unittest.TestCase):
    def test_create(self):
        x = client.ServiceProxy('spam', 'eggs')

        self.assertEqual(x._gw, 'spam')
        self.assertEqual(x._name, 'eggs')
        self.assertEqual(x._auto_execute, True)

        x = client.ServiceProxy('hello', 'world', True)

        self.assertEqual(x._gw, 'hello')
        self.assertEqual(x._name, 'world')
        self.assertEqual(x._auto_execute, True)

        x = client.ServiceProxy(ord, chr, False)

        self.assertEqual(x._gw, ord)
        self.assertEqual(x._name, chr)
        self.assertEqual(x._auto_execute, False)

    def test_getattr(self):
        x = client.ServiceProxy(None, None)
        y = x.spam

        self.assertTrue(isinstance(y, client.ServiceMethodProxy))
        self.assertEqual(y.name, 'spam')

    def test_call(self):
        class DummyGateway(object):
            def __init__(self, tc):
                self.tc = tc

            def addRequest(self, method_proxy, *args):
                self.tc.assertEqual(method_proxy, self.method_proxy)
                self.tc.assertEqual(args, self.args)

                self.request = {'method_proxy': method_proxy, 'args': args}
                return self.request

            def execute_single(self, request):
                self.tc.assertEqual(request, self.request)

                return pyamf.ASObject(body=None, status=None)

        gw = DummyGateway(self)
        x = client.ServiceProxy(gw, 'test')
        y = x.spam

        gw.method_proxy = y
        gw.args = ()

        y()
        gw.args = (1, 2, 3)

        y(1, 2, 3)

    def test_service_call(self):
        class DummyGateway(object):
            def __init__(self, tc):
                self.tc = tc

            def addRequest(self, method_proxy, *args):
                self.tc.assertEqual(method_proxy.service, self.x)
                self.tc.assertEqual(method_proxy.name, None)

                return pyamf.ASObject(method_proxy=method_proxy, args=args)

            def execute_single(self, request):
                return pyamf.ASObject(body=None, status=None)

        gw = DummyGateway(self)
        x = client.ServiceProxy(gw, 'test')
        gw.x = x

        x()

    def test_pending_call(self):
        class DummyGateway(object):
            def __init__(self, tc):
                self.tc = tc

            def addRequest(self, method_proxy, *args):
                self.tc.assertEqual(method_proxy, self.method_proxy)
                self.tc.assertEqual(args, self.args)

                self.request = pyamf.ASObject(method_proxy=method_proxy, args=args)

                return self.request

        gw = DummyGateway(self)
        x = client.ServiceProxy(gw, 'test', False)
        y = x.eggs

        gw.method_proxy = y
        gw.args = ()

        res = y()

        self.assertEqual(id(gw.request), id(res))

    def test_str(self):
        x = client.ServiceProxy(None, 'test')

        self.assertEqual(str(x), 'test')

    def test_error(self):
        class DummyGateway(object):
            def __init__(self, tc):
                self.tc = tc

            def addRequest(self, method_proxy, *args):
                self.request = pyamf.ASObject(method_proxy=method_proxy, args=args)

                return self.request

            def execute_single(self, request):
                body = remoting.ErrorFault(code='TypeError', description='foobar')

                return remoting.Response(status=remoting.STATUS_ERROR, body=body)

        gw = DummyGateway(self)

        proxy = client.ServiceProxy(gw, 'test')

        self.assertRaises(TypeError, proxy)


class RequestWrapperTestCase(unittest.TestCase):
    def test_create(self):
        x = client.RequestWrapper(1, 2, 3, 4)

        self.assertEqual(x.gw, 1)
        self.assertEqual(x.id, 2)
        self.assertEqual(x.service, 3)
        self.assertEqual(x.args, (4,))

    def test_str(self):
        x = client.RequestWrapper(None, '/1', None, None)

        self.assertEqual(str(x), '/1')

    def test_null_response(self):
        x = client.RequestWrapper(None, None, None, None)

        self.assertRaises(AttributeError, getattr, x, 'result')

    def test_set_response(self):
        x = client.RequestWrapper(None, None, None, None)

        y = pyamf.ASObject(body='spam.eggs')

        x.setResponse(y)

        self.assertEqual(x.response, y)
        self.assertEqual(x.result, 'spam.eggs')


class MockOpener(object):
    """
    opener for urllib2.install_opener
    """

    def __init__(self, test, response=None):
        self.test = test
        self.response = response

    def open(self, request, data=None, timeout=None):
        if self.response.code != 200:
            raise urllib2.URLError(self.response.code)

        self.request = request
        self.data = data

        return self.response


class MockHeaderCollection(object):

    def __init__(self, headers):
        self.headers = headers

    def getheader(self, name):
        return self.headers.get(name, None)

    def __repr__(self):
        return repr(self.headers)


class MockResponse(object):
    """
    """

    headers = None
    body = None

    def info(self):
        return MockHeaderCollection(self.headers)

    def read(self, amount):
        return self.body[0:amount]


class BaseServiceTestCase(unittest.TestCase):
    """
    """

    canned_response = ('\x00\x00\x00\x00\x00\x01\x00\x0b/1/onResult\x00'
        '\x04null\x00\x00\x00\x00\n\x00\x00\x00\x03\x00?\xf0\x00\x00'
        '\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00@\x08\x00'
        '\x00\x00\x00\x00\x00')

    headers = {
        'Content-Type': 'application/x-amf',
    }

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.response = MockResponse()
        self.opener = MockOpener(self, self.response)

        self.gw = client.RemotingService('http://example.org/amf-gateway', opener=self.opener.open)

        self.headers = self.__class__.headers.copy()
        self.headers['Content-Length'] = len(self.canned_response)

        self.setResponse(200, self.canned_response, self.headers)

    def setResponse(self, status, body, headers=None):
        self.response.code = status
        self.response.body = body
        self.response.headers = headers or {
            'Content-Type': remoting.CONTENT_TYPE
        }


class RemotingServiceTestCase(BaseServiceTestCase):
    """
    """

    def test_create(self):
        self.assertRaises(TypeError, client.RemotingService)
        x = client.RemotingService('http://example.org')

        self.assertEqual(x.url, ('http', 'example.org', '', '', '', ''))

        # amf version
        x = client.RemotingService('http://example.org', pyamf.AMF3)
        self.assertEqual(x.amf_version, pyamf.AMF3)

    def test_schemes(self):
        x = client.RemotingService('http://example.org')
        self.assertEqual(x.url, ('http', 'example.org', '', '', '', ''))

        x = client.RemotingService('https://example.org')
        self.assertEqual(x.url, ('https', 'example.org', '', '', '', ''))

        self.assertRaises(ValueError, client.RemotingService,
            'ftp://example.org')

    def test_port(self):
        x = client.RemotingService('http://example.org:8080')

        self.assertEqual(x.url, ('http', 'example.org:8080', '', '', '', ''))

    def test_get_service(self):
        x = client.RemotingService('http://example.org')

        y = x.getService('spam')

        self.assertTrue(isinstance(y, client.ServiceProxy))
        self.assertEqual(y._name, 'spam')
        self.assertEqual(y._gw, x)

        self.assertRaises(TypeError, x.getService, 1)

    def test_add_request(self):
        gw = client.RemotingService('http://spameggs.net')

        self.assertEqual(gw.request_number, 1)
        self.assertEqual(gw.requests, [])
        service = gw.getService('baz')
        wrapper = gw.addRequest(service, 1, 2, 3)

        self.assertEqual(gw.requests, [wrapper])
        self.assertEqual(wrapper.gw, gw)
        self.assertEqual(gw.request_number, 2)
        self.assertEqual(wrapper.id, '/1')
        self.assertEqual(wrapper.service, service)
        self.assertEqual(wrapper.args, (1, 2, 3))

        # add 1 arg
        wrapper2 = gw.addRequest(service, None)

        self.assertEqual(gw.requests, [wrapper, wrapper2])
        self.assertEqual(wrapper2.gw, gw)
        self.assertEqual(gw.request_number, 3)
        self.assertEqual(wrapper2.id, '/2')
        self.assertEqual(wrapper2.service, service)
        self.assertEqual(wrapper2.args, (None,))

        # add no args
        wrapper3 = gw.addRequest(service)

        self.assertEqual(gw.requests, [wrapper, wrapper2, wrapper3])
        self.assertEqual(wrapper3.gw, gw)
        self.assertEqual(gw.request_number, 4)
        self.assertEqual(wrapper3.id, '/3')
        self.assertEqual(wrapper3.service, service)
        self.assertEqual(wrapper3.args, tuple())

    def test_remove_request(self):
        gw = client.RemotingService('http://spameggs.net')
        self.assertEqual(gw.requests, [])

        service = gw.getService('baz')
        wrapper = gw.addRequest(service, 1, 2, 3)
        self.assertEqual(gw.requests, [wrapper])

        gw.removeRequest(wrapper)
        self.assertEqual(gw.requests, [])

        wrapper = gw.addRequest(service, 1, 2, 3)
        self.assertEqual(gw.requests, [wrapper])

        gw.removeRequest(service, 1, 2, 3)
        self.assertEqual(gw.requests, [])

        self.assertRaises(LookupError, gw.removeRequest, service, 1, 2, 3)

    def test_get_request(self):
        gw = client.RemotingService('http://spameggs.net')

        service = gw.getService('baz')
        wrapper = gw.addRequest(service, 1, 2, 3)

        wrapper2 = gw.getRequest(str(wrapper))
        self.assertEqual(wrapper, wrapper2)

        wrapper2 = gw.getRequest('/1')
        self.assertEqual(wrapper, wrapper2)

        wrapper2 = gw.getRequest(wrapper.id)
        self.assertEqual(wrapper, wrapper2)

    def test_get_amf_request(self):
        gw = client.RemotingService('http://example.org', pyamf.AMF3)

        service = gw.getService('baz')
        method_proxy = service.gak
        wrapper = gw.addRequest(method_proxy, 1, 2, 3)

        envelope = gw.getAMFRequest([wrapper])

        self.assertEqual(envelope.amfVersion, pyamf.AMF3)
        self.assertEqual(envelope.keys(), ['/1'])

        request = envelope['/1']
        self.assertEqual(request.target, 'baz.gak')
        self.assertEqual(request.body, [1, 2, 3])

        envelope2 = gw.getAMFRequest(gw.requests)

        self.assertEqual(envelope2.amfVersion, pyamf.AMF3)
        self.assertEqual(envelope2.keys(), ['/1'])

        request = envelope2['/1']
        self.assertEqual(request.target, 'baz.gak')
        self.assertEqual(request.body, [1, 2, 3])

    def test_execute_single(self):
        service = self.gw.getService('baz', auto_execute=False)
        wrapper = service.gak()

        response = self.gw.execute_single(wrapper)
        self.assertEqual(self.gw.requests, [])

        r = self.opener.request

        self.assertEqual(r.headers, {
            'Content-type': remoting.CONTENT_TYPE,
            'User-agent': client.DEFAULT_USER_AGENT
        })
        self.assertEqual(r.get_method(), 'POST')
        self.assertEqual(r.get_full_url(), 'http://example.org/amf-gateway')

        self.assertEqual(r.get_data(), '\x00\x00\x00\x00\x00\x01\x00\x07'
            'baz.gak\x00\x02/1\x00\x00\x00\x00\x0a\x00\x00\x00\x00')

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, [1, 2, 3])

    def test_execute(self):
        baz = self.gw.getService('baz', auto_execute=False)
        spam = self.gw.getService('spam', auto_execute=False)
        wrapper = baz.gak()
        wrapper2 = spam.eggs()

        self.assertTrue(wrapper)
        self.assertTrue(wrapper2)

        response = self.gw.execute()
        self.assertTrue(response)
        self.assertEqual(self.gw.requests, [])

        r = self.opener.request

        self.assertEqual(r.headers, {
            'Content-type': remoting.CONTENT_TYPE,
            'User-agent': client.DEFAULT_USER_AGENT
        })
        self.assertEqual(r.get_method(), 'POST')
        self.assertEqual(r.get_full_url(), 'http://example.org/amf-gateway')

        self.assertEqual(r.get_data(), '\x00\x00\x00\x00\x00\x02\x00\x07'
            'baz.gak\x00\x02/1\x00\x00\x00\x00\n\x00\x00\x00\x00\x00\tspam.'
            'eggs\x00\x02/2\x00\x00\x00\x00\n\x00\x00\x00\x00')

    def test_get_response(self):
        self.setResponse(200, '\x00\x00\x00\x00\x00\x00\x00\x00')

        self.gw._getResponse(None)

        self.setResponse(404, '', {})

        self.assertRaises(remoting.RemotingError, self.gw._getResponse, None)

        # bad content type
        self.setResponse(200, '<html></html>', {'Content-Type': 'text/html'})

        self.assertRaises(remoting.RemotingError, self.gw._getResponse, None)

    def test_credentials(self):
        self.assertFalse('Credentials' in self.gw.headers)
        self.gw.setCredentials('spam', 'eggs')
        self.assertTrue('Credentials' in self.gw.headers)
        self.assertEqual(self.gw.headers['Credentials'],
            {'userid': u'spam', 'password': u'eggs'})

        envelope = self.gw.getAMFRequest([])
        self.assertTrue('Credentials' in envelope.headers)

        cred = envelope.headers['Credentials']

        self.assertEqual(cred, self.gw.headers['Credentials'])

    def test_append_url_header(self):
        self.setResponse(200, '\x00\x00\x00\x01\x00\x12AppendToGatewayUrl'
            '\x01\x00\x00\x00\x00\x02\x00\x05hello\x00\x00\x00\x00', {
            'Content-Type': 'application/x-amf'})

        response = self.gw._getResponse(None)
        self.assertTrue(response)

        self.assertEqual(self.gw.original_url,
            'http://example.org/amf-gatewayhello')

    def test_replace_url_header(self):
        self.setResponse(200, '\x00\x00\x00\x01\x00\x11ReplaceGatewayUrl\x01'
            '\x00\x00\x00\x00\x02\x00\x10http://spam.eggs\x00\x00\x00\x00',
            {'Content-Type': 'application/x-amf'})

        response = self.gw._getResponse(None)
        self.assertTrue(response)
        self.assertEqual(self.gw.original_url, 'http://spam.eggs')

    def test_add_http_header(self):
        self.assertEqual(self.gw.http_headers, {})

        self.gw.addHTTPHeader('ETag', '29083457239804752309485')

        self.assertEqual(self.gw.http_headers, {
            'ETag': '29083457239804752309485'
        })

    def test_remove_http_header(self):
        self.gw.http_headers = {
            'Set-Cookie': 'foo-bar'
        }

        self.gw.removeHTTPHeader('Set-Cookie')

        self.assertEqual(self.gw.http_headers, {})
        self.assertRaises(KeyError, self.gw.removeHTTPHeader, 'foo-bar')

    def test_http_request_headers(self):
        self.gw.addHTTPHeader('ETag', '29083457239804752309485')

        expected_headers = {
            'Etag': '29083457239804752309485',
            'Content-type': 'application/x-amf',
            'User-agent': self.gw.user_agent
        }

        self.setResponse(200, '\x00\x00\x00\x01\x00\x11ReplaceGatewayUrl'
            '\x01\x00\x00\x00\x00\x02\x00\x10http://spam.eggs\x00\x00\x00\x00')

        self.gw.execute()

        request = self.opener.request

        self.assertEqual(expected_headers, request.headers)

    def test_empty_content_length(self):
        self.setResponse(200, '\x00\x00\x00\x01\x00\x11ReplaceGatewayUrl\x01'
            '\x00\x00\x00\x00\x02\x00\x10http://spam.eggs\x00\x00\x00\x00', {
            'Content-Type': 'application/x-amf',
            'Content-Length': ''
        })

        response = self.gw._getResponse(None)
        self.assertTrue(response)

    def test_bad_content_length(self):
        # test a really borked content-length header
        self.setResponse(200, self.canned_response, {
            'Content-Type': 'application/x-amf',
            'Content-Length': 'asdfasdf'
        })

        self.assertRaises(ValueError, self.gw._getResponse, None)

    def test_content_type_with_charset(self):
        """
        The HTTP protocol dictates that the header 'Content-Type' can have a
        '; charset=*' at the end.
        """
        old_headers = self.headers.copy()

        self.headers['Content-Type'] = remoting.CONTENT_TYPE + '; charset=utf-8'

        try:
            self.gw._getResponse(None)
        finally:
            self.headers = old_headers



class GZipTestCase(BaseServiceTestCase):
    """
    Tests for gzipping responses
    """

    def setUp(self):
        import gzip

        env = remoting.Envelope(pyamf.AMF3)
        r = remoting.Response(['foo' * 50000] * 200)

        env['/1'] = r

        response = remoting.encode(env).getvalue()

        buf = util.BufferedByteStream()
        x = gzip.GzipFile(fileobj=buf, mode='wb')

        x.write(response)

        x.close()

        self.canned_response = buf.getvalue()

        BaseServiceTestCase.setUp(self)

        self.headers['Content-Encoding'] = 'gzip'

    def test_good_response(self):
        self.gw._getResponse(None)

    def test_bad_response(self):
        self.headers['Content-Length'] = len('foobar')
        self.setResponse(200, 'foobar', self.headers)

        self.assertRaises(IOError, self.gw._getResponse, None)

########NEW FILE########
__FILENAME__ = test_remoteobject
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
RemoteObject Tests.

@since: 0.1
"""

import unittest

import pyamf
from pyamf import remoting
from pyamf.remoting import amf3, gateway
from pyamf.flex import messaging


class RandomIdGeneratorTestCase(unittest.TestCase):
    def test_generate(self):
        x = []

        for i in range(5):
            id_ = amf3.generate_random_id()

            self.assertTrue(id_ not in x)
            x.append(id_)


class AcknowlegdementGeneratorTestCase(unittest.TestCase):
    def test_generate(self):
        ack = amf3.generate_acknowledgement()

        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertTrue(ack.messageId is not None)
        self.assertTrue(ack.clientId is not None)
        self.assertTrue(ack.timestamp is not None)

    def test_request(self):
        ack = amf3.generate_acknowledgement(pyamf.ASObject(messageId='123123'))

        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertTrue(ack.messageId is not None)
        self.assertTrue(ack.clientId is not None)
        self.assertTrue(ack.timestamp is not None)

        self.assertEqual(ack.correlationId, '123123')


class RequestProcessorTestCase(unittest.TestCase):
    def test_create(self):
        rp = amf3.RequestProcessor('xyz')
        self.assertEqual(rp.gateway, 'xyz')

    def test_ping(self):
        message = messaging.CommandMessage(operation=5)
        rp = amf3.RequestProcessor(None)
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertEqual(ack.body, True)

    def test_request(self):
        def echo(x):
            return x

        gw = gateway.BaseGateway({'echo': echo})
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertEqual(ack.body, 'spam.eggs')

    def test_error(self):
        def echo(x):
            raise TypeError('foo')

        gw = gateway.BaseGateway({'echo': echo})
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertFalse(gw.debug)
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(ack, messaging.ErrorMessage))
        self.assertEqual(ack.faultCode, 'TypeError')
        self.assertEqual(ack.faultString, 'foo')

    def test_error_debug(self):
        def echo(x):
            raise TypeError('foo')

        gw = gateway.BaseGateway({'echo': echo}, debug=True)
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(gw.debug)
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(ack, messaging.ErrorMessage))
        self.assertEqual(ack.faultCode, 'TypeError')
        self.assertNotEquals(ack.extendedData, None)

    def test_too_many_args(self):
        def spam(bar):
            return bar

        gw = gateway.BaseGateway({'spam': spam})
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['eggs', 'baz'], operation='spam')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(ack, messaging.ErrorMessage))
        self.assertEqual(ack.faultCode, 'TypeError')

    def test_preprocess(self):
        def echo(x):
            return x

        self.called = False

        def preproc(sr, *args):
            self.called = True

            self.assertEqual(args, ('spam.eggs',))
            self.assertTrue(isinstance(sr, gateway.ServiceRequest))

        gw = gateway.BaseGateway({'echo': echo}, preprocessor=preproc)
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertEqual(ack.body, 'spam.eggs')
        self.assertTrue(self.called)

    def test_fail_preprocess(self):
        def preproc(sr, *args):
            raise IndexError

        def echo(x):
            return x

        gw = gateway.BaseGateway({'echo': echo}, preprocessor=preproc)
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(ack, messaging.ErrorMessage))

    def test_destination(self):
        def echo(x):
            return x

        gw = gateway.BaseGateway({'spam.eggs': echo})
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=[None], destination='spam', operation='eggs')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))
        self.assertEqual(ack.body, None)

    def test_disconnect(self):
        message = messaging.CommandMessage(operation=12)
        rp = amf3.RequestProcessor(None)
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))

    def test_async(self):
        message = messaging.AsyncMessage()
        rp = amf3.RequestProcessor(None)
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertTrue(isinstance(ack, messaging.AcknowledgeMessage))

    def test_error_unicode_message(self):
        """
        See #727
        """
        def echo(x):
            raise TypeError(u'ƒøø')

        gw = gateway.BaseGateway({'echo': echo})
        rp = amf3.RequestProcessor(gw)
        message = messaging.RemotingMessage(body=['spam.eggs'], operation='echo')
        request = remoting.Request('null', body=[message])

        response = rp(request)
        ack = response.body

        self.assertFalse(gw.debug)
        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(ack, messaging.ErrorMessage))
        self.assertEqual(ack.faultCode, 'TypeError')
        self.assertEqual(ack.faultString, u'ƒøø')

########NEW FILE########
__FILENAME__ = test_adapters
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the adapters module.

@since: 0.3.1
"""

import os
import sys

from pyamf import adapters
from pyamf.tests import util
from pyamf.tests.test_imports import ImportsTestCase


class AdapterHelperTestCase(ImportsTestCase):
    def setUp(self):
        ImportsTestCase.setUp(self)

        self.old_env = os.environ.copy()
        self.mods = sys.modules.copy()

        self.path = os.path.join(os.path.dirname(__file__), 'imports')
        sys.path.append(self.path)

    def tearDown(self):
        ImportsTestCase.tearDown(self)

        util.replace_dict(os.environ, self.old_env)
        util.replace_dict(sys.modules, self.mods)
        sys.path.remove(self.path)

    def test_basic(self):
        class Foo(object):
            def __call__(self, *args, **kwargs):
                pass

        def bar(*args, **kargs):
            pass

        self.assertRaises(TypeError, adapters.register_adapter, 'foo', 1)
        self.assertRaises(TypeError, adapters.register_adapter, 'foo', 'asdf')
        adapters.register_adapter('foo', Foo())
        adapters.register_adapter('foo', bar)
        adapters.register_adapter('foo', lambda x: x)

    def test_import(self):
        self.imported = False

        def x(mod):
            self.imported = True
            self.spam = mod

        adapters.register_adapter('spam', x)

        import spam

        self.assertTrue(self.imported)
        self.assertEqual(self.spam, spam)

    def test_get_adapter(self):
        from pyamf.adapters import _decimal

        self.assertTrue(adapters.get_adapter('decimal') is _decimal)

########NEW FILE########
__FILENAME__ = test_adapters_util
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for the adapters.util module.

@since: 0.4
"""

import unittest

from pyamf.adapters import util

# check for set function in python 2.3
import __builtin__

if not hasattr(__builtin__, 'set'):
    from sets import Set as set


class Iterable(object):
    """
    A generic iterable class that supports .. iterating.
    """

    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        return iter(self.iterable)

    def keys(self):
        return self.iterable.keys()

    def values(self):
        return self.iterable.values()

    def __getitem__(self, name):
        return self.iterable.__getitem__(name)


class HelperTestCase(unittest.TestCase):
    def setUp(self):
        self.encoder = object()

    def test_to_list(self):
        self.assertEqual(util.to_list(Iterable([1, 2, 3]), self.encoder), [1, 2, 3])
        self.assertEqual(util.to_list(['a', 'b'], self.encoder), ['a', 'b'])
        self.assertEqual(util.to_list('a', self.encoder), ['a'])

        obj = object()
        self.assertRaises(TypeError, util.to_list, obj, self.encoder)

    def test_to_set(self):
        self.assertEqual(util.to_set(Iterable([1, 2, 3]), self.encoder), set([1, 2, 3]))
        self.assertEqual(util.to_set(['a', 'b'], self.encoder), set(['a', 'b']))
        self.assertEqual(util.to_set('a', self.encoder), set('a'))

        obj = object()
        self.assertRaises(TypeError, util.to_set, obj, self.encoder)

    def test_to_dict(self):
        self.assertEqual(util.to_dict(Iterable({'a': 'b'}), self.encoder), {'a': 'b'})

        obj = object()
        self.assertRaises(TypeError, util.to_dict, obj, self.encoder)

    def test_to_tuple(self):
        self.assertEqual(util.to_tuple(Iterable((1, 2, 3)), self.encoder), (1, 2, 3))

        obj = object()
        self.assertRaises(TypeError, util.to_tuple, obj, self.encoder)

########NEW FILE########
__FILENAME__ = test_alias
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for L{ClassAlias} and L{register_class}. Both are the most
fundamental parts of PyAMF and the test suite for it is big so it makes sense
to have them in one file.

@since: 0.5
"""

import unittest

import pyamf
from pyamf import ClassAlias
from pyamf.tests.util import ClassCacheClearingTestCase, Spam, get_fqcn

try:
    set
except NameError:
    from sets import Set as set


class ClassAliasTestCase(ClassCacheClearingTestCase):
    """
    Test all functionality relating to the class L{ClassAlias}.
    """

    def test_init(self):
        x = ClassAlias(Spam)

        self.assertTrue(x.anonymous)
        self.assertTrue(x.dynamic)
        self.assertFalse(x.amf3)
        self.assertFalse(x.external)

        self.assertEqual(x.readonly_attrs, None)
        self.assertEqual(x.static_attrs, [])
        self.assertEqual(x.exclude_attrs, None)
        self.assertEqual(x.proxy_attrs, None)

        self.assertEqual(x.alias, '')
        self.assertEqual(x.klass, Spam)

        # compiled attributes
        self.assertEqual(x.decodable_properties, None)
        self.assertEqual(x.encodable_properties, None)
        self.assertTrue(x._compiled)

    def test_init_deferred(self):
        """
        Test for initial deferred compliation
        """
        x = ClassAlias(Spam, defer=True)

        self.assertTrue(x.anonymous)
        self.assertEqual(x.dynamic, None)
        self.assertFalse(x.amf3)
        self.assertFalse(x.external)

        self.assertEqual(x.readonly_attrs, None)
        self.assertEqual(x.static_attrs, None)
        self.assertEqual(x.exclude_attrs, None)
        self.assertEqual(x.proxy_attrs, None)

        self.assertEqual(x.alias, '')
        self.assertEqual(x.klass, Spam)

        # compiled attributes
        self.assertFalse(hasattr(x, 'static_properties'))
        self.assertFalse(x._compiled)

    def test_init_kwargs(self):
        x = ClassAlias(Spam, alias='foo', static_attrs=('bar',),
            exclude_attrs=('baz',), readonly_attrs='gak', amf3='spam',
            external='eggs', dynamic='goo', proxy_attrs=('blarg',))

        self.assertFalse(x.anonymous)
        self.assertEqual(x.dynamic, 'goo')
        self.assertEqual(x.amf3, 'spam')
        self.assertEqual(x.external, 'eggs')

        self.assertEqual(x.readonly_attrs, ['a', 'g', 'k'])
        self.assertEqual(x.static_attrs, ['bar'])
        self.assertEqual(x.exclude_attrs, ['baz'])
        self.assertEqual(x.proxy_attrs, ['blarg'])

        self.assertEqual(x.alias, 'foo')
        self.assertEqual(x.klass, Spam)

        # compiled attributes
        self.assertEqual(x.encodable_properties, ['bar'])
        self.assertEqual(x.decodable_properties, ['bar'])
        self.assertTrue(x._compiled)

    def test_bad_class(self):
        self.assertRaises(TypeError, ClassAlias, 'eggs', 'blah')

    def test_init_args(self):
        class ClassicFoo:
            def __init__(self, foo, bar):
                pass

        class NewFoo(object):
            def __init__(self, foo, bar):
                pass

        self.assertRaises(TypeError, ClassAlias, ClassicFoo)
        ClassAlias(NewFoo)

    def test_createInstance(self):
        x = ClassAlias(Spam, 'org.example.spam.Spam')

        y = x.createInstance()

        self.assertTrue(isinstance(y, Spam))

    def test_str(self):
        class Eggs(object):
            pass

        x = ClassAlias(Eggs, 'org.example.eggs.Eggs')

        self.assertEqual(str(x), 'org.example.eggs.Eggs')

    def test_eq(self):
        class A(object):
            pass

        class B(object):
            pass

        x = ClassAlias(A, 'org.example.A')
        y = ClassAlias(A, 'org.example.A')
        z = ClassAlias(B, 'org.example.B')

        self.assertEqual(x, A)
        self.assertEqual(x, y)
        self.assertNotEquals(x, z)


class GetEncodableAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.getEncodableAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_empty(self):
        attrs = self.alias.getEncodableAttributes(self.obj)

        self.assertEqual(attrs, {})

    def test_static(self):
        self.alias.static_attrs = ['foo', 'bar']
        self.alias.compile()

        self.obj.foo = 'bar'
        # leave self.obj.bar
        self.assertFalse(hasattr(self.obj, 'bar'))

        attrs = self.alias.getEncodableAttributes(self.obj)

        self.assertEqual(attrs, {'foo': 'bar', 'bar': pyamf.Undefined})

    def test_not_dynamic(self):
        self.alias.compile()
        self.alias.dynamic = False

        self.assertEqual(self.alias.getEncodableAttributes(self.obj), {})

    def test_dynamic(self):
        self.alias.compile()

        self.assertEqual(self.alias.encodable_properties, None)
        self.obj.foo = 'bar'
        self.obj.bar = 'foo'

        attrs = self.alias.getEncodableAttributes(self.obj)
        self.assertEqual(attrs, {'foo': 'bar', 'bar': 'foo'})

    def test_proxy(self):
        from pyamf import flex

        c = pyamf.get_encoder(pyamf.AMF3)

        self.alias.proxy_attrs = ('foo', 'bar')
        self.alias.compile()

        self.assertEqual(self.alias.proxy_attrs, ['bar', 'foo'])

        self.obj.foo = ['bar', 'baz']
        self.obj.bar = {'foo': 'gak'}

        attrs = self.alias.getEncodableAttributes(self.obj, c)

        k = attrs.keys()

        k.sort()

        self.assertEqual(k, ['bar', 'foo'])

        self.assertTrue(isinstance(attrs['foo'], flex.ArrayCollection))
        self.assertEqual(attrs['foo'], ['bar', 'baz'])

        self.assertTrue(isinstance(attrs['bar'], flex.ObjectProxy))
        self.assertEqual(attrs['bar']._amf_object, {'foo': 'gak'})

    def test_synonym(self):
        self.alias.synonym_attrs = {'foo': 'bar'}
        self.alias.compile()

        self.assertFalse(self.alias.shortcut_encode)
        self.assertFalse(self.alias.shortcut_decode)

        self.obj.foo = 'bar'
        self.obj.spam = 'eggs'

        ret = self.alias.getEncodableAttributes(self.obj)

        self.assertEquals(ret, {'bar': 'bar', 'spam': 'eggs'})


class GetDecodableAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.getDecodableAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_compile(self):
        self.assertFalse(self.alias._compiled)

        self.alias.applyAttributes(self.obj, {})

        self.assertTrue(self.alias._compiled)

    def test_missing_static_property(self):
        self.alias.static_attrs = ['foo', 'bar']
        self.alias.compile()

        attrs = {'foo': None} # missing bar key ..

        self.assertRaises(AttributeError, self.alias.getDecodableAttributes,
            self.obj, attrs)

    def test_no_static(self):
        self.alias.compile()

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'foo': None, 'bar': [1, 2, 3]})

    def test_readonly(self):
        self.alias.compile()

        self.alias.readonly_attrs = ['bar']

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'foo': None})

    def test_not_dynamic(self):
        self.alias.compile()

        self.alias.decodable_properties = set(['bar'])
        self.alias.dynamic = False

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'bar': [1, 2, 3]})

    def test_dynamic(self):
        self.alias.compile()

        self.alias.static_properties = ['bar']
        self.alias.dynamic = True

        attrs = {'foo': None, 'bar': [1, 2, 3]}

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'foo': None, 'bar': [1, 2, 3]})

    def test_complex(self):
        self.alias.compile()

        self.alias.static_properties = ['foo', 'bar']
        self.alias.exclude_attrs = ['baz', 'gak']
        self.alias.readonly_attrs = ['spam', 'eggs']

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
            'spam': 'spam',
            'eggs': 'eggs',
            'dyn1': 'dyn1',
            'dyn2': 'dyn2'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {
            'foo': 'foo',
            'bar': 'bar',
            'dyn2': 'dyn2',
            'dyn1': 'dyn1'
        })

    def test_complex_not_dynamic(self):
        self.alias.compile()

        self.alias.decodable_properties = ['foo', 'bar']
        self.alias.exclude_attrs = ['baz', 'gak']
        self.alias.readonly_attrs = ['spam', 'eggs']
        self.alias.dynamic = False

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
            'spam': 'spam',
            'eggs': 'eggs',
            'dyn1': 'dyn1',
            'dyn2': 'dyn2'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'foo': 'foo', 'bar': 'bar'})

    def test_static(self):
        self.alias.dynamic = False
        self.alias.compile()

        self.alias.decodable_properties = set(['foo', 'bar'])

        attrs = {
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz',
            'gak': 'gak',
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEqual(ret, {'foo': 'foo', 'bar': 'bar'})

    def test_proxy(self):
        from pyamf import flex

        c = pyamf.get_encoder(pyamf.AMF3)

        self.alias.proxy_attrs = ('foo', 'bar')
        self.alias.compile()

        self.assertEqual(self.alias.proxy_attrs, ['bar', 'foo'])

        attrs = {
            'foo': flex.ArrayCollection(['bar', 'baz']),
            'bar': flex.ObjectProxy({'foo': 'gak'})
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs, c)

        self.assertEqual(ret, {
            'foo': ['bar', 'baz'],
            'bar': {'foo': 'gak'}
        })

    def test_synonym(self):
        self.alias.synonym_attrs = {'foo': 'bar'}
        self.alias.compile()

        self.assertFalse(self.alias.shortcut_encode)
        self.assertFalse(self.alias.shortcut_decode)

        attrs = {
            'foo': 'foo',
            'spam': 'eggs'
        }

        ret = self.alias.getDecodableAttributes(self.obj, attrs)

        self.assertEquals(ret, {'bar': 'foo', 'spam': 'eggs'})


class ApplyAttributesTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias.applyAttributes}
    """

    def setUp(self):
        self.alias = ClassAlias(Spam, 'foo', defer=True)
        self.obj = Spam()

    def test_object(self):
        class Foo(object):
            pass

        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Foo()
        self.alias = ClassAlias(Foo, 'foo', defer=True)

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})

    def test_classic(self):
        class Foo:
            pass

        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Foo()
        self.alias = ClassAlias(Foo, 'foo', defer=True)

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})

    def test_readonly(self):
        self.alias.readonly_attrs = ['foo', 'bar']

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {})

    def test_exclude(self):
        self.alias.exclude_attrs = ['foo', 'bar']

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {})

    def test_not_dynamic(self):
        self.alias.static_properties = None
        self.alias.dynamic = False

        attrs = {'foo': 'spam', 'bar': 'eggs'}

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {})

    def test_dict(self):
        attrs = {'foo': 'spam', 'bar': 'eggs'}
        self.obj = Spam()

        self.assertEqual(self.obj.__dict__, {})
        self.alias.applyAttributes(self.obj, attrs)

        self.assertEqual(self.obj.__dict__, {'foo': 'spam', 'bar': 'eggs'})


class SimpleCompliationTestCase(unittest.TestCase):
    """
    Tests for L{ClassAlias} property compliation for no inheritance.
    """

    def test_compiled(self):
        x = ClassAlias(Spam, defer=True)

        self.assertFalse(x._compiled)

        x._compiled = True
        o = x.static_properties = object()

        x.compile()

        self.assertTrue(o is x.static_properties)

    def test_external(self):
        class A(object):
            pass

        class B:
            pass

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__readamf__ = None
        B.__readamf__ = None

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__readamf__ = lambda x: None
        B.__readamf__ = lambda x: None

        self.assertRaises(AttributeError, ClassAlias, A, external=True)
        self.assertRaises(AttributeError, ClassAlias, B, external=True)

        A.__writeamf__ = 'foo'
        B.__writeamf__ = 'bar'

        self.assertRaises(TypeError, ClassAlias, A, external=True)
        self.assertRaises(TypeError, ClassAlias, B, external=True)

        A.__writeamf__ = lambda x: None
        B.__writeamf__ = lambda x: None

        a = ClassAlias(A, external=True)
        b = ClassAlias(B, external=True)

        self.assertEqual(a.readonly_attrs, None)
        self.assertEqual(a.static_attrs, [])
        self.assertEqual(a.decodable_properties, None)
        self.assertEqual(a.encodable_properties, None)
        self.assertEqual(a.exclude_attrs, None)

        self.assertTrue(a.anonymous)
        self.assertTrue(a.external)
        self.assertTrue(a._compiled)

        self.assertEqual(a.klass, A)
        self.assertEqual(a.alias, '')

        # now b

        self.assertEqual(b.readonly_attrs, None)
        self.assertEqual(b.static_attrs, [])
        self.assertEqual(b.decodable_properties, None)
        self.assertEqual(b.encodable_properties, None)
        self.assertEqual(b.exclude_attrs, None)

        self.assertTrue(b.anonymous)
        self.assertTrue(b.external)
        self.assertTrue(b._compiled)

        self.assertEqual(b.klass, B)
        self.assertEqual(b.alias, '')

    def test_anonymous(self):
        x = ClassAlias(Spam, None)

        x.compile()

        self.assertTrue(x.anonymous)
        self.assertTrue(x._compiled)

        self.assertEqual(x.klass, Spam)
        self.assertEqual(x.alias, '')

    def test_exclude(self):
        x = ClassAlias(Spam, exclude_attrs=['foo', 'bar'], defer=True)

        self.assertEqual(x.exclude_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEqual(x.exclude_attrs, ['bar', 'foo'])

    def test_readonly(self):
        x = ClassAlias(Spam, readonly_attrs=['foo', 'bar'], defer=True)

        self.assertEqual(x.readonly_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEqual(x.readonly_attrs, ['bar', 'foo'])

    def test_static(self):
        x = ClassAlias(Spam, static_attrs=['foo', 'bar'], defer=True)

        self.assertEqual(x.static_attrs, ['foo', 'bar'])

        x.compile()

        self.assertEqual(x.static_attrs, ['foo', 'bar'])

    def test_custom_properties(self):
        class A(ClassAlias):
            def getCustomProperties(self):
                self.encodable_properties.update(['foo', 'bar'])
                self.decodable_properties.update(['bar', 'foo'])

        a = A(Spam)

        self.assertEqual(a.encodable_properties, ['bar', 'foo'])
        self.assertEqual(a.decodable_properties, ['bar', 'foo'])

        # test combined
        b = A(Spam, static_attrs=['foo', 'baz', 'gak'])

        self.assertEqual(b.encodable_properties, ['bar', 'baz', 'foo', 'gak'])
        self.assertEqual(b.decodable_properties, ['bar', 'baz', 'foo', 'gak'])

    def test_amf3(self):
        x = ClassAlias(Spam, amf3=True)
        self.assertTrue(x.amf3)

    def test_dynamic(self):
        x = ClassAlias(Spam, dynamic=True)
        self.assertTrue(x.dynamic)

        x = ClassAlias(Spam, dynamic=False)
        self.assertFalse(x.dynamic)

        x = ClassAlias(Spam)
        self.assertTrue(x.dynamic)

    def test_sealed_external(self):
        class A(object):
            __slots__ = ('foo',)

            class __amf__:
                external = True

            def __readamf__(self, foo):
                pass

            def __writeamf__(self, foo):
                pass

        x = ClassAlias(A)

        x.compile()

        self.assertTrue(x.sealed)

    def test_synonym_attrs(self):
        x = ClassAlias(Spam, synonym_attrs={'foo': 'bar'}, defer=True)

        self.assertEquals(x.synonym_attrs, {'foo': 'bar'})

        x.compile()

        self.assertEquals(x.synonym_attrs, {'foo': 'bar'})


class CompilationInheritanceTestCase(ClassCacheClearingTestCase):
    """
    """

    def _register(self, alias):
        pyamf.CLASS_CACHE[get_fqcn(alias.klass)] = alias
        pyamf.CLASS_CACHE[alias.klass] = alias

        return alias

    def test_bases(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', defer=True))

        self.assertEqual(a.bases, None)
        self.assertEqual(b.bases, None)
        self.assertEqual(c.bases, None)

        a.compile()
        self.assertEqual(a.bases, [])

        b.compile()
        self.assertEqual(a.bases, [])
        self.assertEqual(b.bases, [(A, a)])

        c.compile()
        self.assertEqual(a.bases, [])
        self.assertEqual(b.bases, [(A, a)])
        self.assertEqual(c.bases, [(B, b), (A, a)])


    def test_exclude_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', exclude_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', exclude_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.exclude_attrs, ['foo'])
        self.assertEqual(b.exclude_attrs, ['foo'])
        self.assertEqual(c.exclude_attrs, ['bar', 'foo'])

    def test_exclude_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', exclude_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', exclude_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.exclude_attrs, ['foo'])
        self.assertEqual(b.exclude_attrs, ['foo'])
        self.assertEqual(c.exclude_attrs, ['bar', 'foo'])

    def test_readonly_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', readonly_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', readonly_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.readonly_attrs, ['foo'])
        self.assertEqual(b.readonly_attrs, ['foo'])
        self.assertEqual(c.readonly_attrs, ['bar', 'foo'])

    def test_readonly_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', readonly_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', readonly_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.readonly_attrs, ['foo'])
        self.assertEqual(b.readonly_attrs, ['foo'])
        self.assertEqual(c.readonly_attrs, ['bar', 'foo'])

    def test_static_classic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', static_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', static_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.static_attrs, ['foo'])
        self.assertEqual(b.static_attrs, ['foo'])
        self.assertEqual(c.static_attrs, ['foo', 'bar'])

    def test_static_new(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', static_attrs=['foo'], defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', static_attrs=['bar'], defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEqual(a.static_attrs, ['foo'])
        self.assertEqual(b.static_attrs, ['foo'])
        self.assertEqual(c.static_attrs, ['foo', 'bar'])

    def test_amf3(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', amf3=True, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', amf3=False, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertTrue(a.amf3)
        self.assertTrue(b.amf3)
        self.assertFalse(c.amf3)

    def test_dynamic(self):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', dynamic=False, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', dynamic=True, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertFalse(a.dynamic)
        self.assertFalse(b.dynamic)
        self.assertTrue(c.dynamic)


    def test_synonym_attrs(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(B):
            pass

        a = self._register(ClassAlias(A, 'a', synonym_attrs={'foo': 'bar', 'bar': 'baz'}, defer=True))
        b = self._register(ClassAlias(B, 'b', defer=True))
        c = self._register(ClassAlias(C, 'c', synonym_attrs={'bar': 'spam'}, defer=True))

        self.assertFalse(a._compiled)
        self.assertFalse(b._compiled)
        self.assertFalse(c._compiled)

        c.compile()

        self.assertTrue(a._compiled)
        self.assertTrue(b._compiled)
        self.assertTrue(c._compiled)

        self.assertEquals(a.synonym_attrs, {'foo': 'bar', 'bar': 'baz'})
        self.assertEquals(b.synonym_attrs, {'foo': 'bar', 'bar': 'baz'})
        self.assertEquals(c.synonym_attrs, {'foo': 'bar', 'bar': 'spam'})


class CompilationIntegrationTestCase(unittest.TestCase):
    """
    Integration tests for ClassAlias's
    """

    def test_slots_classic(self):
        class A:
            __slots__ = ('foo', 'bar')

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        class D(C, B):
            __slots__ = ('spam',)

        a = ClassAlias(A)

        self.assertFalse(a.dynamic)
        self.assertEqual(a.encodable_properties, ['bar', 'foo'])
        self.assertEqual(a.decodable_properties, ['bar', 'foo'])

        b = ClassAlias(B)

        self.assertFalse(b.dynamic)
        self.assertEqual(b.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEqual(b.decodable_properties, ['bar', 'foo', 'gak'])

        c = ClassAlias(C)

        self.assertFalse(c.dynamic)
        self.assertEqual(c.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEqual(c.decodable_properties, ['bar', 'foo', 'gak'])

        d = ClassAlias(D)

        self.assertFalse(d.dynamic)
        self.assertEqual(d.encodable_properties, ['bar', 'foo', 'gak', 'spam'])
        self.assertEqual(d.decodable_properties, ['bar', 'foo', 'gak', 'spam'])

    def test_slots_new(self):
        class A(object):
            __slots__ = ('foo', 'bar')

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        class D(C, B):
            __slots__ = ('spam',)

        a = ClassAlias(A)

        self.assertFalse(a.dynamic)
        self.assertEqual(a.encodable_properties, ['bar', 'foo'])
        self.assertEqual(a.decodable_properties, ['bar', 'foo'])

        b = ClassAlias(B)

        self.assertFalse(b.dynamic)
        self.assertEqual(b.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEqual(b.decodable_properties, ['bar', 'foo', 'gak'])

        c = ClassAlias(C)

        self.assertTrue(c.dynamic)
        self.assertEqual(c.encodable_properties, ['bar', 'foo', 'gak'])
        self.assertEqual(c.decodable_properties, ['bar', 'foo', 'gak'])

        d = ClassAlias(D)

        self.assertTrue(d.dynamic)
        self.assertEqual(d.encodable_properties, ['bar', 'foo', 'gak', 'spam'])
        self.assertEqual(d.decodable_properties, ['bar', 'foo', 'gak', 'spam'])

    def test_properties(self):
        class A:
            a_rw = property(lambda _: None, lambda _, x: None)
            a_ro = property(lambda _: None)

        class B(A):
            b_rw = property(lambda _: None, lambda _, x: None)
            b_ro = property(lambda _: None)

        class C(B):
            pass

        a = ClassAlias(A)

        self.assertTrue(a.dynamic)
        self.assertEqual(a.encodable_properties, ['a_ro', 'a_rw'])
        self.assertEqual(a.decodable_properties, ['a_rw'])

        b = ClassAlias(B)

        self.assertTrue(b.dynamic)
        self.assertEqual(b.encodable_properties, ['a_ro', 'a_rw', 'b_ro', 'b_rw'])
        self.assertEqual(b.decodable_properties, ['a_rw', 'b_rw'])

        c = ClassAlias(C)

        self.assertTrue(c.dynamic)
        self.assertEqual(c.encodable_properties, ['a_ro', 'a_rw', 'b_ro', 'b_rw'])
        self.assertEqual(c.decodable_properties, ['a_rw', 'b_rw'])


class RegisterClassTestCase(ClassCacheClearingTestCase):
    """
    Tests for L{pyamf.register_class}
    """

    def tearDown(self):
        ClassCacheClearingTestCase.tearDown(self)

        if hasattr(Spam, '__amf__'):
            del Spam.__amf__

    def test_meta(self):
        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE.keys())

        Spam.__amf__ = {
            'alias': 'spam.eggs'
        }

        alias = pyamf.register_class(Spam)

        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())
        self.assertEqual(pyamf.CLASS_CACHE['spam.eggs'], alias)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertEqual(alias.klass, Spam)
        self.assertEqual(alias.alias, 'spam.eggs')

        self.assertFalse(alias._compiled)

    def test_kwarg(self):
        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE.keys())

        alias = pyamf.register_class(Spam, 'spam.eggs')

        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())
        self.assertEqual(pyamf.CLASS_CACHE['spam.eggs'], alias)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertEqual(alias.klass, Spam)
        self.assertEqual(alias.alias, 'spam.eggs')

        self.assertFalse(alias._compiled)


class UnregisterClassTestCase(ClassCacheClearingTestCase):
    """
    Tests for L{pyamf.unregister_class}
    """

    def test_alias(self):
        self.assertFalse('foo' in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, pyamf.unregister_class, 'foo')

    def test_class(self):
        self.assertFalse(Spam in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, pyamf.unregister_class, Spam)

    def test_remove(self):
        alias = ClassAlias(Spam, 'foo', defer=True)

        pyamf.CLASS_CACHE['foo'] = alias
        pyamf.CLASS_CACHE[Spam] = alias

        self.assertFalse(alias.anonymous)
        ret = pyamf.unregister_class('foo')

        self.assertFalse('foo' in pyamf.CLASS_CACHE)
        self.assertFalse(Spam in pyamf.CLASS_CACHE)
        self.assertTrue(ret is alias)

    def test_anonymous(self):
        alias = ClassAlias(Spam, defer=True)

        pyamf.CLASS_CACHE['foo'] = alias
        pyamf.CLASS_CACHE[Spam] = alias

        self.assertTrue(alias.anonymous)
        ret = pyamf.unregister_class(Spam)

        self.assertTrue('foo' in pyamf.CLASS_CACHE)
        self.assertFalse(Spam in pyamf.CLASS_CACHE)
        self.assertTrue(ret is alias)

########NEW FILE########
__FILENAME__ = test_amf0
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF0 Implementation.

@since: 0.1.0
"""

import unittest
import datetime

import pyamf
from pyamf import amf0, util, xml, python
from pyamf.tests.util import (
    EncoderMixIn, DecoderMixIn, ClassCacheClearingTestCase, Spam, ClassicSpam)


class TypesTestCase(unittest.TestCase):
    """
    Tests the type mappings.
    """

    def test_types(self):
        self.assertEqual(amf0.TYPE_NUMBER, '\x00')
        self.assertEqual(amf0.TYPE_BOOL, '\x01')
        self.assertEqual(amf0.TYPE_STRING, '\x02')
        self.assertEqual(amf0.TYPE_OBJECT, '\x03')
        self.assertEqual(amf0.TYPE_MOVIECLIP, '\x04')
        self.assertEqual(amf0.TYPE_NULL, '\x05')
        self.assertEqual(amf0.TYPE_UNDEFINED, '\x06')
        self.assertEqual(amf0.TYPE_REFERENCE, '\x07')
        self.assertEqual(amf0.TYPE_MIXEDARRAY, '\x08')
        self.assertEqual(amf0.TYPE_OBJECTTERM, '\x09')
        self.assertEqual(amf0.TYPE_ARRAY, '\x0a')
        self.assertEqual(amf0.TYPE_DATE, '\x0b')
        self.assertEqual(amf0.TYPE_LONGSTRING, '\x0c')
        self.assertEqual(amf0.TYPE_UNSUPPORTED, '\x0d')
        self.assertEqual(amf0.TYPE_RECORDSET, '\x0e')
        self.assertEqual(amf0.TYPE_XML, '\x0f')
        self.assertEqual(amf0.TYPE_TYPEDOBJECT, '\x10')
        self.assertEqual(amf0.TYPE_AMF3, '\x11')


class EncoderTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    Tests the output from the AMF0 L{Encoder<pyamf.amf0.Encoder>} class.
    """

    amf_type = pyamf.AMF0

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_number(self):
        self.assertEncoded(0, '\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(0.2, '\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a')
        self.assertEncoded(1, '\x00\x3f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(42, '\x00\x40\x45\x00\x00\x00\x00\x00\x00')
        self.assertEncoded(-123, '\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00')
        self.assertEncoded(1.23456789, '\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b')

    def test_boolean(self):
        self.assertEncoded(True, '\x01\x01')
        self.assertEncoded(False, '\x01\x00')

    def test_string(self):
        self.assertEncoded('', '\x02\x00\x00')
        self.assertEncoded('hello', '\x02\x00\x05hello')
        # unicode taken from http://www.columbia.edu/kermit/utf8.html
        self.assertEncoded(u'ᚠᛇᚻ', '\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb')

    def test_null(self):
        self.assertEncoded(None, '\x05')

    def test_undefined(self):
        self.assertEncoded(pyamf.Undefined, '\x06')

    def test_list(self):
        self.assertEncoded([], '\x0a\x00\x00\x00\x00')
        self.assertEncoded([1, 2, 3],
            '\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00\x00\x00\x40'
            '\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00\x00\x00\x00\x00')
        self.assertEncoded((1, 2, 3), '\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00'
            '\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00'
            '\x40\x08\x00\x00\x00\x00\x00\x00')

    def test_list_references(self):
        x = []

        self.assertEqual(self.encode(x, x), '\n\x00\x00\x00\x00\x07\x00\x00')

    def test_longstring(self):
        s = 'a' * 65537

        self.assertEncoded(s, '\x0c\x00\x01\x00\x01' + s)

    def test_dict(self):
        self.assertEncoded({'a': 'a'}, '\x03\x00\x01a\x02\x00\x01a\x00\x00\t')

        self.assertEncoded({12: True, 42: "Testing"}, '\x03', (
            '\x00\x0242\x02\x00\x07Testing',
            '\x00\x0212\x01\x01'
        ), '\x00\x00\t')

    def test_mixed_array(self):
        d = pyamf.MixedArray(a=1, b=2, c=3)

        bytes = ('\x08\x00\x00\x00\x00', (
            '\x00\x01a\x00?\xf0\x00\x00\x00\x00\x00\x00',
            '\x00\x01c\x00@\x08\x00\x00\x00\x00\x00\x00',
            '\x00\x01b\x00@\x00\x00\x00\x00\x00\x00\x00'
        ), '\x00\x00\t')

        self.assertEncoded(d, bytes)

        # test the reference
        self.assertEqual(self.encode(d), '\x07\x00\x00')

    def test_date(self):
        self.assertEncoded(datetime.datetime(2005, 3, 18, 1, 58, 31),
            '\x0bBp+6!\x15\x80\x00\x00\x00')
        self.assertEncoded(datetime.date(2003, 12, 1),
            '\x0bBo%\xe2\xb2\x80\x00\x00\x00\x00')
        self.assertEncoded(datetime.datetime(2009, 3, 8, 23, 30, 47, 770122),
            '\x0bBq\xfe\x86\xca5\xa1\xf4\x00\x00')

        self.assertRaises(pyamf.EncodeError, self.encode, datetime.time(22, 3))

    def test_xml(self):
        blob = '<a><b>hello world</b></a>'

        self.assertEncoded(xml.fromstring(blob),
            '\x0f\x00\x00\x00\x19' + blob)

    def test_xml_references(self):
        blob = '<a><b>hello world</b></a>'
        x = xml.fromstring(blob)

        self.assertEncoded([x, x], '\n\x00\x00\x00\x02' +
                ('\x0f\x00\x00\x00\x19' + blob) * 2)

    def test_object(self):
        self.assertEncoded({'a': 'b'}, '\x03\x00\x01a\x02\x00\x01b\x00\x00\x09')

    def test_force_amf3(self):
        alias = pyamf.register_class(Spam, 'spam.eggs')
        alias.amf3 = True

        x = Spam()
        x.x = 'y'

        self.assertEncoded(x, '\x11\n\x0b\x13spam.eggs\x03x\x06\x03y\x01')

    def test_typed_object(self):
        pyamf.register_class(Spam, alias='org.pyamf.spam')

        x = Spam()
        x.baz = 'hello'

        self.assertEncoded(x, '\x10\x00\x0eorg.pyamf.spam\x00\x03baz'
            '\x02\x00\x05hello\x00\x00\t')

    def test_complex_list(self):
        self.assertEncoded([[1.0]], '\x0a\x00\x00\x00\x01\x0a\x00\x00\x00\x01'
            '\x00\x3f\xf0\x00\x00\x00\x00\x00\x00')

        self.assertEncoded([['test', 'test', 'test', 'test']],
            '\x0a\x00\x00\x00\x01\x0a\x00\x00\x00\x04' + ('\x02\x00\x04test' * 4))

        x = {'a': 'spam', 'b': 'eggs'}

        self.assertEncoded([[x, x]], '\n\x00\x00\x00\x01\n\x00\x00\x00\x02'
            '\x03\x00\x01a\x02\x00\x04spam\x00\x01b\x02\x00\x04eggs\x00\x00'
            '\t\x07\x00\x02')

    def test_amf3(self):
        self.encoder.use_amf3 = True

        o = Spam()

        self.assertEncoded(o, '\x11\n\x0b\x01\x01')

    def test_anonymous(self):
        pyamf.register_class(Spam)

        x = Spam()
        x.spam = 'eggs'
        x.hello = 'world'

        self.assertEncoded(x, '\x03', ('\x00\x05hello\x02\x00\x05world',
            '\x00\x04spam\x02\x00\x04eggs'), '\x00\x00\t')

    def test_dynamic(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam)

        alias.exclude_attrs = ['foo']

        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(x, '\x03\x00\x05hello\x02\x00\x05world\x00\x00\t')

    def test_dynamic_static(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam)

        alias.static_attrs = ['hello']
        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(x, '\x03', ('\x00\x05hello\x02\x00\x05world',
            '\x00\x03foo\x02\x00\x03bar'), '\x00\x00\t')

    def test_dynamic_registered(self):
        x = Spam()

        x.foo = 'bar'
        x.hello = 'world'

        alias = pyamf.register_class(Spam, 'x')

        alias.exclude_attrs = ['foo']

        alias.compile()

        self.assertTrue(alias.dynamic)

        self.assertEncoded(x, '\x10\x00\x01x', '\x00\x05hello\x02\x00\x05world',
            '\x00\x00\t')

    def test_custom_type(self):
        def write_as_list(list_interface_obj, encoder):
            list_interface_obj.ran = True
            self.assertEqual(id(encoder), id(self.encoder))

            return list(list_interface_obj)

        class ListWrapper(object):
            ran = False

            def __iter__(self):
                return iter([1, 2, 3])

        pyamf.add_type(ListWrapper, write_as_list)
        x = ListWrapper()

        self.encoder.writeElement(x)
        self.assertEqual(x.ran, True)

        self.assertEqual(self.buf.getvalue(), '\n\x00\x00\x00\x03\x00?\xf0'
            '\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00@'
            '\x08\x00\x00\x00\x00\x00\x00')

    def test_old_style_classes(self):
        class Person:
            pass

        pyamf.register_class(Person, 'spam.eggs.Person')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.encoder.writeElement(u)

        self.assertEncoded(u, '\x10\x00\x10spam.eggs.Person', (
            '\x00\x0bfamily_name\x02\x00\x03Doe',
            '\x00\ngiven_name\x02\x00\x04Jane'
        ), '\x00\x00\t')

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.assertEncoded(u, '\x03', (
            '\x00\x0bfamily_name\x02\x00\x03Doe',
            '\x00\ngiven_name\x02\x00\x04Jane'
        ), '\x00\x00\t')

    def test_slots_registered(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        pyamf.register_class(Person, 'spam.eggs.Person')

        self.assertEncoded(u, '\x10\x00\x10spam.eggs.Person', (
            '\x00\x0bfamily_name\x02\x00\x03Doe',
            '\x00\ngiven_name\x02\x00\x04Jane'
        ), '\x00\x00\t')

    def test_elementtree_tag(self):
        """
        Pretend to look like an ElementTree object to try to fool PyAMF into
        encoding an xml type.
        """
        class NotAnElement(object):
            items = lambda self: []

            def __iter__(self):
                return iter([])

        foo = NotAnElement()
        foo.tag = 'foo'
        foo.text = 'bar'
        foo.tail = None

        self.assertEncoded(foo, '\x03', (
            '\x00\x04text\x02\x00\x03bar',
            '\x00\x04tail\x05',
            '\x00\x03tag\x02\x00\x03foo',
        ), '\x00\x00\t')

    def test_funcs(self):
        def x():
            pass

        for i in (chr, self.assertRaises, lambda x: x, pyamf):
            self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, i)

    def test_external_subclassed_list(self):
        class L(list):
            class __amf__:
                external = True

            def __readamf__(self, o):
                pass

            def __writeamf__(self, o):
                pass

        pyamf.register_class(L, 'a')

        a = L()

        a.append('foo')
        a.append('bar')

        self.assertEncoded(a, '\x10\x00\x01a\x00\x00\t')

    def test_nonexternal_subclassed_list(self):
        class L(list):
            pass

        pyamf.register_class(L, 'a')

        a = L()

        a.append('foo')
        a.append('bar')

        self.assertEncoded(a, '\n\x00\x00\x00\x02\x02\x00\x03foo\x02\x00\x03bar')

    def test_amf3_xml(self):
        self.encoder.use_amf3 = True
        blob = '<root><sections><section /><section /></sections></root>'

        blob = xml.tostring(xml.fromstring(blob))

        bytes = self.encode(xml.fromstring(blob))

        buf = util.BufferedByteStream(bytes)

        self.assertEqual(buf.read_uchar(), 17)
        self.assertEqual(buf.read_uchar(), 11)
        self.assertEqual(buf.read_uchar() >> 1, buf.remaining())
        self.assertEqual(buf.read(), blob)

    def test_use_amf3(self):
        self.encoder.use_amf3 = True

        x = {'foo': 'bar', 'baz': 'gak'}

        self.assertEncoded(x, '\x11\n\x0b', ('\x01\x07foo\x06\x07bar',
            '\x07baz\x06\x07gak\x01'))

    def test_static_attrs(self):
        class Foo(object):
            class __amf__:
                static = ('foo', 'bar')

        pyamf.register_class(Foo)

        x = Foo()
        x.foo = 'baz'
        x.bar = 'gak'

        self.assertEncoded(x, '\x03', ('\x00\x03bar\x02\x00\x03gak',
            '\x00\x03foo\x02\x00\x03baz'), '\x00\x00\t')

    def test_class(self):
        class Classic:
            pass

        class New(object):
            pass

        self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, Classic)
        self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, New)

    def test_timezone(self):
        d = datetime.datetime(2009, 9, 24, 14, 23, 23)
        self.encoder.timezone_offset = datetime.timedelta(hours=-5)

        self.assertEncoded(d, '\x0bBr>\xd8\x1f\xff\x80\x00\x00\x00')

    def test_generators(self):
        def foo():
            yield [1, 2, 3]
            yield '\xff'
            yield pyamf.Undefined

        self.assertEncoded(foo(), '\n\x00\x00\x00\x03\x00?\xf0\x00\x00\x00\x00'
            '\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00@\x08\x00\x00\x00\x00'
            '\x00\x00\x02\x00\x01\xff\x06')

    def test_iterate(self):
        self.assertRaises(StopIteration, self.encoder.next)

        self.encoder.send('')
        self.encoder.send('hello')
        self.encoder.send(u'ƒøø')

        self.assertEqual(self.encoder.next(), '\x02\x00\x00')
        self.assertEqual(self.encoder.next(), '\x02\x00\x05hello')
        self.assertEqual(self.encoder.next(), '\x02\x00\x06\xc6\x92\xc3\xb8\xc3\xb8')

        self.assertRaises(StopIteration, self.encoder.next)

        self.assertIdentical(iter(self.encoder), self.encoder)
        self.assertEqual(self.buf.getvalue(),
            '\x02\x00\x00\x02\x00\x05hello\x02\x00\x06\xc6\x92\xc3\xb8\xc3\xb8')


    def test_subclassed_tuple(self):
        """
        A subclassed tuple must encode an AMF list.

        @see: #830
        """
        class Foo(tuple):
            pass

        x = Foo([1,2])

        self.encoder.send(x)

        self.assertEqual(self.encoder.next(), '\n\x00\x00\x00\x02\x00?\xf0\x00'
            '\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00')



class DecoderTestCase(ClassCacheClearingTestCase, DecoderMixIn):
    """
    Tests the output from the AMF0 L{Decoder<pyamf.amf0.Decoder>} class.
    """

    amf_type = pyamf.AMF0

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        DecoderMixIn.setUp(self)

    def test_undefined(self):
        self.assertDecoded(pyamf.Undefined, '\x06')

    def test_number(self):
        self.assertDecoded(0, '\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(0.2, '\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a')
        self.assertDecoded(1, '\x00\x3f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(42, '\x00\x40\x45\x00\x00\x00\x00\x00\x00')
        self.assertDecoded(-123, '\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00')
        self.assertDecoded(1.23456789, '\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b')

    def test_number_types(self):
        nr_types = [
            ('\x00\x00\x00\x00\x00\x00\x00\x00\x00', int),
            ('\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a', float),
            ('\x00\x3f\xf0\x00\x00\x00\x00\x00\x00', int),
            ('\x00\x40\x45\x00\x00\x00\x00\x00\x00', int),
            ('\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00', int),
            ('\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b', float),
            ('\x00\xff\xf8\x00\x00\x00\x00\x00\x00', float), # nan
            ('\x00\xff\xf0\x00\x00\x00\x00\x00\x00', float), # -inf
            ('\x00\x7f\xf0\x00\x00\x00\x00\x00\x00', float), # inf
        ]

        for t in nr_types:
            bytes, expected_type = t
            self.buf.truncate()
            self.buf.write(bytes)
            self.buf.seek(0)
            self.assertEqual(type(self.decoder.readElement()), expected_type)

    def test_infinites(self):
        self.buf.truncate()
        self.buf.write('\x00\xff\xf8\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isNaN(x))

        self.buf.truncate()
        self.buf.write('\x00\xff\xf0\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isNegInf(x))

        self.buf.truncate()
        self.buf.write('\x00\x7f\xf0\x00\x00\x00\x00\x00\x00')
        self.buf.seek(0)
        x = self.decoder.readElement()
        self.assertTrue(python.isPosInf(x))

    def test_boolean(self):
        self.assertDecoded(True, '\x01\x01')
        self.assertDecoded(False, '\x01\x00')

    def test_string(self):
        self.assertDecoded('', '\x02\x00\x00')
        self.assertDecoded('hello', '\x02\x00\x05hello')
        self.assertDecoded(u'ᚠᛇᚻ',
            '\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb')

    def test_longstring(self):
        a = 'a' * 65537

        self.assertDecoded(a, '\x0c\x00\x01\x00\x01' + a)

    def test_null(self):
        self.assertDecoded(None, '\x05')

    def test_list(self):
        self.assertDecoded([], '\x0a\x00\x00\x00\x00')
        self.assertDecoded([1, 2, 3], '\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00'
            '\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x40'
            '\x08\x00\x00\x00\x00\x00\x00')

    def test_dict(self):
        bytes = '\x08\x00\x00\x00\x00\x00\x01\x61\x02\x00\x01\x61\x00\x00\x09'

        self.assertDecoded({'a': 'a'}, bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        d = self.decoder.readElement()

    def test_mixed_array(self):
        bytes = ('\x08\x00\x00\x00\x00\x00\x01a\x00?\xf0\x00\x00\x00\x00\x00'
            '\x00\x00\x01c\x00@\x08\x00\x00\x00\x00\x00\x00\x00\x01b\x00@\x00'
            '\x00\x00\x00\x00\x00\x00\x00\x00\t')

        self.assertDecoded(pyamf.MixedArray(a=1, b=2, c=3), bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        d = self.decoder.readElement()

    def test_date(self):
        self.assertDecoded(datetime.datetime(2005, 3, 18, 1, 58, 31),
            '\x0bBp+6!\x15\x80\x00\x00\x00')
        self.assertDecoded(datetime.datetime(2009, 3, 8, 23, 30, 47, 770122),
            '\x0bBq\xfe\x86\xca5\xa1\xf4\x00\x00')

    def test_xml(self):
        e = '<a><b>hello world</b></a>'
        ret = self.decode('\x0f\x00\x00\x00\x19' + e)

        self.assertEqual(xml.tostring(ret), e)

    def test_xml_references(self):
        self.buf.truncate(0)
        self.buf.write('\x0f\x00\x00\x00\x19<a><b>hello world</b></a>'
            '\x07\x00\x00')
        self.buf.seek(0)

        self.assertEqual(
            xml.tostring(xml.fromstring('<a><b>hello world</b></a>')),
            xml.tostring(self.decoder.readElement()))

        self.assertEqual(
            xml.tostring(xml.fromstring('<a><b>hello world</b></a>')),
            xml.tostring(self.decoder.readElement()))

    def test_object(self):
        bytes = '\x03\x00\x01a\x02\x00\x01b\x00\x00\x09'

        self.assertDecoded({'a': 'b'}, bytes)

        self.buf.write(bytes)
        self.buf.seek(0)
        d = self.decoder.readElement()

    def test_registered_class(self):
        pyamf.register_class(Spam, alias='org.pyamf.spam')

        bytes = ('\x10\x00\x0eorg.pyamf.spam\x00\x03baz'
            '\x02\x00\x05hello\x00\x00\x09')

        obj = self.decode(bytes)

        self.assertEqual(type(obj), Spam)

        self.assertTrue(hasattr(obj, 'baz'))
        self.assertEqual(obj.baz, 'hello')

    def test_complex_list(self):
        x = datetime.datetime(2007, 11, 3, 8, 7, 37, 437000)

        self.assertDecoded([['test','test','test','test']],
            '\x0A\x00\x00\x00\x01\x0A\x00\x00\x00\x04\x02\x00\x04\x74\x65\x73'
            '\x74\x02\x00\x04\x74\x65\x73\x74\x02\x00\x04\x74\x65\x73\x74\x02'
            '\x00\x04\x74\x65\x73\x74')
        self.assertDecoded([x], '\x0a\x00\x00\x00\x01\x0b\x42\x71\x60\x48\xcf'
            '\xed\xd0\x00\x00\x00')
        self.assertDecoded(
            [[{u'a': u'spam', u'b': u'eggs'}, {u'a': u'spam', u'b': u'eggs'}]],
            '\n\x00\x00\x00\x01\n\x00\x00\x00\x02\x08\x00\x00\x00\x00\x00\x01'
            'a\x02\x00\x04spam\x00\x01b\x02\x00\x04eggs\x00\x00\t\x07\x00\x02')
        self.assertDecoded([[1.0]], '\x0A\x00\x00\x00\x01\x0A\x00\x00\x00\x01'
            '\x00\x3F\xF0\x00\x00\x00\x00\x00\x00')

    def test_amf3(self):
        self.buf.write('\x11\x04\x01')
        self.buf.seek(0)

        self.assertEqual(self.decoder.readElement(), 1)

    def test_dynamic(self):
        class Foo(pyamf.ASObject):
            pass

        x = Foo()

        x.foo = 'bar'

        alias = pyamf.register_class(Foo, 'x')
        alias.exclude_attrs = ['hello']

        self.assertDecoded(x, '\x10\x00\x01x\x00\x03foo\x02\x00\x03bar\x00'
            '\x05hello\x02\x00\x05world\x00\x00\t')

    def test_classic_class(self):
        pyamf.register_class(ClassicSpam, 'spam.eggs')

        self.buf.write('\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t')
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertEqual(foo.foo, 'bar')

    def test_not_strict(self):
        self.assertFalse(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write('\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t')
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        obj = self.decoder.readElement()

        self.assertTrue(isinstance(obj, pyamf.TypedObject))
        self.assertEqual(obj.alias, 'spam.eggs')
        self.assertEqual(obj, {'foo': 'bar'})

    def test_strict(self):
        self.decoder.strict = True

        self.assertTrue(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write('\x10\x00\tspam.eggs\x00\x03foo\x02\x00\x03bar\x00\x00\t')
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, self.decoder.readElement)

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        self.buf.write('\x03\x00\x0bfamily_name\x02\x00\x03Doe\x00\n'
            'given_name\x02\x00\x04Jane\x00\x00\t')
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertEqual(foo.family_name, 'Doe')
        self.assertEqual(foo.given_name, 'Jane')

    def test_slots_registered(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        pyamf.register_class(Person, 'spam.eggs.Person')

        self.buf.write('\x10\x00\x10spam.eggs.Person\x00\x0bfamily_name\x02'
            '\x00\x03Doe\x00\ngiven_name\x02\x00\x04Jane\x00\x00\t')
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertTrue(isinstance(foo, Person))
        self.assertEqual(foo.family_name, 'Doe')
        self.assertEqual(foo.given_name, 'Jane')

    def test_ioerror_buffer_position(self):
        """
        Test to ensure that if an IOError is raised by `readElement` that
        the original position of the stream is restored.
        """
        bytes = pyamf.encode(u'foo', [1, 2, 3], encoding=pyamf.AMF0).getvalue()

        self.buf.write(bytes[:-1])
        self.buf.seek(0)

        self.decoder.readElement()
        self.assertEqual(self.buf.tell(), 6)

        self.assertRaises(IOError, self.decoder.readElement)
        self.assertEqual(self.buf.tell(), 6)

    def test_timezone(self):
        self.decoder.timezone_offset = datetime.timedelta(hours=-5)

        self.buf.write('\x0bBr>\xc6\xf5w\x80\x00\x00\x00')
        self.buf.seek(0)

        f = self.decoder.readElement()

        self.assertEqual(f, datetime.datetime(2009, 9, 24, 9, 23, 23))

    def test_unsupported(self):
        self.assertDecoded(None, '\x0D')

    def test_bad_reference(self):
        self.assertRaises(pyamf.ReferenceError, self.decode, '\x07\x00\x03')

    def test_iterate(self):
        self.assertRaises(StopIteration, self.decoder.next)

        self.decoder.send('\x02\x00\x00')
        self.decoder.send('\x02\x00\x05hello')
        self.decoder.send('\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb')

        self.assertEqual(self.decoder.next(), '')
        self.assertEqual(self.decoder.next(), 'hello')
        self.assertEqual(self.decoder.next(), u'\u16a0\u16c7\u16bb')

        self.assertRaises(StopIteration, self.decoder.next)

        self.assertIdentical(iter(self.decoder), self.decoder)

    def test_bad_type(self):
        self.assertRaises(pyamf.DecodeError, self.decode, '\xff')

    def test_kwargs(self):
        """
        Python <= 3 demand that kwargs keys be bytes instead of unicode/string.
        """
        def f(**kwargs):
            self.assertEqual(kwargs, {'a': 'a'})

        kwargs = self.decode('\x03\x00\x01a\x02\x00\x01a\x00\x00\t')

        f(**kwargs)

    def test_numerical_keys_mixed_array(self):
        """
        Numerical keys in L{pyamf.MixedArray} must not cause a KeyError on
        decode.

        @see: #843
        """
        x = pyamf.MixedArray({'10': u'foobar'})

        bytes = pyamf.encode(x, encoding=pyamf.AMF0)

        d = list(pyamf.decode(bytes, encoding=pyamf.AMF0))

        self.assertEqual(d, [{10: u'foobar'}])



class RecordSetTestCase(unittest.TestCase, EncoderMixIn, DecoderMixIn):
    """
    Tests for L{amf0.RecordSet}
    """

    amf_type = pyamf.AMF0
    blob = (
        '\x10\x00\tRecordSet\x00\nserverInfo\x03', (
            '\x00\x06cursor\x00?\xf0\x00\x00\x00\x00\x00\x00',
            '\x00\x0bcolumnNames\n\x00\x00\x00\x03\x02\x00\x01a\x02\x00\x01b\x02\x00\x01c',
            '\x00\x0binitialData\n\x00\x00\x00\x03\n\x00\x00\x00\x03\x00?\xf0'
                '\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00'
                '@\x08\x00\x00\x00\x00\x00\x00\n\x00\x00\x00\x03\x00@\x10\x00'
                '\x00\x00\x00\x00\x00\x00@\x14\x00\x00\x00\x00\x00\x00\x00@\x18'
                '\x00\x00\x00\x00\x00\x00\n\x00\x00\x00\x03\x00@\x1c\x00\x00'
                '\x00\x00\x00\x00\x00@ \x00\x00\x00\x00\x00\x00\x00@"\x00\x00'
                '\x00\x00\x00\x00',
            '\x00\x07version\x00?\xf0\x00\x00\x00\x00\x00\x00',
            '\x00\ntotalCount\x00@\x08\x00\x00\x00\x00\x00\x00'),
        '\x00\x00\t\x00\x00\t')

    def setUp(self):
        unittest.TestCase.setUp(self)
        EncoderMixIn.setUp(self)
        DecoderMixIn.setUp(self)

    def test_create(self):
        x = amf0.RecordSet()

        self.assertEqual(x.columns, [])
        self.assertEqual(x.items, [])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

        x = amf0.RecordSet(columns=['spam', 'eggs'], items=[[1, 2]])

        self.assertEqual(x.columns, ['spam', 'eggs'])
        self.assertEqual(x.items, [[1, 2]])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

        x = amf0.RecordSet(service={}, id=54)

        self.assertEqual(x.columns, [])
        self.assertEqual(x.items, [])
        self.assertEqual(x.service, {})
        self.assertEqual(x.id, 54)

    def test_server_info(self):
        # empty recordset
        x = amf0.RecordSet()

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, [])
        self.assertEqual(si.initialData, [])
        self.assertEqual(si.totalCount, 0)

        try:
            si.serviceName
        except AttributeError:
            pass

        try:
            si.id
        except AttributeError:
            pass

        # basic create
        x = amf0.RecordSet(columns=['a', 'b', 'c'], items=[
            [1, 2, 3], [4, 5, 6], [7, 8, 9]])

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, ['a', 'b', 'c'])
        self.assertEqual(si.initialData, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(si.totalCount, 3)

        try:
            si.serviceName
        except AttributeError:
            pass

        try:
            si.id
        except AttributeError:
            pass

        # with service & id
        service = {'name': 'baz'}

        x = amf0.RecordSet(columns=['spam'], items=[['eggs']],
            service=service, id='asdfasdf')

        si = x.serverInfo

        self.assertTrue(isinstance(si, dict))
        self.assertEqual(si.cursor, 1)
        self.assertEqual(si.version, 1)
        self.assertEqual(si.columnNames, ['spam'])
        self.assertEqual(si.initialData, [['eggs']])
        self.assertEqual(si.totalCount, 1)
        self.assertEqual(si.serviceName, 'baz')
        self.assertEqual(si.id, 'asdfasdf')

    def test_encode(self):
        self.buf = self.encoder.stream

        x = amf0.RecordSet(columns=['a', 'b', 'c'], items=[
            [1, 2, 3], [4, 5, 6], [7, 8, 9]])

        self.assertEncoded(x, self.blob)

    def test_decode(self):
        self.buf = self.decoder.stream
        x = self.decode(self.blob)

        self.assertTrue(isinstance(x, amf0.RecordSet))
        self.assertEqual(x.columns, ['a', 'b', 'c'])
        self.assertEqual(x.items, [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        self.assertEqual(x.service, None)
        self.assertEqual(x.id, None)

    def test_repr(self):
        x = amf0.RecordSet(columns=['spam'], items=[['eggs']],
            service={'name': 'baz'}, id='asdfasdf')

        self.assertEqual(repr(x), "<pyamf.amf0.RecordSet id=asdfasdf "
            "service={'name': 'baz'} at 0x%x>" % (id(x),))


class ClassInheritanceTestCase(ClassCacheClearingTestCase, EncoderMixIn):

    amf_type = pyamf.AMF0

    def setUp(self):
        # wtf
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_simple(self):
        class A(object):
            class __amf__:
                static = ('a')


        class B(A):
            class __amf__:
                static = ('b')

        pyamf.register_class(A, 'A')
        pyamf.register_class(B, 'B')

        x = B()
        x.a = 'spam'
        x.b = 'eggs'

        self.assertEncoded(x, '\x10\x00\x01B', ('\x00\x01a\x02\x00\x04spam',
            '\x00\x01b\x02\x00\x04eggs'), '\x00\x00\t')

    def test_deep(self):
        class A(object):
            class __amf__:
                static = ('a')

        class B(A):
            class __amf__:
                static = ('b')

        class C(B):
            class __amf__:
                static = ('c')

        pyamf.register_class(A, 'A')
        pyamf.register_class(B, 'B')
        pyamf.register_class(C, 'C')

        x = C()
        x.a = 'spam'
        x.b = 'eggs'
        x.c = 'foo'

        self.assertEncoded(x, '\x10\x00\x01C', ('\x00\x01a\x02\x00\x04spam',
            '\x00\x01c\x02\x00\x03foo', '\x00\x01b\x02\x00\x04eggs'),
            '\x00\x00\t')


class ExceptionEncodingTestCase(ClassCacheClearingTestCase):
    """
    Tests for encoding exceptions.
    """

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)

        self.buffer = util.BufferedByteStream()
        self.encoder = amf0.Encoder(self.buffer)

    def test_exception(self):
        try:
            raise Exception('foo bar')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buffer.getvalue(), '\x03\x00\x07message\x02'
            '\x00\x07foo bar\x00\x04name\x02\x00\tException\x00\x00\t')

    def test_user_defined(self):
        class FooBar(Exception):
            pass

        try:
            raise FooBar('foo bar')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buffer.getvalue(), '\x03\x00\x07message\x02'
            '\x00\x07foo bar\x00\x04name\x02\x00\x06FooBar\x00\x00\t')

    def test_typed(self):
        class XYZ(Exception):
            pass

        pyamf.register_class(XYZ, 'foo.bar')

        try:
            raise XYZ('blarg')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buffer.getvalue(), '\x10\x00\x07foo.bar\x00'
            '\x07message\x02\x00\x05blarg\x00\x04name\x02\x00\x03XYZ\x00\x00\t')


class AMF0ContextTestCase(unittest.TestCase):
    """
    """

    bytes = ('\x00\x03\x00\x02\x00\x0eServiceLicense\x00\x00\x00\x00O\x11\n\x0b'
        '\x01-serviceConfigurationId\x06\t1234\x15licenseKey\x06Axxxxxxxxxxxxxx'
        'xxxxxxxxxxxxxxxxxx\x01\x00\tSessionId\x00\x00\x00\x00\xb2\x11\n\x0b'
        '\x01\x0bToken\x06\x82Iyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
        'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
        'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\x01\x00\x01\x00\x0cRegi'
        'sterUser\x00\x02/3\x00\x00\x01k\n\x00\x00\x00\x07\x11\n#\x01\rformat'
        '\x0bvalue\x069urn:TribalDDB:identity:email\x06!tester@trial.com\x11\n'
        '#\x01\x02\ttype\x06\x0fpasswrd\x06Kurn:TribalDDB:authentication:passwo'
        'rd\x11\nS\x01\x19EmailAddress\x15PostalCode\x17DateOfBirth\x11LastName'
        '\x13FirstName\x06\x06\x06\x0b12345\n3\x12\x0bmonth\x07day\tyear\x04'
        '\x04\x04\x0f\x04\x8fF\x06\rewrwer\x06\x07wer\x11\n3\x1fSectionTracking'
        '\tCsId\x11TrtmntId\x13LocalCsId\x04\x00\x04\x86\x94z\x04\x00\x11\n'
        '\x13\x11Tracking\x07CTC\x06\x07555\x11\t\x03\x01\n#\x13UserOptIn\x1dli'
        'veModeEnable\x05id\x02\x04\x884\x02\x00\x10wwwwwwwwwwwwwwww')

    def test_decode(self):
        from pyamf.remoting import decode

        e = decode(self.bytes)

        a, b, c, d, e, f, g = e['/3'].body

        self.assertEqual(a, {'value': u'tester@trial.com',
            'format': u'urn:TribalDDB:identity:email'})
        self.assertEqual(b, {'type': u'urn:TribalDDB:authentication:password',
            'value': u'passwrd'})
        self.assertEqual(c, {'PostalCode': u'12345',
            'DateOfBirth': {'month': 4, 'day': 15, 'year': 1990},
            'EmailAddress': u'tester@trial.com',
            'FirstName': u'wer',
            'LastName': u'ewrwer'})
        self.assertEqual(d, {'CsId': 0, 'TrtmntId': 100986, 'LocalCsId': 0})
        self.assertEqual(e, {'CTC': u'555'})
        self.assertEqual(f, [{'liveModeEnable': False, 'id': 1076}])
        self.assertEqual(g, u'wwwwwwwwwwwwwwww')

########NEW FILE########
__FILENAME__ = test_amf3
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF3 Implementation.

@since: 0.1.0
"""

import unittest
import datetime

import pyamf
from pyamf import amf3, util, xml, python
from pyamf.tests.util import (
    Spam, EncoderMixIn, DecoderMixIn, ClassCacheClearingTestCase)


class MockAlias(object):
    def __init__(self):
        self.get_attributes = []
        self.get_static_attrs = []
        self.apply_attrs = []

        self.static_attrs = {}
        self.attrs = ({}, {})
        self.create_instance = []
        self.expected_instance = object()

    def getStaticAttrs(self, *args, **kwargs):
        self.get_static_attrs.append([args, kwargs])

        return self.static_attrs

    def getAttributes(self, *args, **kwargs):
        self.get_attributes.append([args, kwargs])

        return self.attrs

    def createInstance(self, *args, **kwargs):
        self.create_instance.append([args, kwargs])

        return self.expected_instance

    def applyAttributes(self, *args, **kwargs):
        self.apply_attrs.append([args, kwargs])


class TypesTestCase(unittest.TestCase):
    """
    Tests the type mappings.
    """
    def test_types(self):
        self.assertEqual(amf3.TYPE_UNDEFINED, '\x00')
        self.assertEqual(amf3.TYPE_NULL, '\x01')
        self.assertEqual(amf3.TYPE_BOOL_FALSE, '\x02')
        self.assertEqual(amf3.TYPE_BOOL_TRUE, '\x03')
        self.assertEqual(amf3.TYPE_INTEGER, '\x04')
        self.assertEqual(amf3.TYPE_NUMBER, '\x05')
        self.assertEqual(amf3.TYPE_STRING, '\x06')
        self.assertEqual(amf3.TYPE_XML, '\x07')
        self.assertEqual(amf3.TYPE_DATE, '\x08')
        self.assertEqual(amf3.TYPE_ARRAY, '\x09')
        self.assertEqual(amf3.TYPE_OBJECT, '\x0a')
        self.assertEqual(amf3.TYPE_XMLSTRING, '\x0b')
        self.assertEqual(amf3.TYPE_BYTEARRAY, '\x0c')


class ContextTestCase(ClassCacheClearingTestCase):
    def test_create(self):
        c = amf3.Context()

        self.assertEqual(c.strings, [])
        self.assertEqual(c.classes, {})
        self.assertEqual(len(c.strings), 0)
        self.assertEqual(len(c.classes), 0)

    def test_add_string(self):
        x = amf3.Context()
        y = 'abc'

        self.assertEqual(x.addString(y), 0)
        self.assertTrue(y in x.strings)
        self.assertEqual(len(x.strings), 1)

        self.assertEqual(x.addString(''), -1)

        self.assertRaises(TypeError, x.addString, 132)

    def test_add_class(self):
        x = amf3.Context()

        alias = pyamf.register_class(Spam, 'spam.eggs')
        y = amf3.ClassDefinition(alias)

        self.assertEqual(x.addClass(y, Spam), 0)
        self.assertEqual(x.classes, {Spam: y})
        self.assertEqual(x.class_ref, {0: y})
        self.assertEqual(len(x.class_ref), 1)

    def test_clear(self):
        x = amf3.Context()
        y = [1, 2, 3]
        z = '<a></a>'

        x.addObject(y)
        x.addString('spameggs')
        x.clear()

        self.assertEqual(x.strings, [])
        self.assertEqual(len(x.strings), 0)
        self.assertFalse('spameggs' in x.strings)

    def test_get_by_reference(self):
        x = amf3.Context()
        y = [1, 2, 3]
        z = {'spam': 'eggs'}

        alias_spam = pyamf.register_class(Spam, 'spam.eggs')

        class Foo:
            pass

        class Bar:
            pass

        alias_foo = pyamf.register_class(Foo, 'foo.bar')

        a = amf3.ClassDefinition(alias_spam)
        b = amf3.ClassDefinition(alias_foo)

        x.addObject(y)
        x.addObject(z)
        x.addString('abc')
        x.addString('def')
        x.addClass(a, Foo)
        x.addClass(b, Bar)

        self.assertEqual(x.getObject(0), y)
        self.assertEqual(x.getObject(1), z)
        self.assertEqual(x.getObject(2), None)
        self.assertRaises(TypeError, x.getObject, '')
        self.assertRaises(TypeError, x.getObject, 2.2323)

        self.assertEqual(x.getString(0), 'abc')
        self.assertEqual(x.getString(1), 'def')
        self.assertEqual(x.getString(2), None)
        self.assertRaises(TypeError, x.getString, '')
        self.assertRaises(TypeError, x.getString, 2.2323)

        self.assertEqual(x.getClass(Foo), a)
        self.assertEqual(x.getClass(Bar), b)
        self.assertEqual(x.getClass(2), None)

        self.assertEqual(x.getClassByReference(0), a)
        self.assertEqual(x.getClassByReference(1), b)
        self.assertEqual(x.getClassByReference(2), None)

        self.assertEqual(x.getObject(2), None)
        self.assertEqual(x.getString(2), None)
        self.assertEqual(x.getClass(2), None)
        self.assertEqual(x.getClassByReference(2), None)

    def test_get_reference(self):
        x = amf3.Context()
        y = [1, 2, 3]
        z = {'spam': 'eggs'}

        spam_alias = pyamf.register_class(Spam, 'spam.eggs')

        class Foo:
            pass

        foo_alias = pyamf.register_class(Foo, 'foo.bar')

        a = amf3.ClassDefinition(spam_alias)
        b = amf3.ClassDefinition(foo_alias)

        ref1 = x.addObject(y)
        ref2 = x.addObject(z)
        x.addString('abc')
        x.addString('def')
        x.addClass(a, Spam)
        x.addClass(b, Foo)

        self.assertEqual(x.getObjectReference(y), ref1)
        self.assertEqual(x.getObjectReference(z), ref2)
        self.assertEqual(x.getObjectReference({}), -1)

        self.assertEqual(x.getStringReference('abc'), 0)
        self.assertEqual(x.getStringReference('def'), 1)
        self.assertEqual(x.getStringReference('asdfas'), -1)

        self.assertEqual(x.getClass(Spam), a)
        self.assertEqual(x.getClass(Foo), b)
        self.assertEqual(x.getClass(object()), None)


class ClassDefinitionTestCase(ClassCacheClearingTestCase):

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)

        self.alias = pyamf.ClassAlias(Spam, defer=True)

    def test_dynamic(self):
        self.assertFalse(self.alias.is_compiled())

        x = amf3.ClassDefinition(self.alias)

        self.assertTrue(x.alias is self.alias)
        self.assertEqual(x.encoding, 2)
        self.assertEqual(x.attr_len, 0)

        self.assertTrue(self.alias.is_compiled())

    def test_static(self):
        self.alias.static_attrs = ['foo', 'bar']
        self.alias.dynamic = False

        x = amf3.ClassDefinition(self.alias)

        self.assertTrue(x.alias is self.alias)
        self.assertEqual(x.encoding, 0)
        self.assertEqual(x.attr_len, 2)

    def test_mixed(self):
        self.alias.static_attrs = ['foo', 'bar']

        x = amf3.ClassDefinition(self.alias)

        self.assertTrue(x.alias is self.alias)
        self.assertEqual(x.encoding, 2)
        self.assertEqual(x.attr_len, 2)

    def test_external(self):
        self.alias.external = True

        x = amf3.ClassDefinition(self.alias)

        self.assertTrue(x.alias is self.alias)
        self.assertEqual(x.encoding, 1)
        self.assertEqual(x.attr_len, 0)


class EncoderTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    Tests the output from the AMF3 L{Encoder<pyamf.amf3.Encoder>} class.
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_list_references(self):
        y = [0, 1, 2, 3]

        self.assertEncoded(y, '\x09\x09\x01\x04\x00\x04\x01\x04\x02\x04\x03')
        self.assertEncoded(y, '\x09\x00', clear=False)
        self.assertEncoded(y, '\x09\x00', clear=False)

    def test_list_proxy_references(self):
        self.encoder.use_proxies = True
        y = [0, 1, 2, 3]

        self.assertEncoded(y, '\n\x07Cflex.messaging.io.ArrayCollection\t\t'
            '\x01\x04\x00\x04\x01\x04\x02\x04\x03')
        self.assertEncoded(y, '\n\x00', clear=False)
        self.assertEncoded(y, '\n\x00', clear=False)

    def test_dict(self):
        self.assertEncoded({'spam': 'eggs'}, '\n\x0b\x01\tspam\x06\teggs\x01')
        self.assertEncoded({'a': u'e', 'b': u'f', 'c': u'g', 'd': u'h'},
            '\n\x0b\x01', ('\x03c\x06\x03g', '\x03b\x06\x03f', '\x03a\x06\x03e',
            '\x03d\x06\x03h'), '\x01')
        self.assertEncoded({12: True, 42: "Testing"}, ('\n\x0b', (
            '\x01\x0542\x06\x0fTesting',
            '\x0512\x03\x01'
        )))

    def test_boolean(self):
        self.assertEncoded(True, '\x03')
        self.assertEncoded(False, '\x02')

    def test_mixed_array(self):
        x = pyamf.MixedArray()
        x.update({0:u'hello', 'spam': u'eggs'})

        self.assertEncoded(x, '\t\x03\tspam\x06\teggs\x01\x06\x0bhello')

        x = pyamf.MixedArray()
        x.update({0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 'a': 'a'})

        self.assertEncoded(x, '\x09\x0d\x03\x61\x06\x00\x01\x04\x00\x04\x01'
            '\x04\x02\x04\x03\x04\x04\x04\x05')

    def test_empty_key_string(self):
        """
        Test to see if there is an empty key in the C{dict}. There is a design
        bug in Flash 9 which means that it cannot read this specific data.

        @bug: See U{http://www.docuverse.com/blog/donpark/2007/05/14/flash-9-amf3-bug}
        for more info.
        """
        def x():
            y = pyamf.MixedArray()
            y.update({'': 1, 0: 1})
            self.encode(y)

        self.failUnlessRaises(pyamf.EncodeError, x)

    def test_object(self):
        self.assertEncoded({'a': u'spam', 'b': 5},
            '\n\x0b\x01\x03a\x06\tspam\x03b\x04\x05\x01')

        pyamf.register_class(Spam, 'org.pyamf.spam')

        obj = Spam()
        obj.baz = 'hello'

        self.assertEncoded(obj,
            '\n\x0b\x1dorg.pyamf.spam\x07baz\x06\x0bhello\x01')

    def test_date(self):
        x = datetime.datetime(2005, 3, 18, 1, 58, 31)

        self.assertEncoded(x, '\x08\x01Bp+6!\x15\x80\x00')
        self.assertEncoded(x, '\x08\x00', clear=False)

        self.assertRaises(pyamf.EncodeError, self.encode, datetime.time(22, 3))

    def test_byte_array(self):
        self.assertEncoded(amf3.ByteArray('hello'), '\x0c\x0bhello')

    def test_xmlstring(self):
        x = xml.fromstring('<a><b>hello world</b></a>')
        self.assertEqual(self.encode(x), '\x0b\x33<a><b>hello world</b></a>')
        self.assertEqual(self.encode(x), '\x0b\x00')

    def test_anonymous(self):
        pyamf.register_class(Spam)

        x = Spam({'spam': 'eggs'})

        self.assertEncoded(x, '\n\x0b\x01\x09spam\x06\x09eggs\x01')

    def test_custom_type(self):
        def write_as_list(list_interface_obj, encoder):
            list_interface_obj.ran = True
            self.assertEqual(id(self.encoder), id(encoder))

            return list(list_interface_obj)

        class ListWrapper(object):
            ran = False

            def __iter__(self):
                return iter([1, 2, 3])

        pyamf.add_type(ListWrapper, write_as_list)
        x = ListWrapper()

        self.assertEncoded(x, '\t\x07\x01\x04\x01\x04\x02\x04\x03')
        self.assertTrue(x.ran)

    def test_old_style_classes(self):
        class Person:
            pass

        pyamf.register_class(Person, 'spam.eggs.Person')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.assertEncoded(u, '\n\x0b!spam.eggs.Person', (
            '\x17family_name\x06\x07Doe', '\x15given_name\x06\tJane'), '\x01')

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.assertEncoded(u, '\n\x0b\x01', ('\x17family_name\x06\x07Doe',
            '\x15given_name\x06\tJane'), '\x01')

    def test_slots_registered(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        pyamf.register_class(Person, 'spam.eggs.Person')

        u = Person()
        u.family_name = 'Doe'
        u.given_name = 'Jane'

        self.assertEncoded(u, '\n\x0b!spam.eggs.Person', (
            '\x17family_name\x06\x07Doe', '\x15given_name\x06\tJane'), '\x01')

    def test_elementtree_tag(self):
        class NotAnElement(object):
            items = lambda self: []

            def __iter__(self):
                return iter([])

        foo = NotAnElement()
        foo.tag = 'foo'
        foo.text = 'bar'
        foo.tail = None

        self.assertEncoded(foo, '\n\x0b\x01', ('\ttext\x06\x07bar',
            '\ttail\x01', '\x07tag\x06\x07foo'), '\x01')

    def test_funcs(self):
        def x():
            pass

        for f in (chr, lambda x: x, x, pyamf, ''.startswith):
            self.assertRaises(pyamf.EncodeError, self.encode, f)

    def test_29b_ints(self):
        """
        Tests for ints that don't fit into 29bits. Reference: #519
        """
        ints = [
            (amf3.MIN_29B_INT - 1, '\x05\xc1\xb0\x00\x00\x01\x00\x00\x00'),
            (amf3.MAX_29B_INT + 1, '\x05A\xb0\x00\x00\x00\x00\x00\x00')
        ]

        for i, val in ints:
            self.buf.truncate()

            self.encoder.writeElement(i)
            self.assertEqual(self.buf.getvalue(), val)

    def test_number(self):
        vals = [
            (0,        '\x04\x00'),
            (0.2,      '\x05\x3f\xc9\x99\x99\x99\x99\x99\x9a'),
            (1,        '\x04\x01'),
            (127,      '\x04\x7f'),
            (128,      '\x04\x81\x00'),
            (0x3fff,   '\x04\xff\x7f'),
            (0x4000,   '\x04\x81\x80\x00'),
            (0x1FFFFF, '\x04\xff\xff\x7f'),
            (0x200000, '\x04\x80\xc0\x80\x00'),
            (0x3FFFFF, '\x04\x80\xff\xff\xff'),
            (0x400000, '\x04\x81\x80\x80\x00'),
            (-1,       '\x04\xff\xff\xff\xff'),
            (42,       '\x04\x2a'),
            (-123,     '\x04\xff\xff\xff\x85'),
            (amf3.MIN_29B_INT, '\x04\xc0\x80\x80\x00'),
            (amf3.MAX_29B_INT, '\x04\xbf\xff\xff\xff'),
            (1.23456789, '\x05\x3f\xf3\xc0\xca\x42\x83\xde\x1b')
        ]

        for i, val in vals:
            self.buf.truncate()

            self.encoder.writeElement(i)
            self.assertEqual(self.buf.getvalue(), val)

    def test_class(self):
        class New(object):
            pass

        class Classic:
            pass

        self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, Classic)
        self.assertRaises(pyamf.EncodeError, self.encoder.writeElement, New)

    def test_proxy(self):
        """
        Test to ensure that only C{dict} objects will be proxied correctly
        """
        self.encoder.use_proxies = True
        bytes = '\n\x07;flex.messaging.io.ObjectProxy\n\x0b\x01\x01'

        self.assertEncoded(pyamf.ASObject(), bytes)
        self.assertEncoded({}, bytes)

    def test_proxy_non_dict(self):
        class Foo(object):
            pass

        self.encoder.use_proxies = True
        bytes = '\n\x0b\x01\x01'

        self.assertEncoded(Foo(), bytes)

    def test_timezone(self):
        d = datetime.datetime(2009, 9, 24, 14, 23, 23)
        self.encoder.timezone_offset = datetime.timedelta(hours=-5)

        self.encoder.writeElement(d)

        self.assertEqual(self.buf.getvalue(), '\x08\x01Br>\xd8\x1f\xff\x80\x00')

    def test_generator(self):
        def foo():
            yield [1, 2, 3]
            yield u'\xff'
            yield pyamf.Undefined

        self.assertEncoded(foo(), '\t\x07\x01\x04\x01\x04\x02\x04\x03\x06\x05'
            '\xc3\xbf\x00')

    def test_iterate(self):
        self.assertRaises(StopIteration, self.encoder.next)

        self.encoder.send('')
        self.encoder.send('hello')
        self.encoder.send(u'ƒøø')

        self.assertEqual(self.encoder.next(), '\x06\x01')
        self.assertEqual(self.encoder.next(), '\x06\x0bhello')
        self.assertEqual(self.encoder.next(), '\x06\r\xc6\x92\xc3\xb8\xc3\xb8')

        self.assertRaises(StopIteration, self.encoder.next)

        self.assertIdentical(iter(self.encoder), self.encoder)
        self.assertEqual(self.buf.getvalue(),
            '\x06\x01\x06\x0bhello\x06\r\xc6\x92\xc3\xb8\xc3\xb8')


    def test_subclassed_tuple(self):
        """
        A subclassed tuple must encode an AMF list.

        @see: #830
        """
        class Foo(tuple):
            pass

        x = Foo([1,2])

        self.encoder.send(x)

        self.assertEqual(self.encoder.next(), '\t\x05\x01\x04\x01\x04\x02')


class DecoderTestCase(ClassCacheClearingTestCase, DecoderMixIn):
    """
    Tests the output from the AMF3 L{Decoder<pyamf.amf3.Decoder>} class.
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        DecoderMixIn.setUp(self)

    def test_undefined(self):
        self.assertDecoded(pyamf.Undefined, '\x00')

    def test_number(self):
        self.assertDecoded(0, '\x04\x00')
        self.assertDecoded(0.2, '\x05\x3f\xc9\x99\x99\x99\x99\x99\x9a')
        self.assertDecoded(1, '\x04\x01')
        self.assertDecoded(-1, '\x04\xff\xff\xff\xff')
        self.assertDecoded(42, '\x04\x2a')

        # two ways to represent -123, as an int and as a float
        self.assertDecoded(-123, '\x04\xff\xff\xff\x85')
        self.assertDecoded(-123, '\x05\xc0\x5e\xc0\x00\x00\x00\x00\x00')

        self.assertDecoded(1.23456789, '\x05\x3f\xf3\xc0\xca\x42\x83\xde\x1b')

    def test_integer(self):
        self.assertDecoded(0, '\x04\x00')
        self.assertDecoded(0x35, '\x04\x35')
        self.assertDecoded(0x7f, '\x04\x7f')
        self.assertDecoded(0x80, '\x04\x81\x00')
        self.assertDecoded(0xd4, '\x04\x81\x54')
        self.assertDecoded(0x3fff, '\x04\xff\x7f')
        self.assertDecoded(0x4000, '\x04\x81\x80\x00')
        self.assertDecoded(0x1a53f, '\x04\x86\xca\x3f')
        self.assertDecoded(0x1fffff, '\x04\xff\xff\x7f')
        self.assertDecoded(0x200000, '\x04\x80\xc0\x80\x00')
        self.assertDecoded(-0x01, '\x04\xff\xff\xff\xff')
        self.assertDecoded(-0x2a, '\x04\xff\xff\xff\xd6')
        self.assertDecoded(0xfffffff, '\x04\xbf\xff\xff\xff')
        self.assertDecoded(-0x10000000, '\x04\xc0\x80\x80\x00')

    def test_infinites(self):
        x = self.decode('\x05\xff\xf8\x00\x00\x00\x00\x00\x00')
        self.assertTrue(python.isNaN(x))

        x = self.decode('\x05\xff\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(python.isNegInf(x))

        x = self.decode('\x05\x7f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(python.isPosInf(x))

    def test_boolean(self):
        self.assertDecoded(True, '\x03')
        self.assertDecoded(False, '\x02')

    def test_null(self):
        self.assertDecoded(None, '\x01')

    def test_string(self):
        self.assertDecoded('', '\x06\x01')
        self.assertDecoded('hello', '\x06\x0bhello')
        self.assertDecoded(
            u'ღმერთსი შემვედრე, ნუთუ კვლა დამხსნას სოფლისა შრომასა, ცეცხლს',
            '\x06\x82\x45\xe1\x83\xa6\xe1\x83\x9b\xe1\x83\x94\xe1\x83\xa0'
            '\xe1\x83\x97\xe1\x83\xa1\xe1\x83\x98\x20\xe1\x83\xa8\xe1\x83'
            '\x94\xe1\x83\x9b\xe1\x83\x95\xe1\x83\x94\xe1\x83\x93\xe1\x83'
            '\xa0\xe1\x83\x94\x2c\x20\xe1\x83\x9c\xe1\x83\xa3\xe1\x83\x97'
            '\xe1\x83\xa3\x20\xe1\x83\x99\xe1\x83\x95\xe1\x83\x9a\xe1\x83'
            '\x90\x20\xe1\x83\x93\xe1\x83\x90\xe1\x83\x9b\xe1\x83\xae\xe1'
            '\x83\xa1\xe1\x83\x9c\xe1\x83\x90\xe1\x83\xa1\x20\xe1\x83\xa1'
            '\xe1\x83\x9d\xe1\x83\xa4\xe1\x83\x9a\xe1\x83\x98\xe1\x83\xa1'
            '\xe1\x83\x90\x20\xe1\x83\xa8\xe1\x83\xa0\xe1\x83\x9d\xe1\x83'
            '\x9b\xe1\x83\x90\xe1\x83\xa1\xe1\x83\x90\x2c\x20\xe1\x83\xaa'
            '\xe1\x83\x94\xe1\x83\xaa\xe1\x83\xae\xe1\x83\x9a\xe1\x83\xa1')

    def test_mixed_array(self):
        y = self.decode('\x09\x09\x03\x62\x06\x00\x03\x64\x06\x02\x03\x61'
            '\x06\x04\x03\x63\x06\x06\x01\x04\x00\x04\x01\x04\x02\x04\x03')

        self.assertTrue(isinstance(y,pyamf.MixedArray))
        self.assertEqual(y,
            {'a': u'a', 'b': u'b', 'c': u'c', 'd': u'd', 0: 0, 1: 1, 2: 2, 3: 3})

    def test_string_references(self):
        self.assertDecoded('hello', '\x06\x0bhello')
        self.assertDecoded('hello', '\x06\x00', clear=False)
        self.assertDecoded('hello', '\x06\x00', clear=False)

    def test_xmlstring(self):
        self.buf.write('\x0b\x33<a><b>hello world</b></a>')
        self.buf.seek(0, 0)
        x = self.decoder.readElement()

        self.assertEqual(xml.tostring(x), '<a><b>hello world</b></a>')

        self.buf.truncate()
        self.buf.write('\x0b\x00')
        self.buf.seek(0, 0)
        y = self.decoder.readElement()

        self.assertEqual(x, y)

    def test_xmlstring_references(self):
        self.buf.write('\x0b\x33<a><b>hello world</b></a>\x0b\x00')
        self.buf.seek(0, 0)
        x = self.decoder.readElement()
        y = self.decoder.readElement()

        self.assertEqual(id(x), id(y))

    def test_list(self):
        self.assertDecoded([], '\x09\x01\x01')
        self.assertDecoded([0, 1, 2, 3],
            '\x09\x09\x01\x04\x00\x04\x01\x04\x02\x04\x03')
        self.assertDecoded(["Hello", 2, 3, 4, 5], '\x09\x0b\x01\x06\x0b\x48'
            '\x65\x6c\x6c\x6f\x04\x02\x04\x03\x04\x04\x04\x05')

    def test_list_references(self):
        y = [0, 1, 2, 3]
        z = [0, 1, 2]

        self.assertDecoded(y, '\x09\x09\x01\x04\x00\x04\x01\x04\x02\x04\x03')
        self.assertDecoded(y, '\x09\x00', clear=False)
        self.assertDecoded(z, '\x09\x07\x01\x04\x00\x04\x01\x04\x02', clear=False)
        self.assertDecoded(z, '\x09\x02', clear=False)

    def test_dict(self):
        self.assertDecoded({'a': u'a', 'b': u'b', 'c': u'c', 'd': u'd'},
            '\n\x0b\x01\x03a\x06\x00\x03c\x06\x02\x03b\x06\x04\x03d\x06\x06\x01')

        self.assertDecoded({0: u'hello', 'foo': u'bar'}, '\x09\x03\x07\x66\x6f'
            '\x6f\x06\x07\x62\x61\x72\x01\x06\x0b\x68\x65\x6c\x6c\x6f')
        self.assertDecoded({0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 'a': 'a'},
            '\x09\x0d\x03\x61\x06\x00\x01\x04\x00\x04\x01\x04\x02\x04\x03\x04'
            '\x04\x04\x05')
        self.assertDecoded({'a': u'a', 'b': u'b', 'c': u'c', 'd': u'd',
            0: 0, 1: 1, 2: 2, 3: 3},
            '\x09\x09\x03\x62\x06\x00\x03\x64\x06\x02\x03\x61\x06\x04\x03\x63'
            '\x06\x06\x01\x04\x00\x04\x01\x04\x02\x04\x03')
        self.assertDecoded({'a': 1, 'b': 2}, '\x0a\x0b\x01\x03\x62\x04\x02\x03'
            '\x61\x04\x01\x01')
        self.assertDecoded({'baz': u'hello'}, '\x0a\x0b\x01\x07\x62\x61\x7a'
            '\x06\x0b\x68\x65\x6c\x6c\x6f\x01')
        self.assertDecoded({'baz': u'hello'}, '\x0a\x13\x01\x07\x62\x61\x7a'
            '\x06\x0b\x68\x65\x6c\x6c\x6f')

        bytes = '\x0a\x0b\x01\x07\x62\x61\x7a\x06\x0b\x68\x65\x6c\x6c\x6f\x01'

        self.buf.write(bytes)
        self.buf.seek(0)
        d = self.decoder.readElement()

    def test_object(self):
        pyamf.register_class(Spam, 'org.pyamf.spam')

        self.buf.truncate(0)
        self.buf.write(
            '\x0a\x13\x1dorg.pyamf.spam\x07baz\x06\x0b\x68\x65\x6c\x6c\x6f')
        self.buf.seek(0)

        obj = self.decoder.readElement()

        self.assertEqual(obj.__class__, Spam)

        self.failUnless(hasattr(obj, 'baz'))
        self.assertEqual(obj.baz, 'hello')

    def test_byte_array(self):
        self.assertDecoded(amf3.ByteArray('hello'), '\x0c\x0bhello')

    def test_date(self):
        import datetime

        self.assertDecoded(datetime.datetime(2005, 3, 18, 1, 58, 31),
            '\x08\x01Bp+6!\x15\x80\x00')

    def test_not_strict(self):
        self.assertFalse(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write('\n\x0b\x13spam.eggs\x07foo\x06\x07bar\x01')
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        obj = self.decoder.readElement()

        self.assertTrue(isinstance(obj, pyamf.TypedObject))
        self.assertEqual(obj.alias, 'spam.eggs')
        self.assertEqual(obj, {'foo': 'bar'})

    def test_strict(self):
        self.decoder.strict = True

        self.assertTrue(self.decoder.strict)

        # write a typed object to the stream
        self.buf.write('\n\x0b\x13spam.eggs\x07foo\x06\x07bar\x01')
        self.buf.seek(0)

        self.assertFalse('spam.eggs' in pyamf.CLASS_CACHE)

        self.assertRaises(pyamf.UnknownClassAlias, self.decoder.readElement)

    def test_slots(self):
        class Person(object):
            __slots__ = ('family_name', 'given_name')

        pyamf.register_class(Person, 'spam.eggs.Person')

        self.buf.write('\n+!spam.eggs.Person\x17family_name\x15given_name\x06'
            '\x07Doe\x06\tJane\x02\x06\x06\x04\x06\x08\x01')
        self.buf.seek(0)

        foo = self.decoder.readElement()

        self.assertTrue(isinstance(foo, Person))
        self.assertEqual(foo.family_name, 'Doe')
        self.assertEqual(foo.given_name, 'Jane')
        self.assertEqual(self.buf.remaining(), 0)

    def test_default_proxy_flag(self):
        amf3.use_proxies_default = True
        decoder = amf3.Decoder(self.buf, context=self.context)
        self.assertTrue(decoder.use_proxies)
        amf3.use_proxies_default = False
        decoder = amf3.Decoder(self.buf, context=self.context)
        self.assertFalse(decoder.use_proxies)

    def test_ioerror_buffer_position(self):
        """
        Test to ensure that if an IOError is raised by `readElement` that
        the original position of the stream is restored.
        """
        bytes = pyamf.encode(u'foo', [1, 2, 3], encoding=pyamf.AMF3).getvalue()

        self.buf.write(bytes[:-1])
        self.buf.seek(0)

        self.decoder.readElement()
        self.assertEqual(self.buf.tell(), 5)

        self.assertRaises(IOError, self.decoder.readElement)
        self.assertEqual(self.buf.tell(), 5)

    def test_timezone(self):
        self.decoder.timezone_offset = datetime.timedelta(hours=-5)

        self.buf.write('\x08\x01Br>\xc6\xf5w\x80\x00')
        self.buf.seek(0)

        f = self.decoder.readElement()

        self.assertEqual(f, datetime.datetime(2009, 9, 24, 9, 23, 23))

    def test_iterate(self):
        self.assertRaises(StopIteration, self.decoder.next)

        self.decoder.send('\x01')
        self.decoder.send('\x03')
        self.decoder.send('\x02')

        self.assertEqual(self.decoder.next(), None)
        self.assertEqual(self.decoder.next(), True)
        self.assertEqual(self.decoder.next(), False)

        self.assertRaises(StopIteration, self.decoder.next)

        self.assertIdentical(iter(self.decoder), self.decoder)

    def test_bad_type(self):
        self.assertRaises(pyamf.DecodeError, self.decode, '\xff')

    def test_kwargs(self):
        """
        Python <= 3 demand that kwargs keys be bytes instead of unicode/string.
        """
        def f(**kwargs):
            self.assertEqual(kwargs, {'spam': 'eggs'})

        kwargs = self.decode('\n\x0b\x01\tspam\x06\teggs\x01')

        f(**kwargs)


class ObjectEncodingTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_object_references(self):
        obj = pyamf.ASObject(a='b')

        self.encoder.writeElement(obj)
        pos = self.buf.tell()
        self.encoder.writeElement(obj)
        self.assertEqual(self.buf.getvalue()[pos:], '\x0a\x00')
        self.buf.truncate()

        self.encoder.writeElement(obj)
        self.assertEqual(self.buf.getvalue(), '\x0a\x00')
        self.buf.truncate()

    def test_class_references(self):
        alias = pyamf.register_class(Spam, 'abc.xyz')

        x = Spam({'spam': 'eggs'})
        y = Spam({'foo': 'bar'})

        self.encoder.writeElement(x)

        cd = self.context.getClass(Spam)

        self.assertTrue(cd.alias is alias)

        self.assertEqual(self.buf.getvalue(), '\n\x0b\x0fabc.xyz\tspam\x06\teggs\x01')

        pos = self.buf.tell()
        self.encoder.writeElement(y)
        self.assertEqual(self.buf.getvalue()[pos:], '\n\x01\x07foo\x06\x07bar\x01')

    def test_static(self):
        alias = pyamf.register_class(Spam, 'abc.xyz')

        alias.dynamic = False

        x = Spam({'spam': 'eggs'})
        self.encoder.writeElement(x)
        self.assertEqual(self.buf.getvalue(), '\n\x03\x0fabc.xyz')
        pyamf.unregister_class(Spam)
        self.buf.truncate()
        self.encoder.context.clear()

        alias = pyamf.register_class(Spam, 'abc.xyz')
        alias.dynamic = False
        alias.static_attrs = ['spam']

        x = Spam({'spam': 'eggs', 'foo': 'bar'})
        self.encoder.writeElement(x)
        self.assertEqual(self.buf.getvalue(), '\n\x13\x0fabc.xyz\tspam\x06\teggs')

    def test_dynamic(self):
        pyamf.register_class(Spam, 'abc.xyz')

        x = Spam({'spam': 'eggs'})
        self.encoder.writeElement(x)

        self.assertEqual(self.buf.getvalue(), '\n\x0b\x0fabc.xyz\tspam\x06\teggs\x01')

    def test_combined(self):
        alias = pyamf.register_class(Spam, 'abc.xyz')

        alias.static_attrs = ['spam']

        x = Spam({'spam': 'foo', 'eggs': 'bar'})
        self.encoder.writeElement(x)

        buf = self.buf.getvalue()

        self.assertEqual(buf, '\n\x1b\x0fabc.xyz\tspam\x06\x07foo\teggs\x06\x07bar\x01')

    def test_external(self):
        alias = pyamf.register_class(Spam, 'abc.xyz')

        alias.external = True

        x = Spam({'spam': 'eggs'})
        self.encoder.writeElement(x)

        buf = self.buf.getvalue()

        # an inline object with and inline class-def, encoding = 0x01, 1 attr

        self.assertEqual(buf[:2], '\x0a\x07')
        # class alias name
        self.assertEqual(buf[2:10], '\x0fabc.xyz')

        self.assertEqual(len(buf), 10)

    def test_anonymous_class_references(self):
        """
        Test to ensure anonymous class references with static attributes
        are encoded propertly
        """
        class Foo:
            class __amf__:
                static = ('name', 'id', 'description')

        x = Foo()
        x.id = 1
        x.name = 'foo'
        x.description = None

        y = Foo()
        y.id = 2
        y.name = 'bar'
        y.description = None

        self.encoder.writeElement([x, y])

        self.assertEqual(self.buf.getvalue(),
            '\t\x05\x01\n;\x01\tname\x05id\x17description\x06\x07foo\x04\x01'
            '\x01\x01\n\x01\x06\x07bar\x04\x02\x01\x01')


class ObjectDecodingTestCase(ClassCacheClearingTestCase, DecoderMixIn):
    """
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        DecoderMixIn.setUp(self)

    def test_object_references(self):
        self.buf.write('\x0a\x23\x01\x03a\x03b\x06\x09spam\x04\x05')
        self.buf.seek(0, 0)

        obj1 = self.decoder.readElement()

        self.buf.truncate()
        self.buf.write('\n\x00')
        self.buf.seek(0, 0)

        obj2 = self.decoder.readElement()

        self.assertEqual(id(obj1), id(obj2))

    def test_static(self):
        pyamf.register_class(Spam, 'abc.xyz')

        self.buf.write('\x0a\x13\x0fabc.xyz\x09spam\x06\x09eggs')
        self.buf.seek(0, 0)

        obj = self.decoder.readElement()

        class_def = self.context.getClass(Spam)

        self.assertEqual(class_def.static_properties, ['spam'])

        self.assertTrue(isinstance(obj, Spam))
        self.assertEqual(obj.__dict__, {'spam': 'eggs'})

    def test_dynamic(self):
        pyamf.register_class(Spam, 'abc.xyz')

        self.buf.write('\x0a\x0b\x0fabc.xyz\x09spam\x06\x09eggs\x01')
        self.buf.seek(0, 0)

        obj = self.decoder.readElement()

        class_def = self.context.getClass(Spam)

        self.assertEqual(class_def.static_properties, [])

        self.assertTrue(isinstance(obj, Spam))
        self.assertEqual(obj.__dict__, {'spam': 'eggs'})

    def test_combined(self):
        """
        This tests an object encoding with static properties and dynamic
        properties
        """
        pyamf.register_class(Spam, 'abc.xyz')

        self.buf.write(
            '\x0a\x1b\x0fabc.xyz\x09spam\x06\x09eggs\x07baz\x06\x07nat\x01')
        self.buf.seek(0, 0)

        obj = self.decoder.readElement()

        class_def = self.context.getClass(Spam)

        self.assertEqual(class_def.static_properties, ['spam'])

        self.assertTrue(isinstance(obj, Spam))
        self.assertEqual(obj.__dict__, {'spam': 'eggs', 'baz': 'nat'})

    def test_external(self):
        alias = pyamf.register_class(Spam, 'abc.xyz')
        alias.external = True

        self.buf.write('\x0a\x07\x0fabc.xyz')
        self.buf.seek(0)
        x = self.decoder.readElement()

        self.assertTrue(isinstance(x, Spam))
        self.assertEqual(x.__dict__, {})


class DataOutputTestCase(unittest.TestCase, EncoderMixIn):
    """
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        EncoderMixIn.setUp(self)

        self.x = amf3.DataOutput(self.encoder)

    def test_create(self):
        self.assertEqual(self.x.encoder, self.encoder)
        self.assertEqual(self.x.stream, self.buf)

    def test_boolean(self):
        self.x.writeBoolean(True)
        self.assertEqual(self.buf.getvalue(), '\x01')
        self.buf.truncate()

        self.x.writeBoolean(False)
        self.assertEqual(self.buf.getvalue(), '\x00')

    def test_byte(self):
        for y in xrange(10):
            self.x.writeByte(y)

        self.assertEqual(self.buf.getvalue(),
            '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')

    def test_double(self):
        self.x.writeDouble(0.0)
        self.assertEqual(self.buf.getvalue(), '\x00' * 8)
        self.buf.truncate()

        self.x.writeDouble(1234.5678)
        self.assertEqual(self.buf.getvalue(), '@\x93JEm\\\xfa\xad')

    def test_float(self):
        self.x.writeFloat(0.0)
        self.assertEqual(self.buf.getvalue(), '\x00' * 4)
        self.buf.truncate()

        self.x.writeFloat(1234.5678)
        self.assertEqual(self.buf.getvalue(), 'D\x9aR+')

    def test_int(self):
        self.x.writeInt(0)
        self.assertEqual(self.buf.getvalue(), '\x00\x00\x00\x00')
        self.buf.truncate()

        self.x.writeInt(-12345)
        self.assertEqual(self.buf.getvalue(), '\xff\xff\xcf\xc7')
        self.buf.truncate()

        self.x.writeInt(98)
        self.assertEqual(self.buf.getvalue(), '\x00\x00\x00b')

    def test_multi_byte(self):
        # TODO nick: test multiple charsets
        self.x.writeMultiByte('this is a test', 'utf-8')
        self.assertEqual(self.buf.getvalue(), u'this is a test')
        self.buf.truncate()

        self.x.writeMultiByte(u'ἔδωσαν', 'utf-8')
        self.assertEqual(self.buf.getvalue(), '\xe1\xbc\x94\xce\xb4\xcf'
            '\x89\xcf\x83\xce\xb1\xce\xbd')

    def test_object(self):
        obj = pyamf.MixedArray(spam='eggs')

        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(), '\t\x01\tspam\x06\teggs\x01')
        self.buf.truncate()

        # check references
        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(), '\t\x00')
        self.buf.truncate()

    def test_object_proxy(self):
        self.encoder.use_proxies = True
        obj = {'spam': 'eggs'}

        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(),
            '\n\x07;flex.messaging.io.ObjectProxy\n\x0b\x01\tspam\x06\teggs\x01')
        self.buf.truncate()

        # check references
        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(), '\n\x00')
        self.buf.truncate()

    def test_object_proxy_mixed_array(self):
        self.encoder.use_proxies = True
        obj = pyamf.MixedArray(spam='eggs')

        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(),
            '\n\x07;flex.messaging.io.ObjectProxy\n\x0b\x01\tspam\x06\teggs\x01')
        self.buf.truncate()

        # check references
        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(), '\n\x00')
        self.buf.truncate()

    def test_object_proxy_inside_list(self):
        self.encoder.use_proxies = True
        obj = [{'spam': 'eggs'}]

        self.x.writeObject(obj)
        self.assertEqual(self.buf.getvalue(),
            '\n\x07Cflex.messaging.io.ArrayCollection\t\x03\x01\n\x07;'
            'flex.messaging.io.ObjectProxy\n\x0b\x01\tspam\x06\teggs\x01')

    def test_short(self):
        self.x.writeShort(55)
        self.assertEqual(self.buf.getvalue(), '\x007')
        self.buf.truncate()

        self.x.writeShort(-55)
        self.assertEqual(self.buf.getvalue(), '\xff\xc9')

    def test_uint(self):
        self.x.writeUnsignedInt(55)
        self.assertEqual(self.buf.getvalue(), '\x00\x00\x007')
        self.buf.truncate()

        self.assertRaises(OverflowError, self.x.writeUnsignedInt, -55)

    def test_utf(self):
        self.x.writeUTF(u'ἔδωσαν')

        self.assertEqual(self.buf.getvalue(), '\x00\r\xe1\xbc\x94\xce'
            '\xb4\xcf\x89\xcf\x83\xce\xb1\xce\xbd')

    def test_utf_bytes(self):
        self.x.writeUTFBytes(u'ἔδωσαν')

        self.assertEqual(self.buf.getvalue(),
            '\xe1\xbc\x94\xce\xb4\xcf\x89\xcf\x83\xce\xb1\xce\xbd')


class DataInputTestCase(unittest.TestCase):
    def setUp(self):
        self.buf = util.BufferedByteStream()
        self.decoder = amf3.Decoder(self.buf)

    def test_create(self):
        x = amf3.DataInput(self.decoder)

        self.assertEqual(x.decoder, self.decoder)
        self.assertEqual(x.stream, self.buf)
        self.assertEqual(x.stream, self.decoder.stream)

    def _test(self, bytes, value, func, *params):
        self.buf.write(bytes)
        self.buf.seek(0)

        self.assertEqual(func(*params), value)
        self.buf.truncate()

    def test_boolean(self):
        x = amf3.DataInput(self.decoder)

        self.buf.write('\x01')
        self.buf.seek(-1, 2)
        self.assertEqual(x.readBoolean(), True)

        self.buf.write('\x00')
        self.buf.seek(-1, 2)
        self.assertEqual(x.readBoolean(), False)

    def test_byte(self):
        x = amf3.DataInput(self.decoder)

        self.buf.write('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')
        self.buf.seek(0)

        for y in xrange(10):
            self.assertEqual(x.readByte(), y)

    def test_double(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x00' * 8, 0.0, x.readDouble)
        self._test('@\x93JEm\\\xfa\xad', 1234.5678, x.readDouble)

    def test_float(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x00' * 4, 0.0, x.readFloat)
        self._test('?\x00\x00\x00', 0.5, x.readFloat)

    def test_int(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x00\x00\x00\x00', 0, x.readInt)
        self._test('\xff\xff\xcf\xc7', -12345, x.readInt)
        self._test('\x00\x00\x00b', 98, x.readInt)

    def test_multi_byte(self):
        # TODO nick: test multiple charsets
        x = amf3.DataInput(self.decoder)

        self._test('this is a test', 'this is a test', x.readMultiByte,
            14, 'utf-8')
        self._test('\xe1\xbc\x94\xce\xb4\xcf\x89\xcf\x83\xce\xb1\xce\xbd',
            u'ἔδωσαν', x.readMultiByte, 13, 'utf-8')

    def test_object(self):
        x = amf3.DataInput(self.decoder)

        self._test('\t\x01\x09spam\x06\x09eggs\x01', {'spam': 'eggs'}, x.readObject)
        # check references
        self._test('\t\x00', {'spam': 'eggs'}, x.readObject)

    def test_short(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x007', 55, x.readShort)
        self._test('\xff\xc9', -55, x.readShort)

    def test_uint(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x00\x00\x007', 55, x.readUnsignedInt)

    def test_utf(self):
        x = amf3.DataInput(self.decoder)

        self._test('\x00\x0bhello world', u'hello world', x.readUTF)
        self._test('\x00\r\xe1\xbc\x94\xce\xb4\xcf\x89\xcf\x83\xce\xb1\xce\xbd',
            u'ἔδωσαν', x.readUTF)

    def test_utf_bytes(self):
        x = amf3.DataInput(self.decoder)

        self._test('\xe1\xbc\x94\xce\xb4\xcf\x89\xcf\x83\xce\xb1\xce\xbd',
            u'ἔδωσαν', x.readUTFBytes, 13)


class ClassInheritanceTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_simple(self):
        class A(object):
            pass

        alias = pyamf.register_class(A, 'A')
        alias.static_attrs = ['a']

        class B(A):
            pass

        alias = pyamf.register_class(B, 'B')
        alias.static_attrs = ['b']

        x = B()
        x.a = 'spam'
        x.b = 'eggs'

        self.assertEncoded(x,
            '\n+\x03B\x03a\x03b\x06\tspam\x06\teggs\x01')

    def test_deep(self):
        class A(object):
            pass

        alias = pyamf.register_class(A, 'A')
        alias.static_attrs = ['a']

        class B(A):
            pass

        alias = pyamf.register_class(B, 'B')
        alias.static_attrs = ['b']

        class C(B):
            pass

        alias = pyamf.register_class(C, 'C')
        alias.static_attrs = ['c']

        x = C()
        x.a = 'spam'
        x.b = 'eggs'
        x.c = 'foo'

        self.assertEncoded(x,
            '\n;\x03C\x03b\x03a\x03c\x06\teggs\x06\tspam\x06\x07foo\x01')


class ComplexEncodingTestCase(unittest.TestCase, EncoderMixIn):
    """
    """

    amf_type = pyamf.AMF3

    class TestObject(object):
        def __init__(self):
            self.number = None
            self.test_list = ['test']
            self.sub_obj = None
            self.test_dict = {'test': 'ignore'}

        def __repr__(self):
            return '<TestObject %r @ 0x%x>' % (self.__dict__, id(self))

    class TestSubObject(object):
        def __init__(self):
            self.number = None

        def __repr__(self):
            return '<TestSubObject %r @ 0x%x>' % (self.__dict__, id(self))

    def setUp(self):
        EncoderMixIn.setUp(self)

        pyamf.register_class(self.TestObject, 'test_complex.test')
        pyamf.register_class(self.TestSubObject, 'test_complex.sub')

    def tearDown(self):
        EncoderMixIn.tearDown(self)

        pyamf.unregister_class(self.TestObject)
        pyamf.unregister_class(self.TestSubObject)

    def build_complex(self, max=5):
        test_objects = []

        for i in range(0, max):
            test_obj = self.TestObject()
            test_obj.number = i
            test_obj.sub_obj = self.TestSubObject()
            test_obj.sub_obj.number = i
            test_objects.append(test_obj)

        return test_objects

    def complex_test(self):
        to_cd = self.context.getClass(self.TestObject)
        tso_cd = self.context.getClass(self.TestSubObject)

        self.assertIdentical(to_cd.alias.klass, self.TestObject)
        self.assertIdentical(tso_cd.alias.klass, self.TestSubObject)

        self.assertEqual(self.context.getClassByReference(3), None)

    def complex_encode_decode_test(self, decoded):
        for obj in decoded:
            self.assertEqual(self.TestObject, obj.__class__)
            self.assertEqual(self.TestSubObject, obj.sub_obj.__class__)

    def test_complex_dict(self):
        complex = {'element': 'ignore', 'objects': self.build_complex()}

        self.encoder.writeElement(complex)
        self.complex_test()

    def test_complex_encode_decode_dict(self):
        complex = {'element': 'ignore', 'objects': self.build_complex()}
        self.encoder.writeElement(complex)
        encoded = self.encoder.stream.getvalue()

        context = amf3.Context()
        decoded = amf3.Decoder(encoded, context).readElement()

        self.complex_encode_decode_test(decoded['objects'])

    def test_class_refs(self):
        a = self.TestSubObject()
        b = self.TestSubObject()

        self.encoder.writeObject(a)

        cd = self.context.getClass(self.TestSubObject)

        self.assertIdentical(self.context.getClassByReference(0), cd)
        self.assertEqual(self.context.getClassByReference(1), None)

        self.encoder.writeElement({'foo': 'bar'})

        cd2 = self.context.getClass(dict)
        self.assertIdentical(self.context.getClassByReference(1), cd2)
        self.assertEqual(self.context.getClassByReference(2), None)

        self.encoder.writeElement({})

        self.assertIdentical(self.context.getClassByReference(0), cd)
        self.assertIdentical(self.context.getClassByReference(1), cd2)
        self.assertEqual(self.context.getClassByReference(2), None)

        self.encoder.writeElement(b)

        self.assertIdentical(self.context.getClassByReference(0), cd)
        self.assertIdentical(self.context.getClassByReference(1), cd2)
        self.assertEqual(self.context.getClassByReference(2), None)

        c = self.TestObject()

        self.encoder.writeElement(c)
        cd3 = self.context.getClass(self.TestObject)

        self.assertIdentical(self.context.getClassByReference(0), cd)
        self.assertIdentical(self.context.getClassByReference(1), cd2)
        self.assertIdentical(self.context.getClassByReference(2), cd3)


class ExceptionEncodingTestCase(ClassCacheClearingTestCase, EncoderMixIn):
    """
    Tests for encoding exceptions.
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_exception(self):
        try:
            raise Exception('foo bar')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buf.getvalue(), '\n\x0b\x01\x0fmessage\x06'
            '\x0ffoo bar\tname\x06\x13Exception\x01')

    def test_user_defined(self):
        class FooBar(Exception):
            pass

        try:
            raise FooBar('foo bar')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buf.getvalue(), '\n\x0b\x01\x0fmessage\x06'
            '\x0ffoo bar\tname\x06\rFooBar\x01')

    def test_typed(self):
        class XYZ(Exception):
            pass

        pyamf.register_class(XYZ, 'foo.bar')

        try:
            raise XYZ('blarg')
        except Exception, e:
            self.encoder.writeElement(e)

        self.assertEqual(self.buf.getvalue(), '\n\x0b\x0ffoo.bar\x0f'
            'message\x06\x0bblarg\tname\x06\x07XYZ\x01')


class ByteArrayTestCase(unittest.TestCase):
    """
    Tests for L{amf3.ByteArray}
    """

    def test_write_context(self):
        """
        @see: #695
        """
        obj = {'foo': 'bar'}
        b = amf3.ByteArray()

        b.writeObject(obj)

        bytes = b.getvalue()
        b.stream.truncate()

        b.writeObject(obj)
        self.assertEqual(b.getvalue(), bytes)

    def test_context(self):
        b = amf3.ByteArray()
        c = b.context

        obj = {'foo': 'bar'}

        c.addObject(obj)

        b.writeObject(obj)

        self.assertEqual(b.getvalue(), '\n\x0b\x01\x07foo\x06\x07bar\x01')

    def test_read_context(self):
        """
        @see: #695
        """
        obj = {'foo': 'bar'}
        b = amf3.ByteArray()

        b.stream.write('\n\x0b\x01\x07foo\x06\x07bar\x01\n\x00')
        b.stream.seek(0)

        self.assertEqual(obj, b.readObject())
        self.assertRaises(pyamf.ReferenceError, b.readObject)

    def test_compressed(self):
        """
        ByteArrays can be compressed. Test the C{compressed} attribute for
        validity.
        """
        try:
            import zlib
        except ImportError:
            self.skipTest('zlib is missing')

        ba = amf3.ByteArray()

        self.assertFalse(ba.compressed)

        z = zlib.compress('b' * 100)
        ba = amf3.ByteArray(z)

        self.assertTrue(ba.compressed)

        z = zlib.compress('\x00' * 100)
        ba = amf3.ByteArray(z)

        self.assertTrue(ba.compressed)

########NEW FILE########
__FILENAME__ = test_basic
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
General tests.

@since: 0.1.0
"""

import unittest
import new

import pyamf
from pyamf.tests.util import ClassCacheClearingTestCase, replace_dict, Spam


class ASObjectTestCase(unittest.TestCase):
    """
    I exercise all functionality relating to the L{ASObject<pyamf.ASObject>}
    class.
    """

    def test_init(self):
        bag = pyamf.ASObject(spam='eggs', baz='spam')

        self.assertEqual(bag, dict(spam='eggs', baz='spam'))
        self.assertEqual(bag.spam, 'eggs')
        self.assertEqual(bag.baz, 'spam')

    def test_eq(self):
        bag = pyamf.ASObject()

        self.assertEqual(bag, {})
        self.assertNotEquals(bag, {'spam': 'eggs'})

        bag2 = pyamf.ASObject()

        self.assertEqual(bag2, {})
        self.assertEqual(bag, bag2)
        self.assertNotEquals(bag, None)

    def test_setitem(self):
        bag = pyamf.ASObject()

        self.assertEqual(bag, {})

        bag['spam'] = 'eggs'

        self.assertEqual(bag.spam, 'eggs')

    def test_delitem(self):
        bag = pyamf.ASObject({'spam': 'eggs'})

        self.assertEqual(bag.spam, 'eggs')
        del bag['spam']

        self.assertRaises(AttributeError, lambda: bag.spam)

    def test_getitem(self):
        bag = pyamf.ASObject({'spam': 'eggs'})

        self.assertEqual(bag['spam'], 'eggs')

    def test_iter(self):
        bag = pyamf.ASObject({'spam': 'eggs'})

        x = []

        for k, v in bag.iteritems():
            x.append((k, v))

        self.assertEqual(x, [('spam', 'eggs')])

    def test_hash(self):
        bag = pyamf.ASObject({'spam': 'eggs'})

        self.assertNotEquals(None, hash(bag))


class HelperTestCase(unittest.TestCase):
    """
    Tests all helper functions in C{pyamf.__init__}
    """

    def setUp(self):
        self.default_encoding = pyamf.DEFAULT_ENCODING

    def tearDown(self):
        pyamf.DEFAULT_ENCODING = self.default_encoding

    def test_get_decoder(self):
        self.assertRaises(ValueError, pyamf.get_decoder, 'spam')

        decoder = pyamf.get_decoder(pyamf.AMF0, stream='123', strict=True)
        self.assertEqual(decoder.stream.getvalue(), '123')
        self.assertTrue(decoder.strict)

        decoder = pyamf.get_decoder(pyamf.AMF3, stream='456', strict=True)
        self.assertEqual(decoder.stream.getvalue(), '456')
        self.assertTrue(decoder.strict)

    def test_get_encoder(self):
        pyamf.get_encoder(pyamf.AMF0)
        pyamf.get_encoder(pyamf.AMF3)
        self.assertRaises(ValueError, pyamf.get_encoder, 'spam')

        encoder = pyamf.get_encoder(pyamf.AMF0, stream='spam')
        self.assertEqual(encoder.stream.getvalue(), 'spam')
        self.assertFalse(encoder.strict)

        encoder = pyamf.get_encoder(pyamf.AMF3, stream='eggs')
        self.assertFalse(encoder.strict)

        encoder = pyamf.get_encoder(pyamf.AMF0, strict=True)
        self.assertTrue(encoder.strict)

        encoder = pyamf.get_encoder(pyamf.AMF3, strict=True)
        self.assertTrue(encoder.strict)

    def test_encode(self):
        self.assertEqual('\x06\x0fconnect\x05?\xf0\x00\x00\x00\x00\x00\x00',
            pyamf.encode(u'connect', 1.0).getvalue())

    def test_decode(self):
        expected = [u'connect', 1.0]
        bytes = '\x06\x0fconnect\x05?\xf0\x00\x00\x00\x00\x00\x00'

        returned = [x for x in pyamf.decode(bytes)]

        self.assertEqual(expected, returned)

    def test_default_encoding(self):
        pyamf.DEFAULT_ENCODING = pyamf.AMF3

        x = pyamf.encode('foo').getvalue()

        self.assertEqual(x, '\x06\x07foo')

        pyamf.DEFAULT_ENCODING = pyamf.AMF0

        x = pyamf.encode('foo').getvalue()

        self.assertEqual(x, '\x02\x00\x03foo')


class UnregisterClassTestCase(ClassCacheClearingTestCase):
    def test_klass(self):
        alias = pyamf.register_class(Spam, 'spam.eggs')

        pyamf.unregister_class(Spam)
        self.assertTrue('spam.eggs' not in pyamf.CLASS_CACHE.keys())
        self.assertTrue(Spam not in pyamf.CLASS_CACHE.keys())
        self.assertTrue(alias not in pyamf.CLASS_CACHE)

    def test_alias(self):
        alias = pyamf.register_class(Spam, 'spam.eggs')

        pyamf.unregister_class('spam.eggs')
        self.assertTrue('spam.eggs' not in pyamf.CLASS_CACHE.keys())
        self.assertTrue(alias not in pyamf.CLASS_CACHE)


class ClassLoaderTestCase(ClassCacheClearingTestCase):
    def test_register(self):
        self.assertTrue(chr not in pyamf.CLASS_LOADERS)
        pyamf.register_class_loader(chr)
        self.assertTrue(chr in pyamf.CLASS_LOADERS)

    def test_bad_register(self):
        self.assertRaises(TypeError, pyamf.register_class_loader, 1)
        pyamf.register_class_loader(ord)

    def test_unregister(self):
        self.assertTrue(chr not in pyamf.CLASS_LOADERS)
        pyamf.register_class_loader(chr)
        self.assertTrue(chr in pyamf.CLASS_LOADERS)

        pyamf.unregister_class_loader(chr)
        self.assertTrue(chr not in pyamf.CLASS_LOADERS)

        self.assertRaises(LookupError, pyamf.unregister_class_loader, chr)

    def test_load_class(self):
        def class_loader(x):
            self.assertEqual(x, 'spam.eggs')

            return Spam

        pyamf.register_class_loader(class_loader)

        self.assertTrue('spam.eggs' not in pyamf.CLASS_CACHE.keys())
        pyamf.load_class('spam.eggs')
        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())

    def test_load_unknown_class(self):
        def class_loader(x):
            return None

        pyamf.register_class_loader(class_loader)

        self.assertRaises(pyamf.UnknownClassAlias, pyamf.load_class, 'spam.eggs')

    def test_load_class_by_alias(self):
        def class_loader(x):
            self.assertEqual(x, 'spam.eggs')
            return pyamf.ClassAlias(Spam, 'spam.eggs')

        pyamf.register_class_loader(class_loader)

        self.assertTrue('spam.eggs' not in pyamf.CLASS_CACHE.keys())
        pyamf.load_class('spam.eggs')
        self.assertTrue('spam.eggs' in pyamf.CLASS_CACHE.keys())

    def test_load_class_bad_return(self):
        def class_loader(x):
            return 'xyz'

        pyamf.register_class_loader(class_loader)

        self.assertRaises(TypeError, pyamf.load_class, 'spam.eggs')

    def test_load_class_by_module(self):
        pyamf.load_class('__builtin__.tuple')

    def test_load_class_by_module_bad(self):
        self.assertRaises(pyamf.UnknownClassAlias, pyamf.load_class,
            '__builtin__.tuple.')


class TypeMapTestCase(unittest.TestCase):
    def setUp(self):
        self.tm = pyamf.TYPE_MAP.copy()

        self.addCleanup(replace_dict, self.tm, pyamf.TYPE_MAP)

    def test_add_invalid(self):
        mod = new.module('spam')
        self.assertRaises(TypeError, pyamf.add_type, mod)
        self.assertRaises(TypeError, pyamf.add_type, {})
        self.assertRaises(TypeError, pyamf.add_type, 'spam')
        self.assertRaises(TypeError, pyamf.add_type, u'eggs')
        self.assertRaises(TypeError, pyamf.add_type, 1)
        self.assertRaises(TypeError, pyamf.add_type, 234234L)
        self.assertRaises(TypeError, pyamf.add_type, 34.23)
        self.assertRaises(TypeError, pyamf.add_type, None)
        self.assertRaises(TypeError, pyamf.add_type, object())

        class A:
            pass

        self.assertRaises(TypeError, pyamf.add_type, A())

    def test_add_same(self):
        pyamf.add_type(chr)
        self.assertRaises(KeyError, pyamf.add_type, chr)

    def test_add_class(self):
        class A:
            pass

        class B(object):
            pass

        pyamf.add_type(A)
        self.assertTrue(A in pyamf.TYPE_MAP)

        pyamf.add_type(B)
        self.assertTrue(B in pyamf.TYPE_MAP)

    def test_add_callable(self):
        td = pyamf.add_type(ord)

        self.assertTrue(ord in pyamf.TYPE_MAP)
        self.assertTrue(td in pyamf.TYPE_MAP.values())

    def test_add_multiple(self):
        td = pyamf.add_type((chr,))

        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        td = pyamf.add_type([A, B, C])
        self.assertEqual(td, pyamf.get_type([A, B, C]))

    def test_get_type(self):
        self.assertRaises(KeyError, pyamf.get_type, chr)
        td = pyamf.add_type((chr,))
        self.assertRaises(KeyError, pyamf.get_type, chr)

        td2 = pyamf.get_type((chr,))
        self.assertEqual(td, td2)

        td2 = pyamf.get_type([chr,])
        self.assertEqual(td, td2)

    def test_remove(self):
        self.assertRaises(KeyError, pyamf.remove_type, chr)
        td = pyamf.add_type((chr,))

        self.assertRaises(KeyError, pyamf.remove_type, chr)
        td2 = pyamf.remove_type((chr,))

        self.assertEqual(td, td2)


class ErrorClassMapTestCase(unittest.TestCase):
    """
    I test all functionality related to manipulating L{pyamf.ERROR_CLASS_MAP}
    """

    def setUp(self):
        self.map_copy = pyamf.ERROR_CLASS_MAP.copy()
        self.addCleanup(replace_dict, self.map_copy, pyamf.ERROR_CLASS_MAP)

    def test_add(self):
        class A:
            pass

        class B(Exception):
            pass

        self.assertRaises(TypeError, pyamf.add_error_class, None, 'a')

        # class A does not sub-class Exception
        self.assertRaises(TypeError, pyamf.add_error_class, A, 'a')

        pyamf.add_error_class(B, 'b')
        self.assertEqual(pyamf.ERROR_CLASS_MAP['b'], B)

        pyamf.add_error_class(B, 'a')
        self.assertEqual(pyamf.ERROR_CLASS_MAP['a'], B)

        class C(Exception):
            pass

        self.assertRaises(ValueError, pyamf.add_error_class, C, 'b')

    def test_remove(self):
        class B(Exception):
            pass

        pyamf.ERROR_CLASS_MAP['abc'] = B

        self.assertRaises(TypeError, pyamf.remove_error_class, None)

        pyamf.remove_error_class('abc')
        self.assertFalse('abc' in pyamf.ERROR_CLASS_MAP.keys())
        self.assertRaises(KeyError, pyamf.ERROR_CLASS_MAP.__getitem__, 'abc')

        pyamf.ERROR_CLASS_MAP['abc'] = B

        pyamf.remove_error_class(B)

        self.assertRaises(KeyError, pyamf.ERROR_CLASS_MAP.__getitem__, 'abc')
        self.assertRaises(ValueError, pyamf.remove_error_class, B)
        self.assertRaises(ValueError, pyamf.remove_error_class, 'abc')


class DummyAlias(pyamf.ClassAlias):
    pass


class RegisterAliasTypeTestCase(unittest.TestCase):
    def setUp(self):
        self.old_aliases = pyamf.ALIAS_TYPES.copy()
        self.addCleanup(replace_dict, self.old_aliases, pyamf.ALIAS_TYPES)

    def test_bad_klass(self):
        self.assertRaises(TypeError, pyamf.register_alias_type, 1)

    def test_subclass(self):
        self.assertFalse(issubclass(self.__class__, pyamf.ClassAlias))
        self.assertRaises(ValueError, pyamf.register_alias_type, self.__class__)

    def test_no_args(self):
        self.assertTrue(issubclass(DummyAlias, pyamf.ClassAlias))
        self.assertRaises(ValueError, pyamf.register_alias_type, DummyAlias)

    def test_type_args(self):
        self.assertTrue(issubclass(DummyAlias, pyamf.ClassAlias))
        self.assertRaises(TypeError, pyamf.register_alias_type, DummyAlias, 1)

    def test_single(self):
        class A(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertTrue(DummyAlias in pyamf.ALIAS_TYPES.keys())
        self.assertEqual(pyamf.ALIAS_TYPES[DummyAlias], (A,))

    def test_multiple(self):
        class A(object):
            pass

        class B(object):
            pass

        self.assertRaises(TypeError, pyamf.register_alias_type, DummyAlias, A, 'hello')

        pyamf.register_alias_type(DummyAlias, A, B)
        self.assertTrue(DummyAlias in pyamf.ALIAS_TYPES)
        self.assertEqual(pyamf.ALIAS_TYPES[DummyAlias], (A, B))

    def test_duplicate(self):
        class A(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertRaises(RuntimeError, pyamf.register_alias_type, DummyAlias, A)

    def test_unregister(self):
        """
        Tests for L{pyamf.unregister_alias_type}
        """
        class A(object):
            pass

        self.assertFalse(DummyAlias in pyamf.ALIAS_TYPES)
        self.assertEqual(pyamf.unregister_alias_type(A), None)

        pyamf.register_alias_type(DummyAlias, A)

        self.assertTrue(DummyAlias in pyamf.ALIAS_TYPES.keys())
        self.assertEqual(pyamf.unregister_alias_type(DummyAlias), (A,))


class TypedObjectTestCase(unittest.TestCase):
    def test_externalised(self):
        o = pyamf.TypedObject(None)

        self.assertRaises(pyamf.DecodeError, o.__readamf__, None)
        self.assertRaises(pyamf.EncodeError, o.__writeamf__, None)

    def test_alias(self):
        class Foo:
            pass

        alias = pyamf.TypedObjectClassAlias(Foo, 'bar')

        self.assertEqual(alias.klass, pyamf.TypedObject)
        self.assertNotEqual(alias.klass, Foo)


class PackageTestCase(ClassCacheClearingTestCase):
    """
    Tests for L{pyamf.register_package}
    """

    class NewType(object):
        pass

    class ClassicType:
        pass

    def setUp(self):
        ClassCacheClearingTestCase.setUp(self)

        self.module = new.module('foo')

        self.module.Classic = self.ClassicType
        self.module.New = self.NewType
        self.module.s = 'str'
        self.module.i = 12323
        self.module.f = 345.234
        self.module.u = u'unicode'
        self.module.l = ['list', 'of', 'junk']
        self.module.d = {'foo': 'bar', 'baz': 'gak'}
        self.module.obj = object()
        self.module.mod = self.module
        self.module.lam = lambda _: None

        self.NewType.__module__ = 'foo'
        self.ClassicType.__module__ = 'foo'

        self.spam_module = Spam.__module__
        Spam.__module__ = 'foo'

        self.names = (self.module.__name__,)

    def tearDown(self):
        ClassCacheClearingTestCase.tearDown(self)

        Spam.__module__ = self.spam_module

        self.module.__name__ = self.names

    def check_module(self, r, base_package):
        self.assertEqual(len(r), 2)

        for c in [self.NewType, self.ClassicType]:
            alias = r[c]

            self.assertTrue(isinstance(alias, pyamf.ClassAlias))
            self.assertEqual(alias.klass, c)
            self.assertEqual(alias.alias, base_package + c.__name__)

    def test_module(self):
        r = pyamf.register_package(self.module, 'com.example')
        self.check_module(r, 'com.example.')

    def test_all(self):
        self.module.Spam = Spam

        self.module.__all__ = ['Classic', 'New']

        r = pyamf.register_package(self.module, 'com.example')
        self.check_module(r, 'com.example.')

    def test_ignore(self):
        self.module.Spam = Spam

        r = pyamf.register_package(self.module, 'com.example', ignore=['Spam'])
        self.check_module(r, 'com.example.')

    def test_separator(self):
        r = pyamf.register_package(self.module, 'com.example', separator='/')

        self.ClassicType.__module__ = 'com.example'
        self.NewType.__module__ = 'com.example'
        self.check_module(r, 'com.example/')

    def test_name(self):
        self.module.__name__ = 'spam.eggs'
        self.ClassicType.__module__ = 'spam.eggs'
        self.NewType.__module__ = 'spam.eggs'

        r = pyamf.register_package(self.module)
        self.check_module(r, 'spam.eggs.')

    def test_dict(self):
        """
        @see: #585
        """
        d = dict()
        d['Spam'] = Spam

        r = pyamf.register_package(d, 'com.example', strict=False)

        self.assertEqual(len(r), 1)

        alias = r[Spam]

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertEqual(alias.klass, Spam)
        self.assertEqual(alias.alias, 'com.example.Spam')

    def test_odd(self):
        self.assertRaises(TypeError, pyamf.register_package, object())
        self.assertRaises(TypeError, pyamf.register_package, 1)
        self.assertRaises(TypeError, pyamf.register_package, 1.2)
        self.assertRaises(TypeError, pyamf.register_package, 23897492834L)
        self.assertRaises(TypeError, pyamf.register_package, [])
        self.assertRaises(TypeError, pyamf.register_package, '')
        self.assertRaises(TypeError, pyamf.register_package, u'')

    def test_strict(self):
        self.module.Spam = Spam

        Spam.__module__ = self.spam_module

        r = pyamf.register_package(self.module, 'com.example', strict=True)
        self.check_module(r, 'com.example.')

    def test_not_strict(self):
        self.module.Spam = Spam

        Spam.__module__ = self.spam_module

        r = pyamf.register_package(self.module, 'com.example', strict=False)

        self.assertEqual(len(r), 3)

        for c in [self.NewType, self.ClassicType, Spam]:
            alias = r[c]

            self.assertTrue(isinstance(alias, pyamf.ClassAlias))
            self.assertEqual(alias.klass, c)
            self.assertEqual(alias.alias, 'com.example.' + c.__name__)

    def test_list(self):
        class Foo:
            pass

        class Bar:
            pass

        ret = pyamf.register_package([Foo, Bar], 'spam.eggs')

        self.assertEqual(len(ret), 2)

        for c in [Foo, Bar]:
            alias = ret[c]

            self.assertTrue(isinstance(alias, pyamf.ClassAlias))
            self.assertEqual(alias.klass, c)
            self.assertEqual(alias.alias, 'spam.eggs.' + c.__name__)


class UndefinedTestCase(unittest.TestCase):
    """
    Tests for L{pyamf.Undefined}
    """

    def test_none(self):
        """
        L{pyamf.Undefined} is not referentially identical to C{None}.
        """
        self.assertFalse(pyamf.Undefined is None)

    def test_non_zero(self):
        """
        Truth test for L{pyamf.Undefined} == C{False}.
        """
        self.assertFalse(pyamf.Undefined)

########NEW FILE########
__FILENAME__ = test_codec
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF utilities.

@since: 0.1.0
"""

import unittest

import pyamf
from pyamf import codec

try:
    unicode
except NameError:
    # py3k
    unicode = str
    str = bytes


class TestObject(object):
    def __init__(self):
        self.name = 'test'


class DummyAlias(pyamf.ClassAlias):
    pass


class IndexedCollectionTestCase(unittest.TestCase):
    """
    Tests for L{codec.IndexedCollection}
    """

    def setUp(self):
        self.collection = codec.IndexedCollection()

    def test_clear(self):
        o = object()

        self.assertEqual(self.collection.getReferenceTo(o), -1)

        self.collection.append(o)
        self.assertEqual(self.collection.getReferenceTo(o), 0)

        self.collection.clear()

        self.assertEqual(self.collection.getReferenceTo(o), -1)

    def test_append(self):
        n = 5

        for i in range(0, n):
            test_obj = TestObject()

            test_obj.name = i

            self.collection.append(test_obj)

        self.assertEqual(len(self.collection), n)

        for i in range(0, n):
            self.assertEqual(i, self.collection[i].name)

    def test_get_reference_to(self):
        test_obj = TestObject()

        self.collection.append(test_obj)

        idx = self.collection.getReferenceTo(test_obj)

        self.assertEqual(0, idx)
        self.assertEqual(-1, self.collection.getReferenceTo(TestObject()))

    def test_get_by_reference(self):
        test_obj = TestObject()
        idx = self.collection.append(test_obj)

        self.assertIdentical(test_obj, self.collection.getByReference(idx))

        idx = self.collection.getReferenceTo(test_obj)

        self.assertIdentical(test_obj, self.collection.getByReference(idx))
        self.assertRaises(TypeError, self.collection.getByReference, 'bad ref')

        self.assertEqual(None, self.collection.getByReference(74))

    def test_len(self):
        self.assertEqual(0, len(self.collection))

        self.collection.append([])

        self.assertEqual(1, len(self.collection))

        self.collection.append({})

        self.assertEqual(2, len(self.collection))

        self.collection.clear()
        self.assertEqual(0, len(self.collection))

    def test_repr(self):
        x = "0x%x" % id(self.collection)

        self.assertEqual(repr(self.collection),
            '<pyamf.codec.IndexedCollection size=0 %s>' % (x,))

    def test_contains(self):
        o = object()

        self.assertFalse(o in self.collection)

        self.collection.append(o)

        self.assertTrue(o in self.collection)

    def test_eq(self):
        self.assertEqual(self.collection, [])
        self.assertRaises(NotImplementedError, self.collection.__eq__, self)

    def test_hash(self):
        class A(object):
            def __hash__(self):
                return 1

        self.collection = codec.IndexedCollection(True)

        o = A()

        self.assertEqual(self.collection.getReferenceTo(o), -1)

        self.collection.append(o)
        self.assertEqual(self.collection.getReferenceTo(o), 0)

        self.collection.clear()

        self.assertEqual(self.collection.getReferenceTo(o), -1)


class ContextTestCase(unittest.TestCase):
    """
    Tests for L{codec.Context}
    """

    def setUp(self):
        self.context = codec.Context()

    def test_add(self):
        y = [1, 2, 3]

        self.assertEqual(self.context.getObjectReference(y), -1)
        self.assertEqual(self.context.addObject(y), 0)
        self.assertEqual(self.context.getObjectReference(y), 0)

    def test_clear(self):
        y = [1, 2, 3]

        self.context.addObject(y)

        self.assertEqual(self.context.getObjectReference(y), 0)

        self.context.clear()

        self.assertEqual(self.context.getObjectReference(y), -1)

    def test_get_by_reference(self):
        y = [1, 2, 3]
        z = {'spam': 'eggs'}

        self.context.addObject(y)
        self.context.addObject(z)

        self.assertIdentical(self.context.getObject(0), y)
        self.assertIdentical(self.context.getObject(1), z)
        self.assertIdentical(self.context.getObject(2), None)

        for t in ['', 2.2323]:
            self.assertRaises(TypeError, self.context.getObject, t)

    def test_get_reference(self):
        y = [1, 2, 3]
        z = {'spam': 'eggs'}

        ref1 = self.context.addObject(y)
        ref2 = self.context.addObject(z)

        self.assertIdentical(self.context.getObjectReference(y), ref1)
        self.assertIdentical(self.context.getObjectReference(z), ref2)
        self.assertEqual(self.context.getObjectReference({}), -1)

    def test_no_alias(self):
        class A:
            pass

        alias = self.context.getClassAlias(A)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertIdentical(alias.klass, A)

    def test_registered_alias(self):
        class A:
            pass

        pyamf.register_class(A)
        self.addCleanup(pyamf.unregister_class, A)

        alias = self.context.getClassAlias(A)

        self.assertTrue(isinstance(alias, pyamf.ClassAlias))
        self.assertIdentical(alias.klass, A)

    def test_registered_deep(self):
        class A:
            pass

        class B(A):
            pass

        pyamf.register_alias_type(DummyAlias, A)
        self.addCleanup(pyamf.unregister_alias_type, DummyAlias)
        alias = self.context.getClassAlias(B)

        self.assertTrue(isinstance(alias, DummyAlias))
        self.assertIdentical(alias.klass, B)

    def test_get_class_alias(self):
        class A:
            pass

        alias1 = self.context.getClassAlias(A)
        alias2 = self.context.getClassAlias(A)

        self.assertIdentical(alias1, alias2)

    def test_string(self):
        s = 'foo'.encode('ascii')
        u = self.context.getStringForBytes(s)

        self.assertTrue(type(u) is unicode)
        self.assertEqual(u, s.decode('ascii'))

        i = self.context.getStringForBytes(s)

        self.assertIdentical(u, i)

        self.context.clear()

        i = self.context.getStringForBytes(s)

        self.assertFalse(u is i)

    def test_bytes(self):
        s = 'foo'.decode('ascii')

        b = self.context.getBytesForString(s)

        self.assertTrue(type(b) is str)
        self.assertEqual(b, s.encode('ascii'))

        i = self.context.getBytesForString(s)

        self.assertIdentical(i, b)

        self.context.clear()

        i = self.context.getBytesForString(s)

        self.assertNotIdentical(i, s)

########NEW FILE########
__FILENAME__ = test_flex
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Flex compatibility tests.

@since: 0.1.0
"""

import unittest

import pyamf
from pyamf import flex, util, amf3, amf0
from pyamf.tests.util import EncoderMixIn


class ArrayCollectionTestCase(unittest.TestCase, EncoderMixIn):
    """
    Tests for L{flex.ArrayCollection}
    """

    amf_type = pyamf.AMF3

    def setUp(self):
        unittest.TestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_create(self):
        self.assertEqual(flex.ArrayCollection(), [])
        self.assertEqual(flex.ArrayCollection([1, 2, 3]), [1, 2, 3])
        self.assertEqual(flex.ArrayCollection(('a', 'b', 'b')), ['a', 'b', 'b'])

        class X(object):
            def __iter__(self):
                return iter(['foo', 'bar', 'baz'])

        self.assertEqual(flex.ArrayCollection(X()), ['foo', 'bar', 'baz'])

        self.assertRaises(TypeError, flex.ArrayCollection,
            {'first': 'Matt', 'last': 'Matthews'})

    def test_encode_amf3(self):
        x = flex.ArrayCollection()
        x.append('eggs')

        self.assertEncoded(x,
            '\n\x07Cflex.messaging.io.ArrayCollection\t\x03\x01\x06\teggs')

    def test_encode_amf0(self):
        self.encoder = pyamf.get_encoder(pyamf.AMF0)
        self.buf = self.encoder.stream

        x = flex.ArrayCollection()
        x.append('eggs')

        self.assertEncoded(x,
            '\x11\n\x07Cflex.messaging.io.ArrayCollection\t\x03\x01\x06\teggs')

    def test_decode_amf3(self):
        stream = util.BufferedByteStream(
            '\n\x07Cflex.messaging.io.ArrayCollection\t\x03\x01\x06\teggs')
        decoder = amf3.Decoder(stream)
        x = decoder.readElement()

        self.assertEqual(x.__class__, flex.ArrayCollection)
        self.assertEqual(x, ['eggs'])

    def test_decode_proxy(self):
        stream = util.BufferedByteStream(
            '\x0a\x07;flex.messaging.io.ObjectProxy\x09\x01\x03a\x06\x09spam'
            '\x03b\x04\x05\x01')
        decoder = amf3.Decoder(stream)
        decoder.use_proxies = True

        x = decoder.readElement()

        self.assertEqual(x.__class__, pyamf.MixedArray)
        self.assertEqual(x, {'a': 'spam', 'b': 5})

    def test_decode_amf0(self):
        stream = util.BufferedByteStream(
            '\x11\n\x07Cflex.messaging.io.ArrayCollection\t\x03\x01\x06\teggs')
        decoder = amf0.Decoder(stream)
        x = decoder.readElement()

        self.assertEqual(x.__class__, flex.ArrayCollection)
        self.assertEqual(x, ['eggs'])

    def test_source_attr(self):
        s = ('\n\x07Cflex.messaging.io.ArrayCollection\n\x0b\x01\rsource'
            '\t\x05\x01\x06\x07foo\x06\x07bar\x01')

        x = pyamf.decode(s, encoding=pyamf.AMF3).next()

        self.assertTrue(isinstance(x, flex.ArrayCollection))
        self.assertEqual(x, ['foo', 'bar'])

    def test_readonly_length_property(self):
        a = flex.ArrayCollection()

        self.assertRaises(AttributeError, setattr, a, 'length', 3)


class ArrayCollectionAPITestCase(unittest.TestCase):
    def test_addItem(self):
        a = flex.ArrayCollection()
        self.assertEqual(a, [])
        self.assertEqual(a.length, 0)

        a.addItem('hi')
        self.assertEqual(a, ['hi'])
        self.assertEqual(a.length, 1)

    def test_addItemAt(self):
        a = flex.ArrayCollection()
        self.assertEqual(a, [])

        self.assertRaises(IndexError, a.addItemAt, 'foo', -1)
        self.assertRaises(IndexError, a.addItemAt, 'foo', 1)

        a.addItemAt('foo', 0)
        self.assertEqual(a, ['foo'])
        a.addItemAt('bar', 0)
        self.assertEqual(a, ['bar', 'foo'])
        self.assertEqual(a.length, 2)

    def test_getItemAt(self):
        a = flex.ArrayCollection(['a', 'b', 'c'])

        self.assertEqual(a.getItemAt(0), 'a')
        self.assertEqual(a.getItemAt(1), 'b')
        self.assertEqual(a.getItemAt(2), 'c')

        self.assertRaises(IndexError, a.getItemAt, -1)
        self.assertRaises(IndexError, a.getItemAt, 3)

    def test_getItemIndex(self):
        a = flex.ArrayCollection(['a', 'b', 'c'])

        self.assertEqual(a.getItemIndex('a'), 0)
        self.assertEqual(a.getItemIndex('b'), 1)
        self.assertEqual(a.getItemIndex('c'), 2)
        self.assertEqual(a.getItemIndex('d'), -1)

    def test_removeAll(self):
        a = flex.ArrayCollection(['a', 'b', 'c'])
        self.assertEqual(a.length, 3)

        a.removeAll()

        self.assertEqual(a, [])
        self.assertEqual(a.length, 0)

    def test_removeItemAt(self):
        a = flex.ArrayCollection(['a', 'b', 'c'])

        self.assertRaises(IndexError, a.removeItemAt, -1)
        self.assertRaises(IndexError, a.removeItemAt, 3)

        self.assertEqual(a.removeItemAt(1), 'b')
        self.assertEqual(a, ['a', 'c'])
        self.assertEqual(a.length, 2)
        self.assertEqual(a.removeItemAt(1), 'c')
        self.assertEqual(a, ['a'])
        self.assertEqual(a.length, 1)
        self.assertEqual(a.removeItemAt(0), 'a')
        self.assertEqual(a, [])
        self.assertEqual(a.length, 0)

    def test_setItemAt(self):
        a = flex.ArrayCollection(['a', 'b', 'c'])

        self.assertEqual(a.setItemAt('d', 1), 'b')
        self.assertEqual(a, ['a', 'd', 'c'])
        self.assertEqual(a.length, 3)


class ObjectProxyTestCase(unittest.TestCase, EncoderMixIn):

    amf_type = pyamf.AMF3

    def setUp(self):
        unittest.TestCase.setUp(self)
        EncoderMixIn.setUp(self)

    def test_encode(self):
        x = flex.ObjectProxy(pyamf.MixedArray(a='spam', b=5))

        self.assertEncoded(x, '\n\x07;flex.messaging.io.ObjectProxy\n\x0b\x01',
            ('\x03a\x06\tspam', '\x03b\x04\x05', '\x01'))

    def test_decode(self):
        stream = util.BufferedByteStream(
            '\x0a\x07;flex.messaging.io.ObjectProxy\x09\x01\x03a\x06\x09spam'
            '\x03b\x04\x05\x01')
        decoder = amf3.Decoder(stream)

        x = decoder.readElement()

        self.assertEqual(x.__class__, flex.ObjectProxy)
        self.assertEqual(x._amf_object, {'a': 'spam', 'b': 5})

    def test_decode_proxy(self):
        stream = util.BufferedByteStream(
            '\x0a\x07;flex.messaging.io.ObjectProxy\x09\x01\x03a\x06\x09spam'
            '\x03b\x04\x05\x01')
        decoder = amf3.Decoder(stream)
        decoder.use_proxies = True

        x = decoder.readElement()

        self.assertEqual(x.__class__, pyamf.MixedArray)
        self.assertEqual(x, {'a': 'spam', 'b': 5})

    def test_get_attrs(self):
        x = flex.ObjectProxy()

        self.assertEqual(x._amf_object, pyamf.ASObject())

        x._amf_object = None
        self.assertEqual(x._amf_object, None)

    def test_repr(self):
        x = flex.ObjectProxy()

        self.assertEqual(repr(x), '<flex.messaging.io.ObjectProxy {}>')

        x = flex.ObjectProxy(u'ƒøø')

        self.assertEqual(repr(x), "<flex.messaging.io.ObjectProxy u'\\u0192\\xf8\\xf8'>")

########NEW FILE########
__FILENAME__ = test_flex_messaging
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Flex Messaging compatibility tests.

@since: 0.3.2
"""

import unittest
import datetime
import uuid

import pyamf
from pyamf.flex import messaging


class AbstractMessageTestCase(unittest.TestCase):
    def test_repr(self):
        a = messaging.AbstractMessage()

        a.body = u'é,è'

        try:
            repr(a)
        except:
            raise


class EncodingTestCase(unittest.TestCase):
    """
    Encoding tests for L{messaging}
    """

    def test_AcknowledgeMessage(self):
        m = messaging.AcknowledgeMessage()
        m.correlationId = '1234'

        self.assertEqual(pyamf.encode(m).getvalue(),
            '\n\x81\x0bUflex.messaging.messages.AcknowledgeMessage\tbody'
            '\x11clientId\x17destination\x0fheaders\x13messageId\x13timestamp'
            '\x15timeToLive\x1bcorrelationId\x01\x01\x01\n\x0b\x01\x01\x01\x01'
            '\x01\x06\t1234\x01')

    def test_CommandMessage(self):
        m = messaging.CommandMessage(operation='foo.bar')

        self.assertEqual(pyamf.encode(m).getvalue(),
            '\n\x81\x1bMflex.messaging.messages.CommandMessage\x1bcorrelationId'
            '\tbody\x11clientId\x17destination\x0fheaders\x13messageId\x13'
            'timestamp\x15timeToLive\x13operation\x01\x01\x01\x01\n\x0b\x01\x01'
            '\x01\x01\x01\x06\x0ffoo.bar\x01')

    def test_ErrorMessage(self):
        m = messaging.ErrorMessage(faultString='ValueError')

        self.assertEqual(pyamf.encode(m).getvalue(),
            '\n\x81[Iflex.messaging.messages.ErrorMessage\x1bcorrelationId\x15'
            'timeToLive\x13timestamp\x13messageId\x0fheaders\x17destination'
            '\x11clientId\tbody\x19extendedData\x13faultCode\x17faultDetail'
            '\x17faultString\x13rootCause\x01\x01\x01\x01\n\x0b\x01\x01\x01'
            '\x01\x01\n\x05\x01\x01\x01\x06\x15ValueError\n\x05\x01\x01')

    def test_RemotingMessage(self):
        m = messaging.RemotingMessage(source='foo.bar')

        self.assertEqual(pyamf.encode(m).getvalue(),
            '\n\x81\x1bOflex.messaging.messages.RemotingMessage\x15timeToLive'
            '\x13timestamp\x13messageId\x0fheaders\x17destination\x11clientId'
            '\tbody\x13operation\rsource\x01\x01\x01\n\x0b\x01\x01\x01\x01\x01'
            '\x01\x06\x0ffoo.bar\x01')


class SmallMessageTestCase(unittest.TestCase):
    """
    Tests for L{messaging.SmallMessageMixIn}
    """

    def setUp(self):
        self.decoder = pyamf.get_decoder(pyamf.AMF3)
        self.buffer = self.decoder.stream

    def test_acknowledge(self):
        bytes = ('\n\x07\x07DSK\xa8\x03\n\x0b\x01%DSMessagingVersion\x05?\xf0'
            '\x00\x00\x00\x00\x00\x00\tDSId\x06IEE0D161D-C11D-25CB-8DBE-3B77B'
            '54B55D9\x01\x05Br3&m\x85\x10\x00\x0c!\xee\r\x16\x1d\xc1(&[\xc9'
            '\x80RK\x9bE\xc6\xc4\x0c!\xee\r\x16\x1d\xc1=\x8e\xa3\xe0\x10\xef'
            '\xad;\xe5\xc5j\x02\x0c!S\x84\x83\xdb\xa9\xc8\xcaM`\x952f\xdbQ'
            '\xc9<\x00')
        self.buffer.write(bytes)
        self.buffer.seek(0)

        msg = self.decoder.readElement()

        self.assertTrue(isinstance(msg, messaging.AcknowledgeMessageExt))
        self.assertEqual(msg.body, None)
        self.assertEqual(msg.destination, None)
        self.assertEqual(msg.timeToLive, None)

        self.assertEqual(msg.timestamp, datetime.datetime(2009, 8, 19, 11, 24, 43, 985000))
        self.assertEqual(msg.headers, {
            'DSMessagingVersion': 1.0,
            'DSId': u'EE0D161D-C11D-25CB-8DBE-3B77B54B55D9'
        })
        self.assertEqual(msg.clientId, uuid.UUID('ee0d161d-c128-265b-c980-524b9b45c6c4'))
        self.assertEqual(msg.messageId, uuid.UUID('ee0d161d-c13d-8ea3-e010-efad3be5c56a'))
        self.assertEqual(msg.correlationId, uuid.UUID('538483db-a9c8-ca4d-6095-3266db51c93c'))
        self.assertEqual(self.buffer.remaining(), 0)

        # now encode the msg to check that encoding is byte for byte the same
        buffer = pyamf.encode(msg, encoding=pyamf.AMF3).getvalue()

        self.assertEqual(buffer, bytes)

    def test_command(self):
        bytes = ('\n\x07\x07DSC\x88\x02\n\x0b\x01\tDSId\x06IEE0D161D-C11D-'
            '25CB-8DBE-3B77B54B55D9\x01\x0c!\xc0\xdf\xb7|\xd6\xee$1s\x152f'
            '\xe11\xa8f\x01\x06\x01\x01\x04\x02')

        self.buffer.write(bytes)
        self.buffer.seek(0)

        msg = self.decoder.readElement()

        self.assertTrue(isinstance(msg, messaging.CommandMessageExt))
        self.assertEqual(msg.body, None)
        self.assertEqual(msg.destination, None)
        self.assertEqual(msg.timeToLive, None)

        self.assertEqual(msg.timestamp, None)
        self.assertEqual(msg.headers, {
            'DSId': u'EE0D161D-C11D-25CB-8DBE-3B77B54B55D9'
        })
        self.assertEqual(msg.clientId, None)
        self.assertEqual(msg.messageId, uuid.UUID('c0dfb77c-d6ee-2431-7315-3266e131a866'))
        self.assertEqual(msg.correlationId, u'')
        self.assertEqual(self.buffer.remaining(), 0)

        # now encode the msg to check that encoding is byte for byte the same
        buffer = pyamf.encode(msg, encoding=pyamf.AMF3).getvalue()

        self.assertEqual(buffer, bytes)

    def test_async(self):
        pass

    def test_getmessage(self):
        """
        Tests for `getSmallMessage`
        """
        for cls in ['AbstractMessage', 'ErrorMessage', 'RemotingMessage']:
            cls = getattr(messaging, cls)
            self.assertRaises(NotImplementedError, cls().getSmallMessage)

        kwargs = {
            'body': {'foo': 'bar'},
            'clientId': 'spam',
            'destination': 'eggs',
            'headers': {'blarg': 'whoop'},
            'messageId': 'baz',
            'timestamp': 1234,
            'timeToLive': 99
        }

        # test async
        a = messaging.AsyncMessage(correlationId='yay', **kwargs)
        m = a.getSmallMessage()

        k = kwargs.copy()
        k.update({'correlationId': 'yay'})

        self.assertTrue(isinstance(m, messaging.AsyncMessageExt))
        self.assertEqual(m.__dict__, k)

        # test command
        a = messaging.CommandMessage(operation='yay', **kwargs)
        m = a.getSmallMessage()

        k = kwargs.copy()
        k.update({'operation': 'yay', 'correlationId': None})

        self.assertTrue(isinstance(m, messaging.CommandMessageExt))
        self.assertEqual(m.__dict__, k)

        # test ack
        a = messaging.AcknowledgeMessage(**kwargs)
        m = a.getSmallMessage()

        k = kwargs.copy()
        k.update({'correlationId': None})

        self.assertTrue(isinstance(m, messaging.AcknowledgeMessageExt))
        self.assertEqual(m.__dict__, k)

########NEW FILE########
__FILENAME__ = test_gateway
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
General gateway tests.

@since: 0.1.0
"""

import unittest
import sys

import pyamf
from pyamf import remoting
from pyamf.remoting import gateway, amf0


class TestService(object):
    def spam(self):
        return 'spam'

    def echo(self, x):
        return x


class FaultTestCase(unittest.TestCase):
    def test_create(self):
        x = remoting.ErrorFault()

        self.assertEqual(x.code, '')
        self.assertEqual(x.details, '')
        self.assertEqual(x.description, '')

        x = remoting.ErrorFault(code=404, details='Not Found', description='Spam eggs')

        self.assertEqual(x.code, 404)
        self.assertEqual(x.details, 'Not Found')
        self.assertEqual(x.description, 'Spam eggs')

    def test_build(self):
        fault = None

        try:
            raise TypeError("Unknown type")
        except TypeError:
            fault = amf0.build_fault(*sys.exc_info())

        self.assertTrue(isinstance(fault, remoting.ErrorFault))
        self.assertEqual(fault.level, 'error')
        self.assertEqual(fault.code, 'TypeError')
        self.assertEqual(fault.details, None)

    def test_build_traceback(self):
        fault = None

        try:
            raise TypeError("Unknown type")
        except TypeError:
            fault = amf0.build_fault(include_traceback=True, *sys.exc_info())

        self.assertTrue(isinstance(fault, remoting.ErrorFault))
        self.assertEqual(fault.level, 'error')
        self.assertEqual(fault.code, 'TypeError')
        self.assertTrue("\\n" not in fault.details)

    def test_encode(self):
        encoder = pyamf.get_encoder(pyamf.AMF0)
        decoder = pyamf.get_decoder(pyamf.AMF0)
        decoder.stream = encoder.stream

        try:
            raise TypeError("Unknown type")
        except TypeError:
            encoder.writeElement(amf0.build_fault(*sys.exc_info()))

        buffer = encoder.stream
        buffer.seek(0, 0)

        fault = decoder.readElement()
        old_fault = amf0.build_fault(*sys.exc_info())

        self.assertEqual(fault.level, old_fault.level)
        self.assertEqual(fault.type, old_fault.type)
        self.assertEqual(fault.code, old_fault.code)
        self.assertEqual(fault.details, old_fault.details)
        self.assertEqual(fault.description, old_fault.description)

    def test_explicit_code(self):
        class X(Exception):
            _amf_code = 'Server.UnknownResource'

        try:
            raise X()
        except X:
            fault = amf0.build_fault(*sys.exc_info())

        self.assertEqual(fault.code, 'Server.UnknownResource')


class ServiceWrapperTestCase(unittest.TestCase):
    def test_create(self):
        x = gateway.ServiceWrapper('blah')

        self.assertEqual(x.service, 'blah')

    def test_create_preprocessor(self):
        x = gateway.ServiceWrapper('blah', preprocessor=ord)

        self.assertEqual(x.preprocessor, ord)

    def test_cmp(self):
        x = gateway.ServiceWrapper('blah')
        y = gateway.ServiceWrapper('blah')
        z = gateway.ServiceWrapper('bleh')

        self.assertEqual(x, y)
        self.assertNotEquals(y, z)

    def test_call(self):
        def add(x, y):
            self.assertEqual(x, 1)
            self.assertEqual(y, 2)

            return x + y

        x = gateway.ServiceWrapper(add)

        self.assertTrue(callable(x))
        self.assertEqual(x(None, [1, 2]), 3)

        x = gateway.ServiceWrapper('blah')

        self.assertRaises(gateway.UnknownServiceMethodError, x, None, [])

        x = gateway.ServiceWrapper(TestService)

        self.assertRaises(gateway.UnknownServiceMethodError, x, None, [])
        self.assertEqual(x('spam', []), 'spam')

        self.assertRaises(gateway.UnknownServiceMethodError, x, 'xyx', [])
        self.assertRaises(gateway.InvalidServiceMethodError, x, '_private', [])

        self.assertEqual(x('echo', [x]), x)


class ServiceRequestTestCase(unittest.TestCase):
    def test_create(self):
        sw = gateway.ServiceWrapper(TestService)
        request = remoting.Envelope()

        x = gateway.ServiceRequest(request, sw, None)

        self.assertEqual(x.request, request)
        self.assertEqual(x.service, sw)
        self.assertEqual(x.method, None)

    def test_call(self):
        sw = gateway.ServiceWrapper(TestService)
        request = remoting.Envelope()

        x = gateway.ServiceRequest(request, sw, None)

        self.assertRaises(gateway.UnknownServiceMethodError, x)

        x = gateway.ServiceRequest(request, sw, 'spam')
        self.assertEqual(x(), 'spam')

        x = gateway.ServiceRequest(request, sw, 'echo')
        self.assertEqual(x(x), x)


class ServiceCollectionTestCase(unittest.TestCase):
    def test_contains(self):
        x = gateway.ServiceCollection()

        self.assertFalse(TestService in x)
        self.assertFalse('spam.eggs' in x)

        x['spam.eggs'] = gateway.ServiceWrapper(TestService)

        self.assertTrue(TestService in x)
        self.assertTrue('spam.eggs' in x)


class BaseGatewayTestCase(unittest.TestCase):
    def test_create(self):
        x = gateway.BaseGateway()
        self.assertEqual(x.services, {})

        x = gateway.BaseGateway({})
        self.assertEqual(x.services, {})

        x = gateway.BaseGateway({})
        self.assertEqual(x.services, {})

        x = gateway.BaseGateway({'x': TestService})
        self.assertEqual(x.services, {'x': TestService})

        x = gateway.BaseGateway({}, timezone_offset=-180)
        self.assertEqual(x.timezone_offset, -180)

        self.assertRaises(TypeError, gateway.BaseGateway, [])
        self.assertRaises(TypeError, gateway.BaseGateway, foo='bar')

    def test_add_service(self):
        gw = gateway.BaseGateway()
        self.assertEqual(gw.services, {})

        gw.addService(TestService)
        self.assertTrue(TestService in gw.services)
        self.assertTrue('TestService' in gw.services)

        del gw.services['TestService']

        gw.addService(TestService, 'spam.eggs')
        self.assertTrue(TestService in gw.services)
        self.assertTrue('spam.eggs' in gw.services)

        del gw.services['spam.eggs']

        class SpamService(object):
            def __str__(self):
                return 'spam'

            def __call__(*args, **kwargs):
                pass

        x = SpamService()

        gw.addService(x)
        self.assertTrue(x in gw.services)
        self.assertTrue('spam' in gw.services)

        del gw.services['spam']

        self.assertEqual(gw.services, {})

        self.assertRaises(TypeError, gw.addService, 1)

        import new

        temp = new.module('temp')
        gw.addService(temp)

        self.assertTrue(temp in gw.services)
        self.assertTrue('temp' in gw.services)

        del gw.services['temp']

        self.assertEqual(gw.services, {})

    def test_remove_service(self):
        gw = gateway.BaseGateway({'test': TestService})
        self.assertTrue('test' in gw.services)
        wrapper = gw.services['test']

        gw.removeService('test')

        self.assertFalse('test' in gw.services)
        self.assertFalse(TestService in gw.services)
        self.assertFalse(wrapper in gw.services)
        self.assertEqual(gw.services, {})

        gw = gateway.BaseGateway({'test': TestService})
        self.assertTrue(TestService in gw.services)
        wrapper = gw.services['test']

        gw.removeService(TestService)

        self.assertFalse('test' in gw.services)
        self.assertFalse(TestService in gw.services)
        self.assertFalse(wrapper in gw.services)
        self.assertEqual(gw.services, {})

        gw = gateway.BaseGateway({'test': TestService})
        self.assertTrue(TestService in gw.services)
        wrapper = gw.services['test']

        gw.removeService(wrapper)

        self.assertFalse('test' in gw.services)
        self.assertFalse(TestService in gw.services)
        self.assertFalse(wrapper in gw.services)
        self.assertEqual(gw.services, {})

        x = TestService()
        gw = gateway.BaseGateway({'test': x})

        gw.removeService(x)

        self.assertFalse('test' in gw.services)
        self.assertEqual(gw.services, {})

        self.assertRaises(NameError, gw.removeService, 'test')
        self.assertRaises(NameError, gw.removeService, TestService)
        self.assertRaises(NameError, gw.removeService, wrapper)

    def test_service_request(self):
        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()

        message = remoting.Request('spam', [], envelope=envelope)
        self.assertRaises(gateway.UnknownServiceError, gw.getServiceRequest,
            message, 'spam')

        message = remoting.Request('test.spam', [], envelope=envelope)
        sr = gw.getServiceRequest(message, 'test.spam')

        self.assertTrue(isinstance(sr, gateway.ServiceRequest))
        self.assertEqual(sr.request, envelope)
        self.assertEqual(sr.service, TestService)
        self.assertEqual(sr.method, 'spam')

        message = remoting.Request('test')
        sr = gw.getServiceRequest(message, 'test')

        self.assertTrue(isinstance(sr, gateway.ServiceRequest))
        self.assertEqual(sr.request, None)
        self.assertEqual(sr.service, TestService)
        self.assertEqual(sr.method, None)

        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()
        message = remoting.Request('test')

        sr = gw.getServiceRequest(message, 'test')

        self.assertTrue(isinstance(sr, gateway.ServiceRequest))
        self.assertEqual(sr.request, None)
        self.assertEqual(sr.service, TestService)
        self.assertEqual(sr.method, None)

        # try to access an unknown service
        message = remoting.Request('spam')
        self.assertRaises(gateway.UnknownServiceError, gw.getServiceRequest,
            message, 'spam')

        # check x.x calls
        message = remoting.Request('test.test')
        sr = gw.getServiceRequest(message, 'test.test')

        self.assertTrue(isinstance(sr, gateway.ServiceRequest))
        self.assertEqual(sr.request, None)
        self.assertEqual(sr.service, TestService)
        self.assertEqual(sr.method, 'test')

    def test_long_service_name(self):
        gw = gateway.BaseGateway({'a.c.b.d': TestService})
        envelope = remoting.Envelope()

        message = remoting.Request('a.c.b.d', [], envelope=envelope)
        sr = gw.getServiceRequest(message, 'a.c.b.d.spam')

        self.assertTrue(isinstance(sr, gateway.ServiceRequest))
        self.assertEqual(sr.request, envelope)
        self.assertEqual(sr.service, TestService)
        self.assertEqual(sr.method, 'spam')

    def test_get_response(self):
        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()

        self.assertRaises(NotImplementedError, gw.getResponse, envelope)

    def test_process_request(self):
        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()

        request = remoting.Request('test.spam', envelope=envelope)

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_unknown_service(self):
        # Test a non existant service call
        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()

        request = remoting.Request('nope', envelope=envelope)
        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertFalse(gw.debug)
        self.assertTrue(isinstance(response, remoting.Message))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, remoting.ErrorFault))

        self.assertEqual(response.body.code, 'Service.ResourceNotFound')
        self.assertEqual(response.body.description, 'Unknown service nope')
        self.assertEqual(response.body.details, None)

    def test_debug_traceback(self):
        # Test a non existant service call
        gw = gateway.BaseGateway({'test': TestService}, debug=True)
        envelope = remoting.Envelope()

        # Test a non existant service call
        request = remoting.Request('nope', envelope=envelope)
        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertTrue(isinstance(response, remoting.Message))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, remoting.ErrorFault))

        self.assertEqual(response.body.code, 'Service.ResourceNotFound')
        self.assertEqual(response.body.description, 'Unknown service nope')
        self.assertNotEquals(response.body.details, None)

    def test_malformed_credentials_header(self):
        gw = gateway.BaseGateway({'test': TestService})
        envelope = remoting.Envelope()

        request = remoting.Request('test.spam', envelope=envelope)
        request.headers['Credentials'] = {'spam': 'eggs'}

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)
        self.assertTrue(isinstance(response.body, remoting.ErrorFault))

        self.assertEqual(response.body.code, 'KeyError')

    def test_authenticate(self):
        gw = gateway.BaseGateway({'test': TestService})
        sr = gateway.ServiceRequest(None, gw.services['test'], None)

        self.assertTrue(gw.authenticateRequest(sr, None, None))

        def auth(u, p):
            if u == 'spam' and p == 'eggs':
                return True

            return False

        gw = gateway.BaseGateway({'test': TestService}, authenticator=auth)

        self.assertFalse(gw.authenticateRequest(sr, None, None))
        self.assertTrue(gw.authenticateRequest(sr, 'spam', 'eggs'))

    def test_null_target(self):
        gw = gateway.BaseGateway({})

        request = remoting.Request(None)
        processor = gw.getProcessor(request)

        from pyamf.remoting import amf3

        self.assertTrue(isinstance(processor, amf3.RequestProcessor))

    def test_empty_target(self):
        gw = gateway.BaseGateway({})

        request = remoting.Request('')
        processor = gw.getProcessor(request)

        from pyamf.remoting import amf3

        self.assertTrue(isinstance(processor, amf3.RequestProcessor))


class QueryBrowserTestCase(unittest.TestCase):
    def test_request(self):
        gw = gateway.BaseGateway()
        echo = lambda x: x

        gw.addService(echo, 'echo', description='This is a test')

        envelope = remoting.Envelope()
        request = remoting.Request('echo')
        envelope['/1'] = request

        request.headers['DescribeService'] = None

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'This is a test')


class AuthenticatorTestCase(unittest.TestCase):
    def setUp(self):
        self.called = False

    def tearDown(self):
        if self.called is False:
            self.fail("authenticator not called")

    def _auth(self, username, password):
        self.called = True

        if username == 'fred' and password == 'wilma':
            return True

        return False

    def test_gateway(self):
        gw = gateway.BaseGateway(authenticator=self._auth)
        echo = lambda x: x

        gw.addService(echo, 'echo')

        envelope = remoting.Envelope()
        request = remoting.Request('echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_service(self):
        gw = gateway.BaseGateway()
        echo = lambda x: x

        gw.addService(echo, 'echo', authenticator=self._auth)

        envelope = remoting.Envelope()
        request = remoting.Request('echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_class_decorator(self):
        class TestService:
            def echo(self, x):
                return x

        TestService.echo = gateway.authenticate(TestService.echo, self._auth)

        gw = gateway.BaseGateway({'test': TestService})

        envelope = remoting.Envelope()
        request = remoting.Request('test.echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_func_decorator(self):
        def echo(x):
            return x

        echo = gateway.authenticate(echo, self._auth)

        gw = gateway.BaseGateway({'echo': echo})

        envelope = remoting.Envelope()
        request = remoting.Request('echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_expose_request_decorator(self):
        def echo(x):
            return x

        def exposed_auth(request, username, password):
            return self._auth(username, password)

        exposed_auth = gateway.expose_request(exposed_auth)

        echo = gateway.authenticate(echo, exposed_auth)
        gw = gateway.BaseGateway({'echo': echo})

        envelope = remoting.Envelope()
        request = remoting.Request('echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')

    def test_expose_request_keyword(self):
        def echo(x):
            return x

        def exposed_auth(request, username, password):
            return self._auth(username, password)

        echo = gateway.authenticate(echo, exposed_auth, expose_request=True)
        gw = gateway.BaseGateway({'echo': echo})

        envelope = remoting.Envelope()
        request = remoting.Request('echo', body=['spam'])
        envelope.headers['Credentials'] = dict(userid='fred', password='wilma')
        envelope['/1'] = request

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')


class ExposeRequestTestCase(unittest.TestCase):
    def test_default(self):
        gw = gateway.BaseGateway()

        gw.addService(lambda x: x, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertFalse(gw.mustExposeRequest(service_request))

    def test_gateway(self):
        gw = gateway.BaseGateway(expose_request=True)

        gw.addService(lambda x: x, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertTrue(gw.mustExposeRequest(service_request))

    def test_service(self):
        gw = gateway.BaseGateway()

        gw.addService(lambda x: x, 'test', expose_request=True)

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertTrue(gw.mustExposeRequest(service_request))

    def test_decorator(self):
        def echo(x):
            return x

        gateway.expose_request(echo)

        gw = gateway.BaseGateway()

        gw.addService(echo, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertTrue(gw.mustExposeRequest(service_request))


class PreProcessingTestCase(unittest.TestCase):
    def _preproc(self):
        pass

    def test_default(self):
        gw = gateway.BaseGateway()

        gw.addService(lambda x: x, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertEqual(gw.getPreprocessor(service_request), None)

    def test_global(self):
        gw = gateway.BaseGateway(preprocessor=self._preproc)

        gw.addService(lambda x: x, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertEqual(gw.getPreprocessor(service_request), self._preproc)

    def test_service(self):
        gw = gateway.BaseGateway()

        gw.addService(lambda x: x, 'test', preprocessor=self._preproc)

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertEqual(gw.getPreprocessor(service_request), self._preproc)

    def test_decorator(self):
        def echo(x):
            return x

        gateway.preprocess(echo, self._preproc)

        gw = gateway.BaseGateway()

        gw.addService(echo, 'test')

        envelope = remoting.Envelope()
        request = remoting.Request('test')
        envelope['/1'] = request

        service_request = gateway.ServiceRequest(envelope, gw.services['test'], None)

        self.assertEqual(gw.getPreprocessor(service_request), self._preproc)

    def test_call(self):
        def preproc(sr, *args):
            self.called = True

            self.assertEqual(args, tuple())
            self.assertTrue(isinstance(sr, gateway.ServiceRequest))

        gw = gateway.BaseGateway({'test': TestService}, preprocessor=preproc)
        envelope = remoting.Envelope()

        request = remoting.Request('test.spam', envelope=envelope)

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_OK)
        self.assertEqual(response.body, 'spam')
        self.assertTrue(self.called)

    def test_fail(self):
        def preproc(sr, *args):
            raise IndexError

        gw = gateway.BaseGateway({'test': TestService}, preprocessor=preproc)
        envelope = remoting.Envelope()

        request = remoting.Request('test.spam', envelope=envelope)

        processor = gw.getProcessor(request)
        response = processor(request)

        self.assertTrue(isinstance(response, remoting.Response))
        self.assertEqual(response.status, remoting.STATUS_ERROR)

########NEW FILE########
__FILENAME__ = test_imports
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests pyamf.util.imports

@since: 0.3.1
"""

import unittest
import sys
import os.path

from pyamf.util import imports


class InstalledTestCase(unittest.TestCase):
    """
    Tests to ensure that L{imports.finder} is installed in L{sys.meta_path}
    """

    def test_installed(self):
        f = imports.finder

        self.assertTrue(f in sys.meta_path)
        self.assertIdentical(sys.meta_path[0], f)


class ImportsTestCase(unittest.TestCase):
    def setUp(self):
        self.finder = imports.finder

        self._state = self.finder.__getstate__()

        path = os.path.join(os.path.dirname(__file__), 'imports')
        sys.path.insert(0, path)

    def tearDown(self):
        self.finder.__setstate__(self._state)

        del sys.path[0]
        self._clearModules('spam')

    def _clearModules(self, *args):
        for mod in args:
            for k, v in sys.modules.copy().iteritems():
                if k.startswith(mod) or k == 'pyamf.tests.%s' % (mod,):
                    del sys.modules[k]


class WhenImportedTestCase(ImportsTestCase):
    """
    Tests for L{imports.when_imported}
    """

    def setUp(self):
        ImportsTestCase.setUp(self)

        self.executed = False

    def _hook(self, module):
        self.executed = True

    def _check_module(self, mod):
        name = mod.__name__

        self.assertTrue(name in sys.modules)
        self.assertIdentical(sys.modules[name], mod)

    def test_import(self):
        imports.when_imported('spam', self._hook)

        self.assertFalse(self.executed)

        import spam

        self._check_module(spam)
        self.assertTrue(self.executed)

    def test_already_imported(self):
        import spam

        self.assertFalse(self.executed)

        imports.when_imported('spam', self._hook)

        self._check_module(spam)
        self.assertTrue(self.executed)

    def test_failed_hook(self):
        def h(mod):
            raise RuntimeError

        imports.when_imported('spam', h)

        try:
            import spam
        except Exception, e:
            pass
        else:
            self.fail('expected exception')

        self.assertFalse('spam' in self.finder.loaded_modules)

        self.assertEqual(e.__class__, RuntimeError)

########NEW FILE########
__FILENAME__ = test_remoting
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF Remoting.

@since: 0.1.0
"""

import unittest

import pyamf
from pyamf import remoting, util


class DecoderTestCase(unittest.TestCase):
    """
    Tests the decoders.
    """

    def test_client_version(self):
        """
        Tests the AMF client version.
        """
        for x in ('\x00', '\x01', '\x03'):
            try:
                remoting.decode('\x00' + x)
            except IOError:
                pass

    def test_null_msg(self):
        msg = remoting.decode('\x00\x00\x00\x00\x00\x00')

        self.assertEqual(msg.amfVersion, 0)
        self.assertEqual(msg.headers, {})
        self.assertEqual(msg, {})

        y = [x for x in msg]

        self.assertEqual(y, [])

    def test_simple_header(self):
        """
        Test header decoder.
        """
        msg = remoting.decode('\x00\x00\x00\x01\x00\x04name\x00\x00\x00\x00'
            '\x05\x0a\x00\x00\x00\x00\x00\x00')

        self.assertEqual(msg.amfVersion, 0)
        self.assertEqual(len(msg.headers), 1)
        self.assertEqual('name' in msg.headers, True)
        self.assertEqual(msg.headers['name'], [])
        self.assertFalse(msg.headers.is_required('name'))
        self.assertEqual(msg, {})

        y = [x for x in msg]

        self.assertEqual(y, [])

    def test_required_header(self):
        msg = remoting.decode('\x00\x00\x00\x01\x00\x04name\x01\x00\x00\x00'
            '\x05\x0a\x00\x00\x00\x00\x00\x00')

        self.assertTrue(msg.headers.is_required('name'))

    def test_invalid_header_data_length(self):
        remoting.decode('\x00\x00\x00\x01\x00\x04name\x00\x00\x00\x00\x06\x0a'
            '\x00\x00\x00\x00\x00\x00')

        self.failUnlessRaises(pyamf.DecodeError, remoting.decode,
            '\x00\x00\x00\x01\x00\x04name\x00\x00\x00\x00\x06\x0a\x00\x00\x00'
            '\x00\x00\x00', strict=True)

    def test_multiple_headers(self):
        msg = remoting.decode('\x00\x00\x00\x02\x00\x04name\x00\x00\x00\x00'
            '\x05\x0a\x00\x00\x00\x00\x00\x04spam\x01\x00\x00\x00\x01\x05\x00'
            '\x00')

        self.assertEqual(msg.amfVersion, 0)
        self.assertEqual(len(msg.headers), 2)
        self.assertEqual('name' in msg.headers, True)
        self.assertEqual('spam' in msg.headers, True)
        self.assertEqual(msg.headers['name'], [])
        self.assertFalse(msg.headers.is_required('name'))
        self.assertEqual(msg.headers['spam'], None)
        self.assertTrue(msg.headers.is_required('spam'))
        self.assertEqual(msg, {})

        y = [x for x in msg]

        self.assertEqual(y, [])

    def test_simple_body(self):
        self.failUnlessRaises(IOError, remoting.decode,
            '\x00\x00\x00\x00\x00\x01')

        msg = remoting.decode('\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00'
            '\x02/1\x00\x00\x00\x14\x0a\x00\x00\x00\x01\x08\x00\x00\x00\x00'
            '\x00\x01\x61\x02\x00\x01\x61\x00\x00\x09')

        self.assertEqual(msg.amfVersion, 0)
        self.assertEqual(len(msg.headers), 0)
        self.assertEqual(len(msg), 1)
        self.assertTrue('/1' in msg)

        m = msg['/1']

        self.assertEqual(m.target, 'test.test')
        self.assertEqual(m.body, [{'a': 'a'}])

        y = [x for x in msg]

        self.assertEqual(len(y), 1)

        x = y[0]
        self.assertEqual(('/1', m), x)

    def test_invalid_body_data_length(self):
        remoting.decode('\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00\x02/1'
            '\x00\x00\x00\x13\x0a\x00\x00\x00\x01\x08\x00\x00\x00\x00\x00\x01'
            '\x61\x02\x00\x01\x61\x00\x00\x09')

        self.failUnlessRaises(pyamf.DecodeError, remoting.decode,
            '\x00\x00\x00\x00\x00\x01\x00\x09test.test\x00\x02/1\x00\x00\x00'
            '\x13\x0a\x00\x00\x00\x01\x08\x00\x00\x00\x00\x00\x01\x61\x02\x00'
            '\x01\x61\x00\x00\x09', strict=True)

    def test_message_order(self):
        request = util.BufferedByteStream()
        request.write('\x00\x00\x00\x00\x00\x02\x00\x08get_spam\x00\x02/2\x00'
            '\x00\x00\x00\x0a\x00\x00\x00\x00\x00\x04echo\x00\x02/1\x00\x00'
            '\x00\x00\x0a\x00\x00\x00\x01\x02\x00\x0bhello world')
        request.seek(0, 0)

        request_envelope = remoting.decode(request)
        it = iter(request_envelope)

        self.assertEqual(it.next()[0], '/2')
        self.assertEqual(it.next()[0], '/1')

        self.assertRaises(StopIteration, it.next)

    def test_multiple_request_header_references(self):
        msg = remoting.decode(
            '\x00\x00\x00\x01\x00\x0b\x43\x72\x65\x64\x65\x6e\x74\x69\x61\x6c'
            '\x73\x00\x00\x00\x00\x2c\x11\x0a\x0b\x01\x0d\x75\x73\x65\x72\x69'
            '\x64\x06\x1f\x67\x65\x6e\x6f\x70\x72\x6f\x5c\x40\x67\x65\x72\x61'
            '\x72\x64\x11\x70\x61\x73\x73\x77\x6f\x72\x64\x06\x09\x67\x67\x67'
            '\x67\x01\x00\x01\x00\x0b\x63\x72\x65\x61\x74\x65\x47\x72\x6f\x75'
            '\x70\x00\x02\x2f\x31\x00\x00\x00\x1c\x0a\x00\x00\x00\x01\x11\x0a'
            '\x0b\x01\x09\x73\x74\x72\x41\x06\x09\x74\x65\x73\x74\x09\x73\x74'
            '\x72\x42\x06\x02\x01')

        self.assertEqual(msg.amfVersion, 0)
        self.assertEqual(len(msg.headers), 1)
        self.assertEqual(msg.headers['Credentials'],
            {'password': 'gggg', 'userid':'genopro\\@gerard'})
        self.assertEqual(len(msg), 1)
        self.assertTrue('/1' in msg)

        m = msg['/1']

        self.assertEqual(m.target, 'createGroup')
        self.assertEqual(m.body, [{'strB':'test', 'strA':'test'}])

    def test_timezone(self):
        """
        Ensure that the timezone offsets work as expected
        """
        import datetime

        td = datetime.timedelta(hours=-5)

        msg = remoting.decode(
            '\x00\x00\x00\x00\x00\x01\x00\x0b/1/onResult\x00\x04null\x00\x00'
            '\x00\x00\n\x00\x00\x00\x01\x0bBr>\xcc\n~\x00\x00\x00\x00',
            timezone_offset=td)

        self.assertEqual(msg['/1'].body[0],
            datetime.datetime(2009, 9, 24, 10, 52, 12))


class EncoderTestCase(unittest.TestCase):
    """
    Test the encoders.
    """
    def test_basic(self):
        """
        """
        msg = remoting.Envelope(pyamf.AMF0)
        self.assertEqual(remoting.encode(msg).getvalue(), '\x00' * 6)

        msg = remoting.Envelope(pyamf.AMF3)
        self.assertEqual(remoting.encode(msg).getvalue(),
            '\x00\x03' + '\x00' * 4)

    def test_header(self):
        """
        Test encoding of header.
        """
        msg = remoting.Envelope(pyamf.AMF0)

        msg.headers['spam'] = (False, 'eggs')
        self.assertEqual(remoting.encode(msg).getvalue(),
            '\x00\x00\x00\x01\x00\x04spam\x00\x00\x00\x00\x00\n\x00\x00\x00\x02'
            '\x01\x00\x02\x00\x04eggs\x00\x00')

        msg = remoting.Envelope(pyamf.AMF0)

        msg.headers['spam'] = (True, ['a', 'b', 'c'])
        self.assertEqual(remoting.encode(msg).getvalue(),
            '\x00\x00\x00\x01\x00\x04spam\x00\x00\x00\x00\x00\n\x00\x00\x00\x02'
            '\x01\x01\n\x00\x00\x00\x03\x02\x00\x01a\x02\x00\x01b\x02\x00\x01c'
            '\x00\x00')

    def test_request(self):
        """
        Test encoding of request body.
        """
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Request('test.test', body=['hello'])

        self.assertEqual(len(msg), 1)

        x = msg['/1']

        self.assertTrue(isinstance(x, remoting.Request))
        self.assertEqual(x.envelope, msg)
        self.assertEqual(x.target, 'test.test')
        self.assertEqual(x.body, ['hello'])
        self.assertEqual(x.headers, msg.headers)

        self.assertEqual(remoting.encode(msg).getvalue(),
            '\x00\x00\x00\x00\x00\x01\x00\ttest.test\x00\x02/1\x00\x00\x00'
            '\x00\n\x00\x00\x00\x01\x02\x00\x05hello')

    def test_response(self):
        """
        Test encoding of request body.
        """
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Response(body=[1, 2, 3])

        self.assertEqual(len(msg), 1)

        x = msg['/1']

        self.assertTrue(isinstance(x, remoting.Response))
        self.assertEqual(x.envelope, msg)
        self.assertEqual(x.body, [1, 2, 3])
        self.assertEqual(x.status, 0)
        self.assertEqual(x.headers, msg.headers)

        self.assertEqual(remoting.encode(msg).getvalue(), '\x00\x00\x00\x00'
            '\x00\x01\x00\x0b/1/onResult\x00\x04null\x00\x00\x00\x00\n\x00\x00'
            '\x00\x03\x00?\xf0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00'
            '\x00\x00\x00\x00@\x08\x00\x00\x00\x00\x00\x00')

    def test_message_order(self):
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/3'] = remoting.Request('test.test', body='hello')
        msg['/1'] = remoting.Request('test.test', body='hello')
        msg['/2'] = remoting.Request('test.test', body='hello')

        it = iter(msg)

        self.assertEqual(it.next()[0], '/3')
        self.assertEqual(it.next()[0], '/1')
        self.assertEqual(it.next()[0], '/2')

        self.assertRaises(StopIteration, it.next)

    def test_stream_pos(self):
        """
        Ensure that the stream pointer is placed at the beginning.
        """
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Response(body=[1, 2, 3])

        stream = remoting.encode(msg)
        self.assertEqual(stream.tell(), 0)

    def test_timezone(self):
        """
        Ensure that the timezone offsets work as expected
        """
        import datetime

        d = datetime.datetime(2009, 9, 24, 15, 52, 12)
        td = datetime.timedelta(hours=-5)
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Response(body=[d])

        stream = remoting.encode(msg, timezone_offset=td).getvalue()

        self.assertEqual(stream, '\x00\x00\x00\x00\x00\x01\x00\x0b/1/onResult'
            '\x00\x04null\x00\x00\x00\x00\n\x00\x00\x00\x01\x0bBr>\xdd5\x06'
            '\x00\x00\x00\x00')


class StrictEncodingTestCase(unittest.TestCase):
    def test_request(self):
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Request('test.test', body=['hello'])

        self.assertEqual(remoting.encode(msg, strict=True).getvalue(),
            '\x00\x00\x00\x00\x00\x01\x00\ttest.test\x00\x02/1\x00\x00\x00'
            '\r\n\x00\x00\x00\x01\x02\x00\x05hello')

    def test_response(self):
        msg = remoting.Envelope(pyamf.AMF0)

        msg['/1'] = remoting.Response(['spam'])

        self.assertEqual(remoting.encode(msg, strict=True).getvalue(),
            '\x00\x00\x00\x00\x00\x01\x00\x0b/1/onResult\x00\x04null\x00\x00'
            '\x00\x0c\n\x00\x00\x00\x01\x02\x00\x04spam')


class FaultTestCase(unittest.TestCase):
    def test_exception(self):
        x = remoting.get_fault({'level': 'error', 'code': 'Server.Call.Failed'})

        self.assertRaises(remoting.RemotingCallFailed, x.raiseException)

    def test_kwargs(self):
        # The fact that this doesn't throw an error means that this test passes
        x = remoting.get_fault({'foo': 'bar'})

        self.assertIsInstance(x, remoting.ErrorFault)


class ContextTextCase(unittest.TestCase):
    def test_body_references(self):
        msg = remoting.Envelope(pyamf.AMF0)
        f = ['a', 'b', 'c']

        msg['/1'] = remoting.Request('foo', body=[f])
        msg['/2'] = remoting.Request('bar', body=[f])

        s = remoting.encode(msg).getvalue()
        self.assertEqual(s, '\x00\x00\x00\x00\x00\x02\x00\x03foo\x00\x02/1'
            '\x00\x00\x00\x00\n\x00\x00\x00\x01\n\x00\x00\x00\x03\x02\x00\x01'
            'a\x02\x00\x01b\x02\x00\x01c\x00\x03bar\x00\x02/2\x00\x00\x00\x00'
            '\n\x00\x00\x00\x01\n\x00\x00\x00\x03\x02\x00\x01a\x02\x00\x01b'
            '\x02\x00\x01c')


class FunctionalTestCase(unittest.TestCase):
    def test_encode_bytearray(self):
        from pyamf.amf3 import ByteArray

        stream = ByteArray()

        stream.write('12345678')

        msg = remoting.Envelope(pyamf.AMF0)
        msg['/1'] = remoting.Response([stream])

        self.assertEqual(remoting.encode(msg).getvalue(),
            '\x00\x00\x00\x00\x00\x01\x00\x0b/1/onResult\x00\x04null'
            '\x00\x00\x00\x00\n\x00\x00\x00\x01\x11\x0c\x1112345678')


class ReprTestCase(unittest.TestCase):
    def test_response(self):
        r = remoting.Response(u'€±')

        self.assertEqual(repr(r),
            "<Response status=/onResult>u'\\u20ac\\xb1'</Response>")

    def test_request(self):
        r = remoting.Request(u'€±', [u'å∫ç'])

        self.assertEqual(repr(r),
            "<Request target=u'\\u20ac\\xb1'>[u'\\xe5\\u222b\\xe7']</Request>")

    def test_base_fault(self):
        r = remoting.BaseFault(code=u'å', type=u'å', description=u'å', details=u'å')

        self.assertEqual(repr(r),
            "BaseFault level=None code=u'\\xe5' type=u'\\xe5' description=u'\\xe5'\nTraceback:\nu'\\xe5'")

########NEW FILE########
__FILENAME__ = test_sol
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for Local Shared Object (LSO) Implementation.

@since: 0.1.0
"""

import unittest
import os.path
import warnings
import tempfile

from StringIO import StringIO

import pyamf
from pyamf import sol
from pyamf.tests.util import check_buffer, expectedFailureIfAppengine

warnings.simplefilter('ignore', RuntimeWarning)


class DecoderTestCase(unittest.TestCase):
    def test_header(self):
        bytes = '\x00\xbf\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00'

        try:
            sol.decode(bytes)
        except:
            self.fail("Error occurred during decoding stream")

    def test_invalid_header(self):
        bytes = '\x00\x00\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00'
        self.assertRaises(pyamf.DecodeError, sol.decode, bytes)

    def test_invalid_header_length(self):
        bytes = '\x00\xbf\x00\x00\x00\x05TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00'
        self.assertRaises(pyamf.DecodeError, sol.decode, bytes)

    def test_strict_header_length(self):
        bytes = '\x00\xbf\x00\x00\x00\x00TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00'

        try:
            sol.decode(bytes, strict=False)
        except:
            self.fail("Error occurred during decoding stream")

    def test_invalid_signature(self):
        bytes = '\x00\xbf\x00\x00\x00\x15ABCD\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00'
        self.assertRaises(pyamf.DecodeError, sol.decode, bytes)

    def test_invalid_header_name_length(self):
        bytes = '\x00\xbf\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x01hello\x00\x00\x00\x00'
        self.assertRaises(pyamf.DecodeError, sol.decode, bytes)

    def test_invalid_header_padding(self):
        bytes = '\x00\xbf\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x01\x00'
        self.assertRaises(pyamf.DecodeError, sol.decode, bytes)

    def test_unknown_encoding(self):
        bytes = '\x00\xbf\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x01'
        self.assertRaises(ValueError, sol.decode, bytes)

    def test_amf3(self):
        bytes = ('\x00\xbf\x00\x00\x00aTCSO\x00\x04\x00\x00\x00\x00\x00\x08'
            'EchoTest\x00\x00\x00\x03\x0fhttpUri\x06=http://localhost:8000'
            '/gateway/\x00\x0frtmpUri\x06+rtmp://localhost/echo\x00')

        self.assertEqual(sol.decode(bytes), (u'EchoTest',
            {u'httpUri': u'http://localhost:8000/gateway/', u'rtmpUri': u'rtmp://localhost/echo'}))


class EncoderTestCase(unittest.TestCase):
    def test_encode_header(self):
        stream = sol.encode('hello', {})

        self.assertEqual(stream.getvalue(),
            '\x00\xbf\x00\x00\x00\x15TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00')

    def test_multiple_values(self):
        stream = sol.encode('hello', {'name': 'value', 'spam': 'eggs'})

        self.assertTrue(check_buffer(stream.getvalue(), HelperTestCase.contents))

    def test_amf3(self):
        bytes = ('\x00\xbf\x00\x00\x00aTCSO\x00\x04\x00\x00\x00\x00\x00\x08' + \
            'EchoTest\x00\x00\x00\x03', (
                '\x0fhttpUri\x06=http://localhost:8000/gateway/\x00',
                '\x0frtmpUri\x06+rtmp://localhost/echo\x00'
            )
        )

        stream = sol.encode(u'EchoTest',
            {u'httpUri': u'http://localhost:8000/gateway/', u'rtmpUri': u'rtmp://localhost/echo'}, encoding=pyamf.AMF3)

        self.assertTrue(check_buffer(stream.getvalue(), bytes))


class HelperTestCase(unittest.TestCase):
    contents = (
        '\x00\xbf\x00\x00\x002TCSO\x00\x04\x00\x00\x00\x00\x00\x05hello\x00\x00\x00\x00', (
            '\x00\x04name\x02\x00\x05value\x00',
            '\x00\x04spam\x02\x00\x04eggs\x00'
        )
    )

    contents_str = (
        '\x00\xbf\x00\x00\x002TCSO\x00\x04\x00\x00\x00\x00\x00'
        '\x05hello\x00\x00\x00\x00\x00\x04name\x02\x00\x05value\x00\x00'
        '\x04spam\x02\x00\x04eggs\x00')

    def setUp(self):
        try:
            self.fp, self.file_name = tempfile.mkstemp()
        except NotImplementedError:
            try:
                import google.appengine
            except ImportError:
                raise
            else:
                self.skipTest('Not available on AppEngine')

        os.close(self.fp)

    def tearDown(self):
        if os.path.isfile(self.file_name):
            os.unlink(self.file_name)

    def _load(self):
        fp = open(self.file_name, 'wb+')

        fp.write(self.contents_str)
        fp.flush()

        return fp

    def test_load_name(self):
        fp = self._load()
        fp.close()

        s = sol.load(self.file_name)

        self.assertEqual(s.name, 'hello')
        self.assertEqual(s, {'name': 'value', 'spam': 'eggs'})

    def test_load_file(self):
        fp = self._load()
        y = fp.tell()
        fp.seek(0)

        s = sol.load(fp)

        self.assertEqual(s.name, 'hello')
        self.assertEqual(s, {'name': 'value', 'spam': 'eggs'})
        self.assertEqual(y, fp.tell())

    def test_save_name(self):
        s = sol.SOL('hello')
        s.update({'name': 'value', 'spam': 'eggs'})

        sol.save(s, self.file_name)

        fp = open(self.file_name, 'rb')

        try:
            self.assertTrue(check_buffer(fp.read(), self.contents))
        finally:
            fp.close()

    def test_save_file(self):
        fp = open(self.file_name, 'wb+')
        s = sol.SOL('hello')
        s.update({'name': 'value', 'spam': 'eggs'})

        sol.save(s, fp)
        fp.seek(0)

        self.assertFalse(fp.closed)
        self.assertTrue(check_buffer(fp.read(), self.contents))

        fp.close()


class SOLTestCase(unittest.TestCase):
    def test_create(self):
        s = sol.SOL('eggs')

        self.assertEqual(s, {})
        self.assertEqual(s.name, 'eggs')

    @expectedFailureIfAppengine
    def test_save(self):
        s = sol.SOL('hello')
        s.update({'name': 'value', 'spam': 'eggs'})

        x = StringIO()

        s.save(x)

        self.assertTrue(check_buffer(x.getvalue(), HelperTestCase.contents))

        x = tempfile.mkstemp()[1]

        try:
            fp = open(x, 'wb+')

            self.assertEqual(fp.closed, False)

            s.save(fp)
            self.assertNotEquals(fp.tell(), 0)

            fp.seek(0)

            self.assertTrue(check_buffer(fp.read(), HelperTestCase.contents))
            self.assertEqual(fp.closed, False)

            self.assertTrue(check_buffer(open(x, 'rb').read(), HelperTestCase.contents))
        except:
            if os.path.isfile(x):
                os.unlink(x)

            raise

########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF utilities.

@since: 0.1.0
"""

import unittest

from datetime import datetime
from StringIO import StringIO

import pyamf
from pyamf import util
from pyamf.tests.util import replace_dict

PosInf = 1e300000
NegInf = -1e300000
NaN = PosInf / PosInf


def isNaN(val):
    return str(float(val)) == str(NaN)


def isPosInf(val):
    return str(float(val)) == str(PosInf)


def isNegInf(val):
    return str(float(val)) == str(NegInf)


class TimestampTestCase(unittest.TestCase):
    """
    Test UTC timestamps.
    """

    def test_get_timestamp(self):
        self.assertEqual(util.get_timestamp(datetime(2007, 11, 12)), 1194825600)

    def test_get_datetime(self):
        self.assertEqual(util.get_datetime(1194825600), datetime(2007, 11, 12))

    def test_get_negative_datetime(self):
        self.assertEqual(util.get_datetime(-31536000), datetime(1969, 1, 1))

    def test_preserved_microseconds(self):
        dt = datetime(2009, 3, 8, 23, 30, 47, 770122)
        ts = util.get_timestamp(dt)
        self.assertEqual(util.get_datetime(ts), dt)


class StringIOTestCase(unittest.TestCase):

    def test_create(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.getvalue(), '')

        sp = util.BufferedByteStream(None)

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('')

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('spam')

        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), 'spam')
        self.assertEqual(len(sp), 4)

        sp = util.BufferedByteStream(StringIO('this is a test'))
        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), 'this is a test')
        self.assertEqual(len(sp), 14)

        self.assertRaises(TypeError, util.BufferedByteStream, self)

    def test_getvalue(self):
        sp = util.BufferedByteStream()

        sp.write('asdfasdf')
        self.assertEqual(sp.getvalue(), 'asdfasdf')
        sp.write('spam')
        self.assertEqual(sp.getvalue(), 'asdfasdfspam')

    def test_read(self):
        sp = util.BufferedByteStream('this is a test')

        self.assertEqual(len(sp), 14)
        self.assertEqual(sp.read(1), 't')
        self.assertEqual(sp.getvalue(), 'this is a test')
        self.assertEqual(len(sp), 14)
        self.assertEqual(sp.read(10), 'his is a t')
        self.assertEqual(sp.read(), 'est')

    def test_seek(self):
        sp = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.tell(), 0)

        # Relative to the beginning of the stream
        sp.seek(0, 0)
        self.assertEqual(sp.tell(), 0)
        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), 'a')
        self.assertEqual(len(sp), 26)

        sp.seek(10, 0)
        self.assertEqual(sp.tell(), 10)
        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), 'k')
        self.assertEqual(len(sp), 26)

        sp.seek(-5, 1)
        self.assertEqual(sp.tell(), 6)
        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), 'g')
        self.assertEqual(len(sp), 26)

        sp.seek(-3, 2)
        self.assertEqual(sp.tell(), 23)
        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(sp.read(1), 'x')
        self.assertEqual(len(sp), 26)

    def test_tell(self):
        sp = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(len(sp), 26)

        self.assertEqual(sp.tell(), 0)
        sp.read(1)
        self.assertEqual(sp.tell(), 1)

        self.assertEqual(sp.getvalue(), 'abcdefghijklmnopqrstuvwxyz')
        self.assertEqual(len(sp), 26)

        sp.read(5)
        self.assertEqual(sp.tell(), 6)

    def test_truncate(self):
        sp = util.BufferedByteStream('abcdef')

        self.assertEqual(sp.getvalue(), 'abcdef')
        self.assertEqual(len(sp), 6)

        sp.truncate()
        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('hello')

        self.assertEqual(sp.getvalue(), 'hello')
        self.assertEqual(len(sp), 5)

        sp.truncate(3)

        self.assertEqual(sp.getvalue(), 'hel')
        self.assertEqual(len(sp), 3)

    def test_write(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.tell(), 0)

        sp.write('hello')
        self.assertEqual(sp.getvalue(), 'hello')
        self.assertEqual(len(sp), 5)
        self.assertEqual(sp.tell(), 5)

        sp = util.BufferedByteStream('xyz')

        self.assertEqual(sp.getvalue(), 'xyz')
        self.assertEqual(len(sp), 3)
        self.assertEqual(sp.tell(), 0)

        sp.write('abc')
        self.assertEqual(sp.getvalue(), 'abc')
        self.assertEqual(len(sp), 3)
        self.assertEqual(sp.tell(), 3)

    def test_len(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(len(sp), 0)
        self.assertEqual(sp.tell(), 0)

        sp.write('xyz')

        self.assertEqual(len(sp), 3)

        sp = util.BufferedByteStream('foo')

        self.assertEqual(len(sp), 3)

        sp.seek(0, 2)
        sp.write('xyz')

        self.assertEqual(len(sp), 6)

    def test_consume(self):
        sp = util.BufferedByteStream()

        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(sp.tell(), 0)

        sp.consume()

        self.assertEqual(sp.getvalue(), '')
        self.assertEqual(sp.tell(), 0)

        sp = util.BufferedByteStream('foobar')

        self.assertEqual(sp.getvalue(), 'foobar')
        self.assertEqual(sp.tell(), 0)

        sp.seek(3)

        self.assertEqual(sp.tell(), 3)
        sp.consume()

        self.assertEqual(sp.getvalue(), 'bar')
        self.assertEqual(sp.tell(), 0)

        # from ticket 451 - http://pyamf.org/ticket/451
        sp = util.BufferedByteStream('abcdef')
        # move the stream pos to the end
        sp.read()

        self.assertEqual(len(sp), 6)
        sp.consume()
        self.assertEqual(len(sp), 0)

        sp = util.BufferedByteStream('abcdef')
        sp.seek(6)
        sp.consume()
        self.assertEqual(sp.getvalue(), '')


class DataTypeMixInTestCase(unittest.TestCase):
    endians = ('>', '<') # big, little

    def _write_endian(self, obj, func, args, expected):
        old_endian = obj.endian

        for x in range(2):
            obj.truncate()
            obj.endian = self.endians[x]

            func(*args)

            self.assertEqual(obj.getvalue(), expected[x])

        obj.endian = old_endian

    def _read_endian(self, data, func, args, expected):
        for x in range(2):
            obj = util.BufferedByteStream(data[x])
            obj.endian = self.endians[x]

            result = getattr(obj, func)(*args)

            self.assertEqual(result, expected)

    def test_read_uchar(self):
        x = util.BufferedByteStream('\x00\xff')

        self.assertEqual(x.read_uchar(), 0)
        self.assertEqual(x.read_uchar(), 255)

    def test_write_uchar(self):
        x = util.BufferedByteStream()

        x.write_uchar(0)
        self.assertEqual(x.getvalue(), '\x00')
        x.write_uchar(255)
        self.assertEqual(x.getvalue(), '\x00\xff')

        self.assertRaises(OverflowError, x.write_uchar, 256)
        self.assertRaises(OverflowError, x.write_uchar, -1)
        self.assertRaises(TypeError, x.write_uchar, 'f')

    def test_read_char(self):
        x = util.BufferedByteStream('\x00\x7f\xff\x80')

        self.assertEqual(x.read_char(), 0)
        self.assertEqual(x.read_char(), 127)
        self.assertEqual(x.read_char(), -1)
        self.assertEqual(x.read_char(), -128)

    def test_write_char(self):
        x = util.BufferedByteStream()

        x.write_char(0)
        x.write_char(-128)
        x.write_char(127)

        self.assertEqual(x.getvalue(), '\x00\x80\x7f')

        self.assertRaises(OverflowError, x.write_char, 128)
        self.assertRaises(OverflowError, x.write_char, -129)
        self.assertRaises(TypeError, x.write_char, 'f')

    def test_write_ushort(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_ushort, (0,), ('\x00\x00', '\x00\x00'))
        self._write_endian(x, x.write_ushort, (12345,), ('09', '90'))
        self._write_endian(x, x.write_ushort, (65535,), ('\xff\xff', '\xff\xff'))

        self.assertRaises(OverflowError, x.write_ushort, 65536)
        self.assertRaises(OverflowError, x.write_ushort, -1)
        self.assertRaises(TypeError, x.write_ushort, 'aa')

    def test_read_ushort(self):
        self._read_endian(['\x00\x00', '\x00\x00'], 'read_ushort', (), 0)
        self._read_endian(['09', '90'], 'read_ushort', (), 12345)
        self._read_endian(['\xff\xff', '\xff\xff'], 'read_ushort', (), 65535)

    def test_write_short(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_short, (-5673,), ('\xe9\xd7', '\xd7\xe9'))
        self._write_endian(x, x.write_short, (32767,), ('\x7f\xff', '\xff\x7f'))

        self.assertRaises(OverflowError, x.write_ushort, 65537)
        self.assertRaises(OverflowError, x.write_ushort, -1)
        self.assertRaises(TypeError, x.write_short, '\x00\x00')

    def test_read_short(self):
        self._read_endian(['\xe9\xd7', '\xd7\xe9'], 'read_short', (), -5673)
        self._read_endian(['\x7f\xff', '\xff\x7f'], 'read_short', (), 32767)

    def test_write_ulong(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_ulong, (0,), ('\x00\x00\x00\x00', '\x00\x00\x00\x00'))
        self._write_endian(x, x.write_ulong, (16810049,), ('\x01\x00\x80A', 'A\x80\x00\x01'))
        self._write_endian(x, x.write_ulong, (4294967295L,), ('\xff\xff\xff\xff', '\xff\xff\xff\xff'))

        self.assertRaises(OverflowError, x.write_ulong, 4294967296L)
        self.assertRaises(OverflowError, x.write_ulong, -1)
        self.assertRaises(TypeError, x.write_ulong, '\x00\x00\x00\x00')

    def test_read_ulong(self):
        self._read_endian(['\x00\x00\x00\x00', '\x00\x00\x00\x00'], 'read_ulong', (), 0)
        self._read_endian(['\x01\x00\x80A', 'A\x80\x00\x01'], 'read_ulong', (), 16810049)
        self._read_endian(['\xff\xff\xff\xff', '\xff\xff\xff\xff'], 'read_ulong', (), 4294967295L)

    def test_write_long(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_long, (0,), ('\x00\x00\x00\x00', '\x00\x00\x00\x00'))
        self._write_endian(x, x.write_long, (16810049,), ('\x01\x00\x80A', 'A\x80\x00\x01'))
        self._write_endian(x, x.write_long, (2147483647L,), ('\x7f\xff\xff\xff', '\xff\xff\xff\x7f'))
        self._write_endian(x, x.write_long, (-2147483648,), ('\x80\x00\x00\x00', '\x00\x00\x00\x80'))

        self.assertRaises(OverflowError, x.write_long, 2147483648)
        self.assertRaises(OverflowError, x.write_long, -2147483649)
        self.assertRaises(TypeError, x.write_long, '\x00\x00\x00\x00')

    def test_read_long(self):
        self._read_endian(['\xff\xff\xcf\xc7', '\xc7\xcf\xff\xff'], 'read_long', (), -12345)
        self._read_endian(['\x00\x00\x00\x00', '\x00\x00\x00\x00'], 'read_long', (), 0)
        self._read_endian(['\x01\x00\x80A', 'A\x80\x00\x01'], 'read_long', (), 16810049)
        self._read_endian(['\x7f\xff\xff\xff', '\xff\xff\xff\x7f'], 'read_long', (), 2147483647L)

    def test_write_u24bit(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_24bit_uint, (0,), ('\x00\x00\x00', '\x00\x00\x00'))
        self._write_endian(x, x.write_24bit_uint, (4292609,), ('A\x80\x01', '\x01\x80A'))
        self._write_endian(x, x.write_24bit_uint, (16777215,), ('\xff\xff\xff', '\xff\xff\xff'))

        self.assertRaises(OverflowError, x.write_24bit_uint, 16777216)
        self.assertRaises(OverflowError, x.write_24bit_uint, -1)
        self.assertRaises(TypeError, x.write_24bit_uint, '\x00\x00\x00')

    def test_read_u24bit(self):
        self._read_endian(['\x00\x00\x00', '\x00\x00\x00'], 'read_24bit_uint', (), 0)
        self._read_endian(['\x00\x00\x80', '\x80\x00\x00'], 'read_24bit_uint', (), 128)
        self._read_endian(['\x80\x00\x00', '\x00\x00\x80'], 'read_24bit_uint', (), 8388608)
        self._read_endian(['\xff\xff\x7f', '\x7f\xff\xff'], 'read_24bit_uint', (), 16777087)
        self._read_endian(['\x7f\xff\xff', '\xff\xff\x7f'], 'read_24bit_uint', (), 8388607)

    def test_write_24bit(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_24bit_int, (0,), ('\x00\x00\x00', '\x00\x00\x00'))
        self._write_endian(x, x.write_24bit_int, (128,), ('\x00\x00\x80', '\x80\x00\x00'))
        self._write_endian(x, x.write_24bit_int, (8388607,), ('\x7f\xff\xff', '\xff\xff\x7f'))
        self._write_endian(x, x.write_24bit_int, (-1,), ('\xff\xff\xff', '\xff\xff\xff'))
        self._write_endian(x, x.write_24bit_int, (-8388608,), ('\x80\x00\x00', '\x00\x00\x80'))

        self.assertRaises(OverflowError, x.write_24bit_int, 8388608)
        self.assertRaises(OverflowError, x.write_24bit_int, -8388609)
        self.assertRaises(TypeError, x.write_24bit_int, '\x00\x00\x00')

    def test_read_24bit(self):
        self._read_endian(['\x00\x00\x00', '\x00\x00\x00'], 'read_24bit_int', (), 0)
        self._read_endian(['\x00\x00\x80', '\x80\x00\x00'], 'read_24bit_int', (), 128)
        self._read_endian(['\x80\x00\x00', '\x00\x00\x80'], 'read_24bit_int', (), -8388608)
        self._read_endian(['\xff\xff\x7f', '\x7f\xff\xff'], 'read_24bit_int', (), -129)
        self._read_endian(['\x7f\xff\xff', '\xff\xff\x7f'], 'read_24bit_int', (), 8388607)

    def test_write_float(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_float, (0.2,), ('>L\xcc\xcd', '\xcd\xccL>'))
        self.assertRaises(TypeError, x.write_float, 'foo')

    def test_read_float(self):
        self._read_endian(['?\x00\x00\x00', '\x00\x00\x00?'], 'read_float', (), 0.5)

    def test_write_double(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_double, (0.2,), ('?\xc9\x99\x99\x99\x99\x99\x9a', '\x9a\x99\x99\x99\x99\x99\xc9?'))
        self.assertRaises(TypeError, x.write_double, 'foo')

    def test_read_double(self):
        self._read_endian(['?\xc9\x99\x99\x99\x99\x99\x9a', '\x9a\x99\x99\x99\x99\x99\xc9?'], 'read_double', (), 0.2)

    def test_write_utf8_string(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_utf8_string, (u'ᚠᛇᚻ',), ['\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'] * 2)
        self.assertRaises(TypeError, x.write_utf8_string, 1)
        self.assertRaises(TypeError, x.write_utf8_string, 1.0)
        self.assertRaises(TypeError, x.write_utf8_string, object())
        x.write_utf8_string('\xff')

    def test_read_utf8_string(self):
        self._read_endian(['\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb'] * 2, 'read_utf8_string', (9,), u'ᚠᛇᚻ')

    def test_nan(self):
        x = util.BufferedByteStream('\xff\xf8\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isNaN(x.read_double()))

        x = util.BufferedByteStream('\xff\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isNegInf(x.read_double()))

        x = util.BufferedByteStream('\x7f\xf0\x00\x00\x00\x00\x00\x00')
        self.assertTrue(isPosInf(x.read_double()))

        # now test little endian
        x = util.BufferedByteStream('\x00\x00\x00\x00\x00\x00\xf8\xff')
        x.endian = '<'
        self.assertTrue(isNaN(x.read_double()))

        x = util.BufferedByteStream('\x00\x00\x00\x00\x00\x00\xf0\xff')
        x.endian = '<'
        self.assertTrue(isNegInf(x.read_double()))

        x = util.BufferedByteStream('\x00\x00\x00\x00\x00\x00\xf0\x7f')
        x.endian = '<'
        self.assertTrue(isPosInf(x.read_double()))

    def test_write_infinites(self):
        x = util.BufferedByteStream()

        self._write_endian(x, x.write_double, (NaN,), (
            '\xff\xf8\x00\x00\x00\x00\x00\x00',
            '\x00\x00\x00\x00\x00\x00\xf8\xff'
        ))

        self._write_endian(x, x.write_double, (PosInf,), (
            '\x7f\xf0\x00\x00\x00\x00\x00\x00',
            '\x00\x00\x00\x00\x00\x00\xf0\x7f'
        ))

        self._write_endian(x, x.write_double, (NegInf,), (
            '\xff\xf0\x00\x00\x00\x00\x00\x00',
            '\x00\x00\x00\x00\x00\x00\xf0\xff'
        ))


class BufferedByteStreamTestCase(unittest.TestCase):
    """
    Tests for L{BufferedByteStream<util.BufferedByteStream>}
    """

    def test_create(self):
        x = util.BufferedByteStream()

        self.assertEqual(x.getvalue(), '')
        self.assertEqual(x.tell(), 0)

        x = util.BufferedByteStream('abc')

        self.assertEqual(x.getvalue(), 'abc')
        self.assertEqual(x.tell(), 0)

    def test_read(self):
        x = util.BufferedByteStream()

        self.assertEqual(x.tell(), 0)
        self.assertEqual(len(x), 0)
        self.assertRaises(IOError, x.read)

        self.assertRaises(IOError, x.read, 10)

        x.write('hello')
        x.seek(0)
        self.assertRaises(IOError, x.read, 10)
        self.assertEqual(x.read(), 'hello')

    def test_read_negative(self):
        """
        @see: #799
        """
        x = util.BufferedByteStream()

        x.write('*' * 6000)
        x.seek(100)
        self.assertRaises(IOError, x.read, -345)

    def test_peek(self):
        x = util.BufferedByteStream('abcdefghijklmnopqrstuvwxyz')

        self.assertEqual(x.tell(), 0)

        self.assertEqual(x.peek(), 'a')
        self.assertEqual(x.peek(5), 'abcde')
        self.assertEqual(x.peek(-1), 'abcdefghijklmnopqrstuvwxyz')

        x.seek(10)
        self.assertEqual(x.peek(50), 'klmnopqrstuvwxyz')

    def test_eof(self):
        x = util.BufferedByteStream()

        self.assertTrue(x.at_eof())
        x.write('hello')
        x.seek(0)
        self.assertFalse(x.at_eof())
        x.seek(0, 2)
        self.assertTrue(x.at_eof())

    def test_remaining(self):
        x = util.BufferedByteStream('spameggs')

        self.assertEqual(x.tell(), 0)
        self.assertEqual(x.remaining(), 8)

        x.seek(2)
        self.assertEqual(x.tell(), 2)
        self.assertEqual(x.remaining(), 6)

    def test_add(self):
        a = util.BufferedByteStream('a')
        b = util.BufferedByteStream('b')

        c = a + b

        self.assertTrue(isinstance(c, util.BufferedByteStream))
        self.assertEqual(c.getvalue(), 'ab')
        self.assertEqual(c.tell(), 0)

    def test_add_pos(self):
        a = util.BufferedByteStream('abc')
        b = util.BufferedByteStream('def')

        a.seek(1)
        b.seek(0, 2)

        self.assertEqual(a.tell(), 1)
        self.assertEqual(b.tell(), 3)

        self.assertEqual(a.tell(), 1)
        self.assertEqual(b.tell(), 3)

    def test_append_types(self):
        # test non string types
        a = util.BufferedByteStream()

        self.assertRaises(TypeError, a.append, 234234)
        self.assertRaises(TypeError, a.append, 234.0)
        self.assertRaises(TypeError, a.append, 234234L)
        self.assertRaises(TypeError, a.append, [])
        self.assertRaises(TypeError, a.append, {})
        self.assertRaises(TypeError, a.append, lambda _: None)
        self.assertRaises(TypeError, a.append, ())
        self.assertRaises(TypeError, a.append, object())

    def test_append_string(self):
        """
        Test L{util.BufferedByteStream.append} with C{str} objects.
        """
        # test empty
        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), '')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append('foo')

        self.assertEqual(a.getvalue(), 'foo')
        self.assertEqual(a.tell(), 0) # <-- pointer hasn't moved
        self.assertEqual(len(a), 3)

        # test pointer beginning, some data

        a = util.BufferedByteStream('bar')

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 0) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer middle, some data

        a = util.BufferedByteStream('bar')
        a.seek(2)

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 2)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 2) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer end, some data

        a = util.BufferedByteStream('bar')
        a.seek(0, 2)

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 3)
        self.assertEqual(len(a), 3)

        a.append('gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 3) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        class Foo(object):
            def getvalue(self):
                return 'foo'

            def __str__(self):
                raise AttributeError()

        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), '')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append(Foo())

        self.assertEqual(a.getvalue(), 'foo')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

    def test_append_unicode(self):
        """
        Test L{util.BufferedByteStream.append} with C{unicode} objects.
        """
        # test empty
        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), '')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append(u'foo')

        self.assertEqual(a.getvalue(), 'foo')
        self.assertEqual(a.tell(), 0) # <-- pointer hasn't moved
        self.assertEqual(len(a), 3)

        # test pointer beginning, some data

        a = util.BufferedByteStream('bar')

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)

        a.append(u'gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 0) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer middle, some data

        a = util.BufferedByteStream('bar')
        a.seek(2)

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 2)
        self.assertEqual(len(a), 3)

        a.append(u'gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 2) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        # test pointer end, some data

        a = util.BufferedByteStream('bar')
        a.seek(0, 2)

        self.assertEqual(a.getvalue(), 'bar')
        self.assertEqual(a.tell(), 3)
        self.assertEqual(len(a), 3)

        a.append(u'gak')

        self.assertEqual(a.getvalue(), 'bargak')
        self.assertEqual(a.tell(), 3) # <-- pointer hasn't moved
        self.assertEqual(len(a), 6)

        class Foo(object):
            def getvalue(self):
                return u'foo'

            def __str__(self):
                raise AttributeError()

        a = util.BufferedByteStream()

        self.assertEqual(a.getvalue(), '')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 0)

        a.append(Foo())

        self.assertEqual(a.getvalue(), 'foo')
        self.assertEqual(a.tell(), 0)
        self.assertEqual(len(a), 3)



class DummyAlias(pyamf.ClassAlias):
    pass


class AnotherDummyAlias(pyamf.ClassAlias):
    pass


class YADummyAlias(pyamf.ClassAlias):
    pass


class ClassAliasTestCase(unittest.TestCase):
    def setUp(self):
        self.old_aliases = pyamf.ALIAS_TYPES.copy()

    def tearDown(self):
        replace_dict(self.old_aliases, pyamf.ALIAS_TYPES)

    def test_simple(self):
        class A(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertEqual(util.get_class_alias(A), DummyAlias)

    def test_nested(self):
        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        pyamf.register_alias_type(DummyAlias, A, B, C)

        self.assertEqual(util.get_class_alias(B), DummyAlias)

    def test_multiple(self):
        class A(object):
            pass

        class B(object):
            pass

        class C(object):
            pass

        pyamf.register_alias_type(DummyAlias, A)
        pyamf.register_alias_type(AnotherDummyAlias, B)
        pyamf.register_alias_type(YADummyAlias, C)

        self.assertEqual(util.get_class_alias(B), AnotherDummyAlias)
        self.assertEqual(util.get_class_alias(C), YADummyAlias)
        self.assertEqual(util.get_class_alias(A), DummyAlias)

    def test_none_existant(self):
        self.assertEqual(util.get_class_alias(self.__class__), None)

    def test_subclass(self):
        class A(object):
            pass

        class B(A):
            pass

        pyamf.register_alias_type(DummyAlias, A)

        self.assertEqual(util.get_class_alias(B), DummyAlias)


class IsClassSealedTestCase(unittest.TestCase):
    """
    Tests for L{util.is_class_sealed}
    """

    def test_new_mixed(self):
        class A(object):
            __slots__ = ['foo', 'bar']

        class B(A):
            pass

        class C(B):
            __slots__ = ('spam', 'eggs')

        self.assertTrue(util.is_class_sealed(A))
        self.assertFalse(util.is_class_sealed(B))
        self.assertFalse(util.is_class_sealed(C))

    def test_deep(self):
        class A(object):
            __slots__ = ['foo', 'bar']

        class B(A):
            __slots__ = ('gak',)

        class C(B):
            pass

        self.assertTrue(util.is_class_sealed(A))
        self.assertTrue(util.is_class_sealed(B))
        self.assertFalse(util.is_class_sealed(C))


class GetClassMetaTestCase(unittest.TestCase):
    """
    Tests for L{util.get_class_meta}
    """

    def test_types(self):
        class A:
            pass

        class B(object):
            pass

        for t in ['', u'', 1, 1.0, 1L, [], {}, object, object(), A(), B()]:
            self.assertRaises(TypeError, util.get_class_meta, t)

    def test_no_meta(self):
        class A:
            pass

        class B(object):
            pass

        empty = {
            'readonly_attrs': None,
            'static_attrs': None,
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'exclude_attrs': None,
            'proxy_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), empty)
        self.assertEqual(util.get_class_meta(B), empty)

    def test_alias(self):
        class A:
            class __amf__:
                alias = 'foo.bar.Spam'

        class B(object):
            class __amf__:
                alias = 'foo.bar.Spam'

        meta = {
            'readonly_attrs': None,
            'static_attrs': None,
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': 'foo.bar.Spam',
            'amf3': None,
            'proxy_attrs': None,
            'exclude_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_static(self):
        class A:
            class __amf__:
                static = ['foo', 'bar']

        class B(object):
            class __amf__:
                static = ['foo', 'bar']

        meta = {
            'readonly_attrs': None,
            'static_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'exclude_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_exclude(self):
        class A:
            class __amf__:
                exclude = ['foo', 'bar']

        class B(object):
            class __amf__:
                exclude = ['foo', 'bar']

        meta = {
            'readonly_attrs': None,
            'exclude_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'proxy_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_readonly(self):
        class A:
            class __amf__:
                readonly = ['foo', 'bar']

        class B(object):
            class __amf__:
                readonly = ['foo', 'bar']

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None,
            'proxy_attrs': None,
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_amf3(self):
        class A:
            class __amf__:
                amf3 = True

        class B(object):
            class __amf__:
                amf3 = True

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': True,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_dynamic(self):
        class A:
            class __amf__:
                dynamic = False

        class B(object):
            class __amf__:
                dynamic = False

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': False,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_external(self):
        class A:
            class __amf__:
                external = True

        class B(object):
            class __amf__:
                external = True

        meta = {
            'exclude_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': True
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_dict(self):
        meta = {
            'exclude': ['foo'],
            'readonly': ['bar'],
            'dynamic': False,
            'alias': 'spam.eggs',
            'proxy_attrs': None,
            'synonym_attrs': None,
            'amf3': True,
            'static': ['baz'],
            'external': True
        }

        class A:
            __amf__ = meta

        class B(object):
            __amf__ = meta

        ret = {
            'readonly_attrs': ['bar'],
            'static_attrs': ['baz'],
            'proxy_attrs': None,
            'dynamic': False,
            'alias': 'spam.eggs',
            'amf3': True,
            'exclude_attrs': ['foo'],
            'synonym_attrs': None,
            'proxy_attrs': None,
            'external': True
        }

        self.assertEqual(util.get_class_meta(A), ret)
        self.assertEqual(util.get_class_meta(B), ret)

    def test_proxy(self):
        class A:
            class __amf__:
                proxy = ['foo', 'bar']

        class B(object):
            class __amf__:
                proxy = ['foo', 'bar']

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': ['foo', 'bar'],
            'synonym_attrs': None,
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)

    def test_synonym(self):
        class A:
            class __amf__:
                synonym = {'foo': 'bar'}

        class B(object):
            class __amf__:
                synonym = {'foo': 'bar'}

        meta = {
            'exclude_attrs': None,
            'readonly_attrs': None,
            'proxy_attrs': None,
            'synonym_attrs': {'foo': 'bar'},
            'dynamic': None,
            'alias': None,
            'amf3': None,
            'static_attrs': None,
            'external': None
        }

        self.assertEqual(util.get_class_meta(A), meta)
        self.assertEqual(util.get_class_meta(B), meta)


########NEW FILE########
__FILENAME__ = test_versions
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for L{pyamf.version}
"""

import unittest

from pyamf import versions


class VersionTestCase(unittest.TestCase):
    """
    Tests for L{pyamf.version.get_version}
    """

    def test_version(self):
        self.assertEqual(versions.get_version((0, 0)), '0.0')
        self.assertEqual(versions.get_version((0, 1)), '0.1')
        self.assertEqual(versions.get_version((3, 2)), '3.2')
        self.assertEqual(versions.get_version((3, 2, 1)), '3.2.1')

        self.assertEqual(versions.get_version((3, 2, 1, 'alpha')), '3.2.1alpha')

        self.assertEqual(versions.get_version((3, 2, 1, 'final')), '3.2.1final')

    def test_class(self):
        V = versions.Version

        v1 = V(0, 1)

        self.assertEqual(v1, (0, 1))
        self.assertEqual(str(v1), '0.1')

        v2 = V(3, 2, 1, 'final')

        self.assertEqual(v2, (3, 2, 1, 'final'))
        self.assertEqual(str(v2), '3.2.1final')

        self.assertTrue(v2 > v1)

########NEW FILE########
__FILENAME__ = test_xml
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for XML library integration

@since: 0.4
"""

import unittest

import pyamf.xml
from pyamf import util


class ElementTreeTestCase(unittest.TestCase):
    """
    Tests the type mappings.
    """

    xml = '<foo bar="baz" />'

    def check_amf0(self, bytes, xml):
        b = util.BufferedByteStream(bytes)

        self.assertEqual(b.read_char(), 15)

        l = b.read_ulong()

        self.assertEqual(l, b.remaining())
        self.assertEqual(b.read(), xml)

    def check_amf3(self, bytes, xml):
        b = util.BufferedByteStream(bytes)

        self.assertEqual(b.read_char(), 11)

        l = b.read_uchar()

        self.assertEqual(l >> 1, b.remaining())
        self.assertEqual(b.read(), xml)


for mod in pyamf.xml.ETREE_MODULES:
    name = 'test_' + mod.replace('.', '_')

    def check_etree(self):
        # holy hack batman
        import inspect

        mod = inspect.stack()[1][0].f_locals['testMethod'].__name__[5:]
        mod = mod.replace('_', '.')

        try:
            etree = util.get_module(mod)
        except ImportError:
            self.skipTest('%r is not available' % (mod,))

        element = etree.fromstring(self.xml)
        xml = etree.tostring(element)

        old = pyamf.set_default_etree(etree)

        if old:
            self.addCleanup(lambda x: pyamf.set_default_etree(x), old)

        bytes = pyamf.encode(element, encoding=pyamf.AMF0).getvalue()
        self.check_amf0(bytes, xml)

        new_element = pyamf.decode(bytes, encoding=pyamf.AMF0).next()
        self.assertIdentical(type(element), type(new_element))

        bytes = pyamf.encode(element, encoding=pyamf.AMF3).getvalue()
        self.check_amf3(bytes, xml)

        new_element = pyamf.decode(bytes, encoding=pyamf.AMF3).next()
        self.assertIdentical(type(element), type(new_element))

    check_etree.__name__ = name

    setattr(ElementTreeTestCase, name, check_etree)


########NEW FILE########
__FILENAME__ = util
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Test utilities.

@since: 0.1.0
"""

import unittest
import copy

import pyamf
from pyamf import python


class ClassicSpam:
    def __readamf__(self, input):
        pass

    def __writeamf__(self, output):
        pass


class Spam(object):
    """
    A generic object to use for object encoding.
    """

    def __init__(self, d={}):
        self.__dict__.update(d)

    def __readamf__(self, input):
        pass

    def __writeamf__(self, output):
        pass


class EncoderMixIn(object):
    """
    A mixin class that provides an AMF* encoder and some helpful methods to do
    testing.
    """

    amf_type = None

    def setUp(self):
        self.encoder = pyamf.get_encoder(encoding=self.amf_type)
        self.buf = self.encoder.stream
        self.context = self.encoder.context

    def tearDown(self):
        pass

    def encode(self, *args):
        self.buf.seek(0, 0)
        self.buf.truncate()

        for arg in args:
            self.encoder.writeElement(arg)

        return self.buf.getvalue()

    def assertEncoded(self, arg, *args, **kwargs):
        if kwargs.get('clear', True):
            self.context.clear()

        assert_buffer(self, self.encode(arg), args)


class DecoderMixIn(object):
    """
    A mixin class that provides an AMF* decoder and some helpful methods to do
    testing.
    """

    amf_type = None

    def setUp(self):
        self.decoder = pyamf.get_decoder(encoding=self.amf_type)
        self.buf = self.decoder.stream
        self.context = self.decoder.context

    def tearDown(self):
        pass

    def decode(self, bytes, raw=False):
        if not isinstance(bytes, basestring):
            bytes = _join(bytes)

        self.buf.seek(0, 0)
        self.buf.truncate()

        self.buf.write(bytes)
        self.buf.seek(0, 0)

        ret = []

        while not self.buf.at_eof():
            ret.append(self.decoder.readElement())

        if raw:
            return ret

        if len(ret) == 1:
            return ret[0]

        return ret

    def assertDecoded(self, decoded, bytes, raw=False, clear=True):
        if clear:
            self.context.clear()

        ret = self.decode(bytes, raw)

        self.assertEqual(ret, decoded)
        self.assertEqual(self.buf.remaining(), 0)


class ClassCacheClearingTestCase(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)

        self._class_cache = pyamf.CLASS_CACHE.copy()
        self._class_loaders = copy.copy(pyamf.CLASS_LOADERS)

    def tearDown(self):
        unittest.TestCase.tearDown(self)

        pyamf.CLASS_CACHE = self._class_cache
        pyamf.CLASS_LOADERS = self._class_loaders

    def assertBuffer(self, first, second, msg=None):
        assert_buffer(self, first, second, msg)

    def assertEncodes(self, obj, buffer, encoding=pyamf.AMF3):
        bytes = pyamf.encode(obj, encoding=encoding).getvalue()

        if isinstance(buffer, basestring):
            self.assertEqual(bytes, buffer)

            return

        self.assertBuffer(bytes, buffer)

    def assertDecodes(self, bytes, cb, encoding=pyamf.AMF3, raw=False):
        if not isinstance(bytes, basestring):
            bytes = _join(bytes)

        ret = list(pyamf.decode(bytes, encoding=encoding))

        if not raw and len(ret) == 1:
            ret = ret[0]

        if python.callable(cb):
            cb(ret)
        else:
            self.assertEqual(ret, cb)


def assert_buffer(testcase, val, s, msg=None):
    if not check_buffer(val, s):
        testcase.fail(msg or ('%r != %r' % (val, s)))


def check_buffer(buf, parts, inner=False):
    assert isinstance(parts, (tuple, list))

    parts = [p for p in parts]

    for part in parts:
        if inner is False:
            if isinstance(part, (tuple, list)):
                buf = check_buffer(buf, part, inner=True)
            else:
                if not buf.startswith(part):
                    return False

                buf = buf[len(part):]
        else:
            for k in parts[:]:
                for p in parts[:]:
                    if isinstance(p, (tuple, list)):
                        buf = check_buffer(buf, p, inner=True)
                    else:
                        if buf.startswith(p):
                            parts.remove(p)
                            buf = buf[len(p):]

            return buf

    return len(buf) == 0


def replace_dict(src, dest):
    seen = []

    for name in dest.copy().keys():
        seen.append(name)

        if name not in src:
            del dest[name]

            continue

        if dest[name] is not src[name]:
            dest[name] = src[name]

    for name in src.keys():
        if name in seen:
            continue

        dest[name] = src[name]

    assert src == dest


class NullFileDescriptor(object):
    """
    A file like object that no-ops when writing.
    """

    def write(self, *args, **kwargs):
        pass


def get_fqcn(klass):
    return '%s.%s' % (klass.__module__, klass.__name__)


def expectedFailureIfAppengine(func):
    try:
        from google import appengine
    except ImportError:
        return func
    else:
        import os

        if os.environ.get('SERVER_SOFTWARE', None) is None:
            return func

        return unittest.expectedFailure(func)


def _join(parts):
    ret = ''

    for p in parts:
        if not isinstance(p, basestring):
            ret += _join(p)

            continue

        ret += p

    return ret

########NEW FILE########
__FILENAME__ = imports
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Tools for doing dynamic imports.

@since: 0.3
"""

import sys


__all__ = ['when_imported']


def when_imported(name, *hooks):
    """
    Call C{hook(module)} when module named C{name} is first imported. C{name}
    must be a fully qualified (i.e. absolute) module name.

    C{hook} must accept one argument: which will be the imported module object.

    If the module has already been imported, 'hook(module)' is called
    immediately, and the module object is returned from this function. If the
    module has not been imported, then the hook is called when the module is
    first imported.
    """
    global finder

    finder.when_imported(name, *hooks)


class ModuleFinder(object):
    """
    This is a special module finder object that executes a collection of
    callables when a specific module has been imported. An instance of this
    is placed in C{sys.meta_path}, which is consulted before C{sys.modules} -
    allowing us to provide this functionality.

    @ivar post_load_hooks: C{dict} of C{full module path -> callable} to be
        executed when the module is imported.
    @ivar loaded_modules: C{list} of modules that this finder has seen. Used
        to stop recursive imports in L{load_module}
    @see: L{when_imported}
    @since: 0.5
    """

    def __init__(self):
        self.post_load_hooks = {}
        self.loaded_modules = []

    def find_module(self, name, path=None):
        """
        Called when an import is made. If there are hooks waiting for this
        module to be imported then we stop the normal import process and
        manually load the module.

        @param name: The name of the module being imported.
        @param path The root path of the module (if a package). We ignore this.
        @return: If we want to hook this module, we return a C{loader}
            interface (which is this instance again). If not we return C{None}
            to allow the standard import process to continue.
        """
        if name in self.loaded_modules:
            return None

        hooks = self.post_load_hooks.get(name, None)

        if hooks:
            return self

    def load_module(self, name):
        """
        If we get this far, then there are hooks waiting to be called on
        import of this module. We manually load the module and then run the
        hooks.

        @param name: The name of the module to import.
        """
        self.loaded_modules.append(name)

        try:
            __import__(name, {}, {}, [])

            mod = sys.modules[name]
            self._run_hooks(name, mod)
        except:
            self.loaded_modules.pop()

            raise

        return mod

    def when_imported(self, name, *hooks):
        """
        @see: L{when_imported}
        """
        if name in sys.modules:
            for hook in hooks:
                hook(sys.modules[name])

            return

        h = self.post_load_hooks.setdefault(name, [])
        h.extend(hooks)

    def _run_hooks(self, name, module):
        """
        Run all hooks for a module.
        """
        hooks = self.post_load_hooks.pop(name, [])

        for hook in hooks:
            hook(module)

    def __getstate__(self):
        return (self.post_load_hooks.copy(), self.loaded_modules[:])

    def __setstate__(self, state):
        self.post_load_hooks, self.loaded_modules = state


def _init():
    """
    Internal function to install the module finder.
    """
    global finder

    if finder is None:
        finder = ModuleFinder()

    if finder not in sys.meta_path:
        sys.meta_path.insert(0, finder)


finder = None
_init()

########NEW FILE########
__FILENAME__ = pure
# -*- coding: utf-8 -*-
#
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Provides the pure Python versions of L{BufferedByteStream}.

Do not reference directly, use L{pyamf.util.BufferedByteStream} instead.

@since: 0.6
"""

import struct

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from pyamf import python

# worked out a little further down
SYSTEM_ENDIAN = None


class StringIOProxy(object):
    """
    I am a C{StringIO} type object containing byte data from the AMF stream.

    @see: U{ByteArray on OSFlash
        <http://osflash.org/documentation/amf3#x0c_-_bytearray>}
    @see: U{Parsing ByteArrays on OSFlash
        <http://osflash.org/documentation/amf3/parsing_byte_arrays>}
    """

    def __init__(self, buf=None):
        """
        @raise TypeError: Unable to coerce C{buf} to C{StringIO}.
        """
        self._buffer = StringIO()

        if isinstance(buf, python.str_types):
            self._buffer.write(buf)
        elif hasattr(buf, 'getvalue'):
            self._buffer.write(buf.getvalue())
        elif hasattr(buf, 'read') and hasattr(buf, 'seek') and hasattr(buf, 'tell'):
            old_pos = buf.tell()
            buf.seek(0)
            self._buffer.write(buf.read())
            buf.seek(old_pos)
        elif buf is not None:
            raise TypeError("Unable to coerce buf->StringIO got %r" % (buf,))

        self._get_len()
        self._len_changed = False
        self._buffer.seek(0, 0)

    def getvalue(self):
        """
        Get raw data from buffer.
        """
        return self._buffer.getvalue()

    def read(self, n=-1):
        """
        Reads C{n} bytes from the stream.
        """
        if n < -1:
            raise IOError('Cannot read backwards')

        bytes = self._buffer.read(n)

        return bytes

    def seek(self, pos, mode=0):
        """
        Sets the file-pointer offset, measured from the beginning of this stream,
        at which the next write operation will occur.

        @param pos:
        @type pos: C{int}
        @param mode:
        @type mode: C{int}
        """
        return self._buffer.seek(pos, mode)

    def tell(self):
        """
        Returns the position of the stream pointer.
        """
        return self._buffer.tell()

    def truncate(self, size=0):
        """
        Truncates the stream to the specified length.

        @param size: The length of the stream, in bytes.
        @type size: C{int}
        """
        if size == 0:
            self._buffer = StringIO()
            self._len_changed = True

            return

        cur_pos = self.tell()
        self.seek(0)
        buf = self.read(size)
        self._buffer = StringIO()

        self._buffer.write(buf)
        self.seek(cur_pos)
        self._len_changed = True

    def write(self, s, size=None):
        """
        Writes the content of the specified C{s} into this buffer.

        @param s: Raw bytes
        """
        self._buffer.write(s)
        self._len_changed = True

    def _get_len(self):
        """
        Return total number of bytes in buffer.
        """
        if hasattr(self._buffer, 'len'):
            self._len = self._buffer.len

            return

        old_pos = self._buffer.tell()
        self._buffer.seek(0, 2)

        self._len = self._buffer.tell()
        self._buffer.seek(old_pos)

    def __len__(self):
        if not self._len_changed:
            return self._len

        self._get_len()
        self._len_changed = False

        return self._len

    def consume(self):
        """
        Chops the tail off the stream starting at 0 and ending at C{tell()}.
        The stream pointer is set to 0 at the end of this function.

        @since: 0.4
        """
        try:
            bytes = self.read()
        except IOError:
            bytes = ''

        self.truncate()

        if len(bytes) > 0:
            self.write(bytes)
            self.seek(0)


class DataTypeMixIn(object):
    """
    Provides methods for reading and writing basic data types for file-like
    objects.

    @ivar endian: Byte ordering used to represent the data. Default byte order
        is L{ENDIAN_NETWORK}.
    @type endian: C{str}
    """

    #: Network byte order
    ENDIAN_NETWORK = "!"

    #: Native byte order
    ENDIAN_NATIVE = "@"

    #: Little endian
    ENDIAN_LITTLE = "<"

    #: Big endian
    ENDIAN_BIG = ">"

    endian = ENDIAN_NETWORK

    def _read(self, length):
        """
        Reads C{length} bytes from the stream. If an attempt to read past the
        end of the buffer is made, L{IOError} is raised.
        """
        bytes = self.read(length)

        if len(bytes) != length:
            self.seek(0 - len(bytes), 1)

            raise IOError("Tried to read %d byte(s) from the stream" % length)

        return bytes

    def _is_big_endian(self):
        """
        Whether the current endian is big endian.
        """
        if self.endian == DataTypeMixIn.ENDIAN_NATIVE:
            return SYSTEM_ENDIAN == DataTypeMixIn.ENDIAN_BIG

        return self.endian in (DataTypeMixIn.ENDIAN_BIG, DataTypeMixIn.ENDIAN_NETWORK)

    def read_uchar(self):
        """
        Reads an C{unsigned char} from the stream.
        """
        return ord(self._read(1))

    def write_uchar(self, c):
        """
        Writes an C{unsigned char} to the stream.

        @param c: Unsigned char
        @type c: C{int}
        @raise TypeError: Unexpected type for int C{c}.
        @raise OverflowError: Not in range.
        """
        if type(c) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % type(c))

        if not 0 <= c <= 255:
            raise OverflowError("Not in range, %d" % c)

        self.write(struct.pack("B", c))

    def read_char(self):
        """
        Reads a C{char} from the stream.
        """
        return struct.unpack("b", self._read(1))[0]

    def write_char(self, c):
        """
        Write a C{char} to the stream.

        @param c: char
        @type c: C{int}
        @raise TypeError: Unexpected type for int C{c}.
        @raise OverflowError: Not in range.
        """
        if type(c) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % type(c))

        if not -128 <= c <= 127:
            raise OverflowError("Not in range, %d" % c)

        self.write(struct.pack("b", c))

    def read_ushort(self):
        """
        Reads a 2 byte unsigned integer from the stream.
        """
        return struct.unpack("%sH" % self.endian, self._read(2))[0]

    def write_ushort(self, s):
        """
        Writes a 2 byte unsigned integer to the stream.

        @param s: 2 byte unsigned integer
        @type s: C{int}
        @raise TypeError: Unexpected type for int C{s}.
        @raise OverflowError: Not in range.
        """
        if type(s) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(s),))

        if not 0 <= s <= 65535:
            raise OverflowError("Not in range, %d" % s)

        self.write(struct.pack("%sH" % self.endian, s))

    def read_short(self):
        """
        Reads a 2 byte integer from the stream.
        """
        return struct.unpack("%sh" % self.endian, self._read(2))[0]

    def write_short(self, s):
        """
        Writes a 2 byte integer to the stream.

        @param s: 2 byte integer
        @type s: C{int}
        @raise TypeError: Unexpected type for int C{s}.
        @raise OverflowError: Not in range.
        """
        if type(s) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(s),))

        if not -32768 <= s <= 32767:
            raise OverflowError("Not in range, %d" % s)

        self.write(struct.pack("%sh" % self.endian, s))

    def read_ulong(self):
        """
        Reads a 4 byte unsigned integer from the stream.
        """
        return struct.unpack("%sL" % self.endian, self._read(4))[0]

    def write_ulong(self, l):
        """
        Writes a 4 byte unsigned integer to the stream.

        @param l: 4 byte unsigned integer
        @type l: C{int}
        @raise TypeError: Unexpected type for int C{l}.
        @raise OverflowError: Not in range.
        """
        if type(l) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(l),))

        if not 0 <= l <= 4294967295:
            raise OverflowError("Not in range, %d" % l)

        self.write(struct.pack("%sL" % self.endian, l))

    def read_long(self):
        """
        Reads a 4 byte integer from the stream.
        """
        return struct.unpack("%sl" % self.endian, self._read(4))[0]

    def write_long(self, l):
        """
        Writes a 4 byte integer to the stream.

        @param l: 4 byte integer
        @type l: C{int}
        @raise TypeError: Unexpected type for int C{l}.
        @raise OverflowError: Not in range.
        """
        if type(l) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(l),))

        if not -2147483648 <= l <= 2147483647:
            raise OverflowError("Not in range, %d" % l)

        self.write(struct.pack("%sl" % self.endian, l))

    def read_24bit_uint(self):
        """
        Reads a 24 bit unsigned integer from the stream.

        @since: 0.4
        """
        order = None

        if not self._is_big_endian():
            order = [0, 8, 16]
        else:
            order = [16, 8, 0]

        n = 0

        for x in order:
            n += (self.read_uchar() << x)

        return n

    def write_24bit_uint(self, n):
        """
        Writes a 24 bit unsigned integer to the stream.

        @since: 0.4
        @param n: 24 bit unsigned integer
        @type n: C{int}
        @raise TypeError: Unexpected type for int C{n}.
        @raise OverflowError: Not in range.
        """
        if type(n) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(n),))

        if not 0 <= n <= 0xffffff:
            raise OverflowError("n is out of range")

        order = None

        if not self._is_big_endian():
            order = [0, 8, 16]
        else:
            order = [16, 8, 0]

        for x in order:
            self.write_uchar((n >> x) & 0xff)

    def read_24bit_int(self):
        """
        Reads a 24 bit integer from the stream.

        @since: 0.4
        """
        n = self.read_24bit_uint()

        if n & 0x800000 != 0:
            # the int is signed
            n -= 0x1000000

        return n

    def write_24bit_int(self, n):
        """
        Writes a 24 bit integer to the stream.

        @since: 0.4
        @param n: 24 bit integer
        @type n: C{int}
        @raise TypeError: Unexpected type for int C{n}.
        @raise OverflowError: Not in range.
        """
        if type(n) not in python.int_types:
            raise TypeError('expected an int (got:%r)' % (type(n),))

        if not -8388608 <= n <= 8388607:
            raise OverflowError("n is out of range")

        order = None

        if not self._is_big_endian():
            order = [0, 8, 16]
        else:
            order = [16, 8, 0]

        if n < 0:
            n += 0x1000000

        for x in order:
            self.write_uchar((n >> x) & 0xff)

    def read_double(self):
        """
        Reads an 8 byte float from the stream.
        """
        return struct.unpack("%sd" % self.endian, self._read(8))[0]

    def write_double(self, d):
        """
        Writes an 8 byte float to the stream.

        @param d: 8 byte float
        @type d: C{float}
        @raise TypeError: Unexpected type for float C{d}.
        """
        if not type(d) is float:
            raise TypeError('expected a float (got:%r)' % (type(d),))

        self.write(struct.pack("%sd" % self.endian, d))

    def read_float(self):
        """
        Reads a 4 byte float from the stream.
        """
        return struct.unpack("%sf" % self.endian, self._read(4))[0]

    def write_float(self, f):
        """
        Writes a 4 byte float to the stream.

        @param f: 4 byte float
        @type f: C{float}
        @raise TypeError: Unexpected type for float C{f}.
        """
        if type(f) is not float:
            raise TypeError('expected a float (got:%r)' % (type(f),))

        self.write(struct.pack("%sf" % self.endian, f))

    def read_utf8_string(self, length):
        """
        Reads a UTF-8 string from the stream.

        @rtype: C{unicode}
        """
        s = struct.unpack("%s%ds" % (self.endian, length), self.read(length))[0]

        return s.decode('utf-8')

    def write_utf8_string(self, u):
        """
        Writes a unicode object to the stream in UTF-8.

        @param u: unicode object
        @raise TypeError: Unexpected type for str C{u}.
        """
        if not isinstance(u, python.str_types):
            raise TypeError('Expected %r, got %r' % (python.str_types, u))

        bytes = u

        if isinstance(bytes, unicode):
            bytes = u.encode("utf8")

        self.write(struct.pack("%s%ds" % (self.endian, len(bytes)), bytes))


class BufferedByteStream(StringIOProxy, DataTypeMixIn):
    """
    An extension of C{StringIO}.

    Features:
     - Raises L{IOError} if reading past end.
     - Allows you to C{peek()} into the stream.
    """

    def __init__(self, buf=None, min_buf_size=None):
        """
        @param buf: Initial byte stream.
        @type buf: C{str} or C{StringIO} instance
        @param min_buf_size: Ignored in the pure Python version.
        """
        StringIOProxy.__init__(self, buf=buf)

    def read(self, length=-1):
        """
        Reads up to the specified number of bytes from the stream into
        the specified byte array of specified length.

        @raise IOError: Attempted to read past the end of the buffer.
        """
        if length == -1 and self.at_eof():
            raise IOError(
                'Attempted to read from the buffer but already at the end')
        elif length > 0 and self.tell() + length > len(self):
            raise IOError('Attempted to read %d bytes from the buffer but '
                'only %d remain' % (length, len(self) - self.tell()))

        return StringIOProxy.read(self, length)

    def peek(self, size=1):
        """
        Looks C{size} bytes ahead in the stream, returning what it finds,
        returning the stream pointer to its initial position.

        @param size: Default is 1.
        @type size: C{int}
        @raise ValueError: Trying to peek backwards.

        @return: Bytes.
        """
        if size == -1:
            return self.peek(len(self) - self.tell())

        if size < -1:
            raise ValueError("Cannot peek backwards")

        bytes = ''
        pos = self.tell()

        while not self.at_eof() and len(bytes) != size:
            bytes += self.read(1)

        self.seek(pos)

        return bytes

    def remaining(self):
        """
        Returns number of remaining bytes.

        @rtype: C{number}
        @return: Number of remaining bytes.
        """
        return len(self) - self.tell()

    def at_eof(self):
        """
        Returns C{True} if the internal pointer is at the end of the stream.

        @rtype: C{bool}
        """
        return self.tell() == len(self)

    def append(self, data):
        """
        Append data to the end of the stream. The pointer will not move if
        this operation is successful.

        @param data: The data to append to the stream.
        @type data: C{str} or C{unicode}
        @raise TypeError: data is not C{str} or C{unicode}
        """
        t = self.tell()

        # seek to the end of the stream
        self.seek(0, 2)

        if hasattr(data, 'getvalue'):
            self.write_utf8_string(data.getvalue())
        else:
            self.write_utf8_string(data)

        self.seek(t)

    def __add__(self, other):
        old_pos = self.tell()
        old_other_pos = other.tell()

        new = BufferedByteStream(self)

        other.seek(0)
        new.seek(0, 2)
        new.write(other.read())

        self.seek(old_pos)
        other.seek(old_other_pos)
        new.seek(0)

        return new


def is_float_broken():
    """
    Older versions of Python (<=2.5) and the Windows platform are renowned for
    mixing up 'special' floats. This function determines whether this is the
    case.

    @since: 0.4
    @rtype: C{bool}
    @return: Boolean indicating whether floats are broken on this platform.
    """
    return str(python.NaN) != str(
        struct.unpack("!d", '\xff\xf8\x00\x00\x00\x00\x00\x00')[0])


# init the module from here ..

if is_float_broken():
    def read_double_workaround(self):
        """
        Override the L{DataTypeMixIn.read_double} method to fix problems
        with doubles by using the third-party C{fpconst} library.
        """
        bytes = self.read(8)

        if self._is_big_endian():
            if bytes == '\xff\xf8\x00\x00\x00\x00\x00\x00':
                return python.NaN

            if bytes == '\xff\xf0\x00\x00\x00\x00\x00\x00':
                return python.NegInf

            if bytes == '\x7f\xf0\x00\x00\x00\x00\x00\x00':
                return python.PosInf
        else:
            if bytes == '\x00\x00\x00\x00\x00\x00\xf8\xff':
                return python.NaN

            if bytes == '\x00\x00\x00\x00\x00\x00\xf0\xff':
                return python.NegInf

            if bytes == '\x00\x00\x00\x00\x00\x00\xf0\x7f':
                return python.PosInf

        return struct.unpack("%sd" % self.endian, bytes)[0]

    DataTypeMixIn.read_double = read_double_workaround

    def write_double_workaround(self, d):
        """
        Override the L{DataTypeMixIn.write_double} method to fix problems
        with doubles by using the third-party C{fpconst} library.

        @raise TypeError: Unexpected type for float C{d}.
        """
        if type(d) is not float:
            raise TypeError('expected a float (got:%r)' % (type(d),))

        if python.isNaN(d):
            if self._is_big_endian():
                self.write('\xff\xf8\x00\x00\x00\x00\x00\x00')
            else:
                self.write('\x00\x00\x00\x00\x00\x00\xf8\xff')
        elif python.isNegInf(d):
            if self._is_big_endian():
                self.write('\xff\xf0\x00\x00\x00\x00\x00\x00')
            else:
                self.write('\x00\x00\x00\x00\x00\x00\xf0\xff')
        elif python.isPosInf(d):
            if self._is_big_endian():
                self.write('\x7f\xf0\x00\x00\x00\x00\x00\x00')
            else:
                self.write('\x00\x00\x00\x00\x00\x00\xf0\x7f')
        else:
            write_double_workaround.old_func(self, d)

    x = DataTypeMixIn.write_double
    DataTypeMixIn.write_double = write_double_workaround
    write_double_workaround.old_func = x


if struct.pack('@H', 1)[0] == '\x01':
    SYSTEM_ENDIAN = DataTypeMixIn.ENDIAN_LITTLE
else:
    SYSTEM_ENDIAN = DataTypeMixIn.ENDIAN_BIG

########NEW FILE########
__FILENAME__ = versions
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Because there is disparity between Python packaging (and it is being sorted
out ...) we currently provide our own way to get the string of a version tuple.

@since: 0.6
"""


class Version(tuple):

    _version = None

    def __new__(cls, *args):
        x = tuple.__new__(cls, args)

        return x

    def __str__(self):
        if not self._version:
            self._version = get_version(self)

        return self._version


def get_version(_version):
    v = ''
    prev = None

    for x in _version:
        if prev is not None:
            if isinstance(x, int):
                v += '.'

        prev = x
        v += str(x)

    return v.strip('.')

########NEW FILE########
__FILENAME__ = xml
# Copyright (c) The PyAMF Project.
# See LICENSE.txt for details.

"""
Provides XML support.

@since: 0.6
"""

#: list of supported third party packages that support the C{etree}
#: interface. At least enough for our needs anyway.
ETREE_MODULES = [
    'lxml.etree',
    'xml.etree.cElementTree',
    'cElementTree',
    'xml.etree.ElementTree',
    'elementtree.ElementTree'
]

#: A tuple of class/type objects that are used to represent XML objects.
types = None
#: A mapping of type -> module for all known xml types.
modules = {}
#: The module that will be used to create C{ElementTree} instances.
ET = None

__all__ = ['set_default_interface']


def set_default_interface(etree):
    """
    Sets the default interface that PyAMF will use to deal with XML entities
    (both objects and blobs).
    """
    global types, ET, modules

    t = _get_etree_type(etree)

    _types = set(types or [])
    _types.update([t])

    types = tuple(_types)

    modules[t] = etree

    old, ET = ET, etree

    return old


def find_libs():
    """
    Run through L{ETREE_MODULES} and find C{ElementTree} implementations so
    that any type can be encoded.

    We work through the C implementations first, then the pure Python versions.
    The downside to this is that B{all} libraries will be imported but I{only}
    one is ever used. The libs are small (relatively) and the flexibility that
    this gives seems to outweigh the cost. Time will tell.
    """
    from pyamf.util import get_module

    types = []
    mapping = {}

    for mod in ETREE_MODULES:
        try:
            etree = get_module(mod)
        except ImportError:
            continue

        t = _get_etree_type(etree)

        types.append(t)
        mapping[t] = etree

    return tuple(types), mapping


def is_xml(obj):
    """
    Determines C{obj} is a valid XML type.

    If L{types} is not populated then L{find_libs} be called.
    """
    global types

    try:
        _bootstrap()
    except ImportError:
        return False

    return isinstance(obj, types)


def _get_type(e):
    """
    Returns the type associated with handling XML objects from this etree
    interface.
    """
    try:
        return e.__class__
    except AttributeError:
        return type(e)


def _get_etree_type(etree):
    """
    Returns the type associated with handling XML objects from this etree
    interface.
    """
    e = etree.fromstring('<foo/>')

    return _get_type(e)


def _no_et():
    raise ImportError('Unable to find at least one compatible ElementTree '
        'library, use pyamf.set_default_etree to enable XML support')


def _bootstrap():
    global types, modules, ET

    if types is None:
        types, modules = find_libs()

    if ET is None:
        try:
            etree = modules[types[0]]
        except IndexError:
            _no_et()

        set_default_interface(etree)


def tostring(element, *args, **kwargs):
    """
    Helper func to provide easy access to the (possibly) moving target that is
    C{ET}.
    """
    global modules

    _bootstrap()
    t = _get_type(element)

    etree = modules.get(t, None)

    if not etree:
        raise RuntimeError('Unable to find the etree implementation related '
            'to %r (type %r)' % (element, t))

    return etree.tostring(element, *args, **kwargs)


def fromstring(*args, **kwargs):
    """
    Helper func to provide easy access to the (possibly) moving target that is
    C{ET}.
    """
    global ET

    _bootstrap()

    return ET.fromstring(*args, **kwargs)

########NEW FILE########
