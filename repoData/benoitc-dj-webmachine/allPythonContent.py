__FILENAME__ = conf
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import sys, os
import webmachine


sys.path.insert(0, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'django.conf.global_settings'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest',
'sphinx.ext.viewcode', 'sphinxtogithub']


templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = u'dj-webmachine'
copyright = u'2010, Benoît Chesnea <benoitc@e-engura.org>u'

version = webmachine.__version__
release = version

exclude_trees = ['_build']

pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'dj-webmachinedoc'

latex_documents = [
  ('index', 'dj-webmachine.tex', u'dj-webmachine Documentation',
   u'Benoît Chesneau', 'manual'),
]

man_pages = [
    ('index', 'dj-webmachine', u'dj-webmachine Documentation',
     [u'Benoît Chesneau'], 1)
]

epub_title = u'dj-webmachine'
epub_author = u'Benoît Chesneau'
epub_publisher = u'Benoît Chesneau'
epub_copyright = u'2010, Benoît Chesneau'



########NEW FILE########
__FILENAME__ = sphinxtogithub
#! /usr/bin/env python
 
import optparse as op
import os
import sys
import shutil


class NoDirectoriesError(Exception):
    "Error thrown when no directories starting with an underscore are found"

class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree

class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists

class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace( self.from_, self.to )

class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name).read()

        for replacer in self.replacers:
            text = replacer.process( text )

        self.opener(self.name, "w").write(text)

class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)

class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)

class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):
        
        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper, dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):

        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove) 

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream) 

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            raise NoDirectoriesError()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))



def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    # This code is sadly untestable in its current state
    # It would be helped if there was some function for loading extension
    # specific data on to the app object and the app object providing 
    # a file-like object for writing to standard out.
    # The former is doable, but not officially supported (as far as I know)
    # so I wouldn't know where to stash the data. 

    if app.builder.name != "html":
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Disabled, doing nothing."
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Exception raised in main build, doing nothing."
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')

    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = OptionParser(usage=usage)
    parser.add_option("-v","--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    try:
        layout = layout_factory.create_layout(path)
    except NoDirectoriesError:
        sys.stderr.write(
                "Error - No top level directories starting with an underscore "
                "were found in '%s'\n" % path
                )
        return

    layout.process()
    


if __name__ == "__main__":
    main(sys.argv[1:])




########NEW FILE########
__FILENAME__ = sphinxtogithub
#! /usr/bin/env python

import optparse as op
import os
import sys
import shutil


class NoDirectoriesError(Exception):
    "Error thrown when no directories starting with an underscore are found"


class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree


class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists


class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace(self.from_, self.to)


class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name).read()

        for replacer in self.replacers:
            text = replacer.process(text)

        self.opener(self.name, "w").write(text)


class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)


class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)


class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):

        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper,
                 dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):

        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove)

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream)

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            raise NoDirectoriesError()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))


def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    # This code is sadly untestable in its current state
    # It would be helped if there was some function for loading extension
    # specific data on to the app object and the app object providing
    # a file-like object for writing to standard out.
    # The former is doable, but not officially supported (as far as I know)
    # so I wouldn't know where to stash the data.

    if app.builder.name != "html":
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Disabled, doing nothing."
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Exception raised in main build, doing nothing."
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )

    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')

    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = op.OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )

    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    try:
        layout = layout_factory.create_layout(path)
    except NoDirectoriesError:
        sys.stderr.write(
                "Error - No top level directories starting with an underscore "
                "were found in '%s'\n" % path
                )
        return

    layout.process()

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = resource
import json

from webmachine import Resource
from webmachine import wm

class Hello(Resource):

    def content_types_provided(self, req, resp):
        return ( 
            ("", self.to_html),
            ("application/json", self.to_json)
        )

    def to_html(self, req, resp):
        return "<html><body>Hello world!</body></html>\n"
    
    def to_json(self, req, resp):
        return "%s\n" % json.dumps({"message": "hello world!", "ok": True})


# available at wm/hello
wm.add_resource(Hello, r"^hello")


# available at wm/helloworld/hello
wm.add_resource(Hello)


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
# Django settings for testapi project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

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
SECRET_KEY = 'qawvnb9++2gek1lirm7_(e=iu(km-g8)yzqo2j&l05id@20%o*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'helloworld.urls'

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
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'webmachine',
    'helloworld.hello',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from helloworld.hello.resource import Hello

import webmachine
urlpatterns = patterns('',
    (r'^wm/', include(webmachine.wm.urls)),
    (r'^$', Hello()),

)


########NEW FILE########
__FILENAME__ = resources
from webmachine import wm

import json
@wm.route(r"^$")
def hello(req, resp):
    return "<html><p>hello world!</p></html>"


@wm.route(r"^$", provided=[("application/json", json.dumps)])
def hello_json(req, resp):
    return {"ok": True, "message": "hellow world"}


def resource_exists(req, resp):
    return True

@wm.route(r"^hello$", 
        provided=["text/html", ("application/json", json.dumps)],
        resource_exists=resource_exists
        
        )
def all_in_one(req, resp):
    if resp.content_type == "application/json":
        return {"ok": True, "message": "hellow world! All in one"}
    else:
        return "<html><p>hello world! All in one</p></html>"



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
# Django settings for helloworld2 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

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
SECRET_KEY = 'z6@bl1^xn9jpajhjktj3bk-*j1x9tmc_2zyndlw3-x$g2wu1z@'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'helloworld2.urls'

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
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'webmachine',
    'helloworld2.hello'
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

import webmachine

webmachine.autodiscover()
print len(webmachine.wm.routes)

urlpatterns = patterns('',
    (r'^', include(webmachine.wm.urls))
)

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
__FILENAME__ = resource
from webmachine import Resource
from webmachine.auth.oauth import Oauth

class Protected(Resource):

    def to_html(self, req, resp):
        return "<html><p>I'm protected you know.</p></html>"

    def is_authorized(self, req, resp):
        return Oauth().authorized(req, resp)

########NEW FILE########
__FILENAME__ = settings
# Django settings for oauth project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'oauth.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

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
SECRET_KEY = '#i=e163$15)prr-_mpo!po085%jtan0y0%yd8gx++wz0fy(qg%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'testoauth.urls'

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
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'webmachine',
    'testoauth.protected'
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from webmachine.auth import oauth_res

from testoauth.protected.resource import Protected

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()


urlpatterns = patterns('',
    # Example:
    # (r'^oauth/', include('oauth.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),

    (r'^auth/', include(oauth_res.OauthResource().get_urls())),
    (r'$^', Protected()),
)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import binascii

from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser

from webmachine.exc import HTTPClientError

class Auth(object):

    def authorized(self, request):
        return True

class BasicAuth(Auth):

    def __init__(self, func=authenticate, realm="API"):
        """
        :attr func: authentification function. By default it's the
        :func:`django.contrib.auth.authenticate` function.
        :attr realm: string, the authentification realm
        """

        self.func = func
        self.realm = realm

    def authorized(self, req, resp):
        auth_str = req.META.get("HTTP_AUTHORIZATION")
        if not auth_str:
            return 'Basic realm="%s"' % self.realm

        try:
            (meth, auth) = auth_str.split(" ", 1)
            if meth.lower() != "basic":
                # bad method
                return False
            auth1 = auth.strip().decode('base64')
            (user, pwd) = auth1.split(":", 1)
        except (ValueError, binascii.Error):
            raise HTTPClientError()

        req.user = self.func(username=user, password=pwd)
        if not req.user:
            req.user = AnonymousUser()
            return 'Basic realm="%s"' % self.realm
        return True


########NEW FILE########
__FILENAME__ = oauth
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license.
# See the NOTICE for more information.

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.importlib import import_module

try:
    from restkit import oauth2
except ImportError:
    raise ImportError("restkit>=3.0.2 package is needed for auth.")

from webmachine.auth.base import Auth
from webmachine.util.const import TOKEN_REQUEST, TOKEN_ACCESS


def load_oauth_datastore():
    datastore = getattr(settings, 'OAUTH_DATASTORE',
            'webmachine.auth.oauth_store.DataStore')
    i = datastore.rfind('.')
    module, clsname = datastore[:i], datastore[i+1:]
    try:
        mod = import_module(module)
    except ImportError:
        raise ImproperlyConfigured("oauth datastore module '%s' isn't valid" % module)

    try:
        cls = getattr(mod, clsname)
    except AttributeError:
        raise ImproperlyConfigured("oauth datastore '%s' doesn't exist in '%s' module" % (clsname, module))
    return cls


class OAuthServer(oauth2.Server):

    def __init__(self, datastore):
        self.datastore = datastore
        super(OAuthServer, self).__init__()

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, TOKEN_REQUEST)
        except oauth2.Error:
            # No token required for the initial token request.
            timestamp = self._get_timestamp(oauth_request)
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except oauth2.Error:
                callback = None # 1.0, no callback specified.

            #hack

            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.datastore.fetch_request_token(consumer,
                    callback, timestamp)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        timestamp = self._get_timestamp(oauth_request)
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except oauth2.Error:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, TOKEN_REQUEST)
        self._check_signature(oauth_request, consumer, token)
        new_token = self.datastore.fetch_access_token(consumer, token,
                verifier, timestamp)
        return new_token

    def verify_request(self, oauth_request):
        consumer = self._get_consumer(oauth_request)
        token = self._get_token(oauth_request, TOKEN_ACCESS)
        parameters = super(OAuthServer, self).verify_request(oauth_request,
                consumer, token)
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.datastore.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.datastore.lookup_consumer(consumer_key)
        if not consumer:
            raise oauth2.Error('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type=TOKEN_ACCESS):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.datastore.lookup_token(token_type, token_field)
        if not token:
            raise oauth2.Error('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.datastore.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise oauth2.Error('Nonce already used: %s' % str(nonce))

    def _get_timestamp(self, oauth_request):
        return int(oauth_request.get_parameter('oauth_timestamp'))


class Oauth(Auth):

    def __init__(self, realm="OAuth"):
        oauth_datastore = load_oauth_datastore()
        self.realm = realm
        self.oauth_server = OAuthServer(oauth_datastore())
        self.oauth_server.add_signature_method(oauth2.SignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth2.SignatureMethod_HMAC_SHA1())

    def authorized(self, req, resp):
        params = {}
        headers = {}

        if req.method == "POST":
            params = req.REQUEST.items()

        if 'HTTP_AUTHORIZATION' in req.META:
            headers['Authorization'] = req.META.get('HTTP_AUTHORIZATION')


        oauth_request = oauth2.Request.from_request(req.method,
            req.build_absolute_uri(), headers=headers,
            parameters=params,
            query_string=req.META.get('QUERY_STRING'))

        if not oauth_request:
            return 'OAuth realm="%s"' % self.realm

        try:
            consumer, token, params = self.oauth_server.verify_request(oauth_request)
        except oauth2.Error, err:
            resp.content = str(err)
            return 'OAuth realm="%s"' % self.realm

        req.user = consumer.user
        return True

########NEW FILE########
__FILENAME__ = oauth_res
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license.
# See the NOTICE for more information.

from django.template import loader, RequestContext
from django.utils.encoding import iri_to_uri

try:
    from restkit import oauth2
except ImportError:
    raise ImportError("restkit>=3.0.2 package is needed for auth.")

from webmachine.auth.oauth import OAuthServer, load_oauth_datastore
from webmachine.forms import OAuthAuthenticationForm
from webmachine.resource import Resource


class OauthResource(Resource):

    def __init__(self, realm='OAuth',
            auth_template='webmachine/authorize_token.html',
            auth_form=OAuthAuthenticationForm):

        self.auth_template = auth_template
        self.auth_form = auth_form
        self.realm = realm

        oauth_datastore = load_oauth_datastore()
        self.oauth_server = OAuthServer(oauth_datastore())
        self.oauth_server.add_signature_method(oauth2.SignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth2.SignatureMethod_HMAC_SHA1())

    def allowed_methods(self, req, resp):
        return ["GET", "HEAD", "POST"]

    def oauth_authorize(self, req, resp):
        try:
            token = self.oauth_server.fetch_request_token(req.oauth_request)
        except oauth2.Error, err:
            return self.auth_error(req, resp, err)

        try:
            callback = self.auth_server.get_callback(req.oauth_request)
        except:
            callback = None

        if req.method == "GET":
            params = req.oauth_request.get_normalized_parameters()
            form = self.auth_form(initial={
                'oauth_token': token.key,
                'oauth_callback': token.get_callback_url() or callback,
            })
            resp.content = loader.render_to_string(self.auth_template,
                    {'form': form}, RequestContext(req))

        elif req.method == "POST":

            try:
                form = self.auth_form(req.POST)
                if form.is_valid():
                    token = self.oauth_server.authorize_token(token, req.user)
                    args = '?'+token.to_string(only_key=True)
                else:
                    args = '?error=%s' % 'Access not granted by user.'
                    if not callback:
                        resp.content = 'Access not granted by user.'

                if not callback:
                    return True

                resp.redirect_to = iri_to_uri("%s%s" % (callback, args))
            except oauth2.Error, err:
                return self.oauth_error(req, resp, err)
        return True

    def oauth_access_token(self, req, resp):
        try:
            token = self.oauth_server.fetch_access_token(req.oauth_request)
            if not token:
                return False
            resp.content = token.to_string()
        except oauth2.Error, err:
            return self.oauth_error(req, resp, err)
        return True

    def oauth_request_token(self, req, resp):
        try:
            token = self.oauth_server.fetch_request_token(req.oauth_request)
            if not token:
                return False
            resp.content = token.to_string()
        except oauth2.Error, err:
            return self.oauth_error(req, resp, err)
        return True

    def oauth_error(self, req, resp, err):
        resp.content = str(err)
        return 'OAuth realm="%s"' % self.realm

    def oauth_resp(self, req, resp):
        return resp.content

    def content_types_provided(self, req, resp):
        return [("", self.oauth_resp)]

    def process_post(self, res, resp):
        # we already processed POST
        return True

    def created_location(self, req, resp):
        try:
            return resp.redirect_to
        except AttributeError:
            return False

    def is_authorized(self, req, resp):
        func = getattr(self, "oauth_%s" % req.oauth_action)
        return func(req, resp)

    def malformed_request(self, req, resp):
        params = {}
        headers = {}

        if req.method == "POST":
            params = dict(req.REQUEST.items())

        if 'HTTP_AUTHORIZATION' in req.META:
            headers['Authorization'] = req.META.get('HTTP_AUTHORIZATION')

        oauth_request = oauth2.Request.from_request(req.method,
            req.build_absolute_uri(), headers=headers,
            parameters=params,
            query_string=req.META.get('QUERY_STRING'))

        if not oauth_request:

            return True

        req.oauth_request = oauth_request
        return False

    def ping(self, req, resp):
        action = req.url_kwargs.get("action")
        if not action or action not in ("authorize", "access_token",
                "request_token"):
            return False

        req.oauth_action = action

        return True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urlpatterns = patterns('',
                url(r'^authorize$', self,
                    kwargs={"action": "authorize"},
                    name="oauth_authorize"),
                url(r'^access_token$', self,
                    kwargs={"action": "access_token"},
                    name="oauth_access_token"),
                url(r'^request_token$', self,
                    kwargs= {"action": "request_token"},
                    name="oauth_request_token"),
        )
        return urlpatterns

    urls = property(get_urls)

########NEW FILE########
__FILENAME__ = oauth_store
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license.
# See the NOTICE for more information.

from django.contrib.auth.models import AnonymousUser

from webmachine.models import Nonce, Consumer, Token
from webmachine.util import generate_random
from webmachine.util.const import VERIFIER_SIZE, TOKEN_REQUEST, TOKEN_ACCESS


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, token_type, key):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback,
            oauth_timestamp):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token,
            oauth_verifier, oauth_timestamp):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class DataStore(OAuthDataStore):

    def lookup_consumer(self, key):
        try:
            self.consumer = Consumer.objects.get(key=key)
        except Consumer.DoesNotExist:
            return None
        return self.consumer

    def lookup_token(self, token_type, key):
        try:
            self.request_token = Token.objects.get(
                token_type=token_type,
                key=key)
        except Consumer.DoesNotExist:
            return None
        return self.request_token

    def lookup_nonce(self, consumer, token, nonce):
        if not token:
            return

        nonce, created = Nonce.objects.get_or_create(
            consumer_key=consumer.key,
            token_key=token.key,
            nonce=nonce)

        if created:
            return None
        return nonce

    def fetch_request_token(self, consumer, callback, timestamp):
        if consumer.key == self.consumer.key:
            request_token = Token.objects.create_token(
                consumer=self.consumer,
                token_type=TOKEN_REQUEST,
                timestamp=timestamp)

            if callback:
                self.request_token.set_callback(callback)

            self.request_token = request_token
            return request_token
        return None

    def fetch_access_token(self, consumer, token, verifier, timestamp):
        if consumer.key == self.consumer.key \
        and token.key == self.request_token.key \
        and self.request_token.is_approved:
            if (self.request_token.callback_confirmed \
                    and verifier == self.request_token.verifier) \
                    or not self.request_token.callback_confirmed:

                self.access_token = Token.objects.create_token(
                    consumer=self.consumer,
                    token_type=TOKEN_ACCESS,
                    timestamp=timestamp,
                    user=self.request_token.user)
                return self.access_token
        return None

    def authorize_request_token(self, oauth_token, user):
        if oauth_token.key == self.request_token.key:
            # authorize the request token in the store
            self.request_token.is_approved = True
            if not isinstance(user, AnonymousUser):
                self.request_token.user = user
            self.request_token.verifier = generate_random(VERIFIER_SIZE)
            self.request_token.save()
            return self.request_token
        return None

########NEW FILE########
__FILENAME__ = decisions
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import datetime

from webob.datetime_utils import UTC
import webmachine.exc

def b03(res, req, resp):
    "Options?"
    if req.method == 'OPTIONS':
        for (header, value) in res.options(req, resp):
            resp[header] = value
        return True
    return False

def b04(res, req, resp):
    "Request entity too large?"
    return not res.valid_entity_length(req, resp)

def b05(res, req, resp):
    "Unknown Content-Type?"
    return not res.known_content_type(req, resp)

def b06(res, req, resp):
    "Unknown or unsupported Content-* header?"
    return not res.valid_content_headers(req, resp)

def b07(res, req, resp):
    "Forbidden?"
    return res.forbidden(req, resp)

def b08(res, req, resp):
    "Authorized?"
    auth = res.is_authorized(req, resp)
    if auth is True:
        return True
    elif isinstance(auth, basestring):
        resp["WWW-Authenticate"] = auth
    return False

def b09(res, req, resp):
    "Malformed?"
    return res.malformed_request(req, resp)

def b10(res, req, resp):
    "Is method allowed?"
    if req.method in res.allowed_methods(req, resp):
        return True
    return False 

def b11(res, req, resp):
    "URI too long?"
    return res.uri_too_long(req, resp)

def b12(res, req, resp):
    "Known method?"
    return req.method in res.known_methods(req, resp)

def b13(res, req, resp):
    "Service available?"
    return res.ping(req, resp) and res.service_available(req, resp)

def c03(res, req, resp):
    "Accept exists?"
    return "HTTP_ACCEPT" in req.META

def c04(res, req, resp):
    "Acceptable media type available?"
    ctypes = [ctype for (ctype, func) in res.content_types_provided(req, resp)]
    ctype = req.accept.best_match(ctypes)
    if ctype is None:
        return False
    resp.content_type = ctype
    return True

def d04(res, req, resp):
    "Accept-Language exists?"
    return "HTTP_ACCEPT_LANGUAGE" in req.META

def d05(res, req, resp):
    "Accept-Language available?"
    langs = res.languages_provided(req, resp)
    if langs is not None:
        lang = req.accept_language.best_match(langs)
        if lang is None:
            return False
        resp.content_language = lang
    return True
    
def e05(res, req, resp):
    "Accept-Charset exists?"
    return "HTTP_ACCEPT_CHARSET" in req.META

def e06(res, req, resp):
    "Acceptable charset available?"
    charsets = res.charsets_provided(req, resp)
    if charsets is not None:
        charset = req.accept_charset.best_match(charsets)
        if charset is None:
            return False
        resp._charset = charset
    return True

def f06(res, req, resp):
    "Accept-Encoding exists?"
    return "HTTP_ACCEPT_ENCODING" in req.META

def f07(res, req, resp):
    "Acceptable encoding available?"
    encodings = res.encodings_provided(req, resp)
    if encodings is not None:
        encodings = [enc for (enc, func) in encodings]
        enc = req.accept_encoding.best_match(encodings)
        if enc is None:
            return False
        resp.content_encoding = enc
    return True

def g07(res, req, resp):
    "Resource exists?"

    # Set variances now that conneg is done
    hdr = []
    if len(res.content_types_provided(req, resp) or []) > 1:
        hdr.append("Accept")
    if len(res.charsets_provided(req, resp) or []) > 1:
        hdr.append("Accept-Charset")
    if len(res.encodings_provided(req, resp) or []) > 1:
        hdr.append("Accept-Encoding")
    if len(res.languages_provided(req, resp) or []) > 1:
        hdr.append("Accept-Language")
    hdr.extend(res.variances(req, resp))
    resp.vary = hdr

    return res.resource_exists(req, resp)

def g08(res, req, resp):
    "If-Match exists?"
    return "HTTP_IF_MATCH" in req.META

def g09(res, req, resp):
    "If-Match: * exists?"
    return '*' in req.if_match

def g11(res, req, resp):
    "Etag in If-Match?"
    return res.generate_etag(req, resp) in req.if_match

def h07(res, req, resp):
    "If-Match: * exists?"
    # Need to recheck that if-match was an actual header
    # because WebOb is says that '*' will match no header.
    return 'HTTP_IF_MATCH' in req.META and '*' in req.if_match

def h10(res, req, resp):
    "If-Unmodified-Since exists?"
    return "HTTP_IF_MODIFIED_SINCE" in req.META

def h11(res, req, resp):
    "If-Unmodified-Since is a valid date?"
    return req.if_unmodified_since is not None

def h12(res, req, resp):
    "Last-Modified > If-Unmodified-Since?"
    if not req.if_unmodified_since:
        return True

    resp.last_modified = res.last_modified(req, resp)
    return resp.last_modified > req.if_unmodified_since

def i04(res, req, resp):
    "Apply to a different URI?"
    uri = res.moved_permanently(req, resp)
    if not uri:
        return False
    resp.location = uri
    return True

def i07(res, req, resp):
    "PUT?"
    return req.method == "PUT"

def i12(res, req, resp):
    "If-None-Match exists?"
    return "HTTP_IF_NONE_MATCH" in req.META
    
def i13(res, req, resp):
    "If-None-Match: * exists?"
    return '*' in req.if_none_match
    
def j18(res, req, resp):
    "GET/HEAD?"
    return req.method in ["GET", "HEAD"]

def k05(res, req, resp):
    "Resource moved permanently?"
    uri = res.moved_permanently(req, resp)
    if not uri:
        return False
    resp.location = uri
    return True

def k07(res, req, resp):
    "Resource previously existed?"
    return res.previously_existed(req, resp)

def k13(res, req, resp):
    "Etag in If-None-Match?"
    resp.etag = res.generate_etag(req, resp)
    return resp.etag in req.if_none_match

def l05(res, req, resp):
    "Resource moved temporarily?"
    uri = res.moved_temporarily(req, resp)
    if not uri:
        return False
    resp.location = uri
    return True

def l07(res, req, resp):
    "POST?"
    return req.method == "POST"

def l13(res, req, resp):
    "If-Modified-Since exists?"
    return "HTTP_IF_MODIFIED_SINCE" in req.META

def l14(res, req, resp):
    "If-Modified-Since is a valid date?"
    return req.if_modified_since is not None

def l15(res, req, resp):
    "If-Modified-Since > Now?"
    return req.if_modified_since > datetime.datetime.now(UTC)

def l17(res, req, resp):
    "Last-Modified > If-Modified-Since?"
    resp.last_modified = res.last_modified(req, resp)
    if not (req.if_modified_since and resp.last_modified):
        return True
    return resp.last_modified > req.if_modified_since

def m05(res, req, resp):
    "POST?"
    return req.method == "POST"

def m07(res, req, resp):
    "Server permits POST to missing resource?"
    return res.allow_missing_post(req, resp)

def m16(res, req, resp):
    "DELETE?"
    return req.method == "DELETE"

def m20(res, req, resp):
    """Delete enacted immediayly?
    Also where DELETE is forced."""
    return res.delete_resource(req, resp)

def m20b(res, req, resp):
    """ Delete completed """
    return res.delete_completed(req, resp)

def n05(res, req, resp):
    "Server permits POST to missing resource?"
    return res.allow_missing_post(req, resp)

def n11(res, req, resp):
    "Redirect?"
    if res.post_is_create(req, resp):
        handle_request_body(res, req, resp)
    else:
        if not res.process_post(req, resp):
            raise webmachine.exc.HTTPInternalServerError("Failed to process POST.")
        return False
    resp.location = res.created_location(req, resp)
    if resp.location:
        return True     
    return False


def n16(res, req, resp):
    "POST?"
    return req.method == "POST"

def o14(res, req, resp):
    "Is conflict?"
    if not res.is_conflict(req, resp):
        handle_response_body(res, req, resp)
        return False
    return True

def o16(res, req, resp):
    "PUT?"
    return req.method == "PUT"

def o18(res, req, resp):
    "Multiple representations? (Build GET/HEAD body)"
    if req.method not in ["GET", "HEAD"]:
        return res.multiple_choices(req, resp)

    handle_response_body(res, req, resp)
    return res.multiple_choices(req, resp)

def o20(res, req, resp):
    "Response includes entity?"
    return bool(resp._container)

def p03(res, req, resp):
    "Conflict?"
    if res.is_conflict(req, resp):
        return True

    handle_request_body(res, req, resp)
    return False

def p11(res, req, resp):
    "New resource?"
    if not resp.location:
        return False
    return True

def first_match(func, req, resp, expect):
    for (key, value) in func(req, resp):
        if key == expect:
            return value
    return None

def handle_request_body(res, req, resp):
    ctype = req.content_type or "application/octet-stream"
    mtype = ctype.split(";", 1)[0]

    func = first_match(res.content_types_accepted, req, resp, mtype)
    if func is None:
        raise webmachine.exc.HTTPUnsupportedMediaType()
    func(req, resp)

def handle_response_body(res, req, resp):
    resp.etag = res.generate_etag(req, resp)
    resp.last_modified = res.last_modified(req, resp)
    resp.expires = res.expires(req, resp)
    
    # Generate the body
    func = first_match(res.content_types_provided, req, resp, resp.content_type)
    if func is None:
        raise webmachine.exc.HTTPInternalServerError()
  
    body = func(req, resp)

    if not resp.content_type:
        resp.content_type = "text/plain" 

    # Handle our content encoding.
    encoding = resp.content_encoding
    if encoding:
        func = first_match(res.encodings_provided, req, resp, encoding)
        if func is None:
            raise webmachine.exc.HTTPInternalServerError()
        resp.body = func(resp.body)
        resp['Content-Encoding'] = encoding

    if not isinstance(body, basestring) and hasattr(body, '__iter__'):
        resp._container = body
        resp._is_string = False
    else:
        resp._container = [body]
        resp._is_string = True


TRANSITIONS = {
    b03: (200, c03), # Options?
    b04: (413, b03), # Request entity too large?
    b05: (415, b04), # Unknown Content-Type?
    b06: (501, b05), # Unknown or unsupported Content-* header?
    b07: (403, b06), # Forbidden?
    b08: (b07, 401), # Authorized?
    b09: (400, b08), # Malformed?
    b10: (b09, 405), # Is method allowed?
    b11: (414, b10), # URI too long?
    b12: (b11, 501), # Known method?
    b13: (b12, 503), # Service available?
    c03: (c04, d04), # Accept exists?
    c04: (d04, 406), # Acceptable media type available?
    d04: (d05, e05), # Accept-Language exists?
    d05: (e05, 406), # Accept-Language available?
    e05: (e06, f06), # Accept-Charset exists?
    e06: (f06, 406), # Acceptable charset available?
    f06: (f07, g07), # Accept-Encoding exists?
    f07: (g07, 406), # Acceptable encoding available?
    g07: (g08, h07), # Resource exists?
    g08: (g09, h10), # If-Match exists?
    g09: (h10, g11), # If-Match: * exists?
    g11: (h10, 412), # Etag in If-Match?
    h07: (412, i07), # If-Match: * exists?
    h10: (h11, i12), # If-Unmodified-Since exists?
    h11: (h12, i12), # If-Unmodified-Since is valid date?
    h12: (412, i12), # Last-Modified > If-Unmodified-Since?
    i04: (301, p03), # Apply to a different URI?
    i07: (i04, k07), # PUT?
    i12: (i13, l13), # If-None-Match exists?
    i13: (j18, k13), # If-None-Match: * exists?
    j18: (304, 412), # GET/HEAD?
    k05: (301, l05), # Resource moved permanently?
    k07: (k05, l07), # Resource previously existed?
    k13: (j18, l13), # Etag in If-None-Match?
    l05: (307, m05), # Resource moved temporarily?
    l07: (m07, 404), # POST?
    l13: (l14, m16), # If-Modified-Since exists?
    l14: (l15, m16), # If-Modified-Since is valid date?
    l15: (m16, l17), # If-Modified-Since > Now?
    l17: (m16, 304), # Last-Modified > If-Modified-Since?
    m05: (n05, 410), # POST?
    m07: (n11, 404), # Server permits POST to missing resource?
    m16: (m20, n16), # DELETE?
    m20: (m20b, 500), # DELETE enacted immediately?
    m20b: (o20, 202), # Delete completeed?
    m20: (o20, 202), # Delete enacted?
    n05: (n11, 410), # Server permits POST to missing resource?
    n11: (303, p11), # Redirect?
    n16: (n11, o16), # POST?
    o14: (409, p11), # Conflict?
    o16: (o14, o18), # PUT?
    o18: (300, 200), # Multiple representations?
    o20: (o18, 204), # Response includes entity?
    p03: (409, p11), # Conflict?
    p11: (201, o20)  # New resource?
}

########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT. 
# See the NOTICE for more information.


from django.http import HttpResponse
from django import template


class HTTPException(Exception):

    def __init__(self, message, resp):
        Exception.__init__(self, message)
        self.__dict__['response'] = resp

    def __call__(self):
        return self.response

class DjangoHttpException(HttpResponse, HTTPException):
    status_code = 200
    title = None
    explanation = ''
    body_template = """\
{{explanation|safe}}<br><br>
{{detail|safe}}
{{comment|safe}}"""

    ## Set this to True for responses that should have no request body
    empty_body = False

    def __init__(self, detail=None, body_template=None, comment=None, **kw):
        HttpResponse.__init__(
                self,
                status = '%s %s' % (self.code, self.title), 
                **kw)
        Exception.__init__(self, detail)


        if comment is not None:
            self.comment = comment

        if body_template is not None:
            self.body_template = body_template
        if isinstance(self.explanation, (list, tuple)):
            self.explanation = "<p>%s</p>" % "<br>".join(self.explanation)


        if not self.empty_body:
            t = template.Template(self.body_template)
            c = template.Context(dict(
                detail=detail,
                explanation=self.explanation,
                comment=comment))

            self._container = [t.render(c)]
        else:
            self._container = ['']
        self._is_string = True




class HTTPOk(DjangoHttpException):
    """ return response with Status 200 """
    title = "OK"

class HTTPError(DjangoHttpException):
    code = 400

############################################################
## 2xx success
############################################################

class HTTPCreated(HTTPOk):
    code = 201
    title = 'Created'

class HTTPAccepted(HTTPOk):
    code = 202
    title = 'Accepted'
    explanation = 'The request is accepted for processing.'

class HTTPNonAuthoritativeInformation(HTTPOk):
    code = 203
    title = 'Non-Authoritative Information'

class HTTPNoContent(HTTPOk):
    code = 204
    title = 'No Content'
    empty_body = True

class HTTPResetContent(HTTPOk):
    code = 205
    title = 'Reset Content'
    empty_body = True

class HTTPPartialContent(HTTPOk):
    code = 206
    title = 'Partial Content'

############################################################
## 4xx client error
############################################################

class HTTPClientError(HTTPError):
    """
    base class for the 400's, where the client is in error

    This is an error condition in which the client is presumed to be
    in-error.  This is an expected problem, and thus is not considered
    a bug.  A server-side traceback is not warranted.  Unless specialized,
    this is a '400 Bad Request'
    """
    code = 400
    title = 'Bad Request'
    explanation = ('The server could not comply with the request since\r\n'
                   'it is either malformed or otherwise incorrect.\r\n')

class HTTPBadRequest(HTTPClientError):
    pass

class HTTPUnauthorized(HTTPClientError):
    code = 401
    title = 'Unauthorized'
    explanation = (
        'This server could not verify that you are authorized to\r\n'
        'access the document you requested.  Either you supplied the\r\n'
        'wrong credentials (e.g., bad password), or your browser\r\n'
        'does not understand how to supply the credentials required.\r\n')

class HTTPPaymentRequired(HTTPClientError):
    code = 402
    title = 'Payment Required'
    explanation = ('Access was denied for financial reasons.')

class HTTPForbidden(HTTPClientError):
    code = 403
    title = 'Forbidden'
    explanation = ('Access was denied to this resource.')

class HTTPNotFound(HTTPClientError):
    code = 404
    title = 'Not Found'
    explanation = ('The resource could not be found.')

class HTTPMethodNotAllowed(HTTPClientError):
    code = 405
    title = 'Method Not Allowed'
    
class HTTPNotAcceptable(HTTPClientError):
    code = 406
    title = 'Not Acceptable'


class HTTPProxyAuthenticationRequired(HTTPClientError):
    code = 407
    title = 'Proxy Authentication Required'
    explanation = ('Authentication with a local proxy is needed.')

class HTTPRequestTimeout(HTTPClientError):
    code = 408
    title = 'Request Timeout'
    explanation = ('The server has waited too long for the request to '
                   'be sent by the client.')

class HTTPConflict(HTTPClientError):
    code = 409
    title = 'Conflict'
    explanation = ('There was a conflict when trying to complete '
                   'your request.')

class HTTPGone(HTTPClientError):
    code = 410
    title = 'Gone'
    explanation = ('This resource is no longer available.  No forwarding '
                   'address is given.')

class HTTPLengthRequired(HTTPClientError):
    code = 411
    title = 'Length Required'
    explanation = ('Content-Length header required.')

class HTTPPreconditionFailed(HTTPClientError):
    code = 412
    title = 'Precondition Failed'
    explanation = ('Request precondition failed.')

class HTTPRequestEntityTooLarge(HTTPClientError):
    code = 413
    title = 'Request Entity Too Large'
    explanation = ('The body of your request was too large for this server.')

class HTTPRequestURITooLong(HTTPClientError):
    code = 414
    title = 'Request-URI Too Long'
    explanation = ('The request URI was too long for this server.')

class HTTPUnsupportedMediaType(HTTPClientError):
    code = 415
    title = 'Unsupported Media Type'


class HTTPRequestRangeNotSatisfiable(HTTPClientError):
    code = 416
    title = 'Request Range Not Satisfiable'
    explanation = ('The Range requested is not available.')

class HTTPExpectationFailed(HTTPClientError):
    code = 417
    title = 'Expectation Failed'
    explanation = ('Expectation failed.')

class HTTPUnprocessableEntity(HTTPClientError):
    ## Note: from WebDAV
    code = 422
    title = 'Unprocessable Entity'
    explanation = 'Unable to process the contained instructions'

class HTTPLocked(HTTPClientError):
    ## Note: from WebDAV
    code = 423
    title = 'Locked'
    explanation = ('The resource is locked')

class HTTPFailedDependency(HTTPClientError):
    ## Note: from WebDAV
    code = 424
    title = 'Failed Dependency'
    explanation = ('The method could not be performed because the requested '
                   'action dependended on another action and that action failed')

############################################################
## 5xx Server Error
############################################################


class HTTPServerError(HTTPError):
    """
    base class for the 500's, where the server is in-error

    This is an error condition in which the server is presumed to be
    in-error.  This is usually unexpected, and thus requires a traceback;
    ideally, opening a support ticket for the customer. Unless specialized,
    this is a '500 Internal Server Error'
    """
    code = 500
    title = 'Internal Server Error'
    explanation = (
      'The server has either erred or is incapable of performing\r\n'
      'the requested operation.\r\n')

class HTTPInternalServerError(HTTPServerError):
    pass

class HTTPNotImplemented(HTTPServerError):
    code = 501
    title = 'Not Implemented'


class HTTPBadGateway(HTTPServerError):
    code = 502
    title = 'Bad Gateway'
    explanation = ('Bad gateway.')

class HTTPServiceUnavailable(HTTPServerError):
    code = 503
    title = 'Service Unavailable'
    explanation = ('The server is currently unavailable. '
                   'Please try again at a later time.')

class HTTPGatewayTimeout(HTTPServerError):
    code = 504
    title = 'Gateway Timeout'
    explanation = ('The gateway has timed out.')

class HTTPVersionNotSupported(HTTPServerError):
    code = 505
    title = 'HTTP Version Not Supported'
    explanation = ('The HTTP version is not supported.')

class HTTPInsufficientStorage(HTTPServerError):
    code = 507
    title = 'Insufficient Storage'
    explanation = ('There was not enough space to save the resource')


########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import base64
import hmac
try:
    import hashlib
    _sha = hashlib.sha1
except ImportError:
    import sha
    _sha = sha

from django.conf import settings
from django import forms


class OAuthAuthenticationForm(forms.Form):
    oauth_token = forms.CharField(widget=forms.HiddenInput)
    oauth_callback = forms.CharField(widget=forms.HiddenInput, required=False)
    authorize_access = forms.BooleanField(required=True)
    csrf_signature = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)

        self.fields['csrf_signature'].initial = self.initial_csrf_signature

    def clean_csrf_signature(self):
        sig = self.cleaned_data['csrf_signature']
        token = self.cleaned_data['oauth_token']

        sig1 = OAuthAuthenticationForm.get_csrf_signature(settings.SECRET_KEY, 
                token)
        if sig != sig1:
            raise forms.ValidationError("CSRF signature is not valid")

        return sig

    def initial_csrf_signature(self):
        token = self.initial['oauth_token']
        return OAuthAuthenticationForm.get_csrf_signature(
                settings.SECRET_KEY, token)

    @staticmethod
    def get_csrf_signature(key, token):
        """ Check signature """
        hashed = hmac.new(key, token, _sha)
        return base64.b64encode(hashed.digest())


########NEW FILE########
__FILENAME__ = serialize
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import decimal
import datetime
import re
import time

from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import smart_unicode


re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
re_time = re.compile('^([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?$')
re_datetime = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)?)?$')
re_decimal = re.compile('^(\d+)\.(\d+)$')


__all__ = ['Serializer', 'JSONSerializer', 'value_to_emittable',
'value_to_python']

try:
    import json
except ImportError:
    import django.utils.simplejson as json

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class Serializer(object):

    def __init__(self, fields=None, exclude=None):
        self.fields = fields
        self.exclude = exclude

    def _to_string(self, value):
        return value

    def _to_python(self, value):
        return value

    def serialize(self, value):
        value = value_to_emittable(value, fields=self.fields,
                exclude=self.exclude)
        return self._to_string(value)

    def unserialize(self, value):
        if isinstance(value, basestring):
            value = StringIO.StringIO(value)

        return value_to_python(self._to_python(value))

class JSONSerializer(Serializer):

    def _to_string(self, value):
        stream = StringIO.StringIO()
        json.dump(value, stream)
        return stream.getvalue()

    def _to_python(self, value):
        return json.load(value)



def dict_to_emittable(value, fields=None, exclude=None):
    """ convert a dict to json """
    return dict([(k, value_to_emittable(v, fields=fields,
        exclude=exclude)) for k, v in value.iteritems()])

def list_to_emittable(value, fields=None, exclude=None):
    """ convert a list to json """
    return [value_to_emittable(item, fields=fields, exclude=exclude) for item in value]

def relm_to_emittable(value):
    return value_to_emittable(value.all())


def fk_to_emittable(value, field, fields=None, exclude=None):
    return value_to_emittable(getattr(value, field.name))


def m2m_to_emittable(value, field, fields=None, exclude=None):
    return [model_to_emittable(m, fields=fields, exclude=exclude) \
            for m in getattr(value, field.name).iterator() ]

def qs_to_emittable(value, fields=None, exclude=None):
    return [value_to_emittable(v, fields=fields, exclude=exclude) for v in value]

def model_to_emittable(instance, fields=None, exclude=None):
    meta = instance._meta
    if not fields and not exclude:
        ret = {}
        for f in meta.fields:
            ret[f.attname] = value_to_emittable(getattr(instance,
                f.attname))

        fields = dir(instance.__class__) + ret.keys()
        extra = [k for k in dir(instance) if k not in fields]

        for k in extra:
            ret[k] = value_to_emittable(getattr(instance, k))
    else:
        fields_list = []
        fields_iter = iter(meta.local_fields + meta.virtual_fields + meta.many_to_many)
        # fields_iter = iter(meta.fields + meta.many_to_many)
        for f in fields_iter:
            value = None
            if fields is not None and not f.name in fields:
                continue
            if exclude is not None and f.name in exclude:
                continue

            if f in meta.many_to_many:
                if f.serialize:
                    value = m2m_to_emittable(instance, f, fields=fields,
                            exclude=exclude)
            else:
                if f.serialize:
                    if not f.rel:
                        value = value_to_emittable(getattr(instance,
                            f.attname), fields=fields, exclude=exclude)
                    else:
                        value = fk_to_emittable(instance, f,
                                fields=fields, exclude=exclude)

            if value is None:
                continue

            fields_list.append((f.name, value))

        ret = dict(fields_list)
    return ret

def value_to_emittable(value, fields=None, exclude=None):
    """ convert a value to json using appropriate regexp.
For Dates we use ISO 8601. Decimal are converted to string.
"""
    if isinstance(value, QuerySet):
        value = qs_to_emittable(value, fields=fields, exclude=exclude)
    elif isinstance(value, datetime.datetime):
        value = value.replace(microsecond=0).isoformat() + 'Z'
    elif isinstance(value, datetime.date):
        value = value.isoformat()
    elif isinstance(value, datetime.time):
        value = value.replace(microsecond=0).isoformat()
    elif isinstance(value, decimal.Decimal):
        value = str(value)
    elif isinstance(value, list):
        value = list_to_emittable(value, fields=fields, exclude=exclude)
    elif isinstance(value, dict):
        value = dict_to_emittable(value, fields=fields,
                exclude=exclude)
    elif isinstance(value, Model):
        value = model_to_emittable(value, fields=fields,
                exclude=exclude)

    elif repr(value).startswith("<django.db.models.fields.related.RelatedManager"):
        # related managers
        value = relm_to_emittable(value)
    else:
        value = smart_unicode(value, strings_only=True)

    return value

def datetime_to_python(value):
    if isinstance(value, basestring):
        try:
            value = value.split('.', 1)[0] # strip out microseconds
            value = value.rstrip('Z') # remove timezone separator
            value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        except ValueError, e:
            raise ValueError('Invalid ISO date/time %r' % value)
        return value

def date_to_python(value):
    if isinstance(value, basestring):
        try:
            value = datetime.date(*time.strptime(value, '%Y-%m-%d')[:3])
        except ValueError, e:
            raise ValueError('Invalid ISO date %r' % value)
    return value

def time_to_python(value):
    if isinstance(value, basestring):
        try:
            value = value.split('.', 1)[0] # strip out microseconds
            value = datetime.time(*time.strptime(value, '%H:%M:%S')[3:6])
        except ValueError, e:
            raise ValueError('Invalid ISO time %r' % value)
    return value



def value_to_python(value, convert_decimal=True, convert_number=True):
    """ convert a json value to python type using regexp. values converted
    have been put in json via `value_to_emittable` .
    """

    if isinstance(value, basestring):
        if re_date.match(value):
            value = date_to_python(value)
        elif re_time.match(value):
            value = time_to_python(value)
        elif re_datetime.match(value):
            value = datetime_to_python(value)
        elif re_decimal.match(value) and convert_decimal:
            value = decimal.Decimal(value)
        elif value.isdigit() and convert_number:
            value = int(value)
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False

    elif isinstance(value, list):
        value = list_to_python(value, convert_decimal=convert_decimal,
                convert_number=convert_number)
    elif isinstance(value, dict):
        value = dict_to_python(value, convert_decimal=convert_decimal,
                convert_number=convert_number)
    return value

def list_to_python(value, convert_decimal=True,
        convert_number=True):
    """ convert a list of json values to python list """
    return [value_to_python(item, convert_decimal=convert_decimal, \
        convert_number=convert_number) for item in value]

def dict_to_python(value, convert_decimal=True,
        convert_number=True):
    """ convert a json object values to python dict """
    return dict([(k, value_to_python(v,  convert_decimal=convert_decimal, \
        convert_number=convert_number)) for k, v in value.iteritems()]) 

########NEW FILE########
__FILENAME__ = managers
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import uuid


from django.contrib.auth.models import User
from django.db import models

from webmachine.util.const import SECRET_SIZE

class KeyManager(models.Manager):

    def generate_key_secret(self):
        key = uuid.uuid4().hex
        secret = User.objects.make_random_password(SECRET_SIZE)
        return key, secret

class ConsumerManager(KeyManager):

    def create_consumer(self, name=None, description=None, user=None):
        key, secret = self.generate_key_secret()
        consumer = self.create(
                key=key, 
                secret=secret,
                name=name or '',
                description=description or '', 
                user=user
        )
        return consumer

class TokenManager(KeyManager):

    def create_token(self, consumer, token_type, timestamp, user=None):
        key, secret = self.generate_key_secret()
        kwargs = dict(
            key=key, 
            secret=secret, 
            token_type=token_type,
            consumer=consumer,
            timestamp=timestamp,
            user=user
        )
        if not user:
            del kwargs["user"]
        token = self.create(**kwargs)
        return token


########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import time
import urllib
import urlparse

from django.contrib.auth.models import User
from django.db import models

from webmachine.util.const import KEY_SIZE, SECRET_SIZE, VERIFIER_SIZE, \
TOKEN_TYPES, PENDING, CONSUMER_STATES

from webmachine.managers import ConsumerManager, TokenManager

def generate_random(length=SECRET_SIZE):
    return User.objects.make_random_password(length=length)

class Nonce(models.Model):
    token_key = models.CharField(max_length=KEY_SIZE)
    consumer_key = models.CharField(max_length=KEY_SIZE)
    key = models.CharField(max_length=255)

class Consumer(models.Model):
    name = models.CharField(max_length=255)
    key = models.CharField(max_length=KEY_SIZE)
    secret = models.CharField(max_length=SECRET_SIZE)
    description = models.TextField()
    user = models.ForeignKey(User, null=True, blank=True,
            related_name="consumers_user")
    status = models.SmallIntegerField(choices=CONSUMER_STATES, 
            default=PENDING)

    objects = ConsumerManager()

    def __str__(self):
        data = {'oauth_consumer_key': self.key,
            'oauth_consumer_secret': self.secret}

        return urllib.urlencode(data)

class Token(models.Model):
    key = models.CharField(max_length=KEY_SIZE)
    secret = models.CharField(max_length=SECRET_SIZE)
    token_type = models.SmallIntegerField(choices=TOKEN_TYPES)
    callback = models.CharField(max_length=2048) #URL
    callback_confirmed = models.BooleanField(default=False)
    verifier = models.CharField(max_length=VERIFIER_SIZE)
    consumer = models.ForeignKey(Consumer,
            related_name="tokens_consumer")
    timestamp = models.IntegerField(default=time.time())
    user = models.ForeignKey(User, null=True, blank=True, 
            related_name="tokens_user")
    is_approved = models.BooleanField(default=False)
    
    objects = TokenManager()

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = True
        self.save()

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_random(VERIFIER_SIZE)
        self.save()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback


    def to_string(self, only_key=False):
        token_dict = {
                'oauth_token': self.key, 
                'oauth_token_secret': self.secret,
                'oauth_callback_confirmed': self.callback_confirmed and 'true' or 'error',
        }

        if self.verifier:
            token_dict.update({ 'oauth_verifier': self.verifier })

        if only_key:
            del token_dict['oauth_token_secret']
            del token_dict['oauth_callback_confirmed']

        return urllib.urlencode(token_dict)

########NEW FILE########
__FILENAME__ = resource
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.


"""
all dj-webmachine resources should inherit from the Resource object:

.. code-block:: python

    from webmachine import Resource

    class MyResource(Resource):
        pass 


All Resource methods are of the signature:

.. code-block:: python

    def f(self, req, resp):
        return result

``req`` is a :class:`django.http.HttpRequest` instance, and ``resp`` a
:class:`django.http.HttpResource` instance. This instances have been
:ref:`improved to support more HTTP semantics <http>`. At any time you
can manipulate this object to return the response you want or pass
values to other methods.

There are over 30 Resource methods you can define, but any of them can 
be omitted as they have reasonable defaults.
"""

from __future__ import with_statement
from datetime import datetime
import os
import re
import sys
import traceback
import types

try:
    import json
except ImportError:
    import django.utils.simplejson as json

from django.utils.translation import activate, deactivate_all, get_language, \
string_concat
from django.utils.encoding import smart_str, force_unicode

from webmachine.exc import HTTPException, HTTPInternalServerError
from webmachine.wrappers import WMRequest, WMResponse
from webmachine.decisions import b13, TRANSITIONS, first_match


CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
get_verbose_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', class_name).lower().strip()

DEFAULT_NAMES = ('verbose_name', 'app_label', 'resource_path')

def update_trace(resource, state, req, resp, trace):
    if not resource.trace:
        # do nothing
        return

    infos = {
            "request": {
                "headers": req.headers.items(),
                "get": [(k, req.GET.getlist(k)) for k in req.GET],
                "post": [(k, req.POST.getlist(k)) for k in req.POST],
                "cookies": [(k, req.COOKIES.get(k)) for k in req.COOKIES],
                "url_args": req.url_args,
                "url_kwarg": req.url_kwargs
            },
            "response": {
                "code": resp.status_code,
                "headers": resp.headerlist
            }

    }

    if hasattr(req, 'session'):
        infos['request'].update({
            'session': [(k, req.session.get(k)) for k in \
                    req.session.keys()]
        })

    if isinstance(state, int):
        name = str(state)
    else:
        name = state.__name__

    trace.append((name, infos))

def update_ex_trace(trace, e):
    trace.append(("error", traceback.format_exc()))

def write_trace(res, trace):
    if not res.trace:
        return

    if not res.trace_path:
        trace_path = "/tmp"

    now = datetime.now().replace(microsecond=0).isoformat() + 'Z'
    fname = os.path.join(os.path.abspath(trace_path),
            "wmtrace-%s-%s.json" % (res.__class__.__name__, now))

    with open(fname, "w+b") as f:
        f.write(json.dumps(trace))


class Options(object):
    """ class based on django.db.models.options. We only keep
    useful bits."""
    
    def __init__(self, meta, app_label=None):
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.resource_path = None
        self.object_name, self.app_label = None, app_label
        self.meta = meta
    
    def contribute_to_class(self, cls, name):
        cls._meta = self

        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)
        self.resource_path = self.module_name
        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            setattr(self, 'verbose_name_plural', meta_attrs.pop('verbose_name_plural', 
                string_concat(self.verbose_name, 's')))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta
        
    def __str__(self):
        return "%s.%s" % (smart_str(self.app_label), smart_str(self.module_name))

    def verbose_name_raw(self):
        """
        There are a few places where the untranslated verbose name is needed
        (so that we get the same value regardless of currently active
        locale).
        """
        lang = get_language()
        deactivate_all()
        raw = force_unicode(self.verbose_name)
        activate(lang)
        return raw
    verbose_name_raw = property(verbose_name_raw)


class ResourceMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(ResourceMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, ResourceMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)
            
        new_class = super_new(cls, name, bases, attrs)

        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        
        if getattr(meta, 'app_label', None) is None:
            document_module = sys.modules[new_class.__module__]
            app_label = document_module.__name__.split('.')[-2]
        else:
            app_label = getattr(meta, 'app_label')

        
        new_class.add_to_class('_meta',  Options(meta, app_label=app_label))
        return new_class
    
    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


RESOURCE_METHODS = ["allowed_methods", "allow_missing_post",
"auth_required", "charsets_provided", "content_types_accepted",
"content_types_provided", "created_location", "delete_completed",
"delete_resource", "encodings_provided", "expires", "finish_request",
"forbidden", "format_suffix_accepted", "generate_etag", "is_authorized",
"is_conflict", "known_content_type", "known_methods",
"languages_provided", "last_modified", "malformed_request",
"moved_permanently", "moved_temporarily", "multiple_choices", "options",
"ping", "post_is_create", "previously_existed", "process_post",
"resource_exists", "service_available", "uri_too_long",
"valid_content_headers", "valid_entity_length", "variances"]


# FIXME: we should propbably wrap full HttpRequest object instead of
# adding properties to it in __call__ . Also datetime_utils has surely
# equivalent in Django. 
class Resource(object):
    __metaclass__ = ResourceMeta

    base_url = None
    csrf_exempt = True
    url_regexp = r"^$"

    trace = False
    trace_path = None

    def allowed_methods(self, req, resp):
        """
        If a Method not in this list is requested, then a 
        405 Method Not Allowed will be sent. Note that 
        these are all-caps and are string. 

        :return: [Method] 
        """
        return ["GET", "HEAD"]

    def allow_missing_post(self, req, resp):
        """
        If the resource accepts POST requests to nonexistent resources, 
        then this should return True.

        :return: True or False
        """
        return False

    def auth_required(self, req, resp):
        """
        :return: True or False
        """
        return True
    
    def charsets_provided(self, req, resp):
        """
        If this is anything other than None, it must be a list of pairs 
        where each pair is of the form Charset, Converter where Charset
        is a string naming a charset and Converter is a callable function 
        in the resource which will be called on the produced body in a GET
        and ensure that it is in Charset.

        Ex:
            return [("iso-8859-1", lambda x: x)]
        
        Returning None prevents the character set negotiation
        logic.

        :return: [(Charset, Handler)]
        """
        return None

    def content_types_accepted(self, req, resp):
        """
        This is used similarly to content_types_provided, 
        except that it is for incoming resource representations
        -- for example, PUT requests.

        :return: [(MediaType, Handler)] or None
        """
        return []

    def content_types_provided(self, req, resp):
        """
        This should return a list of pairs where each pair is of the form 
        (Mediatype, Handler) where Mediatype is a string of content-type 
        format and the Handler is an callable function which can provide
        a resource representation in that media type. Content negotiation 
        is driven by this return value. For example, if a client request
        includes an Accept header with a value that does not appear as a 
        first element in any of the return tuples, then a 406 Not Acceptable 
        will be sent.

        :return: [(MediaType, Handler)] or None
        """
        return [
            ("text/html", self.to_html)
        ]

    def created_location(self, req, resp):
        """
        :return: Path or None
        """
        return None

    def delete_completed(self, req, resp):
        """
        This is only called after a successful delete_resource 
        call, and should return false if the deletion was accepted
        but cannot yet be guaranteed to have finished.

        :return: True or False
        """
        return True
    
    def delete_resource(self, req, resp):
        """
        This is called when a DELETE request should be enacted, 
        and should return true if the deletion succeeded.

        :return: True or False
        """
        return False

    def encodings_provided(self, req, resp):
        """\
        This must be a list of pairs where in each pair Encoding 
        is a string naming a valid content encoding and Encoder
        is a callable function in the resource which will be 
        called on the produced body in a GET and ensure that it
        is so encoded. One useful setting is to have the function
        check on method, and on GET requests return [("identity", lambda x: x)] 
        as this is all that is needed to support identity encoding.

            return [("identity", lambda x: x)]

        Returning None prevents the encoding negotiation logic.

        :return: [(Encoding, Encoder)]
        """
        return None

    def expires(self, req, resp):
        """
        :return: Nonr or Date string
        """
        return None
    
    def finish_request(self, req, resp):
        """
        This function, if defined, is called just before the final 
        response is constructed and sent. The Result is ignored, so
        any effect of this function must be by returning a modified 
        request.

        :return: True or False
        """
        return True

    def forbidden(self, req, resp):
        """
        :return: True or False
        """
        return False

    def format_suffix_accepted(self, req, resp):
        """
        Allows you to force the accepted format depending on path
        suffix.

        Ex:  return [("json", "application/json")]
        will allows to force `Accept` header to `application/json` on
        url `/some/url.json` 

        :return: [(Suffix, MediaType)] or None
        """
        return []
    
    def generate_etag(self, req, resp):
        """
        If this returns a value, it will be used as the value of the ETag 
        header and for comparison in conditional requests.

        :return: Str or None
        """
        return None

    def is_authorized(self, req, resp):
        """
        If this returns anything other than true, the response will 
        be 401 Unauthorized. The AuthHead return value will be used 
        as the value in the WWW-Authenticate header.

        :return: True or False
        """
        return True
    
    def is_conflict(self, req, resp):
        """
        If this returns true, the client will receive a 409 Conflict.

        :return: True or False
        """
        return False

    def known_content_type(self, req, resp):
        """
        :return: True or False
        """
        return True

    def known_methods(self, req, resp):
        """
        :return: set([Method])
        """
        return set([
            "GET", "HEAD", "POST", "PUT", "DELETE",
            "TRACE", "CONNECT", "OPTIONS"
        ])

    def languages_provided(self, req, resp):
        """\
        return ["en", "es", "en-gb"]
        
        returning None short circuits the language negotiation

        :return: [Language]
        """
        return None

    def last_modified(self, req, resp):
        """
        :return: DateString or None
        """
        return None

    def malformed_request(self, req, resp):
        """
        :return: True or False
        """
        return False

    def moved_permanently(self, req, resp):
        """
        :return: True Or False
        """
        return False
    
    def moved_temporarily(self, req, resp):
        """
        :return: True or False
        """
        return False
    
    def multiple_choices(self, req, resp):
        """
        If this returns true, then it is assumed that multiple 
        representations of the response are possible and a single
        one cannot be automatically chosen, so a 300 Multiple Choices
        will be sent instead of a 200.

        :return: True or False
        """
        return False

    def options(self, req, resp):
        """
        If the OPTIONS method is supported and is used, the return 
        value of this function is expected to be a list of pairs 
        representing header names and values that should appear 
        in the response.

        :return: [(HeaderName, Value)]
        """
        return []

    def ping(self, req, resp):
        """
        :return: True or False
        """
        return True
    
    def post_is_create(self, req, resp):
        """
        If POST requests should be treated as a request to put content
        into a (potentially new) resource as opposed to being a generic 
        submission for processing, then this function should return true. 
        If it does return true, then created_location will be called and the 
        rest of the request will be treated much like a PUT to the Path 
        entry returned by that call.

        :return: True or False
        """
        return False
    
    def previously_existed(self, req, resp):
        """
        :return: True or False
        """
        return False

    def process_post(self, req, resp):
        """
        If post_is_create returns false, then this will be called to process
        any POST requests. If it succeeds, it should return True.

        :return: True or False
        """
        return False

    def resource_exists(self, req, resp):
        """
        Returning non-true values will result in 404 Not Found.

        :return: True or False
        """
        return True
    
    def service_available(self, req, resp):
        """
        :return: True or False
        """
        return True

    def uri_too_long(self, req, resp):
        """
        :return: True or False
        """
        return False
    
    def valid_content_headers(self, req, resp):
        """
        :return: True or False
        """
        return True
    
    def valid_entity_length(self, req, resp):
        """
        :return: True or False
        """
        return True

    def variances(self, req, resp):
        """
        If this function is implemented, it should return a list 
        of strings with header names that should be included in 
        a given response's Vary header. The standard conneg headers
        (Accept, Accept-Encoding, Accept-Charset, Accept-Language)
        do not need to be specified here as Webmachine will add the
        correct elements of those automatically depending on resource
        behavior.

        :return: True or False
        """
        return []


    def get_urls(self):
        """
        method used to register utls in django urls routing.

        :return: urlpattern
        """
        from django.conf.urls.defaults import patterns, url

        regexp = getattr(self, "url_regexp") or r'^$'

        urlpatterns = patterns('',
            url(regexp, self, name="%s_index" % self.__class__.__name__), 
            
        )
        return urlpatterns


    ###################
    # PRIVATE METHODS #
    ###################

    def _process(self, req, *args, **kwargs):
        """ Process request and return the response """

        req = WMRequest(req.environ, *args, **kwargs)

        # initialize response object
        resp = WMResponse(request=req)

        # force format ?
        url_parts = req.path.rsplit(".", 1)
        try:
            fmt = url_parts[1]
            fctype = first_match(self.format_suffix_accepted, req, resp,
                    fmt)
            if fctype is not None:
                req.META['HTTP_ACCEPT'] = fctype
        except IndexError:
            pass


  
        ctypes = [ct for (ct, func) in (self.content_types_provided(req, resp) or [])]
        if len(ctypes):
            ctype = ctypes[0]
            if not ctype:
                ctype = resp.default_content_type 
            resp.content_type = ctype

        trace = []
        try:
            state = b13
            while not isinstance(state, int):
                if state(self, req, resp):
                    state = TRANSITIONS[state][0]
                else:
                    state = TRANSITIONS[state][1]

                if not isinstance(state, (int, types.FunctionType)):
                    raise HTTPInternalServerError("Invalid state: %r" % state)
                update_trace(self, state, req, resp, trace)                
            resp.status_code = state
        except HTTPException, e:
            # Error while processing request
            # Return HTTP response
            update_ex_trace(trace, e)
            return e
         
        self.finish_request(req, resp)
       
        # write the trace if needed
        write_trace(self, trace)

        # hack, django try to cache all the response and put it in
        # pickle rather than just caching needed infos.
        # since request object isn't pickable, remove it before
        # returning.
        del resp.request
        
        # return final response.
        return resp

    def __call__(self, request, *args, **kwargs):
        return self._process(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = route
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

"""
Minimal Route handling 
++++++++++++++++++++++

Combinating the power of Django and the :ref:`resources <resources>` it's relatively easy to buid an api. The process is also eased using the WM object. dj-webmachine offer a way to create automatically resources by using the ``route`` decorator.

Using this decorator, our helloworld example can be rewritten like that:

.. code-block:: python


    from webmachine import wm

    import json
    @wm.route(r"^$")
    def hello(req, resp):
        return "<html><p>hello world!</p></html>"


    @wm.route(r"^$", provided=[("application/json", json.dumps)])
    def hello_json(req, resp):
        return {"ok": True, "message": "hellow world"}

and the urls.py:

.. code-block:: python

    from django.conf.urls.defaults import *

    import webmachine

    webmachine.autodiscover()

    urlpatterns = patterns('',
        (r'^', include(webmachine.wm.urls))
    )

The autodiscover will detect all resources modules and add then to the
url dispatching. The route decorator works a little like the one in
bottle_ or for that matter flask_ (though bottle was the first). 

This decorator works differently though. It creates full
:class:`webmachine.resource.Resource` instancse registered in the wm
object. So we are abble to provide all the features available in a
resource:

    * settings which content is accepted, provided
    * assiciate serializers to the content types
    * throttling
    * authorization

"""
import webmachine.exc
from webmachine.resource import Resource, RESOURCE_METHODS

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def validate_ctype(value):
    if isinstance(value, basestring):
        return [value]
    elif not isinstance(value, list) and value is not None:
        raise TypeError("'%s' should be a list or a string, got %s" %
                (value, type(value)))
    return value


def serializer_cb(serializer, method):
    if hasattr(serializer, method):
        return getattr(serializer, method)
    return serializer

def build_ctypes(ctypes,method):
    for ctype in ctypes:
        if isinstance(ctype, tuple):
            cb = serializer_cb(ctype[1], method) 
            yield ctype[0], cb
        else:
            yield ctype, lambda v: v


class RouteResource(Resource):

    def __init__(self, pattern, fun, **kwargs):
        self.set_pattern(pattern, **kwargs)

        methods = kwargs.get('methods') or ['GET', 'HEAD']
        if isinstance(methods, basestring):
            methods = [methods]

        elif not isinstance(methods, (list, tuple,)):
            raise TypeError("methods should be list or a tuple, '%s' provided" % type(methods))

        # associate methods to the function
        self.methods = {}
        for m in methods:
            self.methods[m.upper()] = fun

        # build content provided list
        provided = validate_ctype(kwargs.get('provided') or \
                ['text/html'])
        self.provided = list(build_ctypes(provided, "serialize"))

        # build content accepted list
        accepted = validate_ctype(kwargs.get('accepted')) or []
        self.accepted = list(build_ctypes(accepted, "unserialize"))
        self.kwargs = kwargs

        # override method if needed
        for k, v in self.kwargs.items():
            if k in RESOURCE_METHODS:
                setattr(self, k, self.wrap(v))           

    def set_pattern(self, pattern, **kwargs):
        self.url = (pattern, kwargs.get('name'))

    def update(self, fun, **kwargs):
        methods = kwargs.get('methods') or ['GET', 'HEAD']
        if isinstance(methods, basestring):
            methods = [methods]
        elif not isinstance(methods, (list, tuple,)):
            raise TypeError("methods should be list or a tuple, '%s' provided" % type(methods))

        # associate methods to the function
        for m in methods:
            self.methods[m.upper()] = fun

        # we probably should merge here
        provided = validate_ctype(kwargs.get('provided'))
        if provided is not None:
            provided = list(build_ctypes(provided, "serialize"))
            self.provided.extend(provided)
        
        accepted = validate_ctype(kwargs.get('accepted'))
        if accepted is not None:
            accepted = list(build_ctypes(accepted, "unserialize"))
            self.accepted.extend(accepted)


    def wrap(self, f, cb=None):
        def _wrapped(req, resp):
            if cb is not None:
                return cb(f(req, resp))
            return f(req, resp)
        return _wrapped

    def first_match(self, media, expect):
        for key, value in media:
            if key == expect:
                return value
        return None

    def accept_body(self, req, resp):
        ctype = req.content_type or "application/octet-stream"
        mtype = ctype.split(";", 1)[0]
        funload = self.first_match(self.accepted, mtype)
        if funload is None:
            raise webmachine.exc.HTTPUnsupportedMediaType()
        req._raw_post_data = funload(req.raw_post_data)
        if isinstance(req._raw_post_data, basestring):
            req._stream = StringIO(req._raw_post_data)

        fun = self.methods[req.method]
        body = fun(req, resp)
        if isinstance(body, tuple):
            resp._container, resp.location = body
        else:
           resp._container = body

        return self.return_body(req, resp)

    def return_body(self, req, resp):
        fundump = self.first_match(self.provided, resp.content_type)
        if fundump is None:
            raise webmachine.exc.HTTPInternalServerError()
        resp._container = fundump(resp._container)
        if not isinstance(resp._container, basestring):
            resp._is_tring = False
        else:
            resp._container = [resp._container]
            resp._is_string = True
        return resp._container


    #### resources methods

    def allowed_methods(self, req, resp):
        return self.methods.keys()

    def format_suffix_accepted(self, req, resp):
        if 'formats' in self.kwargs:
            return self.kwargs['formats']
        return []

    def content_types_accepted(self, req, resp):
        if not self.accepted:
            return None
        return [(c, self.accept_body) for c, f in self.accepted]
        
    def content_types_provided(self, req, resp):
        fun = self.methods[req.method]
        if not self.provided:
            return [("text/html", self.wrap(fun))]

        return [(c, self.wrap(fun, f)) for c, f in self.provided]

    def delete_resource(self, req, resp):
        fun = self.methods['DELETE']
        ret = fun(req, resp)
        if isinstance(ret, basestring) or hasattr(ret, '__iter__'):
            resp._container = ret
            self.return_body(req, resp)
            return True
        return False

    def post_is_create(self, req, resp):
        if req.method == 'POST':
            return True
        return False

    def created_location(self, req, resp):
        return resp.location

    def process_post(self, req, resp):
        return self.accept_body(req, resp)

    def multiple_choices(self, req, resp):
        return False

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        url_kwargs = self.kwargs.get('url_kwargs') or {}

        if len(self.url) >2:
            url1 =url(self.url[0], self, name=self.url[1], kwargs=url_kwargs)
        else:
            url1 =url(self.url[0], self, kwargs=url_kwargs)

        return patterns('', url1)


class WM(object):

    def __init__(self, name="webmachine", version=None):
        self.name = name
        self.version = version
        self.resources = {}
        self.routes = []

    def route(self, pattern, **kwargs):
        """
        A decorator that is used to register a new resource using
        this function to return response.

        **Parameters**

        :attr pattern: regular expression, like the one you give in
        your urls.py

        :attr methods: methods accepted on this function

        :attr provides: list of provided contents tpes and associated
        serializers::

            [(MediaType, Handler)]


        :attr accepted: list of content you accept in POST/PUT with
        associated deserializers::

            [(MediaType, Handler)]


        A serializer can be a simple callable taking a value or a class:

        .. code-block:: python

            class Myserializer(object):

                def unserialize(self, value):
                    # ... do something to value
                    return value

                def serialize(self, value):
                    # ... do something to value
                    return value


        :attr formats: return a list of format with their associated 
        contenttype::

            [(Suffix, MediaType)]

        :attr kwargs: any named parameter coresponding to a
        :ref:`resource method <resource>`. Each value is a callable
        taking a request and a response as arguments:

        .. code-block:: python

            def f(req, resp):
                pass

        """
        def _decorated(func):
            self.add_route(pattern, func, **kwargs)
            return func
        return _decorated

    def _wrap_urls(self, f, pattern):
        from django.conf.urls.defaults import patterns, url, include
        def _wrapped(*args):
            return patterns('', 
                    url(pattern, include(f(*args)))
            )
        return _wrapped

    def add_resource(self, klass, pattern=None):
        """
        Add one :ref:`Resource class<resource>` to the routing.

        :attr klass: class inheriting from :class:webmachine.Resource
        :attr pattern: regexp.

        """
        res = klass()
        if not pattern:
            if hasattr(res._meta, "resource_path"):
                kname = res._meta.resource_path
            else:
                kname = klass.__name__.lower()

            pattern = r'^%s/' % res._meta.app_label
            if kname:
                pattern = r'%s/' % kname
        res.get_urls = self._wrap_urls(res.get_urls, pattern)
        self.resources[pattern] = res

    def add_resources(self, *klasses):
        """
        Allows you to add multiple Resource classes to the WM instance. You
        can also pass a pattern by using a tupple instead of simply
        provided the Resource class. Example::

            (MyResource, r"^some/path$")

        """
        for klass in klasses:
            if isinstance(klass, tuple):
                klass, pattern = klass
            else:
                pattern = None
            self.add_resource(klass, pattern=pattern)

    def add_route(self, pattern, func, **kwargs):
        if pattern in self.resources:
            res = self.resources[pattern]
            res.update(func, **kwargs)
        else:
            res = RouteResource(pattern, func, **kwargs)
        self.resources[pattern] = res

        self.routes.append((pattern, func, kwargs))
        # associate the resource to the function
        setattr(func, "_wmresource", res)


    def get_urls(self):
        from django.conf.urls.defaults import patterns
        urlpatterns = patterns('')
        for pattern, resource in self.resources.items():
            urlpatterns += resource.get_urls()
        return urlpatterns

    urls = property(get_urls)

wm = WM()

########NEW FILE########
__FILENAME__ = throttle
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import time

from django.core.cache import cache

class Limiter(object):

    def __init__(self, res, **options):
        self.res = res
        self.options = options

    def allowed(self, request):
        if self.whitelisted(request):
            return True
        elif self.blacklisted(request):
            return False
        return True

    def whitelisted(self, request):
        return False

    def blacklisted(self, request):
        return False

    def client_identifier(self, request):
        if request.user.is_authenticated:
            ident = request.user.username
        else:
            ident = request.META.get("REMOTE_ADDR", None)
        if not ident:
            return ''

        ident = "%s,%s" % (self.res.__class__.__name__, ident)
        return ident

    def cache_get(self, key, default=None):
        return cache.get(key, default)

    def cache_set(self, key, value, expires):
        return cache.set(key, value, expires)

    def cache_key(self, request):
        if not "key_prefix" in self.options:
            return self.client_identifier()
        key = "%s:%s" % (self.options.get("key_prefix"), 
                self.client_identifier())
        return key


class Interval(Limiter):
    """
    This rate limiter strategy throttles the application by enforcing a
    minimum interval (by default, 1 second) between subsequent allowed HTTP
    requests.

    ex::
        from webmachine import Resource
        from webmachine.throttle import Interval
        
        class MyResource(Resource):
            ...

            def forbidden(self, req, resp):
                return Interval(self).allowed(req)
    """

    def allowed(self, request):
        t1 = time.time()
        key = self.cache_key(request)
        t0 = self.cache_get(key)
        allowed = not t0 or (t1 - t0) >= self.min_interval()
        try:
            self.cache_set(key, t1) 
        except:
            return True
        return allowed

    def min_interval(self):
        return "min" in self.options and self.options.get("min") or 1

class TimeWindow(Limiter):
    """
    Return ```true``` if fewer than maximum number of requests
    permitted for the current window of time have been made.
    """

    def allowed(self, request):
        t1 = time.time()
        key = self.cache_key(request)
        count = int(self.cache_get(key) or 0)
        allowed = count <= self.max_per_window()
        try:
            self.cache_set(key, t1) 
        except:
            return True
        return allowed

    def max_per_window(self):
        raise NotImplementedError


class Daily(TimeWindow):
    """ 
    This rate limiter strategy throttles the application by defining a
    maximum number of allowed HTTP requests per day (by default, 86,400
    requests per 24 hours, which works out to an average of 1 request per
    second).

    Note that this strategy doesn't use a sliding time window, but rather
    tracks requests per calendar day. This means that the throttling counter
    is reset at midnight (according to the server's local timezone) every
    night.

    ex::
        from webmachine import Resource
        from webmachine.throttle import Daily
        
        class MyResource(Resource):
            ...

            def forbidden(self, req, resp):
                return Daily(self).allowed(req)    
    """

    def max_per_window(self):
        return "max" in self.options and self.options.get(max) or 86400

    def cache_key(self, request):
        return "%s:%s" % (super(Daily, self).cache_key(request),
                time.strftime('%Y-%m-%d'))

class Hourly(TimeWindow):
    """
    This rate limiter strategy throttles the application by defining a
    maximum number of allowed HTTP requests per hour (by default, 3,600
    requests per 60 minutes, which works out to an average of 1 request per
    second).

    Note that this strategy doesn't use a sliding time window, but rather
    tracks requests per distinct hour. This means that the throttling
    counter is reset every hour on the hour (according to the server's local
    timezone).

    ex::
        from webmachine import Resource
        from webmachine.throttle import Hourly
        
        class MyResource(Resource):
            ...

            def forbidden(self, req, resp):
                return Hourly(self).allowed(req)    
    """

    def max_per_window(self):
        return "max" in self.options and self.options.get(max) or 3600

    def cache_key(self, request):
        return "%s:%s" % (super(Daily, self).cache_key(request),
                time.strftime('%Y-%m-%dT%H'))


########NEW FILE########
__FILENAME__ = const
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

from django.utils.translation import ugettext_lazy as _

VERIFIER_SIZE = 16
KEY_SIZE = 32
SECRET_SIZE = 32 

# token types
TOKEN_REQUEST  = 2
TOKEN_ACCESS = 1

TOKEN_TYPES = (
    (TOKEN_ACCESS, _("Access")),
    (TOKEN_REQUEST, _("Request"))
)

# consumer states
PENDING = 1
ACCEPTED = 2
CANCELED = 3
REJECTED = 4

CONSUMER_STATES = (
    (PENDING,  _('Pending')),
    (ACCEPTED, _('Accepted')),
    (CANCELED, _('Canceled')),
    (REJECTED, _('Rejected')),
)

########NEW FILE########
__FILENAME__ = wmtrace
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

import os
import os.path
from glob import iglob

try:
    import json
except ImportError:
    import django.utils.simplejson as json

from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.views import static
from webmachine import Resource

class WMTraceResource(Resource):

    def __init__(self, path="/tmp"):
        if path.endswith("/"):
            path = path[:-1]
        self.path = os.path.abspath(path)
    
    def trace_list_html(self, req, resp):
        files = [os.path.basename(f).split("wmtrace-")[1] for f in \
                iglob("%s/wmtrace-*.*" % self.path)]
        return render_to_string("wm/wmtrace_list.html", {
            "path": self.path, 
            "files": files
        })

    def trace_html(self, req, resp):
        fname = req.url_kwargs["file"]
        fname = os.path.join(self.path, "wmtrace-%s" % fname)
        with open(fname, "r+b") as f:
            return render_to_string("wm/wmtrace.html", {
                "fname": fname,
                "trace": f.read()
            })

    def to_html(self, req, resp):
        if "file" in req.url_kwargs:
            return self.trace_html(req, resp)
        return self.trace_list_html(req, resp)


    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        media_path = os.path.abspath(os.path.join(__file__, "..",
            "media"))
        print media_path
        urlpatterns = patterns('',
            url(r'wmtrace-(?P<file>.+)$', self, name="wmtrace"),
            url(r'^static/(?P<path>.*)', static.serve, {
                'document_root': media_path,
                'show_indexes': False
            }),
            url(r'$', self, name="wmtrace_list"),
            
        )

        return urlpatterns


########NEW FILE########
__FILENAME__ = wrappers
# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.
import re

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from webob import Request
from webob.descriptors import *
from webob.datetime_utils import *
from webob.headers import ResponseHeaders


_PARAM_RE = re.compile(r'([a-z0-9]+)=(?:"([^"]*)"|([a-z0-9_.-]*))', re.I)
_OK_PARAM_RE = re.compile(r'^[a-z0-9_.-]+$', re.I)

class WMRequest(WSGIRequest, Request):

    environ = None
    path = None
    method = None
    META = None

    def __init__(self, environ, *args, **kwargs):
        Request.__init__(self, environ)
        WSGIRequest.__init__(self, environ)

        # add path args args to the request
        self.url_args = args or []
        self.url_kwargs = kwargs or {}

    webob_POST = Request.POST
    webob_WGET = Request.GET

    @property
    def str_POST(self):

        clength = self.environ.get('CONTENT_LENGTH')
        try:
            return super(WMRequest, self).str_POST
        finally:
            self.environ['CONTENT_LENGTH'] = clength
            self._seek_input()

    def _load_post_and_files(self):
        try:
            return WSGIRequest._load_post_and_files(self)
        finally:
            # "Resetting" the input so WebOb will read it:
            self._seek_input()
    
    def _seek_input(self):
        if "wsgi.input" in self.environ:
            try:
                self.environ['wsgi.input'].seek(0)
            except AttributeError:
                pass

class WMResponse(HttpResponse):
    """ Add some properties to HttpResponse """

    status_code = 200

    default_content_type = 'text/html'
    default_charset = 'UTF-8'
    unicode_errors = 'strict'
    default_conditional_response = False

    def __init__(self, content='', mimetype=None, status=None,
            content_type=None, request=None):
        if isinstance(status, basestring):
            (status_code, status_reason) = status.split(" ", 1)
            status_code = int(status_code)
            self.status_reason = status_reason or None
        else:
            status_code = status
            self.status_reason = None

        self.request = request
        self._headerlist = []

        HttpResponse.__init__(self, content=content, mimetype=mimetype, 
                status=status_code, content_type=content_type)

        

    def _headerlist__get(self):
        """
        The list of response headers
        """
        return self._headers.values()

    def _headerlist__set(self, value):
        self._headers = {}
        if not isinstance(value, list):
            if hasattr(value, 'items'):
                value = value.items()
            value = list(value)
        
        headers = ResponseHeaders.view_list(self.headerlist)
        for hname in headers.keys():
            self._headers[hname.lower()] = (hname, headers[hname])
        self._headerlist = value


    def _headerlist__del(self):
        self.headerlist = []
        self._headers = {}

    headerlist = property(_headerlist__get, _headerlist__set, _headerlist__del, doc=_headerlist__get.__doc__)

    def __setitem__(self, header, value):
        header, value = self._convert_to_ascii(header, value)
        self._headers[header.lower()] = (header, value)

    def __delitem__(self, header):
        try:
            del self._headers[header.lower()]
        except KeyError:
            return

    def __getitem__(self, header):
        return self._headers[header.lower()][1]

    allow = list_header('Allow', '14.7')
    ## FIXME: I realize response.vary += 'something' won't work.  It should.
    ## Maybe for all listy headers.
    vary = list_header('Vary', '14.44')

    content_length = converter(
        header_getter('Content-Length', '14.17'),
        parse_int, serialize_int, 'int')

    content_encoding = header_getter('Content-Encoding', '14.11')
    content_language = list_header('Content-Language', '14.12')
    content_location = header_getter('Content-Location', '14.14')
    content_md5 = header_getter('Content-MD5', '14.14')
    # FIXME: a special ContentDisposition type would be nice
    content_disposition = header_getter('Content-Disposition', '19.5.1')

    accept_ranges = header_getter('Accept-Ranges', '14.5')
    content_range = converter(
        header_getter('Content-Range', '14.16'),
        parse_content_range, serialize_content_range, 'ContentRange object')

    date = date_header('Date', '14.18')
    expires = date_header('Expires', '14.21')
    last_modified = date_header('Last-Modified', '14.29')

    etag = converter(
        header_getter('ETag', '14.19'),
        parse_etag_response, serialize_etag_response, 'Entity tag')

    location = header_getter('Location', '14.30')
    pragma = header_getter('Pragma', '14.32')
    age = converter(
        header_getter('Age', '14.6'),
        parse_int_safe, serialize_int, 'int')

    retry_after = converter(
        header_getter('Retry-After', '14.37'),
        parse_date_delta, serialize_date_delta, 'HTTP date or delta seconds')

    server = header_getter('Server', '14.38')

    #
    # charset
    #

    def _charset__get(self):
        """
        Get/set the charset (in the Content-Type)
        """
        header = self._headers.get('content-type')
        if not header:
            return None
        match = CHARSET_RE.search(header[1])
        if match:
            return match.group(1)
        return None

    def _charset__set(self, charset):
        if charset is None:
            del self.charset
            return
        try:
            hname, header = self._headers.pop('content-type')
        except KeyError:
            raise AttributeError(
                    "You cannot set the charset when no content-type is defined")
            match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        header += '; charset=%s' % charset
        self._headers['content-type'] = hname, header

    def _charset__del(self):
        try:
            hname, header = self._headers.pop('content-type')
        except KeyError:
            # Don't need to remove anything
            return
        match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        self[hname] = header

    charset = property(_charset__get, _charset__set, _charset__del, doc=_charset__get.__doc__)


    #
    # content_type
    #

    def _content_type__get(self):
        """
        Get/set the Content-Type header (or None), *without* the
        charset or any parameters.

        If you include parameters (or ``;`` at all) when setting the
        content_type, any existing parameters will be deleted;
        otherwise they will be preserved.
        """
        header = self._headers.get('content-type')

        if not header:
            return None
        return header[1].split(';', 1)[0]

    def _content_type__set(self, value):
        if ';' not in value:
            if 'content-type' in self._headers:
                header = self._headers.get('content-type')
                if ';' in header[1]:
                    params = header[1].split(';', 1)[1]
                    value += ';' + params
        self['Content-Type'] = value

    def _content_type__del(self):
        try:
            del self._headers['content-type']
        except KeyError:
            pass

    content_type = property(_content_type__get, _content_type__set,
            _content_type__del, doc=_content_type__get.__doc__)


    #
    # content_type_params
    #

    def _content_type_params__get(self):
        """
        A dictionary of all the parameters in the content type.

        (This is not a view, set to change, modifications of the dict would not be
        applied otherwise)
        """
        if not 'content-type' in self._headers:
            return {}

        params = self._headers.get('content-type')
        if ';' not in params[1]:
            return {}
        params = params[1].split(';', 1)[1]
        result = {}
        for match in _PARAM_RE.finditer(params):
            result[match.group(1)] = match.group(2) or match.group(3) or ''
        return result

    def _content_type_params__set(self, value_dict):
        if not value_dict:
            del self.content_type_params
            return
        params = []
        for k, v in sorted(value_dict.items()):
            if not _OK_PARAM_RE.search(v):
                ## FIXME: I'm not sure what to do with "'s in the parameter value
                ## I think it might be simply illegal
                v = '"%s"' % v.replace('"', '\\"')
            params.append('; %s=%s' % (k, v))
        ct = self._headers.pop('content-type')
        if not ct:
            ct = ''
        else:
            ct = ct[1].split(';', 1)[0]
        ct += ''.join(params)
        self._headers['content-type'] = 'Content-Type', ct

    def _content_type_params__del(self, value):
        try:
            header = self._headers['content-type']
        except KeyError:
            return

        self._headers['content-type'] = header[0], header[1].split(';', 1)[0]

    content_type_params = property(
            _content_type_params__get,
            _content_type_params__set,
            _content_type_params__del,
            doc=_content_type_params__get.__doc__
            )


########NEW FILE########
