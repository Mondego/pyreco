__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from admin_honeypot.models import LoginAttempt


class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'get_ip_address', 'get_session_key', 'timestamp', 'get_path')
    list_filter = ('timestamp',)
    readonly_fields = ('path', 'username', 'password', 'ip_address', 'session_key', 'user_agent')
    search_fields = ('username', 'password', 'ip_address', 'user_agent', 'path')

    def get_actions(self, request):
        actions = super(LoginAttemptAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_session_key(self, instance):
        return '<a href="?session_key=%(key)s">%(key)s</a>' % {'key': instance.session_key}
    get_session_key.short_description = _('Session')
    get_session_key.allow_tags = True

    def get_ip_address(self, instance):
        return '<a href="?ip_address=%(ip)s">%(ip)s</a>' % {'ip': instance.ip_address}
    get_ip_address.short_description = _('IP Address')
    get_ip_address.allow_tags = True

    def get_path(self, instance):
        return '<a href="?path=%(path)s">%(path)s</a>' % {'path': instance.path}
    get_path.short_description = _('URL')
    get_path.allow_tags = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(LoginAttempt, LoginAttemptAdmin)

########NEW FILE########
__FILENAME__ = forms
import django
from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm, ERROR_MESSAGE


class HoneypotLoginForm(AdminAuthenticationForm):
    def clean(self):
        """
        Always raise the default error message, because we don't
        care what they entered here.
        """
        # first check if the form has the username_field attribute
        # set, which indicates custom user model support
        username_field = getattr(self, 'username_field', None)
        if username_field is not None:
            params = {'username': username_field.verbose_name}
            # then raise the validation error in different ways,
            # depending on the Django version
            if django.VERSION >= (1, 6):
                raise forms.ValidationError(ERROR_MESSAGE,
                                            code='invalid',
                                            params=params)
            else:
                raise forms.ValidationError(ERROR_MESSAGE % params)
        # fall back to just using the error message as a string
        raise forms.ValidationError(ERROR_MESSAGE)

########NEW FILE########
__FILENAME__ = listeners
from admin_honeypot.signals import honeypot
from django.conf import settings
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string


def notify_admins(instance, request, **kwargs):
    path = reverse('admin:admin_honeypot_loginattempt_change', args=(instance.pk,))
    admin_detail_url = 'http://{0}{1}'.format(request.get_host(), path)
    context = {
        'request': request,
        'instance': instance,
        'admin_detail_url': admin_detail_url,
    }
    subject = render_to_string('admin_honeypot/email_subject.txt', context).strip()
    message = render_to_string('admin_honeypot/email_message.txt', context).strip()
    mail_admins(subject=subject, message=message)

if getattr(settings, 'ADMIN_HONEYPOT_EMAIL_ADMINS', True):
    honeypot.connect(notify_admins)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'LoginAttempt'
        db.create_table('admin_honeypot_loginattempt', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('ip_address', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('session_key', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('user_agent', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('admin_honeypot', ['LoginAttempt'])


    def backwards(self, orm):
        
        # Deleting model 'LoginAttempt'
        db.delete_table('admin_honeypot_loginattempt')


    models = {
        'admin_honeypot.loginattempt': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'LoginAttempt'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['admin_honeypot']

########NEW FILE########
__FILENAME__ = 0002_add_field_LoginAttempt_path
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'LoginAttempt.path'
        db.add_column('admin_honeypot_loginattempt', 'path',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'LoginAttempt.path'
        db.delete_column('admin_honeypot_loginattempt', 'path')


    models = {
        'admin_honeypot.loginattempt': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'LoginAttempt'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['admin_honeypot']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from admin_honeypot import listeners


class LoginAttempt(models.Model):
    username = models.CharField(_("username"), max_length=255, blank=True, null=True)
    password = models.CharField(_("password"), max_length=255, blank=True, null=True)
    ip_address = models.IPAddressField(_("ip address"), blank=True, null=True)
    session_key = models.CharField(_("session key"), max_length=50, blank=True, null=True)
    user_agent = models.TextField(_("user-agent"), blank=True, null=True)
    timestamp = models.DateTimeField(_("timestamp"), auto_now_add=True)
    path = models.CharField(_("path"), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("login attempt")
        verbose_name_plural = _("login attempts")
        ordering = ('timestamp',)

    def __str__(self):
        return self.username

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

honeypot = Signal(providing_args=['instance', 'request'])

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('admin_honeypot.views',
    url(r'^.*$', 'admin_honeypot', name='admin_honeypot'),
)

########NEW FILE########
__FILENAME__ = views
from admin_honeypot.forms import HoneypotLoginForm
from admin_honeypot.models import LoginAttempt
from admin_honeypot.signals import honeypot
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.utils.translation import ugettext as _


def admin_honeypot(request, extra_context=None):
    if not request.path.endswith('/'):
        return redirect(request.path + '/', permanent=True)
    path = request.get_full_path()

    context = {
        'app_path': path,
        'form': HoneypotLoginForm(request, request.POST or None),
        REDIRECT_FIELD_NAME: path,
        'title': _('Log in'),
    }
    context['form'].is_valid()
    context.update(extra_context or {})
    if len(path) > 255:
        path = path[:230] + '...(%d chars)' % len(path)
    if request.method == 'POST':
        failed = LoginAttempt.objects.create(
            username=request.POST.get('username'),
            password=request.POST.get('password'),
            session_key=request.session.session_key,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            path=path,
        )
        honeypot.send(sender=LoginAttempt, instance=failed, request=request)
    return render_to_response('admin_honeypot/login.html', context,
        context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = conftest
import os
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-admin-honeypot documentation build configuration file, created by
# sphinx-quickstart on Sat Mar  3 21:17:00 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-admin-honeypot'
copyright = u'2012, Derek Payton'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.0'

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
htmlhelp_basename = 'django-admin-honeypotdoc'


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
  ('index', 'django-admin-honeypot.tex', u'django-admin-honeypot Documentation',
   u'Derek Payton', 'manual'),
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
    ('index', 'django-admin-honeypot', u'django-admin-honeypot Documentation',
     [u'Derek Payton'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-admin-honeypot', u'django-admin-honeypot Documentation',
   u'Derek Payton', 'django-admin-honeypot', 'One line description of project.',
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
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = MANAGERS = (('Admin User', 'admin@example.com'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

LANGUAGE_CODE = 'en-us'
ROOT_URLCONF = 'tests.urls'
SECRET_KEY = 'local'
SITE_ID = 1
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
STATIC_URL = '/static/'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'admin_honeypot',
)

ADMIN_HONEYPOT_EMAIL_ADMINS = True

########NEW FILE########
__FILENAME__ = test_suite
from admin_honeypot.models import LoginAttempt
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase


class AdminHoneypotTest(TestCase):

    def test_same_content(self):
        """
        The honeypot should be an exact replica of the admin login page,
        with the exception of where the form submits to and the CSS to
        hide the user tools.
        """

        admin_url = reverse('admin:index')
        honeypot_url = reverse('admin_honeypot')

        admin_html = self.client.get(admin_url).content.decode('utf-8')
        honeypot_html = self.client.get(honeypot_url).content.decode('utf-8').replace(
            '"{0}"'.format(honeypot_url),
            '"{0}"'.format(admin_url)
        )

        self.assertEqual(honeypot_html, admin_html)

    def test_create_login_attempt(self):
        """
        A new LoginAttempt object is created
        """
        data = {
            'username': 'admin',
            'password': 'letmein'
        }
        response = self.client.post(reverse('admin_honeypot'), data)
        attempt = LoginAttempt.objects.latest('pk')
        self.assertEqual(data['username'], attempt.username)
        self.assertEqual(data['password'], attempt.password)
        self.assertEqual(data['username'], str(attempt))

    def test_email_admins(self):
        """
        An email is sent to settings.ADMINS
        """
        response = self.client.post(reverse('admin_honeypot'), {
            'username': 'admin',
            'password': 'letmein'
        })
        # CONSIDER: Is there a better way to do this?
        self.assertTrue(len(mail.outbox) > 0)  # We sent at least one email...
        self.assertIn(settings.ADMINS[0][1], mail.outbox[0].to)  # ...to an admin

    def test_arbitrary_urls(self):
        """
        The Django admin displays a login screen for everything under /admin/
        """
        data = {
            'username': 'admin',
            'password': 'letmein',
        }
        url_list = (
            'auth/',
            'comments/moderate/',
            'flatpages/flatpage/?ot=desc&o=1'
            'auth/user/1/',
        )
        base_url = reverse('admin_honeypot')
        for url in url_list:
            response = self.client.post(base_url + url, data)
            attempt = LoginAttempt.objects.latest('pk')
            self.assertEqual(base_url + url, attempt.path)
            self.assertEqual(data['username'], attempt.username)
            self.assertEqual(data['password'], attempt.password)

    def test_trailing_slash(self):
        """
        /admin/foo redirects to /admin/foo/ permanent redirect.
        """
        url = reverse('admin_honeypot')
        response = self.client.get(url + 'foo')
        self.assertRedirects(response, url + 'foo/', status_code=301)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('playground.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include('admin_honeypot.urls')),
    url(r'^secret/', include(admin.site.urls)),
)

########NEW FILE########
