__FILENAME__ = createdb
import MySQLdb
import psycopg2
import os
from wsgi import *

def create_dbs():
    print("create_dbs: let's go.")
    django_settings = __import__(os.environ['DJANGO_SETTINGS_MODULE'], fromlist='DATABASES')
    print("create_dbs: got settings.")
    databases = django_settings.DATABASES
    for name, db in databases.iteritems():
        host = db['HOST']
        user = db['USER']
        password = db['PASSWORD']
        port = db['PORT']
        db_name = db['NAME']
        db_type = db['ENGINE']
        # see if it is mysql
        if db_type.endswith('mysql'):
            print 'creating database %s on %s' % (db_name, host)
            db = MySQLdb.connect(user=user,
                                passwd=password,
                                host=host,
                                port=port)
            cur = db.cursor()
            print("Check if database is already there.")
            cur.execute("""SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA
                         WHERE SCHEMA_NAME = %s""", (db_name,))
            results = cur.fetchone()
            if not results:
                print("Database %s doesn't exist, lets create it." % db_name)
                sql = """CREATE DATABASE IF NOT EXISTS %s """ % (db_name,)
                print("> %s" % sql)
                cur.execute(sql)
                print(".....")
            else:
                print("database already exists, moving on to next step.")
        # see if it is postgresql
        elif db_type.endswith('postgresql_psycopg2'):
            print 'creating database %s on %s' % (db_name, host)
            con = psycopg2.connect(host=host, user=user, password=password, port=port, database='postgres')
            con.set_isolation_level(0)
            cur = con.cursor()
            try:
                cur.execute('CREATE DATABASE %s' % db_name)
            except psycopg2.ProgrammingError as detail:
                print detail
                print 'moving right along...'
        else:
            print("ERROR: {0} is not supported by this script, you will need to create your database by hand.".format(db_type))

if __name__ == '__main__':
    import sys
    print("create_dbs start")
    create_dbs()
    print("create_dbs all done")

########NEW FILE########
__FILENAME__ = settings
# Django settings for Userena demo project.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

import os
settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.dirname(settings_dir))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'private/development.db'),
    }
}

# Internationalization
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ugettext = lambda s: s
LANGUAGES = (
    ('en', ugettext('English')),
    ('nl', ugettext('Dutch')),
    ('fr', ugettext('French')),
    ('pl', ugettext('Polish')),
    ('pt', ugettext('Portugese')),
    ('pt-br', ugettext('Brazilian Portuguese')),
    ('es', ugettext('Spanish')),
    ('el', ugettext('Greek')),
)
LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, 'locale'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'public/media/')
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'public/static/')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'demo/static/'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_g-js)o8z#8=9pr1&amp;05h^1_#)91sbo-)g^(*=-+epxmt4kc9m#'

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
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'userena.middleware.UserenaLocaleMiddleware',
)

# Add the Guardian and userena authentication backends
AUTHENTICATION_BACKENDS = (
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Settings used by Userena
LOGIN_REDIRECT_URL = '/accounts/%(username)s/'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/accounts/signout/'
AUTH_PROFILE_MODULE = 'profiles.Profile'
USERENA_DISABLE_PROFILE_LIST = True
USERENA_MUGSHOT_SIZE = 140

ROOT_URLCONF = 'demo.urls'
WSGI_APPLICATION = 'demo.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'demo/templates/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'guardian',
    'south',
    'userena',
    'userena.contrib.umessages',
    'profiles',
)

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

# Needed for Django guardian
ANONYMOUS_USER_ID = -1

# Test runner
TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'

########NEW FILE########
__FILENAME__ = settings_dotcloud
from settings import *

import json

DEBUG = False
TEMPLATE_DEBUG = DEBUG
with open('/home/dotcloud/environment.json') as f:
    env = json.load(f)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'django_userena',
            'USER': env['DOTCLOUD_DB_SQL_LOGIN'],
            'PASSWORD': env['DOTCLOUD_DB_SQL_PASSWORD'],
            'HOST': env['DOTCLOUD_DB_SQL_HOST'],
            'PORT': int(env['DOTCLOUD_DB_SQL_PORT']),
        }
    }

    # Email settings
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = env['GMAIL_USER']
    EMAIL_HOST_PASSWORD = env['GMAIL_PASSWORD']
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = "Userena <hello@breadandpepper.com>"

# Media and static
MEDIA_ROOT = '/home/dotcloud/data/media/'
STATIC_ROOT = '/home/dotcloud/volatile/static/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': '/var/log/supervisor/userena.log',
            'maxBytes': 1024*1024*25, # 25 MB
            'backupCount': 5,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        # Catch All Logger -- Captures any other logging
        '': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.conf import settings

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),

    # Demo Override the signup form with our own, which includes a
    # first and last name.
    # (r'^accounts/signup/$',
    #  'userena.views.signup',
    #  {'signup_form': SignupFormExtra}),

    (r'^accounts/', include('userena.urls')),
    (r'^messages/', include('userena.contrib.umessages.urls')),
    url(r'^$', 'profiles.views.promo', name='promo'),
    (r'^i18n/', include('django.conf.urls.i18n')),
)

# Add media and static files
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demo_2 project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_2.settings")

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
    cwd = os.path.dirname(__file__)
    sys.path.append(os.path.join(os.path.abspath(os.path.dirname(cwd)), '../'))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from userena.forms import SignupForm

class SignupFormExtra(SignupForm):
    """ 
    A form to demonstrate how to add extra fields to the signup form, in this
    case adding the first and last name.
    

    """
    first_name = forms.CharField(label=_(u'First name'),
                                 max_length=30,
                                 required=False)

    last_name = forms.CharField(label=_(u'Last name'),
                                max_length=30,
                                required=False)

    def __init__(self, *args, **kw):
        """
        
        A bit of hackery to get the first name and last name at the top of the
        form instead at the end.
        
        """
        super(SignupFormExtra, self).__init__(*args, **kw)
        # Put the first and last name at the top
        new_order = self.fields.keyOrder[:-2]
        new_order.insert(0, 'first_name')
        new_order.insert(1, 'last_name')
        self.fields.keyOrder = new_order

    def save(self):
        """ 
        Override the save method to save the first and last name to the user
        field.

        """
        # First save the parent form and get the user.
        new_user = super(SignupFormExtra, self).save()

        new_user.first_name = self.cleaned_data['first_name']
        new_user.last_name = self.cleaned_data['last_name']
        new_user.save()

        # Userena expects to get the new user from this form, so return the new
        # user.
        return new_user

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from userena.models import UserenaLanguageBaseProfile
from userena.utils import user_model_label

import datetime

class Profile(UserenaLanguageBaseProfile):
    """ Default profile """
    GENDER_CHOICES = (
        (1, _('Male')),
        (2, _('Female')),
    )

    user = models.OneToOneField(user_model_label,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='profile')

    gender = models.PositiveSmallIntegerField(_('gender'),
                                              choices=GENDER_CHOICES,
                                              blank=True,
                                              null=True)
    website = models.URLField(_('website'), blank=True)
    location =  models.CharField(_('location'), max_length=255, blank=True)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    about_me = models.TextField(_('about me'), blank=True)

    @property
    def age(self):
        if not self.birth_date: return False
        else:
            today = datetime.date.today()
            # Raised when birth date is February 29 and the current year is not a
            # leap year.
            try:
                birthday = self.birth_date.replace(year=today.year)
            except ValueError:
                day = today.day - 1 if today.day != 1 else today.day + 2
                birthday = self.birth_date.replace(year=today.year, day=day)
            if birthday > today: return today.year - self.birth_date.year - 1
            else: return today.year - self.birth_date.year

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def promo(request):
    return render(request, 'static/promo.html')

########NEW FILE########
__FILENAME__ = superuser
#!/usr/bin/env python
from wsgi import *
from userena.utils import get_user_model
try:
    wunki = get_user_model().objects.get(username='wunki')
except get_user_model().DoesNotExist:
    pass
else:
    wunki.is_staff = True
    wunki.is_superuser = True
    wunki.save()

########NEW FILE########
__FILENAME__ = wsgi
import django.core.handlers.wsgi

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'demo')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'demo.settings_dotcloud'
application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Userena documentation build configuration file, created by
# sphinx-quickstart on Fri Jul  2 09:28:08 2010.
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
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../demo'))
userena = __import__('userena')
demo = __import__('demo')
os.environ['DJANGO_SETTINGS_MODULE'] = 'demo.settings'


# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-userena'
copyright = u'2010, 2011 Bread & Pepper'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = userena.get_version()
# The full version, including alpha/beta/rc tags.
release = userena.__version__

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
pygments_style = 'murphy'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = ['theme']

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
html_static_path = []

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
htmlhelp_basename = 'userenadoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Userena.tex', u'Userena Documentation',
   u'Petar Radosevic', 'manual'),
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
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext as _
from guardian.admin import GuardedModelAdmin

from userena.models import UserenaSignup
from userena import settings as userena_settings
from userena.utils import get_profile_model, get_user_model

class UserenaSignupInline(admin.StackedInline):
    model = UserenaSignup
    max_num = 1

class UserenaAdmin(UserAdmin, GuardedModelAdmin):
    inlines = [UserenaSignupInline, ]
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')


if userena_settings.USERENA_REGISTER_USER:
    try:
        admin.site.unregister(get_user_model())
    except admin.sites.NotRegistered:
        pass
    
    admin.site.register(get_user_model(), UserenaAdmin)
    
if userena_settings.USERENA_REGISTER_PROFILE:    
    admin.site.register(get_profile_model(), GuardedModelAdmin)

########NEW FILE########
__FILENAME__ = backends
import django.core.validators
from django.contrib.auth.backends import ModelBackend

from userena.utils import get_user_model

class UserenaAuthenticationBackend(ModelBackend):
    """
    Custom backend because the user must be able to supply a ``email`` or
    ``username`` to the login form.

    """
    def authenticate(self, identification, password=None, check_password=True):
        """
        Authenticates a user through the combination email/username with
        password.

        :param identification:
            A string containing the username or e-mail of the user that is
            trying to authenticate.

        :password:
            Optional string containing the password for the user.

        :param check_password:
            Boolean that defines if the password should be checked for this
            user.  Always keep this ``True``. This is only used by userena at
            activation when a user opens a page with a secret hash.

        :return: The signed in :class:`User`.

        """
        User = get_user_model()
        try:
            django.core.validators.validate_email(identification)
            try: user = User.objects.get(email__iexact=identification)
            except User.DoesNotExist: return None
        except django.core.validators.ValidationError:
            try: user = User.objects.get(username__iexact=identification)
            except User.DoesNotExist: return None
        if check_password:
            if user.check_password(password):
                return user
            return None
        else: return user

    def get_user(self, user_id):
        User = get_user_model()
        try: return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
from collections import defaultdict
import django




# this default dict will store all compat quirks for parameters of
# django.contrib.auth views
auth_views_compat_quirks = defaultdict(lambda: dict())

# below are quirks we must use because we can't change some userena API's
# like (url names)
if django.VERSION >= (1, 6, 0):
    # in django >= 1.6.0 django.contrib.auth.views.reset no longer looks
    # for django.contrib.auth.views.password_reset_done but for
    # password_reset_done named url. To avoid duplicating urls we
    # provide custom post_reset_redirect
    auth_views_compat_quirks['userena_password_reset'] = {
        'post_reset_redirect': 'userena_password_reset_done',
    }

    # same case as above
    auth_views_compat_quirks['userena_password_reset_confirm'] = {
        'post_reset_redirect': 'userena_password_reset_complete',
    }

# below are backward compatibility fixes
password_reset_uid_kwarg = 'uidb64'
if django.VERSION < (1, 6, 0):
    # Django<1.6.0 uses uidb36, we construct urlpattern depending on this
    password_reset_uid_kwarg = 'uidb36'
########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.contrib.auth.models import Group

from userena.contrib.umessages.models import Message, MessageContact, MessageRecipient

class MessageRecipientInline(admin.TabularInline):
    """ Inline message recipients """
    model = MessageRecipient

class MessageAdmin(admin.ModelAdmin):
    """ Admin message class with inline recipients """
    inlines = [
        MessageRecipientInline,
    ]

    fieldsets = (
        (None, {
            'fields': (
                'sender', 'body',
            ),
            'classes': ('monospace' ),
        }),
        (_('Date/time'), {
            'fields': (
                'sender_deleted_at',
            ),
            'classes': ('collapse', 'wide'),
        }),
    )
    list_display = ('sender', 'body', 'sent_at')
    list_filter = ('sent_at', 'sender')
    search_fields = ('body',)

admin.site.register(Message, MessageAdmin)
admin.site.register(MessageContact)

########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

from userena.utils import get_user_model

class CommaSeparatedUserInput(widgets.Input):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, (list, tuple)):
            value = (', '.join([user.username for user in value]))
        return super(CommaSeparatedUserInput, self).render(name, value, attrs)

class CommaSeparatedUserField(forms.Field):
    """
    A :class:`CharField` that exists of comma separated usernames.

    :param recipient_filter:
        Optional function which receives as :class:`User` as parameter. The
        function should return ``True`` if the user is allowed or ``False`` if
        the user is not allowed.

    :return:
        A list of :class:`User`.

    """
    widget = CommaSeparatedUserInput

    def __init__(self, *args, **kwargs):
        recipient_filter = kwargs.pop('recipient_filter', None)
        self._recipient_filter = recipient_filter
        super(CommaSeparatedUserField, self).__init__(*args, **kwargs)

    def clean(self, value):
        super(CommaSeparatedUserField, self).clean(value)

        names = set(value.split(','))
        names_set = set([name.strip() for name in names])
        users = list(get_user_model().objects.filter(username__in=names_set))

        # Check for unknown names.
        unknown_names = names_set ^ set([user.username for user in users])

        recipient_filter = self._recipient_filter
        invalid_users = []
        if recipient_filter is not None:
            for r in users:
                if recipient_filter(r) is False:
                    users.remove(r)
                    invalid_users.append(r.username)

        if unknown_names or invalid_users:
            humanized_usernames = ', '.join(list(unknown_names) + invalid_users)
            raise forms.ValidationError(_("The following usernames are incorrect: %(users)s.") % {'users': humanized_usernames})

        return users

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from userena.contrib.umessages.fields import CommaSeparatedUserField
from userena.contrib.umessages.models import Message, MessageRecipient

import datetime

class ComposeForm(forms.Form):
    to = CommaSeparatedUserField(label=_("To"))
    body = forms.CharField(label=_("Message"),
                           widget=forms.Textarea({'class': 'message'}),
                           required=True)

    def save(self, sender):
        """
        Save the message and send it out into the wide world.

        :param sender:
            The :class:`User` that sends the message.

        :param parent_msg:
            The :class:`Message` that preceded this message in the thread.

        :return: The saved :class:`Message`.

        """
        um_to_user_list = self.cleaned_data['to']
        body = self.cleaned_data['body']

        msg = Message.objects.send_message(sender,
                                           um_to_user_list,
                                           body)

        return msg

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models import Q

from userena.contrib.umessages import signals

import datetime

class MessageContactManager(models.Manager):
    """ Manager for the :class:`MessageContact` model """

    def get_or_create(self, um_from_user, um_to_user, message):
        """
        Get or create a Contact

        We override Django's :func:`get_or_create` because we want contact to
        be unique in a bi-directional manner.

        """
        created = False
        try:
            contact = self.get(Q(um_from_user=um_from_user, um_to_user=um_to_user) |
                               Q(um_from_user=um_to_user, um_to_user=um_from_user))

        except self.model.DoesNotExist:
            created = True
            contact = self.create(um_from_user=um_from_user,
                                  um_to_user=um_to_user,
                                  latest_message=message)

        return (contact, created)

    def update_contact(self, um_from_user, um_to_user, message):
        """ Get or update a contacts information """
        contact, created = self.get_or_create(um_from_user,
                                              um_to_user,
                                              message)

        # If the contact already existed, update the message
        if not created:
            contact.latest_message = message
            contact.save()
        return contact

    def get_contacts_for(self, user):
        """
        Returns the contacts for this user.

        Contacts are other users that this user has received messages
        from or send messages to.

        :param user:
            The :class:`User` which to get the contacts for.

        """
        contacts = self.filter(Q(um_from_user=user) | Q(um_to_user=user))
        return contacts

class MessageManager(models.Manager):
    """ Manager for the :class:`Message` model. """

    def send_message(self, sender, um_to_user_list, body):
        """
        Send a message from a user, to a user.

        :param sender:
            The :class:`User` which sends the message.

        :param um_to_user_list:
            A list which elements are :class:`User` to whom the message is for.

        :param message:
            String containing the message.

        """
        msg = self.model(sender=sender,
                         body=body)
        msg.save()

        # Save the recipients
        msg.save_recipients(um_to_user_list)
        msg.update_contacts(um_to_user_list)
        signals.email_sent.send(sender=None,msg=msg)

        return msg

    def get_conversation_between(self, um_from_user, um_to_user):
        """ Returns a conversation between two users """
        messages = self.filter(Q(sender=um_from_user, recipients=um_to_user,
                                 sender_deleted_at__isnull=True) |
                               Q(sender=um_to_user, recipients=um_from_user,
                                 messagerecipient__deleted_at__isnull=True))
        return messages

class MessageRecipientManager(models.Manager):
    """ Manager for the :class:`MessageRecipient` model. """

    def count_unread_messages_for(self, user):
        """
        Returns the amount of unread messages for this user

        :param user:
            A Django :class:`User`

        :return:
            An integer with the amount of unread messages.

        """
        unread_total = self.filter(user=user,
                                   read_at__isnull=True,
                                   deleted_at__isnull=True).count()

        return unread_total

    def count_unread_messages_between(self, um_to_user, um_from_user):
        """
        Returns the amount of unread messages between two users

        :param um_to_user:
            A Django :class:`User` for who the messages are for.

        :param um_from_user:
            A Django :class:`User` from whom the messages originate from.

        :return:
            An integer with the amount of unread messages.

        """
        unread_total = self.filter(message__sender=um_from_user,
                                   user=um_to_user,
                                   read_at__isnull=True,
                                   deleted_at__isnull=True).count()

        return unread_total

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'MessageContact'
        db.create_table('umessages_messagecontact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('um_from_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='um_from_users', to=orm['auth.User'])),
            ('um_to_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='um_to_users', to=orm['auth.User'])),
            ('latest_message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['umessages.Message'])),
        ))
        db.send_create_signal('umessages', ['MessageContact'])

        # Adding unique constraint on 'MessageContact', fields ['um_from_user', 'um_to_user']
        db.create_unique('umessages_messagecontact', ['um_from_user_id', 'um_to_user_id'])

        # Adding model 'MessageRecipient'
        db.create_table('umessages_messagerecipient', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['umessages.Message'])),
            ('read_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('deleted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('umessages', ['MessageRecipient'])

        # Adding model 'Message'
        db.create_table('umessages_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sent_messages', to=orm['auth.User'])),
            ('sent_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('sender_deleted_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('umessages', ['Message'])


    def backwards(self, orm):

        # Removing unique constraint on 'MessageContact', fields ['um_from_user', 'um_to_user']
        db.delete_unique('umessages_messagecontact', ['um_from_user_id', 'um_to_user_id'])

        # Deleting model 'MessageContact'
        db.delete_table('umessages_messagecontact')

        # Deleting model 'MessageRecipient'
        db.delete_table('umessages_messagerecipient')

        # Deleting model 'Message'
        db.delete_table('umessages_message')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        'umessages.message': {
            'Meta': {'ordering': "['-sent_at']", 'object_name': 'Message'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipients': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'received_messages'", 'symmetrical': 'False', 'through': "orm['umessages.MessageRecipient']", 'to': "orm['auth.User']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_messages'", 'to': "orm['auth.User']"}),
            'sender_deleted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sent_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'umessages.messagecontact': {
            'Meta': {'ordering': "['latest_message']", 'unique_together': "(('um_from_user', 'um_to_user'),)", 'object_name': 'MessageContact'},
            'um_from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'um_from_users'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latest_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['umessages.Message']"}),
            'um_to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'um_to_users'", 'to': "orm['auth.User']"})
        },
        'umessages.messagerecipient': {
            'Meta': {'object_name': 'MessageRecipient'},
            'deleted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['umessages.Message']"}),
            'read_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['umessages']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from userena.utils import truncate_words
from userena.contrib.umessages.managers import (MessageManager, MessageContactManager,
                                                MessageRecipientManager)
from userena.utils import user_model_label

class MessageContact(models.Model):
    """
    Contact model.

    A contact is a user to whom a user has send a message to or
    received a message from.

    """
    um_from_user = models.ForeignKey(user_model_label, verbose_name=_("from user"),
                                  related_name=('um_from_users'))

    um_to_user = models.ForeignKey(user_model_label, verbose_name=_("to user"),
                                related_name=('um_to_users'))

    latest_message = models.ForeignKey('Message',
                                       verbose_name=_("latest message"))

    objects = MessageContactManager()

    class Meta:
        unique_together = ('um_from_user', 'um_to_user')
        ordering = ['latest_message']
        verbose_name = _("contact")
        verbose_name_plural = _("contacts")

    def __unicode__(self):
        return (_("%(um_from_user)s and %(um_to_user)s")
                % {'um_from_user': self.um_from_user.username,
                   'um_to_user': self.um_to_user.username})

    def opposite_user(self, user):
        """
        Returns the user opposite of the user that is given

        :param user:
            A Django :class:`User`.

        :return:
            A Django :class:`User`.

        """
        if self.um_from_user == user:
            return self.um_to_user
        else: return self.um_from_user

class MessageRecipient(models.Model):
    """
    Intermediate model to allow per recipient marking as
    deleted, read etc. of a message.

    """
    user = models.ForeignKey(user_model_label,
                             verbose_name=_("recipient"))

    message = models.ForeignKey('Message',
                                verbose_name=_("message"))

    read_at = models.DateTimeField(_("read at"),
                                   null=True,
                                   blank=True)

    deleted_at = models.DateTimeField(_("recipient deleted at"),
                                      null=True,
                                      blank=True)

    objects = MessageRecipientManager()

    class Meta:
        verbose_name = _("recipient")
        verbose_name_plural = _("recipients")

    def __unicode__(self):
        return (_("%(message)s")
                % {'message': self.message})

    def is_read(self):
        """ Returns a boolean whether the recipient has read the message """
        return self.read_at is None

class Message(models.Model):
    """ Private message model, from user to user(s) """
    body = models.TextField(_("body"))

    sender = models.ForeignKey(user_model_label,
                               related_name='sent_messages',
                               verbose_name=_("sender"))

    recipients = models.ManyToManyField(user_model_label,
                                        through='MessageRecipient',
                                        related_name="received_messages",
                                        verbose_name=_("recipients"))

    sent_at = models.DateTimeField(_("sent at"),
                                   auto_now_add=True)

    sender_deleted_at = models.DateTimeField(_("sender deleted at"),
                                             null=True,
                                             blank=True)

    objects = MessageManager()

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __unicode__(self):
        """ Human representation, displaying first ten words of the body. """
        truncated_body = truncate_words(self.body, 10)
        return "%(truncated_body)s" % {'truncated_body': truncated_body}

    def save_recipients(self, um_to_user_list):
        """
        Save the recipients for this message

        :param um_to_user_list:
            A list which elements are :class:`User` to whom the message is for.

        :return:
            Boolean indicating if any users are saved.

        """
        created = False
        for user in um_to_user_list:
            MessageRecipient.objects.create(user=user,
                                            message=self)
            created = True
        return created

    def update_contacts(self, um_to_user_list):
        """
        Updates the contacts that are used for this message.

        :param um_to_user_list:
            List of Django :class:`User`.

        :return:
            A boolean if a user is contact is updated.

        """
        updated = False
        for user in um_to_user_list:
            MessageContact.objects.update_contact(self.sender,
                                                  user,
                                                  self)
            updated = True
        return updated

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

email_sent = Signal(providing_args=["msg"])

########NEW FILE########
__FILENAME__ = umessages_tags
from django import template

from userena.contrib.umessages.models import MessageRecipient

import re

register = template.Library()

class MessageCount(template.Node):
    def __init__(self, um_from_user, var_name, um_to_user=None):
        self.user = template.Variable(um_from_user)
        self.var_name = var_name
        if um_to_user:
            self.um_to_user = template.Variable(um_to_user)
        else: self.um_to_user = um_to_user

    def render(self, context):
        try:
            user = self.user.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        if not self.um_to_user:
            message_count = MessageRecipient.objects.count_unread_messages_for(user)

        else:
            try:
                um_to_user = self.um_to_user.resolve(context)
            except template.VariableDoesNotExist:
                return ''

            message_count = MessageRecipient.objects.count_unread_messages_between(user,
                                                                                   um_to_user)

        context[self.var_name] = message_count

        return ''

@register.tag
def get_unread_message_count_for(parser, token):
    """
    Returns the unread message count for a user.

    Syntax::

        {% get_unread_message_count_for [user] as [var_name] %}

    Example usage::

        {% get_unread_message_count_for pero as message_count %}

    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("%s tag requires arguments" % token.contents.split()[0])
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError("%s tag had invalid arguments" % tag_name)
    user, var_name = m.groups()
    return MessageCount(user, var_name)

@register.tag
def get_unread_message_count_between(parser, token):
    """
    Returns the unread message count between two users.

    Syntax::

        {% get_unread_message_count_between [user] and [user] as [var_name] %}

    Example usage::

        {% get_unread_message_count_between funky and wunki as message_count %}

    """
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("%s tag requires arguments" % token.contents.split()[0])
    m = re.search(r'(.*?) and (.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError("%s tag had invalid arguments" % tag_name)
    um_from_user, um_to_user, var_name = m.groups()
    return MessageCount(um_from_user, var_name, um_to_user)

########NEW FILE########
__FILENAME__ = test_fields
from django.test import TestCase
from django import forms

from userena.contrib.umessages.fields import CommaSeparatedUserField

class CommaSeparatedTestForm(forms.Form):
    users = CommaSeparatedUserField()

    def __init__(self, *args, **kwargs):
        super(CommaSeparatedTestForm, self).__init__(*args, **kwargs)
        self.fields['users']._recipient_filter = self.filter_jane

    def filter_jane(self, user):
        if user.username == 'jane':
            return False
        return True

class CommaSeperatedFieldTests(TestCase):
    fixtures = ['users',]

    def test_invalid_data(self):
        # Test invalid data supplied to the field.
        invalid_data_dicts = [
            # Empty username
            {'data': {'users': ''},
             'error': ('users', [u'This field is required.'])},
            # No data
            {'data': {},
             'error': ('users', [u'This field is required.'])},
            # A list
            {'data': {'users': []},
             'error': ('users', [u'This field is required.'])},
            # Forbidden username
            {'data': {'users': 'jane'},
             'error': ('users', [u'The following usernames are incorrect: jane.'])},
            # Non-existant username
            {'data': {'users': 'foo'},
             'error': ('users', [u'The following usernames are incorrect: foo.'])},
            # Multiple invalid usernames
            {'data': {'users': 'foo, bar'},
             'error': ('users', [u'The following usernames are incorrect: foo, bar.'])},
            # Valid and invalid
            {'data': {'users': 'foo, john, bar'},
             'error': ('users', [u'The following usernames are incorrect: foo, bar.'])},
            # Extra whitespace
            {'data': {'users': 'foo,    john  '},
             'error': ('users', [u'The following usernames are incorrect: foo.'])},

        ]
        for invalid_dict in invalid_data_dicts:
            form = CommaSeparatedTestForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

########NEW FILE########
__FILENAME__ = test_forms
from django.test import TestCase

from userena.contrib.umessages.forms import ComposeForm
from userena.utils import get_user_model

class ComposeFormTests(TestCase):
    """ Test the compose form. """
    fixtures = ['users']

    def test_invalid_data(self):
        """
        Test the save method of :class:`ComposeForm`

        We don't need to make the ``to`` field sweat because we have done that
        in the ``fields`` test.

        """
        invalid_data_dicts = [
            # No body
            {'data': {'to': 'john',
                      'body': ''},
             'error': ('body', [u'This field is required.'])},
        ]

        for invalid_dict in invalid_data_dicts:
            form = ComposeForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

    def test_save_msg(self):
        """ Test valid data """
        valid_data = {'to': 'john, jane',
                      'body': 'Body'}

        form = ComposeForm(data=valid_data)

        self.failUnless(form.is_valid())

        # Save the form.
        sender = get_user_model().objects.get(username='jane')
        msg = form.save(sender)

        # Check if the values are set correctly
        self.failUnlessEqual(msg.body, valid_data['body'])
        self.failUnlessEqual(msg.sender, sender)
        self.failUnless(msg.sent_at)

        # Check recipients
        self.failUnlessEqual(msg.recipients.all()[0].username, 'jane')
        self.failUnlessEqual(msg.recipients.all()[1].username, 'john')

########NEW FILE########
__FILENAME__ = test_managers
from django.test import TestCase

from userena.contrib.umessages.models import (Message, MessageContact,
                                              MessageRecipient)
from userena.utils import get_user_model

User = get_user_model()


class MessageManagerTests(TestCase):
    fixtures = ['users', 'messages']

    def test_get_conversation(self):
        """ Test that the conversation is returned between two users """
        user_1 = User.objects.get(pk=1)
        user_2 = User.objects.get(pk=2)

        messages = Message.objects.get_conversation_between(user_1, user_2)

class MessageRecipientManagerTest(TestCase):
    fixtures = ['users', 'messages']

    def test_count_unread_messages_for(self):
        """ Test the unread messages count for user """
        jane = User.objects.get(pk=2)

        # Jane has one unread message from john
        unread_messages = MessageRecipient.objects.count_unread_messages_for(jane)

        self.failUnlessEqual(unread_messages, 1)

    def test_count_unread_messages_between(self):
        """ Test the unread messages count between two users """
        john = User.objects.get(pk=1)
        jane = User.objects.get(pk=2)

        # Jane should have one unread message from john
        unread_messages = MessageRecipient.objects.count_unread_messages_between(jane, john)

        self.failUnlessEqual(unread_messages, 1)

class MessageContactManagerTest(TestCase):
    fixtures = ['users', 'messages']

    def test_get_contacts_for(self):
        """ Test if the correct contacts are returned """
        john = User.objects.get(pk=1)
        contacts = MessageContact.objects.get_contacts_for(john)

        # There is only one contact for John, and that's Jane.
        self.failUnlessEqual(len(contacts), 1)

        jane = User.objects.get(pk=2)
        self.failUnlessEqual(contacts[0].um_to_user,
                             jane)


########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase

from userena.contrib.umessages.models import Message, MessageRecipient, MessageContact
from userena.utils import get_user_model, truncate_words

User = get_user_model()

class MessageContactTests(TestCase):
    fixtures = ['users', 'messages']

    def test_string_formatting(self):
        """ Test the human representation of a message """
        contact = MessageContact.objects.get(pk=1)
        correct_format = "john and jane"
        self.failUnlessEqual(contact.__unicode__(),
                             correct_format)

    def test_opposite_user(self):
        """ Test if the opposite user is returned """
        contact = MessageContact.objects.get(pk=1)
        john = User.objects.get(pk=1)
        jane = User.objects.get(pk=2)

        # Test the opposites
        self.failUnlessEqual(contact.opposite_user(john),
                             jane)

        self.failUnlessEqual(contact.opposite_user(jane),
                             john)

class MessageModelTests(TestCase):
    fixtures = ['users', 'messages']

    def test_string_formatting(self):
        """ Test the human representation of a message """
        message = Message.objects.get(pk=1)
        truncated_body = truncate_words(message.body, 10)
        self.failUnlessEqual(message.__unicode__(),
                             truncated_body)

class MessageRecipientModelTest(TestCase):
    fixtures = ['users', 'messages']

    def test_string_formatting(self):
        """ Test the human representation of a recipient """
        recipient = MessageRecipient.objects.get(pk=1)

        valid_unicode = '%s' % (recipient.message)

        self.failUnlessEqual(recipient.__unicode__(),
                             valid_unicode)

    def test_new(self):
        """ Test if the message that is new is correct """
        new_message = MessageRecipient.objects.get(pk=1)
        read_message = MessageRecipient.objects.get(pk=2)

        self.failUnless(new_message.is_read())
        self.failIf(read_message.is_read())

########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from userena.contrib.umessages.forms import ComposeForm
from userena.contrib.umessages.models import Message, MessageRecipient
from userena.utils import get_user_model

User = get_user_model()


class MessagesViewsTests(TestCase):
    fixtures = ['users', 'messages']

    def _test_login(self, named_url, **kwargs):
        """ Test that the view requires login """
        response = self.client.get(reverse(named_url, **kwargs))
        self.assertEqual(response.status_code, 302)

    def test_compose(self):
        """ A ``GET`` to the compose view """
        # Login is required.
        self._test_login('userena_umessages_compose')

        # Sign in
        client = self.client.login(username='john', password='blowfish')
        response = self.client.get(reverse('userena_umessages_compose'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'umessages/message_form.html')

        self.failUnless(isinstance(response.context['form'],
                                   ComposeForm))

    def test_compose_post(self):
        """ ``POST`` to the compose view """
        client = self.client.login(username='john', password='blowfish')

        valid_data = {'to': 'john',
                      'body': 'Hi'}

        # Check for a normal redirect
        response = self.client.post(reverse('userena_umessages_compose'),
                                    data=valid_data)

        self.assertRedirects(response,
                             reverse('userena_umessages_detail',
                                     kwargs={'username': 'john'}))

        # Check for a requested redirect
        valid_data['next'] = reverse('userena_umessages_compose')
        response = self.client.post(reverse('userena_umessages_compose'),
                                    data=valid_data)
        self.assertRedirects(response,
                             valid_data['next'])

    def test_compose_recipients(self):
        """ A ``GET`` to the compose view with recipients """
        client = self.client.login(username='john', password='blowfish')

        valid_recipients = "john+jane"
        invalid_recipients = "johny+jane"

        # Test valid recipients
        response = self.client.get(reverse('userena_umessages_compose_to',
                                           kwargs={'recipients': valid_recipients}))

        self.assertEqual(response.status_code, 200)

        # Test the users
        jane = User.objects.get(username='jane')
        john = User.objects.get(username='john')
        self.assertEqual(response.context['recipients'][0], jane)
        self.assertEqual(response.context['recipients'][1], john)

        # Test that the initial data of the form is set.
        self.assertEqual(response.context['form'].initial['to'],
                         [jane, john])

    def test_message_detail(self):
        """ A ``GET`` to the detail view """
        self._test_login('userena_umessages_detail',
                          kwargs={'message_id': 2})

        # Sign in
        client = self.client.login(username='jane', password='blowfish')
        response = self.client.get(reverse('userena_umessages_detail',
                                   kwargs={'message_id': 1}))


        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'umessages/message_detail.html')

        # Test that the message is read.
        jane = User.objects.get(pk=2)
        mr = MessageRecipient.objects.get(message=Message.objects.get(pk=1),
                                          user=jane)
        self.failUnless(mr.read_at)

    def test_valid_message_remove(self):
        """ ``POST`` to remove a message """
        # Test that sign in is required
        response = self.client.post(reverse('userena_umessages_remove'))
        self.assertEqual(response.status_code, 302)

        # Sign in
        client = self.client.login(username='john', password='blowfish')

        # Test that only posts are allowed
        response = self.client.get(reverse('userena_umessages_remove'))
        self.assertEqual(response.status_code, 405)

        # Test a valid post to delete a senders message
        response = self.client.post(reverse('userena_umessages_remove'),
                                    data={'message_pks': '1'})
        self.assertRedirects(response,
                             reverse('userena_umessages_list'))
        msg = Message.objects.get(pk=1)
        self.failUnless(msg.sender_deleted_at)

        # Test a valid post to delete a recipients message and a redirect
        client = self.client.login(username='jane', password='blowfish')
        response = self.client.post(reverse('userena_umessages_remove'),
                                    data={'message_pks': '1',
                                          'next': reverse('userena_umessages_list')})
        self.assertRedirects(response,
                             reverse('userena_umessages_list'))
        jane = User.objects.get(username='jane')
        mr = msg.messagerecipient_set.get(user=jane,
                                          message=msg)
        self.failUnless(mr.deleted_at)

    def test_invalid_message_remove(self):
        """ ``POST`` to remove an invalid message """
        # Sign in
        client = self.client.login(username='john', password='blowfish')

        bef_len = Message.objects.filter(sender_deleted_at__isnull=False).count()
        response = self.client.post(reverse('userena_umessages_remove'),
                                    data={'message_pks': ['a', 'b']})

        # The program should play nice, nothing happened.
        af_len = Message.objects.filter(sender_deleted_at__isnull=False).count()
        self.assertRedirects(response,
                             reverse('userena_umessages_list'))
        self.assertEqual(bef_len, af_len)

    def test_valid_message_remove_multiple(self):
        """ ``POST`` to remove multiple messages """
        # Sign in
        client = self.client.login(username='john', password='blowfish')
        response = self.client.post(reverse('userena_umessages_remove'),
                                    data={'message_pks': [1, 2]})
        self.assertRedirects(response,
                             reverse('userena_umessages_list'))

        # Message #1 and #2 should be deleted
        msg_list = Message.objects.filter(pk__in=['1','2'],
                                          sender_deleted_at__isnull=False)
        self.assertEqual(msg_list.count(), 2)

    def test_message_unremove(self):
        """ Unremove a message """
        client = self.client.login(username='john', password='blowfish')

        # Delete a message as owner
        response = self.client.post(reverse('userena_umessages_unremove'),
                                    data={'message_pks': [1,]})

        self.assertRedirects(response,
                             reverse('userena_umessages_list'))

        # Delete the message as a recipient
        response = self.client.post(reverse('userena_umessages_unremove'),
                                    data={'message_pks': [2,]})

        self.assertRedirects(response,
                             reverse('userena_umessages_list'))

    def test_message_list(self):
        """ ``GET`` the message list for a user """
        self._test_login("userena_umessages_list")

        client = self.client.login(username="john", password="blowfish")
        response = self.client.get(reverse("userena_umessages_list"))
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "umessages/message_list.html")

    def test_message_detail(self):
        """ ``GET`` to a detail page between two users """
        self._test_login("userena_umessages_detail",
                         kwargs={'username': "jane"})
        client = self.client.login(username='john', password='blowfish')

        response = self.client.get(reverse("userena_umessages_detail",
                                           kwargs={'username': "jane"}))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "umessages/message_detail.html")

        # Check that all the messages are marked as read.
        john = User.objects.get(pk=1)
        jane = User.objects.get(pk=2)
        unread_messages = MessageRecipient.objects.filter(user=john,
                                                          message__sender=jane,
                                                          read_at__isnull=True)

        self.assertEqual(len(unread_messages), 0)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from userena.contrib.umessages import views as messages_views
from django.contrib.auth.decorators import login_required

urlpatterns = patterns('',
    url(r'^compose/$',
        messages_views.message_compose,
        name='userena_umessages_compose'),

    url(r'^compose/(?P<recipients>[\+\.\w]+)/$',
        messages_views.message_compose,
        name='userena_umessages_compose_to'),

    url(r'^reply/(?P<parent_id>[\d]+)/$',
        messages_views.message_compose,
        name='userena_umessages_reply'),

    url(r'^view/(?P<username>[\.\w]+)/$',
        login_required(messages_views.MessageDetailListView.as_view()),
        name='userena_umessages_detail'),

    url(r'^remove/$',
        messages_views.message_remove,
        name='userena_umessages_remove'),

    url(r'^unremove/$',
        messages_views.message_remove,
        {'undo': True},
        name='userena_umessages_unremove'),

    url(r'^$',
        login_required(messages_views.MessageListView.as_view()),
        name='userena_umessages_list'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.generic.list import ListView

from userena.contrib.umessages.models import Message, MessageRecipient, MessageContact
from userena.contrib.umessages.forms import ComposeForm
from userena.utils import get_datetime_now, get_user_model
from userena import settings as userena_settings


class MessageListView(ListView):
    """

    Returns the message list for this user. This is a list contacts
    which at the top has the user that the last conversation was with. This is
    an imitation of the iPhone SMS functionality.

    """
    page=1
    paginate_by=50
    template_name='umessages/message_list.html'
    extra_context={}
    context_object_name = 'message_list'

    def get_context_data(self, **kwargs):
        context = super(MessageListView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get_queryset(self):
        return MessageContact.objects.get_contacts_for(self.request.user)


class MessageDetailListView(MessageListView):
    """

    Returns a conversation between two users

    """
    template_name='umessages/message_detail.html'

    def get_context_data(self, **kwargs):
        context = super(MessageDetailListView, self).get_context_data(**kwargs)
        context['recipient'] = self.recipient
        return context

    def get_queryset(self):
        username = self.kwargs['username']
        self.recipient = get_object_or_404(get_user_model(),
                                  username__iexact=username)
        queryset = Message.objects.get_conversation_between(self.request.user,
                                                        self.recipient)
        self._update_unread_messages(queryset)
        return queryset

    def _update_unread_messages(self, queryset):
        message_pks = [m.pk for m in queryset]
        unread_list = MessageRecipient.objects.filter(message__in=message_pks,
                                                  user=self.request.user,
                                                  read_at__isnull=True)
        now = get_datetime_now()
        unread_list.update(read_at=now)


@login_required
def message_compose(request, recipients=None, compose_form=ComposeForm,
                    success_url=None, template_name="umessages/message_form.html",
                    recipient_filter=None, extra_context=None):
    """
    Compose a new message

    :recipients:
        String containing the usernames to whom the message is send to. Can be
        multiple username by seperating them with a ``+`` sign.

    :param compose_form:
        The form that is used for getting neccesary information. Defaults to
        :class:`ComposeForm`.

    :param success_url:
        String containing the named url which to redirect to after successfull
        sending a message. Defaults to ``userena_umessages_list`` if there are
        multiple recipients. If there is only one recipient, will redirect to
        ``userena_umessages_detail`` page, showing the conversation.

    :param template_name:
        String containing the name of the template that is used.

    :param recipient_filter:
        A list of :class:`User` that don"t want to receive any messages.

    :param extra_context:
        Dictionary with extra variables supplied to the template.

    **Context**

    ``form``
        The form that is used.

    """
    initial_data = dict()

    if recipients:
        username_list = [r.strip() for r in recipients.split("+")]
        recipients = [u for u in get_user_model().objects.filter(username__in=username_list)]
        initial_data["to"] = recipients

    form = compose_form(initial=initial_data)
    if request.method == "POST":
        form = compose_form(request.POST)
        if form.is_valid():
            requested_redirect = request.REQUEST.get("next", False)

            message = form.save(request.user)
            recipients = form.cleaned_data['to']

            if userena_settings.USERENA_USE_MESSAGES:
                messages.success(request, _('Message is sent.'),
                                 fail_silently=True)

            requested_redirect = request.REQUEST.get(REDIRECT_FIELD_NAME,
                                                     False)

            # Redirect mechanism
            redirect_to = reverse('userena_umessages_list')
            if requested_redirect: redirect_to = requested_redirect
            elif success_url: redirect_to = success_url
            elif len(recipients) == 1:
                redirect_to = reverse('userena_umessages_detail',
                                      kwargs={'username': recipients[0].username})
            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context["form"] = form
    extra_context["recipients"] = recipients
    return render(request, template_name, extra_context)

@login_required
@require_http_methods(["POST"])
def message_remove(request, undo=False):
    """
    A ``POST`` to remove messages.

    :param undo:
        A Boolean that if ``True`` unremoves messages.

    POST can have the following keys:

        ``message_pks``
            List of message id's that should be deleted.

        ``next``
            String containing the URI which to redirect to after the keys are
            removed. Redirect defaults to the inbox view.

    The ``next`` value can also be supplied in the URI with ``?next=<value>``.

    """
    message_pks = request.POST.getlist('message_pks')
    redirect_to = request.REQUEST.get('next', False)

    if message_pks:
        # Check that all values are integers.
        valid_message_pk_list = set()
        for pk in message_pks:
            try: valid_pk = int(pk)
            except (TypeError, ValueError): pass
            else:
                valid_message_pk_list.add(valid_pk)

        # Delete all the messages, if they belong to the user.
        now = get_datetime_now()
        changed_message_list = set()
        for pk in valid_message_pk_list:
            message = get_object_or_404(Message, pk=pk)

            # Check if the user is the owner
            if message.sender == request.user:
                if undo:
                    message.sender_deleted_at = None
                else:
                    message.sender_deleted_at = now
                message.save()
                changed_message_list.add(message.pk)

            # Check if the user is a recipient of the message
            if request.user in message.recipients.all():
                mr = message.messagerecipient_set.get(user=request.user,
                                                      message=message)
                if undo:
                    mr.deleted_at = None
                else:
                    mr.deleted_at = now
                mr.save()
                changed_message_list.add(message.pk)

        # Send messages
        if (len(changed_message_list) > 0) and userena_settings.USERENA_USE_MESSAGES:
            if undo:
                message = ungettext('Message is succesfully restored.',
                                    'Messages are succesfully restored.',
                                    len(changed_message_list))
            else:
                message = ungettext('Message is successfully removed.',
                                    'Messages are successfully removed.',
                                    len(changed_message_list))

            messages.success(request, message, fail_silently=True)

    if redirect_to: return redirect(redirect_to)
    else: return redirect(reverse('userena_umessages_list'))

########NEW FILE########
__FILENAME__ = decorators
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.decorators import available_attrs

from userena import settings as userena_settings

from django.utils.functional import wraps

def secure_required(view_func):
    """
    Decorator to switch an url from http to https.

    If a view is accessed through http and this decorator is applied to that
    view, than it will return a permanent redirect to the secure (https)
    version of the same view.

    The decorator also must check that ``USERENA_USE_HTTPS`` is enabled. If
    disabled, it should not redirect to https because the project doesn't
    support it.

    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.is_secure():
            if userena_settings.USERENA_USE_HTTPS:
                request_url = request.build_absolute_uri(request.get_full_path())
                secure_url = request_url.replace('http://', 'https://')
                return HttpResponsePermanentRedirect(secure_url)
        return view_func(request, *args, **kwargs)
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate

try:
    from hashlib import sha1 as sha_constructor
except ImportError:
    from django.utils.hashcompat import sha_constructor

from userena import settings as userena_settings
from userena.models import UserenaSignup
from userena.utils import get_profile_model, get_user_model

import random

attrs_dict = {'class': 'required'}

USERNAME_RE = r'^[\.\w]+$'

class SignupForm(forms.Form):
    """
    Form for creating a new user account.

    Validates that the requested username and e-mail is not already in use.
    Also requires the password to be entered twice.

    """
    username = forms.RegexField(regex=USERNAME_RE,
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_("Username"),
                                error_messages={'invalid': _('Username must contain only letters, numbers, dots and underscores.')})
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_("Email"))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict,
                                                           render_value=False),
                                label=_("Create password"))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict,
                                                           render_value=False),
                                label=_("Repeat password"))

    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already in use.
        Also validates that the username is not listed in
        ``USERENA_FORBIDDEN_USERNAMES`` list.

        """
        try:
            user = get_user_model().objects.get(username__iexact=self.cleaned_data['username'])
        except get_user_model().DoesNotExist:
            pass
        else:
            if userena_settings.USERENA_ACTIVATION_REQUIRED and UserenaSignup.objects.filter(user__username__iexact=self.cleaned_data['username']).exclude(activation_key=userena_settings.USERENA_ACTIVATED):
                raise forms.ValidationError(_('This username is already taken but not confirmed. Please check your email for verification steps.'))
            raise forms.ValidationError(_('This username is already taken.'))
        if self.cleaned_data['username'].lower() in userena_settings.USERENA_FORBIDDEN_USERNAMES:
            raise forms.ValidationError(_('This username is not allowed.'))
        return self.cleaned_data['username']

    def clean_email(self):
        """ Validate that the e-mail address is unique. """
        if get_user_model().objects.filter(email__iexact=self.cleaned_data['email']):
            if userena_settings.USERENA_ACTIVATION_REQUIRED and UserenaSignup.objects.filter(user__email__iexact=self.cleaned_data['email']).exclude(activation_key=userena_settings.USERENA_ACTIVATED):
                raise forms.ValidationError(_('This email is already in use but not confirmed. Please check your email for verification steps.'))
            raise forms.ValidationError(_('This email is already in use. Please supply a different email.'))
        return self.cleaned_data['email']

    def clean(self):
        """
        Validates that the values entered into the two password fields match.
        Note that an error here will end up in ``non_field_errors()`` because
        it doesn't apply to a single field.

        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_('The two password fields didn\'t match.'))
        return self.cleaned_data

    def save(self):
        """ Creates a new user and account. Returns the newly created user. """
        username, email, password = (self.cleaned_data['username'],
                                     self.cleaned_data['email'],
                                     self.cleaned_data['password1'])

        new_user = UserenaSignup.objects.create_user(username,
                                                     email,
                                                     password,
                                                     not userena_settings.USERENA_ACTIVATION_REQUIRED,
                                                     userena_settings.USERENA_ACTIVATION_REQUIRED)
        return new_user

class SignupFormOnlyEmail(SignupForm):
    """
    Form for creating a new user account but not needing a username.

    This form is an adaptation of :class:`SignupForm`. It's used when
    ``USERENA_WITHOUT_USERNAME`` setting is set to ``True``. And thus the user
    is not asked to supply an username, but one is generated for them. The user
    can than keep sign in by using their email.

    """
    def __init__(self, *args, **kwargs):
        super(SignupFormOnlyEmail, self).__init__(*args, **kwargs)
        del self.fields['username']

    def save(self):
        """ Generate a random username before falling back to parent signup form """
        while True:
            username = sha_constructor(str(random.random())).hexdigest()[:5]
            try:
                get_user_model().objects.get(username__iexact=username)
            except get_user_model().DoesNotExist: break

        self.cleaned_data['username'] = username
        return super(SignupFormOnlyEmail, self).save()

class SignupFormTos(SignupForm):
    """ Add a Terms of Service button to the ``SignupForm``. """
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={'required': _('You must agree to the terms to register.')})

def identification_field_factory(label, error_required):
    """
    A simple identification field factory which enable you to set the label.

    :param label:
        String containing the label for this field.

    :param error_required:
        String containing the error message if the field is left empty.

    """
    return forms.CharField(label=label,
                           widget=forms.TextInput(attrs=attrs_dict),
                           max_length=75,
                           error_messages={'required': _("%(error)s") % {'error': error_required}})

class AuthenticationForm(forms.Form):
    """
    A custom form where the identification can be a e-mail address or username.

    """
    identification = identification_field_factory(_(u"Email or username"),
                                                  _(u"Either supply us with your email or username."))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput(attrs=attrs_dict, render_value=False))
    remember_me = forms.BooleanField(widget=forms.CheckboxInput(),
                                     required=False,
                                     label=_(u'Remember me for %(days)s') % {'days': _(userena_settings.USERENA_REMEMBER_ME_DAYS[0])})

    def __init__(self, *args, **kwargs):
        """ A custom init because we need to change the label if no usernames is used """
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        # Dirty hack, somehow the label doesn't get translated without declaring
        # it again here.
        self.fields['remember_me'].label = _(u'Remember me for %(days)s') % {'days': _(userena_settings.USERENA_REMEMBER_ME_DAYS[0])}
        if userena_settings.USERENA_WITHOUT_USERNAMES:
            self.fields['identification'] = identification_field_factory(_(u"Email"),
                                                                         _(u"Please supply your email."))

    def clean(self):
        """
        Checks for the identification and password.

        If the combination can't be found will raise an invalid sign in error.

        """
        identification = self.cleaned_data.get('identification')
        password = self.cleaned_data.get('password')

        if identification and password:
            user = authenticate(identification=identification, password=password)
            if user is None:
                raise forms.ValidationError(_(u"Please enter a correct username or email and password. Note that both fields are case-sensitive."))
        return self.cleaned_data

class ChangeEmailForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_(u"New email"))

    def __init__(self, user, *args, **kwargs):
        """
        The current ``user`` is needed for initialisation of this form so
        that we can check if the email address is still free and not always
        returning ``True`` for this query because it's the users own e-mail
        address.

        """
        super(ChangeEmailForm, self).__init__(*args, **kwargs)
        if not isinstance(user, get_user_model()):
            raise TypeError("user must be an instance of %s" % get_user_model().__name__)
        else: self.user = user

    def clean_email(self):
        """ Validate that the email is not already registered with another user """
        if self.cleaned_data['email'].lower() == self.user.email:
            raise forms.ValidationError(_(u'You\'re already known under this email.'))
        if get_user_model().objects.filter(email__iexact=self.cleaned_data['email']).exclude(email__iexact=self.user.email):
            raise forms.ValidationError(_(u'This email is already in use. Please supply a different email.'))
        return self.cleaned_data['email']

    def save(self):
        """
        Save method calls :func:`user.change_email()` method which sends out an
        email with an verification key to verify and with it enable this new
        email address.

        """
        return self.user.userena_signup.change_email(self.cleaned_data['email'])

class EditProfileForm(forms.ModelForm):
    """ Base form used for fields that are always required """
    first_name = forms.CharField(label=_(u'First name'),
                                 max_length=30,
                                 required=False)
    last_name = forms.CharField(label=_(u'Last name'),
                                max_length=30,
                                required=False)

    def __init__(self, *args, **kw):
        super(EditProfileForm, self).__init__(*args, **kw)
        # Put the first and last name at the top
        new_order = self.fields.keyOrder[:-2]
        new_order.insert(0, 'first_name')
        new_order.insert(1, 'last_name')
        self.fields.keyOrder = new_order

    class Meta:
        model = get_profile_model()
        exclude = ['user']

    def save(self, force_insert=False, force_update=False, commit=True):
        profile = super(EditProfileForm, self).save(commit=commit)
        # Save first and last name
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        return profile

########NEW FILE########
__FILENAME__ = mail
# -*- coding: utf-8 -*-
import re
from StringIO import StringIO

from django.utils.translation import ugettext as _
from django.core.mail import EmailMultiAlternatives

from html2text import html2text as html2text_orig


LINK_RE = re.compile(r"https?://([^ \n]+\n)+[^ \n]+", re.MULTILINE)
def html2text(html):
    """Use html2text but repair newlines cutting urls.
    Need to use this hack until
    https://github.com/aaronsw/html2text/issues/#issue/7 is not fixed"""
    txt = html2text_orig(html)
    links = list(LINK_RE.finditer(txt))
    out = StringIO()
    pos = 0
    for l in links:
        out.write(txt[pos:l.start()])
        out.write(l.group().replace('\n', ''))
        pos = l.end()
    out.write(txt[pos:])
    return out.getvalue()

def send_mail(subject, message_plain, message_html, email_from, email_to,
              custom_headers={}, attachments=()):
    """
    Build the email as a multipart message containing
    a multipart alternative for text (plain, HTML) plus
    all the attached files.
    """
    if not message_plain and not message_html:
        raise ValueError(_("Either message_plain or message_html should be not None"))

    if not message_plain:
        message_plain = html2text(message_html)

    message = {}

    message['subject'] = subject
    message['body'] = message_plain
    message['from_email'] = email_from
    message['to'] = email_to
    if attachments:
        message['attachments'] = attachments
    if custom_headers:
        message['headers'] = custom_headers

    msg = EmailMultiAlternatives(**message)
    if message_html:
        msg.attach_alternative(message_html, "text/html")
    msg.send()


def wrap_attachment():
    pass
########NEW FILE########
__FILENAME__ = check_permissions
from django.core.management.base import NoArgsCommand, BaseCommand
from optparse import make_option

from userena.models import UserenaSignup

class Command(NoArgsCommand):
    """
    For unknown reason, users can get wrong permissions.
    This command checks that all permissions are correct.

    """
    option_list = BaseCommand.option_list + (
        make_option('--no-output',
            action='store_false',
            dest='output',
            default=True,
            help='Hide informational output.'),
        make_option('--test',
            action='store_true',
            dest='test',
            default=False,
            help="Displays that it's testing management command. Don't use it yourself."),
        )
    
    help = 'Check that user permissions are correct.'
    def handle_noargs(self, **options):
        permissions, users, warnings  = UserenaSignup.objects.check_permissions()
        output = options.pop("output")
        test = options.pop("test")
        if test:
            self.stdout.write(40 * ".")
            self.stdout.write("\nChecking permission management command. Ignore output..\n\n")
        if output:
            for p in permissions:
                self.stdout.write("Added permission: %s\n" % p)

            for u in users:
                self.stdout.write("Changed permissions for user: %s\n" % u)

            for w in warnings:
                self.stdout.write("WARNING: %s\n" %w)

        if test:
            self.stdout.write("\nFinished testing permissions command.. continuing..\n")

########NEW FILE########
__FILENAME__ = clean_expired
from django.core.management.base import NoArgsCommand

from userena.models import UserenaSignup

class Command(NoArgsCommand):
    """
    Search for users that still haven't verified their email after
    ``USERENA_ACTIVATION_DAYS`` and delete them.

    """
    help = 'Deletes expired users.'
    def handle_noargs(self, **options):
        users = UserenaSignup.objects.delete_expired_users()

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import UserManager, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.conf import settings

from userena import settings as userena_settings
from userena.utils import generate_sha1, get_profile_model, get_datetime_now, \
    get_user_model
from userena import signals as userena_signals

from guardian.shortcuts import assign_perm, get_perms


import re, datetime

SHA1_RE = re.compile('^[a-f0-9]{40}$')

ASSIGNED_PERMISSIONS = {
    'profile':
        (('view_profile', 'Can view profile'),
         ('change_profile', 'Can change profile'),
         ('delete_profile', 'Can delete profile')),
    'user':
        (('change_user', 'Can change user'),
         ('delete_user', 'Can delete user'))
}

class UserenaManager(UserManager):
    """ Extra functionality for the Userena model. """

    def create_user(self, username, email, password, active=False,
                    send_email=True):
        """
        A simple wrapper that creates a new :class:`User`.

        :param username:
            String containing the username of the new user.

        :param email:
            String containing the email address of the new user.

        :param password:
            String containing the password for the new user.

        :param active:
            Boolean that defines if the user requires activation by clicking
            on a link in an e-mail. Defaults to ``False``.

        :param send_email:
            Boolean that defines if the user should be sent an email. You could
            set this to ``False`` when you want to create a user in your own
            code, but don't want the user to activate through email.

        :return: :class:`User` instance representing the new user.

        """
        now = get_datetime_now()

        new_user = get_user_model().objects.create_user(
            username, email, password)
        new_user.is_active = active
        new_user.save()

        userena_profile = self.create_userena_profile(new_user)

        # All users have an empty profile
        profile_model = get_profile_model()
        try:
            new_profile = new_user.get_profile()
        except profile_model.DoesNotExist:
            new_profile = profile_model(user=new_user)
            new_profile.save(using=self._db)

        # Give permissions to view and change profile
        for perm in ASSIGNED_PERMISSIONS['profile']:
            assign_perm(perm[0], new_user, new_profile)

        # Give permissions to view and change itself
        for perm in ASSIGNED_PERMISSIONS['user']:
            assign_perm(perm[0], new_user, new_user)

        if send_email:
            userena_profile.send_activation_email()

        return new_user

    def create_userena_profile(self, user):
        """
        Creates an :class:`UserenaSignup` instance for this user.

        :param user:
            Django :class:`User` instance.

        :return: The newly created :class:`UserenaSignup` instance.

        """
        if isinstance(user.username, unicode):
            user.username = user.username.encode('utf-8')
        salt, activation_key = generate_sha1(user.username)

        return self.create(user=user,
                           activation_key=activation_key)

    def reissue_activation(self, activation_key):
        """
        Creates a new ``activation_key`` resetting activation timeframe when
        users let the previous key expire.

        :param activation_key:
            String containing the secret SHA1 activation key.

        """
        try:
            userena = self.get(activation_key=activation_key)
        except self.model.DoesNotExist:
            return False
        try:
            salt, new_activation_key = generate_sha1(userena.user.username)
            userena.activation_key = new_activation_key
            userena.save(using=self._db)
            userena.user.date_joined = get_datetime_now()
            userena.user.save(using=self._db)
            userena.send_activation_email()
            return True
        except Exception:
            return False

    def activate_user(self, activation_key):
        """
        Activate an :class:`User` by supplying a valid ``activation_key``.

        If the key is valid and an user is found, activates the user and
        return it. Also sends the ``activation_complete`` signal.

        :param activation_key:
            String containing the secret SHA1 for a valid activation.

        :return:
            The newly activated :class:`User` or ``False`` if not successful.

        """
        if SHA1_RE.search(activation_key):
            try:
                userena = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not userena.activation_key_expired():
                userena.activation_key = userena_settings.USERENA_ACTIVATED
                user = userena.user
                user.is_active = True
                userena.save(using=self._db)
                user.save(using=self._db)

                # Send the activation_complete signal
                userena_signals.activation_complete.send(sender=None,
                                                         user=user)

                return user
        return False

    def check_expired_activation(self, activation_key):
        """
        Check if ``activation_key`` is still valid.

        Raises a ``self.model.DoesNotExist`` exception if key is not present or
         ``activation_key`` is not a valid string

        :param activation_key:
            String containing the secret SHA1 for a valid activation.

        :return:
            True if the ket has expired, False if still valid.

        """
        if SHA1_RE.search(activation_key):
            userena = self.get(activation_key=activation_key)
            return userena.activation_key_expired()
        raise self.model.DoesNotExist

    def confirm_email(self, confirmation_key):
        """
        Confirm an email address by checking a ``confirmation_key``.

        A valid ``confirmation_key`` will set the newly wanted e-mail
        address as the current e-mail address. Returns the user after
        success or ``False`` when the confirmation key is
        invalid. Also sends the ``confirmation_complete`` signal.

        :param confirmation_key:
            String containing the secret SHA1 that is used for verification.

        :return:
            The verified :class:`User` or ``False`` if not successful.

        """
        if SHA1_RE.search(confirmation_key):
            try:
                userena = self.get(email_confirmation_key=confirmation_key,
                                   email_unconfirmed__isnull=False)
            except self.model.DoesNotExist:
                return False
            else:
                user = userena.user
                old_email = user.email
                user.email = userena.email_unconfirmed
                userena.email_unconfirmed, userena.email_confirmation_key = '',''
                userena.save(using=self._db)
                user.save(using=self._db)

                # Send the confirmation_complete signal
                userena_signals.confirmation_complete.send(sender=None,
                                                           user=user,
                                                           old_email=old_email)

                return user
        return False

    def delete_expired_users(self):
        """
        Checks for expired users and delete's the ``User`` associated with
        it. Skips if the user ``is_staff``.

        :return: A list containing the deleted users.

        """
        deleted_users = []
        for user in get_user_model().objects.filter(is_staff=False,
                                                    is_active=False):
            if user.userena_signup.activation_key_expired():
                deleted_users.append(user)
                user.delete()
        return deleted_users

    def check_permissions(self):
        """
        Checks that all permissions are set correctly for the users.

        :return: A set of users whose permissions was wrong.

        """
        # Variable to supply some feedback
        changed_permissions = []
        changed_users = []
        warnings = []

        # Check that all the permissions are available.
        for model, perms in ASSIGNED_PERMISSIONS.items():
            if model == 'profile':
                model_obj = get_profile_model()
            else: model_obj = get_user_model()

            model_content_type = ContentType.objects.get_for_model(model_obj)

            for perm in perms:
                try:
                    Permission.objects.get(codename=perm[0],
                                           content_type=model_content_type)
                except Permission.DoesNotExist:
                    changed_permissions.append(perm[1])
                    Permission.objects.create(name=perm[1],
                                              codename=perm[0],
                                              content_type=model_content_type)

        # it is safe to rely on settings.ANONYMOUS_USER_ID since it is a
        # requirement of django-guardian
        for user in get_user_model().objects.exclude(id=settings.ANONYMOUS_USER_ID):
            try:
                user_profile = user.get_profile()
            except ObjectDoesNotExist:
                warnings.append(_("No profile found for %(username)s") \
                                    % {'username': user.username})
            else:
                all_permissions = get_perms(user, user_profile) + get_perms(user, user)

                for model, perms in ASSIGNED_PERMISSIONS.items():
                    if model == 'profile':
                        perm_object = user.get_profile()
                    else: perm_object = user

                    for perm in perms:
                        if perm[0] not in all_permissions:
                            assign_perm(perm[0], user, perm_object)
                            changed_users.append(user)

        return (changed_permissions, changed_users, warnings)

class UserenaBaseProfileManager(models.Manager):
    """ Manager for :class:`UserenaProfile` """
    def get_visible_profiles(self, user=None):
        """
        Returns all the visible profiles available to this user.

        For now keeps it simple by just applying the cases when a user is not
        active, a user has it's profile closed to everyone or a user only
        allows registered users to view their profile.

        :param user:
            A Django :class:`User` instance.

        :return:
            All profiles that are visible to this user.

        """
        profiles = self.all()

        filter_kwargs = {'user__is_active': True}

        profiles = profiles.filter(**filter_kwargs)
        if user and isinstance(user, AnonymousUser):
            profiles = profiles.exclude(Q(privacy='closed') | Q(privacy='registered'))
        else: profiles = profiles.exclude(Q(privacy='closed'))
        return profiles

########NEW FILE########
__FILENAME__ = middleware
from django.utils import translation
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable

from userena import settings as userena_settings

class UserenaLocaleMiddleware(object):
    """
    Set the language by looking at the language setting in the profile.

    It doesn't override the cookie that is set by Django so a user can still
    switch languages depending if the cookie is set.

    """
    def process_request(self, request):
        lang_cookie = request.session.get(settings.LANGUAGE_COOKIE_NAME)
        if not lang_cookie:
            if request.user.is_authenticated():
                try:
                    profile = request.user.get_profile()
                except (ObjectDoesNotExist, SiteProfileNotAvailable):
                    profile = False

                if profile:
                    try:
                        lang = getattr(profile, userena_settings.USERENA_LANGUAGE_FIELD)
                        translation.activate(lang)
                        request.LANGUAGE_CODE = translation.get_language()
                    except AttributeError: pass

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from userena.utils import user_model_label

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'UserenaSignup'
        db.create_table('userena_userenasignup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name=u'userena_signup', unique=True, to=orm[user_model_label])),
            ('last_active', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('activation_key', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('activation_notification_send', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('email_unconfirmed', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('email_confirmation_key', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('email_confirmation_key_created', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('userena', ['UserenaSignup'])


    def backwards(self, orm):

        # Deleting model 'UserenaSignup'
        db.delete_table('userena_userenasignup')


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
        'userena.userenasignup': {
            'Meta': {'object_name': 'UserenaSignup'},
            'activation_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'activation_notification_send': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email_confirmation_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'email_confirmation_key_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'email_unconfirmed': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_active': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'userena_signup'", 'unique': 'True', 'to': "orm['%s']" % user_model_label})
        }
    }

    complete_apps = ['userena']

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from easy_thumbnails.fields import ThumbnailerImageField
from guardian.shortcuts import get_perms
from userena import settings as userena_settings
from userena.managers import UserenaManager, UserenaBaseProfileManager
from userena.utils import get_gravatar, generate_sha1, get_protocol, \
    get_datetime_now, get_user_model, user_model_label
import datetime
from .mail import send_mail


PROFILE_PERMISSIONS = (
            ('view_profile', 'Can view profile'),
)


def upload_to_mugshot(instance, filename):
    """
    Uploads a mugshot for a user to the ``USERENA_MUGSHOT_PATH`` and saving it
    under unique hash for the image. This is for privacy reasons so others
    can't just browse through the mugshot directory.

    """
    extension = filename.split('.')[-1].lower()
    salt, hash = generate_sha1(instance.id)
    path = userena_settings.USERENA_MUGSHOT_PATH % {'username': instance.user.username,
                                                    'id': instance.user.id,
                                                    'date': instance.user.date_joined,
                                                    'date_now': get_datetime_now().date()}
    return '%(path)s%(hash)s.%(extension)s' % {'path': path,
                                               'hash': hash[:10],
                                               'extension': extension}


class UserenaSignup(models.Model):
    """
    Userena model which stores all the necessary information to have a full
    functional user implementation on your Django website.

    """
    user = models.OneToOneField(user_model_label,
                                verbose_name=_('user'),
                                related_name='userena_signup')

    last_active = models.DateTimeField(_('last active'),
                                       blank=True,
                                       null=True,
                                       help_text=_('The last date that the user was active.'))

    activation_key = models.CharField(_('activation key'),
                                      max_length=40,
                                      blank=True)

    activation_notification_send = models.BooleanField(_('notification send'),
                                                       default=False,
                                                       help_text=_('Designates whether this user has already got a notification about activating their account.'))

    email_unconfirmed = models.EmailField(_('unconfirmed email address'),
                                          blank=True,
                                          help_text=_('Temporary email address when the user requests an email change.'))

    email_confirmation_key = models.CharField(_('unconfirmed email verification key'),
                                              max_length=40,
                                              blank=True)

    email_confirmation_key_created = models.DateTimeField(_('creation date of email confirmation key'),
                                                          blank=True,
                                                          null=True)

    objects = UserenaManager()

    class Meta:
        verbose_name = _('userena registration')
        verbose_name_plural = _('userena registrations')

    def __unicode__(self):
        return '%s' % self.user.username

    def change_email(self, email):
        """
        Changes the email address for a user.

        A user needs to verify this new email address before it becomes
        active. By storing the new email address in a temporary field --
        ``temporary_email`` -- we are able to set this email address after the
        user has verified it by clicking on the verification URI in the email.
        This email gets send out by ``send_verification_email``.

        :param email:
            The new email address that the user wants to use.

        """
        self.email_unconfirmed = email

        salt, hash = generate_sha1(self.user.username)
        self.email_confirmation_key = hash
        self.email_confirmation_key_created = get_datetime_now()
        self.save()

        # Send email for activation
        self.send_confirmation_email()

    def send_confirmation_email(self):
        """
        Sends an email to confirm the new email address.

        This method sends out two emails. One to the new email address that
        contains the ``email_confirmation_key`` which is used to verify this
        this email address with :func:`UserenaUser.objects.confirm_email`.

        The other email is to the old email address to let the user know that
        a request is made to change this email address.

        """
        context = {'user': self.user,
                  'without_usernames': userena_settings.USERENA_WITHOUT_USERNAMES,
                  'new_email': self.email_unconfirmed,
                  'protocol': get_protocol(),
                  'confirmation_key': self.email_confirmation_key,
                  'site': Site.objects.get_current()}

        # Email to the old address, if present
        subject_old = render_to_string('userena/emails/confirmation_email_subject_old.txt',
                                       context)
        subject_old = ''.join(subject_old.splitlines())

        if userena_settings.USERENA_HTML_EMAIL:
            message_old_html = render_to_string('userena/emails/confirmation_email_message_old.html',
                                                context)
        else:
            message_old_html = None

        if (not userena_settings.USERENA_HTML_EMAIL or not message_old_html or
            userena_settings.USERENA_USE_PLAIN_TEMPLATE):
            message_old = render_to_string('userena/emails/confirmation_email_message_old.txt',
                                       context)
        else:
            message_old = None

        if self.user.email:
            send_mail(subject_old,
                      message_old,
                      message_old_html,
                      settings.DEFAULT_FROM_EMAIL,
                    [self.user.email])

        # Email to the new address
        subject_new = render_to_string('userena/emails/confirmation_email_subject_new.txt',
                                       context)
        subject_new = ''.join(subject_new.splitlines())

        if userena_settings.USERENA_HTML_EMAIL:
            message_new_html = render_to_string('userena/emails/confirmation_email_message_new.html',
                                                context)
        else:
            message_new_html = None

        if (not userena_settings.USERENA_HTML_EMAIL or not message_new_html or
            userena_settings.USERENA_USE_PLAIN_TEMPLATE):
            message_new = render_to_string('userena/emails/confirmation_email_message_new.txt',
                                       context)
        else:
            message_new = None

        send_mail(subject_new,
                  message_new,
                  message_new_html,
                  settings.DEFAULT_FROM_EMAIL,
                  [self.email_unconfirmed, ])

    def activation_key_expired(self):
        """
        Checks if activation key is expired.

        Returns ``True`` when the ``activation_key`` of the user is expired and
        ``False`` if the key is still valid.

        The key is expired when it's set to the value defined in
        ``USERENA_ACTIVATED`` or ``activation_key_created`` is beyond the
        amount of days defined in ``USERENA_ACTIVATION_DAYS``.

        """
        expiration_days = datetime.timedelta(days=userena_settings.USERENA_ACTIVATION_DAYS)
        expiration_date = self.user.date_joined + expiration_days
        if self.activation_key == userena_settings.USERENA_ACTIVATED:
            return True
        if get_datetime_now() >= expiration_date:
            return True
        return False

    def send_activation_email(self):
        """
        Sends a activation email to the user.

        This email is send when the user wants to activate their newly created
        user.

        """
        context = {'user': self.user,
                  'without_usernames': userena_settings.USERENA_WITHOUT_USERNAMES,
                  'protocol': get_protocol(),
                  'activation_days': userena_settings.USERENA_ACTIVATION_DAYS,
                  'activation_key': self.activation_key,
                  'site': Site.objects.get_current()}

        subject = render_to_string('userena/emails/activation_email_subject.txt',
                                   context)
        subject = ''.join(subject.splitlines())


        if userena_settings.USERENA_HTML_EMAIL:
            message_html = render_to_string('userena/emails/activation_email_message.html',
                                            context)
        else:
            message_html = None

        if (not userena_settings.USERENA_HTML_EMAIL or not message_html or
            userena_settings.USERENA_USE_PLAIN_TEMPLATE):
            message = render_to_string('userena/emails/activation_email_message.txt',
                                   context)
        else:
            message = None

        send_mail(subject,
                  message,
                  message_html,
                  settings.DEFAULT_FROM_EMAIL,
                  [self.user.email, ])


class UserenaBaseProfile(models.Model):
    """ Base model needed for extra profile functionality """
    PRIVACY_CHOICES = (
        ('open', _('Open')),
        ('registered', _('Registered')),
        ('closed', _('Closed')),
    )

    MUGSHOT_SETTINGS = {'size': (userena_settings.USERENA_MUGSHOT_SIZE,
                                 userena_settings.USERENA_MUGSHOT_SIZE),
                        'crop': userena_settings.USERENA_MUGSHOT_CROP_TYPE}

    mugshot = ThumbnailerImageField(_('mugshot'),
                                    blank=True,
                                    upload_to=upload_to_mugshot,
                                    resize_source=MUGSHOT_SETTINGS,
                                    help_text=_('A personal image displayed in your profile.'))

    privacy = models.CharField(_('privacy'),
                               max_length=15,
                               choices=PRIVACY_CHOICES,
                               default=userena_settings.USERENA_DEFAULT_PRIVACY,
                               help_text=_('Designates who can view your profile.'))

    objects = UserenaBaseProfileManager()


    class Meta:
        """
        Meta options making the model abstract and defining permissions.

        The model is ``abstract`` because it only supplies basic functionality
        to a more custom defined model that extends it. This way there is not
        another join needed.

        We also define custom permissions because we don't know how the model
        that extends this one is going to be called. So we don't know what
        permissions to check. For ex. if the user defines a profile model that
        is called ``MyProfile``, than the permissions would be
        ``add_myprofile`` etc. We want to be able to always check
        ``add_profile``, ``change_profile`` etc.

        """
        abstract = True
        permissions = PROFILE_PERMISSIONS

    def __unicode__(self):
        return 'Profile of %(username)s' % {'username': self.user.username}

    def get_mugshot_url(self):
        """
        Returns the image containing the mugshot for the user.

        The mugshot can be a uploaded image or a Gravatar.

        Gravatar functionality will only be used when
        ``USERENA_MUGSHOT_GRAVATAR`` is set to ``True``.

        :return:
            ``None`` when Gravatar is not used and no default image is supplied
            by ``USERENA_MUGSHOT_DEFAULT``.

        """
        # First check for a mugshot and if any return that.
        if self.mugshot:
            return self.mugshot.url

        # Use Gravatar if the user wants to.
        if userena_settings.USERENA_MUGSHOT_GRAVATAR:
            return get_gravatar(self.user.email,
                                userena_settings.USERENA_MUGSHOT_SIZE,
                                userena_settings.USERENA_MUGSHOT_DEFAULT)

        # Gravatar not used, check for a default image.
        else:
            if userena_settings.USERENA_MUGSHOT_DEFAULT not in ['404', 'mm',
                                                                'identicon',
                                                                'monsterid',
                                                                'wavatar']:
                return userena_settings.USERENA_MUGSHOT_DEFAULT
            else:
                return None

    def get_full_name_or_username(self):
        """
        Returns the full name of the user, or if none is supplied will return
        the username.

        Also looks at ``USERENA_WITHOUT_USERNAMES`` settings to define if it
        should return the username or email address when the full name is not
        supplied.

        :return:
            ``String`` containing the full name of the user. If no name is
            supplied it will return the username or email address depending on
            the ``USERENA_WITHOUT_USERNAMES`` setting.

        """
        user = self.user
        if user.first_name or user.last_name:
            # We will return this as translated string. Maybe there are some
            # countries that first display the last name.
            name = _("%(first_name)s %(last_name)s") % \
                {'first_name': user.first_name,
                 'last_name': user.last_name}
        else:
            # Fallback to the username if usernames are used
            if not userena_settings.USERENA_WITHOUT_USERNAMES:
                name = "%(username)s" % {'username': user.username}
            else:
                name = "%(email)s" % {'email': user.email}
        return name.strip()

    def can_view_profile(self, user):
        """
        Can the :class:`User` view this profile?

        Returns a boolean if a user has the rights to view the profile of this
        user.

        Users are divided into four groups:

            ``Open``
                Everyone can view your profile

            ``Closed``
                Nobody can view your profile.

            ``Registered``
                Users that are registered on the website and signed
                in only.

            ``Admin``
                Special cases like superadmin and the owner of the profile.

        Through the ``privacy`` field a owner of an profile can define what
        they want to show to whom.

        :param user:
            A Django :class:`User` instance.

        """
        # Simple cases first, we don't want to waste CPU and DB hits.
        # Everyone.
        if self.privacy == 'open':
            return True
        # Registered users.
        elif self.privacy == 'registered' \
        and isinstance(user, get_user_model()):
            return True

        # Checks done by guardian for owner and admins.
        elif 'view_profile' in get_perms(user, self):
            return True

        # Fallback to closed profile.
        return False


class UserenaLanguageBaseProfile(UserenaBaseProfile):
    """
    Extends the :class:`UserenaBaseProfile` with a language choice.

    Use this model in combination with ``UserenaLocaleMiddleware`` automatically
    set the language of users when they are signed in.

    """
    language = models.CharField(_('language'),
                                max_length=5,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE[:2],
                                help_text=_('Default language.'))

    class Meta:
        abstract = True
        permissions = PROFILE_PERMISSIONS

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'userena.runtests.settings'

import django
from django.conf import settings
from django.db.models import get_app

from django.test.utils import get_runner
from south.management.commands import patch_for_test_db_setup



def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, failfast=False)

    if len(sys.argv) > 1:
        test_modules = sys.argv[1:]
    elif len(sys.argv) == 1:
        test_modules = []
    else:
        print(usage())
        sys.exit(1)

    if django.VERSION >= (1, 6, 0):
        # this is a compat hack because in django>=1.6.0 you must provide
        # module like "userena.contrib.umessages" not "umessages"
        test_modules = [get_app(module_name).__name__[:-7] for module_name in test_modules]

    patch_for_test_db_setup()
    failures = test_runner.run_tests(test_modules or ['userena'])

    sys.exit(failures)

get_app

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
# Django settings for Userena demo project.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

import os
settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(settings_dir)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'private/development.db'),
    }
}

# Internationalization
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ugettext = lambda s: s
LANGUAGES = (
    ('en', ugettext('English')),
    ('nl', ugettext('Dutch')),
    ('fr', ugettext('French')),
    ('pl', ugettext('Polish')),
    ('pt', ugettext('Portugese')),
    ('pt-br', ugettext('Brazilian Portuguese')),
    ('es', ugettext('Spanish')),
    ('el', ugettext('Greek')),
)
LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, 'locale'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'public/media/')
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'public/static/')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'demo/static/'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_g-js)o8z#8=9pr1&amp;05h^1_#)91sbo-)g^(*=-+epxmt4kc9m#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'userena.middleware.UserenaLocaleMiddleware',
)

# Add the Guardian and userena authentication backends
AUTHENTICATION_BACKENDS = (
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# Settings used by Userena
LOGIN_REDIRECT_URL = '/accounts/%(username)s/'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/accounts/signout/'
AUTH_PROFILE_MODULE = 'profiles.Profile'
USERENA_DISABLE_PROFILE_LIST = True
USERENA_MUGSHOT_SIZE = 140

ROOT_URLCONF = 'urls'
WSGI_APPLICATION = 'demo.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'guardian',
    'south',
    'userena',
    'userena.contrib.umessages',
    'userena.tests.profiles',
)

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

# Needed for Django guardian
ANONYMOUS_USER_ID = -1

# Test runner
TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.conf import settings

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),

    # Demo Override the signup form with our own, which includes a
    # first and last name.
    # (r'^accounts/signup/$',
    #  'userena.views.signup',
    #  {'signup_form': SignupFormExtra}),

    (r'^accounts/', include('userena.urls')),
    (r'^messages/', include('userena.contrib.umessages.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
)

# Add media and static files
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



########NEW FILE########
__FILENAME__ = settings
# Userena settings file.
#
# Please consult the docs for more information about each setting.

from django.conf import settings
gettext = lambda s: s


USERENA_SIGNIN_AFTER_SIGNUP = getattr(settings,
                                      'USERENA_SIGNIN_AFTER_SIGNUP',
                                      False)

USERENA_REDIRECT_ON_SIGNOUT = getattr(settings,
                                      'USERENA_REDIRECT_ON_SIGNOUT',
                                      None)

USERENA_SIGNIN_REDIRECT_URL = getattr(settings,
                                      'USERENA_SIGNIN_REDIRECT_URL',
                                      '/accounts/%(username)s/')

USERENA_ACTIVATION_REQUIRED = getattr(settings,
                                      'USERENA_ACTIVATION_REQUIRED',
                                      True)

USERENA_ACTIVATION_DAYS = getattr(settings,
                                  'USERENA_ACTIVATION_DAYS',
                                  7)

USERENA_ACTIVATION_NOTIFY = getattr(settings,
                                    'USERENA_ACTIVATION_NOTIFY',
                                    True)

USERENA_ACTIVATION_NOTIFY_DAYS = getattr(settings,
                                         'USERENA_ACTIVATION_NOTIFY_DAYS',
                                         5)

USERENA_ACTIVATION_RETRY = getattr(settings,
                                    'USERENA_ACTIVATION_RETRY',
                                    False)

USERENA_ACTIVATED = getattr(settings,
                            'USERENA_ACTIVATED',
                            'ALREADY_ACTIVATED')

USERENA_REMEMBER_ME_DAYS = getattr(settings,
                                   'USERENA_REMEMBER_ME_DAYS',
                                   (gettext('a month'), 30))

USERENA_FORBIDDEN_USERNAMES = getattr(settings,
                                      'USERENA_FORBIDDEN_USERNAMES',
                                      ('signup', 'signout', 'signin',
                                       'activate', 'me', 'password'))

USERENA_USE_HTTPS = getattr(settings,
                            'USERENA_USE_HTTPS',
                            False)

USERENA_MUGSHOT_GRAVATAR = getattr(settings,
                                   'USERENA_MUGSHOT_GRAVATAR',
                                   True)

USERENA_MUGSHOT_GRAVATAR_SECURE = getattr(settings,
                                          'USERENA_MUGSHOT_GRAVATAR_SECURE',
                                          USERENA_USE_HTTPS)

USERENA_MUGSHOT_DEFAULT = getattr(settings,
                                  'USERENA_MUGSHOT_DEFAULT',
                                  'identicon')

USERENA_MUGSHOT_SIZE = getattr(settings,
                               'USERENA_MUGSHOT_SIZE',
                               80)

USERENA_MUGSHOT_CROP_TYPE = getattr(settings,
                                    'USERENA_MUGSHOT_CROP_TYPE',
                                    'smart')

USERENA_MUGSHOT_PATH = getattr(settings,
                               'USERENA_MUGSHOT_PATH',
                               'mugshots/')

USERENA_DEFAULT_PRIVACY = getattr(settings,
                                  'USERENA_DEFAULT_PRIVACY',
                                  'registered')

USERENA_DISABLE_PROFILE_LIST = getattr(settings,
                                       'USERENA_DISABLE_PROFILE_LIST',
                                       False)

USERENA_DISABLE_SIGNUP = getattr(settings,
                                 'USERENA_DISABLE_SIGNUP',
                                 False)

USERENA_USE_MESSAGES = getattr(settings,
                               'USERENA_USE_MESSAGES',
                               True)

USERENA_LANGUAGE_FIELD = getattr(settings,
                                 'USERENA_LANGUAGE_FIELD',
                                 'language')

USERENA_WITHOUT_USERNAMES = getattr(settings,
                                    'USERENA_WITHOUT_USERNAMES',
                                    False)

USERENA_PROFILE_DETAIL_TEMPLATE = getattr(
    settings, 'USERENA_PROFILE_DETAIL_TEMPLATE', 'userena/profile_detail.html')

USERENA_PROFILE_LIST_TEMPLATE = getattr(
    settings, 'USERENA_PROFILE_LIST_TEMPLATE', 'userena/profile_list.html')

USERENA_HIDE_EMAIL = getattr(settings, 'USERENA_HIDE_EMAIL', False)

USERENA_HTML_EMAIL = getattr(settings, 'USERENA_HTML_EMAIL', False)

USERENA_USE_PLAIN_TEMPLATE = getattr(settings, 'USERENA_USE_PLAIN_TEMPLATE', not USERENA_HTML_EMAIL)

USERENA_REGISTER_PROFILE = getattr(settings, 'USERENA_REGISTER_PROFILE', True)

USERENA_REGISTER_USER = getattr(settings, 'USERENA_REGISTER_USER', True)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

signup_complete = Signal(providing_args=["user",])
activation_complete = Signal(providing_args=["user",])
confirmation_complete = Signal(providing_args=["user","old_email"])
password_complete = Signal(providing_args=["user",])
email_change = Signal(providing_args=["user","prev_email","new_email"])
profile_change = Signal(providing_args=["user",])
account_signin = Signal(providing_args=["user",])
account_signout = Signal(providing_args=["user",])

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

from userena.models import UserenaBaseProfile
from userena.utils import user_model_label

import datetime

class Profile(UserenaBaseProfile):
    """ Default profile """
    GENDER_CHOICES = (
        (1, _('Male')),
        (2, _('Female')),
    )

    user = models.OneToOneField(user_model_label,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='profile')

    gender = models.PositiveSmallIntegerField(_('gender'),
                                              choices=GENDER_CHOICES,
                                              blank=True,
                                              null=True)
    website = models.URLField(_('website'), blank=True)
    location = models.CharField(_('location'), max_length=255, blank=True)
    about_me = models.TextField(_('about me'), blank=True)
    language = models.TextField(_('language'), blank=True)

class SecondProfile(UserenaBaseProfile):
    user = models.OneToOneField(user_model_label,
                                unique=True,
                                verbose_name=_('user'),
                                related_name='profile_second')

########NEW FILE########
__FILENAME__ = tests_decorators
from django.test import TestCase
from django.core.urlresolvers import reverse

from userena.utils import get_gravatar
from userena import settings as userena_settings

import re

class DecoratorTests(TestCase):
    """ Test the decorators """

    def test_secure_required(self):
        """
        Test that the ``secure_required`` decorator does a permanent redirect
        to a secured page.

        """
        userena_settings.USERENA_USE_HTTPS = True
        response = self.client.get(reverse('userena_signin'))

        # Test for the permanent redirect
        self.assertEqual(response.status_code, 301)

        # Test if the redirected url contains 'https'. Couldn't use
        # ``assertRedirects`` here because the redirected to page is
        # non-existant.
        self.assertTrue('https' in str(response))

        # Set back to the old settings
        userena_settings.USERENA_USE_HTTPS = False

########NEW FILE########
__FILENAME__ = tests_forms
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from userena import forms
from userena import settings as userena_settings
from userena.utils import get_user_model


class SignupFormTests(TestCase):
    """ Test the signup form. """
    fixtures = ['users']

    def test_signup_form(self):
        """
        Test that the ``SignupForm`` checks for unique usernames and unique
        e-mail addresses.

        """
        invalid_data_dicts = [
            # Non-alphanumeric username.
            {'data': {'username': 'foo@bar',
                      'email': 'foo@example.com',
                      'password': 'foo',
                      'password2': 'foo',
                      'tos': 'on'},
             'error': ('username', [_(u'Username must contain only letters, numbers, dots and underscores.')])},
            # Password is not the same
            {'data': {'username': 'katy-',
                      'email': 'katy@newexample.com',
                      'password1': 'foo',
                      'password2': 'foo2',
                      'tos': 'on'},
             'error': ('__all__', [_(u'The two password fields didn\'t match.')])},

            # Already taken username
            {'data': {'username': 'john',
                      'email': 'john@newexample.com',
                      'password1': 'foo',
                      'password2': 'foo',
                      'tos': 'on'},
             'error': ('username', [_(u'This username is already taken.')])},

            # Forbidden username
            {'data': {'username': 'SignUp',
                      'email': 'foo@example.com',
                      'password': 'foo',
                      'password2': 'foo2',
                      'tos': 'on'},
             'error': ('username', [_(u'This username is not allowed.')])},

            # Already taken email
            {'data': {'username': 'alice',
                      'email': 'john@example.com',
                      'password': 'foo',
                      'password2': 'foo',
                      'tos': 'on'},
             'error': ('email', [_(u'This email is already in use. Please supply a different email.')])},
        ]

        for invalid_dict in invalid_data_dicts:
            form = forms.SignupForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])


        # And finally, a valid form.
        form = forms.SignupForm(data={'username': 'foo.bla',
                                      'email': 'foo@example.com',
                                      'password1': 'foo',
                                      'password2': 'foo',
                                      'tos': 'on'})

        self.failUnless(form.is_valid())

class AuthenticationFormTests(TestCase):
    """ Test the ``AuthenticationForm`` """

    fixtures = ['users',]

    def test_signin_form(self):
        """
        Check that the ``SigninForm`` requires both identification and password

        """
        invalid_data_dicts = [
            {'data': {'identification': '',
                      'password': 'inhalefish'},
             'error': ('identification', [u'Either supply us with your email or username.'])},
            {'data': {'identification': 'john',
                      'password': 'inhalefish'},
             'error': ('__all__', [u'Please enter a correct username or email and password. Note that both fields are case-sensitive.'])}
        ]

        for invalid_dict in invalid_data_dicts:
            form = forms.AuthenticationForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

        valid_data_dicts = [
            {'identification': 'john',
             'password': 'blowfish'},
            {'identification': 'john@example.com',
             'password': 'blowfish'}
        ]

        for valid_dict in valid_data_dicts:
            form = forms.AuthenticationForm(valid_dict)
            self.failUnless(form.is_valid())

    def test_signin_form_email(self):
        """
        Test that the signin form has a different label is
        ``USERENA_WITHOUT_USERNAME`` is set to ``True``

        """
        userena_settings.USERENA_WITHOUT_USERNAMES = True

        form = forms.AuthenticationForm(data={'identification': "john",
                                              'password': "blowfish"})

        correct_label = "Email"
        self.assertEqual(form.fields['identification'].label,
                         correct_label)

        # Restore default settings
        userena_settings.USERENA_WITHOUT_USERNAMES = False

class SignupFormOnlyEmailTests(TestCase):
    """
    Test the :class:`SignupFormOnlyEmail`.

    This is the same form as :class:`SignupForm` but doesn't require an
    username for a successfull signup.

    """
    fixtures = ['users']

    def test_signup_form_only_email(self):
        """
        Test that the form has no username field. And that the username is
        generated in the save method

        """
        valid_data = {'email': 'hans@gretel.com',
                      'password1': 'blowfish',
                      'password2': 'blowfish'}

        form = forms.SignupFormOnlyEmail(data=valid_data)

        # Should have no username field
        self.failIf(form.fields.get('username', False))

        # Form should be valid.
        self.failUnless(form.is_valid())

        # Creates an unique username
        user = form.save()

        self.failUnless(len(user.username), 5)

class ChangeEmailFormTests(TestCase):
    """ Test the ``ChangeEmailForm`` """
    fixtures = ['users']

    def test_change_email_form(self):
        user = get_user_model().objects.get(pk=1)
        invalid_data_dicts = [
            # No change in e-mail address
            {'data': {'email': 'john@example.com'},
             'error': ('email', [u'You\'re already known under this email.'])},
            # An e-mail address used by another
            {'data': {'email': 'jane@example.com'},
             'error': ('email', [u'This email is already in use. Please supply a different email.'])},
        ]
        for invalid_dict in invalid_data_dicts:
            form = forms.ChangeEmailForm(user, data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

        # Test a valid post
        form = forms.ChangeEmailForm(user,
                                     data={'email': 'john@newexample.com'})
        self.failUnless(form.is_valid())

    def test_form_init(self):
        """ The form must be initialized with a ``User`` instance. """
        self.assertRaises(TypeError, forms.ChangeEmailForm, None)

class EditAccountFormTest(TestCase):
    """ Test the ``EditAccountForm`` """
    pass

########NEW FILE########
__FILENAME__ = tests_managers
from django.test import TestCase
from django.core import mail

from userena.models import UserenaSignup
from userena import settings as userena_settings
from userena.utils import get_user_model

from guardian.shortcuts import get_perms

import datetime, re

User = get_user_model()


class UserenaManagerTests(TestCase):
    """ Test the manager of Userena """
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}

    fixtures = ['users']

    def test_create_inactive_user(self):
        """
        Test the creation of a new user.

        ``UserenaSignup.create_inactive_user`` should create a new user that is
        not active. The user should get an ``activation_key`` that is used to
        set the user as active.

        Every user also has a profile, so this method should create an empty
        profile.

        """
        # Check that the fields are set.
        new_user = UserenaSignup.objects.create_user(**self.user_info)
        self.assertEqual(new_user.username, self.user_info['username'])
        self.assertEqual(new_user.email, self.user_info['email'])
        self.failUnless(new_user.check_password(self.user_info['password']))

        # User should be inactive
        self.failIf(new_user.is_active)

        # User has a valid SHA1 activation key
        self.failUnless(re.match('^[a-f0-9]{40}$', new_user.userena_signup.activation_key))

        # User now has an profile.
        self.failUnless(new_user.get_profile())

        # User should be saved
        self.failUnlessEqual(User.objects.filter(email=self.user_info['email']).count(), 1)

    def test_activation_valid(self):
        """
        Valid activation of an user.

        Activation of an user with a valid ``activation_key`` should activate
        the user and set a new invalid ``activation_key`` that is defined in
        the setting ``USERENA_ACTIVATED``.

        """
        user = UserenaSignup.objects.create_user(**self.user_info)
        active_user = UserenaSignup.objects.activate_user(user.userena_signup.activation_key)

        # The returned user should be the same as the one just created.
        self.failUnlessEqual(user, active_user)

        # The user should now be active.
        self.failUnless(active_user.is_active)

        # The user should have permission to view and change its profile
        self.failUnless('view_profile' in get_perms(active_user, active_user.get_profile()))
        self.failUnless('change_profile' in get_perms(active_user, active_user.get_profile()))

        # The activation key should be the same as in the settings
        self.assertEqual(active_user.userena_signup.activation_key,
                         userena_settings.USERENA_ACTIVATED)

    def test_activation_invalid(self):
        """
        Activation with a key that's invalid should make
        ``UserenaSignup.objects.activate_user`` return ``False``.

        """
        # Wrong key
        self.failIf(UserenaSignup.objects.activate_user('wrong_key'))

        # At least the right length
        invalid_key = 10 * 'a1b2'
        self.failIf(UserenaSignup.objects.activate_user(invalid_key))

    def test_activation_expired(self):
        """
        Activation with a key that's expired should also make
        ``UserenaSignup.objects.activation_user`` return ``False``.

        """
        user = UserenaSignup.objects.create_user(**self.user_info)

        # Set the date that the key is created a day further away than allowed
        user.date_joined -= datetime.timedelta(days=userena_settings.USERENA_ACTIVATION_DAYS + 1)
        user.save()

        # Try to activate the user
        UserenaSignup.objects.activate_user(user.userena_signup.activation_key)

        active_user = User.objects.get(username='alice')

        # UserenaSignup activation should have failed
        self.failIf(active_user.is_active)

        # The activation key should still be a hash
        self.assertEqual(user.userena_signup.activation_key,
                         active_user.userena_signup.activation_key)

    def test_confirmation_valid(self):
        """
        Confirmation of a new e-mail address with turns out to be valid.

        """
        new_email = 'john@newexample.com'
        user = User.objects.get(pk=1)
        user.userena_signup.change_email(new_email)

        # Confirm email
        confirmed_user = UserenaSignup.objects.confirm_email(user.userena_signup.email_confirmation_key)
        self.failUnlessEqual(user, confirmed_user)

        # Check the new email is set.
        self.failUnlessEqual(confirmed_user.email, new_email)

        # ``email_new`` and ``email_verification_key`` should be empty
        self.failIf(confirmed_user.userena_signup.email_unconfirmed)
        self.failIf(confirmed_user.userena_signup.email_confirmation_key)

    def test_confirmation_invalid(self):
        """
        Trying to confirm a new e-mail address when the ``confirmation_key``
        is invalid.

        """
        new_email = 'john@newexample.com'
        user = User.objects.get(pk=1)
        user.userena_signup.change_email(new_email)

        # Verify email with wrong SHA1
        self.failIf(UserenaSignup.objects.confirm_email('sha1'))

        # Correct SHA1, but non-existend in db.
        self.failIf(UserenaSignup.objects.confirm_email(10 * 'a1b2'))

    def test_delete_expired_users(self):
        """
        Test if expired users are deleted from the database.

        """
        expired_user = UserenaSignup.objects.create_user(**self.user_info)
        expired_user.date_joined -= datetime.timedelta(days=userena_settings.USERENA_ACTIVATION_DAYS + 1)
        expired_user.save()

        deleted_users = UserenaSignup.objects.delete_expired_users()

        self.failUnlessEqual(deleted_users[0].username, 'alice')

########NEW FILE########
__FILENAME__ = tests_middleware
from django.http import HttpRequest
from django.test import TestCase
from django.utils.importlib import import_module
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from userena.tests.profiles.models import Profile
from userena.middleware import UserenaLocaleMiddleware
from userena import settings as userena_settings
from userena.utils import get_user_model

User = get_user_model()


class UserenaLocaleMiddlewareTests(TestCase):
    """ Test the ``UserenaLocaleMiddleware`` """
    fixtures = ['users', 'profiles']

    def _get_request_with_user(self, user):
        """ Fake a request with an user """
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.method = 'GET'
        request.session = {}

        # Add user
        request.user = user
        return request

    def test_preference_user(self):
        """ Test the language preference of two users """
        users = ((1, 'nl'),
                 (2, 'en'))

        for pk, lang in users:
            user = User.objects.get(pk=pk)
            profile = user.get_profile()

            req = self._get_request_with_user(user)

            # Check that the user has this preference
            self.failUnlessEqual(profile.language, lang)

            # Request should have a ``LANGUAGE_CODE`` with dutch
            UserenaLocaleMiddleware().process_request(req)
            self.failUnlessEqual(req.LANGUAGE_CODE, lang)

    def test_without_profile(self):
        """ Middleware should do nothing when a user has no profile """
        # Delete the profile
        Profile.objects.get(pk=1).delete()
        user = User.objects.get(pk=1)

        # User shouldn't have a profile
        self.assertRaises(ObjectDoesNotExist, user.get_profile)

        req = self._get_request_with_user(user)
        UserenaLocaleMiddleware().process_request(req)

        self.failIf(hasattr(req, 'LANGUAGE_CODE'))

    def test_without_language_field(self):
        """ Middleware should do nothing if the profile has no language field """
        userena_settings.USERENA_LANGUAGE_FIELD = 'non_existant_language_field'
        user = User.objects.get(pk=1)

        req = self._get_request_with_user(user)

        # Middleware should do nothing
        UserenaLocaleMiddleware().process_request(req)
        self.failIf(hasattr(req, 'LANGUAGE_CODE'))

########NEW FILE########
__FILENAME__ = tests_models
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.core import mail
from django.conf import settings
from django.test import TestCase

from userena.models import UserenaSignup, upload_to_mugshot
from userena import settings as userena_settings
from userena.tests.profiles.models import Profile
from userena.utils import get_user_model

import datetime, hashlib, re

User = get_user_model()

MUGSHOT_RE = re.compile('^[a-f0-9]{40}$')

class UserenaSignupModelTests(TestCase):
    """ Test the model of UserenaSignup """
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}

    fixtures = ['users', 'profiles']

    def test_upload_mugshot(self):
        """
        Test the uploaded path of mugshots

        TODO: What if a image get's uploaded with no extension?

        """
        user = User.objects.get(pk=1)
        filename = 'my_avatar.png'
        path = upload_to_mugshot(user.get_profile(), filename)

        # Path should be changed from the original
        self.failIfEqual(filename, path)

        # Check if the correct path is returned
        MUGSHOT_RE = re.compile('^%(mugshot_path)s[a-f0-9]{10}.png$' %
                                {'mugshot_path': userena_settings.USERENA_MUGSHOT_PATH})

        self.failUnless(MUGSHOT_RE.search(path))

    def test_stringification(self):
        """
        Test the stringification of a ``UserenaSignup`` object. A
        "human-readable" representation of an ``UserenaSignup`` object.

        """
        signup = UserenaSignup.objects.get(pk=1)
        self.failUnlessEqual(signup.__unicode__(),
                             signup.user.username)

    def test_change_email(self):
        """ TODO """
        pass

    def test_activation_expired_account(self):
        """
        ``UserenaSignup.activation_key_expired()`` is ``True`` when the
        ``activation_key_created`` is more days ago than defined in
        ``USERENA_ACTIVATION_DAYS``.

        """
        user = UserenaSignup.objects.create_user(**self.user_info)
        user.date_joined -= datetime.timedelta(days=userena_settings.USERENA_ACTIVATION_DAYS + 1)
        user.save()

        user = User.objects.get(username='alice')
        self.failUnless(user.userena_signup.activation_key_expired())

    def test_activation_used_account(self):
        """
        An user cannot be activated anymore once the activation key is
        already used.

        """
        user = UserenaSignup.objects.create_user(**self.user_info)
        activated_user = UserenaSignup.objects.activate_user(user.userena_signup.activation_key)
        self.failUnless(activated_user.userena_signup.activation_key_expired())

    def test_activation_unexpired_account(self):
        """
        ``UserenaSignup.activation_key_expired()`` is ``False`` when the
        ``activation_key_created`` is within the defined timeframe.``

        """
        user = UserenaSignup.objects.create_user(**self.user_info)
        self.failIf(user.userena_signup.activation_key_expired())

    def test_activation_email(self):
        """
        When a new account is created, a activation e-mail should be send out
        by ``UserenaSignup.send_activation_email``.

        """
        new_user = UserenaSignup.objects.create_user(**self.user_info)
        self.failUnlessEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_info['email']])

    def test_plain_email(self):
        """
        If HTML emails are disabled, check that outgoing emails are not multipart
        """
        userena_settings.USERENA_HTML_EMAIL = False
        new_user = UserenaSignup.objects.create_user(**self.user_info)
        self.failUnlessEqual(len(mail.outbox), 1)
        self.assertEqual(unicode(mail.outbox[0].message()).find("multipart/alternative"),-1)

    def test_html_email(self):
        """
        If HTML emails are enabled, check outgoings emails are multipart and
        that different html and plain text templates are used
        """
        userena_settings.USERENA_HTML_EMAIL = True
        userena_settings.USERENA_USE_PLAIN_TEMPLATE = True

        new_user = UserenaSignup.objects.create_user(**self.user_info)

        # Reset configuration
        userena_settings.USERENA_HTML_EMAIL = False
        self.failUnlessEqual(len(mail.outbox), 1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("multipart/alternative")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("text/plain")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("text/html")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("<html>")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("<p>Thank you for signing up")>-1)
        self.assertFalse(mail.outbox[0].body.find("<p>Thank you for signing up")>-1)

    def test_generated_plain_email(self):
        """
        If HTML emails are enabled and plain text template are disabled,
        check outgoings emails are multipart and that plain text is generated
        from html body
        """
        userena_settings.USERENA_HTML_EMAIL = True
        userena_settings.USERENA_USE_PLAIN_TEMPLATE = False

        new_user = UserenaSignup.objects.create_user(**self.user_info)

        # Reset configuration
        userena_settings.USERENA_HTML_EMAIL = False
        userena_settings.USERENA_USE_PLAIN_TEMPLATE = True

        self.failUnlessEqual(len(mail.outbox), 1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("multipart/alternative")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("text/plain")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("text/html")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("<html>")>-1)
        self.assertTrue(unicode(mail.outbox[0].message()).find("<p>Thank you for signing up")>-1)
        self.assertTrue(mail.outbox[0].body.find("Thank you for signing up")>-1)

class BaseProfileModelTest(TestCase):
    """ Test the ``BaseProfile`` model """
    fixtures = ['users', 'profiles']

    def test_mugshot_url(self):
        """ The user has uploaded it's own mugshot. This should be returned. """
        profile = Profile.objects.get(pk=1)
        profile.mugshot = 'fake_image.png'
        profile.save()

        profile = Profile.objects.get(pk=1)
        self.failUnlessEqual(profile.get_mugshot_url(),
                             settings.MEDIA_URL + 'fake_image.png')

    def test_stringification(self):
        """ Profile should return a human-readable name as an object """
        profile = Profile.objects.get(pk=1)
        self.failUnlessEqual(profile.__unicode__(),
                             'Profile of %s' % profile.user.username)

    def test_get_mugshot_url_without_gravatar(self):
        """
        Test if the correct mugshot is returned for the user when
        ``USERENA_MUGSHOT_GRAVATAR`` is set to ``False``.

        """
        # This user has no mugshot, and gravatar is disabled. And to make
        # matters worse, there isn't even a default image.
        userena_settings.USERENA_MUGSHOT_GRAVATAR = False
        profile = Profile.objects.get(pk=1)
        self.failUnlessEqual(profile.get_mugshot_url(), None)

        # There _is_ a default image
        userena_settings.USERENA_MUGSHOT_DEFAULT = 'http://example.com'
        profile = Profile.objects.get(pk=1)
        self.failUnlessEqual(profile.get_mugshot_url(), 'http://example.com')

        # Settings back to default
        userena_settings.USERENA_MUGSHOT_GRAVATAR = True

    def test_get_mugshot_url_with_gravatar(self):
        """
        Test if the correct mugshot is returned when the user makes use of gravatar.

        """
        template = '//www.gravatar.com/avatar/%(hash)s?s=%(size)s&d=%(default)s'
        profile = Profile.objects.get(pk=1)

        gravatar_hash = hashlib.md5(profile.user.email).hexdigest()

        # Test with the default settings
        self.failUnlessEqual(profile.get_mugshot_url(),
                             template % {'hash': gravatar_hash,
                                         'size': userena_settings.USERENA_MUGSHOT_SIZE,
                                         'default': userena_settings.USERENA_MUGSHOT_DEFAULT})

        # Change userena settings
        userena_settings.USERENA_MUGSHOT_SIZE = 180
        userena_settings.USERENA_MUGSHOT_DEFAULT = '404'

        self.failUnlessEqual(profile.get_mugshot_url(),
                             template % {'hash': gravatar_hash,
                                         'size': userena_settings.USERENA_MUGSHOT_SIZE,
                                         'default': userena_settings.USERENA_MUGSHOT_DEFAULT})

        # Settings back to default
        userena_settings.USERENA_MUGSHOT_SIZE = 80
        userena_settings.USERENA_MUGSHOT_DEFAULT = 'identicon'

    def test_get_full_name_or_username(self):
        """ Test if the full name or username are returned correcly """
        user = User.objects.get(pk=1)
        profile = user.get_profile()

        # Profile #1 has a first and last name
        full_name = profile.get_full_name_or_username()
        self.failUnlessEqual(full_name, "John Doe")

        # Let's empty out his name, now we should get his username
        user.first_name = ''
        user.last_name = ''
        user.save()

        self.failUnlessEqual(profile.get_full_name_or_username(),
                             "john")

        # Finally, userena doesn't use any usernames, so we should return the
        # e-mail address.
        userena_settings.USERENA_WITHOUT_USERNAMES = True
        self.failUnlessEqual(profile.get_full_name_or_username(),
                             "john@example.com")
        userena_settings.USERENA_WITHOUT_USERNAMES = False

    def test_can_view_profile(self):
        """ Test if the user can see the profile with three type of users. """
        anon_user = AnonymousUser()
        super_user = User.objects.get(pk=1)
        reg_user = User.objects.get(pk=2)

        profile = Profile.objects.get(pk=1)

        # All users should be able to see a ``open`` profile.
        profile.privacy = 'open'
        self.failUnless(profile.can_view_profile(anon_user))
        self.failUnless(profile.can_view_profile(super_user))
        self.failUnless(profile.can_view_profile(reg_user))

        # Registered and super users should be able to see a ``registered``
        # profile.
        profile.privacy = 'registered'
        self.failIf(profile.can_view_profile(anon_user))
        self.failUnless(profile.can_view_profile(super_user))
        self.failUnless(profile.can_view_profile(reg_user))

        # Only superusers can see a closed profile.
        profile.privacy = 'closed'
        self.failIf(profile.can_view_profile(anon_user))
        self.failUnless(profile.can_view_profile(super_user))
        self.failIf(profile.can_view_profile(reg_user))

########NEW FILE########
__FILENAME__ = tests_utils
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable

from userena.utils import (get_gravatar, signin_redirect, get_profile_model,
                           get_protocol, get_user_model)
from userena import settings as userena_settings
from userena.models import UserenaBaseProfile

import hashlib

class UtilsTests(TestCase):
    """ Test the extra utils methods """
    fixtures = ['users']

    def test_get_gravatar(self):
        template = '//www.gravatar.com/avatar/%(hash)s?s=%(size)s&d=%(type)s'

        # The hash for alice@example.com
        hash = hashlib.md5('alice@example.com').hexdigest()

        # Check the defaults.
        self.failUnlessEqual(get_gravatar('alice@example.com'),
                             template % {'hash': hash,
                                         'size': 80,
                                         'type': 'identicon'})

        # Check different size
        self.failUnlessEqual(get_gravatar('alice@example.com', size=200),
                             template % {'hash': hash,
                                         'size': 200,
                                         'type': 'identicon'})

        # Check different default
        http_404 = get_gravatar('alice@example.com', default='404')
        self.failUnlessEqual(http_404,
                             template % {'hash': hash,
                                         'size': 80,
                                         'type': '404'})

        # Is it really a 404?
        response = self.client.get(http_404)
        self.failUnlessEqual(response.status_code, 404)

    def test_signin_redirect(self):
        """
        Test redirect function which should redirect the user after a
        succesfull signin.

        """
        # Test with a requested redirect
        self.failUnlessEqual(signin_redirect(redirect='/accounts/'), '/accounts/')

        # Test with only the user specified
        user = get_user_model().objects.get(pk=1)
        self.failUnlessEqual(signin_redirect(user=user),
                             '/accounts/%s/' % user.username)

        # The ultimate fallback, probably never used
        self.failUnlessEqual(signin_redirect(), settings.LOGIN_REDIRECT_URL)

    def test_get_profile_model(self):
        """
        Test if the correct profile model is returned when
        ``get_profile_model()`` is called.

        """
        # A non existent model should also raise ``SiteProfileNotAvailable``
        # error.
        with self.settings(AUTH_PROFILE_MODULE='userena.FakeProfile'):
            self.assertRaises(SiteProfileNotAvailable, get_profile_model)

        # An error should be raised when there is no ``AUTH_PROFILE_MODULE``
        # supplied.
        with self.settings(AUTH_PROFILE_MODULE=None):
            self.assertRaises(SiteProfileNotAvailable, get_profile_model)

    def test_get_protocol(self):
        """ Test if the correct protocol is returned """
        self.failUnlessEqual(get_protocol(), 'http')

        userena_settings.USERENA_USE_HTTPS = True
        self.failUnlessEqual(get_protocol(), 'https')
        userena_settings.USERENA_USE_HTTPS = False

########NEW FILE########
__FILENAME__ = tests_views
import re

from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from userena import forms
from userena import settings as userena_settings
from userena.utils import get_user_model

User = get_user_model()


class UserenaViewsTests(TestCase):
    """ Test the account views """
    fixtures = ['users', 'profiles']

    def test_valid_activation(self):
        """ A ``GET`` to the activation view """
        # First, register an account.
        self.client.post(reverse('userena_signup'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish',
                               'tos': 'on'})
        user = User.objects.get(email='alice@example.com')
        response = self.client.get(reverse('userena_activate',
                                           kwargs={'activation_key': user.userena_signup.activation_key}))
        self.assertRedirects(response,
                             reverse('userena_profile_detail', kwargs={'username': user.username}))

        user = User.objects.get(email='alice@example.com')
        self.failUnless(user.is_active)

    def test_activation_expired_retry(self):
        """ A ``GET`` to the activation view when activation link is expired """
        # First, register an account.
        userena_settings.USERENA_ACTIVATION_RETRY = True
        self.client.post(reverse('userena_signup'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish',
                               'tos': 'on'})
        user = User.objects.get(email='alice@example.com')
        user.date_joined = datetime.today() - timedelta(days=30)
        user.save()
        response = self.client.get(reverse('userena_activate',
                                           kwargs={'activation_key': user.userena_signup.activation_key}))
        self.assertContains(response, "Request a new activation link")

        user = User.objects.get(email='alice@example.com')
        self.failUnless(not user.is_active)
        userena_settings.USERENA_ACTIVATION_RETRY = False

    def test_retry_activation_ask(self):
        """ Ask for a new activation link """
        # First, register an account.
        userena_settings.USERENA_ACTIVATION_RETRY = True
        self.client.post(reverse('userena_signup'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish',
                               'tos': 'on'})
        user = User.objects.get(email='alice@example.com')
        user.date_joined = datetime.today() - timedelta(days=30)
        user.save()
        old_key = user.userena_signup.activation_key
        response = self.client.get(reverse('userena_activate_retry',
                                           kwargs={'activation_key': old_key}))

        # We must reload the object from database to get the new key
        user = User.objects.get(email='alice@example.com')
        self.assertContains(response, "Account re-activation succeeded")

        self.failIfEqual(old_key, user.userena_signup.activation_key)
        user = User.objects.get(email='alice@example.com')
        self.failUnless(not user.is_active)

        self.failUnlessEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ['alice@example.com'])
        self.assertTrue(mail.outbox[1].body.find("activate your account ")>-1)

        response = self.client.get(reverse('userena_activate',
                                           kwargs={'activation_key': user.userena_signup.activation_key}))
        self.assertRedirects(response,
                             reverse('userena_profile_detail', kwargs={'username': user.username}))

        user = User.objects.get(email='alice@example.com')
        self.failUnless(user.is_active)
        userena_settings.USERENA_ACTIVATION_RETRY = False

    def test_invalid_activation(self):
        """
        A ``GET`` to the activation view with a wrong ``activation_key``.

        """
        response = self.client.get(reverse('userena_activate',
                                           kwargs={'activation_key': 'fake'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'userena/activate_fail.html')

    def test_valid_confirmation(self):
        """ A ``GET`` to the verification view """
        # First, try to change an email.
        user = User.objects.get(pk=1)
        user.userena_signup.change_email('johnie@example.com')

        response = self.client.get(reverse('userena_email_confirm',
                                           kwargs={'confirmation_key': user.userena_signup.email_confirmation_key}))

        self.assertRedirects(response,
                             reverse('userena_email_confirm_complete', kwargs={'username': user.username}))

    def test_invalid_confirmation(self):
        """
        A ``GET`` to the verification view with an invalid verification key.

        """
        response = self.client.get(reverse('userena_email_confirm',
                                           kwargs={'confirmation_key': 'WRONG'}))
        self.assertTemplateUsed(response,
                                'userena/email_confirm_fail.html')

    def test_disabled_view(self):
        """ A ``GET`` to the ``disabled`` view """
        response = self.client.get(reverse('userena_disabled',
                                           kwargs={'username': 'john'}))
        self.assertEqual(response.status_code, 404)
        u = User.objects.filter(username='john').update(is_active=False)
        response = self.client.get(reverse('userena_disabled',
                                           kwargs={'username': 'john'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'userena/disabled.html')

    def test_signup_view(self):
        """ A ``GET`` to the ``signup`` view """
        response = self.client.get(reverse('userena_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'userena/signup_form.html')

        # Check that the correct form is used.
        self.failUnless(isinstance(response.context['form'],
                                   forms.SignupForm))

        # Now check that a different form is used when
        # ``USERENA_WITHOUT_USERNAMES`` setting is set to ``True``
        userena_settings.USERENA_WITHOUT_USERNAMES = True

        response = self.client.get(reverse('userena_signup'))
        self.failUnless(isinstance(response.context['form'],
                                   forms.SignupFormOnlyEmail))

        # Back to default
        userena_settings.USERENA_WITHOUT_USERNAMES = False
        
        # Check for 403 with signups disabled
        userena_settings.USERENA_DISABLE_SIGNUP = True
        
        response = self.client.get(reverse('userena_signup'))
        self.assertEqual(response.status_code, 403)
        
        # Back to default
        userena_settings.USERENA_DISABLE_SIGNUP = False

    def test_signup_view_signout(self):
        """ Check that a newly signed user shouldn't be signed in. """
        # User should be signed in
        self.failUnless(self.client.login(username='john', password='blowfish'))
        # Post a new, valid signup
        response = self.client.post(reverse('userena_signup'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'blueberry',
                                          'password2': 'blueberry',
                                          'tos': 'on'})

        # And should now be signed out
        self.failIf(len(self.client.session.keys()) > 0)

    def test_signup_view_success(self):
        """
        After a ``POST`` to the ``signup`` view a new user should be created,
        the user should be logged in and redirected to the signup success page.

        """
        response = self.client.post(reverse('userena_signup'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'blueberry',
                                          'password2': 'blueberry',
                                          'tos': 'on'})

        # Check for redirect.
        self.assertRedirects(response,
                             reverse('userena_signup_complete', kwargs={'username': 'alice'}))

        # Check for new user.
        self.assertEqual(User.objects.filter(email__iexact='alice@example.com').count(), 1)

    def test_signup_view_with_signin(self):
        """
        After a ``POST`` to the ``signup`` view a new user should be created,
        the user should be logged in and redirected to the signup success page.

        """
        # If activation is required, user is not logged in after signup,
        # disregarding USERENA_SIGNIN_AFTER_SIGNUP setting
        userena_settings.USERENA_SIGNIN_AFTER_SIGNUP = True
        userena_settings.USERENA_ACTIVATION_REQUIRED = True
        response = self.client.post(reverse('userena_signup'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'blueberry',
                                          'password2': 'blueberry',
                                          'tos': 'on'})
        # Immediate reset to default to avoid leaks
        userena_settings.USERENA_SIGNIN_AFTER_SIGNUP = False
        userena_settings.USERENA_ACTIVATION_REQUIRED = True

        response_check = self.client.get(reverse('userena_profile_edit',
                                                 kwargs={'username': 'alice'}))
        self.assertEqual(response_check.status_code, 403)

        userena_settings.USERENA_SIGNIN_AFTER_SIGNUP = True
        userena_settings.USERENA_ACTIVATION_REQUIRED = False
        response = self.client.post(reverse('userena_signup'),
                                    data={'username': 'johndoe',
                                          'email': 'johndoe@example.com',
                                          'password1': 'blueberry',
                                          'password2': 'blueberry',
                                          'tos': 'on'})
        # Immediate reset to default to avoid leaks
        userena_settings.USERENA_SIGNIN_AFTER_SIGNUP = False
        userena_settings.USERENA_ACTIVATION_REQUIRED = True

        # Kind of hackish way to check if the user is logged in
        response_check = self.client.get(reverse('userena_profile_edit',
                                           kwargs={'username': 'johndoe'}))
        self.assertEqual(response_check.status_code, 200)

    def test_signin_view(self):
        """ A ``GET`` to the signin view should render the correct form """
        response = self.client.get(reverse('userena_signin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'userena/signin_form.html')

    def test_signin_view_remember_me_on(self):
        """
        A ``POST`` to the signin with tells it to remember the user for
        ``REMEMBER_ME_DAYS``.

        """
        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish',
                                          'remember_me': True})
        self.assertEqual(self.client.session.get_expiry_age(),
                         userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 3600 * 24)

    def test_signin_view_remember_off(self):
        """
        A ``POST`` to the signin view of which the user doesn't want to be
        remembered.

        """
        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish'})

        self.failUnless(self.client.session.get_expire_at_browser_close())

    def test_signin_view_inactive(self):
        """ A ``POST`` from a inactive user """
        user = User.objects.get(email='john@example.com')
        user.is_active = False
        user.save()

        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish'})

        self.assertRedirects(response,
                             reverse('userena_disabled',
                                     kwargs={'username': user.username}))

    def test_signin_view_success(self):
        """
        A valid ``POST`` to the signin view should redirect the user to it's
        own profile page if no ``next`` value is supplied. Else it should
        redirect to ``next``.

        """
        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish'})

        self.assertRedirects(response, reverse('userena_profile_detail',
                                               kwargs={'username': 'john'}))

        # Redirect to supplied ``next`` value.
        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish',
                                          'next': '/accounts/'})
        self.assertRedirects(response, '/accounts/')

    def test_signin_view_with_invalid_next(self):
        """
        If the value of "next" is not a real URL, this should not raise
        an exception
        """
        response = self.client.post(reverse('userena_signin'),
                                    data={'identification': 'john@example.com',
                                          'password': 'blowfish',
                                          'next': 'something-fake'},
                                    follow=True)
        self.assertEqual(response.status_code, 404)

    def test_signout_view(self):
        """ A ``GET`` to the signout view """
        response = self.client.get(reverse('userena_signout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'userena/signout.html')

    def test_change_email_view(self):
        """ A ``GET`` to the change e-mail view. """
        response = self.client.get(reverse('userena_email_change',
                                           kwargs={'username': 'john'}))

        # Anonymous user should not be able to view the profile page
        self.assertEqual(response.status_code, 403)

        # Login
        client = self.client.login(username='john', password='blowfish')
        response = self.client.get(reverse('userena_email_change',
                                           kwargs={'username': 'john'}))

        self.assertEqual(response.status_code, 200)

        # Check that the correct form is used.
        self.failUnless(isinstance(response.context['form'],
                                   forms.ChangeEmailForm))

        self.assertTemplateUsed(response,
                                'userena/email_form.html')

    def test_change_valid_email_view(self):
        """ A ``POST`` with a valid e-mail address """
        self.client.login(username='john', password='blowfish')
        response = self.client.post(reverse('userena_email_change',
                                            kwargs={'username': 'john'}),
                                    data={'email': 'john_new@example.com'})

        self.assertRedirects(response,
                             reverse('userena_email_change_complete',
                                     kwargs={'username': 'john'}))

    def test_change_password_view(self):
        """ A ``GET`` to the change password view """
        self.client.login(username='john', password='blowfish')
        response = self.client.get(reverse('userena_password_change',
                                           kwargs={'username': 'john'}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'userena/password_form.html')
        self.failUnless(response.context['form'],
                        PasswordChangeForm)

    def test_change_password_view_success(self):
        """ A valid ``POST`` to the password change view """
        self.client.login(username='john', password='blowfish')

        new_password = 'suckfish'
        response = self.client.post(reverse('userena_password_change',
                                            kwargs={'username': 'john'}),
                                    data={'new_password1': new_password,
                                          'new_password2': 'suckfish',
                                          'old_password': 'blowfish'})

        self.assertRedirects(response, reverse('userena_password_change_complete',
                                               kwargs={'username': 'john'}))

        # Check that the new password is set.
        john = User.objects.get(username='john')
        self.failUnless(john.check_password(new_password))

    def test_profile_detail_view(self):
        """ A ``GET`` to the detailed view of a user """
        response = self.client.get(reverse('userena_profile_detail',
                                           kwargs={'username': 'john'}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'userena/profile_detail.html')

    def test_profile_edit_view(self):
        """ A ``GET`` to the edit view of a users account """
        self.client.login(username='john', password='blowfish')
        response = self.client.get(reverse('userena_profile_edit',
                                           kwargs={'username': 'john'}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'userena/profile_form.html')
        self.failUnless(isinstance(response.context['form'],
                                   forms.EditProfileForm))

    def test_profile_edit_view_success(self):
        """ A ``POST`` to the edit view """
        self.client.login(username='john', password='blowfish')
        new_about_me = 'I hate it when people use my name for testing.'
        response = self.client.post(reverse('userena_profile_edit',
                                            kwargs={'username': 'john'}),
                                    data={'about_me': new_about_me,
                                          'privacy': 'open',
                                          'language': 'en'})

        # A valid post should redirect to the detail page.
        self.assertRedirects(response, reverse('userena_profile_detail',
                                               kwargs={'username': 'john'}))

        # Users hould be changed now.
        profile = User.objects.get(username='john').get_profile()
        self.assertEqual(profile.about_me, new_about_me)


    def test_profile_list_view(self):
        """ A ``GET`` to the list view of a user """

        # A profile list should be shown.
        userena_settings.USERENA_DISABLE_PROFILE_LIST = False
        response = self.client.get(reverse('userena_profile_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'userena/profile_list.html')

        # Profile list is disabled.
        userena_settings.USERENA_DISABLE_PROFILE_LIST = True
        response = self.client.get(reverse('userena_profile_list'))
        self.assertEqual(response.status_code, 404)

    def test_password_reset_view_success(self):
        """ A ``POST`` to the password reset view with email that exists"""
        response = self.client.post(reverse('userena_password_reset'),
                                    data={'email': 'john@example.com',})
        # check if there was success redirect to userena_password_reset_done
        # and email was sent
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('userena_password_reset_done'), str(response))
        self.assertTrue(mail.outbox)

    def test_password_reset_view_failure(self):
        """ A ``POST`` to the password reset view with incorrect email"""
        response = self.client.post(reverse('userena_password_reset'),
                                    data={'email': 'no.such.user@example.com',})
        # note: status code can be different depending on django version
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(mail.outbox)

    def test_password_reset_confirm(self):
        # post reset request and search form confirmation url
        self.client.post(reverse('userena_password_reset'),
                         data={'email': 'john@example.com',})
        confirm_mail = mail.outbox[0]
        confirm_url = re.search(r'\bhttps?://\S+', confirm_mail.body).group()

        # get confirmation request page
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)

        # post new password and check if redirected with success
        response = self.client.post(confirm_url,
                                    data={'new_password1': 'pass',
                                          'new_password2': 'pass',})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('userena_password_reset_complete'), str(response))

########NEW FILE########
__FILENAME__ = test_backends
from django.test import TestCase
from django.contrib.auth import authenticate

from userena.backends import UserenaAuthenticationBackend
from userena.utils import get_user_model

User = get_user_model()


class UserenaAuthenticationBackendTests(TestCase):
    """
    Test the ``UserenaAuthenticationBackend`` which should return a ``User``
    when supplied with a username/email and a correct password.

    """
    fixtures = ['users',]
    backend = UserenaAuthenticationBackend()

    def test_with_username(self):
        """ Test the backend when usernames are supplied. """
        # Invalid usernames or passwords
        invalid_data_dicts = [
            # Invalid password
            {'identification': 'john',
             'password': 'inhalefish'},
            # Invalid username
            {'identification': 'alice',
             'password': 'blowfish'},
        ]
        for invalid_dict in invalid_data_dicts:
            result = self.backend.authenticate(identification=invalid_dict['identification'],
                                               password=invalid_dict['password'])
            self.failIf(isinstance(result, User))

        # Valid username and password
        result = self.backend.authenticate(identification='john',
                                           password='blowfish')
        self.failUnless(isinstance(result, User))

    def test_with_email(self):
        """ Test the backend when email address is supplied """
        # Invalid e-mail adressses or passwords
        invalid_data_dicts = [
            # Invalid password
            {'identification': 'john@example.com',
             'password': 'inhalefish'},
            # Invalid e-mail address
            {'identification': 'alice@example.com',
             'password': 'blowfish'},
        ]
        for invalid_dict in invalid_data_dicts:
            result = self.backend.authenticate(identification=invalid_dict['identification'],
                                               password=invalid_dict['password'])
            self.failIf(isinstance(result, User))

        # Valid e-email address and password
        result = self.backend.authenticate(identification='john@example.com',
                                           password='blowfish')
        self.failUnless(isinstance(result, User))

    def test_get_user(self):
        """ Test that the user is returned """
        user = self.backend.get_user(1)
        self.failUnlessEqual(user.username, 'john')

        # None should be returned when false id.
        user = self.backend.get_user(99)
        self.failIf(user)

########NEW FILE########
__FILENAME__ = test_commands
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from userena.models import UserenaSignup
from userena.managers import ASSIGNED_PERMISSIONS
from userena import settings as userena_settings
from userena.utils import get_profile_model, get_user_model

from guardian.shortcuts import remove_perm
from guardian.models import UserObjectPermission

import datetime

User = get_user_model()

class CleanExpiredTests(TestCase):
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}

    def test_clean_expired(self):
        """
        Test if ``clean_expired`` deletes all users which ``activation_key``
        is expired.

        """
        # Create an account which is expired.
        user = UserenaSignup.objects.create_user(**self.user_info)
        user.date_joined -= datetime.timedelta(days=userena_settings.USERENA_ACTIVATION_DAYS + 1)
        user.save()

        # There should be one account now
        User.objects.get(username=self.user_info['username'])

        # Clean it.
        call_command('clean_expired')

        self.failUnlessEqual(User.objects.filter(username=self.user_info['username']).count(), 0)

class CheckPermissionTests(TestCase):
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}

    def test_check_permissions(self):
        # Create a new account.
        user = UserenaSignup.objects.create_user(**self.user_info)
        user.save()

        # Remove all permissions
        UserObjectPermission.objects.filter(user=user).delete()
        self.failUnlessEqual(UserObjectPermission.objects.filter(user=user).count(),
                             0)

        # Check it
        call_command('check_permissions')

        # User should have all permissions again
        user_permissions = UserObjectPermission.objects.filter(user=user).values_list('permission__codename', flat=True)

        required_permissions = [u'change_user', u'delete_user', u'change_profile', u'view_profile']
        for perm in required_permissions:
            if perm not in user_permissions:
                self.fail()

        # Check it again should do nothing
        call_command('check_permissions', test=True)

    def test_incomplete_permissions(self):
        # Delete the neccesary permissions
        profile_model_obj = get_profile_model()
        content_type_profile = ContentType.objects.get_for_model(profile_model_obj)
        content_type_user = ContentType.objects.get_for_model(User)
        for model, perms in ASSIGNED_PERMISSIONS.items():
            if model == "profile":
                content_type = content_type_profile
            else: content_type = content_type_user
            for perm in perms:
                Permission.objects.get(name=perm[1],
                                       content_type=content_type).delete()

        # Check if they are they are back
        for model, perms in ASSIGNED_PERMISSIONS.items():
            if model == "profile":
                content_type = content_type_profile
            else: content_type = content_type_user
            for perm in perms:
                try:
                    perm = Permission.objects.get(name=perm[1],
                                                  content_type=content_type)
                except Permission.DoesNotExist: pass
                else: self.fail("Found %s: " % perm)

        # Repair them
        call_command('check_permissions', test=True)

        # Check if they are they are back
        for model, perms in ASSIGNED_PERMISSIONS.items():
            if model == "profile":
                content_type = content_type_profile
            else: content_type = content_type_user
            for perm in perms:
                try:
                    perm = Permission.objects.get(name=perm[1],
                                                  content_type=content_type)
                except Permission.DoesNotExist:
                    self.fail()

    def test_no_profile(self):
        """ Check for warning when there is no profile """
        # TODO: Dirty! Currently we check for the warning by getting a 100%
        # test coverage, meaning that it dit output some warning.
        user = UserenaSignup.objects.create_user(**self.user_info)

        # remove the profile of this user
        get_profile_model().objects.get(user=user).delete()

        # run the command to check for the warning.
        call_command('check_permissions', test=True)


########NEW FILE########
__FILENAME__ = test_privacy
from django.core.urlresolvers import reverse
from django.test import TestCase

from userena.tests.profiles.models import Profile

class PrivacyTests(TestCase):
    """
    Privacy testing of views concerning profiles.

    Test the privacy of the views that are available with three type of users:

        - Anonymous: An user that is not signed in.
        - Registered: An user that is registered and signed in.
        - Superuser: An user that is administrator at the site.

    """
    fixtures = ['users', 'profiles']

    reg_user = {'username': 'jane',
                'password': 'blowfish'}

    super_user = {'username': 'john',
                  'password': 'blowfish'}

    detail_profile_url = reverse('userena_profile_detail',
                                 kwargs={'username': 'john'})

    edit_profile_url = reverse('userena_profile_edit',
                                kwargs={'username': 'john'})

    def _test_status_codes(self, url, users_status):
        """
        Test if the status codes are corresponding to what that user should
        see.

        """
        for user, status in users_status:
            if user:
                self.client.login(**user)
            response = self.client.get(url)
            self.failUnlessEqual(response.status_code, status)

    def test_detail_open_profile_view(self):
        """ Viewing an open profile should be visible to everyone """
        profile = Profile.objects.get(pk=1)
        profile.privacy = 'open'
        profile.save()

        users_status = (
            (None, 200),
            (self.reg_user, 200),
            (self.super_user, 200)
        )
        self._test_status_codes(self.detail_profile_url, users_status)

    def test_detail_registered_profile_view(self):
        """ Viewing a users who's privacy is registered """
        profile = Profile.objects.get(pk=1)
        profile.privacy = 'registered'
        profile.save()

        users_status = (
            (None, 403),
            (self.reg_user, 200),
            (self.super_user, 200)
        )
        self._test_status_codes(self.detail_profile_url, users_status)

    def test_detail_closed_profile_view(self):
        """ Viewing a closed profile should only by visible to the admin """
        profile = Profile.objects.get(pk=1)
        profile.privacy = 'closed'
        profile.save()

        users_status = (
            (None, 403),
            (self.reg_user, 403),
            (self.super_user, 200)
        )
        self._test_status_codes(self.detail_profile_url, users_status)

    def test_edit_profile_view(self):
        """ Editing a profile should only be available to the owner and the admin """
        profile = Profile.objects.get(pk=1)

        users_status = (
            (None, 403),
            (self.reg_user, 403),
            (self.super_user, 200)
        )
        self._test_status_codes(self.edit_profile_url, users_status)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from django.contrib.auth import views as auth_views

from userena import views as userena_views
from userena import settings as userena_settings
from userena.compat import auth_views_compat_quirks, password_reset_uid_kwarg


def merged_dict(dict_a, dict_b):
    """Merges two dicts and returns output. It's purpose is to ease use of
    ``auth_views_compat_quirks``
    """
    dict_a.update(dict_b)
    return dict_a

urlpatterns = patterns('',
    # Signup, signin and signout
    url(r'^signup/$',
       userena_views.signup,
       name='userena_signup'),
    url(r'^signin/$',
       userena_views.signin,
       name='userena_signin'),
    url(r'^signout/$',
       userena_views.signout,
       name='userena_signout'),

    # Reset password
    url(r'^password/reset/$',
       auth_views.password_reset,
       merged_dict({'template_name': 'userena/password_reset_form.html',
                    'email_template_name': 'userena/emails/password_reset_message.txt',
                    'extra_context': {'without_usernames': userena_settings.USERENA_WITHOUT_USERNAMES}
                   }, auth_views_compat_quirks['userena_password_reset']),
       name='userena_password_reset'),
    url(r'^password/reset/done/$',
       auth_views.password_reset_done,
       {'template_name': 'userena/password_reset_done.html',},
       name='userena_password_reset_done'),
    url(r'^password/reset/confirm/(?P<%s>[0-9A-Za-z]+)-(?P<token>.+)/$' % password_reset_uid_kwarg,
       auth_views.password_reset_confirm,
       merged_dict({'template_name': 'userena/password_reset_confirm_form.html',
                    }, auth_views_compat_quirks['userena_password_reset_confirm']),
       name='userena_password_reset_confirm'),
    url(r'^password/reset/confirm/complete/$',
       auth_views.password_reset_complete,
       {'template_name': 'userena/password_reset_complete.html'},
        name='userena_password_reset_complete'),

    # Signup
    url(r'^(?P<username>[\.\w-]+)/signup/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'userena/signup_complete.html',
        'extra_context': {'userena_activation_required': userena_settings.USERENA_ACTIVATION_REQUIRED,
                          'userena_activation_days': userena_settings.USERENA_ACTIVATION_DAYS}},
       name='userena_signup_complete'),

    # Activate
    url(r'^activate/(?P<activation_key>\w+)/$',
       userena_views.activate,
       name='userena_activate'),

    # Retry activation
    url(r'^activate/retry/(?P<activation_key>\w+)/$',
        userena_views.activate_retry,
        name='userena_activate_retry'),

    # Change email and confirm it
    url(r'^(?P<username>[\.\w-]+)/email/$',
       userena_views.email_change,
       name='userena_email_change'),
    url(r'^(?P<username>[\.\w-]+)/email/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'userena/email_change_complete.html'},
       name='userena_email_change_complete'),
    url(r'^(?P<username>[\.\w-]+)/confirm-email/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'userena/email_confirm_complete.html'},
       name='userena_email_confirm_complete'),
    url(r'^confirm-email/(?P<confirmation_key>\w+)/$',
       userena_views.email_confirm,
       name='userena_email_confirm'),

    # Disabled account
    url(r'^(?P<username>[\.\w-]+)/disabled/$',
       userena_views.disabled_account,
       {'template_name': 'userena/disabled.html'},
       name='userena_disabled'),

    # Change password
    url(r'^(?P<username>[\.\w-]+)/password/$',
       userena_views.password_change,
       name='userena_password_change'),
    url(r'^(?P<username>[\.\w-]+)/password/complete/$',
       userena_views.direct_to_user_template,
       {'template_name': 'userena/password_complete.html'},
       name='userena_password_change_complete'),

    # Edit profile
    url(r'^(?P<username>[\.\w-]+)/edit/$',
       userena_views.profile_edit,
       name='userena_profile_edit'),

    # View profiles
    url(r'^(?P<username>(?!signout|signup|signin)[\.\w-]+)/$',
       userena_views.profile_detail,
       name='userena_profile_detail'),
    url(r'^page/(?P<page>[0-9]+)/$',
       userena_views.ProfileListView.as_view(),
       name='userena_profile_list_paginated'),
    url(r'^$',
       userena_views.ProfileListView.as_view(),
       name='userena_profile_list'),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable
from django.db.models import get_model

try:
    from hashlib import sha1 as sha_constructor, md5 as md5_constructor
except ImportError:
    from django.utils.hashcompat import sha_constructor, md5_constructor

from userena import settings as userena_settings

import urllib, random, datetime

try:
    from django.utils.text import truncate_words
except ImportError:
    # Django >=1.5
    from django.utils.text import Truncator
    from django.utils.functional import allow_lazy
    def truncate_words(s, num, end_text='...'):
        truncate = end_text and ' %s' % end_text or ''
        return Truncator(s).words(num, truncate=truncate)
    truncate_words = allow_lazy(truncate_words, unicode)

def get_gravatar(email, size=80, default='identicon'):
    """ Get's a Gravatar for a email address.

    :param size:
        The size in pixels of one side of the Gravatar's square image.
        Optional, if not supplied will default to ``80``.

    :param default:
        Defines what should be displayed if no image is found for this user.
        Optional argument which defaults to ``identicon``. The argument can be
        a URI to an image or one of the following options:

            ``404``
                Do not load any image if none is associated with the email
                hash, instead return an HTTP 404 (File Not Found) response.

            ``mm``
                Mystery-man, a simple, cartoon-style silhouetted outline of a
                person (does not vary by email hash).

            ``identicon``
                A geometric pattern based on an email hash.

            ``monsterid``
                A generated 'monster' with different colors, faces, etc.

            ``wavatar``
                Generated faces with differing features and backgrounds

    :return: The URI pointing to the Gravatar.

    """
    if userena_settings.USERENA_MUGSHOT_GRAVATAR_SECURE:
        base_url = 'https://secure.gravatar.com/avatar/'
    else: base_url = '//www.gravatar.com/avatar/'

    gravatar_url = '%(base_url)s%(gravatar_id)s?' % \
            {'base_url': base_url,
             'gravatar_id': md5_constructor(email.lower()).hexdigest()}

    gravatar_url += urllib.urlencode({'s': str(size),
                                      'd': default})
    return gravatar_url

def signin_redirect(redirect=None, user=None):
    """
    Redirect user after successful sign in.

    First looks for a ``requested_redirect``. If not supplied will fall-back to
    the user specific account page. If all fails, will fall-back to the standard
    Django ``LOGIN_REDIRECT_URL`` setting. Returns a string defining the URI to
    go next.

    :param redirect:
        A value normally supplied by ``next`` form field. Gets preference
        before the default view which requires the user.

    :param user:
        A ``User`` object specifying the user who has just signed in.

    :return: String containing the URI to redirect to.

    """
    if redirect: return redirect
    elif user is not None:
        return userena_settings.USERENA_SIGNIN_REDIRECT_URL % \
                {'username': user.username}
    else: return settings.LOGIN_REDIRECT_URL

def generate_sha1(string, salt=None):
    """
    Generates a sha1 hash for supplied string. Doesn't need to be very secure
    because it's not used for password checking. We got Django for that.

    :param string:
        The string that needs to be encrypted.

    :param salt:
        Optionally define your own salt. If none is supplied, will use a random
        string of 5 characters.

    :return: Tuple containing the salt and hash.

    """
    if not isinstance(string, (str, unicode)):
        string = str(string)
    if isinstance(string, unicode):
        string = string.encode("utf-8")
    if not salt:
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
    hash = sha_constructor(salt+string).hexdigest()

    return (salt, hash)

def get_profile_model():
    """
    Return the model class for the currently-active user profile
    model, as defined by the ``AUTH_PROFILE_MODULE`` setting.

    :return: The model that is used as profile.

    """
    if (not hasattr(settings, 'AUTH_PROFILE_MODULE')) or \
           (not settings.AUTH_PROFILE_MODULE):
        raise SiteProfileNotAvailable

    profile_mod = get_model(*settings.AUTH_PROFILE_MODULE.rsplit('.',1))
    if profile_mod is None:
        raise SiteProfileNotAvailable
    return profile_mod

def get_protocol():
    """
    Returns a string with the current protocol.

    This can be either 'http' or 'https' depending on ``USERENA_USE_HTTPS``
    setting.

    """
    protocol = 'http'
    if userena_settings.USERENA_USE_HTTPS:
        protocol = 'https'
    return protocol

def get_datetime_now():
    """
    Returns datetime object with current point in time.

    In Django 1.4+ it uses Django's django.utils.timezone.now() which returns
    an aware or naive datetime that represents the current point in time
    when ``USE_TZ`` in project's settings is True or False respectively.
    In older versions of Django it uses datetime.datetime.now().

    """
    try:
        from django.utils import timezone
        return timezone.now() # pragma: no cover
    except ImportError: # pragma: no cover
        return datetime.datetime.now()

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

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout as Signout
from django.views.generic import TemplateView
from django.template.context import RequestContext
from django.views.generic.list import ListView
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.http import Http404, HttpResponseRedirect

from userena.forms import (SignupForm, SignupFormOnlyEmail, AuthenticationForm,
                           ChangeEmailForm, EditProfileForm)
from userena.models import UserenaSignup
from userena.decorators import secure_required
from userena.backends import UserenaAuthenticationBackend
from userena.utils import signin_redirect, get_profile_model, get_user_model
from userena import signals as userena_signals
from userena import settings as userena_settings

from guardian.decorators import permission_required_or_403

import warnings

class ExtraContextTemplateView(TemplateView):
    """ Add extra context to a simple template view """
    extra_context = None

    def get_context_data(self, *args, **kwargs):
        context = super(ExtraContextTemplateView, self).get_context_data(*args, **kwargs)
        if self.extra_context:
            context.update(self.extra_context)
        return context

    # this view is used in POST requests, e.g. signup when the form is not valid
    post = TemplateView.get

class ProfileListView(ListView):
    """ Lists all profiles """
    context_object_name='profile_list'
    page=1
    paginate_by=50
    template_name=userena_settings.USERENA_PROFILE_LIST_TEMPLATE
    extra_context=None

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ProfileListView, self).get_context_data(**kwargs)
        try:
            page = int(self.request.GET.get('page', None))
        except (TypeError, ValueError):
            page = self.page

        if userena_settings.USERENA_DISABLE_PROFILE_LIST \
           and not self.request.user.is_staff:
            raise Http404

        if not self.extra_context: self.extra_context = dict()

        context['page'] = page
        context['paginate_by'] = self.paginate_by
        context['extra_context'] = self.extra_context

        return context

    def get_queryset(self):
        profile_model = get_profile_model()
        queryset = profile_model.objects.get_visible_profiles(self.request.user).select_related()
        return queryset

@secure_required
def signup(request, signup_form=SignupForm,
           template_name='userena/signup_form.html', success_url=None,
           extra_context=None):
    """
    Signup of an account.

    Signup requiring a username, email and password. After signup a user gets
    an email with an activation link used to activate their account. After
    successful signup redirects to ``success_url``.

    :param signup_form:
        Form that will be used to sign a user. Defaults to userena's
        :class:`SignupForm`.

    :param template_name:
        String containing the template name that will be used to display the
        signup form. Defaults to ``userena/signup_form.html``.

    :param success_url:
        String containing the URI which should be redirected to after a
        successful signup. If not supplied will redirect to
        ``userena_signup_complete`` view.

    :param extra_context:
        Dictionary containing variables which are added to the template
        context. Defaults to a dictionary with a ``form`` key containing the
        ``signup_form``.

    **Context**

    ``form``
        Form supplied by ``signup_form``.

    """
    # If signup is disabled, return 403
    if userena_settings.USERENA_DISABLE_SIGNUP:
        raise PermissionDenied

    # If no usernames are wanted and the default form is used, fallback to the
    # default form that doesn't display to enter the username.
    if userena_settings.USERENA_WITHOUT_USERNAMES and (signup_form == SignupForm):
        signup_form = SignupFormOnlyEmail

    form = signup_form()

    if request.method == 'POST':
        form = signup_form(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()

            # Send the signup complete signal
            userena_signals.signup_complete.send(sender=None,
                                                 user=user)


            if success_url: redirect_to = success_url
            else: redirect_to = reverse('userena_signup_complete',
                                        kwargs={'username': user.username})

            # A new signed user should logout the old one.
            if request.user.is_authenticated():
                logout(request)

            if (userena_settings.USERENA_SIGNIN_AFTER_SIGNUP and
                not userena_settings.USERENA_ACTIVATION_REQUIRED):
                user = authenticate(identification=user.email, check_password=False)
                login(request, user)

            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context['form'] = form
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

@secure_required
def activate(request, activation_key,
             template_name='userena/activate_fail.html',
             retry_template_name='userena/activate_retry.html',
             success_url=None, extra_context=None):
    """
    Activate a user with an activation key.

    The key is a SHA1 string. When the SHA1 is found with an
    :class:`UserenaSignup`, the :class:`User` of that account will be
    activated.  After a successful activation the view will redirect to
    ``success_url``.  If the SHA1 is not found, the user will be shown the
    ``template_name`` template displaying a fail message.
    If the SHA1 is found but expired, ``retry_template_name`` is used instead,
    so the user can proceed to :func:`activate_retry` to get a new actvation key.

    :param activation_key:
        String of a SHA1 string of 40 characters long. A SHA1 is always 160bit
        long, with 4 bits per character this makes it --160/4-- 40 characters
        long.

    :param template_name:
        String containing the template name that is used when the
        ``activation_key`` is invalid and the activation fails. Defaults to
        ``userena/activate_fail.html``.

    :param retry_template_name:
        String containing the template name that is used when the
        ``activation_key`` is expired. Defaults to
        ``userena/activate_retry.html``.

    :param success_url:
        String containing the URL where the user should be redirected to after
        a successful activation. Will replace ``%(username)s`` with string
        formatting if supplied. If ``success_url`` is left empty, will direct
        to ``userena_profile_detail`` view.

    :param extra_context:
        Dictionary containing variables which could be added to the template
        context. Default to an empty dictionary.

    """
    try:
        if (not UserenaSignup.objects.check_expired_activation(activation_key)
            or not userena_settings.USERENA_ACTIVATION_RETRY):
            user = UserenaSignup.objects.activate_user(activation_key)
            if user:
                # Sign the user in.
                auth_user = authenticate(identification=user.email,
                                         check_password=False)
                login(request, auth_user)

                if userena_settings.USERENA_USE_MESSAGES:
                    messages.success(request, _('Your account has been activated and you have been signed in.'),
                                     fail_silently=True)

                if success_url: redirect_to = success_url % {'username': user.username }
                else: redirect_to = reverse('userena_profile_detail',
                                            kwargs={'username': user.username})
                return redirect(redirect_to)
            else:
                if not extra_context: extra_context = dict()
                return ExtraContextTemplateView.as_view(template_name=template_name,
                                                        extra_context=extra_context)(
                                        request)
        else:
            if not extra_context: extra_context = dict()
            extra_context['activation_key'] = activation_key
            return ExtraContextTemplateView.as_view(template_name=retry_template_name,
                                                extra_context=extra_context)(request)
    except UserenaSignup.DoesNotExist:
        if not extra_context: extra_context = dict()
        return ExtraContextTemplateView.as_view(template_name=template_name,
                                                extra_context=extra_context)(request)

@secure_required
def activate_retry(request, activation_key,
                   template_name='userena/activate_retry_success.html',
                   extra_context=None):
    """
    Reissue a new ``activation_key`` for the user with the expired
    ``activation_key``.

    If ``activation_key`` does not exists, or ``USERENA_ACTIVATION_RETRY`` is
    set to False and for any other error condition user is redirected to
    :func:`activate` for error message display.

    :param activation_key:
        String of a SHA1 string of 40 characters long. A SHA1 is always 160bit
        long, with 4 bits per character this makes it --160/4-- 40 characters
        long.

    :param template_name:
        String containing the template name that is used when new
        ``activation_key`` has been created. Defaults to
        ``userena/activate_retry_success.html``.

    :param extra_context:
        Dictionary containing variables which could be added to the template
        context. Default to an empty dictionary.

    """
    if not userena_settings.USERENA_ACTIVATION_RETRY:
        return redirect(reverse('userena_activate', args=(activation_key,)))
    try:
        if UserenaSignup.objects.check_expired_activation(activation_key):
            new_key = UserenaSignup.objects.reissue_activation(activation_key)
            if new_key:
                if not extra_context: extra_context = dict()
                return ExtraContextTemplateView.as_view(template_name=template_name,
                                                    extra_context=extra_context)(request)
            else:
                return redirect(reverse('userena_activate',args=(activation_key,)))
        else:
            return redirect(reverse('userena_activate',args=(activation_key,)))
    except UserenaSignup.DoesNotExist:
        return redirect(reverse('userena_activate',args=(activation_key,)))

@secure_required
def email_confirm(request, confirmation_key,
                  template_name='userena/email_confirm_fail.html',
                  success_url=None, extra_context=None):
    """
    Confirms an email address with a confirmation key.

    Confirms a new email address by running :func:`User.objects.confirm_email`
    method. If the method returns an :class:`User` the user will have his new
    e-mail address set and redirected to ``success_url``. If no ``User`` is
    returned the user will be represented with a fail message from
    ``template_name``.

    :param confirmation_key:
        String with a SHA1 representing the confirmation key used to verify a
        new email address.

    :param template_name:
        String containing the template name which should be rendered when
        confirmation fails. When confirmation is successful, no template is
        needed because the user will be redirected to ``success_url``.

    :param success_url:
        String containing the URL which is redirected to after a successful
        confirmation.  Supplied argument must be able to be rendered by
        ``reverse`` function.

    :param extra_context:
        Dictionary of variables that are passed on to the template supplied by
        ``template_name``.

    """
    user = UserenaSignup.objects.confirm_email(confirmation_key)
    if user:
        if userena_settings.USERENA_USE_MESSAGES:
            messages.success(request, _('Your email address has been changed.'),
                             fail_silently=True)

        if success_url: redirect_to = success_url
        else: redirect_to = reverse('userena_email_confirm_complete',
                                    kwargs={'username': user.username})
        return redirect(redirect_to)
    else:
        if not extra_context: extra_context = dict()
        return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

def direct_to_user_template(request, username, template_name,
                            extra_context=None):
    """
    Simple wrapper for Django's :func:`direct_to_template` view.

    This view is used when you want to show a template to a specific user. A
    wrapper for :func:`direct_to_template` where the template also has access to
    the user that is found with ``username``. For ex. used after signup,
    activation and confirmation of a new e-mail.

    :param username:
        String defining the username of the user that made the action.

    :param template_name:
        String defining the name of the template to use. Defaults to
        ``userena/signup_complete.html``.

    **Keyword arguments**

    ``extra_context``
        A dictionary containing extra variables that should be passed to the
        rendered template. The ``account`` key is always the ``User``
        that completed the action.

    **Extra context**

    ``viewed_user``
        The currently :class:`User` that is viewed.

    """
    user = get_object_or_404(get_user_model(), username__iexact=username)

    if not extra_context: extra_context = dict()
    extra_context['viewed_user'] = user
    extra_context['profile'] = user.get_profile()
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

def disabled_account(request, username, template_name, extra_context=None):
    """
    Checks if the account is disabled, if so, returns the disabled account template.

    :param username:
        String defining the username of the user that made the action.

    :param template_name:
        String defining the name of the template to use. Defaults to
        ``userena/signup_complete.html``.

    **Keyword arguments**

    ``extra_context``
        A dictionary containing extra variables that should be passed to the
        rendered template. The ``account`` key is always the ``User``
        that completed the action.

    **Extra context**

    ``viewed_user``
        The currently :class:`User` that is viewed.

    ``profile``
        Profile of the viewed user.
    
    """
    user = get_object_or_404(get_user_model(), username__iexact=username)

    if user.is_active:
        raise Http404

    if not extra_context: extra_context = dict()
    extra_context['viewed_user'] = user
    extra_context['profile'] = user.get_profile()
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)
    
@secure_required
def signin(request, auth_form=AuthenticationForm,
           template_name='userena/signin_form.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           redirect_signin_function=signin_redirect, extra_context=None):
    """
    Signin using email or username with password.

    Signs a user in by combining email/username with password. If the
    combination is correct and the user :func:`is_active` the
    :func:`redirect_signin_function` is called with the arguments
    ``REDIRECT_FIELD_NAME`` and an instance of the :class:`User` who is is
    trying the login. The returned value of the function will be the URL that
    is redirected to.

    A user can also select to be remembered for ``USERENA_REMEMBER_DAYS``.

    :param auth_form:
        Form to use for signing the user in. Defaults to the
        :class:`AuthenticationForm` supplied by userena.

    :param template_name:
        String defining the name of the template to use. Defaults to
        ``userena/signin_form.html``.

    :param redirect_field_name:
        Form field name which contains the value for a redirect to the
        succeeding page. Defaults to ``next`` and is set in
        ``REDIRECT_FIELD_NAME`` setting.

    :param redirect_signin_function:
        Function which handles the redirect. This functions gets the value of
        ``REDIRECT_FIELD_NAME`` and the :class:`User` who has logged in. It
        must return a string which specifies the URI to redirect to.

    :param extra_context:
        A dictionary containing extra variables that should be passed to the
        rendered template. The ``form`` key is always the ``auth_form``.

    **Context**

    ``form``
        Form used for authentication supplied by ``auth_form``.

    """
    form = auth_form()

    if request.method == 'POST':
        form = auth_form(request.POST, request.FILES)
        if form.is_valid():
            identification, password, remember_me = (form.cleaned_data['identification'],
                                                     form.cleaned_data['password'],
                                                     form.cleaned_data['remember_me'])
            user = authenticate(identification=identification,
                                password=password)
            if user.is_active:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(userena_settings.USERENA_REMEMBER_ME_DAYS[1] * 86400)
                else: request.session.set_expiry(0)

                if userena_settings.USERENA_USE_MESSAGES:
                    messages.success(request, _('You have been signed in.'),
                                     fail_silently=True)

                #send a signal that a user has signed in
                userena_signals.account_signin.send(sender=None, user=user)
                # Whereto now?
                redirect_to = redirect_signin_function(
                    request.REQUEST.get(redirect_field_name), user)
                return HttpResponseRedirect(redirect_to)
            else:
                return redirect(reverse('userena_disabled',
                                        kwargs={'username': user.username}))

    if not extra_context: extra_context = dict()
    extra_context.update({
        'form': form,
        'next': request.REQUEST.get(redirect_field_name),
    })
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

@secure_required
def signout(request, next_page=userena_settings.USERENA_REDIRECT_ON_SIGNOUT,
            template_name='userena/signout.html', *args, **kwargs):
    """
    Signs out the user and adds a success message ``You have been signed
    out.`` If next_page is defined you will be redirected to the URI. If
    not the template in template_name is used.

    :param next_page:
        A string which specifies the URI to redirect to.

    :param template_name:
        String defining the name of the template to use. Defaults to
        ``userena/signout.html``.

    """
    if request.user.is_authenticated() and userena_settings.USERENA_USE_MESSAGES: # pragma: no cover
        messages.success(request, _('You have been signed out.'), fail_silently=True)
    userena_signals.account_signout.send(sender=None, user=request.user)
    return Signout(request, next_page, template_name, *args, **kwargs)

@secure_required
@permission_required_or_403('change_user', (get_user_model(), 'username', 'username'))
def email_change(request, username, email_form=ChangeEmailForm,
                 template_name='userena/email_form.html', success_url=None,
                 extra_context=None):
    """
    Change email address

    :param username:
        String of the username which specifies the current account.

    :param email_form:
        Form that will be used to change the email address. Defaults to
        :class:`ChangeEmailForm` supplied by userena.

    :param template_name:
        String containing the template to be used to display the email form.
        Defaults to ``userena/email_form.html``.

    :param success_url:
        Named URL where the user will get redirected to when successfully
        changing their email address.  When not supplied will redirect to
        ``userena_email_complete`` URL.

    :param extra_context:
        Dictionary containing extra variables that can be used to render the
        template. The ``form`` key is always the form supplied by the keyword
        argument ``form`` and the ``user`` key by the user whose email address
        is being changed.

    **Context**

    ``form``
        Form that is used to change the email address supplied by ``form``.

    ``account``
        Instance of the ``Account`` whose email address is about to be changed.

    **Todo**

    Need to have per-object permissions, which enables users with the correct
    permissions to alter the email address of others.

    """
    user = get_object_or_404(get_user_model(), username__iexact=username)
    prev_email = user.email
    form = email_form(user)

    if request.method == 'POST':
        form = email_form(user,
                               request.POST,
                               request.FILES)

        if form.is_valid():
            form.save()

            if success_url:
                # Send a signal that the email has changed
                userena_signals.email_change.send(sender=None,
                                                  user=user,
                                                  prev_email=prev_email,
                                                  new_email=user.email)
                redirect_to = success_url
            else: redirect_to = reverse('userena_email_change_complete',
                                        kwargs={'username': user.username})
            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context['form'] = form
    extra_context['profile'] = user.get_profile()
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

@secure_required
@permission_required_or_403('change_user', (get_user_model(), 'username', 'username'))
def password_change(request, username, template_name='userena/password_form.html',
                    pass_form=PasswordChangeForm, success_url=None, extra_context=None):
    """ Change password of user.

    This view is almost a mirror of the view supplied in
    :func:`contrib.auth.views.password_change`, with the minor change that in
    this view we also use the username to change the password. This was needed
    to keep our URLs logical (and REST) across the entire application. And
    that in a later stadium administrators can also change the users password
    through the web application itself.

    :param username:
        String supplying the username of the user who's password is about to be
        changed.

    :param template_name:
        String of the name of the template that is used to display the password
        change form. Defaults to ``userena/password_form.html``.

    :param pass_form:
        Form used to change password. Default is the form supplied by Django
        itself named ``PasswordChangeForm``.

    :param success_url:
        Named URL that is passed onto a :func:`reverse` function with
        ``username`` of the active user. Defaults to the
        ``userena_password_complete`` URL.

    :param extra_context:
        Dictionary of extra variables that are passed on to the template. The
        ``form`` key is always used by the form supplied by ``pass_form``.

    **Context**

    ``form``
        Form used to change the password.

    """
    user = get_object_or_404(get_user_model(),
                             username__iexact=username)

    form = pass_form(user=user)

    if request.method == "POST":
        form = pass_form(user=user, data=request.POST)
        if form.is_valid():
            form.save()

            # Send a signal that the password has changed
            userena_signals.password_complete.send(sender=None,
                                                   user=user)

            if success_url: redirect_to = success_url
            else: redirect_to = reverse('userena_password_change_complete',
                                        kwargs={'username': user.username})
            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context['form'] = form
    extra_context['profile'] = user.get_profile()
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)
@secure_required
@permission_required_or_403('change_profile', (get_profile_model(), 'user__username', 'username'))
def profile_edit(request, username, edit_profile_form=EditProfileForm,
                 template_name='userena/profile_form.html', success_url=None,
                 extra_context=None, **kwargs):
    """
    Edit profile.

    Edits a profile selected by the supplied username. First checks
    permissions if the user is allowed to edit this profile, if denied will
    show a 404. When the profile is successfully edited will redirect to
    ``success_url``.

    :param username:
        Username of the user which profile should be edited.

    :param edit_profile_form:

        Form that is used to edit the profile. The :func:`EditProfileForm.save`
        method of this form will be called when the form
        :func:`EditProfileForm.is_valid`.  Defaults to :class:`EditProfileForm`
        from userena.

    :param template_name:
        String of the template that is used to render this view. Defaults to
        ``userena/edit_profile_form.html``.

    :param success_url:
        Named URL which will be passed on to a django ``reverse`` function after
        the form is successfully saved. Defaults to the ``userena_detail`` url.

    :param extra_context:
        Dictionary containing variables that are passed on to the
        ``template_name`` template.  ``form`` key will always be the form used
        to edit the profile, and the ``profile`` key is always the edited
        profile.

    **Context**

    ``form``
        Form that is used to alter the profile.

    ``profile``
        Instance of the ``Profile`` that is edited.

    """
    user = get_object_or_404(get_user_model(),
                             username__iexact=username)

    profile = user.get_profile()

    user_initial = {'first_name': user.first_name,
                    'last_name': user.last_name}

    form = edit_profile_form(instance=profile, initial=user_initial)

    if request.method == 'POST':
        form = edit_profile_form(request.POST, request.FILES, instance=profile,
                                 initial=user_initial)

        if form.is_valid():
            profile = form.save()

            if userena_settings.USERENA_USE_MESSAGES:
                messages.success(request, _('Your profile has been updated.'),
                                 fail_silently=True)

            if success_url:
                # Send a signal that the profile has changed
                userena_signals.profile_change.send(sender=None,
                                                    user=user)
                redirect_to = success_url
            else: redirect_to = reverse('userena_profile_detail', kwargs={'username': username})
            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context['form'] = form
    extra_context['profile'] = profile
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)
def profile_detail(request, username,
    template_name=userena_settings.USERENA_PROFILE_DETAIL_TEMPLATE,
    extra_context=None, **kwargs):
    """
    Detailed view of an user.

    :param username:
        String of the username of which the profile should be viewed.

    :param template_name:
        String representing the template name that should be used to display
        the profile.

    :param extra_context:
        Dictionary of variables which should be supplied to the template. The
        ``profile`` key is always the current profile.

    **Context**

    ``profile``
        Instance of the currently viewed ``Profile``.

    """
    user = get_object_or_404(get_user_model(),
                             username__iexact=username)

    profile_model = get_profile_model()
    try:
        profile = user.get_profile()
    except profile_model.DoesNotExist:
        profile = profile_model.objects.create(user=user)

    if not profile.can_view_profile(request.user):
        raise PermissionDenied
    if not extra_context: extra_context = dict()
    extra_context['profile'] = user.get_profile()
    extra_context['hide_email'] = userena_settings.USERENA_HIDE_EMAIL
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)

def profile_list(request, page=1, template_name='userena/profile_list.html',
                 paginate_by=50, extra_context=None, **kwargs): # pragma: no cover
    """
    Returns a list of all profiles that are public.

    It's possible to disable this by changing ``USERENA_DISABLE_PROFILE_LIST``
    to ``True`` in your settings.

    :param page:
        Integer of the active page used for pagination. Defaults to the first
        page.

    :param template_name:
        String defining the name of the template that is used to render the
        list of all users. Defaults to ``userena/list.html``.

    :param paginate_by:
        Integer defining the amount of displayed profiles per page. Defaults to
        50 profiles per page.

    :param extra_context:
        Dictionary of variables that are passed on to the ``template_name``
        template.

    **Context**

    ``profile_list``
        A list of profiles.

    ``is_paginated``
        A boolean representing whether the results are paginated.

    If the result is paginated. It will also contain the following variables.

    ``paginator``
        An instance of ``django.core.paginator.Paginator``.

    ``page_obj``
        An instance of ``django.core.paginator.Page``.

    """
    warnings.warn("views.profile_list is deprecated. Use ProfileListView instead", DeprecationWarning, stacklevel=2)

    try:
        page = int(request.GET.get('page', None))
    except (TypeError, ValueError):
        page = page

    if userena_settings.USERENA_DISABLE_PROFILE_LIST \
       and not request.user.is_staff:
        raise Http404

    profile_model = get_profile_model()
    queryset = profile_model.objects.get_visible_profiles(request.user)

    if not extra_context: extra_context = dict()
    return ProfileListView.as_view(queryset=queryset,
                                   paginate_by=paginate_by,
                                   page=page,
                                   template_name=template_name,
                                   extra_context=extra_context,
                                   **kwargs)(request)

########NEW FILE########
