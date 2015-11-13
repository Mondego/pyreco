__FILENAME__ = models
"""
In Django 1.4+, simply adds itself to the PASSWORD_HASHERS setting so old
passwords will be converted properly.

Otherwise, overrides :class:`django.contrib.auth.models.User` to use bcrypt
hashing for passwords.

You can set the following ``settings``:

``BCRYPT_ENABLED``
   Enables bcrypt hashing when ``User.set_password()`` is called.

``BCRYPT_ENABLED_UNDER_TEST``
   Enables bcrypt hashing when running inside Django
   TestCases. Defaults to False, to speed up user creation.

``BCRYPT_ROUNDS``
   Number of rounds to use for bcrypt hashing. Defaults to 12.

``BCRYPT_MIGRATE``
   Enables bcrypt password migration on a check_password() call.
   Default is set to False.
"""


import bcrypt

from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.utils.encoding import smart_str


def get_rounds():
    """Returns the number of rounds to use for bcrypt hashing."""
    return getattr(settings, "BCRYPT_ROUNDS", 12)


def is_enabled():
    """Returns ``True`` if bcrypt should be used."""
    enabled = getattr(settings, "BCRYPT_ENABLED", True)
    if not enabled:
        return False
    # Are we under a test?
    if hasattr(mail, 'outbox'):
        return getattr(settings, "BCRYPT_ENABLED_UNDER_TEST", False)
    return True


def migrate_to_bcrypt():
    """Returns ``True`` if password migration is activated."""
    return getattr(settings, "BCRYPT_MIGRATE", False)


def bcrypt_check_password(self, raw_password):
    """
    Returns a boolean of whether the *raw_password* was correct.

    Attempts to validate with bcrypt, but falls back to Django's
    ``User.check_password()`` if the hash is incorrect.

    If ``BCRYPT_MIGRATE`` is set, attempts to convert sha1 password to bcrypt
    or converts between different bcrypt rounds values.

    .. note::

        In case of a password migration this method calls ``User.save()`` to
        persist the changes.
    """
    pwd_ok = False
    should_change = False
    if self.password.startswith('bc$'):
        salt_and_hash = self.password[3:]
        pwd_ok = bcrypt.hashpw(smart_str(raw_password), salt_and_hash) == salt_and_hash
        if pwd_ok:
            rounds = int(salt_and_hash.split('$')[2])
            should_change = rounds != get_rounds()
    elif _check_password(self, raw_password):
        pwd_ok = True
        should_change = True

    if pwd_ok and should_change and is_enabled() and migrate_to_bcrypt():
        self.set_password(raw_password)
        salt_and_hash = self.password[3:]
        assert bcrypt.hashpw(raw_password, salt_and_hash) == salt_and_hash
        self.save()

    return pwd_ok


def bcrypt_set_password(self, raw_password):
    """
    Sets the user's password to *raw_password*, hashed with bcrypt.
    """
    if not is_enabled() or raw_password is None:
        _set_password(self, raw_password)
    else:
        salt = bcrypt.gensalt(get_rounds())
        self.password = 'bc$' + bcrypt.hashpw(smart_str(raw_password), salt)


try:
    from django.contrib.auth.hashers import BCryptPasswordHasher

    class LegacyDjangoBCryptPasswordHasher(BCryptPasswordHasher):
        algorithm = 'bc'

    settings.PASSWORD_HASHERS = settings.PASSWORD_HASHERS + ('django_bcrypt.models.LegacyDjangoBCryptPasswordHasher',)
except ImportError:
    _check_password = User.check_password
    User.check_password = bcrypt_check_password
    _set_password = User.set_password
    User.set_password = bcrypt_set_password

########NEW FILE########
__FILENAME__ = tests
from __future__ import with_statement
from contextlib import contextmanager

import bcrypt

from django import conf
from django.contrib.auth.models import User, UNUSABLE_PASSWORD
from django.test import TestCase
from django.utils.functional import LazyObject

from django_bcrypt.models import (bcrypt_check_password, bcrypt_set_password,
                                  _check_password, _set_password,
                                  get_rounds, is_enabled, migrate_to_bcrypt)


class CheckPasswordTest(TestCase):
    def test_bcrypt_password(self):
        user = User()
        with settings():
            bcrypt_set_password(user, 'password')
        self.assertTrue(bcrypt_check_password(user, 'password'))
        self.assertFalse(bcrypt_check_password(user, 'invalid'))

    def test_unicode_password(self):
        user = User()
        with settings():
            bcrypt_set_password(user, u"aáåäeéêëoôö")
        self.assertTrue(bcrypt_check_password(user, u"aaaaeeeeooo"))
        self.assertFalse(bcrypt_check_password(user, 'invalid'))

    def test_sha1_password(self):
        user = User()
        _set_password(user, 'password')
        self.assertTrue(bcrypt_check_password(user, 'password'))
        self.assertFalse(bcrypt_check_password(user, 'invalid'))

    def test_change_rounds(self):
        user = User()
        # Hash with 5 rounds
        with settings(BCRYPT_ROUNDS=5):
            bcrypt_set_password(user, 'password')
        password_5 = user.password
        self.assertTrue(bcrypt_check_password(user, 'password'))
        # Hash with 12 rounds
        with settings(BCRYPT_ROUNDS=12):
            bcrypt_set_password(user, 'password')
        password_12 = user.password
        self.assertTrue(bcrypt_check_password(user, 'password'))


class SetPasswordTest(TestCase):
    def assertBcrypt(self, hashed, password):
        self.assertEqual(hashed[:3], 'bc$')
        self.assertEqual(hashed[3:], bcrypt.hashpw(password, hashed[3:]))

    def test_set_password(self):
        user = User()
        with settings():
            bcrypt_set_password(user, 'password')
        self.assertBcrypt(user.password, 'password')

    def test_disabled(self):
        user = User()
        with settings(BCRYPT_ENABLED=False):
            bcrypt_set_password(user, 'password')
        self.assertFalse(user.password.startswith('bc$'), user.password)

    def test_set_unusable_password(self):
        user = User()
        with settings():
            bcrypt_set_password(user, None)
        self.assertEqual(user.password, UNUSABLE_PASSWORD)

    def test_change_rounds(self):
        user = User()
        with settings(BCRYPT_ROUNDS=0):
            settings.BCRYPT_ROUNDS = 0
            bcrypt_set_password(user, 'password')
            self.assertBcrypt(user.password, 'password')


class MigratePasswordTest(TestCase):
    def assertBcrypt(self, hashed, password):
        self.assertEqual(hashed[:3], 'bc$')
        self.assertEqual(hashed[3:], bcrypt.hashpw(password, hashed[3:]))

    def assertSha1(self, hashed, password):
        self.assertEqual(hashed[:5], 'sha1$')

    def test_migrate_sha1_to_bcrypt(self):
        user = User(username='username')
        with settings(BCRYPT_MIGRATE=True, BCRYPT_ENABLED_UNDER_TEST=True):
            _set_password(user, 'password')
            self.assertSha1(user.password, 'password')
            self.assertTrue(bcrypt_check_password(user, 'password'))
            self.assertBcrypt(user.password, 'password')
        self.assertEqual(User.objects.get(username='username').password,
                         user.password)

    def test_migrate_bcrypt_to_bcrypt(self):
        user = User(username='username')
        with settings(BCRYPT_MIGRATE=True,
                      BCRYPT_ROUNDS=10,
                      BCRYPT_ENABLED_UNDER_TEST=True):
            user.set_password('password')
        with settings(BCRYPT_MIGRATE=True,
                      BCRYPT_ROUNDS=12,
                      BCRYPT_ENABLED_UNDER_TEST=True):
            user.check_password('password')
        salt_and_hash = user.password[3:]
        self.assertEqual(salt_and_hash.split('$')[2], '12')
        self.assertEqual(User.objects.get(username='username').password,
                         user.password)

    def test_no_bcrypt_to_bcrypt(self):
        user = User(username='username')
        with settings(BCRYPT_MIGRATE=True,
                      BCRYPT_ROUNDS=10,
                      BCRYPT_ENABLED_UNDER_TEST=True):
            user.set_password('password')
            old_password = user.password
            user.check_password('password')
        self.assertEqual(old_password, user.password)

    def test_no_migrate_password(self):
        user = User()
        with settings(BCRYPT_MIGRATE=False, BCRYPT_ENABLED_UNDER_TEST=True):
            _set_password(user, 'password')
            self.assertSha1(user.password, 'password')
            self.assertTrue(bcrypt_check_password(user, 'password'))
            self.assertSha1(user.password, 'password')


class SettingsTest(TestCase):
    def test_rounds(self):
        with settings(BCRYPT_ROUNDS=0):
            self.assertEqual(get_rounds(), 0)
        with settings(BCRYPT_ROUNDS=5):
            self.assertEqual(get_rounds(), 5)
        with settings(BCRYPT_ROUNDS=NotImplemented):
            self.assertEqual(get_rounds(), 12)

    def test_enabled(self):
        with settings(BCRYPT_ENABLED=False):
            self.assertFalse(is_enabled())
        with settings(BCRYPT_ENABLED=True):
            self.assertTrue(is_enabled())
        with settings(BCRYPT_ENABLED=NotImplemented):
            self.assertTrue(is_enabled())

    def test_enabled_under_test(self):
        with settings(BCRYPT_ENABLED_UNDER_TEST=True):
            self.assertTrue(is_enabled())
        with settings(BCRYPT_ENABLED_UNDER_TEST=False):
            self.assertFalse(is_enabled())
        with settings(BCRYPT_ENABLED_UNDER_TEST=NotImplemented):
            self.assertFalse(is_enabled())

    def test_migrate_to_bcrypt(self):
        with settings(BCRYPT_MIGRATE=False):
            self.assertEqual(migrate_to_bcrypt(), False)
        with settings(BCRYPT_MIGRATE=True):
            self.assertEqual(migrate_to_bcrypt(), True)
        with settings(BCRYPT_MIGRATE=NotImplemented):
            self.assertEqual(migrate_to_bcrypt(), False)


def settings(**kwargs):
    kwargs = dict({'BCRYPT_ENABLED': True,
                   'BCRYPT_ENABLED_UNDER_TEST': True},
                  **kwargs)
    return patch(conf.settings, **kwargs)


@contextmanager
def patch(namespace, **values):
    """Patches `namespace`.`name` with `value` for (name, value) in values"""

    originals = {}

    if isinstance(namespace, LazyObject):
        if namespace._wrapped is None:
            namespace._setup()
        namespace = namespace._wrapped

    for (name, value) in values.iteritems():
        try:
            originals[name] = getattr(namespace, name)
        except AttributeError:
            originals[name] = NotImplemented
        if value is NotImplemented:
            if originals[name] is not NotImplemented:
                delattr(namespace, name)
        else:
            setattr(namespace, name, value)

    try:
        yield
    finally:
        for (name, original_value) in originals.iteritems():
            if original_value is NotImplemented:
                if values[name] is not NotImplemented:
                    delattr(namespace, name)
            else:
                setattr(namespace, name, original_value)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-bcrypt documentation build configuration file, created by
# sphinx-quickstart on Thu May 19 14:06:46 2011.
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
project = u'django-bcrypt'
copyright = u'2011, Dumbwaiter Design and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.9.2'
# The full version, including alpha/beta/rc tags.
release = '0.9.2'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'waiter'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['../themes']

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
htmlhelp_basename = 'djangobcryptdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'djangobcrypt.tex', u'django-bcrypt Documentation',
   u'Dumbwaiter Design', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'djangobcrypt', u'django-bcrypt Documentation',
     [u'Dumbwaiter Design'], 1)
]

########NEW FILE########
