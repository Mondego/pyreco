__FILENAME__ = models
from django.db import models
from guardian.models import UserObjectPermissionBase
from guardian.models import GroupObjectPermissionBase


class TestModel(models.Model):
    name = models.CharField(max_length=128)



class DirectUser(UserObjectPermissionBase):
    content_object = models.ForeignKey('TestDirectModel')


class DirectGroup(GroupObjectPermissionBase):
    content_object = models.ForeignKey('TestDirectModel')


class TestDirectModel(models.Model):
    name = models.CharField(max_length=128)


########NEW FILE########
__FILENAME__ = run_benchmarks
#!/usr/bin/env python
"""
This benchmark package should be treated as work-in-progress, not a production
ready benchmarking solution for django-guardian.
"""
import datetime
import os
import random
import string
import sys

abspath = lambda *p: os.path.abspath(os.path.join(*p))

THIS_DIR = abspath(os.path.dirname(__file__))
ROOT_DIR = abspath(THIS_DIR, '..')

# so the preferred guardian module is one within this repo and
# not system-wide
sys.path.insert(0, ROOT_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = 'benchmarks.settings'
from benchmarks import settings
from guardian.shortcuts import assign_perm

settings.DJALOG_LEVEL = 40
settings.INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sites',
    'guardian',
    'benchmarks',
)

from utils import show_settings
from django.contrib.auth.models import User, Group
from django.utils.termcolors import colorize
from benchmarks.models import TestModel
from benchmarks.models import TestDirectModel

USERS_COUNT = 50
OBJECTS_COUNT = 1000
OBJECTS_WIHT_PERMS_COUNT = 1000

def random_string(length=25, chars=string.ascii_letters+string.digits):
    return ''.join(random.choice(chars) for i in range(length))


class Call(object):
    def __init__(self, args, kwargs, start=None, finish=None):
        self.args = args
        self.kwargs = kwargs
        self.start = start
        self.finish = finish

    def delta(self):
        return self.finish - self.start


class Timed(object):

    def __init__(self, action=None):
        self.action = action

    def __call__(self, func):

        if not hasattr(func, 'calls'):
            func.calls = []

        def wrapper(*args, **kwargs):
            if self.action:
                print(" -> [%s]" % self.action)
            start = datetime.datetime.now()
            call = Call(list(args), dict(kwargs), start)
            try:
                return func(*args, **kwargs)
            finally:
                call.finish = datetime.datetime.now()
                func.calls.append(call)
                if self.action:
                    print(" -> [%s] Done (Total time: %s)" % (self.action,
                        call.delta()))
        return wrapper


class Benchmark(object):

    def __init__(self, name, users_count, objects_count,
            objects_with_perms_count, model):
        self.name = name
        self.users_count = users_count
        self.objects_count = objects_count
        self.objects_with_perms_count = objects_with_perms_count

        self.Model = model
        self.perm = 'auth.change_%s' % model._meta.module_name

    def info(self, msg):
        print(colorize(msg + '\n', fg='green'))

    def prepare_db(self):
        from django.core.management import call_command
        call_command('syncdb', interactive=False)

        for model in [User, Group, self.Model]:
            model.objects.all().delete()

    @Timed("Creating users")
    def create_users(self):
        User.objects.bulk_create(User(id=x, username=random_string().capitalize())
            for x in range(self.users_count))

    @Timed("Creating objects")
    def create_objects(self):
        Model = self.Model
        Model.objects.bulk_create(Model(id=x, name=random_string(20))
            for x in range(self.objects_count))

    @Timed("Grant permissions")
    def grant_perms(self):
        ids = range(1, self.objects_count)
        for user in User.objects.iterator():
            for x in xrange(self.objects_with_perms_count):
                obj = self.Model.objects.get(id=random.choice(ids))
                self.grant_perm(user, obj, self.perm)

    def grant_perm(self, user, obj, perm):
        assign_perm(perm, user, obj)

    @Timed("Check permissions")
    def check_perms(self):
        ids = range(1, self.objects_count)
        for user in User.objects.iterator():
            for x in xrange(self.objects_with_perms_count):
                obj = self.Model.objects.get(id=random.choice(ids))
                self.check_perm(user, obj, self.perm)

    def check_perm(self, user, obj, perm):
        user.has_perm(perm, obj)

    @Timed("Benchmark")
    def main(self):
        self.info('=' * 80)
        self.info(self.name.center(80))
        self.info('=' * 80)
        self.prepare_db()
        self.create_users()
        self.create_objects()
        self.grant_perms()
        self.check_perms()


def main():
    show_settings(settings, 'benchmarks')
    benchmark = Benchmark('Direct relations benchmark',
        USERS_COUNT, OBJECTS_COUNT, OBJECTS_WIHT_PERMS_COUNT, TestDirectModel)
    benchmark.main()

    benchmark = Benchmark('Generic relations benchmark',
        USERS_COUNT, OBJECTS_COUNT, OBJECTS_WIHT_PERMS_COUNT, TestModel)
    benchmark.main()

if __name__ == '__main__':
    main()




########NEW FILE########
__FILENAME__ = settings
import os
import sys

abspath = lambda *p: os.path.abspath(os.path.join(*p))

THIS_DIR = abspath(os.path.dirname(__file__))
ROOT_DIR = abspath(THIS_DIR, '..')

# so the preferred guardian module is one within this repo and
# not system-wide
sys.path.insert(0, ROOT_DIR)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sites',
    'guardian',
    'benchmarks',
)


ANONYMOUS_USER_ID = -1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'guardian_benchmarks',
        'USER': 'guardian_bench',
        'PASSWORD': 'guardian_bench',
    },
}


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-guardian documentation build configuration file, created by
# sphinx-quickstart on Thu Feb 18 23:18:28 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'guardian.testsettings'
ANONYMOUS_USER_ID = -1 # Required by guardian
guardian = __import__('guardian')

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'exts']
try:
    import rst2pdf
    if rst2pdf.version >= '0.16':
        extensions.append('rst2pdf.pdfbuilder')
except ImportError:
    print("[NOTE] In order to build PDF you need rst2pdf with version >=0.16")


autoclass_content = "both"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-guardian'
copyright = u'2010-2013, Lukasz Balcerzak'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = guardian.get_version()
# The full version, including alpha/beta/rc tags.
release = guardian.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['build']

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
#html_theme = 'default'
# Theme URL: https://github.com/coordt/ADCtheme/
RTD_NEW_THEME = True
html_theme = 'rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['theme']

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
html_static_path = ['theme/rtd_theme/static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'guardiandoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'guardian.tex', u'guardian Documentation',
   u'Lukasz Balcerzak', 'manual'),
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

pdf_documents = [
    ('index', u'django-guardian', u'Documentation for django-guardian',
        u'Lukasz Balcerzak'),
]
pdf_stylesheets = ['sphinx','kerning','a4']
pdf_break_level = 2
pdf_inline_footnotes = True
#pdf_extensions = ['vectorpdf', 'dotted_toc']


########NEW FILE########
__FILENAME__ = exts

def setup(app):
    app.add_crossref_type(
        directivename = "admin",
        rolename      = "admin",
        indextemplate = "pair: %s; admin",
    )
    app.add_crossref_type(
        directivename = "command",
        rolename      = "command",
        indextemplate = "pair: %s; command",
    )
    app.add_crossref_type(
        directivename = "form",
        rolename      = "form",
        indextemplate = "pair: %s; form",
    )
    app.add_crossref_type(
        directivename = "manager",
        rolename      = "manager",
        indextemplate = "pair: %s; manager",
    )
    app.add_crossref_type(
        directivename = "mixin",
        rolename      = "mixin",
        indextemplate = "pair: %s; mixin",
    )
    app.add_crossref_type(
        directivename = "model",
        rolename      = "model",
        indextemplate = "pair: %s; model",
    )
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "shortcut",
        rolename      = "shortcut",
        indextemplate = "pair: %s; shortcut",
    )


########NEW FILE########
__FILENAME__ = context_processors
import guardian

def version(request):
    return {'version': guardian.get_version()}


########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import AbstractUser
from django.db import models
import datetime


class CustomUser(AbstractUser):
    real_username = models.CharField(max_length=120, unique=True)
    birth_date = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'real_username'

    def save(self, *args, **kwargs):
        if not self.real_username:
            self.real_username = self.username
        return super(CustomUser, self).save(*args, **kwargs)


def get_custom_anon_user(User):
    return User(
        real_username='AnonymousUser',
        birth_date=datetime.date(1410, 7, 15),
    )

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from guardian.conf import settings
from guardian.compat import get_user_model
from guardian.management import create_anonymous_user


User = get_user_model()


class CustomUserTests(TestCase):
    def test_create_anonymous_user(self):
        create_anonymous_user(object())
        self.assertEqual(1, User.objects.all().count())
        anonymous = User.objects.all()[0]
        self.assertEqual(anonymous.pk, settings.ANONYMOUS_USER_ID)


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import django
import os
import sys

if django.VERSION < (1, 5):
    sys.stderr.write("ERROR: guardian's example project must be run with "
                     "Django 1.5 or later!\n")
    sys.exit(1)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from example_project.posts.models import Post

from guardian.admin import GuardedModelAdmin


class PostAdmin(GuardedModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'slug', 'created_at')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

admin.site.register(Post, PostAdmin)


########NEW FILE########
__FILENAME__ = models
from django.db import models


class Post(models.Model):
    title = models.CharField('title', max_length=64)
    slug = models.SlugField(max_length=64)
    content = models.TextField('content')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        permissions = (
            ('view_post', 'Can view post'),
        )
        get_latest_by = 'created_at'

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('posts_post_detail', (), {'slug': self.slug})


########NEW FILE########
__FILENAME__ = urls
from guardian.compat import url, patterns


urlpatterns = patterns('posts.views',
    url(r'^$', view='post_list', name='posts_post_list'),
    url(r'^(?P<slug>[-\w]+)/$', view='post_detail', name='posts_post_detail'),
)


########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.models import Group
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic import ListView
from django.template import RequestContext
from guardian.decorators import permission_required_or_403
from guardian.compat import get_user_model

from .models import Post

User = get_user_model()


class PostList(ListView):
    model = Post
    context_object_name = 'posts'

post_list = PostList.as_view()


@permission_required_or_403('posts.view_post', (Post, 'slug', 'slug'))
def post_detail(request, slug, **kwargs):
    data = {
        'post': get_object_or_404(Post, slug=slug),
        'users': User.objects.all(),
        'groups': Group.objects.all(),
    }
    return render_to_response('posts/post_detail.html', data,
        RequestContext(request))


########NEW FILE########
__FILENAME__ = settings
import django
import os
import sys

from django.conf import global_settings

abspath = lambda *p: os.path.abspath(os.path.join(*p))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SECRET_KEY = 'CHANGE_THIS_TO_SOMETHING_UNIQUE_AND_SECURE'

TEST_SOUTH = 'GUARDIAN_TEST_SOUTH' in os.environ

PROJECT_ROOT = abspath(os.path.dirname(__file__))
GUARDIAN_MODULE_PATH = abspath(PROJECT_ROOT, '..')
sys.path.insert(0, GUARDIAN_MODULE_PATH)
sys.path.insert(0, PROJECT_ROOT)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': abspath(PROJECT_ROOT, '.hidden.db'),
        'TEST_NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'guardian',
    'guardian.testapp',
    'posts',
    'core',
    'integration_tests',
)
if django.VERSION < (1, 3):
    INSTALLED_APPS += ('staticfiles',)
else:
    INSTALLED_APPS += ('django.contrib.staticfiles',)

if 'GUARDIAN_NO_TESTS_APP' in os.environ:
    _apps = list(INSTALLED_APPS)
    _apps.remove('guardian.testapp')
    INSTALLED_APPS = tuple(_apps)

if TEST_SOUTH:
    INSTALLED_APPS += ('south',)
if 'GRAPPELLI' in os.environ:
    try:
        __import__('grappelli')
        INSTALLED_APPS = ('grappelli',) + INSTALLED_APPS
    except ImportError:
        print("django-grappelli not installed")

try:
    import rosetta
    INSTALLED_APPS += ('rosetta',)
except ImportError:
    pass

#MIDDLEWARE_CLASSES = (
    #'django.middleware.common.CommonMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    #'django.middleware.transaction.TransactionMiddleware',
#)

STATIC_ROOT = abspath(PROJECT_ROOT, '..', 'public', 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = [abspath(PROJECT_ROOT, 'static')]
MEDIA_ROOT = abspath(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = STATIC_URL + 'grappelli/'

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'example_project.context_processors.version',
    'django.core.context_processors.static',
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

SITE_ID = 1

USE_I18N = True
USE_L10N = True

LOGIN_REDIRECT_URL = '/'

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

ANONYMOUS_USER_ID = -1
GUARDIAN_GET_INIT_ANONYMOUS_USER = 'core.models.get_custom_anon_user'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)

# Neede as some models (located at guardian/tests/models.py)
# are not migrated for tests
SOUTH_TESTS_MIGRATE = TEST_SOUTH

AUTH_USER_MODEL = 'core.CustomUser'

try:
    from conf.localsettings import *
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = urls
from guardian.compat import include, url, patterns, handler404, handler500
from django.conf import settings
from django.contrib import admin

__all__ = ['handler404', 'handler500']


admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'},
        name='logout'),
    (r'^', include('example_project.posts.urls')),
)

if 'grappelli' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        (r'^grappelli/', include('grappelli.urls')),
    )

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns = patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
    ) + urlpatterns

########NEW FILE########
__FILENAME__ = extras
import _ast
import os
import sys
from setuptools import Command
#from pyflakes.scripts import pyflakes as flakes


def check(filename):
    from pyflakes import reporter as mod_reporter
    from pyflakes.checker import Checker
    codeString = open(filename).read()
    reporter = mod_reporter._makeDefaultReporter()
    # First, compile into an AST and handle syntax errors.
    try:
        tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
    except SyntaxError:
        value = sys.exc_info()[1]
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            reporter.unexpectedError(filename, 'problem decoding source')
        else:
            reporter.syntaxError(filename, msg, lineno, offset, text)
        return 1
    except Exception:
        reporter.unexpectedError(filename, 'problem decoding source')
        return 1
    else:
        # Okay, it's syntactically valid.  Now check it.
        lines = codeString.splitlines()
        warnings = Checker(tree, filename)
        warnings.messages.sort(key=lambda m: m.lineno)
        real_messages = []
        for m in warnings.messages:
            line = lines[m.lineno - 1]
            if 'pyflakes:ignore' in line.rsplit('#', 1)[-1]:
                # ignore lines with pyflakes:ignore
                pass
            else:
                real_messages.append(m)
                reporter.flake(m)
        return len(real_messages)

class RunFlakesCommand(Command):
    """
    Runs pyflakes against guardian codebase.
    """
    description = "Check sources with pyflakes"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            import pyflakes # pyflakes:ignore
        except ImportError:
            sys.stderr.write("No pyflakes installed!\n")
            sys.exit(-1)
        thisdir = os.path.dirname(__file__)
        guardiandir = os.path.join(thisdir, 'guardian')
        warns = 0
        # Define top-level directories
        for topdir, dirnames, filenames in os.walk(guardiandir):
            paths = (os.path.join(topdir, f) for f in filenames if f .endswith('.py'))
            for path in paths:
                if path.endswith('tests/__init__.py'):
                    # ignore that module (it should only gather test cases with *)
                    continue
                warns += check(path)
        if warns > 0:
            sys.stderr.write("ERROR: Finished with total %d warnings.\n" % warns)
            sys.exit(1)
        else:
            print("No problems found in source codes.")



########NEW FILE########
__FILENAME__ = admin
from __future__ import unicode_literals

from django import forms
from django.conf import settings
from guardian.compat import url, patterns
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext, ugettext_lazy as _

from guardian.compat import get_user_model
from guardian.forms import UserObjectPermissionsForm
from guardian.forms import GroupObjectPermissionsForm
from guardian.shortcuts import get_perms
from guardian.shortcuts import get_users_with_perms
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_perms_for_model
from guardian.models import Group


class AdminUserObjectPermissionsForm(UserObjectPermissionsForm):
    """
    Extends :form:`UserObjectPermissionsForm`. It only overrides
    ``get_obj_perms_field_widget`` method so it return
    ``django.contrib.admin.widgets.FilteredSelectMultiple`` widget.
    """
    def get_obj_perms_field_widget(self):
        return FilteredSelectMultiple(_("Permissions"), False)


class AdminGroupObjectPermissionsForm(GroupObjectPermissionsForm):
    """
    Extends :form:`GroupObjectPermissionsForm`. It only overrides
    ``get_obj_perms_field_widget`` method so it return
    ``django.contrib.admin.widgets.FilteredSelectMultiple`` widget.
    """
    def get_obj_perms_field_widget(self):
        return FilteredSelectMultiple(_("Permissions"), False)


class GuardedModelAdminMixin(object):
    """
    Serves as a helper for custom subclassing ``admin.ModelAdmin``.
    """
    change_form_template = \
        'admin/guardian/model/change_form.html'
    obj_perms_manage_template = \
        'admin/guardian/model/obj_perms_manage.html'
    obj_perms_manage_user_template = \
        'admin/guardian/model/obj_perms_manage_user.html'
    obj_perms_manage_group_template = \
        'admin/guardian/model/obj_perms_manage_group.html'
    user_can_access_owned_objects_only = False
    user_owned_objects_field = 'user'
    user_can_access_owned_by_group_objects_only = False
    group_owned_objects_field = 'group'
    include_object_permissions_urls = True

    def queryset(self, request):
        qs = super(GuardedModelAdminMixin, self).queryset(request)
        if request.user.is_superuser:
            return qs

        if self.user_can_access_owned_objects_only:
            filters = {self.user_owned_objects_field: request.user}
            qs = qs.filter(**filters)
        if self.user_can_access_owned_by_group_objects_only:
            User = get_user_model()
            user_rel_name = User.groups.field.related_query_name()
            qs_key = '%s__%s' % (self.group_owned_objects_field, user_rel_name)
            filters = {qs_key: request.user}
            qs = qs.filter(**filters)
        return qs


    def get_urls(self):
        """
        Extends standard admin model urls with the following:

        - ``.../permissions/`` under ``app_mdodel_permissions`` url name (params: object_pk)
        - ``.../permissions/user-manage/<user_id>/`` under ``app_model_permissions_manage_user`` url name (params: object_pk, user_pk)
        - ``.../permissions/group-manage/<group_id>/`` under ``app_model_permissions_manage_group`` url name (params: object_pk, group_pk)

        .. note::
           ``...`` above are standard, instance detail url (i.e.
           ``/admin/flatpages/1/``)

        """
        urls = super(GuardedModelAdminMixin, self).get_urls()
        if self.include_object_permissions_urls:
            info = self.model._meta.app_label, self.model._meta.module_name
            myurls = patterns('',
                url(r'^(?P<object_pk>.+)/permissions/$',
                    view=self.admin_site.admin_view(self.obj_perms_manage_view),
                    name='%s_%s_permissions' % info),
                url(r'^(?P<object_pk>.+)/permissions/user-manage/(?P<user_id>\-?\d+)/$',
                    view=self.admin_site.admin_view(
                        self.obj_perms_manage_user_view),
                    name='%s_%s_permissions_manage_user' % info),
                url(r'^(?P<object_pk>.+)/permissions/group-manage/(?P<group_id>\-?\d+)/$',
                    view=self.admin_site.admin_view(
                        self.obj_perms_manage_group_view),
                    name='%s_%s_permissions_manage_group' % info),
            )
            urls = myurls + urls
        return urls

    def get_obj_perms_base_context(self, request, obj):
        """
        Returns context dictionary with common admin and object permissions
        related content.
        """
        context = {
            'adminform': {'model_admin': self},
            'media': self.media,
            'object': obj,
            'app_label': self.model._meta.app_label,
            'opts': self.model._meta,
            'original': hasattr(obj, '__unicode__') and obj.__unicode__() or\
                str(obj),
            'has_change_permission': self.has_change_permission(request, obj),
            'model_perms': get_perms_for_model(obj),
            'title': _("Object permissions"),
        }
        return context

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object permissions view. Presents all users and groups with any
        object permissions for the current model *instance*. Users or groups
        without object permissions for related *instance* would **not** be
        shown. In order to add or manage user or group one should use links or
        forms presented within the page.
        """
        obj = get_object_or_404(self.queryset(request), pk=object_pk)
        users_perms = SortedDict(
            get_users_with_perms(obj, attach_perms=True,
                with_group_users=False))

        users_perms.keyOrder.sort(key=lambda user:
                                  getattr(user, get_user_model().USERNAME_FIELD))
        groups_perms = SortedDict(
            get_groups_with_perms(obj, attach_perms=True))
        groups_perms.keyOrder.sort(key=lambda group: group.name)

        if request.method == 'POST' and 'submit_manage_user' in request.POST:
            user_form = UserManage(request.POST)
            group_form = GroupManage()
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.module_name
            )
            if user_form.is_valid():
                user_id = user_form.cleaned_data['user'].id
                url = reverse(
                    '%s:%s_%s_permissions_manage_user' % info,
                    args=[obj.pk, user_id]
                )
                return redirect(url)
        elif request.method == 'POST' and 'submit_manage_group' in request.POST:
            user_form = UserManage()
            group_form = GroupManage(request.POST)
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.module_name
            )
            if group_form.is_valid():
                group_id = group_form.cleaned_data['group'].id
                url = reverse(
                    '%s:%s_%s_permissions_manage_group' % info,
                    args=[obj.pk, group_id]
                )
                return redirect(url)
        else:
            user_form = UserManage()
            group_form = GroupManage()

        context = self.get_obj_perms_base_context(request, obj)
        context['users_perms'] = users_perms
        context['groups_perms'] = groups_perms
        context['user_form'] = user_form
        context['group_form'] = group_form

        return render_to_response(self.get_obj_perms_manage_template(),
            context, RequestContext(request, current_app=self.admin_site.name))

    def get_obj_perms_manage_template(self):
        """
        Returns main object permissions admin template.  May be overridden if
        need to change it dynamically.

        .. note::
           If ``INSTALLED_APPS`` contains ``grappelli`` this function would
           return ``"admin/guardian/grappelli/obj_perms_manage.html"``.

        """
        if 'grappelli' in settings.INSTALLED_APPS:
            return 'admin/guardian/contrib/grappelli/obj_perms_manage.html'
        return self.obj_perms_manage_template

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """
        Manages selected users' permissions for current object.
        """
        user = get_object_or_404(get_user_model(), id=user_id)
        obj = get_object_or_404(self.queryset(request), pk=object_pk)
        form_class = self.get_obj_perms_manage_user_form()
        form = form_class(user, obj, request.POST or None)

        if request.method == 'POST' and form.is_valid():
            form.save_obj_perms()
            msg = ugettext("Permissions saved.")
            messages.success(request, msg)
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.module_name
            )
            url = reverse(
                '%s:%s_%s_permissions_manage_user' % info,
                args=[obj.pk, user.id]
            )
            return redirect(url)

        context = self.get_obj_perms_base_context(request, obj)
        context['user_obj'] = user
        context['user_perms'] = get_perms(user, obj)
        context['form'] = form

        return render_to_response(self.get_obj_perms_manage_user_template(),
            context, RequestContext(request, current_app=self.admin_site.name))

    def get_obj_perms_manage_user_template(self):
        """
        Returns object permissions for user admin template.  May be overridden
        if need to change it dynamically.

        .. note::
           If ``INSTALLED_APPS`` contains ``grappelli`` this function would
           return ``"admin/guardian/grappelli/obj_perms_manage_user.html"``.

        """
        if 'grappelli' in settings.INSTALLED_APPS:
            return 'admin/guardian/contrib/grappelli/obj_perms_manage_user.html'
        return self.obj_perms_manage_user_template

    def get_obj_perms_manage_user_form(self):
        """
        Returns form class for user object permissions management.  By default
        :form:`AdminUserObjectPermissionsForm` is returned.
        """
        return AdminUserObjectPermissionsForm

    def obj_perms_manage_group_view(self, request, object_pk, group_id):
        """
        Manages selected groups' permissions for current object.
        """
        group = get_object_or_404(Group, id=group_id)
        obj = get_object_or_404(self.queryset(request), pk=object_pk)
        form_class = self.get_obj_perms_manage_group_form()
        form = form_class(group, obj, request.POST or None)

        if request.method == 'POST' and form.is_valid():
            form.save_obj_perms()
            msg = ugettext("Permissions saved.")
            messages.success(request, msg)
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.module_name
            )
            url = reverse(
                '%s:%s_%s_permissions_manage_group' % info,
                args=[obj.pk, group.id]
            )
            return redirect(url)

        context = self.get_obj_perms_base_context(request, obj)
        context['group_obj'] = group
        context['group_perms'] = get_perms(group, obj)
        context['form'] = form

        return render_to_response(self.get_obj_perms_manage_group_template(),
            context, RequestContext(request, current_app=self.admin_site.name))

    def get_obj_perms_manage_group_template(self):
        """
        Returns object permissions for group admin template.  May be overridden
        if need to change it dynamically.

        .. note::
           If ``INSTALLED_APPS`` contains ``grappelli`` this function would
           return ``"admin/guardian/grappelli/obj_perms_manage_group.html"``.

        """
        if 'grappelli' in settings.INSTALLED_APPS:
            return 'admin/guardian/contrib/grappelli/obj_perms_manage_group.html'
        return self.obj_perms_manage_group_template

    def get_obj_perms_manage_group_form(self):
        """
        Returns form class for group object permissions management.  By default
        :form:`AdminGroupObjectPermissionsForm` is returned.
        """
        return AdminGroupObjectPermissionsForm


class GuardedModelAdmin(GuardedModelAdminMixin, admin.ModelAdmin):
    """
    Extends ``django.contrib.admin.ModelAdmin`` class. Provides some extra
    views for object permissions management at admin panel. It also changes
    default ``change_form_template`` option to
    ``'admin/guardian/model/change_form.html'`` which is required for proper
    url (object permissions related) being shown at the model pages.

    **Extra options**

    ``GuardedModelAdmin.obj_perms_manage_template``

        *Default*: ``admin/guardian/model/obj_perms_manage.html``

    ``GuardedModelAdmin.obj_perms_manage_user_template``

        *Default*: ``admin/guardian/model/obj_perms_manage_user.html``

    ``GuardedModelAdmin.obj_perms_manage_group_template``

        *Default*: ``admin/guardian/model/obj_perms_manage_group.html``

    ``GuardedModelAdmin.user_can_access_owned_objects_only``

        *Default*: ``False``

        If this would be set to ``True``, ``request.user`` would be used to
        filter out objects he or she doesn't own (checking ``user`` field
        of used model - field name may be overridden by
        ``user_owned_objects_field`` option).

        .. note::
           Please remember that this will **NOT** affect superusers!
           Admins would still see all items.

    ``GuardedModelAdmin.user_can_access_owned_by_group_objects_only``

        *Default*: ``False``

        If this would be set to ``True``, ``request.user`` would be used to
        filter out objects her or his group doesn't own (checking if any group
        user belongs to is set as ``group`` field of the object; name of the
        field can be changed by overriding ``group_owned_objects_field``).

        .. note::
           Please remember that this will **NOT** affect superusers!
           Admins would still see all items.

    ``GuardedModelAdmin.group_owned_objects_field``

        *Default*: ``group``

    ``GuardedModelAdmin.include_object_permissions_urls``

        *Default*: ``True``

        .. versionadded:: 1.2

        Might be set to ``False`` in order **NOT** to include guardian-specific
        urls.

    **Usage example**

    Just use :admin:`GuardedModelAdmin` instead of
    ``django.contrib.admin.ModelAdmin``.

    .. code-block:: python

        from django.contrib import admin
        from guardian.admin import GuardedModelAdmin
        from myapp.models import Author

        class AuthorAdmin(GuardedModelAdmin):
            pass

        admin.site.register(Author, AuthorAdmin)

    """


class UserManage(forms.Form):
    user = forms.CharField(label=_("User identification"),
                        max_length=200,
                        error_messages = {'does_not_exist': _("This user does not exist")},
                        help_text=_('Enter a value compatible with User.USERNAME_FIELD')
                     )

    def clean_user(self):
        """
        Returns ``User`` instance based on the given identification.
        """
        identification = self.cleaned_data['user']
        user_model = get_user_model()
        try:
            username_field = user_model.USERNAME_FIELD
        except AttributeError:
            username_field = 'username'
        try:
            user = user_model.objects.get(**{username_field: identification})
            return user
        except user_model.DoesNotExist:
            raise forms.ValidationError(
                self.fields['user'].error_messages['does_not_exist'])


class GroupManage(forms.Form):
    group = forms.CharField(max_length=80, error_messages={'does_not_exist':
        _("This group does not exist")})

    def clean_group(self):
        """
        Returns ``Group`` instance based on the given group name.
        """
        name = self.cleaned_data['group']
        try:
            group = Group.objects.get(name=name)
            return group
        except Group.DoesNotExist:
            raise forms.ValidationError(
                self.fields['group'].error_messages['does_not_exist'])


########NEW FILE########
__FILENAME__ = apps

from django.apps import AppConfig
from . import monkey_patch_user

class GuardianConfig(AppConfig):
    name = 'guardian'

    def ready(self):
        monkey_patch_user()
        

########NEW FILE########
__FILENAME__ = backends
from __future__ import unicode_literals

from django.db import models

from guardian.compat import get_user_model
from guardian.conf import settings
from guardian.exceptions import WrongAppError
from guardian.core import ObjectPermissionChecker

class ObjectPermissionBackend(object):
    supports_object_permissions = True
    supports_anonymous_user = True
    supports_inactive_user = True

    def authenticate(self, username, password):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        Returns ``True`` if given ``user_obj`` has ``perm`` for ``obj``. If no
        ``obj`` is given, ``False`` is returned.

        .. note::

           Remember, that if user is not *active*, all checks would return
           ``False``.

        Main difference between Django's ``ModelBackend`` is that we can pass
        ``obj`` instance here and ``perm`` doesn't have to contain
        ``app_label`` as it can be retrieved from given ``obj``.

        **Inactive user support**

        If user is authenticated but inactive at the same time, all checks
        always returns ``False``.
        """
        # Backend checks only object permissions
        if obj is None:
            return False

        # Backend checks only permissions for Django models
        if not isinstance(obj, models.Model):
            return False

        # This is how we support anonymous users - simply try to retrieve User
        # instance and perform checks for that predefined user
        if not user_obj.is_authenticated():
            # If anonymous user permission is disabled then they are always unauthorized
            if settings.ANONYMOUS_USER_ID is None:
                return False
            user_obj = get_user_model().objects.get(pk=settings.ANONYMOUS_USER_ID)

        # Do not check any further if user is not active
        if not user_obj.is_active:
            return False

        if len(perm.split('.')) > 1:
            app_label, perm = perm.split('.')
            if app_label != obj._meta.app_label:
                raise WrongAppError("Passed perm has app label of '%s' and "
                    "given obj has '%s'" % (app_label, obj._meta.app_label))

        check = ObjectPermissionChecker(user_obj)
        return check.has_perm(perm, obj)


########NEW FILE########
__FILENAME__ = compat
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.auth.models import AnonymousUser
from django.utils.importlib import import_module
import six
import sys

try:
    from django.conf.urls import url, patterns, include, handler404, handler500
except ImportError:
    from django.conf.urls.defaults import url, patterns, include, handler404, handler500 # pyflakes:ignore

__all__ = [
    'User',
    'Group',
    'Permission',
    'AnonymousUser',
    'get_user_model',
    'import_string',
    'user_model_label',
    'url',
    'patterns',
    'include',
    'handler404',
    'handler500',
    'mock',
    'unittest',
]

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # pyflakes:ignore
try:
    from unittest import mock  # Since Python 3.3 mock is is in stdlib
except ImportError:
    try:
        import mock # pyflakes:ignore
    except ImportError:
        # mock is used for tests only however it is hard to check if user is
        # running tests or production code so we fail silently here; mock is
        # still required for tests at setup.py (See PR #193)
        pass

# Django 1.5 compatibility utilities, providing support for custom User models.
# Since get_user_model() causes a circular import if called when app models are
# being loaded, the user_model_label should be used when possible, with calls
# to get_user_model deferred to execution time

user_model_label = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

def get_user_model_path():
    """
    Returns 'app_label.ModelName' for User model. Basically if
    ``AUTH_USER_MODEL`` is set at settings it would be returned, otherwise
    ``auth.User`` is returned.
    """
    return getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

def get_user_permission_full_codename(perm):
    """
    Returns 'app_label.<perm>_<usermodulename>'. If standard ``auth.User`` is
    used, for 'change' perm this would return ``auth.change_user`` and if
    ``myapp.CustomUser`` is used it would return ``myapp.change_customuser``.
    """
    User = get_user_model()
    return '%s.%s_%s' % (User._meta.app_label, perm, User._meta.module_name)

def get_user_permission_codename(perm):
    """
    Returns '<perm>_<usermodulename>'. If standard ``auth.User`` is
    used, for 'change' perm this would return ``change_user`` and if
    ``myapp.CustomUser`` is used it would return ``change_customuser``.
    """
    return get_user_permission_full_codename(perm).split('.')[1]


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.

    Backported from Django 1.7
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError:
        msg = "%s doesn't look like a module path" % dotted_path
        six.reraise(ImportError, ImportError(msg), sys.exc_info()[2])

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError:
        msg = 'Module "%s" does not define a "%s" attribute/class' % (
            dotted_path, class_name)
        six.reraise(ImportError, ImportError(msg), sys.exc_info()[2])


# Python 3
try:
    unicode = unicode # pyflakes:ignore
    basestring = basestring # pyflakes:ignore
    str = str # pyflakes:ignore
except NameError:
    basestring = unicode = str = str

# Django 1.7 compatibility
# create_permission API changed: skip the create_models (second
# positional argument) if we have django 1.7+ and 2+ positional
# arguments with the second one being a list/tuple 
def create_permissions(*args, **kwargs):
    from django.contrib.auth.management import create_permissions as original_create_permissions
    import django

    if django.get_version().split('.')[:2] >= ['1','7'] and \
        len(args) > 1 and isinstance(args[1], (list, tuple)):
        args = args[:1] + args[2:]
    return original_create_permissions(*args, **kwargs)

__all__ = ['User', 'Group', 'Permission', 'AnonymousUser']

########NEW FILE########
__FILENAME__ = settings
from __future__ import unicode_literals
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ANONYMOUS_DEFAULT_USERNAME_VALUE = getattr(settings,
    'ANONYMOUS_DEFAULT_USERNAME_VALUE', 'AnonymousUser')

try:
    ANONYMOUS_USER_ID = settings.ANONYMOUS_USER_ID
except AttributeError:
    raise ImproperlyConfigured("In order to use django-guardian's "
        "ObjectPermissionBackend authorization backend you have to configure "
        "ANONYMOUS_USER_ID at your settings module")

RENDER_403 = getattr(settings, 'GUARDIAN_RENDER_403', False)
TEMPLATE_403 = getattr(settings, 'GUARDIAN_TEMPLATE_403', '403.html')
RAISE_403 = getattr(settings, 'GUARDIAN_RAISE_403', False)
GET_INIT_ANONYMOUS_USER = getattr(settings, 'GUARDIAN_GET_INIT_ANONYMOUS_USER',
    'guardian.management.get_init_anonymous_user')

def check_configuration():
    if RENDER_403 and RAISE_403:
        raise ImproperlyConfigured("Cannot use both GUARDIAN_RENDER_403 AND "
            "GUARDIAN_RAISE_403 - only one of this config may be True")

check_configuration()


########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

from itertools import chain

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from guardian.utils import get_identity
from guardian.utils import get_user_obj_perms_model
from guardian.utils import get_group_obj_perms_model
from guardian.compat import get_user_model


class ObjectPermissionChecker(object):
    """
    Generic object permissions checker class being the heart of
    ``django-guardian``.

    .. note::
       Once checked for single object, permissions are stored and we don't hit
       database again if another check is called for this object. This is great
       for templates, views or other request based checks (assuming we don't
       have hundreds of permissions on a single object as we fetch all
       permissions for checked object).

       On the other hand, if we call ``has_perm`` for perm1/object1, then we
       change permission state and call ``has_perm`` again for same
       perm1/object1 on same instance of ObjectPermissionChecker we won't see a
       difference as permissions are already fetched and stored within cache
       dictionary.
    """
    def __init__(self, user_or_group=None):
        """
        :param user_or_group: should be an ``User``, ``AnonymousUser`` or
          ``Group`` instance
        """
        self.user, self.group = get_identity(user_or_group)
        self._obj_perms_cache = {}

    def has_perm(self, perm, obj):
        """
        Checks if user/group has given permission for object.

        :param perm: permission as string, may or may not contain app_label
          prefix (if not prefixed, we grab app_label from ``obj``)
        :param obj: Django model instance for which permission should be checked

        """
        perm = perm.split('.')[-1]
        if self.user and not self.user.is_active:
            return False
        elif self.user and self.user.is_superuser:
            return True
        return perm in self.get_perms(obj)

    def get_perms(self, obj):
        """
        Returns list of ``codename``'s of all permissions for given ``obj``.

        :param obj: Django model instance for which permission should be checked

        """
        if self.user and not self.user.is_active:
            return []
        User = get_user_model()
        ctype = ContentType.objects.get_for_model(obj)
        key = self.get_local_cache_key(obj)
        if not key in self._obj_perms_cache:

            group_model = get_group_obj_perms_model(obj)
            group_rel_name = group_model.permission.field.related_query_name()
            if self.user:
                fieldname = '%s__group__%s' % (
                    group_rel_name,
                    User.groups.field.related_query_name(),
                )
                group_filters = {fieldname: self.user}
            else:
                group_filters = {'%s__group' % group_rel_name: self.group}
            if group_model.objects.is_generic():
                group_filters.update({
                    '%s__content_type' % group_rel_name: ctype,
                    '%s__object_pk' % group_rel_name: obj.pk,
                })
            else:
                group_filters['%s__content_object' % group_rel_name] = obj

            if self.user and self.user.is_superuser:
                perms = list(chain(*Permission.objects
                    .filter(content_type=ctype)
                    .values_list("codename")))
            elif self.user:
                model = get_user_obj_perms_model(obj)
                related_name = model.permission.field.related_query_name()
                user_filters = {'%s__user' % related_name: self.user}
                if model.objects.is_generic():
                    user_filters.update({
                        '%s__content_type' % related_name: ctype,
                        '%s__object_pk' % related_name: obj.pk,
                    })
                else:
                    user_filters['%s__content_object' % related_name] = obj
                perms_qs = Permission.objects.filter(content_type=ctype)
                # Query user and group permissions separately and then combine
                # the results to avoid a slow query
                user_perms_qs = perms_qs.filter(**user_filters)
                user_perms = user_perms_qs.values_list("codename", flat=True)
                group_perms_qs = perms_qs.filter(**group_filters)
                group_perms = group_perms_qs.values_list("codename", flat=True)
                perms = list(set(chain(user_perms, group_perms)))
            else:
                perms = list(set(chain(*Permission.objects
                    .filter(content_type=ctype)
                    .filter(**group_filters)
                    .values_list("codename"))))
            self._obj_perms_cache[key] = perms
        return self._obj_perms_cache[key]

    def get_local_cache_key(self, obj):
        """
        Returns cache key for ``_obj_perms_cache`` dict.
        """
        ctype = ContentType.objects.get_for_model(obj)
        return (ctype.id, obj.pk)


########NEW FILE########
__FILENAME__ = decorators
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.functional import wraps
from django.db.models import Model, get_model
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from guardian.compat import basestring
from guardian.exceptions import GuardianError
from guardian.utils import get_403_or_None


def permission_required(perm, lookup_variables=None, **kwargs):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled.

    Optionally, instances for which check should be made may be passed as an
    second argument or as a tuple parameters same as those passed to
    ``get_object_or_404`` but must be provided as pairs of strings. This way
    decorator can fetch i.e. ``User`` instance based on performed request and
    check permissions on it (without this, one would need to fetch user instance
    at view's logic and check permission inside a view).

    :param login_url: if denied, user would be redirected to location set by
      this parameter. Defaults to ``django.conf.settings.LOGIN_URL``.
    :param redirect_field_name: name of the parameter passed if redirected.
      Defaults to ``django.contrib.auth.REDIRECT_FIELD_NAME``.
    :param return_403: if set to ``True`` then instead of redirecting to the
      login page, response with status code 403 is returned (
      ``django.http.HttpResponseForbidden`` instance or rendered template -
      see :setting:`GUARDIAN_RENDER_403`). Defaults to ``False``.
    :param accept_global_perms: if set to ``True``, then *object level
      permission* would be required **only if user does NOT have global
      permission** for target *model*. If turned on, makes this decorator
      like an extension over standard
      ``django.contrib.admin.decorators.permission_required`` as it would
      check for global permissions first. Defaults to ``False``.

    Examples::

        @permission_required('auth.change_user', return_403=True)
        def my_view(request):
            return HttpResponse('Hello')

        @permission_required('auth.change_user', (User, 'username', 'username'))
        def my_view(request, username):
            '''
            auth.change_user permission would be checked based on given
            'username'. If view's parameter would be named ``name``, we would
            rather use following decorator::

                @permission_required('auth.change_user', (User, 'username', 'name'))
            '''
            user = get_object_or_404(User, username=username)
            return user.get_absolute_url()

        @permission_required('auth.change_user',
            (User, 'username', 'username', 'groups__name', 'group_name'))
        def my_view(request, username, group_name):
            '''
            Similar to the above example, here however we also make sure that
            one of user's group is named same as request's ``group_name`` param.
            '''
            user = get_object_or_404(User, username=username,
                group__name=group_name)
            return user.get_absolute_url()

    """
    login_url = kwargs.pop('login_url', settings.LOGIN_URL)
    redirect_field_name = kwargs.pop('redirect_field_name', REDIRECT_FIELD_NAME)
    return_403 = kwargs.pop('return_403', False)
    accept_global_perms = kwargs.pop('accept_global_perms', False)

    # Check if perm is given as string in order not to decorate
    # view function itself which makes debugging harder
    if not isinstance(perm, basestring):
        raise GuardianError("First argument must be in format: "
            "'app_label.codename or a callable which return similar string'")

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # if more than one parameter is passed to the decorator we try to
            # fetch object for which check would be made
            obj = None
            if lookup_variables:
                model, lookups = lookup_variables[0], lookup_variables[1:]
                # Parse model
                if isinstance(model, basestring):
                    splitted = model.split('.')
                    if len(splitted) != 2:
                        raise GuardianError("If model should be looked up from "
                            "string it needs format: 'app_label.ModelClass'")
                    model = get_model(*splitted)
                elif issubclass(model.__class__, (Model, ModelBase, QuerySet)):
                    pass
                else:
                    raise GuardianError("First lookup argument must always be "
                        "a model, string pointing at app/model or queryset. "
                        "Given: %s (type: %s)" % (model, type(model)))
                # Parse lookups
                if len(lookups) % 2 != 0:
                    raise GuardianError("Lookup variables must be provided "
                        "as pairs of lookup_string and view_arg")
                lookup_dict = {}
                for lookup, view_arg in zip(lookups[::2], lookups[1::2]):
                    if view_arg not in kwargs:
                        raise GuardianError("Argument %s was not passed "
                            "into view function" % view_arg)
                    lookup_dict[lookup] = kwargs[view_arg]
                obj = get_object_or_404(model, **lookup_dict)

            response = get_403_or_None(request, perms=[perm], obj=obj,
                login_url=login_url, redirect_field_name=redirect_field_name,
                return_403=return_403, accept_global_perms=accept_global_perms)
            if response:
                return response
            return view_func(request, *args, **kwargs)
        return wraps(view_func)(_wrapped_view)
    return decorator


def permission_required_or_403(perm, *args, **kwargs):
    """
    Simple wrapper for permission_required decorator.

    Standard Django's permission_required decorator redirects user to login page
    in case permission check failed. This decorator may be used to return
    HttpResponseForbidden (status 403) instead of redirection.

    The only difference between ``permission_required`` decorator is that this
    one always set ``return_403`` parameter to ``True``.
    """
    kwargs['return_403'] = True
    return permission_required(perm, *args, **kwargs)


########NEW FILE########
__FILENAME__ = exceptions
"""
Exceptions used by django-guardian. All internal and guardian-specific errors
should extend GuardianError class.
"""
from __future__ import unicode_literals


class GuardianError(Exception):
    pass

class NotUserNorGroup(GuardianError):
    pass

class ObjectNotPersisted(GuardianError):
    pass

class WrongAppError(GuardianError):
    pass

class MixedContentTypeError(GuardianError):
    pass


########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext as _

from guardian.shortcuts import assign_perm
from guardian.shortcuts import remove_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import get_perms_for_model


class BaseObjectPermissionsForm(forms.Form):
    """
    Base form for object permissions management. Needs to be extended for usage
    with users and/or groups.
    """

    def __init__(self, obj, *args, **kwargs):
        """
        :param obj: Any instance which form would use to manage object
          permissions"
        """
        self.obj = obj
        super(BaseObjectPermissionsForm, self).__init__(*args, **kwargs)
        field_name = self.get_obj_perms_field_name()
        self.fields[field_name] = self.get_obj_perms_field()

    def get_obj_perms_field(self):
        """
        Returns field instance for object permissions management. May be
        replaced entirely.
        """
        field_class = self.get_obj_perms_field_class()
        field = field_class(
            label=self.get_obj_perms_field_label(),
            choices=self.get_obj_perms_field_choices(),
            initial=self.get_obj_perms_field_initial(),
            widget=self.get_obj_perms_field_widget(),
            required=self.are_obj_perms_required(),
        )
        return field

    def get_obj_perms_field_name(self):
        """
        Returns name of the object permissions management field. Default:
        ``permission``.
        """
        return 'permissions'

    def get_obj_perms_field_label(self):
        """
        Returns label of the object permissions management field. Defualt:
        ``_("Permissions")`` (marked to be translated).
        """
        return _("Permissions")

    def get_obj_perms_field_choices(self):
        """
        Returns choices for object permissions management field. Default:
        list of tuples ``(codename, name)`` for each ``Permission`` instance
        for the managed object.
        """
        choices = [(p.codename, p.name) for p in get_perms_for_model(self.obj)]
        return choices

    def get_obj_perms_field_initial(self):
        """
        Returns initial object permissions management field choices. Default:
        ``[]`` (empty list).
        """
        return []

    def get_obj_perms_field_class(self):
        """
        Returns object permissions management field's base class. Default:
        ``django.forms.MultipleChoiceField``.
        """
        return forms.MultipleChoiceField

    def get_obj_perms_field_widget(self):
        """
        Returns object permissions management field's widget base class.
        Default: ``django.forms.SelectMultiple``.
        """
        return forms.SelectMultiple

    def are_obj_perms_required(self):
        """
        Indicates if at least one object permission should be required. Default:
        ``False``.
        """
        return False

    def save_obj_perms(self):
        """
        Must be implemented in concrete form class. This method should store
        selected object permissions.
        """
        raise NotImplementedError


class UserObjectPermissionsForm(BaseObjectPermissionsForm):
    """
    Object level permissions management form for usage with ``User`` instances.

    Example usage::

        from django.shortcuts import get_object_or_404
        from myapp.models import Post
        from guardian.forms import UserObjectPermissionsForm
        from django.contrib.auth.models import User

        def my_view(request, post_slug, user_id):
            user = get_object_or_404(User, id=user_id)
            post = get_object_or_404(Post, slug=post_slug)
            form = UserObjectPermissionsForm(user, post, request.POST or None)
            if request.method == 'POST' and form.is_valid():
                form.save_obj_perms()
            ...

    """

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserObjectPermissionsForm, self).__init__(*args, **kwargs)

    def get_obj_perms_field_initial(self):
        perms = get_perms(self.user, self.obj)
        return perms

    def save_obj_perms(self):
        """
        Saves selected object permissions by creating new ones and removing
        those which were not selected but already exists.

        Should be called *after* form is validated.
        """
        perms = self.cleaned_data[self.get_obj_perms_field_name()]
        model_perms = [c[0] for c in self.get_obj_perms_field_choices()]

        to_remove = set(model_perms) - set(perms)
        for perm in to_remove:
            remove_perm(perm, self.user, self.obj)

        for perm in perms:
            assign_perm(perm, self.user, self.obj)


class GroupObjectPermissionsForm(BaseObjectPermissionsForm):
    """
    Object level permissions management form for usage with ``Group`` instances.

    Example usage::

        from django.shortcuts import get_object_or_404
        from myapp.models import Post
        from guardian.forms import GroupObjectPermissionsForm
        from guardian.models import Group

        def my_view(request, post_slug, group_id):
            group = get_object_or_404(Group, id=group_id)
            post = get_object_or_404(Post, slug=post_slug)
            form = GroupObjectPermissionsForm(group, post, request.POST or None)
            if request.method == 'POST' and form.is_valid():
                form.save_obj_perms()
            ...

    """

    def __init__(self, group, *args, **kwargs):
        self.group = group
        super(GroupObjectPermissionsForm, self).__init__(*args, **kwargs)

    def get_obj_perms_field_initial(self):
        perms = get_perms(self.group, self.obj)
        return perms

    def save_obj_perms(self):
        """
        Saves selected object permissions by creating new ones and removing
        those which were not selected but already exists.

        Should be called *after* form is validated.
        """
        perms = self.cleaned_data[self.get_obj_perms_field_name()]
        model_perms = [c[0] for c in self.get_obj_perms_field_choices()]

        to_remove = set(model_perms) - set(perms)
        for perm in to_remove:
            remove_perm(perm, self.group, self.obj)

        for perm in perms:
            assign_perm(perm, self.group, self.obj)


########NEW FILE########
__FILENAME__ = clean_orphan_obj_perms
from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand

from guardian.utils import clean_orphan_obj_perms


class Command(NoArgsCommand):
    """
    clean_orphan_obj_perms command is a tiny wrapper around
    :func:`guardian.utils.clean_orphan_obj_perms`.

    Usage::

        $ python manage.py clean_orphan_obj_perms
        Removed 11 object permission entries with no targets

    """
    help = "Removes object permissions with not existing targets"

    def handle_noargs(self, **options):
        removed = clean_orphan_obj_perms()
        if options['verbosity'] > 0:
            print("Removed %d object permission entries with no targets" %
                removed)


########NEW FILE########
__FILENAME__ = managers
from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.models import ContentType

from guardian.exceptions import ObjectNotPersisted
from guardian.models import Permission
import warnings

# TODO: consolidate UserObjectPermissionManager and GroupObjectPermissionManager

class BaseObjectPermissionManager(models.Manager):

    def is_generic(self):
        try:
            self.model._meta.get_field('object_pk')
            return True
        except models.fields.FieldDoesNotExist:
            return False


class UserObjectPermissionManager(BaseObjectPermissionManager):

    def assign_perm(self, perm, user, obj):
        """
        Assigns permission with given ``perm`` for an instance ``obj`` and
        ``user``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        permission = Permission.objects.get(content_type=ctype, codename=perm)

        kwargs = {'permission': permission, 'user': user}
        if self.is_generic():
            kwargs['content_type'] = ctype
            kwargs['object_pk'] = obj.pk
        else:
            kwargs['content_object'] = obj
        obj_perm, created = self.get_or_create(**kwargs)
        return obj_perm

    def assign(self, perm, user, obj):
        """ Depreciated function name left in for compatibility"""
        warnings.warn("UserObjectPermissionManager method 'assign' is being renamed to 'assign_perm'. Update your code accordingly as old name will be depreciated in 2.0 version.", DeprecationWarning)
        return self.assign_perm(perm, user, obj)

    def remove_perm(self, perm, user, obj):
        """
        Removes permission ``perm`` for an instance ``obj`` and given ``user``.

        Please note that we do NOT fetch object permission from database - we
        use ``Queryset.delete`` method for removing it. Main implication of this
        is that ``post_delete`` signals would NOT be fired.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        filters = {
            'permission__codename': perm,
            'permission__content_type': ContentType.objects.get_for_model(obj),
            'user': user,
        }
        if self.is_generic():
            filters['object_pk'] = obj.pk
        else:
            filters['content_object__pk'] = obj.pk
        self.filter(**filters).delete()


class GroupObjectPermissionManager(BaseObjectPermissionManager):

    def assign_perm(self, perm, group, obj):
        """
        Assigns permission with given ``perm`` for an instance ``obj`` and
        ``group``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        permission = Permission.objects.get(content_type=ctype, codename=perm)

        kwargs = {'permission': permission, 'group': group}
        if self.is_generic():
            kwargs['content_type'] = ctype
            kwargs['object_pk'] = obj.pk
        else:
            kwargs['content_object'] = obj
        obj_perm, created = self.get_or_create(**kwargs)
        return obj_perm

    def assign(self, perm, user, obj):
        """ Depreciated function name left in for compatibility"""
        warnings.warn("UserObjectPermissionManager method 'assign' is being renamed to 'assign_perm'. Update your code accordingly as old name will be depreciated in 2.0 version.", DeprecationWarning)
        return self.assign_perm(perm, user, obj)

    def remove_perm(self, perm, group, obj):
        """
        Removes permission ``perm`` for an instance ``obj`` and given ``group``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        filters = {
            'permission__codename': perm,
            'permission__content_type': ContentType.objects.get_for_model(obj),
            'group': group,
        }
        if self.is_generic():
            filters['object_pk'] = obj.pk
        else:
            filters['content_object__pk'] = obj.pk

        self.filter(**filters).delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

from guardian.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'UserObjectPermission'
        db.create_table('guardian_userobjectpermission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Permission'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
        ))
        db.send_create_signal('guardian', ['UserObjectPermission'])

        # Adding unique constraint on 'UserObjectPermission', fields ['user', 'permission', 'content_type', 'object_id']
        db.create_unique('guardian_userobjectpermission', ['user_id', 'permission_id', 'content_type_id', 'object_id'])

        # Adding model 'GroupObjectPermission'
        db.create_table('guardian_groupobjectpermission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Permission'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'])),
        ))
        db.send_create_signal('guardian', ['GroupObjectPermission'])

        # Adding unique constraint on 'GroupObjectPermission', fields ['group', 'permission', 'content_type', 'object_id']
        db.create_unique('guardian_groupobjectpermission', ['group_id', 'permission_id', 'content_type_id', 'object_id'])


    def backwards(self, orm):

        # Removing unique constraint on 'GroupObjectPermission', fields ['group', 'permission', 'content_type', 'object_id']
        db.delete_unique('guardian_groupobjectpermission', ['group_id', 'permission_id', 'content_type_id', 'object_id'])

        # Removing unique constraint on 'UserObjectPermission', fields ['user', 'permission', 'content_type', 'object_id']
        db.delete_unique('guardian_userobjectpermission', ['user_id', 'permission_id', 'content_type_id', 'object_id'])

        # Deleting model 'UserObjectPermission'
        db.delete_table('guardian_userobjectpermission')

        # Deleting model 'GroupObjectPermission'
        db.delete_table('guardian_groupobjectpermission')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'guardian.groupobjectpermission': {
            'Meta': {'unique_together': "(['group', 'permission', 'content_type', 'object_id'],)", 'object_name': 'GroupObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"})
        },
        'guardian.userobjectpermission': {
            'Meta': {'unique_together': "(['user', 'permission', 'content_type', 'object_id'],)", 'object_name': 'UserObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['guardian']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_groupobjectpermission_object_pk__add_field_userobjectp
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

from guardian.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'GroupObjectPermission.object_pk'
        db.add_column('guardian_groupobjectpermission', 'object_pk', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'UserObjectPermission.object_pk'
        db.add_column('guardian_userobjectpermission', 'object_pk', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'GroupObjectPermission.object_pk'
        db.delete_column('guardian_groupobjectpermission', 'object_pk')

        # Deleting field 'UserObjectPermission.object_pk'
        db.delete_column('guardian_userobjectpermission', 'object_pk')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'guardian.groupobjectpermission': {
            'Meta': {'unique_together': "(['group', 'permission', 'content_type', 'object_id'],)", 'object_name': 'GroupObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'object_pk': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"})
        },
        'guardian.userobjectpermission': {
            'Meta': {'unique_together': "(['user', 'permission', 'content_type', 'object_id'],)", 'object_name': 'UserObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'object_pk': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['guardian']

########NEW FILE########
__FILENAME__ = 0003_update_objectpermission_object_pk
# encoding: utf-8
from south.v2 import DataMigration

from guardian.compat import user_model_label


class Migration(DataMigration):

    def forwards(self, orm):
        """
        Updates ``object_pk`` fields on both ``UserObjectPermission`` and
        ``GroupObjectPermission`` from ``object_id`` values.
        """
        for Model in [orm.UserObjectPermission, orm.GroupObjectPermission]:
            for obj in Model.objects.all():
                obj.object_pk = str(obj.object_id)
                obj.save()

    def backwards(self, orm):
        """
        Updates ``object_id`` fields on both ``UserObjectPermission`` and
        ``GroupObjectPermission`` from ``object_pk`` values.
        """
        for Model in [orm.UserObjectPermission, orm.GroupObjectPermission]:
            for obj in Model.objects.all():
                obj.object_id = int(obj.object_pk)
                obj.save()

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'guardian.groupobjectpermission': {
            'Meta': {'unique_together': "(['group', 'permission', 'content_type', 'object_id'],)", 'object_name': 'GroupObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'object_pk': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"})
        },
        'guardian.userobjectpermission': {
            'Meta': {'unique_together': "(['user', 'permission', 'content_type', 'object_id'],)", 'object_name': 'UserObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'object_pk': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['guardian']

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_groupobjectpermission_object_id__del_unique_groupobjec
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

from guardian.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'GroupObjectPermission.object_pk'
        db.alter_column('guardian_groupobjectpermission', 'object_pk', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'UserObjectPermission.object_pk'
        db.alter_column('guardian_userobjectpermission', 'object_pk', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Removing unique constraint on 'UserObjectPermission', fields ['object_id', 'user', 'content_type', 'permission']
        db.delete_unique('guardian_userobjectpermission', ['object_id', 'user_id', 'content_type_id', 'permission_id'])

        # Removing unique constraint on 'GroupObjectPermission', fields ['group', 'object_id', 'content_type', 'permission']
        db.delete_unique('guardian_groupobjectpermission', ['group_id', 'object_id', 'content_type_id', 'permission_id'])

        # Adding unique constraint on 'GroupObjectPermission', fields ['object_pk', 'group', 'content_type', 'permission']
        db.create_unique('guardian_groupobjectpermission', ['object_pk', 'group_id', 'content_type_id', 'permission_id'])

        # Adding unique constraint on 'UserObjectPermission', fields ['object_pk', 'user', 'content_type', 'permission']
        db.create_unique('guardian_userobjectpermission', ['object_pk', 'user_id', 'content_type_id', 'permission_id'])


    def backwards(self, orm):

        # Changing field 'GroupObjectPermission.object_pk'
        db.alter_column('guardian_groupobjectpermission', 'object_pk', self.gf('django.db.models.fields.TextField')())

        # Changing field 'UserObjectPermission.object_pk'
        db.alter_column('guardian_userobjectpermission', 'object_pk', self.gf('django.db.models.fields.TextField')())

        # Removing unique constraint on 'UserObjectPermission', fields ['object_pk', 'user', 'content_type', 'permission']
        db.delete_unique('guardian_userobjectpermission', ['object_pk', 'user_id', 'content_type_id', 'permission_id'])

        # Removing unique constraint on 'GroupObjectPermission', fields ['object_pk', 'group', 'content_type', 'permission']
        db.delete_unique('guardian_groupobjectpermission', ['object_pk', 'group_id', 'content_type_id', 'permission_id'])

        # Adding unique constraint on 'GroupObjectPermission', fields ['group', 'object_id', 'content_type', 'permission']
        db.create_unique('guardian_groupobjectpermission', ['group_id', 'object_id', 'content_type_id', 'permission_id'])

        # Adding unique constraint on 'UserObjectPermission', fields ['object_id', 'user', 'content_type', 'permission']
        db.create_unique('guardian_userobjectpermission', ['object_id', 'user_id', 'content_type_id', 'permission_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'guardian.groupobjectpermission': {
            'Meta': {'unique_together': "(['group', 'permission', 'content_type', 'object_pk'],)", 'object_name': 'GroupObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_pk': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"})
        },
        'guardian.userobjectpermission': {
            'Meta': {'unique_together': "(['user', 'permission', 'content_type', 'object_pk'],)", 'object_name': 'UserObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_pk': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['guardian']

########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_groupobjectpermission_object_pk__chg_field_userobjectp
# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

from guardian.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Deleting field 'GroupObjectPermission.object_id'
        db.delete_column('guardian_groupobjectpermission', 'object_id')

        # Deleting field 'UserObjectPermission.object_id'
        db.delete_column('guardian_userobjectpermission', 'object_id')


    def backwards(self, orm):

        # We cannot add back in field 'GroupObjectPermission.object_id'
        raise RuntimeError(
            "Cannot reverse this migration. 'GroupObjectPermission.object_id' and its values cannot be restored.")

        # We cannot add back in field 'UserObjectPermission.object_id'
        raise RuntimeError(
            "Cannot reverse this migration. 'UserObjectPermission.object_id' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'guardian.groupobjectpermission': {
            'Meta': {'unique_together': "(['group', 'permission', 'content_type', 'object_pk'],)", 'object_name': 'GroupObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_pk': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"})
        },
        'guardian.userobjectpermission': {
            'Meta': {'unique_together': "(['user', 'permission', 'content_type', 'object_pk'],)", 'object_name': 'UserObjectPermission'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_pk': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Permission']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['guardian']

########NEW FILE########
__FILENAME__ = mixins
from __future__ import unicode_literals

from collections import Iterable
from django.conf import settings
from django.contrib.auth.decorators import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import PermissionDenied
from guardian.compat import basestring
from guardian.utils import get_403_or_None


class LoginRequiredMixin(object):
    """
    A login required mixin for use with class based views. This Class is a
    light wrapper around the `login_required` decorator and hence function
    parameters are just attributes defined on the class.

    Due to parent class order traversal this mixin must be added as the left
    most mixin of a view.

    The mixin has exaclty the same flow as `login_required` decorator:

        If the user isn't logged in, redirect to ``settings.LOGIN_URL``, passing
        the current absolute path in the query string. Example:
        ``/accounts/login/?next=/polls/3/``.

        If the user is logged in, execute the view normally. The view code is
        free to assume the user is logged in.

    **Class Settings**

    ``LoginRequiredMixin.redirect_field_name``

        *Default*: ``'next'``

    ``LoginRequiredMixin.login_url``

        *Default*: ``settings.LOGIN_URL``

    """
    redirect_field_name = REDIRECT_FIELD_NAME
    login_url = settings.LOGIN_URL

    def dispatch(self, request, *args, **kwargs):
        return login_required(redirect_field_name=self.redirect_field_name,
            login_url=self.login_url)(
            super(LoginRequiredMixin, self).dispatch
        )(request, *args, **kwargs)


class PermissionRequiredMixin(object):
    """
    A view mixin that verifies if the current logged in user has the specified
    permission by wrapping the ``request.user.has_perm(..)`` method.

    If a `get_object()` method is defined either manually or by including
    another mixin (for example ``SingleObjectMixin``) or ``self.object`` is
    defiend then the permission will be tested against that specific instance.

    .. note:
       Testing of a permission against a specific object instance requires an
       authentication backend that supports. Please see ``django-guardian`` to
       add object level permissions to your project.

    The mixin does the following:

        If the user isn't logged in, redirect to settings.LOGIN_URL, passing
        the current absolute path in the query string. Example:
        /accounts/login/?next=/polls/3/.

        If the `raise_exception` is set to True than rather than redirect to
        login page a `PermissionDenied` (403) is raised.

        If the user is logged in, and passes the permission check than the view
        is executed normally.

    **Example Usage**::

        class SecureView(PermissionRequiredMixin, View):
            ...
            permission_required = 'auth.change_user'
            ...

    **Class Settings**

    ``PermissionRequiredMixin.permission_required``

        *Default*: ``None``, must be set to either a string or list of strings
        in format: *<app_label>.<permission_codename>*.

    ``PermissionRequiredMixin.login_url``

        *Default*: ``settings.LOGIN_URL``

    ``PermissionRequiredMixin.redirect_field_name``

        *Default*: ``'next'``

    ``PermissionRequiredMixin.return_403``

        *Default*: ``False``. Returns 403 error page instead of redirecting
        user.

    ``PermissionRequiredMixin.raise_exception``

        *Default*: ``False``

        `permission_required` - the permission to check of form "<app_label>.<permission codename>"
                                i.e. 'polls.can_vote' for a permission on a model in the polls application.

    ``PermissionRequiredMixin.accept_global_perms``

        *Default*: ``False``,  If accept_global_perms would be set to True, then
         mixing would first check for global perms, if none found, then it will
         proceed to check object level permissions.

    """
    ### default class view settings
    login_url = settings.LOGIN_URL
    permission_required = None
    redirect_field_name = REDIRECT_FIELD_NAME
    return_403 = False
    raise_exception = False
    accept_global_perms = False

    def get_required_permissions(self, request=None):
        """
        Returns list of permissions in format *<app_label>.<codename>* that
        should be checked against *request.user* and *object*. By default, it
        returns list from ``permission_required`` attribute.

        :param request: Original request.
        """
        if isinstance(self.permission_required, basestring):
            perms = [self.permission_required]
        elif isinstance(self.permission_required, Iterable):
            perms = [p for p in self.permission_required]
        else:
            raise ImproperlyConfigured("'PermissionRequiredMixin' requires "
                "'permission_required' attribute to be set to "
                "'<app_label>.<permission codename>' but is set to '%s' instead"
                % self.permission_required)
        return perms

    def check_permissions(self, request):
        """
        Checks if *request.user* has all permissions returned by
        *get_required_permissions* method.

        :param request: Original request.
        """
        obj = (hasattr(self, 'get_object') and self.get_object()
            or getattr(self, 'object', None))


        forbidden = get_403_or_None(request,
            perms=self.get_required_permissions(request),
            obj=obj,
            login_url=self.login_url,
            redirect_field_name=self.redirect_field_name,
            return_403=self.return_403,
            accept_global_perms=self.accept_global_perms
        )
        if forbidden:
            self.on_permission_check_fail(request, forbidden, obj=obj)
        if forbidden and self.raise_exception:
            raise PermissionDenied()
        return forbidden

    def on_permission_check_fail(self, request, response, obj=None):
        """
        Method called upon permission check fail. By default it does nothing and
        should be overridden, if needed.

        :param request: Original request
        :param response: 403 response returned by *check_permissions* method.
        :param obj: Object that was fetched from the view (using ``get_object``
          method or ``object`` attribute, in that order).
        """

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        response = self.check_permissions(request)
        if response:
            return response
        return super(PermissionRequiredMixin, self).dispatch(request, *args,
            **kwargs)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.utils.translation import ugettext_lazy as _

from guardian.compat import user_model_label
from guardian.compat import unicode
from guardian.managers import GroupObjectPermissionManager
from guardian.managers import UserObjectPermissionManager


class BaseObjectPermission(models.Model):
    """
    Abstract ObjectPermission class. Actual class should additionally define
    a ``content_object`` field and either ``user`` or ``group`` field.
    """
    permission = models.ForeignKey(Permission)

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s | %s | %s' % (
            unicode(self.content_object),
            unicode(getattr(self, 'user', False) or self.group),
            unicode(self.permission.codename))

    def save(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(self.content_object)
        if content_type != self.permission.content_type:
            raise ValidationError("Cannot persist permission not designed for "
                "this class (permission's type is %r and object's type is %r)"
                % (self.permission.content_type, content_type))
        return super(BaseObjectPermission, self).save(*args, **kwargs)


class BaseGenericObjectPermission(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_pk = models.CharField(_('object ID'), max_length=255)
    content_object = GenericForeignKey(fk_field='object_pk')

    class Meta:
        abstract = True


class UserObjectPermissionBase(BaseObjectPermission):
    """
    **Manager**: :manager:`UserObjectPermissionManager`
    """
    user = models.ForeignKey(user_model_label)

    objects = UserObjectPermissionManager()

    class Meta:
        abstract = True
        unique_together = ['user', 'permission', 'content_object']


class UserObjectPermission(UserObjectPermissionBase, BaseGenericObjectPermission):
    class Meta:
        unique_together = ['user', 'permission', 'object_pk']


class GroupObjectPermissionBase(BaseObjectPermission):
    """
    **Manager**: :manager:`GroupObjectPermissionManager`
    """
    group = models.ForeignKey(Group)

    objects = GroupObjectPermissionManager()

    class Meta:
        abstract = True
        unique_together = ['group', 'permission', 'content_object']


class GroupObjectPermission(GroupObjectPermissionBase, BaseGenericObjectPermission):
    class Meta:
        unique_together = ['group', 'permission', 'object_pk']


# As with Django 1.7, you can't use the get_user_model at this point
# because the app registry isn't ready yet (we're inside a model file).
import django
if django.VERSION < (1, 7):
    from . import monkey_patch_user
    monkey_patch_user()

setattr(Group, 'add_obj_perm',
    lambda self, perm, obj: GroupObjectPermission.objects.assign_perm(perm, self, obj))
setattr(Group, 'del_obj_perm',
    lambda self, perm, obj: GroupObjectPermission.objects.remove_perm(perm, self, obj))

########NEW FILE########
__FILENAME__ = shortcuts
"""
Convenient shortcuts to manage or check object permissions.
"""
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import _get_queryset
from itertools import groupby

from guardian.compat import get_user_model
from guardian.compat import basestring
from guardian.core import ObjectPermissionChecker
from guardian.exceptions import MixedContentTypeError
from guardian.exceptions import WrongAppError
from guardian.utils import get_anonymous_user
from guardian.utils import get_identity
from guardian.utils import get_user_obj_perms_model
from guardian.utils import get_group_obj_perms_model
import warnings

def assign_perm(perm, user_or_group, obj=None):
    """
    Assigns permission to user/group and object pair.

    :param perm: proper permission for given ``obj``, as string (in format:
      ``app_label.codename`` or ``codename``). If ``obj`` is not given, must
      be in format ``app_label.codename``.

    :param user_or_group: instance of ``User``, ``AnonymousUser`` or ``Group``;
      passing any other object would raise
      ``guardian.exceptions.NotUserNorGroup`` exception

    :param obj: persisted Django's ``Model`` instance or ``None`` if assigning
      global permission. Default is ``None``.

    We can assign permission for ``Model`` instance for specific user:

    >>> from django.contrib.sites.models import Site
    >>> from guardian.models import User
    >>> from guardian.shortcuts import assign_perm
    >>> site = Site.objects.get_current()
    >>> user = User.objects.create(username='joe')
    >>> assign_perm("change_site", user, site)
    <UserObjectPermission: example.com | joe | change_site>
    >>> user.has_perm("change_site", site)
    True

    ... or we can assign permission for group:

    >>> group = Group.objects.create(name='joe-group')
    >>> user.groups.add(group)
    >>> assign_perm("delete_site", group, site)
    <GroupObjectPermission: example.com | joe-group | delete_site>
    >>> user.has_perm("delete_site", site)
    True

    **Global permissions**

    This function may also be used to assign standard, *global* permissions if
    ``obj`` parameter is omitted. Added Permission would be returned in that
    case:

    >>> assign_perm("sites.change_site", user)
    <Permission: sites | site | Can change site>

    """

    user, group = get_identity(user_or_group)
    # If obj is None we try to operate on global permissions
    if obj is None:
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label,
            codename=codename)
        if user:
            user.user_permissions.add(perm)
            return perm
        if group:
            group.permissions.add(perm)
            return perm
    perm = perm.split('.')[-1]
    if user:
        model = get_user_obj_perms_model(obj)
        return model.objects.assign_perm(perm, user, obj)
    if group:
        model = get_group_obj_perms_model(obj)
        return model.objects.assign_perm(perm, group, obj)

def assign(perm, user_or_group, obj=None):
    """ Depreciated function name left in for compatibility"""
    warnings.warn("Shortcut function 'assign' is being renamed to 'assign_perm'. Update your code accordingly as old name will be depreciated in 2.0 version.", DeprecationWarning)
    return assign_perm(perm, user_or_group, obj)

def remove_perm(perm, user_or_group=None, obj=None):
    """
    Removes permission from user/group and object pair.

    :param perm: proper permission for given ``obj``, as string (in format:
      ``app_label.codename`` or ``codename``). If ``obj`` is not given, must
      be in format ``app_label.codename``.

    :param user_or_group: instance of ``User``, ``AnonymousUser`` or ``Group``;
      passing any other object would raise
      ``guardian.exceptions.NotUserNorGroup`` exception

    :param obj: persisted Django's ``Model`` instance or ``None`` if assigning
      global permission. Default is ``None``.

    """
    user, group = get_identity(user_or_group)
    if obj is None:
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label,
            codename=codename)
        if user:
            user.user_permissions.remove(perm)
            return
        elif group:
            group.permissions.remove(perm)
            return
    perm = perm.split('.')[-1]
    if user:
        model = get_user_obj_perms_model(obj)
        model.objects.remove_perm(perm, user, obj)
    if group:
        model = get_group_obj_perms_model(obj)
        model.objects.remove_perm(perm, group, obj)

def get_perms(user_or_group, obj):
    """
    Returns permissions for given user/group and object pair, as list of
    strings.
    """
    check = ObjectPermissionChecker(user_or_group)
    return check.get_perms(obj)

def get_perms_for_model(cls):
    """
    Returns queryset of all Permission objects for the given class. It is
    possible to pass Model as class or instance.
    """
    if isinstance(cls, basestring):
        app_label, model_name = cls.split('.')
        model = models.get_model(app_label, model_name)
    else:
        model = cls
    ctype = ContentType.objects.get_for_model(model)
    return Permission.objects.filter(content_type=ctype)

def get_users_with_perms(obj, attach_perms=False, with_superusers=False,
        with_group_users=True):
    """
    Returns queryset of all ``User`` objects with *any* object permissions for
    the given ``obj``.

    :param obj: persisted Django's ``Model`` instance

    :param attach_perms: Default: ``False``. If set to ``True`` result would be
      dictionary of ``User`` instances with permissions' codenames list as
      values. This would fetch users eagerly!

    :param with_superusers: Default: ``False``. If set to ``True`` result would
      contain all superusers.

    :param with_group_users: Default: ``True``. If set to ``False`` result would
      **not** contain those users who have only group permissions for given
      ``obj``.

    Example::

        >>> from django.contrib.flatpages.models import FlatPage
        >>> from django.contrib.auth.models import User
        >>> from guardian.shortcuts import assign_perm, get_users_with_perms
        >>>
        >>> page = FlatPage.objects.create(title='Some page', path='/some/page/')
        >>> joe = User.objects.create_user('joe', 'joe@example.com', 'joesecret')
        >>> assign_perm('change_flatpage', joe, page)
        >>>
        >>> get_users_with_perms(page)
        [<User: joe>]
        >>>
        >>> get_users_with_perms(page, attach_perms=True)
        {<User: joe>: [u'change_flatpage']}

    """
    ctype = ContentType.objects.get_for_model(obj)
    if not attach_perms:
        # It's much easier without attached perms so we do it first if that is
        # the case
        user_model = get_user_obj_perms_model(obj)
        related_name = user_model.user.field.related_query_name()
        if user_model.objects.is_generic():
            user_filters = {
                '%s__content_type' % related_name: ctype,
                '%s__object_pk' % related_name: obj.pk,
            }
        else:
            user_filters = {'%s__content_object' % related_name: obj}
        qset = Q(**user_filters)
        if with_group_users:
            group_model = get_group_obj_perms_model(obj)
            group_rel_name = group_model.group.field.related_query_name()
            if group_model.objects.is_generic():
                group_filters = {
                    'groups__%s__content_type' % group_rel_name: ctype,
                    'groups__%s__object_pk' % group_rel_name: obj.pk,
                }
            else:
                group_filters = {
                    'groups__%s__content_object' % group_rel_name: obj,
                }
            qset = qset | Q(**group_filters)
        if with_superusers:
            qset = qset | Q(is_superuser=True)
        return get_user_model().objects.filter(qset).distinct()
    else:
        # TODO: Do not hit db for each user!
        users = {}
        for user in get_users_with_perms(obj,
                with_group_users=with_group_users):
            users[user] = sorted(get_perms(user, obj))
        return users

def get_groups_with_perms(obj, attach_perms=False):
    """
    Returns queryset of all ``Group`` objects with *any* object permissions for
    the given ``obj``.

    :param obj: persisted Django's ``Model`` instance

    :param attach_perms: Default: ``False``. If set to ``True`` result would be
      dictionary of ``Group`` instances with permissions' codenames list as
      values. This would fetch groups eagerly!

    Example::

        >>> from django.contrib.flatpages.models import FlatPage
        >>> from guardian.shortcuts import assign_perm, get_groups_with_perms
        >>> from guardian.models import Group
        >>>
        >>> page = FlatPage.objects.create(title='Some page', path='/some/page/')
        >>> admins = Group.objects.create(name='Admins')
        >>> assign_perm('change_flatpage', admins, page)
        >>>
        >>> get_groups_with_perms(page)
        [<Group: admins>]
        >>>
        >>> get_groups_with_perms(page, attach_perms=True)
        {<Group: admins>: [u'change_flatpage']}

    """
    ctype = ContentType.objects.get_for_model(obj)
    if not attach_perms:
        # It's much easier without attached perms so we do it first if that is
        # the case
        group_model = get_group_obj_perms_model(obj)
        group_rel_name = group_model.group.field.related_query_name()
        if group_model.objects.is_generic():
            group_filters = {
                '%s__content_type' % group_rel_name: ctype,
                '%s__object_pk' % group_rel_name: obj.pk,
            }
        else:
            group_filters = {'%s__content_object' % group_rel_name: obj}
        groups = Group.objects.filter(**group_filters).distinct()
        return groups
    else:
        # TODO: Do not hit db for each group!
        groups = {}
        for group in get_groups_with_perms(obj):
            if not group in groups:
                groups[group] = sorted(get_perms(group, obj))
        return groups

def get_objects_for_user(user, perms, klass=None, use_groups=True, any_perm=False,
        with_superuser=True):
    """
    Returns queryset of objects for which a given ``user`` has *all*
    permissions present at ``perms``.

    :param user: ``User`` or ``AnonymousUser`` instance for which objects would
      be returned.
    :param perms: single permission string, or sequence of permission strings
      which should be checked.
      If ``klass`` parameter is not given, those should be full permission
      names rather than only codenames (i.e. ``auth.change_user``). If more than
      one permission is present within sequence, their content type **must** be
      the same or ``MixedContentTypeError`` exception would be raised.
    :param klass: may be a Model, Manager or QuerySet object. If not given
      this parameter would be computed based on given ``params``.
    :param use_groups: if ``False``, wouldn't check user's groups object
      permissions. Default is ``True``.
    :param any_perm: if True, any of permission in sequence is accepted
    :param with_superuser: if ``True`` returns the entire queryset if not it will
    only return objects the user has explicit permissions.
    
    :raises MixedContentTypeError: when computed content type for ``perms``
      and/or ``klass`` clashes.
    :raises WrongAppError: if cannot compute app label for given ``perms``/
      ``klass``.

    Example::

        >>> from django.contrib.auth.models import User
        >>> from guardian.shortcuts import get_objects_for_user
        >>> joe = User.objects.get(username='joe')
        >>> get_objects_for_user(joe, 'auth.change_group')
        []
        >>> from guardian.shortcuts import assign_perm
        >>> group = Group.objects.create('some group')
        >>> assign_perm('auth.change_group', joe, group)
        >>> get_objects_for_user(joe, 'auth.change_group')
        [<Group some group>]

    The permission string can also be an iterable. Continuing with the previous example:

        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        []
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'], any_perm=True)
        [<Group some group>]
        >>> assign_perm('auth.delete_group', joe, group)
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        [<Group some group>]

    """
    if isinstance(perms, basestring):
        perms = [perms]
    ctype = None
    app_label = None
    codenames = set()

    # Compute codenames set and ctype if possible
    for perm in perms:
        if '.' in perm:
            new_app_label, codename = perm.split('.', 1)
            if app_label is not None and app_label != new_app_label:
                raise MixedContentTypeError("Given perms must have same app "
                    "label (%s != %s)" % (app_label, new_app_label))
            else:
                app_label = new_app_label
        else:
            codename = perm
        codenames.add(codename)
        if app_label is not None:
            new_ctype = ContentType.objects.get(app_label=app_label,
                permission__codename=codename)
            if ctype is not None and ctype != new_ctype:
                raise MixedContentTypeError("ContentType was once computed "
                    "to be %s and another one %s" % (ctype, new_ctype))
            else:
                ctype = new_ctype

    # Compute queryset and ctype if still missing
    if ctype is None and klass is None:
        raise WrongAppError("Cannot determine content type")
    elif ctype is None and klass is not None:
        queryset = _get_queryset(klass)
        ctype = ContentType.objects.get_for_model(queryset.model)
    elif ctype is not None and klass is None:
        queryset = _get_queryset(ctype.model_class())
    else:
        queryset = _get_queryset(klass)
        if ctype.model_class() != queryset.model:
            raise MixedContentTypeError("Content type for given perms and "
                "klass differs")

    # At this point, we should have both ctype and queryset and they should
    # match which means: ctype.model_class() == queryset.model
    # we should also have ``codenames`` list

    # First check if user is superuser and if so, return queryset immediately
    if with_superuser and user.is_superuser:
        return queryset

    # Check if the user is anonymous. The
    # django.contrib.auth.models.AnonymousUser object doesn't work for queries
    # and it's nice to be able to pass in request.user blindly.
    if user.is_anonymous():
        user = get_anonymous_user()

    # Now we should extract list of pk values for which we would filter queryset
    user_model = get_user_obj_perms_model(queryset.model)
    user_obj_perms_queryset = (user_model.objects
        .filter(user=user)
        .filter(permission__content_type=ctype)
        .filter(permission__codename__in=codenames))
    if user_model.objects.is_generic():
        fields = ['object_pk', 'permission__codename']
    else:
        fields = ['content_object__pk', 'permission__codename']

    if use_groups:
        group_model = get_group_obj_perms_model(queryset.model)
        group_filters = {
            'permission__content_type': ctype,
            'permission__codename__in': codenames,
            'group__%s' % get_user_model().groups.field.related_query_name(): user,
        }
        groups_obj_perms_queryset = group_model.objects.filter(**group_filters)
        if group_model.objects.is_generic():
            fields = ['object_pk', 'permission__codename']
        else:
            fields = ['content_object__pk', 'permission__codename']
        if not any_perm:
            user_obj_perms = user_obj_perms_queryset.values_list(*fields)
            groups_obj_perms = groups_obj_perms_queryset.values_list(*fields)
            data = list(user_obj_perms) + list(groups_obj_perms)
            keyfunc = lambda t: t[0] # sorting/grouping by pk (first in result tuple)
            data = sorted(data, key=keyfunc)
            pk_list = []
            for pk, group in groupby(data, keyfunc):
                obj_codenames = set((e[1] for e in group))
                if codenames.issubset(obj_codenames):
                    pk_list.append(pk)
            objects = queryset.filter(pk__in=pk_list)
            return objects

    if not any_perm and len(codenames) > 1:
        counts = user_obj_perms_queryset.values(fields[0]).annotate(object_pk_count=Count(fields[0]))
        user_obj_perms_queryset = counts.filter(object_pk_count__gte=len(codenames))

    values = user_obj_perms_queryset.values_list(fields[0], flat=True)
    if user_model.objects.is_generic():
        values = [int(v) for v in values]
    objects = queryset.filter(pk__in=values)
    if use_groups:
        values = groups_obj_perms_queryset.values_list(fields[0], flat=True)
        if group_model.objects.is_generic():
            values = [int(v) for v in values]
        objects |= queryset.filter(pk__in=values)

    return objects

def get_objects_for_group(group, perms, klass=None, any_perm=False):
    """
    Returns queryset of objects for which a given ``group`` has *all*
    permissions present at ``perms``.

    :param group: ``Group`` instance for which objects would be returned.
    :param perms: single permission string, or sequence of permission strings
      which should be checked.
      If ``klass`` parameter is not given, those should be full permission
      names rather than only codenames (i.e. ``auth.change_user``). If more than
      one permission is present within sequence, their content type **must** be
      the same or ``MixedContentTypeError`` exception would be raised.
    :param klass: may be a Model, Manager or QuerySet object. If not given
      this parameter would be computed based on given ``params``.
    :param any_perm: if True, any of permission in sequence is accepted

    :raises MixedContentTypeError: when computed content type for ``perms``
      and/or ``klass`` clashes.
    :raises WrongAppError: if cannot compute app label for given ``perms``/
      ``klass``.

    Example:

    Let's assume we have a ``Task`` model belonging to the ``tasker`` app with
    the default add_task, change_task and delete_task permissions provided
    by Django::

        >>> from guardian.shortcuts import get_objects_for_group
        >>> from tasker import Task
        >>> group = Group.objects.create('some group')
        >>> task = Task.objects.create('some task')
        >>> get_objects_for_group(group, 'tasker.add_task')
        []
        >>> from guardian.shortcuts import assign_perm
        >>> assign_perm('tasker.add_task', group, task)
        >>> get_objects_for_group(group, 'tasker.add_task')
        [<Task some task>]

    The permission string can also be an iterable. Continuing with the previous example:
        >>> get_objects_for_group(group, ['tasker.add_task', 'tasker.delete_task'])
        []
        >>> assign_perm('tasker.delete_task', group, task)
        >>> get_objects_for_group(group, ['tasker.add_task', 'tasker.delete_task'])
        [<Task some task>]

    """
    if isinstance(perms, basestring):
        perms = [perms]
    ctype = None
    app_label = None
    codenames = set()

    # Compute codenames set and ctype if possible
    for perm in perms:
        if '.' in perm:
            new_app_label, codename = perm.split('.', 1)
            if app_label is not None and app_label != new_app_label:
                raise MixedContentTypeError("Given perms must have same app "
                    "label (%s != %s)" % (app_label, new_app_label))
            else:
                app_label = new_app_label
        else:
            codename = perm
        codenames.add(codename)
        if app_label is not None:
            new_ctype = ContentType.objects.get(app_label=app_label,
                permission__codename=codename)
            if ctype is not None and ctype != new_ctype:
                raise MixedContentTypeError("ContentType was once computed "
                    "to be %s and another one %s" % (ctype, new_ctype))
            else:
                ctype = new_ctype

    # Compute queryset and ctype if still missing
    if ctype is None and klass is None:
        raise WrongAppError("Cannot determine content type")
    elif ctype is None and klass is not None:
        queryset = _get_queryset(klass)
        ctype = ContentType.objects.get_for_model(queryset.model)
    elif ctype is not None and klass is None:
        queryset = _get_queryset(ctype.model_class())
    else:
        queryset = _get_queryset(klass)
        if ctype.model_class() != queryset.model:
            raise MixedContentTypeError("Content type for given perms and "
                "klass differs")

    # At this point, we should have both ctype and queryset and they should
    # match which means: ctype.model_class() == queryset.model
    # we should also have ``codenames`` list

    # Now we should extract list of pk values for which we would filter queryset
    group_model = get_group_obj_perms_model(queryset.model)
    groups_obj_perms_queryset = (group_model.objects
        .filter(group=group)
        .filter(permission__content_type=ctype)
        .filter(permission__codename__in=codenames))
    if group_model.objects.is_generic():
        fields = ['object_pk', 'permission__codename']
    else:
        fields = ['content_object__pk', 'permission__codename']
    groups_obj_perms = groups_obj_perms_queryset.values_list(*fields)
    data = list(groups_obj_perms)

    keyfunc = lambda t: t[0] # sorting/grouping by pk (first in result tuple)
    data = sorted(data, key=keyfunc)
    pk_list = []
    for pk, group in groupby(data, keyfunc):
        obj_codenames = set((e[1] for e in group))
        if any_perm or codenames.issubset(obj_codenames):
            pk_list.append(pk)

    objects = queryset.filter(pk__in=pk_list)
    return objects

########NEW FILE########
__FILENAME__ = guardian_tags
"""
``django-guardian`` template tags. To use in a template just put the following
*load* tag inside a template::

    {% load guardian_tags %}

"""
from __future__ import unicode_literals
from django import template
from django.contrib.auth.models import Group, AnonymousUser
from django.template import get_library
from django.template import InvalidTemplateLibrary
from django.template.defaulttags import LoadNode

from guardian.compat import get_user_model
from guardian.exceptions import NotUserNorGroup
from guardian.core import ObjectPermissionChecker

register = template.Library()


@register.tag
def friendly_load(parser, token):
    '''
    Tries to load a custom template tag set. Non existing tag libraries
    are ignored.

    This means that, if used in conjuction with ``if_has_tag``, you can try to
    load the comments template tag library to enable comments even if the
    comments framework is not installed.

    For example::

        {% load friendly_loader %}
        {% friendly_load comments webdesign %}

        {% if_has_tag render_comment_list %}
            {% render_comment_list for obj %}
        {% else %}
            {% if_has_tag lorem %}
                {% lorem %}
            {% endif_has_tag %}
        {% endif_has_tag %}
    '''
    bits = token.contents.split()
    for taglib in bits[1:]:
        try:
            lib = get_library(taglib)
            parser.add_library(lib)
        except InvalidTemplateLibrary:
            pass
    return LoadNode()




class ObjectPermissionsNode(template.Node):
    def __init__(self, for_whom, obj, context_var):
        self.for_whom = template.Variable(for_whom)
        self.obj = template.Variable(obj)
        self.context_var = context_var

    def render(self, context):
        for_whom = self.for_whom.resolve(context)
        if isinstance(for_whom, get_user_model()):
            self.user = for_whom
            self.group = None
        elif isinstance(for_whom, AnonymousUser):
            self.user = get_user_model().get_anonymous()
            self.group = None
        elif isinstance(for_whom, Group):
            self.user = None
            self.group = for_whom
        else:
            raise NotUserNorGroup("User or Group instance required (got %s)"
                % for_whom.__class__)
        obj = self.obj.resolve(context)
        if not obj:
            return ''

        check = ObjectPermissionChecker(for_whom)
        perms = check.get_perms(obj)

        context[self.context_var] = perms
        return ''

@register.tag
def get_obj_perms(parser, token):
    """
    Returns a list of permissions (as ``codename`` strings) for a given
    ``user``/``group`` and ``obj`` (Model instance).

    Parses ``get_obj_perms`` tag which should be in format::

        {% get_obj_perms user/group for obj as "context_var" %}

    .. note::
       Make sure that you set and use those permissions in same template
       block (``{% block %}``).

    Example of usage (assuming ``flatpage`` and ``perm`` objects are
    available from *context*)::

        {% get_obj_perms request.user for flatpage as "flatpage_perms" %}

        {% if "delete_flatpage" in flatpage_perms %}
            <a href="/pages/delete?target={{ flatpage.url }}">Remove page</a>
        {% endif %}

    .. note::
       Please remember that superusers would always get full list of permissions
       for a given object.

    .. versionadded:: 1.2

    As of v1.2, passing ``None`` as ``obj`` for this template tag won't rise
    obfuscated exception and would return empty permissions set instead.

    """
    bits = token.split_contents()
    format = '{% get_obj_perms user/group for obj as "context_var" %}'
    if len(bits) != 6 or bits[2] != 'for' or bits[4] != 'as':
        raise template.TemplateSyntaxError("get_obj_perms tag should be in "
            "format: %s" % format)

    for_whom = bits[1]
    obj = bits[3]
    context_var = bits[5]
    if context_var[0] != context_var[-1] or context_var[0] not in ('"', "'"):
        raise template.TemplateSyntaxError("get_obj_perms tag's context_var "
            "argument should be in quotes")
    context_var = context_var[1:-1]
    return ObjectPermissionsNode(for_whom, obj, context_var)


########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from datetime import datetime
from django.db import models
from django.contrib.admin.models import LogEntry
from guardian.models import UserObjectPermissionBase, GroupObjectPermissionBase


class DynamicAccessor(object):
    def __init__(self):
        pass

    def __getattr__(self, key):
        return DynamicAccessor()


class ProjectUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey('Project')


class ProjectGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey('Project')


class Project(models.Model):
    name = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(default=datetime.now)

    class Meta:
        get_latest_by = 'created_at'

    def __unicode__(self):
        return self.name

Project.not_a_relation_descriptor = DynamicAccessor()


class MixedGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey('Mixed')


class Mixed(models.Model):
    """
    Model for tests obj perms checks with generic user object permissions model
    and direct group object permissions model.
    """
    name = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name


class LogEntryWithGroup(LogEntry):
    group = models.ForeignKey('auth.Group', null=True, blank=True)


########NEW FILE########
__FILENAME__ = admin_test
from __future__ import unicode_literals
import copy

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.test import TestCase
from django.test.client import Client

from guardian.admin import GuardedModelAdmin
from guardian.compat import get_user_model
from guardian.compat import str
from guardian.shortcuts import get_perms
from guardian.shortcuts import get_perms_for_model
from guardian.testapp.tests.conf import TEST_SETTINGS
from guardian.testapp.tests.conf import override_settings
from guardian.models import Group
from guardian.testapp.tests.conf import skipUnlessTestApp
from guardian.testapp.models import LogEntryWithGroup as LogEntry

User = get_user_model()

class ContentTypeGuardedAdmin(GuardedModelAdmin):
    pass

try:
    admin.site.unregister(ContentType)
except admin.sites.NotRegistered:
    pass
admin.site.register(ContentType, ContentTypeGuardedAdmin)

@override_settings(**TEST_SETTINGS)
class AdminTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com',
            'admin')
        self.user = User.objects.create_user('joe', 'joe@example.com', 'joe')
        self.group = Group.objects.create(name='group')
        self.client = Client()
        self.obj = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        self.obj_info = self.obj._meta.app_label, self.obj._meta.module_name

    def tearDown(self):
        self.client.logout()

    def _login_superuser(self):
        self.client.login(username='admin', password='admin')

    def test_view_manage_wrong_obj(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_user' % self.obj_info,
                kwargs={'object_pk': -10, 'user_id': self.user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.obj)

    def test_view_manage_wrong_user(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_user' % self.obj_info,
            kwargs={'object_pk': self.obj.pk, 'user_id': -10})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view_manage_user_form(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'user': self.user.username, 'submit_manage_user': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        redirect_url = reverse('admin:%s_%s_permissions_manage_user' %
            self.obj_info, kwargs={'object_pk': self.obj.pk,
                'user_id': self.user.id})
        self.assertEqual(response.request['PATH_INFO'], redirect_url)

    def test_view_manage_negative_user_form(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        self.user = User.objects.create(username='negative_id_user', id=-2010)
        data = {'user': self.user.username, 'submit_manage_user': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        redirect_url = reverse('admin:%s_%s_permissions_manage_user' %
            self.obj_info, args=[self.obj.pk, self.user.id])
        self.assertEqual(response.request['PATH_INFO'], redirect_url)

    def test_view_manage_user_form_wrong_user(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'user': 'wrong-user', 'submit_manage_user': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('user' in response.context['user_form'].errors)

    def test_view_manage_user_form_wrong_field(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'user': '<xss>', 'submit_manage_user': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('user' in response.context['user_form'].errors)

    def test_view_manage_user_form_empty_user(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'user': '', 'submit_manage_user': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('user' in response.context['user_form'].errors)

    def test_view_manage_user_wrong_perms(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_user' % self.obj_info,
            args=[self.obj.pk, self.user.id])
        perms = ['change_user'] # This is not self.obj related permission
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('permissions' in response.context['form'].errors)

    def test_view_manage_user(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_user' % self.obj_info,
            args=[self.obj.pk, self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        choices = set([c[0] for c in
            response.context['form'].fields['permissions'].choices])
        self.assertEqual(
            set([ p.codename for p in get_perms_for_model(self.obj)]),
            choices,
        )

        # Add some perms and check if changes were persisted
        perms = ['change_%s' % self.obj_info[1], 'delete_%s' % self.obj_info[1]]
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)

        self.assertEqual(
            set(get_perms(self.user, self.obj)),
            set(perms),
        )

        # Remove perm and check if change was persisted
        perms = ['change_%s' % self.obj_info[1]]
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)

        self.assertEqual(
            set(get_perms(self.user, self.obj)),
            set(perms),
        )

    def test_view_manage_group_form(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'group': self.group.name, 'submit_manage_group': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        redirect_url = reverse('admin:%s_%s_permissions_manage_group' %
            self.obj_info, args=[self.obj.pk, self.group.id])
        self.assertEqual(response.request['PATH_INFO'], redirect_url)

    def test_view_manage_negative_group_form(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        self.group = Group.objects.create(name='neagive_id_group', id=-2010)
        data = {'group': self.group.name, 'submit_manage_group': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        redirect_url = reverse('admin:%s_%s_permissions_manage_group' %
            self.obj_info, args=[self.obj.pk, self.group.id])
        self.assertEqual(response.request['PATH_INFO'], redirect_url)

    def test_view_manage_group_form_wrong_group(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'group': 'wrong-group', 'submit_manage_group': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('group' in response.context['group_form'].errors)

    def test_view_manage_group_form_wrong_field(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'group': '<xss>', 'submit_manage_group': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('group' in response.context['group_form'].errors)

    def test_view_manage_group_form_empty_group(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions' % self.obj_info,
            args=[self.obj.pk])
        data = {'group': '', 'submit_manage_group': 'submit'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('group' in response.context['group_form'].errors)

    def test_view_manage_group_wrong_perms(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_group' %
            self.obj_info, args=[self.obj.pk, self.group.id])
        perms = ['change_user'] # This is not self.obj related permission
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('permissions' in response.context['form'].errors)

    def test_view_manage_group(self):
        self._login_superuser()
        url = reverse('admin:%s_%s_permissions_manage_group' %
            self.obj_info, args=[self.obj.pk, self.group.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        choices = set([c[0] for c in
            response.context['form'].fields['permissions'].choices])
        self.assertEqual(
            set([ p.codename for p in get_perms_for_model(self.obj)]),
            choices,
        )

        # Add some perms and check if changes were persisted
        perms = ['change_%s' % self.obj_info[1], 'delete_%s' % self.obj_info[1]]
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)

        self.assertEqual(
            set(get_perms(self.group, self.obj)),
            set(perms),
        )

        # Remove perm and check if change was persisted
        perms = ['delete_%s' % self.obj_info[1]]
        data = {'permissions': perms}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)

        self.assertEqual(
            set(get_perms(self.group, self.obj)),
            set(perms),
        )

if 'django.contrib.admin' not in settings.INSTALLED_APPS:
    # Skip admin tests if admin app is not registered
    # we simpy clean up AdminTests class ...
    # TODO: use @unittest.skipUnless('django.contrib.admin' in settings.INSTALLED_APPS)
    #       if possible (requires Python 2.7, though)
    AdminTests = type('AdminTests', (TestCase,), {}) # pyflakes:ignore


@skipUnlessTestApp
class GuardedModelAdminTests(TestCase):

    def _get_gma(self, attrs=None, name=None, model=None):
        """
        Returns ``GuardedModelAdmin`` instance.
        """
        attrs = attrs or {}
        name = str(name or 'GMA')
        model = model or User
        GMA = type(name, (GuardedModelAdmin,), attrs)
        gma = GMA(model, admin.site)
        return gma

    def test_obj_perms_manage_template_attr(self):
        attrs = {'obj_perms_manage_template': 'foobar.html'}
        gma = self._get_gma(attrs=attrs)
        self.assertTrue(gma.get_obj_perms_manage_template(), 'foobar.html')

    def test_obj_perms_manage_user_template_attr(self):
        attrs = {'obj_perms_manage_user_template': 'foobar.html'}
        gma = self._get_gma(attrs=attrs)
        self.assertTrue(gma.get_obj_perms_manage_user_template(), 'foobar.html')

    def test_obj_perms_manage_user_form_attr(self):
        attrs = {'obj_perms_manage_user_form': forms.Form}
        gma = self._get_gma(attrs=attrs)
        self.assertTrue(gma.get_obj_perms_manage_user_form(), forms.Form)

    def test_obj_perms_manage_group_template_attr(self):
        attrs = {'obj_perms_manage_group_template': 'foobar.html'}
        gma = self._get_gma(attrs=attrs)
        self.assertTrue(gma.get_obj_perms_manage_group_template(),
            'foobar.html')

    def test_obj_perms_manage_group_form_attr(self):
        attrs = {'obj_perms_manage_group_form': forms.Form}
        gma = self._get_gma(attrs=attrs)
        self.assertTrue(gma.get_obj_perms_manage_group_form(), forms.Form)

    def test_user_can_acces_owned_objects_only(self):
        attrs = {
            'user_can_access_owned_objects_only': True,
            'user_owned_objects_field': 'user',
        }
        gma = self._get_gma(attrs=attrs, model=LogEntry)
        joe = User.objects.create_user('joe', 'joe@example.com', 'joe')
        jane = User.objects.create_user('jane', 'jane@example.com', 'jane')
        ctype = ContentType.objects.get_for_model(User)
        joe_entry = LogEntry.objects.create(user=joe, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo')
        LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=jane.id, action_flag=1, change_message='bar')
        request = HttpRequest()
        request.user = joe
        qs = gma.queryset(request)
        self.assertEqual([e.pk for e in qs], [joe_entry.pk])

    def test_user_can_acces_owned_objects_only_unless_superuser(self):
        attrs = {
            'user_can_access_owned_objects_only': True,
            'user_owned_objects_field': 'user',
        }
        gma = self._get_gma(attrs=attrs, model=LogEntry)
        joe = User.objects.create_superuser('joe', 'joe@example.com', 'joe')
        jane = User.objects.create_user('jane', 'jane@example.com', 'jane')
        ctype = ContentType.objects.get_for_model(User)
        joe_entry = LogEntry.objects.create(user=joe, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo')
        jane_entry = LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=jane.id, action_flag=1, change_message='bar')
        request = HttpRequest()
        request.user = joe
        qs = gma.queryset(request)
        self.assertEqual(sorted([e.pk for e in qs]),
            sorted([joe_entry.pk, jane_entry.pk]))

    def test_user_can_access_owned_by_group_objects_only(self):
        attrs = {
            'user_can_access_owned_by_group_objects_only': True,
            'group_owned_objects_field': 'group',
        }
        gma = self._get_gma(attrs=attrs, model=LogEntry)
        joe = User.objects.create_user('joe', 'joe@example.com', 'joe')
        joe_group = Group.objects.create(name='joe-group')
        joe.groups.add(joe_group)
        jane = User.objects.create_user('jane', 'jane@example.com', 'jane')
        jane_group = Group.objects.create(name='jane-group')
        jane.groups.add(jane_group)
        ctype = ContentType.objects.get_for_model(User)
        LogEntry.objects.create(user=joe, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo')
        LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=jane.id, action_flag=1, change_message='bar')
        joe_entry_group = LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo',
            group=joe_group)
        request = HttpRequest()
        request.user = joe
        qs = gma.queryset(request)
        self.assertEqual([e.pk for e in qs], [joe_entry_group.pk])

    def test_user_can_access_owned_by_group_objects_only_unless_superuser(self):
        attrs = {
            'user_can_access_owned_by_group_objects_only': True,
            'group_owned_objects_field': 'group',
        }
        gma = self._get_gma(attrs=attrs, model=LogEntry)
        joe = User.objects.create_superuser('joe', 'joe@example.com', 'joe')
        joe_group = Group.objects.create(name='joe-group')
        joe.groups.add(joe_group)
        jane = User.objects.create_user('jane', 'jane@example.com', 'jane')
        jane_group = Group.objects.create(name='jane-group')
        jane.groups.add(jane_group)
        ctype = ContentType.objects.get_for_model(User)
        LogEntry.objects.create(user=joe, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo')
        LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=jane.id, action_flag=1, change_message='bar')
        LogEntry.objects.create(user=jane, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo',
            group=joe_group)
        LogEntry.objects.create(user=joe, content_type=ctype,
            object_id=joe.id, action_flag=1, change_message='foo',
            group=jane_group)
        request = HttpRequest()
        request.user = joe
        qs = gma.queryset(request)
        self.assertEqual(sorted(e.pk for e in qs),
            sorted(LogEntry.objects.values_list('pk', flat=True)))


class GrappelliGuardedModelAdminTests(TestCase):

    org_installed_apps = copy.copy(settings.INSTALLED_APPS)

    def _get_gma(self, attrs=None, name=None, model=None):
        """
        Returns ``GuardedModelAdmin`` instance.
        """
        attrs = attrs or {}
        name = str(name or 'GMA')
        model = model or User
        GMA = type(name, (GuardedModelAdmin,), attrs)
        gma = GMA(model, admin.site)
        return gma

    def setUp(self):
        settings.INSTALLED_APPS = ['grappelli'] + list(settings.INSTALLED_APPS)

    def tearDown(self):
        settings.INSTALLED_APPS = self.org_installed_apps

    def test_get_obj_perms_manage_template(self):
        gma = self._get_gma()
        self.assertEqual(gma.get_obj_perms_manage_template(),
            'admin/guardian/contrib/grappelli/obj_perms_manage.html')

    def test_get_obj_perms_manage_user_template(self):
        gma = self._get_gma()
        self.assertEqual(gma.get_obj_perms_manage_user_template(),
            'admin/guardian/contrib/grappelli/obj_perms_manage_user.html')

    def test_get_obj_perms_manage_group_template(self):
        gma = self._get_gma()
        self.assertEqual(gma.get_obj_perms_manage_group_template(),
            'admin/guardian/contrib/grappelli/obj_perms_manage_group.html')


########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals
import os
from guardian.compat import unittest
from guardian.utils import abspath
from django.conf import settings
from django.conf import UserSettingsHolder
from django.utils.functional import wraps


THIS = abspath(os.path.dirname(__file__))
TEST_TEMPLATES_DIR = abspath(THIS, 'templates')


TEST_SETTINGS = dict(
    TEMPLATE_DIRS=[TEST_TEMPLATES_DIR],
)


def skipUnlessTestApp(obj):
    app = 'guardian.testapp' 
    return unittest.skipUnless(app in settings.INSTALLED_APPS,
                      'app %r must be installed to run this test' % app)(obj)


class TestDataMixin(object):
    def setUp(self):
        super(TestDataMixin, self).setUp()
        from django.contrib.auth.models import Group
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User
        Group.objects.create(pk=1, name='admins')
        jack_group = Group.objects.create(pk=2, name='jackGroup')
        User.objects.get_or_create(pk=settings.ANONYMOUS_USER_ID)
        jack = User.objects.create(pk=1, username='jack', is_active=True,
            is_superuser=False, is_staff=False)
        jack.groups.add(jack_group)


class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown
            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override

    def disable(self):
        settings._wrapped = self.wrapped


########NEW FILE########
__FILENAME__ = conf_test
from __future__ import unicode_literals
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from guardian.compat import mock
from guardian.conf import settings as guardian_settings


class TestConfiguration(TestCase):

    def test_check_configuration(self):

        with mock.patch('guardian.conf.settings.RENDER_403', True):
            with mock.patch('guardian.conf.settings.RAISE_403', True):
                self.assertRaises(ImproperlyConfigured,
                    guardian_settings.check_configuration)


########NEW FILE########
__FILENAME__ = core_test
from __future__ import unicode_literals
from itertools import chain

from django.conf import settings
# Try the new app settings (Django 1.7) and fall back to the old system
try:
    from django.apps import apps as django_apps
    auth_app = django_apps.get_app_config("auth")
except ImportError:
    from django.contrib.auth import models as auth_app
from django.contrib.auth.models import Group, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from guardian.core import ObjectPermissionChecker
from guardian.compat import get_user_model, create_permissions
from guardian.exceptions import NotUserNorGroup
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.shortcuts import assign_perm

User = get_user_model()

class ObjectPermissionTestCase(TestCase):

    def setUp(self):
        self.group, created = Group.objects.get_or_create(name='jackGroup')
        self.user, created = User.objects.get_or_create(username='jack')
        self.user.groups.add(self.group)
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        try:
            self.anonymous_user = User.objects.get(id=settings.ANONYMOUS_USER_ID)
        except User.DoesNotExist:
            self.anonymous_user = User(
                id=settings.ANONYMOUS_USER_ID,
                username='AnonymousUser',
            )
            self.anonymous_user.save()


class ObjectPermissionCheckerTest(ObjectPermissionTestCase):

    def setUp(self):
        super(ObjectPermissionCheckerTest, self).setUp()
        # Required if MySQL backend is used :/
        create_permissions(auth_app, [], 1)

    def test_cache_for_queries_count(self):
        settings.DEBUG = True
        try:
            from django.db import connection

            ContentType.objects.clear_cache()
            checker = ObjectPermissionChecker(self.user)

            # has_perm on Checker should spawn only two queries plus one extra
            # for fetching the content type first time we check for specific
            # model and two more content types as there are additional checks
            # at get_user_obj_perms_model and get_group_obj_perms_model
            query_count = len(connection.queries)
            res = checker.has_perm("change_group", self.group)
            if 'guardian.testapp' in settings.INSTALLED_APPS:
                expected = 5
            else:
                # TODO: This is strange, need to investigate; totally not sure
                # why there are more queries if testapp is not included
                expected = 11
            self.assertEqual(len(connection.queries), query_count + expected)

            # Checking again shouldn't spawn any queries
            query_count = len(connection.queries)
            res_new = checker.has_perm("change_group", self.group)
            self.assertEqual(res, res_new)
            self.assertEqual(len(connection.queries), query_count)

            # Checking for other permission but for Group object again
            # shouldn't spawn any query too
            query_count = len(connection.queries)
            checker.has_perm("delete_group", self.group)
            self.assertEqual(len(connection.queries), query_count)

            # Checking for same model but other instance should spawn 2 queries
            new_group = Group.objects.create(name='new-group')
            query_count = len(connection.queries)
            checker.has_perm("change_group", new_group)
            self.assertEqual(len(connection.queries), query_count + 2)

            # Checking for permission for other model should spawn 3 queries
            # (again: content type and actual permissions for the object...
            query_count = len(connection.queries)
            checker.has_perm("change_user", self.user)
            self.assertEqual(len(connection.queries), query_count + 3)

        finally:
            settings.DEBUG = False

    def test_init(self):
        self.assertRaises(NotUserNorGroup, ObjectPermissionChecker,
            user_or_group=ContentType())
        self.assertRaises(NotUserNorGroup, ObjectPermissionChecker)

    def test_anonymous_user(self):
        user = AnonymousUser()
        check = ObjectPermissionChecker(user)
        # assert anonymous user has no object permissions at all for obj
        self.assertTrue( [] == list(check.get_perms(self.ctype)) )

    def test_superuser(self):
        user = User.objects.create(username='superuser', is_superuser=True)
        check = ObjectPermissionChecker(user)
        ctype = ContentType.objects.get_for_model(self.ctype)
        perms = sorted(chain(*Permission.objects
            .filter(content_type=ctype)
            .values_list('codename')))
        self.assertEqual(perms, check.get_perms(self.ctype))
        for perm in perms:
            self.assertTrue(check.has_perm(perm, self.ctype))

    def test_not_active_superuser(self):
        user = User.objects.create(username='not_active_superuser',
            is_superuser=True, is_active=False)
        check = ObjectPermissionChecker(user)
        ctype = ContentType.objects.get_for_model(self.ctype)
        perms = sorted(chain(*Permission.objects
            .filter(content_type=ctype)
            .values_list('codename')))
        self.assertEqual(check.get_perms(self.ctype), [])
        for perm in perms:
            self.assertFalse(check.has_perm(perm, self.ctype))

    def test_not_active_user(self):
        user = User.objects.create(username='notactive')
        assign_perm("change_contenttype", user, self.ctype)

        # new ObjectPermissionChecker is created for each User.has_perm call
        self.assertTrue(user.has_perm("change_contenttype", self.ctype))
        user.is_active = False
        self.assertFalse(user.has_perm("change_contenttype", self.ctype))

        # use on one checker only (as user's is_active attr should be checked
        # before try to use cache
        user = User.objects.create(username='notactive-cache')
        assign_perm("change_contenttype", user, self.ctype)

        check = ObjectPermissionChecker(user)
        self.assertTrue(check.has_perm("change_contenttype", self.ctype))
        user.is_active = False
        self.assertFalse(check.has_perm("change_contenttype", self.ctype))

    def test_get_perms(self):
        group = Group.objects.create(name='group')
        obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')

        assign_perms = {
            group: ('change_group', 'delete_group'),
            obj1: ('change_contenttype', 'delete_contenttype'),
            obj2: ('delete_contenttype',),
        }

        check = ObjectPermissionChecker(self.user)

        for obj, perms in assign_perms.items():
            for perm in perms:
                UserObjectPermission.objects.assign_perm(perm, self.user, obj)
            self.assertEqual(sorted(perms), sorted(check.get_perms(obj)))

        check = ObjectPermissionChecker(self.group)

        for obj, perms in assign_perms.items():
            for perm in perms:
                GroupObjectPermission.objects.assign_perm(perm, self.group, obj)
            self.assertEqual(sorted(perms), sorted(check.get_perms(obj)))


########NEW FILE########
__FILENAME__ = custompkmodel_test
from __future__ import unicode_literals
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from guardian.compat import get_user_model
from guardian.shortcuts import assign_perm, remove_perm


class CustomPKModelTest(TestCase):
    """
    Tests agains custom model with primary key other than *standard*
    ``id`` integer field.
    """

    def setUp(self):
        self.user = get_user_model().objects.create(username='joe')
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')

    def test_assign_perm(self):
        assign_perm('contenttypes.change_contenttype', self.user, self.ctype)
        self.assertTrue(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))

    def test_remove_perm(self):
        assign_perm('contenttypes.change_contenttype', self.user, self.ctype)
        self.assertTrue(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))
        remove_perm('contenttypes.change_contenttype', self.user, self.ctype)
        self.assertFalse(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))


########NEW FILE########
__FILENAME__ = decorators_test
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth.models import Group, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models.base import ModelBase
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import TemplateDoesNotExist
from django.test import TestCase

from guardian.compat import get_user_model
from guardian.compat import get_user_model_path
from guardian.compat import get_user_permission_full_codename
from guardian.compat import mock
from guardian.decorators import permission_required, permission_required_or_403
from guardian.exceptions import GuardianError
from guardian.exceptions import WrongAppError
from guardian.shortcuts import assign_perm
from guardian.testapp.tests.conf import TEST_SETTINGS
from guardian.testapp.tests.conf import TestDataMixin
from guardian.testapp.tests.conf import override_settings
from guardian.testapp.tests.conf import skipUnlessTestApp

User = get_user_model()
user_model_path = get_user_model_path()


@override_settings(**TEST_SETTINGS)
@skipUnlessTestApp
class PermissionRequiredTest(TestDataMixin, TestCase):

    def setUp(self):
        super(PermissionRequiredTest, self).setUp()
        self.anon = AnonymousUser()
        self.user = User.objects.get_or_create(username='jack')[0]
        self.group = Group.objects.get_or_create(name='jackGroup')[0]

    def _get_request(self, user=None):
        if user is None:
            user = AnonymousUser()
        request = HttpRequest()
        request.user = user
        return request

    def test_no_args(self):

        try:
            @permission_required
            def dummy_view(request):
                return HttpResponse('dummy_view')
        except GuardianError:
            pass
        else:
            self.fail("Trying to decorate using permission_required without "
                "permission as first argument should raise exception")

    def test_RENDER_403_is_false(self):
        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')

        with mock.patch('guardian.conf.settings.RENDER_403', False):
            response = dummy_view(request)
            self.assertEqual(response.content, b'')
            self.assertTrue(isinstance(response, HttpResponseForbidden))

    @mock.patch('guardian.conf.settings.RENDER_403', True)
    def test_TEMPLATE_403_setting(self):
        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')

        with mock.patch('guardian.conf.settings.TEMPLATE_403', 'dummy403.html'):
            response = dummy_view(request)
            self.assertEqual(response.content, b'foobar403\n')

    @mock.patch('guardian.conf.settings.RENDER_403', True)
    def test_403_response_is_empty_if_template_cannot_be_found(self):
        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        with mock.patch('guardian.conf.settings.TEMPLATE_403',
            '_non-exisitng-403.html'):
            response = dummy_view(request)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.content, b'')

    @mock.patch('guardian.conf.settings.RENDER_403', True)
    def test_403_response_raises_error_if_debug_is_turned_on(self):
        org_DEBUG = settings.DEBUG
        settings.DEBUG = True
        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        with mock.patch('guardian.conf.settings.TEMPLATE_403',
            '_non-exisitng-403.html'):
            self.assertRaises(TemplateDoesNotExist, dummy_view, request)
        settings.DEBUG = org_DEBUG

    @mock.patch('guardian.conf.settings.RENDER_403', False)
    @mock.patch('guardian.conf.settings.RAISE_403', True)
    def test_RAISE_403_setting_is_true(self):
        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')

        self.assertRaises(PermissionDenied, dummy_view, request)

    def test_anonymous_user_wrong_app(self):

        request = self._get_request(self.anon)

        @permission_required_or_403('not_installed_app.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        self.assertEqual(dummy_view(request).status_code, 403)

    def test_anonymous_user_wrong_codename(self):

        request = self._get_request()

        @permission_required_or_403('auth.wrong_codename')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        self.assertEqual(dummy_view(request).status_code, 403)

    def test_anonymous_user(self):

        request = self._get_request()

        @permission_required_or_403('auth.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        self.assertEqual(dummy_view(request).status_code, 403)

    def test_wrong_lookup_variables_number(self):

        request = self._get_request()

        try:
            @permission_required_or_403('auth.change_user', (User, 'username'))
            def dummy_view(request, username):
                pass
            dummy_view(request, username='jack')
        except GuardianError:
            pass
        else:
            self.fail("If lookup variables are passed they must be tuple of: "
                "(ModelClass/app_label.ModelClass/queryset, "
                "<pair of lookup_string and view_arg>)\n"
                "Otherwise GuardianError should be raised")

    def test_wrong_lookup_variables(self):

        request = self._get_request()

        args = (
            (2010, 'username', 'username'),
            ('User', 'username', 'username'),
            (User, 'username', 'no_arg'),
        )
        for tup in args:
            try:
                @permission_required_or_403('auth.change_user', tup)
                def show_user(request, username):
                    user = get_object_or_404(User, username=username)
                    return HttpResponse("It's %s here!" % user.username)
                show_user(request, 'jack')
            except GuardianError:
                pass
            else:
                self.fail("Wrong arguments given but GuardianError not raised")

    def test_user_has_no_access(self):

        request = self._get_request()

        @permission_required_or_403('auth.change_user')
        def dummy_view(request):
            return HttpResponse('dummy_view')
        self.assertEqual(dummy_view(request).status_code, 403)

    def test_user_has_access(self):

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')
        assign_perm(perm, self.user, obj=joe)

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            user_model_path, 'username', 'username'))
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'dummy_view')

    def test_user_has_access_on_model_with_metaclass(self):
        """
        Test to the fix issues of comparaison made via type()
        in the decorator. In the case of a `Model` implementing
        a custom metaclass, the decorator fail because type
        doesn't return `ModelBase`
        """
        perm = get_user_permission_full_codename('change')

        class TestMeta(ModelBase):
            pass

        class ProxyUser(User):
            class Meta:
                proxy = True
                app_label = User._meta.app_label
            __metaclass__ = TestMeta

        joe, created = ProxyUser.objects.get_or_create(username='joe')
        assign_perm(perm, self.user, obj=joe)

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            ProxyUser, 'username', 'username'))
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'dummy_view')

    def test_user_has_obj_access_even_if_we_also_check_for_global(self):

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')
        assign_perm(perm, self.user, obj=joe)

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            user_model_path, 'username', 'username'), accept_global_perms=True)
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'dummy_view')

    def test_user_has_no_obj_perm_access(self):

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            user_model_path, 'username', 'username'))
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 403)

    def test_user_has_global_perm_access_but_flag_not_set(self):

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')
        assign_perm(perm, self.user)

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            user_model_path, 'username', 'username'))
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 403)

    def test_user_has_global_perm_access(self):

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')
        assign_perm(perm, self.user)

        request = self._get_request(self.user)

        @permission_required_or_403(perm, (
            user_model_path, 'username', 'username'), accept_global_perms=True)
        def dummy_view(request, username):
            return HttpResponse('dummy_view')
        response = dummy_view(request, username='joe')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'dummy_view')

    def test_model_lookup(self):

        request = self._get_request(self.user)

        perm = get_user_permission_full_codename('change')
        joe, created = User.objects.get_or_create(username='joe')
        assign_perm(perm, self.user, obj=joe)

        models = (
            user_model_path,
            User,
            User.objects.filter(is_active=True),
        )
        for model in models:
            @permission_required_or_403(perm, (model, 'username', 'username'))
            def dummy_view(request, username):
                get_object_or_404(User, username=username)
                return HttpResponse('hello')
            response = dummy_view(request, username=joe.username)
            self.assertEqual(response.content, b'hello')

    def test_redirection_raises_wrong_app_error(self):
        from guardian.testapp.models import Project
        request = self._get_request(self.user)

        User.objects.create(username='foo')
        Project.objects.create(name='foobar')

        @permission_required('auth.change_group',
            (Project, 'name', 'group_name'),
            login_url='/foobar/')
        def dummy_view(request, project_name):
            pass
        # 'auth.change_group' is wrong permission codename (should be one
        # related with User
        self.assertRaises(WrongAppError, dummy_view, request, group_name='foobar')

    def test_redirection(self):
        from guardian.testapp.models import Project

        request = self._get_request(self.user)

        User.objects.create(username='foo')
        Project.objects.create(name='foobar')

        @permission_required('testapp.change_project',
            (Project, 'name', 'project_name'),
            login_url='/foobar/')
        def dummy_view(request, project_name):
            pass
        response = dummy_view(request, project_name='foobar')
        self.assertTrue(isinstance(response, HttpResponseRedirect))
        self.assertTrue(response._headers['location'][1].startswith(
            '/foobar/'))


########NEW FILE########
__FILENAME__ = direct_rel_test
from __future__ import unicode_literals
from guardian.testapp.models import Mixed
from guardian.testapp.models import Project
from guardian.testapp.models import ProjectGroupObjectPermission
from guardian.testapp.models import ProjectUserObjectPermission
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from guardian.compat import get_user_model
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_group
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_users_with_perms
from guardian.shortcuts import remove_perm
from guardian.testapp.tests.conf import skipUnlessTestApp


User = get_user_model()


@skipUnlessTestApp
class TestDirectUserPermissions(TestCase):

    def setUp(self):
        self.joe = User.objects.create_user('joe', 'joe@example.com', 'foobar')
        self.project = Project.objects.create(name='Foobar')

    def get_perm(self, codename):
        filters = {'content_type__app_label': 'testapp', 'codename': codename}
        return Permission.objects.get(**filters)

    def test_after_perm_is_created_without_shortcut(self):
        perm = self.get_perm('add_project')
        # we should not use assign here - if generic user obj perms model is
        # used then everything could go fine if using assign shortcut and we
        # would not be able to see any problem
        ProjectUserObjectPermission.objects.create(
            user=self.joe,
            permission=perm,
            content_object=self.project,
        )
        self.assertTrue(self.joe.has_perm('add_project', self.project))

    def test_assign_perm(self):
        assign_perm('add_project', self.joe, self.project)
        filters = {
            'content_object': self.project,
            'permission__codename': 'add_project',
            'user': self.joe,
        }
        result = ProjectUserObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 1)

    def test_remove_perm(self):
        assign_perm('add_project', self.joe, self.project)
        filters = {
            'content_object': self.project,
            'permission__codename': 'add_project',
            'user': self.joe,
        }
        result = ProjectUserObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 1)

        remove_perm('add_project', self.joe, self.project)
        result = ProjectUserObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 0)

    def test_get_users_with_perms(self):
        User.objects.create_user('john', 'john@foobar.com', 'john')
        jane = User.objects.create_user('jane', 'jane@foobar.com', 'jane')
        assign_perm('add_project', self.joe, self.project)
        assign_perm('change_project', self.joe, self.project)
        assign_perm('change_project', jane, self.project)
        self.assertEqual(get_users_with_perms(self.project, attach_perms=True),
            {
                self.joe: ['add_project', 'change_project'],
                jane: ['change_project'],
            })

    def test_get_users_with_perms_plus_groups(self):
        User.objects.create_user('john', 'john@foobar.com', 'john')
        jane = User.objects.create_user('jane', 'jane@foobar.com', 'jane')
        group = Group.objects.create(name='devs')
        self.joe.groups.add(group)
        assign_perm('add_project', self.joe, self.project)
        assign_perm('change_project', group, self.project)
        assign_perm('change_project', jane, self.project)
        self.assertEqual(get_users_with_perms(self.project, attach_perms=True),
            {
                self.joe: ['add_project', 'change_project'],
                jane: ['change_project'],
            })

    def test_get_objects_for_user(self):
        foo = Project.objects.create(name='foo')
        bar = Project.objects.create(name='bar')
        assign_perm('add_project', self.joe, foo)
        assign_perm('add_project', self.joe, bar)
        assign_perm('change_project', self.joe, bar)

        result = get_objects_for_user(self.joe, 'testapp.add_project')
        self.assertEqual(sorted(p.pk for p in result), sorted([foo.pk, bar.pk]))


@skipUnlessTestApp
class TestDirectGroupPermissions(TestCase):

    def setUp(self):
        self.joe = User.objects.create_user('joe', 'joe@example.com', 'foobar')
        self.group = Group.objects.create(name='admins')
        self.joe.groups.add(self.group)
        self.project = Project.objects.create(name='Foobar')

    def get_perm(self, codename):
        filters = {'content_type__app_label': 'testapp', 'codename': codename}
        return Permission.objects.get(**filters)

    def test_after_perm_is_created_without_shortcut(self):
        perm = self.get_perm('add_project')
        # we should not use assign here - if generic user obj perms model is
        # used then everything could go fine if using assign shortcut and we
        # would not be able to see any problem
        ProjectGroupObjectPermission.objects.create(
            group=self.group,
            permission=perm,
            content_object=self.project,
        )
        self.assertTrue(self.joe.has_perm('add_project', self.project))

    def test_assign_perm(self):
        assign_perm('add_project', self.group, self.project)
        filters = {
            'content_object': self.project,
            'permission__codename': 'add_project',
            'group': self.group,
        }
        result = ProjectGroupObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 1)

    def test_remove_perm(self):
        assign_perm('add_project', self.group, self.project)
        filters = {
            'content_object': self.project,
            'permission__codename': 'add_project',
            'group': self.group,
        }
        result = ProjectGroupObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 1)

        remove_perm('add_project', self.group, self.project)
        result = ProjectGroupObjectPermission.objects.filter(**filters).count()
        self.assertEqual(result, 0)

    def test_get_groups_with_perms(self):
        Group.objects.create(name='managers')
        devs = Group.objects.create(name='devs')
        assign_perm('add_project', self.group, self.project)
        assign_perm('change_project', self.group, self.project)
        assign_perm('change_project', devs, self.project)
        self.assertEqual(get_groups_with_perms(self.project, attach_perms=True),
            {
                self.group: ['add_project', 'change_project'],
                devs: ['change_project'],
            })

    def test_get_objects_for_group(self):
        foo = Project.objects.create(name='foo')
        bar = Project.objects.create(name='bar')
        assign_perm('add_project', self.group, foo)
        assign_perm('add_project', self.group, bar)
        assign_perm('change_project', self.group, bar)

        result = get_objects_for_group(self.group, 'testapp.add_project')
        self.assertEqual(sorted(p.pk for p in result), sorted([foo.pk, bar.pk]))


@skipUnlessTestApp
class TestMixedDirectAndGenericObjectPermission(TestCase):

    def setUp(self):
        self.joe = User.objects.create_user('joe', 'joe@example.com', 'foobar')
        self.group = Group.objects.create(name='admins')
        self.joe.groups.add(self.group)
        self.mixed = Mixed.objects.create(name='Foobar')

    def test_get_users_with_perms_plus_groups(self):
        User.objects.create_user('john', 'john@foobar.com', 'john')
        jane = User.objects.create_user('jane', 'jane@foobar.com', 'jane')
        group = Group.objects.create(name='devs')
        self.joe.groups.add(group)
        assign_perm('add_mixed', self.joe, self.mixed)
        assign_perm('change_mixed', group, self.mixed)
        assign_perm('change_mixed', jane, self.mixed)
        self.assertEqual(get_users_with_perms(self.mixed, attach_perms=True),
            {
                self.joe: ['add_mixed', 'change_mixed'],
                jane: ['change_mixed'],
            })


########NEW FILE########
__FILENAME__ = forms_test
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from guardian.compat import get_user_model
from guardian.forms import BaseObjectPermissionsForm

class BaseObjectPermissionsFormTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'joe', 'joe@example.com', 'joe')
        self.obj = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')

    def test_not_implemented(self):

        class MyUserObjectPermissionsForm(BaseObjectPermissionsForm):

            def __init__(formself, user, *args, **kwargs):
                self.user = user
                super(MyUserObjectPermissionsForm, formself).__init__(*args,
                    **kwargs)

        form = MyUserObjectPermissionsForm(self.user, self.obj, {})
        self.assertRaises(NotImplementedError, form.save_obj_perms)

        field_name = form.get_obj_perms_field_name()
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data[field_name]), 0)


########NEW FILE########
__FILENAME__ = management_test
from __future__ import absolute_import
from __future__ import unicode_literals

from guardian.compat import get_user_model
from guardian.compat import mock
from guardian.compat import unittest
from guardian.management import create_anonymous_user
import django


mocked_get_init_anon = mock.Mock()


class TestGetAnonymousUser(unittest.TestCase):

    @unittest.skipUnless(django.VERSION >= (1, 5), "Django >= 1.5 only")
    @mock.patch('guardian.management.guardian_settings')
    def test_uses_custom_function(self, guardian_settings):
        path = 'guardian.testapp.tests.management_test.mocked_get_init_anon'
        guardian_settings.GET_INIT_ANONYMOUS_USER = path
        guardian_settings.ANONYMOUS_USER_ID = 219
        User = get_user_model()

        anon = mocked_get_init_anon.return_value = mock.Mock()

        create_anonymous_user('sender')

        mocked_get_init_anon.assert_called_once_with(User)

        self.assertEqual(anon.pk, 219)
        anon.save.assert_called_once_with()

########NEW FILE########
__FILENAME__ = managers_test
from __future__ import unicode_literals
from django.test import TestCase
from guardian.compat import mock
from guardian.managers import UserObjectPermissionManager
from guardian.managers import GroupObjectPermissionManager


class TestManagers(TestCase):

    def test_user_manager_assign(self):
        manager = UserObjectPermissionManager()
        manager.assign_perm = mock.Mock()
        manager.assign('perm', 'user', 'object')
        manager.assign_perm.assert_called_once_with('perm', 'user', 'object')

    def test_group_manager_assign(self):
        manager = GroupObjectPermissionManager()
        manager.assign_perm = mock.Mock()
        manager.assign('perm', 'group', 'object')
        manager.assign_perm.assert_called_once_with('perm', 'group', 'object')


########NEW FILE########
__FILENAME__ = mixins_test
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.views.generic import View

from guardian.compat import get_user_model
from guardian.compat import mock
from guardian.mixins import LoginRequiredMixin
from guardian.mixins import PermissionRequiredMixin

class DatabaseRemovedError(Exception):
    pass


class RemoveDatabaseView(View):
    def get(self, request, *args, **kwargs):
        raise DatabaseRemovedError("You've just allowed db to be removed!")

class TestView(PermissionRequiredMixin, RemoveDatabaseView):
    permission_required = 'contenttypes.change_contenttype'
    object = None # should be set at each tests explicitly

class NoObjectView(PermissionRequiredMixin, RemoveDatabaseView):
    permission_required = 'contenttypes.change_contenttype'

class TestViewMixins(TestCase):

    def setUp(self):
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            'joe', 'joe@doe.com', 'doe')
        self.client.login(username='joe', password='doe')

    def test_permission_is_checked_before_view_is_computed(self):
        """
        This test would fail if permission is checked **after** view is
        actually resolved.
        """
        request = self.factory.get('/')
        request.user = self.user
        # View.object is set
        view = TestView.as_view(object=self.ctype)
        response = view(request)
        self.assertEqual(response.status_code, 302)

        # View.get_object returns object
        TestView.get_object = lambda instance: self.ctype
        view = TestView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        del TestView.get_object

    def test_permission_is_checked_before_view_is_computed_perm_denied_raised(self):
        """
        This test would fail if permission is checked **after** view is
        actually resolved.
        """
        request = self.factory.get('/')
        request.user = self.user
        view = TestView.as_view(raise_exception=True, object=self.ctype)
        with self.assertRaises(PermissionDenied):
            view(request)

    def test_permission_required_view_configured_wrongly(self):
        """
        This test would fail if permission is checked **after** view is
        actually resolved.
        """
        request = self.factory.get('/')
        request.user = self.user
        request.user.add_obj_perm('change_contenttype', self.ctype)
        view = TestView.as_view(permission_required=None, object=self.ctype)
        with self.assertRaises(ImproperlyConfigured):
            view(request)

    def test_permission_required(self):
        """
        This test would fail if permission is checked **after** view is
        actually resolved.
        """
        request = self.factory.get('/')
        request.user = self.user
        request.user.add_obj_perm('change_contenttype', self.ctype)
        view = TestView.as_view(object=self.ctype)
        with self.assertRaises(DatabaseRemovedError):
            view(request)

    def test_permission_required_no_object(self):
        """
        This test would fail if permission is checked on a view's
        object when it has none
        """

        request = self.factory.get('/')
        request.user = self.user
        request.user.add_obj_perm('change_contenttype', self.ctype)
        view = NoObjectView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 302)

    def test_permission_required_as_list(self):
        """
        This test would fail if permission is checked **after** view is
        actually resolved.
        """

        global TestView
        class SecretView(TestView):
            on_permission_check_fail = mock.Mock()

        request = self.factory.get('/')
        request.user = self.user
        request.user.add_obj_perm('change_contenttype', self.ctype)
        SecretView.permission_required = ['contenttypes.change_contenttype',
            'contenttypes.add_contenttype']
        view = SecretView.as_view(object=self.ctype)
        response = view(request)
        self.assertEqual(response.status_code, 302)
        SecretView.on_permission_check_fail.assert_called_once_with(request,
            response, obj=self.ctype)

        request.user.add_obj_perm('add_contenttype', self.ctype)
        with self.assertRaises(DatabaseRemovedError):
            view(request)

    def test_login_required_mixin(self):

        class SecretView(LoginRequiredMixin, View):
            redirect_field_name = 'foobar'
            login_url = '/let-me-in/'

            def get(self, request):
                return HttpResponse('secret-view')

        request = self.factory.get('/some-secret-page/')
        request.user = AnonymousUser()

        view = SecretView.as_view()

        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
            '/let-me-in/?foobar=/some-secret-page/')

        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'secret-view')


########NEW FILE########
__FILENAME__ = orphans_test
from __future__ import unicode_literals

# Try the new app settings (Django 1.7) and fall back to the old system
try:
    from django.apps import apps as django_apps
    auth_app = django_apps.get_app_config("auth")
except ImportError:
    from django.contrib.auth import models as auth_app
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase

from guardian.compat import get_user_model, create_permissions
from guardian.utils import clean_orphan_obj_perms
from guardian.shortcuts import assign_perm
from guardian.models import Group
from guardian.testapp.tests.conf import skipUnlessTestApp


User = get_user_model()
user_module_name = User._meta.module_name

@skipUnlessTestApp
class OrphanedObjectPermissionsTest(TestCase):

    def setUp(self):
        # Create objects for which we would assing obj perms
        self.target_user1 = User.objects.create(username='user1')
        self.target_group1 = Group.objects.create(name='group1')
        self.target_obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='fake-for-guardian-tests')
        self.target_obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='fake-for-guardian-tests')
        # Required if MySQL backend is used :/
        create_permissions(auth_app, [], 1)


        self.user = User.objects.create(username='user')
        self.group = Group.objects.create(name='group')

    def test_clean_perms(self):

        # assign obj perms
        target_perms = {
            self.target_user1: ["change_%s" % user_module_name],
            self.target_group1: ["delete_group"],
            self.target_obj1: ["change_contenttype", "delete_contenttype"],
            self.target_obj2: ["change_contenttype"],
        }
        obj_perms_count = sum([len(val) for key, val in target_perms.items()])
        for target, perms in target_perms.items():
            target.__old_pk = target.pk # Store pkeys
            for perm in perms:
                assign_perm(perm, self.user, target)

        # Remove targets
        for target, perms in target_perms.items():
            target.delete()

        # Clean orphans
        removed = clean_orphan_obj_perms()
        self.assertEqual(removed, obj_perms_count)

        # Recreate targets and check if user has no permissions
        for target, perms in target_perms.items():
            target.pk = target.__old_pk
            target.save()
            for perm in perms:
                self.assertFalse(self.user.has_perm(perm, target))

    def test_clean_perms_command(self):
        """
        Same test as the one above but rather function directly, we call
        management command instead.
        """

        # assign obj perms
        target_perms = {
            self.target_user1: ["change_%s" % user_module_name],
            self.target_group1: ["delete_group"],
            self.target_obj1: ["change_contenttype", "delete_contenttype"],
            self.target_obj2: ["change_contenttype"],
        }
        for target, perms in target_perms.items():
            target.__old_pk = target.pk # Store pkeys
            for perm in perms:
                assign_perm(perm, self.user, target)

        # Remove targets
        for target, perms in target_perms.items():
            target.delete()

        # Clean orphans
        call_command("clean_orphan_obj_perms", verbosity=0)

        # Recreate targets and check if user has no permissions
        for target, perms in target_perms.items():
            target.pk = target.__old_pk
            target.save()
            for perm in perms:
                self.assertFalse(self.user.has_perm(perm, target))


########NEW FILE########
__FILENAME__ = other_test
from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

import guardian
from guardian.backends import ObjectPermissionBackend
from guardian.compat import get_user_model
from guardian.compat import get_user_model_path
from guardian.compat import get_user_permission_codename
from guardian.compat import basestring
from guardian.compat import unicode
from guardian.exceptions import GuardianError
from guardian.exceptions import NotUserNorGroup
from guardian.exceptions import ObjectNotPersisted
from guardian.exceptions import WrongAppError
from guardian.models import GroupObjectPermission
from guardian.models import UserObjectPermission
from guardian.testapp.tests.conf import TestDataMixin

User = get_user_model()
user_model_path = get_user_model_path()


class UserPermissionTests(TestDataMixin, TestCase):

    def setUp(self):
        super(UserPermissionTests, self).setUp()
        self.user = User.objects.get(username='jack')
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        self.obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        self.obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')

    def test_assignement(self):
        self.assertFalse(self.user.has_perm('change_contenttype', self.ctype))

        UserObjectPermission.objects.assign_perm('change_contenttype', self.user,
            self.ctype)
        self.assertTrue(self.user.has_perm('change_contenttype', self.ctype))
        self.assertTrue(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))

    def test_assignement_and_remove(self):
        UserObjectPermission.objects.assign_perm('change_contenttype', self.user,
            self.ctype)
        self.assertTrue(self.user.has_perm('change_contenttype', self.ctype))

        UserObjectPermission.objects.remove_perm('change_contenttype',
            self.user, self.ctype)
        self.assertFalse(self.user.has_perm('change_contenttype', self.ctype))

    def test_ctypes(self):
        UserObjectPermission.objects.assign_perm('change_contenttype', self.user, self.obj1)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj1))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj2))

        UserObjectPermission.objects.remove_perm('change_contenttype', self.user, self.obj1)
        UserObjectPermission.objects.assign_perm('change_contenttype', self.user, self.obj2)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj2))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj1))

        UserObjectPermission.objects.assign_perm('change_contenttype', self.user, self.obj1)
        UserObjectPermission.objects.assign_perm('change_contenttype', self.user, self.obj2)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj2))
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj1))

        UserObjectPermission.objects.remove_perm('change_contenttype', self.user, self.obj1)
        UserObjectPermission.objects.remove_perm('change_contenttype', self.user, self.obj2)
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj2))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj1))

    def test_assign_perm_validation(self):
        self.assertRaises(Permission.DoesNotExist,
            UserObjectPermission.objects.assign_perm, 'change_group', self.user,
            self.user)

        group = Group.objects.create(name='test_group_assign_perm_validation')
        ctype = ContentType.objects.get_for_model(group)
        codename = codename=get_user_permission_codename('change')
        perm = Permission.objects.get(codename=codename)

        create_info = dict(
            permission = perm,
            user = self.user,
            content_type = ctype,
            object_pk = group.pk
        )
        self.assertRaises(ValidationError, UserObjectPermission.objects.create,
            **create_info)

    def test_unicode(self):
        codename = get_user_permission_codename('change')
        obj_perm = UserObjectPermission.objects.assign_perm(codename,
            self.user, self.user)
        self.assertTrue(isinstance(obj_perm.__unicode__(), unicode))

    def test_errors(self):
        not_saved_user = User(username='not_saved_user')
        codename = get_user_permission_codename('change')
        self.assertRaises(ObjectNotPersisted,
            UserObjectPermission.objects.assign_perm,
            codename, self.user, not_saved_user)
        self.assertRaises(ObjectNotPersisted,
            UserObjectPermission.objects.remove_perm,
                codename, self.user, not_saved_user)


class GroupPermissionTests(TestDataMixin, TestCase):

    def setUp(self):
        super(GroupPermissionTests, self).setUp()
        self.user = User.objects.get(username='jack')
        self.group, created = Group.objects.get_or_create(name='jackGroup')
        self.user.groups.add(self.group)
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        self.obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        self.obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')

    def test_assignement(self):
        self.assertFalse(self.user.has_perm('change_contenttype', self.ctype))
        self.assertFalse(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))

        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.ctype)
        self.assertTrue(self.user.has_perm('change_contenttype', self.ctype))
        self.assertTrue(self.user.has_perm('contenttypes.change_contenttype',
            self.ctype))

    def test_assignement_and_remove(self):
        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.ctype)
        self.assertTrue(self.user.has_perm('change_contenttype', self.ctype))

        GroupObjectPermission.objects.remove_perm('change_contenttype',
            self.group, self.ctype)
        self.assertFalse(self.user.has_perm('change_contenttype', self.ctype))

    def test_ctypes(self):
        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.obj1)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj1))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj2))

        GroupObjectPermission.objects.remove_perm('change_contenttype',
            self.group, self.obj1)
        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.obj2)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj2))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj1))

        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.obj1)
        GroupObjectPermission.objects.assign_perm('change_contenttype', self.group,
            self.obj2)
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj2))
        self.assertTrue(self.user.has_perm('change_contenttype', self.obj1))

        GroupObjectPermission.objects.remove_perm('change_contenttype',
            self.group, self.obj1)
        GroupObjectPermission.objects.remove_perm('change_contenttype',
            self.group, self.obj2)
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj2))
        self.assertFalse(self.user.has_perm('change_contenttype', self.obj1))

    def test_assign_perm_validation(self):
        self.assertRaises(Permission.DoesNotExist,
            GroupObjectPermission.objects.assign_perm, 'change_user', self.group,
            self.group)

        user = User.objects.create(username='testuser')
        ctype = ContentType.objects.get_for_model(user)
        perm = Permission.objects.get(codename='change_group')

        create_info = dict(
            permission = perm,
            group = self.group,
            content_type = ctype,
            object_pk = user.pk
        )
        self.assertRaises(ValidationError, GroupObjectPermission.objects.create,
            **create_info)

    def test_unicode(self):
        obj_perm = GroupObjectPermission.objects.assign_perm("change_group",
            self.group, self.group)
        self.assertTrue(isinstance(obj_perm.__unicode__(), unicode))

    def test_errors(self):
        not_saved_group = Group(name='not_saved_group')
        self.assertRaises(ObjectNotPersisted,
            GroupObjectPermission.objects.assign_perm,
            "change_group", self.group, not_saved_group)
        self.assertRaises(ObjectNotPersisted,
            GroupObjectPermission.objects.remove_perm,
            "change_group", self.group, not_saved_group)


class ObjectPermissionBackendTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='jack')
        self.backend = ObjectPermissionBackend()

    def test_attrs(self):
        self.assertTrue(self.backend.supports_anonymous_user)
        self.assertTrue(self.backend.supports_object_permissions)
        self.assertTrue(self.backend.supports_inactive_user)

    def test_authenticate(self):
        self.assertEqual(self.backend.authenticate(
            self.user.username, self.user.password), None)

    def test_has_perm_noobj(self):
        result = self.backend.has_perm(self.user, "change_contenttype")
        self.assertFalse(result)

    def test_has_perm_notauthed(self):
        user = AnonymousUser()
        self.assertFalse(self.backend.has_perm(user, "change_user", self.user))

    def test_has_perm_wrong_app(self):
        self.assertRaises(WrongAppError, self.backend.has_perm,
            self.user, "no_app.change_user", self.user)

    def test_obj_is_not_model(self):
        for obj in (Group, 666, "String", [2, 1, 5, 7], {}):
            self.assertFalse(self.backend.has_perm(self.user,
                "any perm", obj))

    def test_not_active_user(self):
        user = User.objects.create(username='non active user')
        ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        perm = 'change_contenttype'
        UserObjectPermission.objects.assign_perm(perm, user, ctype)
        self.assertTrue(self.backend.has_perm(user, perm, ctype))
        user.is_active = False
        user.save()
        self.assertFalse(self.backend.has_perm(user, perm, ctype))


class GuardianBaseTests(TestCase):

    def has_attrs(self):
        self.assertTrue(hasattr(guardian, '__version__'))

    def test_version(self):
        for x in guardian.VERSION:
            self.assertTrue(isinstance(x, (int, basestring)))

    def test_get_version(self):
        self.assertTrue(isinstance(guardian.get_version(), basestring))


class TestExceptions(TestCase):

    def _test_error_class(self, exc_cls):
        self.assertTrue(isinstance(exc_cls, GuardianError))

    def test_error_classes(self):
        self.assertTrue(isinstance(GuardianError(), Exception))
        guardian_errors = [NotUserNorGroup]
        for err in guardian_errors:
            self._test_error_class(err())


########NEW FILE########
__FILENAME__ = shortcuts_test
from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet
from django.test import TestCase

from guardian.shortcuts import get_perms_for_model
from guardian.core import ObjectPermissionChecker
from guardian.compat import get_user_model
from guardian.compat import get_user_permission_full_codename
from guardian.shortcuts import assign
from guardian.shortcuts import assign_perm
from guardian.shortcuts import remove_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import get_users_with_perms
from guardian.shortcuts import get_groups_with_perms
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_objects_for_group
from guardian.exceptions import MixedContentTypeError
from guardian.exceptions import NotUserNorGroup
from guardian.exceptions import WrongAppError
from guardian.testapp.tests.core_test import ObjectPermissionTestCase
from guardian.models import Group, Permission

import warnings


User = get_user_model()
user_app_label = User._meta.app_label
user_module_name = User._meta.module_name

class ShortcutsTests(ObjectPermissionTestCase):

    def test_get_perms_for_model(self):
        self.assertEqual(get_perms_for_model(self.user).count(), 3)
        self.assertTrue(list(get_perms_for_model(self.user)) ==
            list(get_perms_for_model(User)))
        self.assertEqual(get_perms_for_model(Permission).count(), 3)

        model_str = 'contenttypes.ContentType'
        self.assertEqual(
            sorted(get_perms_for_model(model_str).values_list()),
            sorted(get_perms_for_model(ContentType).values_list()))
        obj = ContentType()
        self.assertEqual(
            sorted(get_perms_for_model(model_str).values_list()),
            sorted(get_perms_for_model(obj).values_list()))

class AssignPermTest(ObjectPermissionTestCase):
    """
    Tests permission assigning for user/group and object.
    """
    def test_not_model(self):
        self.assertRaises(NotUserNorGroup, assign_perm,
            perm="change_object",
            user_or_group="Not a Model",
            obj=self.ctype)

    def test_global_wrong_perm(self):
        self.assertRaises(ValueError, assign_perm,
            perm="change_site", # for global permissions must provide app_label
            user_or_group=self.user)

    def test_user_assign_perm(self):
        assign_perm("change_contenttype", self.user, self.ctype)
        assign_perm("change_contenttype", self.group, self.ctype)
        self.assertTrue(self.user.has_perm("change_contenttype", self.ctype))

    def test_group_assign_perm(self):
        assign_perm("change_contenttype", self.group, self.ctype)
        assign_perm("delete_contenttype", self.group, self.ctype)

        check = ObjectPermissionChecker(self.group)
        self.assertTrue(check.has_perm("change_contenttype", self.ctype))
        self.assertTrue(check.has_perm("delete_contenttype", self.ctype))

    def test_user_assign_perm_global(self):
        perm = assign_perm("contenttypes.change_contenttype", self.user)
        self.assertTrue(self.user.has_perm("contenttypes.change_contenttype"))
        self.assertTrue(isinstance(perm, Permission))

    def test_group_assign_perm_global(self):
        perm = assign_perm("contenttypes.change_contenttype", self.group)

        self.assertTrue(self.user.has_perm("contenttypes.change_contenttype"))
        self.assertTrue(isinstance(perm, Permission))

    def test_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            assign("contenttypes.change_contenttype", self.group)
            self.assertEqual(len(warns), 1)
            self.assertTrue(isinstance(warns[0].message, DeprecationWarning))


class RemovePermTest(ObjectPermissionTestCase):
    """
    Tests object permissions removal.
    """
    def test_not_model(self):
        self.assertRaises(NotUserNorGroup, remove_perm,
            perm="change_object",
            user_or_group="Not a Model",
            obj=self.ctype)

    def test_global_wrong_perm(self):
        self.assertRaises(ValueError, remove_perm,
            perm="change_site", # for global permissions must provide app_label
            user_or_group=self.user)

    def test_user_remove_perm(self):
        # assign perm first
        assign_perm("change_contenttype", self.user, self.ctype)
        remove_perm("change_contenttype", self.user, self.ctype)
        self.assertFalse(self.user.has_perm("change_contenttype", self.ctype))

    def test_group_remove_perm(self):
        # assign perm first
        assign_perm("change_contenttype", self.group, self.ctype)
        remove_perm("change_contenttype", self.group, self.ctype)

        check = ObjectPermissionChecker(self.group)
        self.assertFalse(check.has_perm("change_contenttype", self.ctype))

    def test_user_remove_perm_global(self):
        # assign perm first
        perm = "contenttypes.change_contenttype"
        assign_perm(perm, self.user)
        remove_perm(perm, self.user)
        self.assertFalse(self.user.has_perm(perm))

    def test_group_remove_perm_global(self):
        # assign perm first
        perm = "contenttypes.change_contenttype"
        assign_perm(perm, self.group)
        remove_perm(perm, self.group)
        app_label, codename = perm.split('.')
        perm_obj = Permission.objects.get(codename=codename,
            content_type__app_label=app_label)
        self.assertFalse(perm_obj in self.group.permissions.all())


class GetPermsTest(ObjectPermissionTestCase):
    """
    Tests get_perms function (already done at core tests but left here as a
    placeholder).
    """
    def test_not_model(self):
        self.assertRaises(NotUserNorGroup, get_perms,
            user_or_group=None,
            obj=self.ctype)

    def test_user(self):
        perms_to_assign = ("change_contenttype",)

        for perm in perms_to_assign:
            assign_perm("change_contenttype", self.user, self.ctype)

        perms = get_perms(self.user, self.ctype)
        for perm in perms_to_assign:
            self.assertTrue(perm in perms)

class GetUsersWithPermsTest(TestCase):
    """
    Tests get_users_with_perms function.
    """
    def setUp(self):
        self.obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        self.obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')
        self.user1 = User.objects.create(username='user1')
        self.user2 = User.objects.create(username='user2')
        self.user3 = User.objects.create(username='user3')
        self.group1 = Group.objects.create(name='group1')
        self.group2 = Group.objects.create(name='group2')
        self.group3 = Group.objects.create(name='group3')

    def test_empty(self):
        result = get_users_with_perms(self.obj1)
        self.assertTrue(isinstance(result, QuerySet))
        self.assertEqual(list(result), [])

        result = get_users_with_perms(self.obj1, attach_perms=True)
        self.assertTrue(isinstance(result, dict))
        self.assertFalse(bool(result))

    def test_simple(self):
        assign_perm("change_contenttype", self.user1, self.obj1)
        assign_perm("delete_contenttype", self.user2, self.obj1)
        assign_perm("delete_contenttype", self.user3, self.obj2)

        result = get_users_with_perms(self.obj1)
        result_vals = result.values_list('username', flat=True)

        self.assertEqual(
            set(result_vals),
            set([user.username for user in (self.user1, self.user2)]),
        )

    def test_users_groups_perms(self):
        self.user1.groups.add(self.group1)
        self.user2.groups.add(self.group2)
        self.user3.groups.add(self.group3)
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.group2, self.obj1)
        assign_perm("delete_contenttype", self.group3, self.obj2)

        result = get_users_with_perms(self.obj1).values_list('id',
            flat=True)
        self.assertEqual(
            set(result),
            set([u.id for u in (self.user1, self.user2)])
        )

    def test_users_groups_after_removal(self):
        self.test_users_groups_perms()
        remove_perm("change_contenttype", self.group1, self.obj1)

        result = get_users_with_perms(self.obj1).values_list('id',
            flat=True)
        self.assertEqual(
            set(result),
            set([self.user2.id]),
        )

    def test_attach_perms(self):
        self.user1.groups.add(self.group1)
        self.user2.groups.add(self.group2)
        self.user3.groups.add(self.group3)
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.group2, self.obj1)
        assign_perm("delete_contenttype", self.group3, self.obj2)
        assign_perm("delete_contenttype", self.user2, self.obj1)
        assign_perm("change_contenttype", self.user3, self.obj2)

        # Check contenttype1
        result = get_users_with_perms(self.obj1, attach_perms=True)
        expected = {
            self.user1: ["change_contenttype"],
            self.user2: ["change_contenttype", "delete_contenttype"],
        }
        self.assertEqual(result.keys(), expected.keys())
        for key, perms in result.items():
            self.assertEqual(set(perms), set(expected[key]))

        # Check contenttype2
        result = get_users_with_perms(self.obj2, attach_perms=True)
        expected = {
            self.user3: ["change_contenttype", "delete_contenttype"],
        }
        self.assertEqual(result.keys(), expected.keys())
        for key, perms in result.items():
            self.assertEqual(set(perms), set(expected[key]))

    def test_attach_groups_only_has_perms(self):
        self.user1.groups.add(self.group1)
        assign_perm("change_contenttype", self.group1, self.obj1)
        result = get_users_with_perms(self.obj1, attach_perms=True)
        expected = {self.user1: ["change_contenttype"]}
        self.assertEqual(result, expected)

    def test_mixed(self):
        self.user1.groups.add(self.group1)
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.user2, self.obj1)
        assign_perm("delete_contenttype", self.user2, self.obj1)
        assign_perm("delete_contenttype", self.user2, self.obj2)
        assign_perm("change_contenttype", self.user3, self.obj2)
        assign_perm("change_%s" % user_module_name, self.user3, self.user1)

        result = get_users_with_perms(self.obj1)
        self.assertEqual(
            set(result),
            set([self.user1, self.user2]),
        )

    def test_with_superusers(self):
        admin = User.objects.create(username='admin', is_superuser=True)
        assign_perm("change_contenttype", self.user1, self.obj1)

        result = get_users_with_perms(self.obj1, with_superusers=True)
        self.assertEqual(
            set(result),
            set([self.user1, admin]),
        )

    def test_without_group_users(self):
        self.user1.groups.add(self.group1)
        self.user2.groups.add(self.group2)
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.user2, self.obj1)
        assign_perm("change_contenttype", self.group2, self.obj1)
        result = get_users_with_perms(self.obj1, with_group_users=False)
        expected = set([self.user2])
        self.assertEqual(set(result), expected)

    def test_without_group_users_but_perms_attached(self):
        self.user1.groups.add(self.group1)
        self.user2.groups.add(self.group2)
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.user2, self.obj1)
        assign_perm("change_contenttype", self.group2, self.obj1)
        result = get_users_with_perms(self.obj1, with_group_users=False,
            attach_perms=True)
        expected = {self.user2: ["change_contenttype"]}
        self.assertEqual(result, expected)

    def test_without_group_users_no_result(self):
        self.user1.groups.add(self.group1)
        assign_perm("change_contenttype", self.group1, self.obj1)
        result = get_users_with_perms(self.obj1, attach_perms=True,
                with_group_users=False)
        expected = {}
        self.assertEqual(result, expected)

    def test_without_group_users_no_result_but_with_superusers(self):
        admin = User.objects.create(username='admin', is_superuser=True)
        self.user1.groups.add(self.group1)
        assign_perm("change_contenttype", self.group1, self.obj1)
        result = get_users_with_perms(self.obj1, with_group_users=False,
            with_superusers=True)
        expected = [admin]
        self.assertEqual(set(result), set(expected))


class GetGroupsWithPerms(TestCase):
    """
    Tests get_groups_with_perms function.
    """
    def setUp(self):
        self.obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        self.obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')
        self.user1 = User.objects.create(username='user1')
        self.user2 = User.objects.create(username='user2')
        self.user3 = User.objects.create(username='user3')
        self.group1 = Group.objects.create(name='group1')
        self.group2 = Group.objects.create(name='group2')
        self.group3 = Group.objects.create(name='group3')

    def test_empty(self):
        result = get_groups_with_perms(self.obj1)
        self.assertTrue(isinstance(result, QuerySet))
        self.assertFalse(bool(result))

        result = get_groups_with_perms(self.obj1, attach_perms=True)
        self.assertTrue(isinstance(result, dict))
        self.assertFalse(bool(result))

    def test_simple(self):
        assign_perm("change_contenttype", self.group1, self.obj1)
        result = get_groups_with_perms(self.obj1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.group1)

    def test_simple_after_removal(self):
        self.test_simple()
        remove_perm("change_contenttype", self.group1, self.obj1)
        result = get_groups_with_perms(self.obj1)
        self.assertEqual(len(result), 0)

    def test_simple_attach_perms(self):
        assign_perm("change_contenttype", self.group1, self.obj1)
        result = get_groups_with_perms(self.obj1, attach_perms=True)
        expected = {self.group1: ["change_contenttype"]}
        self.assertEqual(result, expected)

    def test_simple_attach_perms_after_removal(self):
        self.test_simple_attach_perms()
        remove_perm("change_contenttype", self.group1, self.obj1)
        result = get_groups_with_perms(self.obj1, attach_perms=True)
        self.assertEqual(len(result), 0)

    def test_mixed(self):
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.group1, self.obj2)
        assign_perm("change_%s" % user_module_name, self.group1, self.user3)
        assign_perm("change_contenttype", self.group2, self.obj2)
        assign_perm("change_contenttype", self.group2, self.obj1)
        assign_perm("delete_contenttype", self.group2, self.obj1)
        assign_perm("change_%s" % user_module_name, self.group3, self.user1)

        result = get_groups_with_perms(self.obj1)
        self.assertEqual(set(result), set([self.group1, self.group2]))

    def test_mixed_attach_perms(self):
        assign_perm("change_contenttype", self.group1, self.obj1)
        assign_perm("change_contenttype", self.group1, self.obj2)
        assign_perm("change_group", self.group1, self.group3)
        assign_perm("change_contenttype", self.group2, self.obj2)
        assign_perm("change_contenttype", self.group2, self.obj1)
        assign_perm("delete_contenttype", self.group2, self.obj1)
        assign_perm("change_group", self.group3, self.group1)

        result = get_groups_with_perms(self.obj1, attach_perms=True)
        expected = {
            self.group1: ["change_contenttype"],
            self.group2: ["change_contenttype", "delete_contenttype"],
        }
        self.assertEqual(result.keys(), expected.keys())
        for key, perms in result.items():
            self.assertEqual(set(perms), set(expected[key]))


class GetObjectsForUser(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='joe')
        self.group = Group.objects.create(name='group')
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')

    def test_superuser(self):
        self.user.is_superuser = True
        ctypes = ContentType.objects.all()
        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ctypes)
        self.assertEqual(set(ctypes), set(objects))

    def test_with_superuser_true(self):
        self.user.is_superuser = True
        ctypes = ContentType.objects.all()
        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ctypes, with_superuser=True)
        self.assertEqual(set(ctypes), set(objects))

    def test_with_superuser_false(self):
        self.user.is_superuser = True
        ctypes = ContentType.objects.all()
        obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        assign_perm('change_contenttype', self.user, obj1)
        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ctypes, with_superuser=False)
        self.assertEqual(set([obj1]), set(objects))

    def test_anonymous(self):
        self.user = AnonymousUser()
        ctypes = ContentType.objects.all()
        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ctypes)

        obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        assign_perm('change_contenttype', self.user, obj1)
        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ctypes)
        self.assertEqual(set([obj1]), set(objects))

    def test_mixed_perms(self):
        codenames = [
            get_user_permission_full_codename('change'),
            'auth.change_permission',
        ]
        self.assertRaises(MixedContentTypeError, get_objects_for_user,
            self.user, codenames)

    def test_perms_with_mixed_apps(self):
        codenames = [
            get_user_permission_full_codename('change'),
            'contenttypes.change_contenttype',
        ]
        self.assertRaises(MixedContentTypeError, get_objects_for_user,
            self.user, codenames)

    def test_mixed_perms_and_klass(self):
        self.assertRaises(MixedContentTypeError, get_objects_for_user,
            self.user, ['auth.change_group'], User)

    def test_no_app_label_nor_klass(self):
        self.assertRaises(WrongAppError, get_objects_for_user, self.user,
            ['change_group'])

    def test_empty_perms_sequence(self):
        self.assertEqual(
            set(get_objects_for_user(self.user, [], Group.objects.all())),
            set()
        )

    def test_perms_single(self):
        perm = 'auth.change_group'
        assign_perm(perm, self.user, self.group)
        self.assertEqual(
            set(get_objects_for_user(self.user, perm)),
            set(get_objects_for_user(self.user, [perm])))

    def test_klass_as_model(self):
        assign_perm('contenttypes.change_contenttype', self.user, self.ctype)

        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'], ContentType)
        self.assertEqual([obj.name for obj in objects], [self.ctype.name])

    def test_klass_as_manager(self):
        assign_perm('auth.change_group', self.user, self.group)
        objects = get_objects_for_user(self.user, ['auth.change_group'],
            Group.objects)
        self.assertEqual([obj.name for obj in objects], [self.group.name])

    def test_klass_as_queryset(self):
        assign_perm('auth.change_group', self.user, self.group)
        objects = get_objects_for_user(self.user, ['auth.change_group'],
            Group.objects.all())
        self.assertEqual([obj.name for obj in objects], [self.group.name])

    def test_ensure_returns_queryset(self):
        objects = get_objects_for_user(self.user, ['auth.change_group'])
        self.assertTrue(isinstance(objects, QuerySet))

    def test_simple(self):
        group_names = ['group1', 'group2', 'group3']
        groups = [Group.objects.create(name=name) for name in group_names]
        for group in groups:
            assign_perm('change_group', self.user, group)

        objects = get_objects_for_user(self.user, ['auth.change_group'])
        self.assertEqual(len(objects), len(groups))
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(
            set(objects),
            set(groups))

    def test_multiple_perms_to_check(self):
        group_names = ['group1', 'group2', 'group3']
        groups = [Group.objects.create(name=name) for name in group_names]
        for group in groups:
            assign_perm('auth.change_group', self.user, group)
        assign_perm('auth.delete_group', self.user, groups[1])

        objects = get_objects_for_user(self.user, ['auth.change_group',
            'auth.delete_group'])
        self.assertEqual(len(objects), 1)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(
            set(objects.values_list('name', flat=True)),
            set([groups[1].name]))

    def test_multiple_perms_to_check_no_groups(self):
        group_names = ['group1', 'group2', 'group3']
        groups = [Group.objects.create(name=name) for name in group_names]
        for group in groups:
            assign_perm('auth.change_group', self.user, group)
        assign_perm('auth.delete_group', self.user, groups[1])

        objects = get_objects_for_user(self.user, ['auth.change_group',
            'auth.delete_group'], use_groups=False)
        self.assertEqual(len(objects), 1)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(
            set(objects.values_list('name', flat=True)),
            set([groups[1].name]))

    def test_any_of_multiple_perms_to_check(self):
        group_names = ['group1', 'group2', 'group3']
        groups = [Group.objects.create(name=name) for name in group_names]
        assign_perm('auth.change_group', self.user, groups[0])
        assign_perm('auth.delete_group', self.user, groups[2])

        objects = get_objects_for_user(self.user, ['auth.change_group',
            'auth.delete_group'], any_perm=True)
        self.assertEqual(len(objects), 2)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(
            set(objects.values_list('name', flat=True)),
            set([groups[0].name, groups[2].name]))

    def test_groups_perms(self):
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')
        group3 = Group.objects.create(name='group3')
        groups = [group1, group2, group3]
        for group in groups:
            self.user.groups.add(group)

        # Objects to operate on
        ctypes = list(ContentType.objects.all().order_by('id'))

        assign_perm('change_contenttype', self.user, ctypes[0])
        assign_perm('change_contenttype', self.user, ctypes[1])
        assign_perm('delete_contenttype', self.user, ctypes[1])
        assign_perm('delete_contenttype', self.user, ctypes[2])

        assign_perm('change_contenttype', groups[0], ctypes[3])
        assign_perm('change_contenttype', groups[1], ctypes[3])
        assign_perm('change_contenttype', groups[2], ctypes[4])
        assign_perm('delete_contenttype', groups[0], ctypes[0])

        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'])
        self.assertEqual(
            set(objects.values_list('id', flat=True)),
            set(ctypes[i].id for i in [0, 1, 3, 4]))

        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype',
            'contenttypes.delete_contenttype'])
        self.assertEqual(
            set(objects.values_list('id', flat=True)),
            set(ctypes[i].id for i in [0, 1]))

        objects = get_objects_for_user(self.user,
            ['contenttypes.change_contenttype'])
        self.assertEqual(
            set(objects.values_list('id', flat=True)),
            set(ctypes[i].id for i in [0, 1, 3, 4]))

class GetObjectsForGroup(TestCase):
    """
    Tests get_objects_for_group function.
    """
    def setUp(self):
        self.obj1 = ContentType.objects.create(name='ct1', model='foo',
            app_label='guardian-tests')
        self.obj2 = ContentType.objects.create(name='ct2', model='bar',
            app_label='guardian-tests')
        self.obj3 = ContentType.objects.create(name='ct3', model='baz',
            app_label='guardian-tests')
        self.user1 = User.objects.create(username='user1')
        self.user2 = User.objects.create(username='user2')
        self.user3 = User.objects.create(username='user3')
        self.group1 = Group.objects.create(name='group1')
        self.group2 = Group.objects.create(name='group2')
        self.group3 = Group.objects.create(name='group3')

    def test_mixed_perms(self):
        codenames = [
            get_user_permission_full_codename('change'),
            'auth.change_permission',
        ]
        self.assertRaises(MixedContentTypeError, get_objects_for_group,
            self.group1, codenames)

    def test_perms_with_mixed_apps(self):
        codenames = [
            get_user_permission_full_codename('change'),
            'contenttypes.contenttypes.change_contenttype',
        ]
        self.assertRaises(MixedContentTypeError, get_objects_for_group,
            self.group1, codenames)

    def test_mixed_perms_and_klass(self):
        self.assertRaises(MixedContentTypeError, get_objects_for_group,
            self.group1, ['auth.change_group'], User)

    def test_no_app_label_nor_klass(self):
        self.assertRaises(WrongAppError, get_objects_for_group, self.group1,
            ['change_contenttype'])

    def test_empty_perms_sequence(self):
        self.assertEqual(
            set(get_objects_for_group(self.group1, [], ContentType)),
            set()
        )

    def test_perms_single(self):
        perm = 'contenttypes.change_contenttype'
        assign_perm(perm, self.group1, self.obj1)
        self.assertEqual(
            set(get_objects_for_group(self.group1, perm)),
            set(get_objects_for_group(self.group1, [perm]))
        )

    def test_klass_as_model(self):
        assign_perm('contenttypes.change_contenttype', self.group1, self.obj1)

        objects = get_objects_for_group(self.group1,
            ['contenttypes.change_contenttype'], ContentType)
        self.assertEqual([obj.name for obj in objects], [self.obj1.name])

    def test_klass_as_manager(self):
        assign_perm('contenttypes.change_contenttype', self.group1, self.obj1)
        objects = get_objects_for_group(self.group1, ['change_contenttype'],
            ContentType.objects)
        self.assertEqual(list(objects), [self.obj1])

    def test_klass_as_queryset(self):
        assign_perm('contenttypes.change_contenttype', self.group1, self.obj1)
        objects = get_objects_for_group(self.group1, ['change_contenttype'],
            ContentType.objects.all())
        self.assertEqual(list(objects), [self.obj1])

    def test_ensure_returns_queryset(self):
        objects = get_objects_for_group(self.group1, ['contenttypes.change_contenttype'])
        self.assertTrue(isinstance(objects, QuerySet))

    def test_simple(self):
        assign_perm('change_contenttype', self.group1, self.obj1)
        assign_perm('change_contenttype', self.group1, self.obj2)

        objects = get_objects_for_group(self.group1, 'contenttypes.change_contenttype')
        self.assertEqual(len(objects), 2)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(
            set(objects),
            set([self.obj1, self.obj2]))

    def test_simple_after_removal(self):
        self.test_simple()
        remove_perm('change_contenttype', self.group1, self.obj1)
        objects = get_objects_for_group(self.group1, 'contenttypes.change_contenttype')
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0], self.obj2)

    def test_multiple_perms_to_check(self):
        assign_perm('change_contenttype', self.group1, self.obj1)
        assign_perm('delete_contenttype', self.group1, self.obj1)
        assign_perm('change_contenttype', self.group1, self.obj2)

        objects = get_objects_for_group(self.group1, [
            'contenttypes.change_contenttype',
            'contenttypes.delete_contenttype'])
        self.assertEqual(len(objects), 1)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual(objects[0], self.obj1)

    def test_any_of_multiple_perms_to_check(self):
        assign_perm('change_contenttype', self.group1, self.obj1)
        assign_perm('delete_contenttype', self.group1, self.obj1)
        assign_perm('add_contenttype', self.group1, self.obj2)
        assign_perm('delete_contenttype', self.group1, self.obj3)

        objects = get_objects_for_group(self.group1,
            ['contenttypes.change_contenttype',
            'contenttypes.delete_contenttype'], any_perm=True)
        self.assertTrue(isinstance(objects, QuerySet))
        self.assertEqual([obj for obj in objects.order_by('name')],
            [self.obj1, self.obj3])

    def test_results_for_different_groups_are_correct(self):
        assign_perm('change_contenttype', self.group1, self.obj1)
        assign_perm('delete_contenttype', self.group2, self.obj2)

        self.assertEqual(set(get_objects_for_group(self.group1, 'contenttypes.change_contenttype')),
            set([self.obj1]))
        self.assertEqual(set(get_objects_for_group(self.group2, 'contenttypes.change_contenttype')),
            set())
        self.assertEqual(set(get_objects_for_group(self.group2, 'contenttypes.delete_contenttype')),
            set([self.obj2]))


########NEW FILE########
__FILENAME__ = tags_test
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth.models import Group, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from guardian.compat import get_user_model
from guardian.exceptions import NotUserNorGroup
from guardian.models import UserObjectPermission, GroupObjectPermission

User = get_user_model()

def render(template, context):
    """
    Returns rendered ``template`` with ``context``, which are given as string
    and dict respectively.
    """
    t = Template(template)
    return t.render(Context(context))

class GetObjPermsTagTest(TestCase):

    def setUp(self):
        self.ctype = ContentType.objects.create(name='foo', model='bar',
            app_label='fake-for-guardian-tests')
        self.group = Group.objects.create(name='jackGroup')
        self.user = User.objects.create(username='jack')
        self.user.groups.add(self.group)

    def test_wrong_formats(self):
        wrong_formats = (
            '{% get_obj_perms user for contenttype as obj_perms %}', # no quotes
            '{% get_obj_perms user for contenttype as \'obj_perms" %}', # wrong quotes
            '{% get_obj_perms user for contenttype as \'obj_perms" %}', # wrong quotes
            '{% get_obj_perms user for contenttype as obj_perms" %}', # wrong quotes
            '{% get_obj_perms user for contenttype as obj_perms\' %}', # wrong quotes
            '{% get_obj_perms user for contenttype as %}', # no context_var
            '{% get_obj_perms for contenttype as "obj_perms" %}', # no user/group
            '{% get_obj_perms user contenttype as "obj_perms" %}', # no "for" bit
            '{% get_obj_perms user for contenttype "obj_perms" %}', # no "as" bit
            '{% get_obj_perms user for as "obj_perms" %}', # no object
        )

        context = {'user': User.get_anonymous(), 'contenttype': self.ctype}
        for wrong in wrong_formats:
            fullwrong = '{% load guardian_tags %}' + wrong
            try:
                render(fullwrong, context)
                self.fail("Used wrong get_obj_perms tag format: \n\n\t%s\n\n "
                    "but TemplateSyntaxError have not been raised" % wrong)
            except TemplateSyntaxError:
                pass

    def test_obj_none(self):
        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms user for object as "obj_perms" %}{{ perms }}',
        ))
        context = {'user': User.get_anonymous(), 'object': None}
        output = render(template, context)
        self.assertEqual(output, '')

    def test_anonymous_user(self):
        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms user for contenttype as "obj_perms" %}{{ perms }}',
        ))
        context = {'user': AnonymousUser(), 'contenttype': self.ctype}
        anon_output = render(template, context)
        context = {'user': User.get_anonymous(), 'contenttype': self.ctype}
        real_anon_user_output = render(template, context)
        self.assertEqual(anon_output, real_anon_user_output)

    def test_wrong_user_or_group(self):
        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms some_obj for contenttype as "obj_perms" %}',
        ))
        context = {'some_obj': ContentType(), 'contenttype': self.ctype}
        # This test would raise TemplateSyntaxError instead of NotUserNorGroup
        # if TEMPLATE_DEBUG is set to True during tests
        tmp = settings.TEMPLATE_DEBUG
        settings.TEMPLATE_DEBUG = False
        self.assertRaises(NotUserNorGroup, render, template, context)
        settings.TEMPLATE_DEBUG = tmp

    def test_superuser(self):
        user = User.objects.create(username='superuser', is_superuser=True)
        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms user for contenttype as "obj_perms" %}',
            '{{ obj_perms|join:" " }}',
        ))
        context = {'user': user, 'contenttype': self.ctype}
        output = render(template, context)

        for perm in ('add_contenttype', 'change_contenttype', 'delete_contenttype'):
            self.assertTrue(perm in output)

    def test_user(self):
        UserObjectPermission.objects.assign_perm("change_contenttype", self.user,
            self.ctype)
        GroupObjectPermission.objects.assign_perm("delete_contenttype", self.group,
            self.ctype)

        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms user for contenttype as "obj_perms" %}',
            '{{ obj_perms|join:" " }}',
        ))
        context = {'user': self.user, 'contenttype': self.ctype}
        output = render(template, context)

        self.assertEqual(
            set(output.split(' ')),
            set('change_contenttype delete_contenttype'.split(' ')))

    def test_group(self):
        GroupObjectPermission.objects.assign_perm("delete_contenttype", self.group,
            self.ctype)

        template = ''.join((
            '{% load guardian_tags %}',
            '{% get_obj_perms group for contenttype as "obj_perms" %}',
            '{{ obj_perms|join:" " }}',
        ))
        context = {'group': self.group, 'contenttype': self.ctype}
        output = render(template, context)

        self.assertEqual(output, 'delete_contenttype')


########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals
# handler404 and handler500 are needed for admin tests
from guardian.compat import include, patterns, handler404, handler500 # pyflakes:ignore
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)



########NEW FILE########
__FILENAME__ = utils_test
from __future__ import unicode_literals
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, AnonymousUser
from django.db import models

from guardian.compat import get_user_model
from guardian.testapp.tests.conf import skipUnlessTestApp
from guardian.testapp.tests.core_test import ObjectPermissionTestCase
from guardian.testapp.models import Project
from guardian.testapp.models import ProjectUserObjectPermission
from guardian.testapp.models import ProjectGroupObjectPermission
from guardian.models import UserObjectPermission
from guardian.models import UserObjectPermissionBase
from guardian.models import GroupObjectPermission
from guardian.utils import get_anonymous_user
from guardian.utils import get_identity
from guardian.utils import get_user_obj_perms_model
from guardian.utils import get_group_obj_perms_model
from guardian.utils import get_obj_perms_model
from guardian.exceptions import NotUserNorGroup

User = get_user_model()

class GetAnonymousUserTest(TestCase):

    def test(self):
        anon = get_anonymous_user()
        self.assertTrue(isinstance(anon, User))

class GetIdentityTest(ObjectPermissionTestCase):

    def test_user(self):
        user, group = get_identity(self.user)
        self.assertTrue(isinstance(user, User))
        self.assertEqual(group, None)

    def test_anonymous_user(self):
        anon = AnonymousUser()
        user, group = get_identity(anon)
        self.assertTrue(isinstance(user, User))
        self.assertEqual(group, None)

    def test_group(self):
        user, group = get_identity(self.group)
        self.assertTrue(isinstance(group, Group))
        self.assertEqual(user, None)

    def test_not_user_nor_group(self):
        self.assertRaises(NotUserNorGroup, get_identity, 1)
        self.assertRaises(NotUserNorGroup, get_identity, "User")
        self.assertRaises(NotUserNorGroup, get_identity, User)


@skipUnlessTestApp
class GetUserObjPermsModelTest(TestCase):

    def test_for_instance(self):
        project = Project(name='Foobar')
        self.assertEqual(get_user_obj_perms_model(project),
            ProjectUserObjectPermission)

    def test_for_class(self):
        self.assertEqual(get_user_obj_perms_model(Project),
            ProjectUserObjectPermission)

    def test_default(self):
        self.assertEqual(get_user_obj_perms_model(ContentType),
            UserObjectPermission)

    def test_user_model(self):
        # this test assumes that there were no direct obj perms model to User
        # model defined (i.e. while testing guardian app in some custom project)
        self.assertEqual(get_user_obj_perms_model(User),
            UserObjectPermission)


@skipUnlessTestApp
class GetGroupObjPermsModelTest(TestCase):

    def test_for_instance(self):
        project = Project(name='Foobar')
        self.assertEqual(get_group_obj_perms_model(project),
            ProjectGroupObjectPermission)

    def test_for_class(self):
        self.assertEqual(get_group_obj_perms_model(Project),
            ProjectGroupObjectPermission)

    def test_default(self):
        self.assertEqual(get_group_obj_perms_model(ContentType),
            GroupObjectPermission)

    def test_group_model(self):
        # this test assumes that there were no direct obj perms model to Group
        # model defined (i.e. while testing guardian app in some custom project)
        self.assertEqual(get_group_obj_perms_model(Group),
            GroupObjectPermission)

class GetObjPermsModelTest(TestCase):

    def test_image_field(self):

        class SomeModel(models.Model):
            image = models.FileField(upload_to='images/')

        obj = SomeModel()
        perm_model = get_obj_perms_model(obj, UserObjectPermissionBase,
            UserObjectPermission)
        self.assertEqual(perm_model, UserObjectPermission)

    def test_file_field(self):

        class SomeModel2(models.Model):
            file = models.FileField(upload_to='images/')

        obj = SomeModel2()
        perm_model = get_obj_perms_model(obj, UserObjectPermissionBase,
            UserObjectPermission)
        self.assertEqual(perm_model, UserObjectPermission)


########NEW FILE########
__FILENAME__ = testsettings
import os
import random
import string

DEBUG = False

ANONYMOUS_USER_ID = -1

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.messages',
    'guardian',
    'guardian.testapp',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST_NAME': ':memory:',
    },
}

ROOT_URLCONF = 'guardian.testapp.tests.urls'
SITE_ID = 1

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'tests', 'templates'),
)

SECRET_KEY = ''.join([random.choice(string.ascii_letters) for x in range(40)])

# Database specific

if os.environ.get('GUARDIAN_TEST_DB_BACKEND') == 'mysql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
    DATABASES['default']['NAME'] = 'guardian_test'
    DATABASES['default']['TEST_NAME'] = 'guardian_test'
    DATABASES['default']['USER'] = os.environ.get('USER', 'root')

if os.environ.get('GUARDIAN_TEST_DB_BACKEND') == 'postgresql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
    DATABASES['default']['NAME'] = 'guardian'
    DATABASES['default']['TEST_NAME'] = 'guardian_test'
    DATABASES['default']['USER'] = os.environ.get('USER', 'postgres')


########NEW FILE########
__FILENAME__ = utils
"""
django-guardian helper functions.

Functions defined within this module should be considered as django-guardian's
internal functionality. They are **not** guaranteed to be stable - which means
they actual input parameters/output type may change in future releases.
"""
from __future__ import unicode_literals
import os
import logging
from itertools import chain
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Model
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext, TemplateDoesNotExist
from django.utils.http import urlquote

from guardian.compat import get_user_model
from guardian.conf import settings as guardian_settings
from guardian.exceptions import NotUserNorGroup


logger = logging.getLogger(__name__)
abspath = lambda *p: os.path.abspath(os.path.join(*p))


def get_anonymous_user():
    """
    Returns ``User`` instance (not ``AnonymousUser``) depending on
    ``ANONYMOUS_USER_ID`` configuration.
    """
    return get_user_model().objects.get(id=guardian_settings.ANONYMOUS_USER_ID)


def get_identity(identity):
    """
    Returns (user_obj, None) or (None, group_obj) tuple depending on what is
    given. Also accepts AnonymousUser instance but would return ``User``
    instead - it is convenient and needed for authorization backend to support
    anonymous users.

    :param identity: either ``User`` or ``Group`` instance

    :raises ``NotUserNorGroup``: if cannot return proper identity instance

    **Examples**::

       >>> from django.contrib.auth.models import User
       >>> user = User.objects.create(username='joe')
       >>> get_identity(user)
       (<User: joe>, None)

       >>> group = Group.objects.create(name='users')
       >>> get_identity(group)
       (None, <Group: users>)

       >>> anon = AnonymousUser()
       >>> get_identity(anon)
       (<User: AnonymousUser>, None)

       >>> get_identity("not instance")
       ...
       NotUserNorGroup: User/AnonymousUser or Group instance is required (got )

    """
    if isinstance(identity, AnonymousUser):
        identity = get_anonymous_user()

    if isinstance(identity, get_user_model()):
        return identity, None
    elif isinstance(identity, Group):
        return None, identity

    raise NotUserNorGroup("User/AnonymousUser or Group instance is required "
        "(got %s)" % identity)


def get_403_or_None(request, perms, obj=None, login_url=None,
    redirect_field_name=None, return_403=False, accept_global_perms=False):
    login_url = login_url or settings.LOGIN_URL
    redirect_field_name = redirect_field_name or REDIRECT_FIELD_NAME

    # Handles both original and with object provided permission check
    # as ``obj`` defaults to None

    has_permissions = False
    # global perms check first (if accept_global_perms)
    if accept_global_perms:
        has_permissions = all(request.user.has_perm(perm) for perm in perms)
    # if still no permission granted, try obj perms
    if not has_permissions:
        has_permissions = all(request.user.has_perm(perm, obj) for perm in perms)

    if not has_permissions:
        if return_403:
            if guardian_settings.RENDER_403:
                try:
                    response = render_to_response(
                        guardian_settings.TEMPLATE_403, {},
                        RequestContext(request))
                    response.status_code = 403
                    return response
                except TemplateDoesNotExist as e:
                    if settings.DEBUG:
                        raise e
            elif guardian_settings.RAISE_403:
                raise PermissionDenied
            return HttpResponseForbidden()
        else:
            path = urlquote(request.get_full_path())
            tup = login_url, redirect_field_name, path
            return HttpResponseRedirect("%s?%s=%s" % tup)


def clean_orphan_obj_perms():
    """
    Seeks and removes all object permissions entries pointing at non-existing
    targets.

    Returns number of removed objects.
    """
    from guardian.models import UserObjectPermission
    from guardian.models import GroupObjectPermission


    deleted = 0
    # TODO: optimise
    for perm in chain(UserObjectPermission.objects.all(),
        GroupObjectPermission.objects.all()):
        if perm.content_object is None:
            logger.debug("Removing %s (pk=%d)" % (perm, perm.pk))
            perm.delete()
            deleted += 1
    logger.info("Total removed orphan object permissions instances: %d" %
        deleted)
    return deleted


# TODO: should raise error when multiple UserObjectPermission direct relations
# are defined

def get_obj_perms_model(obj, base_cls, generic_cls):
    if isinstance(obj, Model):
        obj = obj.__class__
    ctype = ContentType.objects.get_for_model(obj)
    for attr in obj._meta.get_all_related_objects():
        model = getattr(attr, 'model', None)
        if (model and issubclass(model, base_cls) and
                model is not generic_cls):
            # if model is generic one it would be returned anyway
            if not model.objects.is_generic():
                # make sure that content_object's content_type is same as
                # the one of given obj
                fk = model._meta.get_field_by_name('content_object')[0]
                if ctype == ContentType.objects.get_for_model(fk.rel.to):
                    return model
    return generic_cls


def get_user_obj_perms_model(obj):
    """
    Returns model class that connects given ``obj`` and User class.
    """
    from guardian.models import UserObjectPermissionBase
    from guardian.models import UserObjectPermission
    return get_obj_perms_model(obj, UserObjectPermissionBase, UserObjectPermission)


def get_group_obj_perms_model(obj):
    """
    Returns model class that connects given ``obj`` and Group class.
    """
    from guardian.models import GroupObjectPermissionBase
    from guardian.models import GroupObjectPermission
    return get_obj_perms_model(obj, GroupObjectPermissionBase, GroupObjectPermission)

########NEW FILE########
__FILENAME__ = tests
"""
Unit tests runner for ``django-guardian`` based on boundled example project.
Tests are independent from this example application but setuptools need
instructions how to interpret ``test`` command when we run::

    python setup.py test

"""
import os
import sys
import django

os.environ["DJANGO_SETTINGS_MODULE"] = 'guardian.testsettings'
from guardian import testsettings as settings

settings.INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sites',
    'guardian',
    'guardian.testapp',
)
settings.PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)

def run_tests(settings):
    from django.test.utils import get_runner
    from utils import show_settings

    show_settings(settings, 'tests')

    import django
    if hasattr(django, 'setup'):
        django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(interactive=False)
    failures = test_runner.run_tests(['auth', 'guardian', 'testapp'])
    return failures

def main():
    failures = run_tests(settings)
    sys.exit(failures)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = utils

def show_settings(settings, action):
    import guardian
    from django.utils.termcolors import colorize

    guardian_path = guardian.__path__[0]
    msg = "django-guardian module's path: %r" % guardian_path
    print(colorize(msg, fg='magenta'))
    db_conf = settings.DATABASES['default']
    output = []
    msg = "Starting %s for db backend: %s" % (action, db_conf['ENGINE'])
    embracer = '=' * len(msg)
    output.append(msg)
    for key in sorted(db_conf.keys()):
        if key == 'PASSWORD':
            value = '****************'
        else:
            value = db_conf[key]
        line = '    %s: "%s"' % (key, value)
        output.append(line)
    embracer = colorize('=' * len(max(output, key=lambda s: len(s))),
        fg='green', opts=['bold'])
    output = [colorize(line, fg='blue') for line in output]
    output.insert(0, embracer)
    output.append(embracer)
    print('\n'.join(output))


########NEW FILE########
