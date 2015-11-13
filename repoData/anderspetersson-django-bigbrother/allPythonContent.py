__FILENAME__ = core
import datetime
from django.utils.importlib import import_module
from django.template.defaultfilters import slugify
from django.conf import settings
from bigbrother.models import ModuleStat
from bigbrother.warnings import send_warning


def get_module_list():
    """
    Returns a list of currently enabled modules.
    """
    default_modules = (
        'bigbrother.core.UserCount',
        'bigbrother.core.NewUsersTodayCount',
        'bigbrother.core.FreeRamCount',
        'bigbrother.core.FreeDiskCount',
    )
    return getattr(settings, 'BIGBROTHER_MODULES', default_modules)

def get_graph_list():
    """
    Returns a list of the default graphs.
    """
    default_graphs = (
        'bigbrother.graphs.LastWeekGraph',
        'bigbrother.graphs.LastMonthGraph',
        'bigbrother.graphs.LastYearGraph',
    )
    return getattr(settings, 'BIGBROTHER_GRAPHS', default_graphs)

def get_module_classes(group=None):
    """
    Returns all the module classes defined in the settings
    """
    clslist = []
    for m in get_module_list():
        modulename, attr = m.rsplit('.', 1)
        try:
            module = import_module(modulename)
        except ImportError:
            continue
        cls = getattr(module, attr, None)
        if not cls:
            continue
        if group:
            if slugify(cls.group) != group:
                continue
        clslist.append(cls)
    return clslist

def get_graph_classes():
    """
    Returns all the graph classes defined in settings.
    """
    clslist = []
    for m in get_graph_list():
        modulename, attr = m.rsplit('.', 1)
        try:
            module = import_module(modulename)
        except ImportError:
            continue
        cls = getattr(module, attr, None)
        if not cls:
            continue
        clslist.append(cls)
    return clslist

def get_module_by_slug(slug):
    """
    Searches for a module by slug
    """
    for cls in get_module_classes():
        if cls().get_slug() == slug:
            return cls


def update_modules(logger=None):
    """
    Process all module updates
    """
    now = datetime.datetime.utcnow()
    for cls in get_module_classes():
        instance = cls()
        if not instance.check_compatible():
            continue
        if instance.write_to_db:
            if logger:
                logger.debug('Saving %s - Value: %.2f' % (instance.name, instance.get_val()))
            try:
                module = ModuleStat.objects.get(
                modulename=instance.get_slug(),
                added__year=now.year,
                added__month=now.month,
                added__day=now.day)
                module.value=instance.get_val()
                module.save()
            except ModuleStat.DoesNotExist:
                ModuleStat.objects.create(modulename=instance.get_slug(), value=instance.get_val())


class BigBrotherModule():
    """
    Base class for all BigBrother modules that implements the basic skeleton required for a module.
    """

    name = 'Unnamed Module'
    write_to_db = True
    prefix_text = None
    suffix_text = None
    warning_low = None
    warning_high = None
    link_url = None
    aggregate_function = None
    graphs = get_graph_list()
    group = None

    def check_compatible(self):
        """
        Checks if this module can operate in the current enviroment. It is suggested that you check dependencies in
        this function.
        """
        return True

    def get_aggregate_function(self):
        """
        Return the Django aggregation function this module uses for the aggregated graph views.
        """
        return self.aggregate_function

    def get_val(self):
        """
        Returns the current value
        """
        raise NotImplementedError('get_val not implemented.')

    def get_prefix_text(self):
        """
        Get the text to prefix the value with, for example $ for monetary values.
        """
        return self.prefix_text or ''

    def get_suffix_text(self):
        """
        Get the suffix for the value, for example "Users" for a user count.
        """
        return self.suffix_text or ''

    def get_text(self):
        """
        Returns the current value as formatted text
        """
        return '%s%g%s' % (self.get_prefix_text(), self.get_val(), self.get_suffix_text())

    def get_slug(self):
        """
        Returns the URL friendly slug for the module
        """
        return slugify(self.name)

    def check_warning(self):
        """
        Check if a warning level has been breached
        """
        if self.warning_high and self.get_val() >= self.warning_high:
            self.warn(warningtype='high')
            return True
        if self.warning_low and self.get_val() <= self.warning_low:
            self.warn(warningtype='low')
            return True
        return False

    def warn(self, warningtype):
        send_warning(module=self.__class__, warningtype=warningtype)


class UserCount(BigBrotherModule):
    """
    Module providing a count of users from django.contrib.auth
    """
    name = 'Total Users'
    group = 'User'

    def check_compatible(self):
        from django.conf import settings
        if 'django.contrib.auth' in settings.INSTALLED_APPS:
            return True
        return False

    def get_val(self):
        try:
            from django.contrib.auth import get_user_model
            USER_MODEL = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User as USER_MODEL
        users = USER_MODEL.objects.all()
        return users.count()


class NewUsersTodayCount(BigBrotherModule):
    """
    Module providing a count of new users from django.contrib.auth
    """
    name = 'New Users Today'
    group = 'User'

    def check_compatible(self):
        from django.conf import settings
        if 'django.contrib.auth' in settings.INSTALLED_APPS:
            return True
        return False

    def get_val(self):
        try:
            from django.contrib.auth import get_user_model
            USER_MODEL = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User as USER_MODEL
        users = USER_MODEL.objects.filter(date_joined=datetime.date.today())
        return users.count()


class FreeRamCount(BigBrotherModule):
    name = 'Free RAM'
    suffix_text = ' MB'
    warning_low = 16
    group = 'Server'

    def check_compatible(self):
        try:
            import psutil
        except ImportError:
            return False
        return True

    def get_val(self):
        import psutil
        return psutil.phymem_usage()[2] / (1024 * 1024)


class SwapUsage(BigBrotherModule):
    name = 'Swap Usage'
    suffix_text = ' MB'
    warning_high = 1
    group = 'Server'

    def check_compatible(self):
        try:
            import psutil
        except ImportError:
            return False
        return True

    def get_val(self):
        import psutil
        return psutil.virtmem_usage()[1] / (1024 * 1024)


class FreeDiskCount(BigBrotherModule):
    name = 'Free Disk Space'
    suffix_text = ' GB'
    group = 'Server'

    def check_compatible(self):
        import platform
        if platform.system() == 'Windows':
            return False
        return True

    def get_val(self):
        import os
        s = os.statvfs(os.path.split(os.getcwd())[0])
        return round((s.f_bavail * s.f_frsize) / (1024 * 1024 * 1024.0), 1)

########NEW FILE########
__FILENAME__ = graphs
from bigbrother.core import get_module_by_slug
from bigbrother.models import ModuleStat
from django.db.models import Avg
from datetime import datetime, timedelta
import qsstats


class Graph():
    stopdate = datetime.utcnow()
    showpoints = False

    def get_graph_data(self, slug, *args, **kwargs):
        module = get_module_by_slug(slug)()
        q = ModuleStat.objects.filter(modulename=slug)
        qs = qsstats.QuerySetStats(q, 'added', module.get_aggregate_function() or Avg('value'))
        data = qs.time_series(self.startdate, self.stopdate, interval=self.interval)
        return data


class LineGraph(Graph):
    type = 'line'
    showpoints = True


class BarGraph(Graph):
    type = 'bar'


class LastWeekGraph(LineGraph):
    name = 'Last Week'
    interval = 'days'
    startdate = datetime.utcnow() - timedelta(days=7)


class LastMonthGraph(LineGraph):
    name = 'Last Month'
    interval = 'days'
    startdate = datetime.utcnow() - timedelta(days=30)


class LastYearGraph(LineGraph):
    name = 'Last Year'
    interval = 'weeks'
    startdate = datetime.utcnow() - timedelta(days=365)

########NEW FILE########
__FILENAME__ = update_bigbrother
from django.core.management.base import BaseCommand
from bigbrother.core import update_modules


class Command(BaseCommand):
    help = 'Updates all active modules in BigBrother'

    def handle(self, *args, **options):
        update_modules()
        self.stdout.write('All modules updated successfully')
########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ModuleStat'
        db.create_table('bigbrother_modulestat', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('modulename', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('bigbrother', ['ModuleStat'])


    def backwards(self, orm):
        
        # Deleting model 'ModuleStat'
        db.delete_table('bigbrother_modulestat')


    models = {
        'bigbrother.modulestat': {
            'Meta': {'object_name': 'ModuleStat'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modulename': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['bigbrother']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_modulestat_value
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'ModuleStat.value'
        db.alter_column('bigbrother_modulestat', 'value', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2))


    def backwards(self, orm):
        
        # Changing field 'ModuleStat.value'
        db.alter_column('bigbrother_modulestat', 'value', self.gf('django.db.models.fields.IntegerField')())


    models = {
        'bigbrother.modulestat': {
            'Meta': {'object_name': 'ModuleStat'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modulename': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        }
    }

    complete_apps = ['bigbrother']

########NEW FILE########
__FILENAME__ = models
from django.db import models

class ModuleStat(models.Model):
    modulename = models.CharField('Module', max_length=64)
    added = models.DateTimeField('Stat Date', auto_now_add=True)
    value = models.DecimalField('Value', max_digits=10, decimal_places=2)
########NEW FILE########
__FILENAME__ = tasks
import celery
from .core import update_modules

@celery.task(ignore_result=True)
def update_bigbrother():
    logger = update_bigbrother.get_logger()

    logger.info('Updating BigBrother modules...')
    update_modules()
    logger.info('Update complete.')
########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, url
import bigbrother.views

urlpatterns = patterns('',
    url('^$', bigbrother.views.BigBrotherIndexView.as_view(), name='bigbrother_index'),
    url('^graph/(?P<slug>[^/]+)/$', bigbrother.views.BigBrotherGraphView.as_view(), name='bigbrother_graph'),
    url('^group/(?P<slug>[^/]+)/$', bigbrother.views.BigBrotherGroupView.as_view(), name='bigbrother_group'),
    url('^update/$', bigbrother.views.BigBrotherUpdateView.as_view(), name='bigbrother_update'),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic import TemplateView, View
from django.db.models import Avg
from django.conf import settings
import qsstats
from bigbrother.models import ModuleStat
from bigbrother.core import get_module_classes, get_graph_classes


class BigBrotherView(TemplateView):
    """
    If the setting BIGBROTHER_REQUIRE_ADMIN is set to True, checks if the user is staff member.
    """

    def get(self, request, *args, **kwargs):
        if settings.BIGBROTHER_REQUIRE_ADMIN and not request.user.is_staff:
            return HttpResponseForbidden()
        else:
            return super(BigBrotherView, self).get(request, *args, **kwargs)

class BigBrotherIndexView(BigBrotherView):
    """
    Produces a overview of installed modules
    """

    template_name = 'bigbrother/index.html'
    group = None

    def get_group(self):
        """
        Makes it possible to override group for a view.
        """

        return self.group

    def get_overview_data(self):
        data = []
        for cls in get_module_classes(self.get_group()):
            instance = cls()
            if instance.check_compatible():
                data.append({'name': instance.name,
                             'value': instance.get_val(),
                             'text': instance.get_text(),
                             'warning': instance.check_warning(),
                             'link': instance.link_url,
                             'group': self.get_group})
        return data

    def get_context_data(self, **kwargs):
        ctx = super(BigBrotherIndexView, self).get_context_data(**kwargs)
        ctx.update({
            'bb': self.get_overview_data,
        })
        return ctx


class BigBrotherGraphView(BigBrotherView):
    """
    Shows a individual module and produces the related graph
    """

    template_name = 'bigbrother/graph.html'

    def get_graph_data(self):
        data = []
        for cls in get_graph_classes():
            instance = cls()
            dataset = instance.get_graph_data(slug=self.kwargs.get('slug'))
            data.append({'name': instance.name,
                         'data': dataset,
                         'startdate': dataset[0][0],
                         'stopdate': dataset[-1][0],
                         'type': instance.type,
                         'showpoints': instance.showpoints})
        return data

    def get_context_data(self, **kwargs):
        ctx = super(BigBrotherGraphView, self).get_context_data(**kwargs)
        ctx.update({
            'bb': self.get_graph_data,
            'modulename': self.kwargs.get('slug')
        })
        return ctx

class BigBrotherGroupView(BigBrotherIndexView):
    """
    Display overview data for a group.
    """

    template_name = 'bigbrother/group.html'

    def get_group(self):
        return self.kwargs.get('slug')


class BigBrotherUpdateView(View):
    """
    Compatibility view for updating modules
    """
    def get(self, request, *args, **kwargs):
        from .core import update_modules
        update_modules()
        return HttpResponse('ok')

########NEW FILE########
__FILENAME__ = warnings
from django.conf import settings
from django.utils.importlib import import_module

class BigBrotherWarning(object):
    unread_warnings = 0

    def send_warning(self, module, warningtype):
        pass

def send_warning(module, warningtype):
    warningmodule, warningname = get_alert_name()
    obj = getattr(warningmodule, warningname)()
    getattr(warningmodule, warningname).send_warning(obj, module=module, warningtype=warningtype)

def get_alert_name():
    warningname = getattr(settings, 'BIGBROTHER_WARNING', None)
    if not warningname:
        warningname = 'bigbrother.warnings.EmailWarning'

    warningmodulename, warningname = warningname.rsplit('.', 1)
    warningmodule = import_module(warningmodulename)
    return warningmodule, warningname

class EmailWarning(BigBrotherWarning):
    def send_warning(self, module=None, warningtype=None):
        from django.core.mail import mail_admins
        subject = 'BigBrother Warning: %s is to %s' % (module.name, warningtype)
        message = 'Warning, the BigBrother module %s have sent an alert because its current value, %s is to %s.'% (module.name, module.get_text(module()), warningtype)
        mail_admins(subject=subject, message=message)


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-bigbrother documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 11 21:52:34 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath(os.path.join('..', 'example_project')))
import example_project.settings
from django.core.management import setup_environ
setup_environ(example_project.settings)
import bigbrother

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-bigbrother'
copyright = u'2013, Anders Petersson & Contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = bigbrother.__version__
# The full version, including alpha/beta/rc tags.
release = bigbrother.__version__

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
exclude_patterns = ['_build']

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
htmlhelp_basename = 'django-bigbrotherdoc'


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
  ('index', 'django-bigbrother.tex', u'django-bigbrother Documentation',
   u'Anders Petersson, Andrew Williams', 'manual'),
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
    ('index', 'django-bigbrother', u'django-bigbrother Documentation',
     [u'Anders Petersson, Andrew Williams'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-bigbrother', u'django-bigbrother Documentation',
   u'Anders Petersson, Andrew Williams', 'django-bigbrother', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example.sqlite3',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'tc$-fqo+d++c9ll-bg(2bi=m#vgl6jx@@jblz-_99qo#-z$5uq'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example_project.wsgi.application'

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
    'django.contrib.staticfiles',
    'bigbrother',
)

BIGBROTHER_REQUIRE_ADMIN = False

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

INTERNAL_IPS = ('127.0.0.1',)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url('', include('bigbrother.urls')),
    # Examples:
    # url(r'^$', 'example_project.views.home', name='home'),
    # url(r'^example_project/', include('example_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..' ))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
