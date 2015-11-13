__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# WTForms documentation build configuration file, created by
# sphinx-quickstart on Fri Aug 01 15:29:36 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

def _fix_import_path():
    """
    Don't want to pollute the config globals, so do path munging
    here in this function
    """
    import sys, os

    try:
        import wtforms
    except ImportError:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        build_lib = os.path.join(parent_dir, 'build', 'lib')
        if os.path.isdir(build_lib):
            sys.path.insert(0, build_lib)
        else:
            sys.path.insert(0, parent_dir)

_fix_import_path()

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
project = 'WTForms'
copyright = '2010 by Thomas Johansson, James Crasta'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '2.0.1'
# The full version, including alpha/beta/rc tags.
release = '2.0.1dev'


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
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'friendly'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

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

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'WTFormsdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
    ('index', 'WTForms.tex', 'WTForms Documentation',
    'Thomas Johansson, James Crasta', 'manual'),
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
__FILENAME__ = common
from contextlib import contextmanager
from wtforms.validators import ValidationError, StopValidation


class DummyTranslations(object):
    def gettext(self, string):
        return string

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular

        return plural


class DummyField(object):
    _translations = DummyTranslations()

    def __init__(self, data, errors=(), raw_data=None):
        self.data = data
        self.errors = list(errors)
        self.raw_data = raw_data

    def gettext(self, string):
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        return self._translations.ngettext(singular, plural, n)


def grab_error_message(callable, form, field):
    try:
        callable(form, field)
    except ValidationError as e:
        return e.args[0]


def grab_stop_message(callable, form, field):
    try:
        callable(form, field)
    except StopValidation as e:
        return e.args[0]


def contains_validator(field, v_type):
    for v in field.validators:
        if isinstance(v, v_type):
            return True
    return False


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


@contextmanager
def assert_raises_text(e_type, text):
    import re
    try:
        yield
    except e_type as e:
        if not re.match(text, e.args[0]):
            raise AssertionError('Exception raised: %r but text %r did not match pattern %r' % (e, e.args[0], text))
    else:
        raise AssertionError('Expected Exception %r, did not get it' % (e_type, ))

########NEW FILE########
__FILENAME__ = csrf
from __future__ import unicode_literals

from contextlib import contextmanager
from functools import partial
from unittest import TestCase

from wtforms.fields import TextField
from wtforms.form import Form
from wtforms.csrf.core import CSRF
from wtforms.csrf.session import SessionCSRF
from tests.common import DummyPostData

import datetime
import hashlib
import hmac


class DummyCSRF(CSRF):
    def generate_csrf_token(self, csrf_token_field):
        return 'dummytoken'


class FakeSessionRequest(object):
    def __init__(self, session):
        self.session = session


class TimePin(SessionCSRF):
    """
    CSRF with ability to pin times so that we can do a thorough test
    of expected values and keys.
    """
    pinned_time = None

    @classmethod
    @contextmanager
    def pin_time(cls, value):
        original = cls.pinned_time
        cls.pinned_time = value
        yield
        cls.pinned_time = original

    def now(self):
        return self.pinned_time


class SimplePopulateObject(object):
    a = None
    csrf_token = None


class DummyCSRFTest(TestCase):
    class F(Form):
        class Meta:
            csrf = True
            csrf_class = DummyCSRF
        a = TextField()

    def test_base_class(self):
        self.assertRaises(NotImplementedError, self.F, meta={'csrf_class': CSRF})

    def test_basic_impl(self):
        form = self.F()
        assert 'csrf_token' in form
        assert not form.validate()
        self.assertEqual(form.csrf_token._value(), 'dummytoken')
        form = self.F(DummyPostData(csrf_token='dummytoken'))
        assert form.validate()

    def test_csrf_off(self):
        form = self.F(meta={'csrf': False})
        assert 'csrf_token' not in form

    def test_rename(self):
        form = self.F(meta={'csrf_field_name': 'mycsrf'})
        assert 'mycsrf' in form
        assert 'csrf_token' not in form

    def test_no_populate(self):
        obj = SimplePopulateObject()
        form = self.F(a='test', csrf_token='dummytoken')
        form.populate_obj(obj)
        assert obj.csrf_token is None
        self.assertEqual(obj.a, 'test')


class SessionCSRFTest(TestCase):
    class F(Form):
        class Meta:
            csrf = True
            csrf_secret = b'foobar'

        a = TextField()

    class NoTimeLimit(F):
        class Meta:
            csrf_time_limit = None

    class Pinned(F):
        class Meta:
            csrf_class = TimePin

    def test_various_failures(self):
        self.assertRaises(TypeError, self.F)
        self.assertRaises(Exception, self.F, meta={'csrf_secret': None})

    def test_no_time_limit(self):
        session = {}
        form = self._test_phase1(self.NoTimeLimit, session)
        expected_csrf = hmac.new(b'foobar', session['csrf'].encode('ascii'), digestmod=hashlib.sha1).hexdigest()
        self.assertEqual(form.csrf_token.current_token, '##' + expected_csrf)
        self._test_phase2(self.NoTimeLimit, session, form.csrf_token.current_token)

    def test_with_time_limit(self):
        session = {}
        form = self._test_phase1(self.F, session)
        self._test_phase2(self.F, session, form.csrf_token.current_token)

    def test_detailed_expected_values(self):
        """
        A full test with the date and time pinned so we get deterministic output.
        """
        session = {'csrf': '93fed52fa69a2b2b0bf9c350c8aeeb408b6b6dfa'}
        dt = partial(datetime.datetime, 2013, 1, 15)
        with TimePin.pin_time(dt(8, 11, 12)):
            form = self._test_phase1(self.Pinned, session)
            token = form.csrf_token.current_token
            self.assertEqual(token, '20130115084112##53812764d65abb8fa88384551a751ca590dff5fb')

        # Make sure that CSRF validates in a normal case.
        with TimePin.pin_time(dt(8, 18)):
            form = self._test_phase2(self.Pinned, session, token)
            new_token = form.csrf_token.current_token
            self.assertNotEqual(new_token, token)
            self.assertEqual(new_token, '20130115084800##e399e3a6a84860762723672b694134507ba21b58')

        # Make sure that CSRF fails when we're past time
        with TimePin.pin_time(dt(8, 43)):
            form = self._test_phase2(self.Pinned, session, token, False)
            assert not form.validate()
            self.assertEqual(form.csrf_token.errors, ['CSRF token expired'])

            # We can succeed with a slightly newer token
            self._test_phase2(self.Pinned, session, new_token)

        with TimePin.pin_time(dt(8, 44)):
            bad_token = '20130115084800##e399e3a6a84860762723672b694134507ba21b59'
            form = self._test_phase2(self.Pinned, session, bad_token, False)
            assert not form.validate()

    def _test_phase1(self, form_class, session):
        form = form_class(meta={'csrf_context': session})
        assert not form.validate()
        assert form.csrf_token.errors
        assert 'csrf' in session
        return form

    def _test_phase2(self, form_class, session, token, must_validate=True):
        form = form_class(
            formdata=DummyPostData(csrf_token=token),
            meta={'csrf_context': session}
        )
        if must_validate:
            assert form.validate()
        return form

########NEW FILE########
__FILENAME__ = gaetest_common
"""
This contains common tools for gae tests, and also sets up the environment.

It should be the first import in the unit tests.
"""
# -- First setup paths
import sys
import os
my_dir = os.path.dirname(os.path.abspath(__file__))
WTFORMS_DIR = os.path.abspath(os.path.join(my_dir, '..', '..'))
sys.path.insert(0, WTFORMS_DIR)

SAMPLE_AUTHORS = (
    ('Bob', 'Boston'),
    ('Harry', 'Houston'),
    ('Linda', 'London'),
)


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


def fill_authors(Author):
    """
    Fill authors from SAMPLE_AUTHORS.
    Model is passed so it can be either an NDB or DB model.
    """
    AGE_BASE = 30
    authors = []
    for name, city in SAMPLE_AUTHORS:
        author = Author(name=name, city=city, age=AGE_BASE)
        author.put()
        authors.append(author)
        AGE_BASE += 1
    return authors

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
"""
Unittests for wtforms.ext.appengine

To run the tests, use NoseGAE:

pip install nose nosegae

nosetests --with-gae --without-sandbox
"""
from __future__ import unicode_literals

# This needs to stay as the first import, it sets up paths.
from gaetest_common import DummyPostData

from unittest import TestCase
from google.appengine.ext import db

from wtforms import Form, fields as f, validators
from wtforms.ext.appengine.db import model_form
from wtforms.ext.appengine.fields import GeoPtPropertyField


class Author(db.Model):
    name = db.StringProperty(required=True)
    city = db.StringProperty()
    age = db.IntegerProperty(required=True)
    is_admin = db.BooleanProperty(default=False)


class Book(db.Model):
    author = db.ReferenceProperty(Author)


class AllPropertiesModel(db.Model):
    """Property names are ugly, yes."""
    prop_string = db.StringProperty()
    prop_byte_string = db.ByteStringProperty()
    prop_boolean = db.BooleanProperty()
    prop_integer = db.IntegerProperty()
    prop_float = db.FloatProperty()
    prop_date_time = db.DateTimeProperty()
    prop_date = db.DateProperty()
    prop_time = db.TimeProperty()
    prop_list = db.ListProperty(int)
    prop_string_list = db.StringListProperty()
    prop_reference = db.ReferenceProperty()
    prop_self_refeference = db.SelfReferenceProperty()
    prop_user = db.UserProperty()
    prop_blob = db.BlobProperty()
    prop_text = db.TextProperty()
    prop_category = db.CategoryProperty()
    prop_link = db.LinkProperty()
    prop_email = db.EmailProperty()
    prop_geo_pt = db.GeoPtProperty()
    prop_im = db.IMProperty()
    prop_phone_number = db.PhoneNumberProperty()
    prop_postal_address = db.PostalAddressProperty()
    prop_rating = db.RatingProperty()


class DateTimeModel(db.Model):
    prop_date_time_1 = db.DateTimeProperty()
    prop_date_time_2 = db.DateTimeProperty(auto_now=True)
    prop_date_time_3 = db.DateTimeProperty(auto_now_add=True)

    prop_date_1 = db.DateProperty()
    prop_date_2 = db.DateProperty(auto_now=True)
    prop_date_3 = db.DateProperty(auto_now_add=True)

    prop_time_1 = db.TimeProperty()
    prop_time_2 = db.TimeProperty(auto_now=True)
    prop_time_3 = db.TimeProperty(auto_now_add=True)


class TestModelForm(TestCase):
    def tearDown(self):
        for entity in Author.all():
            db.delete(entity)

        for entity in Book.all():
            db.delete(entity)

    def test_model_form_basic(self):
        form_class = model_form(Author)

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'city'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), True)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.city, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)
        self.assertEqual(isinstance(form.is_admin, f.BooleanField), True)

    def test_required_field(self):
        form_class = model_form(Author)

        form = form_class()
        self.assertEqual(form.name.flags.required, True)
        self.assertEqual(form.city.flags.required, False)
        self.assertEqual(form.age.flags.required, True)
        self.assertEqual(form.is_admin.flags.required, False)

    def test_default_value(self):
        form_class = model_form(Author)

        form = form_class()
        self.assertEqual(form.name.default, None)
        self.assertEqual(form.city.default, None)
        self.assertEqual(form.age.default, None)
        self.assertEqual(form.is_admin.default, False)

    def test_model_form_only(self):
        form_class = model_form(Author, only=['name', 'age'])

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'city'), False)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), False)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)

    def test_model_form_exclude(self):
        form_class = model_form(Author, exclude=['is_admin'])

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'city'), True)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), False)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.city, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)

    def test_datetime_model(self):
        """Fields marked as auto_add / auto_add_now should not be included."""
        form_class = model_form(DateTimeModel)

        self.assertEqual(hasattr(form_class, 'prop_date_time_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_time_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_date_time_3'), False)

        self.assertEqual(hasattr(form_class, 'prop_date_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_date_3'), False)

        self.assertEqual(hasattr(form_class, 'prop_time_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_time_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_time_3'), False)

    def test_not_implemented_properties(self):
        # This should not raise NotImplementedError.
        form_class = model_form(AllPropertiesModel)

        # These should be set.
        self.assertEqual(hasattr(form_class, 'prop_string'), True)
        self.assertEqual(hasattr(form_class, 'prop_byte_string'), True)
        self.assertEqual(hasattr(form_class, 'prop_boolean'), True)
        self.assertEqual(hasattr(form_class, 'prop_integer'), True)
        self.assertEqual(hasattr(form_class, 'prop_float'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_time'), True)
        self.assertEqual(hasattr(form_class, 'prop_date'), True)
        self.assertEqual(hasattr(form_class, 'prop_time'), True)
        self.assertEqual(hasattr(form_class, 'prop_string_list'), True)
        self.assertEqual(hasattr(form_class, 'prop_reference'), True)
        self.assertEqual(hasattr(form_class, 'prop_self_refeference'), True)
        self.assertEqual(hasattr(form_class, 'prop_blob'), True)
        self.assertEqual(hasattr(form_class, 'prop_text'), True)
        self.assertEqual(hasattr(form_class, 'prop_category'), True)
        self.assertEqual(hasattr(form_class, 'prop_link'), True)
        self.assertEqual(hasattr(form_class, 'prop_email'), True)
        self.assertEqual(hasattr(form_class, 'prop_geo_pt'), True)
        self.assertEqual(hasattr(form_class, 'prop_phone_number'), True)
        self.assertEqual(hasattr(form_class, 'prop_postal_address'), True)
        self.assertEqual(hasattr(form_class, 'prop_rating'), True)

        # These should NOT be set.
        self.assertEqual(hasattr(form_class, 'prop_list'), False)
        self.assertEqual(hasattr(form_class, 'prop_user'), False)
        self.assertEqual(hasattr(form_class, 'prop_im'), False)

    def test_populate_form(self):
        entity = Author(key_name='test', name='John', city='Yukon', age=25, is_admin=True)
        entity.put()

        obj = Author.get_by_key_name('test')
        form_class = model_form(Author)

        form = form_class(obj=obj)
        self.assertEqual(form.name.data, 'John')
        self.assertEqual(form.city.data, 'Yukon')
        self.assertEqual(form.age.data, 25)
        self.assertEqual(form.is_admin.data, True)

    def test_field_attributes(self):
        form_class = model_form(Author, field_args={
            'name': {
                'label': 'Full name',
                'description': 'Your name',
            },
            'age': {
                'label': 'Age',
                'validators': [validators.NumberRange(min=14, max=99)],
            },
            'city': {
                'label': 'City',
                'description': 'The city in which you live, not the one in which you were born.',
            },
            'is_admin': {
                'label': 'Administrative rights',
            },
        })
        form = form_class()

        self.assertEqual(form.name.label.text, 'Full name')
        self.assertEqual(form.name.description, 'Your name')

        self.assertEqual(form.age.label.text, 'Age')

        self.assertEqual(form.city.label.text, 'City')
        self.assertEqual(form.city.description, 'The city in which you live, not the one in which you were born.')

        self.assertEqual(form.is_admin.label.text, 'Administrative rights')

    def test_reference_property(self):
        keys = set(['__None'])
        for name in ['foo', 'bar', 'baz']:
            author = Author(name=name, age=26)
            author.put()
            keys.add(str(author.key()))

        form_class = model_form(Book)
        form = form_class()

        for key, name, value in form.author.iter_choices():
            assert key in keys
            keys.remove(key)

        assert not keys


class TestFields(TestCase):
    class GeoTestForm(Form):
        geo = GeoPtPropertyField()

    def test_geopt_property(self):
        form = self.GeoTestForm(DummyPostData(geo='5.0, -7.0'))
        self.assertTrue(form.validate())
        self.assertEqual(form.geo.data, '5.0,-7.0')
        form = self.GeoTestForm(DummyPostData(geo='5.0,-f'))
        self.assertFalse(form.validate())

########NEW FILE########
__FILENAME__ = test_ndb
from __future__ import unicode_literals

# This needs to stay as the first import, it sets up paths.
from gaetest_common import DummyPostData, fill_authors

from google.appengine.ext import ndb
from unittest import TestCase
from wtforms import Form, TextField, IntegerField, BooleanField
from wtforms.compat import text_type
from wtforms.ext.appengine.fields import KeyPropertyField
from wtforms.ext.appengine.ndb import model_form


class Author(ndb.Model):
    name = ndb.StringProperty(required=True)
    city = ndb.StringProperty()
    age = ndb.IntegerProperty(required=True)
    is_admin = ndb.BooleanProperty(default=False)


class Book(ndb.Model):
    author = ndb.KeyProperty(kind=Author)


class TestKeyPropertyField(TestCase):
    class F(Form):
        author = KeyPropertyField(reference_class=Author)

    def setUp(self):
        self.authors = fill_authors(Author)
        self.first_author_id = self.authors[0].key.id()

    def tearDown(self):
        for author in Author.query():
            author.key.delete()

    def test_no_data(self):
        form = self.F()
        form.author.query = Author.query().order(Author.name)

        assert not form.validate()
        ichoices = list(form.author.iter_choices())
        self.assertEqual(len(ichoices), len(self.authors))
        for author, (key, label, selected) in zip(self.authors, ichoices):
            self.assertEqual(key, text_type(author.key.id()))

    def test_form_data(self):
        # Valid data
        form = self.F(DummyPostData(author=text_type(self.first_author_id)))
        form.author.query = Author.query().order(Author.name)
        assert form.validate()
        ichoices = list(form.author.iter_choices())
        self.assertEqual(len(ichoices), len(self.authors))
        self.assertEqual(list(x[2] for x in ichoices), [True, False, False])

        # Bogus Data
        form = self.F(DummyPostData(author='fooflaf'))
        assert not form.validate()
        print list(form.author.iter_choices())
        assert all(x[2] is False for x in form.author.iter_choices())


class TestModelForm(TestCase):
    EXPECTED_AUTHOR = [('name', TextField), ('city', TextField), ('age', IntegerField), ('is_admin', BooleanField)]

    def test_author(self):
        form = model_form(Author)
        for (expected_name, expected_type), field in zip(self.EXPECTED_AUTHOR, form()):
            self.assertEqual(field.name, expected_name)
            self.assertEqual(type(field), expected_type)

    def test_book(self):
        authors = set(text_type(x.key.id()) for x in fill_authors(Author))
        authors.add('__None')
        form = model_form(Book)
        keys = set()
        for key, b, c in form().author.iter_choices():
            keys.add(key)

        self.assertEqual(authors, keys)

########NEW FILE########
__FILENAME__ = ext_csrf
from __future__ import unicode_literals

from unittest import TestCase

from wtforms.fields import TextField
from wtforms.ext.csrf import SecureForm
from wtforms.ext.csrf.session import SessionSecureForm
from tests.common import DummyPostData

import datetime
import hashlib
import hmac


class InsecureForm(SecureForm):
    def generate_csrf_token(self, csrf_context):
        return csrf_context

    a = TextField()


class FakeSessionRequest(object):
    def __init__(self, session):
        self.session = session


class StupidObject(object):
    a = None
    csrf_token = None


class SecureFormTest(TestCase):
    def test_base_class(self):
        self.assertRaises(NotImplementedError, SecureForm)

    def test_basic_impl(self):
        form = InsecureForm(csrf_context=42)
        self.assertEqual(form.csrf_token.current_token, 42)
        self.assertFalse(form.validate())
        self.assertEqual(len(form.csrf_token.errors), 1)
        self.assertEqual(form.csrf_token._value(), 42)
        # Make sure csrf_token is taken out from .data
        self.assertEqual(form.data, {'a': None})

    def test_with_data(self):
        post_data = DummyPostData(csrf_token='test', a='hi')
        form = InsecureForm(post_data, csrf_context='test')
        self.assertTrue(form.validate())
        self.assertEqual(form.data, {'a': 'hi'})

        form = InsecureForm(post_data, csrf_context='something')
        self.assertFalse(form.validate())

        # Make sure that value is still the current token despite
        # the posting of a different value
        self.assertEqual(form.csrf_token._value(), 'something')

        # Make sure populate_obj doesn't overwrite the token
        obj = StupidObject()
        form.populate_obj(obj)
        self.assertEqual(obj.a, 'hi')
        self.assertEqual(obj.csrf_token, None)

    def test_with_missing_token(self):
        post_data = DummyPostData(a='hi')
        form = InsecureForm(post_data, csrf_context='test')
        self.assertFalse(form.validate())

        self.assertEqual(form.csrf_token.data, '')
        self.assertEqual(form.csrf_token._value(), 'test')


class SessionSecureFormTest(TestCase):
    class SSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')

    class BadTimeSSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')
        TIME_LIMIT = datetime.timedelta(-1, 86300)

    class NoTimeSSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')
        TIME_LIMIT = None

    def test_basic(self):
        self.assertRaises(Exception, SessionSecureForm)
        self.assertRaises(TypeError, self.SSF)
        session = {}
        form = self.SSF(csrf_context=FakeSessionRequest(session))
        assert 'csrf_token' in form
        assert 'csrf' in session

    def test_timestamped(self):
        session = {}
        postdata = DummyPostData(csrf_token='fake##fake')
        form = self.SSF(postdata, csrf_context=session)
        assert 'csrf' in session
        assert form.csrf_token._value()
        assert form.csrf_token._value() != session['csrf']
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF failed')
        # good_token = form.csrf_token._value()

        # Now test a valid CSRF with invalid timestamp
        evil_form = self.BadTimeSSF(csrf_context=session)
        bad_token = evil_form.csrf_token._value()

        postdata = DummyPostData(csrf_token=bad_token)
        form = self.SSF(postdata, csrf_context=session)
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF token expired')

    def test_notime(self):
        session = {}
        form = self.NoTimeSSF(csrf_context=session)
        hmacced = hmac.new(form.SECRET_KEY, session['csrf'].encode('utf8'), digestmod=hashlib.sha1)
        self.assertEqual(form.csrf_token._value(), '##%s' % hmacced.hexdigest())
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF token missing')

        # Test with pre-made values
        session = {'csrf': '00e9fa5fe507251ac5f32b1608e9282f75156a05'}
        postdata = DummyPostData(csrf_token='##d21f54b7dd2041fab5f8d644d4d3690c77beeb14')

        form = self.NoTimeSSF(postdata, csrf_context=session)
        assert form.validate()

########NEW FILE########
__FILENAME__ = ext_dateutil
from __future__ import unicode_literals

from datetime import datetime, date
from unittest import TestCase

from wtforms.form import Form
from wtforms.ext.dateutil.fields import DateTimeField, DateField
from tests.common import DummyPostData


class DateutilTest(TestCase):
    class F(Form):
        a = DateTimeField()
        b = DateField(default=lambda: date(2004, 9, 12))
        c = DateField(parse_kwargs=dict(yearfirst=True, dayfirst=False))

    def test_form_input(self):
        f = self.F(DummyPostData(a='2008/09/12 4:17 PM', b='04/05/06', c='04/05/06'))
        self.assertEqual(f.a.data, datetime(2008, 9, 12, 16, 17))
        self.assertEqual(f.a._value(), '2008/09/12 4:17 PM')
        self.assertEqual(f.b.data, date(2006, 4, 5))
        self.assertEqual(f.c.data, date(2004, 5, 6))
        self.assertTrue(f.validate())
        f = self.F(DummyPostData(a='Grok Grarg Rawr'))
        self.assertFalse(f.validate())

    def test_blank_input(self):
        f = self.F(DummyPostData(a='', b=''))
        self.assertEqual(f.a.data, None)
        self.assertEqual(f.b.data, None)
        self.assertFalse(f.validate())

    def test_defaults_display(self):
        f = self.F(a=datetime(2001, 11, 15))
        self.assertEqual(f.a.data, datetime(2001, 11, 15))
        self.assertEqual(f.a._value(), '2001-11-15 00:00')
        self.assertEqual(f.b.data, date(2004, 9, 12))
        self.assertEqual(f.b._value(), '2004-09-12')
        self.assertEqual(f.c.data, None)
        self.assertTrue(f.validate())

    def test_render(self):
        f = self.F()
        self.assertEqual(f.b(), r'<input id="b" name="b" type="text" value="2004-09-12">')

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
try:
    from localflavor.us.models import USStateField
except ImportError:
    from django.contrib.localflavor.us.models import USStateField


class Group(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return '%s(%d)' % (self.name, self.pk)

    __str__ = __unicode__


class User(models.Model):
    username = models.CharField(max_length=40)
    group    = models.ForeignKey(Group)
    birthday = models.DateField(help_text="Teh Birthday")
    email    = models.EmailField(blank=True)
    posts    = models.PositiveSmallIntegerField()
    state    = USStateField()
    reg_ip   = models.IPAddressField("IP Addy")
    url      = models.URLField()
    file     = models.FilePathField()
    file2    = models.FileField(upload_to='.')
    bool     = models.BooleanField()
    time1    = models.TimeField()
    slug     = models.SlugField()
    nullbool = models.NullBooleanField()

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals, absolute_import

import sys
import os
TESTS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, TESTS_DIR)

##########################################################################
# -- Django Initialization
#
# Unfortunately, we cannot do this in the setUp for a test case, as the
# settings.configure method cannot be called more than once, and we cannot
# control the order in which tests are run, so making a throwaway test won't
# work either.

from django.conf import settings
settings.configure(
    INSTALLED_APPS=[
        'ext_django', 'wtforms.ext.django',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes'
    ],
    # Django 1.0 to 1.3
    DATABASE_ENGINE='sqlite3',
    TEST_DATABASE_NAME=':memory:',
    LANGUAGE_CODE='es',
    # Django 1.4
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }
    }
)

from django.db import connection
connection.creation.create_test_db(verbosity=0)

# -- End hacky Django initialization

import datetime
from django.template import Context, Template, TemplateSyntaxError
from django.utils import timezone
from django.test import TestCase as DjangoTestCase
from django.test.utils import override_settings
from ext_django import models as test_models
from unittest import TestCase
from tests.common import DummyPostData, contains_validator, assert_raises_text
from wtforms import Form, fields, validators
from wtforms.compat import text_type
from wtforms.ext.django.orm import model_form
from wtforms.ext.django.fields import QuerySetSelectField, ModelSelectField, DateTimeField
from wtforms.ext.django import i18n
try:
    import pytz
    has_pytz = (pytz.VERSION >= '2012')
except ImportError:
    has_pytz = False


def lazy_select(field, **kwargs):
    output = []
    for val, label, selected in field.iter_choices():
        s = selected and 'Y' or 'N'
        output.append('%s:%s:%s' % (s, text_type(val), text_type(label)))
    return tuple(output)


class TemplateTagsTest(TestCase):
    load_tag = '{% load wtforms %}'

    class F(Form):
        a = fields.TextField('I r label')
        b = fields.SelectField(choices=[('a', 'hi'), ('b', 'bai')])

    def _render(self, source):
        t = Template(self.load_tag + source)
        return t.render(Context({'form': self.F(), 'a': self.F().a, 'someclass': "CLASSVAL>!"}))

    def test_simple_print(self):
        self.assertEqual(self._render('{% autoescape off %}{{ form.a }}{% endautoescape %}'), '<input id="a" name="a" type="text" value="">')
        self.assertEqual(self._render('{% autoescape off %}{{ form.a.label }}{% endautoescape %}'), '<label for="a">I r label</label>')
        self.assertEqual(self._render('{% autoescape off %}{{ form.a.name }}{% endautoescape %}'), 'a')

    def test_form_field(self):
        self.assertEqual(self._render('{% form_field form.a %}'), '<input id="a" name="a" type="text" value="">')
        self.assertEqual(
            self._render('{% form_field a class=someclass onclick="alert()" %}'),
            '<input class="CLASSVAL&gt;!" id="a" name="a" onclick="alert()" type="text" value="">'
        )
        self.assertEqual(
            self._render('''{% form_field a class='foo"bar"' %}'''),
            '<input class="foo&quot;bar&quot;" id="a" name="a" type="text" value="">'
        )

    @override_settings(TEMPLATE_STRING_IF_INVALID='__INVALID')
    def test_invalid(self):
        self.assertEqual(self._render('{% form_field form.c %}'), '__INVALID')
        self.assertEqual(
            self._render('{% form_field form.a foo=bar %}'),
            '<input foo="__INVALID" id="a" name="a" type="text" value="">'
        )

    def test_bad_syntax(self):
        with assert_raises_text(TemplateSyntaxError, '^.*must have the form field name as the first value.*$'):
            self._render('{% form_field %}')

        with assert_raises_text(TemplateSyntaxError, '^.*incorrect number of key=value arguments.$'):
            self._render('{% form_field foo=bar baz= quux=hello %}')


class ModelFormTest(TestCase):
    F = model_form(test_models.User, exclude=['id'], field_args={
        'posts': {
            'validators': [validators.NumberRange(min=4, max=7)],
            'description': 'Test'
        }
    })
    form = F()
    form_with_pk = model_form(test_models.User)()
    form_with_only = model_form(test_models.User, only=['nullbool', 'birthday'])()

    def test_form_sanity(self):
        self.assertEqual(self.F.__name__, 'UserForm')
        self.assertEqual(len([x for x in self.form]), 14)
        self.assertEqual(len([x for x in self.form_with_pk]), 15)
        self.assertEqual(len([x for x in self.form_with_only]), 2)

    def test_label(self):
        self.assertEqual(self.form.reg_ip.label.text, 'IP Addy')
        self.assertEqual(self.form.posts.label.text, 'posts')

    def test_description(self):
        self.assertEqual(self.form.birthday.description, 'Teh Birthday')

    def test_max_length(self):
        self.assertTrue(contains_validator(self.form.username, validators.Length))
        self.assertFalse(contains_validator(self.form.posts, validators.Length))

    def test_optional(self):
        self.assertTrue(contains_validator(self.form.email, validators.Optional))

    def test_simple_fields(self):
        self.assertEqual(type(self.form.file), fields.FileField)
        self.assertEqual(type(self.form.file2), fields.FileField)
        self.assertEqual(type(self.form_with_pk.id), fields.IntegerField)
        self.assertEqual(type(self.form.slug), fields.TextField)
        self.assertEqual(type(self.form.birthday), fields.DateField)

    def test_custom_converters(self):
        self.assertEqual(type(self.form.email), fields.TextField)
        self.assertTrue(contains_validator(self.form.email, validators.Email))
        self.assertEqual(type(self.form.reg_ip), fields.TextField)
        self.assertTrue(contains_validator(self.form.reg_ip, validators.IPAddress))
        self.assertEqual(type(self.form.group_id), ModelSelectField)

    def test_us_states(self):
        self.assertTrue(len(self.form.state.choices) >= 50)

    def test_field_args(self):
        self.assertTrue(contains_validator(self.form.posts, validators.NumberRange))
        self.assertEqual(self.form.posts.description, 'Test')

    def test_nullbool(self):
        field = self.form.nullbool
        assert isinstance(field, fields.SelectField)
        self.assertEqual(len(field.choices), 3)
        pairs = (('True', True), ('False', False), ('None', None), ('2', True), ('0', False))
        for input_val, expected in pairs:
            form = self.F(DummyPostData(nullbool=[input_val]))
            assert form.nullbool.data is expected


class QuerySetSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    def setUp(self):
        self.queryset = test_models.Group.objects.all()

        class F(Form):
            a = QuerySetSelectField(allow_blank=True, get_label='name', widget=lazy_select)
            b = QuerySetSelectField(queryset=self.queryset, widget=lazy_select)

        self.F = F

    def test_queryset_freshness(self):
        form = self.F()
        self.assertTrue(form.b.queryset is not self.queryset)

    def test_with_data(self):
        form = self.F()
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a(), ('Y:__None:', 'N:2:Admins'))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.validate(form), False)
        form.b.data = test_models.Group.objects.get(pk=1)
        self.assertEqual(form.b.validate(form), True)
        self.assertEqual(form.b(), ('Y:1:Users(1)', 'N:2:Admins(2)'))

    def test_formdata(self):
        form = self.F(DummyPostData(a=['1'], b=['3']))
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.validate(form), False)
        form = self.F(DummyPostData(a=['__None'], b=[2]))
        assert form.a.data is None
        self.assertEqual(form.b.data.pk, 2)
        self.assertEqual(form.b.validate(form), True)

    def test_get_label_alt(self):
        class TestForm(Form):
            a = QuerySetSelectField(queryset=self.queryset, widget=lazy_select, get_label=lambda x: x.name.upper())
        form = TestForm()
        self.assertEqual(form.a(), ('N:1:USERS', 'N:2:ADMINS'))


class ModelSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    class F(Form):
        a = ModelSelectField(model=test_models.Group, widget=lazy_select)

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), ('N:1:Users(1)', 'N:2:Admins(2)'))


class DateTimeFieldTimezoneTest(DjangoTestCase):

    class F(Form):
        a = DateTimeField()

    @override_settings(USE_TZ=True, TIME_ZONE='America/Los_Angeles')
    def test_convert_input_to_current_timezone(self):
        post_data = {'a': ['2013-09-24 00:00:00']}
        form = self.F(DummyPostData(post_data))
        self.assertTrue(form.validate())
        date = form.data['a']
        assert date.tzinfo
        self.assertEqual(
            timezone._get_timezone_name(date.tzinfo),
            timezone._get_timezone_name(timezone.get_current_timezone()))

    @override_settings(USE_TZ=True, TIME_ZONE='America/Los_Angeles')
    def test_stored_value_converted_to_current_timezone(self):
        if not has_pytz:
            # Ignore this test if we don't have pytz.
            return
        utc_date = datetime.datetime(2013, 9, 25, 2, 15, tzinfo=timezone.utc)
        form = self.F(a=utc_date)
        self.assertTrue('2013-09-24 19:15:00' in form.a())


class I18NTest(DjangoTestCase):
    def test_django_translations(self):
        trans = i18n.DjangoTranslations()
        self.assertEqual(trans.gettext('Username'), u'Nombre de usuario')
        check = lambda n: trans.ngettext('%(counter)s result', "%(counter)s results", n)
        self.assertEqual(check(1), '%(counter)s resultado')
        self.assertEqual(check(3), '%(counter)s resultados')

    def test_i18n_form(self):
        class F(i18n.Form):
            a = fields.IntegerField()

        form = F()
        assert isinstance(form._get_translations(), i18n.DjangoTranslations)
        self.assertEqual(form.a.gettext('Username'), u'Nombre de usuario')

########NEW FILE########
__FILENAME__ = ext_sqlalchemy
from __future__ import unicode_literals

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.schema import MetaData, Table, Column, ColumnDefault
from sqlalchemy.types import String, Integer, Numeric, Date, Text, Enum, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from unittest import TestCase

from wtforms.compat import text_type, iteritems
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms import Form, fields
from wtforms.ext.sqlalchemy.orm import model_form, ModelConversionError, ModelConverter
from wtforms.validators import Optional, Required
from tests.common import DummyPostData, contains_validator


class LazySelect(object):
    def __call__(self, field, **kwargs):
        return list((val, text_type(label), selected) for val, label, selected in field.iter_choices())


class Base(object):
    def __init__(self, **kwargs):
        for k, v in iteritems(kwargs):
            setattr(self, k, v)


class AnotherInteger(Integer):
    """Use me to test if MRO works like we want"""


class TestBase(TestCase):
    def _do_tables(self, mapper, engine):
        metadata = MetaData()

        test_table = Table(
            'test', metadata,
            Column('id', Integer, primary_key=True, nullable=False),
            Column('name', String, nullable=False),
        )

        pk_test_table = Table(
            'pk_test', metadata,
            Column('foobar', String, primary_key=True, nullable=False),
            Column('baz', String, nullable=False),
        )

        Test = type(str('Test'), (Base, ), {})
        PKTest = type(str('PKTest'), (Base, ), {
            '__unicode__': lambda x: x.baz,
            '__str__': lambda x: x.baz,
        })

        mapper(Test, test_table, order_by=[test_table.c.name])
        mapper(PKTest, pk_test_table, order_by=[pk_test_table.c.baz])
        self.Test = Test
        self.PKTest = PKTest

        metadata.create_all(bind=engine)

    def _fill(self, sess):
        for i, n in [(1, 'apple'), (2, 'banana')]:
            s = self.Test(id=i, name=n)
            p = self.PKTest(foobar='hello%s' % (i, ), baz=n)
            sess.add(s)
            sess.add(p)
        sess.flush()
        sess.commit()


class QuerySelectFieldTest(TestBase):
    def setUp(self):
        engine = create_engine('sqlite:///:memory:', echo=False)
        self.Session = sessionmaker(bind=engine)
        from sqlalchemy.orm import mapper
        self._do_tables(mapper, engine)

    def test_without_factory(self):
        sess = self.Session()
        self._fill(sess)

        class F(Form):
            a = QuerySelectField(get_label='name', widget=LazySelect(), get_pk=lambda x: x.id)
        form = F(DummyPostData(a=['1']))
        form.a.query = sess.query(self.Test)
        self.assertTrue(form.a.data is not None)
        self.assertEqual(form.a.data.id, 1)
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertTrue(form.validate())

        form = F(a=sess.query(self.Test).filter_by(name='banana').first())
        form.a.query = sess.query(self.Test).filter(self.Test.name != 'banana')
        assert not form.validate()
        self.assertEqual(form.a.errors, ['Not a valid choice'])

    def test_with_query_factory(self):
        sess = self.Session()
        self._fill(sess)

        class F(Form):
            a = QuerySelectField(get_label=(lambda model: model.name), query_factory=lambda: sess.query(self.Test), widget=LazySelect())
            b = QuerySelectField(allow_blank=True, query_factory=lambda: sess.query(self.PKTest), widget=LazySelect())

        form = F()
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a(), [('1', 'apple', False), ('2', 'banana', False)])
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b(), [('__None', '', True), ('hello1', 'apple', False), ('hello2', 'banana', False)])
        self.assertFalse(form.validate())

        form = F(DummyPostData(a=['1'], b=['hello2']))
        self.assertEqual(form.a.data.id, 1)
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertEqual(form.b.data.baz, 'banana')
        self.assertEqual(form.b(), [('__None', '', False), ('hello1', 'apple', False), ('hello2', 'banana', True)])
        self.assertTrue(form.validate())

        # Make sure the query is cached
        sess.add(self.Test(id=3, name='meh'))
        sess.flush()
        sess.commit()
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        form.a._object_list = None
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False), ('3', 'meh', False)])

        # Test bad data
        form = F(DummyPostData(b=['__None'], a=['fail']))
        assert not form.validate()
        self.assertEqual(form.a.errors, ['Not a valid choice'])
        self.assertEqual(form.b.errors, [])
        self.assertEqual(form.b.data, None)


class QuerySelectMultipleFieldTest(TestBase):
    def setUp(self):
        from sqlalchemy.orm import mapper
        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self._do_tables(mapper, engine)
        self.sess = Session()
        self._fill(self.sess)

    class F(Form):
        a = QuerySelectMultipleField(get_label='name', widget=LazySelect())

    def test_unpopulated_default(self):
        form = self.F()
        self.assertEqual([], form.a.data)

    def test_single_value_without_factory(self):
        form = self.F(DummyPostData(a=['1']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([1], [v.id for v in form.a.data])
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertTrue(form.validate())

    def test_multiple_values_without_query_factory(self):
        form = self.F(DummyPostData(a=['1', '2']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([1, 2], [v.id for v in form.a.data])
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', True)])
        self.assertTrue(form.validate())

        form = self.F(DummyPostData(a=['1', '3']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([x.id for x in form.a.data], [1])
        self.assertFalse(form.validate())

    def test_single_default_value(self):
        first_test = self.sess.query(self.Test).get(2)

        class F(Form):
            a = QuerySelectMultipleField(
                get_label='name', default=[first_test],
                widget=LazySelect(), query_factory=lambda: self.sess.query(self.Test)
            )
        form = F()
        self.assertEqual([v.id for v in form.a.data], [2])
        self.assertEqual(form.a(), [('1', 'apple', False), ('2', 'banana', True)])
        self.assertTrue(form.validate())


class ModelFormTest(TestCase):
    def setUp(self):
        Model = declarative_base()

        student_course = Table(
            'student_course', Model.metadata,
            Column('student_id', Integer, ForeignKey('student.id')),
            Column('course_id', Integer, ForeignKey('course.id'))
        )

        class Course(Model):
            __tablename__ = "course"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            # These are for better model form testing
            cost = Column(Numeric(5, 2), nullable=False)
            description = Column(Text, nullable=False)
            level = Column(Enum('Primary', 'Secondary'))
            has_prereqs = Column(Boolean, nullable=False)
            started = Column(DateTime, nullable=False)
            grade = Column(AnotherInteger, nullable=False)

        class School(Model):
            __tablename__ = "school"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)

        class Student(Model):
            __tablename__ = "student"
            id = Column(Integer, primary_key=True)
            full_name = Column(String(255), nullable=False, unique=True)
            dob = Column(Date(), nullable=True)
            current_school_id = Column(Integer, ForeignKey(School.id), nullable=False)

            current_school = relationship(School, backref=backref('students'))
            courses = relationship(
                "Course",
                secondary=student_course,
                backref=backref("students", lazy='dynamic')
            )

        self.School = School
        self.Student = Student
        self.Course = Course

        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self.metadata = Model.metadata
        self.metadata.create_all(bind=engine)
        self.sess = Session()

    def test_auto_validators(self):
        student_form = model_form(self.Student, self.sess)()
        assert contains_validator(student_form.dob, Optional)
        assert contains_validator(student_form.full_name, Required)

    def test_include_pk(self):
        form_class = model_form(self.Student, self.sess, exclude_pk=False)
        student_form = form_class()
        assert ('id' in student_form._fields)

    def test_exclude_pk(self):
        form_class = model_form(self.Student, self.sess, exclude_pk=True)
        student_form = form_class()
        assert ('id' not in student_form._fields)

    def test_exclude_fk(self):
        student_form = model_form(self.Student, self.sess)()
        assert ('current_school_id' not in student_form._fields)

    def test_include_fk(self):
        student_form = model_form(self.Student, self.sess, exclude_fk=False)()
        assert ('current_school_id' in student_form._fields)

    def test_convert_many_to_one(self):
        student_form = model_form(self.Student, self.sess)()
        assert isinstance(student_form.current_school, QuerySelectField)

    def test_convert_one_to_many(self):
        school_form = model_form(self.School, self.sess)()
        assert isinstance(school_form.students, QuerySelectMultipleField)

    def test_convert_many_to_many(self):
        student_form = model_form(self.Student, self.sess)()
        assert isinstance(student_form.courses, QuerySelectMultipleField)

    def test_convert_basic(self):
        self.assertRaises(TypeError, model_form, None)
        self.assertRaises(ModelConversionError, model_form, self.Course)
        form_class = model_form(self.Course, exclude=['students'])
        form = form_class()
        self.assertEqual(len(list(form)), 7)
        assert isinstance(form.cost, fields.DecimalField)
        assert isinstance(form.has_prereqs, fields.BooleanField)
        assert isinstance(form.started, fields.DateTimeField)

    def test_only(self):
        desired_fields = ['id', 'cost', 'description']
        form = model_form(self.Course, only=desired_fields)()
        self.assertEqual(len(list(form)), 2)
        form = model_form(self.Course, only=desired_fields, exclude_pk=False)()
        self.assertEqual(len(list(form)), 3)

    def test_no_mro(self):
        converter = ModelConverter(use_mro=False)
        # Without MRO, will not be able to convert 'grade'
        self.assertRaises(ModelConversionError, model_form, self.Course, self.sess, converter=converter)
        # If we exclude 'grade' everything should continue working
        F = model_form(self.Course, self.sess, exclude=['grade'], converter=converter)
        self.assertEqual(len(list(F())), 7)


class ModelFormColumnDefaultTest(TestCase):
    def setUp(self):
        Model = declarative_base()

        def default_score():
            return 5

        class StudentDefaultScoreCallable(Model):
            __tablename__ = "course"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            score = Column(Integer, default=default_score, nullable=False)

        class StudentDefaultScoreScalar(Model):
            __tablename__ = "school"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            # Default scalar value
            score = Column(Integer, default=10, nullable=False)

        self.StudentDefaultScoreCallable = StudentDefaultScoreCallable
        self.StudentDefaultScoreScalar = StudentDefaultScoreScalar

        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self.metadata = Model.metadata
        self.metadata.create_all(bind=engine)
        self.sess = Session()

    def test_column_default_callable(self):
        student_form = model_form(self.StudentDefaultScoreCallable, self.sess)()
        self.assertEqual(student_form._fields['score'].default, 5)

    def test_column_default_scalar(self):
        student_form = model_form(self.StudentDefaultScoreScalar, self.sess)()
        assert not isinstance(student_form._fields['score'].default, ColumnDefault)
        self.assertEqual(student_form._fields['score'].default, 10)

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

import sys

from datetime import date, datetime
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from unittest import TestCase

from wtforms import validators, widgets, meta
from wtforms.fields import *
from wtforms.fields import Label, Field, SelectFieldBase, html5
from wtforms.form import Form
from wtforms.compat import text_type
from wtforms.utils import unset_value
from tests.common import DummyPostData

PYTHON_VERSION = sys.version_info


class AttrDict(object):
    def __init__(self, *args, **kw):
        self.__dict__.update(*args, **kw)


def make_form(_name='F', **fields):
    return type(str(_name), (Form, ), fields)


class DefaultsTest(TestCase):
    def test(self):
        expected = 42

        def default_callable():
            return expected

        test_value = TextField(default=expected).bind(Form(), 'a')
        test_value.process(None)
        self.assertEqual(test_value.data, expected)

        test_callable = TextField(default=default_callable).bind(Form(), 'a')
        test_callable.process(None)
        self.assertEqual(test_callable.data, expected)


class LabelTest(TestCase):
    def test(self):
        expected = """<label for="test">Caption</label>"""
        label = Label('test', 'Caption')
        self.assertEqual(label(), expected)
        self.assertEqual(str(label), expected)
        self.assertEqual(text_type(label), expected)
        self.assertEqual(label.__html__(), expected)
        self.assertEqual(label().__html__(), expected)
        self.assertEqual(label('hello'), """<label for="test">hello</label>""")
        self.assertEqual(TextField('hi').bind(Form(), 'a').label.text, 'hi')
        if PYTHON_VERSION < (3,):
            self.assertEqual(repr(label), "Label(u'test', u'Caption')")
        else:
            self.assertEqual(repr(label), "Label('test', 'Caption')")
            self.assertEqual(label.__unicode__(), expected)

    def test_auto_label(self):
        t1 = TextField().bind(Form(), 'foo_bar')
        self.assertEqual(t1.label.text, 'Foo Bar')

        t2 = TextField('').bind(Form(), 'foo_bar')
        self.assertEqual(t2.label.text, '')

    def test_override_for(self):
        label = Label('test', 'Caption')
        self.assertEqual(label(for_='foo'), """<label for="foo">Caption</label>""")
        self.assertEqual(label(**{'for': 'bar'}), """<label for="bar">Caption</label>""")


class FlagsTest(TestCase):
    def setUp(self):
        t = TextField(validators=[validators.Required()]).bind(Form(), 'a')
        self.flags = t.flags

    def test_existing_values(self):
        self.assertEqual(self.flags.required, True)
        self.assertTrue('required' in self.flags)
        self.assertEqual(self.flags.optional, False)
        self.assertTrue('optional' not in self.flags)

    def test_assignment(self):
        self.assertTrue('optional' not in self.flags)
        self.flags.optional = True
        self.assertEqual(self.flags.optional, True)
        self.assertTrue('optional' in self.flags)

    def test_unset(self):
        self.flags.required = False
        self.assertEqual(self.flags.required, False)
        self.assertTrue('required' not in self.flags)

    def test_repr(self):
        self.assertEqual(repr(self.flags), '<wtforms.fields.Flags: {required}>')

    def test_underscore_property(self):
        self.assertRaises(AttributeError, getattr, self.flags, '_foo')
        self.flags._foo = 42
        self.assertEqual(self.flags._foo, 42)


class UnsetValueTest(TestCase):
    def test(self):
        self.assertEqual(str(unset_value), '<unset value>')
        self.assertEqual(repr(unset_value), '<unset value>')
        self.assertEqual(bool(unset_value), False)
        assert not unset_value
        self.assertEqual(unset_value.__nonzero__(), False)
        self.assertEqual(unset_value.__bool__(), False)


class FiltersTest(TestCase):
    class F(Form):
        a = TextField(default=' hello', filters=[lambda x: x.strip()])
        b = TextField(default='42', filters=[int, lambda x: -x])

    def test_working(self):
        form = self.F()
        self.assertEqual(form.a.data, 'hello')
        self.assertEqual(form.b.data, -42)
        assert form.validate()

    def test_failure(self):
        form = self.F(DummyPostData(a=['  foo bar  '], b=['hi']))
        self.assertEqual(form.a.data, 'foo bar')
        self.assertEqual(form.b.data, 'hi')
        self.assertEqual(len(form.b.process_errors), 1)
        assert not form.validate()


class FieldTest(TestCase):
    class F(Form):
        a = TextField(default='hello')

    def setUp(self):
        self.field = self.F().a

    def test_unbound_field(self):
        unbound = self.F.a
        assert unbound.creation_counter != 0
        assert unbound.field_class is TextField
        self.assertEqual(unbound.args, ())
        self.assertEqual(unbound.kwargs, {'default': 'hello'})
        assert repr(unbound).startswith('<UnboundField(TextField')

    def test_htmlstring(self):
        self.assertTrue(isinstance(self.field.__html__(), widgets.HTMLString))

    def test_str_coerce(self):
        self.assertTrue(isinstance(str(self.field), str))
        self.assertEqual(str(self.field), str(self.field()))

    def test_unicode_coerce(self):
        self.assertEqual(text_type(self.field), self.field())

    def test_process_formdata(self):
        Field.process_formdata(self.field, [42])
        self.assertEqual(self.field.data, 42)

    def test_meta_attribute(self):
        # Can we pass in meta via _form?
        form = self.F()
        assert form.a.meta is form.meta

        # Can we pass in meta via _meta?
        form_meta = meta.DefaultMeta()
        field = TextField(_name='Foo', _form=None, _meta=form_meta)
        assert field.meta is form_meta

        # Do we fail if both _meta and _form are None?
        self.assertRaises(TypeError, TextField, _name='foo', _form=None)


class PrePostTestField(TextField):
    def pre_validate(self, form):
        if self.data == "stoponly":
            raise validators.StopValidation()
        elif self.data.startswith("stop"):
            raise validators.StopValidation("stop with message")

    def post_validate(self, form, stopped):
        if self.data == "p":
            raise ValueError("Post")
        elif stopped and self.data == "stop-post":
            raise ValueError("Post-stopped")


class PrePostValidationTest(TestCase):
    class F(Form):
        a = PrePostTestField(validators=[validators.Length(max=1, message="too long")])

    def _init_field(self, value):
        form = self.F(a=value)
        form.validate()
        return form.a

    def test_pre_stop(self):
        a = self._init_field("long")
        self.assertEqual(a.errors, ["too long"])

        stoponly = self._init_field("stoponly")
        self.assertEqual(stoponly.errors, [])

        stopmessage = self._init_field("stopmessage")
        self.assertEqual(stopmessage.errors, ["stop with message"])

    def test_post(self):
        a = self._init_field("p")
        self.assertEqual(a.errors, ["Post"])
        stopped = self._init_field("stop-post")
        self.assertEqual(stopped.errors, ["stop with message", "Post-stopped"])


class SelectFieldTest(TestCase):
    class F(Form):
        a = SelectField(choices=[('a', 'hello'), ('btest', 'bye')], default='a')
        b = SelectField(choices=[(1, 'Item 1'), (2, 'Item 2')], coerce=int, option_widget=widgets.TextInput())

    def test_defaults(self):
        form = self.F()
        self.assertEqual(form.a.data, 'a')
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.validate(), False)
        self.assertEqual(form.a(), """<select id="a" name="a"><option selected value="a">hello</option><option value="btest">bye</option></select>""")
        self.assertEqual(form.b(), """<select id="b" name="b"><option value="1">Item 1</option><option value="2">Item 2</option></select>""")

    def test_with_data(self):
        form = self.F(DummyPostData(a=['btest']))
        self.assertEqual(form.a.data, 'btest')
        self.assertEqual(form.a(), """<select id="a" name="a"><option value="a">hello</option><option selected value="btest">bye</option></select>""")

    def test_value_coercion(self):
        form = self.F(DummyPostData(b=['2']))
        self.assertEqual(form.b.data, 2)
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(b=['b']))
        self.assertEqual(form.b.data, None)
        self.assertFalse(form.b.validate(form))

    def test_iterable_options(self):
        form = self.F()
        first_option = list(form.a)[0]
        self.assertTrue(isinstance(first_option, form.a._Option))
        self.assertEqual(
            list(text_type(x) for x in form.a),
            ['<option selected value="a">hello</option>', '<option value="btest">bye</option>']
        )
        self.assertTrue(isinstance(first_option.widget, widgets.Option))
        self.assertTrue(isinstance(list(form.b)[0].widget, widgets.TextInput))
        self.assertEqual(first_option(disabled=True), '<option disabled selected value="a">hello</option>')

    def test_default_coerce(self):
        F = make_form(a=SelectField(choices=[('a', 'Foo')]))
        form = F(DummyPostData(a=[]))
        assert not form.validate()
        self.assertEqual(form.a.data, 'None')
        self.assertEqual(len(form.a.errors), 1)
        self.assertEqual(form.a.errors[0], 'Not a valid choice')


class SelectMultipleFieldTest(TestCase):
    class F(Form):
        a = SelectMultipleField(choices=[('a', 'hello'), ('b', 'bye'), ('c', 'something')], default=('a', ))
        b = SelectMultipleField(coerce=int, choices=[(1, 'A'), (2, 'B'), (3, 'C')], default=("1", "3"))

    def test_defaults(self):
        form = self.F()
        self.assertEqual(form.a.data, ['a'])
        self.assertEqual(form.b.data, [1, 3])
        # Test for possible regression with null data
        form.a.data = None
        self.assertTrue(form.validate())
        self.assertEqual(list(form.a.iter_choices()), [(v, l, False) for v, l in form.a.choices])

    def test_with_data(self):
        form = self.F(DummyPostData(a=['a', 'c']))
        self.assertEqual(form.a.data, ['a', 'c'])
        self.assertEqual(list(form.a.iter_choices()), [('a', 'hello', True), ('b', 'bye', False), ('c', 'something', True)])
        self.assertEqual(form.b.data, [])
        form = self.F(DummyPostData(b=['1', '2']))
        self.assertEqual(form.b.data, [1, 2])
        self.assertTrue(form.validate())
        form = self.F(DummyPostData(b=['1', '2', '4']))
        self.assertEqual(form.b.data, [1, 2, 4])
        self.assertFalse(form.validate())

    def test_coerce_fail(self):
        form = self.F(b=['a'])
        assert form.validate()
        self.assertEqual(form.b.data, None)
        form = self.F(DummyPostData(b=['fake']))
        assert not form.validate()
        self.assertEqual(form.b.data, [1, 3])


class RadioFieldTest(TestCase):
    class F(Form):
        a = RadioField(choices=[('a', 'hello'), ('b', 'bye')], default='a')
        b = RadioField(choices=[(1, 'Item 1'), (2, 'Item 2')], coerce=int)

    def test(self):
        form = self.F()
        self.assertEqual(form.a.data, 'a')
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.validate(), False)
        self.assertEqual(
            form.a(),
            (
                """<ul id="a">"""
                """<li><input checked id="a-0" name="a" type="radio" value="a"> <label for="a-0">hello</label></li>"""
                """<li><input id="a-1" name="a" type="radio" value="b"> <label for="a-1">bye</label></li></ul>"""
            )
        )
        self.assertEqual(
            form.b(),
            (
                """<ul id="b">"""
                """<li><input id="b-0" name="b" type="radio" value="1"> <label for="b-0">Item 1</label></li>"""
                """<li><input id="b-1" name="b" type="radio" value="2"> <label for="b-1">Item 2</label></li></ul>"""
            )
        )
        self.assertEqual(
            [text_type(x) for x in form.a],
            ['<input checked id="a-0" name="a" type="radio" value="a">', '<input id="a-1" name="a" type="radio" value="b">']
        )

    def test_text_coercion(self):
        # Regression test for text coercsion scenarios where the value is a boolean.
        coerce_func = lambda x: False if x == 'False' else bool(x)
        F = make_form(a=RadioField(choices=[(True, 'yes'), (False, 'no')], coerce=coerce_func))
        form = F()
        self.assertEqual(
            form.a(),
            '''<ul id="a">'''
            '''<li><input id="a-0" name="a" type="radio" value="True"> <label for="a-0">yes</label></li>'''
            '''<li><input checked id="a-1" name="a" type="radio" value="False"> <label for="a-1">no</label></li></ul>'''
        )


class TextFieldTest(TestCase):
    class F(Form):
        a = TextField()

    def test(self):
        form = self.F()
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="">""")
        form = self.F(DummyPostData(a=['hello']))
        self.assertEqual(form.a.data, 'hello')
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="hello">""")
        form = self.F(DummyPostData(b=['hello']))
        self.assertEqual(form.a.data, '')


class HiddenFieldTest(TestCase):
    class F(Form):
        a = HiddenField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="hidden" value="LE DEFAULT">""")


class TextAreaFieldTest(TestCase):
    class F(Form):
        a = TextAreaField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<textarea id="a" name="a">LE DEFAULT</textarea>""")


class PasswordFieldTest(TestCase):
    class F(Form):
        a = PasswordField(widget=widgets.PasswordInput(hide_value=False), default="LE DEFAULT")
        b = PasswordField(default="Hai")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="password" value="LE DEFAULT">""")
        self.assertEqual(form.b(), """<input id="b" name="b" type="password" value="">""")


class FileFieldTest(TestCase):
    class F(Form):
        a = FileField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="file">""")


class IntegerFieldTest(TestCase):
    class F(Form):
        a = IntegerField()
        b = IntegerField(default=48)

    def test(self):
        form = self.F(DummyPostData(a=['v'], b=['-15']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['v'])
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="v">""")
        self.assertEqual(form.b.data, -15)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="-15">""")
        self.assertTrue(not form.a.validate(form))
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(a=[], b=['']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, [])
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.raw_data, [''])
        self.assertTrue(not form.validate())
        self.assertEqual(len(form.b.process_errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        form = self.F(b=9)
        self.assertEqual(form.b.data, 9)
        self.assertEqual(form.a._value(), '')
        self.assertEqual(form.b._value(), '9')


class DecimalFieldTest(TestCase):
    def test(self):
        F = make_form(a=DecimalField())
        form = F(DummyPostData(a='2.1'))
        self.assertEqual(form.a.data, Decimal('2.1'))
        self.assertEqual(form.a._value(), '2.1')
        form.a.raw_data = None
        self.assertEqual(form.a._value(), '2.10')
        self.assertTrue(form.validate())
        form = F(DummyPostData(a='2,1'), a=Decimal(5))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['2,1'])
        self.assertFalse(form.validate())
        form = F(DummyPostData(a='asdf'), a=Decimal('.21'))
        self.assertEqual(form.a._value(), 'asdf')
        assert not form.validate()

    def test_quantize(self):
        F = make_form(a=DecimalField(places=3, rounding=ROUND_UP), b=DecimalField(places=None))
        form = F(a=Decimal('3.1415926535'))
        self.assertEqual(form.a._value(), '3.142')
        form.a.rounding = ROUND_DOWN
        self.assertEqual(form.a._value(), '3.141')
        self.assertEqual(form.b._value(), '')
        form = F(a=3.14159265, b=72)
        self.assertEqual(form.a._value(), '3.142')
        self.assertTrue(isinstance(form.a.data, float))
        self.assertEqual(form.b._value(), '72')


class FloatFieldTest(TestCase):
    class F(Form):
        a = FloatField()
        b = FloatField(default=48.0)

    def test(self):
        form = self.F(DummyPostData(a=['v'], b=['-15.0']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['v'])
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="v">""")
        self.assertEqual(form.b.data, -15.0)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="-15.0">""")
        self.assertFalse(form.a.validate(form))
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(a=[], b=['']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a._value(), '')
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.raw_data, [''])
        self.assertFalse(form.validate())
        self.assertEqual(len(form.b.process_errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        form = self.F(b=9.0)
        self.assertEqual(form.b.data, 9.0)
        self.assertEqual(form.b._value(), "9.0")


class BooleanFieldTest(TestCase):
    class BoringForm(Form):
        bool1 = BooleanField()
        bool2 = BooleanField(default=True, false_values=())

    obj = AttrDict(bool1=None, bool2=True)

    def test_defaults(self):
        # Test with no post data to make sure defaults work
        form = self.BoringForm()
        self.assertEqual(form.bool1.raw_data, None)
        self.assertEqual(form.bool1.data, False)
        self.assertEqual(form.bool2.data, True)

    def test_rendering(self):
        form = self.BoringForm(DummyPostData(bool2="x"))
        self.assertEqual(form.bool1(), '<input id="bool1" name="bool1" type="checkbox" value="y">')
        self.assertEqual(form.bool2(), '<input checked id="bool2" name="bool2" type="checkbox" value="x">')
        self.assertEqual(form.bool2.raw_data, ['x'])

    def test_with_postdata(self):
        form = self.BoringForm(DummyPostData(bool1=['a']))
        self.assertEqual(form.bool1.raw_data, ['a'])
        self.assertEqual(form.bool1.data, True)
        form = self.BoringForm(DummyPostData(bool1=['false'], bool2=['false']))
        self.assertEqual(form.bool1.data, False)
        self.assertEqual(form.bool2.data, True)

    def test_with_model_data(self):
        form = self.BoringForm(obj=self.obj)
        self.assertEqual(form.bool1.data, False)
        self.assertEqual(form.bool1.raw_data, None)
        self.assertEqual(form.bool2.data, True)

    def test_with_postdata_and_model(self):
        form = self.BoringForm(DummyPostData(bool1=['y']), obj=self.obj)
        self.assertEqual(form.bool1.data, True)
        self.assertEqual(form.bool2.data, False)


class DateFieldTest(TestCase):
    class F(Form):
        a = DateField()
        b = DateField(format='%m/%d %Y')

    def test_basic(self):
        d = date(2008, 5, 7)
        form = self.F(DummyPostData(a=['2008-05-07'], b=['05/07', '2008']))
        self.assertEqual(form.a.data, d)
        self.assertEqual(form.a._value(), '2008-05-07')
        self.assertEqual(form.b.data, d)
        self.assertEqual(form.b._value(), '05/07 2008')

    def test_failure(self):
        form = self.F(DummyPostData(a=['2008-bb-cc'], b=['hi']))
        assert not form.validate()
        self.assertEqual(len(form.a.process_errors), 1)
        self.assertEqual(len(form.a.errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        self.assertEqual(form.a.process_errors[0], 'Not a valid date value')


class DateTimeFieldTest(TestCase):
    class F(Form):
        a = DateTimeField()
        b = DateTimeField(format='%Y-%m-%d %H:%M')

    def test_basic(self):
        d = datetime(2008, 5, 5, 4, 30, 0, 0)
        # Basic test with both inputs
        form = self.F(DummyPostData(a=['2008-05-05', '04:30:00'], b=['2008-05-05 04:30']))
        self.assertEqual(form.a.data, d)
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="2008-05-05 04:30:00">""")
        self.assertEqual(form.b.data, d)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="2008-05-05 04:30">""")
        self.assertTrue(form.validate())

        # Test with a missing input
        form = self.F(DummyPostData(a=['2008-05-05']))
        self.assertFalse(form.validate())
        self.assertEqual(form.a.errors[0], 'Not a valid datetime value')

        form = self.F(a=d, b=d)
        self.assertTrue(form.validate())
        self.assertEqual(form.a._value(), '2008-05-05 04:30:00')

    def test_microseconds(self):
        d = datetime(2011, 5, 7, 3, 23, 14, 424200)
        F = make_form(a=DateTimeField(format='%Y-%m-%d %H:%M:%S.%f'))
        form = F(DummyPostData(a=['2011-05-07 03:23:14.4242']))
        self.assertEqual(d, form.a.data)


class SubmitFieldTest(TestCase):
    class F(Form):
        a = SubmitField('Label')

    def test(self):
        self.assertEqual(self.F().a(), """<input id="a" name="a" type="submit" value="Label">""")


class FormFieldTest(TestCase):
    def setUp(self):
        F = make_form(
            a=TextField(validators=[validators.required()]),
            b=TextField(),
        )
        self.F1 = make_form('F1', a=FormField(F))
        self.F2 = make_form('F2', a=FormField(F, separator='::'))

    def test_formdata(self):
        form = self.F1(DummyPostData({'a-a': ['moo']}))
        self.assertEqual(form.a.form.a.name, 'a-a')
        self.assertEqual(form.a['a'].data, 'moo')
        self.assertEqual(form.a['b'].data, '')
        self.assertTrue(form.validate())

    def test_iteration(self):
        self.assertEqual([x.name for x in self.F1().a], ['a-a', 'a-b'])

    def test_with_obj(self):
        obj = AttrDict(a=AttrDict(a='mmm'))
        form = self.F1(obj=obj)
        self.assertEqual(form.a.form.a.data, 'mmm')
        self.assertEqual(form.a.form.b.data, None)
        obj_inner = AttrDict(a=None, b='rawr')
        obj2 = AttrDict(a=obj_inner)
        form.populate_obj(obj2)
        self.assertTrue(obj2.a is obj_inner)
        self.assertEqual(obj_inner.a, 'mmm')
        self.assertEqual(obj_inner.b, None)

    def test_widget(self):
        self.assertEqual(
            self.F1().a(),
            '''<table id="a">'''
            '''<tr><th><label for="a-a">A</label></th><td><input id="a-a" name="a-a" type="text" value=""></td></tr>'''
            '''<tr><th><label for="a-b">B</label></th><td><input id="a-b" name="a-b" type="text" value=""></td></tr>'''
            '''</table>'''
        )

    def test_separator(self):
        form = self.F2(DummyPostData({'a-a': 'fake', 'a::a': 'real'}))
        self.assertEqual(form.a.a.name, 'a::a')
        self.assertEqual(form.a.a.data, 'real')
        self.assertTrue(form.validate())

    def test_no_validators_or_filters(self):
        class A(Form):
            a = FormField(self.F1, validators=[validators.required()])
        self.assertRaises(TypeError, A)

        class B(Form):
            a = FormField(self.F1, filters=[lambda x: x])
        self.assertRaises(TypeError, B)

        class C(Form):
            a = FormField(self.F1)

            def validate_a(form, field):
                pass
        form = C()
        self.assertRaises(TypeError, form.validate)

    def test_populate_missing_obj(self):
        obj = AttrDict(a=None)
        obj2 = AttrDict(a=AttrDict(a='mmm'))
        form = self.F1()
        self.assertRaises(TypeError, form.populate_obj, obj)
        form.populate_obj(obj2)


class FieldListTest(TestCase):
    t = TextField(validators=[validators.Required()])

    def test_form(self):
        F = make_form(a=FieldList(self.t))
        data = ['foo', 'hi', 'rawr']
        a = F(a=data).a
        self.assertEqual(a.entries[1].data, 'hi')
        self.assertEqual(a.entries[1].name, 'a-1')
        self.assertEqual(a.data, data)
        self.assertEqual(len(a.entries), 3)

        pdata = DummyPostData({'a-0': ['bleh'], 'a-3': ['yarg'], 'a-4': [''], 'a-7': ['mmm']})
        form = F(pdata)
        self.assertEqual(len(form.a.entries), 4)
        self.assertEqual(form.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(form.validate())

        form = F(pdata, a=data)
        self.assertEqual(form.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(form.validate())

        # Test for formdata precedence
        pdata = DummyPostData({'a-0': ['a'], 'a-1': ['b']})
        form = F(pdata, a=data)
        self.assertEqual(len(form.a.entries), 2)
        self.assertEqual(form.a.data, ['a', 'b'])
        self.assertEqual(list(iter(form.a)), list(form.a.entries))

    def test_enclosed_subform(self):
        make_inner = lambda: AttrDict(a=None)
        F = make_form(
            a=FieldList(FormField(make_form('FChild', a=self.t), default=make_inner))
        )
        data = [{'a': 'hello'}]
        form = F(a=data)
        self.assertEqual(form.a.data, data)
        self.assertTrue(form.validate())
        form.a.append_entry()
        self.assertEqual(form.a.data, data + [{'a': None}])
        self.assertFalse(form.validate())

        pdata = DummyPostData({'a-0': ['fake'], 'a-0-a': ['foo'], 'a-1-a': ['bar']})
        form = F(pdata, a=data)
        self.assertEqual(form.a.data, [{'a': 'foo'}, {'a': 'bar'}])

        inner_obj = make_inner()
        inner_list = [inner_obj]
        obj = AttrDict(a=inner_list)
        form.populate_obj(obj)
        self.assertTrue(obj.a is not inner_list)
        self.assertEqual(len(obj.a), 2)
        self.assertTrue(obj.a[0] is inner_obj)
        self.assertEqual(obj.a[0].a, 'foo')
        self.assertEqual(obj.a[1].a, 'bar')

        # Test failure on populate
        obj2 = AttrDict(a=42)
        self.assertRaises(TypeError, form.populate_obj, obj2)

    def test_entry_management(self):
        F = make_form(a=FieldList(self.t))
        a = F(a=['hello', 'bye']).a
        self.assertEqual(a.pop_entry().name, 'a-1')
        self.assertEqual(a.data, ['hello'])
        a.append_entry('orange')
        self.assertEqual(a.data, ['hello', 'orange'])
        self.assertEqual(a[-1].name, 'a-1')
        self.assertEqual(a.pop_entry().data, 'orange')
        self.assertEqual(a.pop_entry().name, 'a-0')
        self.assertRaises(IndexError, a.pop_entry)

    def test_min_max_entries(self):
        F = make_form(a=FieldList(self.t, min_entries=1, max_entries=3))
        a = F().a
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].data, None)
        big_input = ['foo', 'flaf', 'bar', 'baz']
        self.assertRaises(AssertionError, F, a=big_input)
        pdata = DummyPostData(('a-%d' % i, v) for i, v in enumerate(big_input))
        a = F(pdata).a
        self.assertEqual(a.data, ['foo', 'flaf', 'bar'])
        self.assertRaises(AssertionError, a.append_entry)

    def test_validators(self):
        def validator(form, field):
            if field.data and field.data[0] == 'fail':
                raise ValueError('fail')
            elif len(field.data) > 2:
                raise ValueError('too many')

        F = make_form(a=FieldList(self.t, validators=[validator]))

        # Case 1: length checking validators work as expected.
        fdata = DummyPostData({'a-0': ['hello'], 'a-1': ['bye'], 'a-2': ['test3']})
        form = F(fdata)
        assert not form.validate()
        self.assertEqual(form.a.errors, ['too many'])

        # Case 2: checking a value within.
        fdata['a-0'] = ['fail']
        form = F(fdata)
        assert not form.validate()
        self.assertEqual(form.a.errors, ['fail'])

        # Case 3: normal field validator still works
        form = F(DummyPostData({'a-0': ['']}))
        assert not form.validate()
        self.assertEqual(form.a.errors, [['This field is required.']])

    def test_no_filters(self):
        my_filter = lambda x: x
        self.assertRaises(TypeError, FieldList, self.t, filters=[my_filter], _form=Form(), _name='foo')

    def test_process_prefilled(self):
        data = ['foo', 'hi', 'rawr']

        class A(object):
            def __init__(self, a):
                self.a = a
        obj = A(data)
        F = make_form(a=FieldList(self.t))
        # fill form
        form = F(obj=obj)
        self.assertEqual(len(form.a.entries), 3)
        # pretend to submit form unchanged
        pdata = DummyPostData({
            'a-0': ['foo'],
            'a-1': ['hi'],
            'a-2': ['rawr']})
        form.process(formdata=pdata)
        # check if data still the same
        self.assertEqual(len(form.a.entries), 3)
        self.assertEqual(form.a.data, data)


class MyCustomField(TextField):
    def process_data(self, data):
        if data == 'fail':
            raise ValueError('Contrived Failure')

        return super(MyCustomField, self).process_data(data)


class CustomFieldQuirksTest(TestCase):
    class F(Form):
        a = MyCustomField()
        b = SelectFieldBase()

    def test_processing_failure(self):
        form = self.F(a='42')
        assert form.validate()
        form = self.F(a='fail')
        assert not form.validate()

    def test_default_impls(self):
        f = self.F()
        self.assertRaises(NotImplementedError, f.b.iter_choices)


class HTML5FieldsTest(TestCase):
    class F(Form):
        search = html5.SearchField()
        telephone = html5.TelField()
        url = html5.URLField()
        email = html5.EmailField()
        datetime = html5.DateTimeField()
        date = html5.DateField()
        dt_local = html5.DateTimeLocalField()
        integer = html5.IntegerField()
        decimal = html5.DecimalField()
        int_range = html5.IntegerRangeField()
        decimal_range = html5.DecimalRangeField()

    def _build_value(self, key, form_input, expected_html, data=unset_value):
        if data is unset_value:
            data = form_input
        if expected_html.startswith('type='):
            expected_html = '<input id="%s" name="%s" %s value="%s">' % (key, key, expected_html, form_input)
        return {
            'key': key,
            'form_input': form_input,
            'expected_html': expected_html,
            'data': data
        }

    def test_simple(self):
        b = self._build_value
        VALUES = (
            b('search', 'search', 'type="search"'),
            b('telephone', '123456789', 'type="tel"'),
            b('url', 'http://wtforms.simplecodes.com/', 'type="url"'),
            b('email', 'foo@bar.com', 'type="email"'),
            b('datetime', '2013-09-05 00:23:42', 'type="datetime"', datetime(2013, 9, 5, 0, 23, 42)),
            b('date', '2013-09-05', 'type="date"', date(2013, 9, 5)),
            b('dt_local', '2013-09-05 00:23:42', 'type="datetime-local"', datetime(2013, 9, 5, 0, 23, 42)),
            b('integer', '42', '<input id="integer" name="integer" step="1" type="number" value="42">', 42),
            b('decimal', '43.5', '<input id="decimal" name="decimal" step="any" type="number" value="43.5">', Decimal('43.5')),
            b('int_range', '4', '<input id="int_range" name="int_range" step="1" type="range" value="4">', 4),
            b('decimal_range', '58', '<input id="decimal_range" name="decimal_range" step="any" type="range" value="58">', 58),
        )
        formdata = DummyPostData()
        kw = {}
        for item in VALUES:
            formdata[item['key']] = item['form_input']
            kw[item['key']] = item['data']

        form = self.F(formdata)
        for item in VALUES:
            field = form[item['key']]
            render_value = field()
            if render_value != item['expected_html']:
                tmpl = 'Field {key} render mismatch: {render_value!r} != {expected_html!r}'
                raise AssertionError(tmpl.format(render_value=render_value, **item))
            if field.data != item['data']:
                tmpl = 'Field {key} data mismatch: {field.data!r} != {data!r}'
                raise AssertionError(tmpl.format(field=field, **item))

########NEW FILE########
__FILENAME__ = form
from __future__ import unicode_literals

from unittest import TestCase

from wtforms.form import BaseForm, Form
from wtforms.meta import DefaultMeta
from wtforms.fields import TextField, IntegerField
from wtforms.validators import ValidationError
from tests.common import DummyPostData


class BaseFormTest(TestCase):
    def get_form(self, **kwargs):
        def validate_test(form, field):
            if field.data != 'foobar':
                raise ValidationError('error')

        return BaseForm({'test': TextField(validators=[validate_test])}, **kwargs)

    def test_data_proxy(self):
        form = self.get_form()
        form.process(test='foo')
        self.assertEqual(form.data, {'test': 'foo'})

    def test_errors_proxy(self):
        form = self.get_form()
        form.process(test='foobar')
        form.validate()
        self.assertEqual(form.errors, {})

        form = self.get_form()
        form.process()
        form.validate()
        self.assertEqual(form.errors, {'test': ['error']})

    def test_contains(self):
        form = self.get_form()
        self.assertTrue('test' in form)
        self.assertTrue('abcd' not in form)

    def test_field_removal(self):
        form = self.get_form()
        del form['test']
        self.assertRaises(AttributeError, getattr, form, 'test')
        self.assertTrue('test' not in form)

    def test_field_adding(self):
        form = self.get_form()
        self.assertEqual(len(list(form)), 1)
        form['foo'] = TextField()
        self.assertEqual(len(list(form)), 2)
        form.process(DummyPostData(foo=['hello']))
        self.assertEqual(form['foo'].data, 'hello')
        form['test'] = IntegerField()
        self.assertTrue(isinstance(form['test'], IntegerField))
        self.assertEqual(len(list(form)), 2)
        self.assertRaises(AttributeError, getattr, form['test'], 'data')
        form.process(DummyPostData(test=['1']))
        self.assertEqual(form['test'].data, 1)
        self.assertEqual(form['foo'].data, '')

    def test_populate_obj(self):
        m = type(str('Model'), (object, ), {})
        form = self.get_form()
        form.process(test='foobar')
        form.populate_obj(m)
        self.assertEqual(m.test, 'foobar')
        self.assertEqual([k for k in dir(m) if not k.startswith('_')], ['test'])

    def test_prefixes(self):
        form = self.get_form(prefix='foo')
        self.assertEqual(form['test'].name, 'foo-test')
        self.assertEqual(form['test'].short_name, 'test')
        self.assertEqual(form['test'].id, 'foo-test')
        form = self.get_form(prefix='foo.')
        form.process(DummyPostData({'foo.test': ['hello'], 'test': ['bye']}))
        self.assertEqual(form['test'].data, 'hello')
        self.assertEqual(self.get_form(prefix='foo[')['test'].name, 'foo[-test')

    def test_formdata_wrapper_error(self):
        form = self.get_form()
        self.assertRaises(TypeError, form.process, [])


class FormMetaTest(TestCase):
    def test_monkeypatch(self):
        class F(Form):
            a = TextField()

        self.assertEqual(F._unbound_fields, None)
        F()
        self.assertEqual(F._unbound_fields, [('a', F.a)])
        F.b = TextField()
        self.assertEqual(F._unbound_fields, None)
        F()
        self.assertEqual(F._unbound_fields, [('a', F.a), ('b', F.b)])
        del F.a
        self.assertRaises(AttributeError, lambda: F.a)
        F()
        self.assertEqual(F._unbound_fields, [('b', F.b)])
        F._m = TextField()
        self.assertEqual(F._unbound_fields, [('b', F.b)])

    def test_subclassing(self):
        class A(Form):
            a = TextField()
            c = TextField()

        class B(A):
            b = TextField()
            c = TextField()
        A()
        B()

        self.assertTrue(A.a is B.a)
        self.assertTrue(A.c is not B.c)
        self.assertEqual(A._unbound_fields, [('a', A.a), ('c', A.c)])
        self.assertEqual(B._unbound_fields, [('a', B.a), ('b', B.b), ('c', B.c)])

    def test_class_meta_reassign(self):
        class MetaA:
            pass

        class MetaB:
            pass

        class F(Form):
            Meta = MetaA

        self.assertEqual(F._wtforms_meta, None)
        assert isinstance(F().meta, MetaA)
        assert issubclass(F._wtforms_meta, MetaA)
        F.Meta = MetaB
        self.assertEqual(F._wtforms_meta, None)
        assert isinstance(F().meta, MetaB)
        assert issubclass(F._wtforms_meta, MetaB)


class FormTest(TestCase):
    class F(Form):
        test = TextField()

        def validate_test(form, field):
            if field.data != 'foobar':
                raise ValidationError('error')

    def test_validate(self):
        form = self.F(test='foobar')
        self.assertEqual(form.validate(), True)

        form = self.F()
        self.assertEqual(form.validate(), False)

    def test_field_adding_disabled(self):
        form = self.F()
        self.assertRaises(TypeError, form.__setitem__, 'foo', TextField())

    def test_field_removal(self):
        form = self.F()
        del form.test
        self.assertTrue('test' not in form)
        self.assertEqual(form.test, None)
        self.assertEqual(len(list(form)), 0)
        # Try deleting a nonexistent field
        self.assertRaises(AttributeError, form.__delattr__, 'fake')

    def test_delattr_idempotency(self):
        form = self.F()
        del form.test
        self.assertEqual(form.test, None)

        # Make sure deleting a normal attribute works
        form.foo = 9
        del form.foo
        self.assertRaises(AttributeError, form.__delattr__, 'foo')

        # Check idempotency
        del form.test
        self.assertEqual(form.test, None)

    def test_ordered_fields(self):
        class MyForm(Form):
            strawberry = TextField()
            banana = TextField()
            kiwi = TextField()

        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi'])
        MyForm.apple = TextField()
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi', 'apple'])
        del MyForm.banana
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'kiwi', 'apple'])
        MyForm.strawberry = TextField()
        self.assertEqual([x.name for x in MyForm()], ['kiwi', 'apple', 'strawberry'])
        # Ensure sort is stable: two fields with the same creation counter
        # should be subsequently sorted by name.
        MyForm.cherry = MyForm.kiwi
        self.assertEqual([x.name for x in MyForm()], ['cherry', 'kiwi', 'apple', 'strawberry'])

    def test_data_arg(self):
        data = {'test': 'foo'}
        form = self.F(data=data)
        self.assertEqual(form.test.data, 'foo')
        form = self.F(data=data, test='bar')
        self.assertEqual(form.test.data, 'bar')


class MetaTest(TestCase):
    class F(Form):
        class Meta:
            foo = 9

        test = TextField()

    class G(Form):
        class Meta:
            foo = 12
            bar = 8

    class H(F, G):
        class Meta:
            quux = 42

    class I(F, G):
        pass

    def test_basic(self):
        form = self.H()
        meta = form.meta
        self.assertEqual(meta.foo, 9)
        self.assertEqual(meta.bar, 8)
        self.assertEqual(meta.csrf, False)
        assert isinstance(meta, self.F.Meta)
        assert isinstance(meta, self.G.Meta)
        self.assertEqual(type(meta).__bases__, (
            self.H.Meta,
            self.F.Meta,
            self.G.Meta,
            DefaultMeta
        ))

    def test_missing_diamond(self):
        meta = self.I().meta
        self.assertEqual(type(meta).__bases__, (
            self.F.Meta,
            self.G.Meta,
            DefaultMeta
        ))

########NEW FILE########
__FILENAME__ = i18n
from __future__ import unicode_literals

from unittest import TestCase
from wtforms import form, TextField, validators
from wtforms.i18n import get_translations
from wtforms.ext.i18n import form as i18n_form


def gettext_lower(self, s):
    return s.lower()


def ngettext_lower(self, singular, plural, n):
    if n == 1:
        return singular.lower()
    else:
        return plural.lower()


class Lower_Translator(object):
    """A fake translator that just converts everything to lowercase."""

    gettext = gettext_lower
    ngettext = ngettext_lower


class Python2_Translator(object):
    """A mock translator which implements python2 ugettext methods."""

    ugettext = gettext_lower
    ungettext = ngettext_lower


class I18NTest(TestCase):
    def test_failure(self):
        self.assertRaises(IOError, get_translations, [])

    def test_us_translation(self):
        translations = get_translations(['en_US'])
        self.assertEqual(translations.gettext('Invalid Mac address.'), 'Invalid MAC address.')

    def _test_converter(self, translator):
        getter = lambda x: translator

        translations = get_translations([], getter=getter)
        self.assertEqual(translations.gettext('Foo'), 'foo')
        self.assertEqual(translations.ngettext('Foo', 'Foos', 1), 'foo')
        self.assertEqual(translations.ngettext('Foo', 'Foos', 2), 'foos')
        return translations

    def test_python2_wrap(self):
        translator = Python2_Translator()
        translations = self._test_converter(translator)
        assert translations is not translator

    def test_python3_nowrap(self):
        translator = Lower_Translator()
        translations = self._test_converter(translator)
        assert translations is translator


class ClassicI18nFormTest(TestCase):
    class F(i18n_form.Form):
        LANGUAGES = ['en_US', 'en']
        a = TextField(validators=[validators.Required()])

    def test_form(self):
        tcache = i18n_form.translations_cache
        tcache.clear()
        form = self.F()

        assert ('en_US', 'en') in tcache
        assert form._get_translations() is tcache[('en_US', 'en')]
        assert not form.validate()
        self.assertEqual(form.a.errors[0], 'This field is required.')

        form = self.F(LANGUAGES=['es'])
        assert ('es', ) in tcache
        self.assertEqual(len(tcache), 2)
        assert not form.validate()
        self.assertEqual(form.a.errors[0], 'Este campo es obligatorio.')


class CoreFormTest(TestCase):
    class F(form.Form):
        class Meta:
            locales = ['en_US', 'en']
        a = TextField(validators=[validators.Required()])

    class F2(form.Form):
        a = TextField(validators=[validators.Required(), validators.Length(max=3)])

    class F3(form.Form):
        a = TextField(validators=[validators.Length(max=1)])

    def _common_test(self, expected_error, form_kwargs, form_class=None):
        if not form_class:
            form_class = self.F
        form = form_class(**form_kwargs)
        assert not form.validate()
        self.assertEqual(form.a.errors[0], expected_error)
        return form

    def test_defaults(self):
        # Test with the default language
        form = self._common_test('This field is required.', {})
        # Make sure we have a gettext translations context
        self.assertNotEqual(form.a.gettext(''), '')

        form = self._common_test('This field is required.', {}, self.F2)
        assert form._get_translations() is None
        assert form.meta.locales is False
        self.assertEqual(form.a.gettext(''), '')

    def test_fallback(self):
        form = self._common_test('This field is required.', dict(meta=dict(locales=False)))
        self.assertEqual(form.a.gettext(''), '')

    def test_override_languages(self):
        self._common_test('Este campo es obligatorio.', dict(meta=dict(locales=['es_ES'])))

    def test_ngettext(self):
        language_settings = [
            (['en_US', 'en'], 'Field cannot be longer than 3 characters.', 'Field cannot be longer than 1 character.'),
            (['de_DE', 'de'], 'Feld kann nicht l\xe4nger als 3 Zeichen sein.', 'Feld kann nicht l\xe4nger als 1 Zeichen sein.'),
            (['et'], 'V\xe4li ei tohi olla \xfcle 3 t\xe4hem\xe4rgi pikk.', 'V\xe4li ei tohi olla \xfcle 1 t\xe4hem\xe4rgi pikk.'),
        ]
        for languages, match1, match2 in language_settings:
            settings = dict(a='toolong', meta=dict(locales=languages))
            self._common_test(match1, settings, self.F2)
            self._common_test(match2, settings, self.F3)

    def test_cache(self):
        settings = {'meta': {'locales': ['de_DE'], 'cache_translations': True}}
        expected = 'Dieses Feld wird ben\xf6tigt.'
        form1 = self._common_test(expected, settings)
        form2 = self._common_test(expected, settings)
        assert form1.meta.get_translations(form1) is form2.meta.get_translations(form2)
        settings['meta']['cache_translations'] = False
        form3 = self._common_test(expected, settings)
        assert form2.meta.get_translations(form2) is not form3.meta.get_translations(form3)


class TranslationsTest(TestCase):
    class F(form.Form):
        a = TextField(validators=[validators.Length(max=5)])

    class F2(form.Form):
        def _get_translations(self):
            return Lower_Translator()

        a = TextField('', [validators.Length(max=5)])

    def setUp(self):
        self.a = self.F().a

    def test_gettext(self):
        x = "foo"
        self.assertTrue(self.a.gettext(x) is x)

    def test_ngettext(self):
        getit = lambda n: self.a.ngettext("antelope", "antelopes", n)
        self.assertEqual(getit(0), "antelopes")
        self.assertEqual(getit(1), "antelope")
        self.assertEqual(getit(2), "antelopes")

    def test_validator_translation(self):
        form = self.F2(a='hellobye')
        self.assertFalse(form.validate())
        self.assertEqual(form.a.errors[0], 'field cannot be longer than 5 characters.')
        form = self.F(a='hellobye')
        self.assertFalse(form.validate())
        self.assertEqual(form.a.errors[0], 'Field cannot be longer than 5 characters.')

########NEW FILE########
__FILENAME__ = locale_babel
from __future__ import unicode_literals
import babel

from decimal import Decimal, ROUND_UP
from unittest import TestCase
from wtforms import Form
from wtforms.fields import DecimalField
from wtforms.utils import unset_value
from tests.common import DummyPostData


class TestLocaleDecimal(TestCase):
    class F(Form):
        class Meta:
            locales = ['hi_IN', 'en_US']
        a = DecimalField(use_locale=True)

    def _format_test(self, expected, val, locales=unset_value):
        meta = None
        if locales is not unset_value:
            meta = {'locales': locales}
        form = self.F(meta=meta, a=Decimal(val))
        self.assertEqual(form.a._value(), expected)

    def test_typeerror(self):
        def build(**kw):
            form = self.F()
            DecimalField(
                use_locale=True,
                _form=form,
                _name='a',
                _translations=form._get_translations(),
                **kw
            )

        self.assertRaises(TypeError, build, places=2)
        self.assertRaises(TypeError, build, rounding=ROUND_UP)

    def test_formatting(self):
        val = Decimal('123456.789')
        neg = Decimal('-5.2')
        self._format_test('1,23,456.789', val)
        self._format_test('-12,52,378.2', '-1252378.2')
        self._format_test('123,456.789', val, ['en_US'])
        self._format_test('-5.2', neg, ['en_US'])
        self._format_test('123.456,789', val, ['es_ES'])
        self._format_test('123.456,789', val, ['de_DE'])
        self._format_test('-5,2', neg, ['de_DE'])
        self._format_test("-12'345.2", '-12345.2', ['de_CH'])

    def _parse_test(self, raw_val, expected, locales=unset_value):
        meta = None
        if locales is not unset_value:
            meta = {'locales': locales}
        form = self.F(DummyPostData(a=raw_val), meta=meta)
        if not form.validate():
            raise AssertionError(
                'Expected value %r to parse as a decimal, instead got %r' % (
                    raw_val, form.a.errors,
                )
            )
        self.assertEqual(form.a.data, expected)

    def _fail_parse(self, raw_val, expected_error, locales=unset_value):
        meta = None
        if locales is not unset_value:
            meta = {'locales': locales}
        form = self.F(DummyPostData(a=raw_val), meta=meta)
        assert not form.validate()
        self.assertEqual(form.a.errors[0], expected_error)

    def test_parsing(self):
        expected = Decimal('123456.789')
        self._parse_test('1,23,456.789', expected)
        self._parse_test('1,23,456.789', expected, ['en_US'])
        self._parse_test('1.23.456,789', expected, ['de_DE'])
        self._parse_test("1'23'456.789", expected, ['de_CH'])

        self._fail_parse('1,23,456.5', 'Keine g\xfcltige Dezimalzahl', ['de_DE'])
        self._fail_parse('1.234.567,5', 'Not a valid decimal value', ['en_US'])

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from unittest import defaultTestLoader, TextTestRunner, TestSuite

TESTS = ('form', 'fields', 'validators', 'widgets', 'webob_wrapper', 'csrf', 'ext_csrf', 'i18n')

OPTIONAL_TESTS = ('ext_django.tests', 'ext_sqlalchemy', 'ext_dateutil', 'locale_babel')


def make_suite(prefix='', extra=(), force_all=False):
    tests = TESTS + extra
    test_names = list(prefix + x for x in tests)
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromNames(test_names))
    for name in OPTIONAL_TESTS:
        test_name = prefix + name
        try:
            suite.addTest(defaultTestLoader.loadTestsFromName(test_name))
        except (ImportError, AttributeError):
            if force_all:
                # If force_all, don't let us skip tests
                raise ImportError('Could not load test module %s and force_all is enabled.' % test_name)
            sys.stderr.write("### Disabled test '%s', dependency not found\n" % name)
    return suite


def additional_tests():
    """
    This is called automatically by setup.py test
    """
    return make_suite('tests.')


def main():
    my_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(my_dir, '..')))

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--with-pep8', action='store_true', dest='with_pep8', default=False)
    parser.add_option('--force-all', action='store_true', dest='force_all', default=False)
    parser.add_option('-v', '--verbose', action='count', dest='verbosity', default=0)
    parser.add_option('-q', '--quiet', action='count', dest='quietness', default=0)
    options, extra_args = parser.parse_args()
    has_pep8 = False
    try:
        import pep8
        has_pep8 = True
    except ImportError:
        if options.with_pep8:
            sys.stderr.write('# Could not find pep8 library.')
            sys.exit(1)

    if has_pep8:
        guide_main = pep8.StyleGuide(
            ignore=[],
            paths=['wtforms/'],
            exclude=[],
            max_line_length=130,
        )
        guide_tests = pep8.StyleGuide(
            ignore=['E221'],
            paths=['tests/'],
            max_line_length=150,
        )
        for guide in (guide_main, guide_tests):
            report = guide.check_files()
            if report.total_errors:
                sys.exit(1)

    suite = make_suite('', tuple(extra_args), options.force_all)

    runner = TextTestRunner(verbosity=options.verbosity - options.quietness + 1)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = validators
from unittest import TestCase
from wtforms.compat import text_type
from wtforms.validators import (
    StopValidation, ValidationError, email, equal_to,
    ip_address, length, required, optional, regexp,
    url, NumberRange, AnyOf, NoneOf, mac_address, UUID,
    input_required, data_required
)
from functools import partial
from tests.common import DummyField, grab_error_message, grab_stop_message


class DummyForm(dict):
    pass


class ValidatorsTest(TestCase):
    def setUp(self):
        self.form = DummyForm()

    def test_email(self):
        self.assertEqual(email()(self.form, DummyField('foo@bar.dk')), None)
        self.assertEqual(email()(self.form, DummyField('123@bar.dk')), None)
        self.assertEqual(email()(self.form, DummyField('foo@456.dk')), None)
        self.assertEqual(email()(self.form, DummyField('foo@bar456.info')), None)
        self.assertRaises(ValidationError, email(), self.form, DummyField(None))
        self.assertRaises(ValidationError, email(), self.form, DummyField(''))
        self.assertRaises(ValidationError, email(), self.form, DummyField('  '))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('bar.dk'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('@bar.dk'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@bar'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@bar.ab12'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@.bar.ab'))

    def test_equal_to(self):
        self.form['foo'] = DummyField('test')
        self.assertEqual(equal_to('foo')(self.form, self.form['foo']), None)
        self.assertRaises(ValidationError, equal_to('invalid_field_name'), self.form, DummyField('test'))
        self.assertRaises(ValidationError, equal_to('foo'), self.form, DummyField('different_value'))

    def test_ip_address(self):
        self.assertEqual(ip_address()(self.form, DummyField('127.0.0.1')), None)
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('abc.0.0.1'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('1278.0.0.1'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('127.0.0.abc'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('900.200.100.75'))
        for bad_address in ('abc.0.0.1', 'abcd:1234::123::1', '1:2:3:4:5:6:7:8:9', 'abcd::1ffff'):
            self.assertRaises(ValidationError, ip_address(ipv6=True), self.form, DummyField(bad_address))

        for good_address in ('::1', 'dead:beef:0:0:0:0:42:1', 'abcd:ef::42:1'):
            self.assertEqual(ip_address(ipv6=True)(self.form, DummyField(good_address)), None)

        # Test ValueError on ipv6=False and ipv4=False
        self.assertRaises(ValueError, ip_address, ipv4=False, ipv6=False)

    def test_mac_address(self):
        self.assertEqual(mac_address()(self.form,
                                       DummyField('01:23:45:67:ab:CD')), None)

        check_fail = partial(
            self.assertRaises, ValidationError,
            mac_address(), self.form
        )

        check_fail(DummyField('00:00:00:00:00'))
        check_fail(DummyField('01:23:45:67:89:'))
        check_fail(DummyField('01:23:45:67:89:gh'))
        check_fail(DummyField('123:23:45:67:89:00'))

    def test_uuid(self):
        self.assertEqual(
            UUID()(self.form, DummyField('2bc1c94f-0deb-43e9-92a1-4775189ec9f8')),
            None
        )
        self.assertRaises(ValidationError, UUID(), self.form,
                          DummyField('2bc1c94f-deb-43e9-92a1-4775189ec9f8'))
        self.assertRaises(ValidationError, UUID(), self.form,
                          DummyField('2bc1c94f-0deb-43e9-92a1-4775189ec9f'))
        self.assertRaises(ValidationError, UUID(), self.form,
                          DummyField('gbc1c94f-0deb-43e9-92a1-4775189ec9f8'))
        self.assertRaises(ValidationError, UUID(), self.form,
                          DummyField('2bc1c94f 0deb-43e9-92a1-4775189ec9f8'))

    def test_length(self):
        field = DummyField('foobar')
        self.assertEqual(length(min=2, max=6)(self.form, field), None)
        self.assertRaises(ValidationError, length(min=7), self.form, field)
        self.assertEqual(length(min=6)(self.form, field), None)
        self.assertRaises(ValidationError, length(max=5), self.form, field)
        self.assertEqual(length(max=6)(self.form, field), None)

        self.assertRaises(AssertionError, length)
        self.assertRaises(AssertionError, length, min=5, max=2)

        # Test new formatting features
        grab = lambda **k: grab_error_message(length(**k), self.form, field)
        self.assertEqual(grab(min=2, max=5, message='%(min)d and %(max)d'), '2 and 5')
        self.assertTrue('at least 8' in grab(min=8))
        self.assertTrue('longer than 5' in grab(max=5))
        self.assertTrue('between 2 and 5' in grab(min=2, max=5))

    def test_required(self):
        self.assertEqual(required()(self.form, DummyField('foobar')), None)
        self.assertRaises(StopValidation, required(), self.form, DummyField(''))

    def test_data_required(self):
        # Make sure we stop the validation chain
        self.assertEqual(data_required()(self.form, DummyField('foobar')), None)
        self.assertRaises(StopValidation, data_required(), self.form, DummyField(''))
        self.assertRaises(StopValidation, data_required(), self.form, DummyField(' '))
        self.assertEqual(data_required().field_flags, ('required', ))

        # Make sure we clobber errors
        f = DummyField('', ['Invalid Integer Value'])
        self.assertEqual(len(f.errors), 1)
        self.assertRaises(StopValidation, data_required(), self.form, f)
        self.assertEqual(len(f.errors), 0)

        # Check message and custom message
        grab = lambda **k: grab_stop_message(data_required(**k), self.form, DummyField(''))
        self.assertEqual(grab(), 'This field is required.')
        self.assertEqual(grab(message='foo'), 'foo')

    def test_input_required(self):
        self.assertEqual(input_required()(self.form, DummyField('foobar', raw_data=['foobar'])), None)
        self.assertRaises(StopValidation, input_required(), self.form, DummyField('', raw_data=['']))
        self.assertEqual(input_required().field_flags, ('required', ))

        # Check message and custom message
        grab = lambda **k: grab_stop_message(input_required(**k), self.form, DummyField('', raw_data=['']))
        self.assertEqual(grab(), 'This field is required.')
        self.assertEqual(grab(message='foo'), 'foo')

    def test_optional(self):
        self.assertEqual(optional()(self.form, DummyField('foobar', raw_data=['foobar'])), None)
        self.assertRaises(StopValidation, optional(), self.form, DummyField('', raw_data=['']))
        self.assertEqual(optional().field_flags, ('optional', ))
        f = DummyField('', ['Invalid Integer Value'], raw_data=[''])
        self.assertEqual(len(f.errors), 1)
        self.assertRaises(StopValidation, optional(), self.form, f)
        self.assertEqual(len(f.errors), 0)

        # Test for whitespace behavior.
        whitespace_field = DummyField(' ', raw_data=[' '])
        self.assertRaises(StopValidation, optional(), self.form, whitespace_field)
        self.assertEqual(optional(strip_whitespace=False)(self.form, whitespace_field), None)

    def test_regexp(self):
        import re
        # String regexp
        self.assertEqual(regexp('^a')(self.form, DummyField('abcd')), None)
        self.assertEqual(regexp('^a', re.I)(self.form, DummyField('ABcd')), None)
        self.assertRaises(ValidationError, regexp('^a'), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, regexp('^a'), self.form, DummyField(None))
        # Compiled regexp
        self.assertEqual(regexp(re.compile('^a'))(self.form, DummyField('abcd')), None)
        self.assertEqual(regexp(re.compile('^a', re.I))(self.form, DummyField('ABcd')), None)
        self.assertRaises(ValidationError, regexp(re.compile('^a')), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, regexp(re.compile('^a')), self.form, DummyField(None))

        # Check custom message
        self.assertEqual(grab_error_message(regexp('^a', message='foo'), self.form, DummyField('f')), 'foo')

    def test_url(self):
        self.assertEqual(url()(self.form, DummyField('http://foobar.dk')), None)
        self.assertEqual(url()(self.form, DummyField('http://foobar.dk/')), None)
        self.assertEqual(url()(self.form, DummyField('http://foobar.museum/foobar')), None)
        self.assertEqual(url()(self.form, DummyField('http://127.0.0.1/foobar')), None)
        self.assertEqual(url()(self.form, DummyField('http://127.0.0.1:9000/fake')), None)
        self.assertEqual(url(require_tld=False)(self.form, DummyField('http://localhost/foobar')), None)
        self.assertEqual(url(require_tld=False)(self.form, DummyField('http://foobar')), None)
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('foobar.dk'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://127.0.0/asdf'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar.d'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar.12'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://localhost:abc/a'))

    def test_number_range(self):
        v = NumberRange(min=5, max=10)
        self.assertEqual(v(self.form, DummyField(7)), None)
        self.assertRaises(ValidationError, v, self.form, DummyField(None))
        self.assertRaises(ValidationError, v, self.form, DummyField(0))
        self.assertRaises(ValidationError, v, self.form, DummyField(12))
        self.assertRaises(ValidationError, v, self.form, DummyField(-5))

        onlymin = NumberRange(min=5)
        self.assertEqual(onlymin(self.form, DummyField(500)), None)
        self.assertRaises(ValidationError, onlymin, self.form, DummyField(4))

        onlymax = NumberRange(max=50)
        self.assertEqual(onlymax(self.form, DummyField(30)), None)
        self.assertRaises(ValidationError, onlymax, self.form, DummyField(75))

    def test_lazy_proxy(self):
        """Tests that the validators support lazy translation strings for messages."""

        class ReallyLazyProxy(object):
            def __unicode__(self):
                raise Exception('Translator function called during form declaration: it should be called at response time.')
            __str__ = __unicode__

        message = ReallyLazyProxy()
        self.assertRaises(Exception, str, message)
        self.assertRaises(Exception, text_type, message)
        self.assertTrue(equal_to('fieldname', message=message))
        self.assertTrue(length(min=1, message=message))
        self.assertTrue(NumberRange(1, 5, message=message))
        self.assertTrue(required(message=message))
        self.assertTrue(regexp('.+', message=message))
        self.assertTrue(email(message=message))
        self.assertTrue(ip_address(message=message))
        self.assertTrue(url(message=message))

    def test_any_of(self):
        self.assertEqual(AnyOf(['a', 'b', 'c'])(self.form, DummyField('b')), None)
        self.assertRaises(ValueError, AnyOf(['a', 'b', 'c']), self.form, DummyField(None))

        # Anyof in 1.0.1 failed on numbers for formatting the error with a TypeError
        check_num = AnyOf([1, 2, 3])
        self.assertEqual(check_num(self.form, DummyField(2)), None)
        self.assertRaises(ValueError, check_num, self.form, DummyField(4))

        # Test values_formatter
        formatter = lambda values: '::'.join(text_type(x) for x in reversed(values))
        checker = AnyOf([7, 8, 9], message='test %(values)s', values_formatter=formatter)
        self.assertEqual(grab_error_message(checker, self.form, DummyField(4)), 'test 9::8::7')

    def test_none_of(self):
        self.assertEqual(NoneOf(['a', 'b', 'c'])(self.form, DummyField('d')), None)
        self.assertRaises(ValueError, NoneOf(['a', 'b', 'c']), self.form, DummyField('a'))

########NEW FILE########
__FILENAME__ = webob_wrapper
from unittest import TestCase
from wtforms.form import BaseForm
from wtforms.utils import WebobInputWrapper
from wtforms.utils import unset_value
from wtforms.fields import Field

try:
    from webob.multidict import MultiDict
    has_webob = True
except ImportError:
    has_webob = False


class MockMultiDict(object):
    def __init__(self, tuples):
        self.tuples = tuples

    def __len__(self):
        return len(self.tuples)

    def __iter__(self):
        for k, _ in self.tuples:
            yield k

    def __contains__(self, key):
        for k, _ in self.tuples:
            if k == key:
                return True
        return False

    def getall(self, key):
        result = []
        for k, v in self.tuples:
            if key == k:
                result.append(v)
        return result


class SneakyField(Field):
    def __init__(self, sneaky_callable, *args, **kwargs):
        super(SneakyField, self).__init__(*args, **kwargs)
        self.sneaky_callable = sneaky_callable

    def process(self, formdata, data=unset_value):
        self.sneaky_callable(formdata)


class WebobWrapperTest(TestCase):
    def setUp(self):
        w_cls = MultiDict if has_webob else MockMultiDict

        self.test_values = [('a', 'Apple'), ('b', 'Banana'), ('a', 'Cherry')]
        self.empty_mdict = w_cls([])
        self.filled_mdict = w_cls(self.test_values)

    def test_automatic_wrapping(self):
        def _check(formdata):
            self.assertTrue(isinstance(formdata, WebobInputWrapper))

        form = BaseForm({'a': SneakyField(_check)})
        form.process(self.filled_mdict)

    def test_empty(self):
        formdata = WebobInputWrapper(self.empty_mdict)
        self.assertFalse(formdata)
        self.assertEqual(len(formdata), 0)
        self.assertEqual(list(formdata), [])
        self.assertEqual(formdata.getlist('fake'), [])

    def test_filled(self):
        formdata = WebobInputWrapper(self.filled_mdict)
        self.assertTrue(formdata)
        self.assertEqual(len(formdata), 3)
        self.assertEqual(list(formdata), ['a', 'b', 'a'])
        self.assertTrue('b' in formdata)
        self.assertTrue('fake' not in formdata)
        self.assertEqual(formdata.getlist('a'), ['Apple', 'Cherry'])
        self.assertEqual(formdata.getlist('b'), ['Banana'])
        self.assertEqual(formdata.getlist('fake'), [])

########NEW FILE########
__FILENAME__ = widgets
from __future__ import unicode_literals

from unittest import TestCase
from wtforms.widgets import html_params, Input
from wtforms.widgets import *
from wtforms.widgets import html5


class DummyField(object):
    def __init__(self, data, name='f', label='', id='', type='TextField'):
        self.data = data
        self.name = name
        self.label = label
        self.id = id
        self.type = type

    _value = lambda x: x.data
    __unicode__ = lambda x: x.data
    __str__ = lambda x: x.data
    __call__ = lambda x, **k: x.data
    __iter__ = lambda x: iter(x.data)
    iter_choices = lambda x: iter(x.data)


class HTMLParamsTest(TestCase):
    def test_basic(self):
        self.assertEqual(html_params(foo=9, k='wuuu'), 'foo="9" k="wuuu"')
        self.assertEqual(html_params(class_='foo'), 'class="foo"')
        self.assertEqual(html_params(class__='foo'), 'class_="foo"')
        self.assertEqual(html_params(for_='foo'), 'for="foo"')
        self.assertEqual(html_params(readonly=False, foo=9), 'foo="9"')

    def test_data_prefix(self):
        self.assertEqual(html_params(data_foo=22), 'data-foo="22"')
        self.assertEqual(html_params(data_foo_bar=1), 'data-foo_bar="1"')

    def test_quoting(self):
        self.assertEqual(html_params(foo='hi&bye"quot'), 'foo="hi&amp;bye&quot;quot"')


class ListWidgetTest(TestCase):
    def test(self):
        # ListWidget just expects an iterable of field-like objects as its
        # 'field' so that is what we will give it
        field = DummyField([DummyField(x, label='l' + x) for x in ['foo', 'bar']], id='hai')

        self.assertEqual(ListWidget()(field), '<ul id="hai"><li>lfoo foo</li><li>lbar bar</li></ul>')

        w = ListWidget(html_tag='ol', prefix_label=False)
        self.assertEqual(w(field), '<ol id="hai"><li>foo lfoo</li><li>bar lbar</li></ol>')


class TableWidgetTest(TestCase):
    def test(self):
        inner_fields = [
            DummyField('hidden1', type='HiddenField'),
            DummyField('foo', label='lfoo'),
            DummyField('bar', label='lbar'),
            DummyField('hidden2', type='HiddenField'),
        ]
        field = DummyField(inner_fields, id='hai')
        self.assertEqual(
            TableWidget()(field),
            '<table id="hai"><tr><th>lfoo</th><td>hidden1foo</td></tr><tr><th>lbar</th><td>bar</td></tr></table>hidden2'
        )


class BasicWidgetsTest(TestCase):
    """Test most of the basic input widget types"""

    def setUp(self):
        self.field = DummyField('foo', name='bar', label='label', id='id')

    def test_input_type(self):
        a = Input()
        self.assertRaises(AttributeError, getattr, a, 'input_type')
        b = Input(input_type='test')
        self.assertEqual(b.input_type, 'test')

    def test_html_marking(self):
        html = TextInput()(self.field)
        self.assertTrue(hasattr(html, '__html__'))
        self.assertTrue(html.__html__() is html)

    def test_text_input(self):
        self.assertEqual(TextInput()(self.field), '<input id="id" name="bar" type="text" value="foo">')

    def test_password_input(self):
        self.assertTrue('type="password"' in PasswordInput()(self.field))
        self.assertTrue('value=""' in PasswordInput()(self.field))
        self.assertTrue('value="foo"' in PasswordInput(hide_value=False)(self.field))

    def test_hidden_input(self):
        self.assertTrue('type="hidden"' in HiddenInput()(self.field))

    def test_checkbox_input(self):
        self.assertEqual(CheckboxInput()(self.field, value='v'), '<input checked id="id" name="bar" type="checkbox" value="v">')
        field2 = DummyField(False)
        self.assertTrue('checked' not in CheckboxInput()(field2))

    def test_radio_input(self):
        self.field.checked = True
        expected = '<input checked id="id" name="bar" type="radio" value="foo">'
        self.assertEqual(RadioInput()(self.field), expected)
        self.field.checked = False
        self.assertEqual(RadioInput()(self.field), expected.replace(' checked', ''))

    def test_textarea(self):
        # Make sure textareas escape properly and render properly
        f = DummyField('hi<>bye')
        self.assertEqual(TextArea()(f), '<textarea id="" name="f">hi&lt;&gt;bye</textarea>')


class SelectTest(TestCase):
    field = DummyField([('foo', 'lfoo', True), ('bar', 'lbar', False)])

    def test(self):
        self.assertEqual(
            Select()(self.field),
            '<select id="" name="f"><option selected value="foo">lfoo</option><option value="bar">lbar</option></select>'
        )
        self.assertEqual(
            Select(multiple=True)(self.field),
            '<select id="" multiple name="f"><option selected value="foo">lfoo</option><option value="bar">lbar</option></select>'
        )

    def test_render_option(self):
        # value, label, selected
        self.assertEqual(
            Select.render_option('bar', 'foo', False),
            '<option value="bar">foo</option>'
        )
        self.assertEqual(
            Select.render_option(True, 'foo', True),
            '<option selected value="True">foo</option>'
        )


class HTML5Test(TestCase):
    field = DummyField('42', name='bar', id='id')

    def test_number(self):
        i1 = html5.NumberInput(step='any')
        self.assertEqual(i1(self.field), '<input id="id" name="bar" step="any" type="number" value="42">')
        i2 = html5.NumberInput(step=2)
        self.assertEqual(i2(self.field, step=3), '<input id="id" name="bar" step="3" type="number" value="42">')

    def test_range(self):
        i1 = html5.RangeInput(step='any')
        self.assertEqual(i1(self.field), '<input id="id" name="bar" step="any" type="range" value="42">')
        i2 = html5.RangeInput(step=2)
        self.assertEqual(i2(self.field, step=3), '<input id="id" name="bar" step="3" type="range" value="42">')

########NEW FILE########
__FILENAME__ = compat
import sys

if sys.version_info[0] >= 3:
    text_type = str
    string_types = (str, )
    iteritems = lambda o: o.items()
    itervalues = lambda o: o.values()
    izip = zip

else:
    text_type = unicode
    string_types = (basestring, )
    iteritems = lambda o: o.iteritems()
    itervalues = lambda o: o.itervalues()
    from itertools import izip


def with_metaclass(meta, base=object):
    return meta("NewBase", (base,), {})

########NEW FILE########
__FILENAME__ = core
from wtforms.validators import ValidationError
from wtforms.fields import HiddenField

__all__ = ('CSRFTokenField', 'CSRF')


class CSRFTokenField(HiddenField):
    """
    A subclass of HiddenField designed for sending the CSRF token that is used
    for most CSRF protection schemes.

    Notably different from a normal field, this field always renders the
    current token regardless of the submitted value, and also will not be
    populated over to object data via populate_obj
    """
    current_token = None

    def __init__(self, *args, **kw):
        self.csrf_impl = kw.pop('csrf_impl')
        super(CSRFTokenField, self).__init__(*args, **kw)

    def _value(self):
        """
        We want to always return the current token on render, regardless of
        whether a good or bad token was passed.
        """
        return self.current_token

    def populate_obj(self, *args):
        """
        Don't populate objects with the CSRF token
        """
        pass

    def pre_validate(self, form):
        """
        Handle validation of this token field.
        """
        self.csrf_impl.validate_csrf_token(form, self)

    def process(self, *args):
        super(CSRFTokenField, self).process(*args)
        self.current_token = self.csrf_impl.generate_csrf_token(self)


class CSRF(object):
    field_class = CSRFTokenField

    def setup_form(self, form):
        """
        Receive the form we're attached to and set up fields.

        The default implementation creates a single field of
        type :attr:`field_class` with name taken from the
        ``csrf_field_name`` of the class meta.

        :param form:
            The form instance we're attaching to.
        :return:
            A sequence of `(field_name, unbound_field)` 2-tuples which
            are unbound fields to be added to the form.
        """
        meta = form.meta
        field_name = meta.csrf_field_name
        unbound_field = self.field_class(
            label='CSRF Token',
            csrf_impl=self
        )
        return [(field_name, unbound_field)]

    def generate_csrf_token(self, csrf_token_field):
        """
        Implementations must override this to provide a method with which one
        can get a CSRF token for this form.

        A CSRF token is usually a string that is generated deterministically
        based on some sort of user data, though it can be anything which you
        can validate on a subsequent request.

        :param csrf_token_field:
            The field which is being used for CSRF.
        :return:
            A generated CSRF string.
        """
        raise NotImplementedError()

    def validate_csrf_token(self, form, field):
        """
        Override this method to provide custom CSRF validation logic.

        The default CSRF validation logic simply checks if the recently
        generated token equals the one we received as formdata.

        :param form: The form which has this CSRF token.
        :param field: The CSRF token field.
        """
        if field.current_token != field.data:
            raise ValidationError(field.gettext('Invalid CSRF Token'))

########NEW FILE########
__FILENAME__ = session
"""
A provided CSRF implementation which puts CSRF data in a session.

This can be used fairly comfortably with many `request.session` type
objects, including the Werkzeug/Flask session store, Django sessions, and
potentially other similar objects which use a dict-like API for storing
session keys.

The basic concept is a randomly generated value is stored in the user's
session, and an hmac-sha1 of it (along with an optional expiration time,
for extra security) is used as the value of the csrf_token. If this token
validates with the hmac of the random value + expiration time, and the
expiration time is not passed, the CSRF validation will pass.
"""
from __future__ import unicode_literals

import hmac
import os

from hashlib import sha1
from datetime import datetime, timedelta

from ..validators import ValidationError
from .core import CSRF

__all__ = ('SessionCSRF', )


class SessionCSRF(CSRF):
    TIME_FORMAT = '%Y%m%d%H%M%S'

    def setup_form(self, form):
        self.form_meta = form.meta
        return super(SessionCSRF, self).setup_form(form)

    def generate_csrf_token(self, csrf_token_field):
        meta = self.form_meta
        if meta.csrf_secret is None:
            raise Exception('must set `csrf_secret` on class Meta for SessionCSRF to work')
        if meta.csrf_context is None:
            raise TypeError('Must provide a session-like object as csrf context')

        session = self.session

        if 'csrf' not in session:
            session['csrf'] = sha1(os.urandom(64)).hexdigest()

        if self.time_limit:
            expires = (self.now() + self.time_limit).strftime(self.TIME_FORMAT)
            csrf_build = '%s%s' % (session['csrf'], expires)
        else:
            expires = ''
            csrf_build = session['csrf']

        hmac_csrf = hmac.new(meta.csrf_secret, csrf_build.encode('utf8'), digestmod=sha1)
        return '%s##%s' % (expires, hmac_csrf.hexdigest())

    def validate_csrf_token(self, form, field):
        meta = self.form_meta
        if not field.data or '##' not in field.data:
            raise ValidationError(field.gettext('CSRF token missing'))

        expires, hmac_csrf = field.data.split('##', 1)

        check_val = (self.session['csrf'] + expires).encode('utf8')

        hmac_compare = hmac.new(meta.csrf_secret, check_val, digestmod=sha1)
        if hmac_compare.hexdigest() != hmac_csrf:
            raise ValidationError(field.gettext('CSRF failed'))

        if self.time_limit:
            now_formatted = self.now().strftime(self.TIME_FORMAT)
            if now_formatted > expires:
                raise ValidationError(field.gettext('CSRF token expired'))

    def now(self):
        """
        Get the current time. Used for test mocking/overriding mainly.
        """
        return datetime.now()

    @property
    def time_limit(self):
        return getattr(self.form_meta, 'csrf_time_limit', timedelta(minutes=30))

    @property
    def session(self):
        return getattr(self.form_meta.csrf_context, 'session', self.form_meta.csrf_context)

########NEW FILE########
__FILENAME__ = db
"""
Form generation utilities for App Engine's ``db.Model`` class.

The goal of ``model_form()`` is to provide a clean, explicit and predictable
way to create forms based on ``db.Model`` classes. No malabarism or black
magic should be necessary to generate a form for models, and to add custom
non-model related fields: ``model_form()`` simply generates a form class
that can be used as it is, or that can be extended directly or even be used
to create other forms using ``model_form()``.

Example usage:

.. code-block:: python

   from google.appengine.ext import db
   from tipfy.ext.model.form import model_form

   # Define an example model and add a record.
   class Contact(db.Model):
       name = db.StringProperty(required=True)
       city = db.StringProperty()
       age = db.IntegerProperty(required=True)
       is_admin = db.BooleanProperty(default=False)

   new_entity = Contact(key_name='test', name='Test Name', age=17)
   new_entity.put()

   # Generate a form based on the model.
   ContactForm = model_form(Contact)

   # Get a form populated with entity data.
   entity = Contact.get_by_key_name('test')
   form = ContactForm(obj=entity)

Properties from the model can be excluded from the generated form, or it can
include just a set of properties. For example:

.. code-block:: python

   # Generate a form based on the model, excluding 'city' and 'is_admin'.
   ContactForm = model_form(Contact, exclude=('city', 'is_admin'))

   # or...

   # Generate a form based on the model, only including 'name' and 'age'.
   ContactForm = model_form(Contact, only=('name', 'age'))

The form can be generated setting field arguments:

.. code-block:: python

   ContactForm = model_form(Contact, only=('name', 'age'), field_args={
       'name': {
           'label': 'Full name',
           'description': 'Your name',
       },
       'age': {
           'label': 'Age',
           'validators': [validators.NumberRange(min=14, max=99)],
       }
   })

The class returned by ``model_form()`` can be used as a base class for forms
mixing non-model fields and/or other model forms. For example:

.. code-block:: python

   # Generate a form based on the model.
   BaseContactForm = model_form(Contact)

   # Generate a form based on other model.
   ExtraContactForm = model_form(MyOtherModel)

   class ContactForm(BaseContactForm):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

       # Add the other model form as a subform.
       extra = f.FormField(ExtraContactForm)

The class returned by ``model_form()`` can also extend an existing form
class:

.. code-block:: python

   class BaseContactForm(Form):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

   # Generate a form based on the model.
   ContactForm = model_form(Contact, base_class=BaseContactForm)

"""
from wtforms import Form, validators, widgets, fields as f
from wtforms.compat import iteritems
from wtforms.ext.appengine.fields import GeoPtPropertyField, ReferencePropertyField, StringListPropertyField


def get_TextField(kwargs):
    """
    Returns a ``TextField``, applying the ``db.StringProperty`` length limit
    of 500 bytes.
    """
    kwargs['validators'].append(validators.length(max=500))
    return f.TextField(**kwargs)


def get_IntegerField(kwargs):
    """
    Returns an ``IntegerField``, applying the ``db.IntegerProperty`` range
    limits.
    """
    v = validators.NumberRange(min=-0x8000000000000000, max=0x7fffffffffffffff)
    kwargs['validators'].append(v)
    return f.IntegerField(**kwargs)


def convert_StringProperty(model, prop, kwargs):
    """Returns a form field for a ``db.StringProperty``."""
    if prop.multiline:
        kwargs['validators'].append(validators.length(max=500))
        return f.TextAreaField(**kwargs)
    else:
        return get_TextField(kwargs)


def convert_ByteStringProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ByteStringProperty``."""
    return get_TextField(kwargs)


def convert_BooleanProperty(model, prop, kwargs):
    """Returns a form field for a ``db.BooleanProperty``."""
    return f.BooleanField(**kwargs)


def convert_IntegerProperty(model, prop, kwargs):
    """Returns a form field for a ``db.IntegerProperty``."""
    return get_IntegerField(kwargs)


def convert_FloatProperty(model, prop, kwargs):
    """Returns a form field for a ``db.FloatProperty``."""
    return f.FloatField(**kwargs)


def convert_DateTimeProperty(model, prop, kwargs):
    """Returns a form field for a ``db.DateTimeProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    kwargs.setdefault('format', '%Y-%m-%d %H:%M:%S')
    return f.DateTimeField(**kwargs)


def convert_DateProperty(model, prop, kwargs):
    """Returns a form field for a ``db.DateProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    kwargs.setdefault('format', '%Y-%m-%d')
    return f.DateField(**kwargs)


def convert_TimeProperty(model, prop, kwargs):
    """Returns a form field for a ``db.TimeProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    kwargs.setdefault('format', '%H:%M:%S')
    return f.DateTimeField(**kwargs)


def convert_ListProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ListProperty``."""
    return None


def convert_StringListProperty(model, prop, kwargs):
    """Returns a form field for a ``db.StringListProperty``."""
    return StringListPropertyField(**kwargs)


def convert_ReferenceProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ReferenceProperty``."""
    kwargs['reference_class'] = prop.reference_class
    kwargs.setdefault('allow_blank', not prop.required)
    return ReferencePropertyField(**kwargs)


def convert_SelfReferenceProperty(model, prop, kwargs):
    """Returns a form field for a ``db.SelfReferenceProperty``."""
    return None


def convert_UserProperty(model, prop, kwargs):
    """Returns a form field for a ``db.UserProperty``."""
    return None


def convert_BlobProperty(model, prop, kwargs):
    """Returns a form field for a ``db.BlobProperty``."""
    return f.FileField(**kwargs)


def convert_TextProperty(model, prop, kwargs):
    """Returns a form field for a ``db.TextProperty``."""
    return f.TextAreaField(**kwargs)


def convert_CategoryProperty(model, prop, kwargs):
    """Returns a form field for a ``db.CategoryProperty``."""
    return get_TextField(kwargs)


def convert_LinkProperty(model, prop, kwargs):
    """Returns a form field for a ``db.LinkProperty``."""
    kwargs['validators'].append(validators.url())
    return get_TextField(kwargs)


def convert_EmailProperty(model, prop, kwargs):
    """Returns a form field for a ``db.EmailProperty``."""
    kwargs['validators'].append(validators.email())
    return get_TextField(kwargs)


def convert_GeoPtProperty(model, prop, kwargs):
    """Returns a form field for a ``db.GeoPtProperty``."""
    return GeoPtPropertyField(**kwargs)


def convert_IMProperty(model, prop, kwargs):
    """Returns a form field for a ``db.IMProperty``."""
    return None


def convert_PhoneNumberProperty(model, prop, kwargs):
    """Returns a form field for a ``db.PhoneNumberProperty``."""
    return get_TextField(kwargs)


def convert_PostalAddressProperty(model, prop, kwargs):
    """Returns a form field for a ``db.PostalAddressProperty``."""
    return get_TextField(kwargs)


def convert_RatingProperty(model, prop, kwargs):
    """Returns a form field for a ``db.RatingProperty``."""
    kwargs['validators'].append(validators.NumberRange(min=0, max=100))
    return f.IntegerField(**kwargs)


class ModelConverter(object):
    """
    Converts properties from a ``db.Model`` class to form fields.

    Default conversions between properties and fields:

    +====================+===================+==============+==================+
    | Property subclass  | Field subclass    | datatype     | notes            |
    +====================+===================+==============+==================+
    | StringProperty     | TextField         | unicode      | TextArea         |
    |                    |                   |              | if multiline     |
    +--------------------+-------------------+--------------+------------------+
    | ByteStringProperty | TextField         | str          |                  |
    +--------------------+-------------------+--------------+------------------+
    | BooleanProperty    | BooleanField      | bool         |                  |
    +--------------------+-------------------+--------------+------------------+
    | IntegerProperty    | IntegerField      | int or long  |                  |
    +--------------------+-------------------+--------------+------------------+
    | FloatProperty      | TextField         | float        |                  |
    +--------------------+-------------------+--------------+------------------+
    | DateTimeProperty   | DateTimeField     | datetime     | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | DateProperty       | DateField         | date         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | TimeProperty       | DateTimeField     | time         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | ListProperty       | None              | list         | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | StringListProperty | TextAreaField     | list of str  |                  |
    +--------------------+-------------------+--------------+------------------+
    | ReferenceProperty  | ReferencePropertyF| db.Model     |                  |
    +--------------------+-------------------+--------------+------------------+
    | SelfReferenceP.    | ReferencePropertyF| db.Model     |                  |
    +--------------------+-------------------+--------------+------------------+
    | UserProperty       | None              | users.User   | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | BlobProperty       | FileField         | str          |                  |
    +--------------------+-------------------+--------------+------------------+
    | TextProperty       | TextAreaField     | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | CategoryProperty   | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | LinkProperty       | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | EmailProperty      | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | GeoPtProperty      | TextField         | db.GeoPt     |                  |
    +--------------------+-------------------+--------------+------------------+
    | IMProperty         | None              | db.IM        | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | PhoneNumberProperty| TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | PostalAddressP.    | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | RatingProperty     | IntegerField      | int or long  |                  |
    +--------------------+-------------------+--------------+------------------+
    | _ReverseReferenceP.| None              | <iterable>   | always skipped   |
    +====================+===================+==============+==================+
    """
    default_converters = {
        'StringProperty':        convert_StringProperty,
        'ByteStringProperty':    convert_ByteStringProperty,
        'BooleanProperty':       convert_BooleanProperty,
        'IntegerProperty':       convert_IntegerProperty,
        'FloatProperty':         convert_FloatProperty,
        'DateTimeProperty':      convert_DateTimeProperty,
        'DateProperty':          convert_DateProperty,
        'TimeProperty':          convert_TimeProperty,
        'ListProperty':          convert_ListProperty,
        'StringListProperty':    convert_StringListProperty,
        'ReferenceProperty':     convert_ReferenceProperty,
        'SelfReferenceProperty': convert_SelfReferenceProperty,
        'UserProperty':          convert_UserProperty,
        'BlobProperty':          convert_BlobProperty,
        'TextProperty':          convert_TextProperty,
        'CategoryProperty':      convert_CategoryProperty,
        'LinkProperty':          convert_LinkProperty,
        'EmailProperty':         convert_EmailProperty,
        'GeoPtProperty':         convert_GeoPtProperty,
        'IMProperty':            convert_IMProperty,
        'PhoneNumberProperty':   convert_PhoneNumberProperty,
        'PostalAddressProperty': convert_PostalAddressProperty,
        'RatingProperty':        convert_RatingProperty,
    }

    # Don't automatically add a required validator for these properties
    NO_AUTO_REQUIRED = frozenset(['ListProperty', 'StringListProperty', 'BooleanProperty'])

    def __init__(self, converters=None):
        """
        Constructs the converter, setting the converter callables.

        :param converters:
            A dictionary of converter callables for each property type. The
            callable must accept the arguments (model, prop, kwargs).
        """
        self.converters = converters or self.default_converters

    def convert(self, model, prop, field_args):
        """
        Returns a form field for a single model property.

        :param model:
            The ``db.Model`` class that contains the property.
        :param prop:
            The model property: a ``db.Property`` instance.
        :param field_args:
            Optional keyword arguments to construct the field.
        """
        prop_type_name = type(prop).__name__
        kwargs = {
            'label': prop.name.replace('_', ' ').title(),
            'default': prop.default_value(),
            'validators': [],
        }
        if field_args:
            kwargs.update(field_args)

        if prop.required and prop_type_name not in self.NO_AUTO_REQUIRED:
            kwargs['validators'].append(validators.required())

        if prop.choices:
            # Use choices in a select field if it was not provided in field_args
            if 'choices' not in kwargs:
                kwargs['choices'] = [(v, v) for v in prop.choices]
            return f.SelectField(**kwargs)
        else:
            converter = self.converters.get(prop_type_name, None)
            if converter is not None:
                return converter(model, prop, kwargs)


def model_fields(model, only=None, exclude=None, field_args=None,
                 converter=None):
    """
    Extracts and returns a dictionary of form fields for a given
    ``db.Model`` class.

    :param model:
        The ``db.Model`` class to extract fields from.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to a keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    # Get the field names we want to include or exclude, starting with the
    # full list of model properties.
    props = model.properties()
    sorted_props = sorted(iteritems(props), key=lambda prop: prop[1].creation_counter)
    field_names = list(x[0] for x in sorted_props)

    if only:
        field_names = list(f for f in only if f in field_names)
    elif exclude:
        field_names = list(f for f in field_names if f not in exclude)

    # Create all fields.
    field_dict = {}
    for name in field_names:
        field = converter.convert(model, props[name], field_args.get(name))
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, only=None, exclude=None, field_args=None,
               converter=None):
    """
    Creates and returns a dynamic ``wtforms.Form`` class for a given
    ``db.Model`` class. The form class can be used as it is or serve as a base
    for extended form classes, which can then mix non-model related fields,
    subforms with other model forms, among other possibilities.

    :param model:
        The ``db.Model`` class to generate a form for.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    # Extract the fields from the model.
    field_dict = model_fields(model, only, exclude, field_args, converter)

    # Return a dynamically created form class, extending from base_class and
    # including the created fields as properties.
    return type(model.kind() + 'Form', (base_class,), field_dict)

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

import decimal
import operator

from wtforms import fields, widgets
from wtforms.compat import text_type, string_types


class ReferencePropertyField(fields.SelectFieldBase):
    """
    A field for ``db.ReferenceProperty``. The list items are rendered in a
    select.

    :param reference_class:
        A db.Model class which will be used to generate the default query
        to make the list of items. If this is not specified, The `query`
        property must be overridden before validation.
    :param get_label:
        If a string, use this attribute on the model class as the label
        associated with each option. If a one-argument callable, this callable
        will be passed model instance and expected to return the label text.
        Otherwise, the model object's `__str__` or `__unicode__` will be used.
    :param allow_blank:
        If set to true, a blank choice will be added to the top of the list
        to allow `None` to be chosen.
    :param blank_text:
        Use this to override the default blank option's label.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, reference_class=None,
                 get_label=None, allow_blank=False,
                 blank_text='', **kwargs):
        super(ReferencePropertyField, self).__init__(label, validators,
                                                     **kwargs)
        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if reference_class is not None:
            self.query = reference_class.all()

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.query:
                if str(obj.key()) == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.query:
            key = str(obj.key())
            label = self.get_label(obj)
            yield (key, label, (self.data.key() == obj.key()) if self.data else False)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.query:
                if str(self.data.key()) == str(obj.key()):
                    break
            else:
                raise ValueError(self.gettext('Not a valid choice'))


class KeyPropertyField(fields.SelectFieldBase):
    """
    A field for ``ndb.KeyProperty``. The list items are rendered in a select.

    :param reference_class:
        A db.Model class which will be used to generate the default query
        to make the list of items. If this is not specified, The `query`
        property must be overridden before validation.
    :param get_label:
        If a string, use this attribute on the model class as the label
        associated with each option. If a one-argument callable, this callable
        will be passed model instance and expected to return the label text.
        Otherwise, the model object's `__str__` or `__unicode__` will be used.
    :param allow_blank:
        If set to true, a blank choice will be added to the top of the list
        to allow `None` to be chosen.
    :param blank_text:
        Use this to override the default blank option's label.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, reference_class=None,
                 get_label=None, allow_blank=False, blank_text='', **kwargs):
        super(KeyPropertyField, self).__init__(label, validators, **kwargs)
        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, basestring):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if reference_class is not None:
            self.query = reference_class.query()

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.query:
                if str(obj.key.id()) == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.query:
            key = str(obj.key.id())
            label = self.get_label(obj)
            yield (key, label, (self.data.key == obj.key) if self.data else False)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if self.data is not None:
            for obj in self.query:
                if self.data.key == obj.key:
                    break
            else:
                raise ValueError(self.gettext('Not a valid choice'))
        elif not self.allow_blank:
            raise ValueError(self.gettext('Not a valid choice'))


class StringListPropertyField(fields.TextAreaField):
    """
    A field for ``db.StringListProperty``. The list items are rendered in a
    textarea.
    """
    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        else:
            return self.data and text_type("\n".join(self.data)) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = valuelist[0].splitlines()
            except ValueError:
                raise ValueError(self.gettext('Not a valid list'))


class IntegerListPropertyField(fields.TextAreaField):
    """
    A field for ``db.StringListProperty``. The list items are rendered in a
    textarea.
    """
    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        else:
            return text_type('\n'.join(self.data)) if self.data else ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = [int(value) for value in valuelist[0].splitlines()]
            except ValueError:
                raise ValueError(self.gettext('Not a valid integer list'))


class GeoPtPropertyField(fields.TextField):

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                lat, lon = valuelist[0].split(',')
                self.data = '%s,%s' % (decimal.Decimal(lat.strip()), decimal.Decimal(lon.strip()),)
            except (decimal.InvalidOperation, ValueError):
                raise ValueError('Not a valid coordinate location')

########NEW FILE########
__FILENAME__ = ndb
"""
Form generation utilities for App Engine's new ``ndb.Model`` class.

The goal of ``model_form()`` is to provide a clean, explicit and predictable
way to create forms based on ``ndb.Model`` classes. No malabarism or black
magic should be necessary to generate a form for models, and to add custom
non-model related fields: ``model_form()`` simply generates a form class
that can be used as it is, or that can be extended directly or even be used
to create other forms using ``model_form()``.

Example usage:

.. code-block:: python

   from google.appengine.ext import ndb
   from wtforms.ext.appengine.ndb import model_form

   # Define an example model and add a record.
   class Contact(ndb.Model):
       name = ndb.StringProperty(required=True)
       city = ndb.StringProperty()
       age = ndb.IntegerProperty(required=True)
       is_admin = ndb.BooleanProperty(default=False)

   new_entity = Contact(key_name='test', name='Test Name', age=17)
   new_entity.put()

   # Generate a form based on the model.
   ContactForm = model_form(Contact)

   # Get a form populated with entity data.
   entity = Contact.get_by_key_name('test')
   form = ContactForm(obj=entity)

Properties from the model can be excluded from the generated form, or it can
include just a set of properties. For example:

.. code-block:: python

   # Generate a form based on the model, excluding 'city' and 'is_admin'.
   ContactForm = model_form(Contact, exclude=('city', 'is_admin'))

   # or...

   # Generate a form based on the model, only including 'name' and 'age'.
   ContactForm = model_form(Contact, only=('name', 'age'))

The form can be generated setting field arguments:

.. code-block:: python

   ContactForm = model_form(Contact, only=('name', 'age'), field_args={
       'name': {
           'label': 'Full name',
           'description': 'Your name',
       },
       'age': {
           'label': 'Age',
           'validators': [validators.NumberRange(min=14, max=99)],
       }
   })

The class returned by ``model_form()`` can be used as a base class for forms
mixing non-model fields and/or other model forms. For example:

.. code-block:: python

   # Generate a form based on the model.
   BaseContactForm = model_form(Contact)

   # Generate a form based on other model.
   ExtraContactForm = model_form(MyOtherModel)

   class ContactForm(BaseContactForm):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

       # Add the other model form as a subform.
       extra = f.FormField(ExtraContactForm)

The class returned by ``model_form()`` can also extend an existing form
class:

.. code-block:: python

   class BaseContactForm(Form):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

   # Generate a form based on the model.
   ContactForm = model_form(Contact, base_class=BaseContactForm)

"""
from wtforms import Form, validators, fields as f
from wtforms.compat import string_types
from wtforms.ext.appengine.fields import GeoPtPropertyField, KeyPropertyField, StringListPropertyField, IntegerListPropertyField


def get_TextField(kwargs):
    """
    Returns a ``TextField``, applying the ``ndb.StringProperty`` length limit
    of 500 bytes.
    """
    kwargs['validators'].append(validators.length(max=500))
    return f.TextField(**kwargs)


def get_IntegerField(kwargs):
    """
    Returns an ``IntegerField``, applying the ``ndb.IntegerProperty`` range
    limits.
    """
    v = validators.NumberRange(min=-0x8000000000000000, max=0x7fffffffffffffff)
    kwargs['validators'].append(v)
    return f.IntegerField(**kwargs)


class ModelConverterBase(object):
    def __init__(self, converters=None):
        """
        Constructs the converter, setting the converter callables.

        :param converters:
            A dictionary of converter callables for each property type. The
            callable must accept the arguments (model, prop, kwargs).
        """
        self.converters = {}

        for name in dir(self):
            if not name.startswith('convert_'):
                continue
            self.converters[name[8:]] = getattr(self, name)

    def convert(self, model, prop, field_args):
        """
        Returns a form field for a single model property.

        :param model:
            The ``db.Model`` class that contains the property.
        :param prop:
            The model property: a ``db.Property`` instance.
        :param field_args:
            Optional keyword arguments to construct the field.
        """

        prop_type_name = type(prop).__name__

        # Check for generic property
        if(prop_type_name == "GenericProperty"):
            # Try to get type from field args
            generic_type = field_args.get("type")
            if generic_type:
                prop_type_name = field_args.get("type")

            # If no type is found, the generic property uses string set in convert_GenericProperty

        kwargs = {
            'label': prop._code_name.replace('_', ' ').title(),
            'default': prop._default,
            'validators': [],
        }
        if field_args:
            kwargs.update(field_args)

        if prop._required and prop_type_name not in self.NO_AUTO_REQUIRED:
            kwargs['validators'].append(validators.required())

        if kwargs.get('choices', None):
            # Use choices in a select field.
            kwargs['choices'] = [(v, v) for v in kwargs.get('choices')]
            return f.SelectField(**kwargs)

        if prop._choices:
            # Use choices in a select field.
            kwargs['choices'] = [(v, v) for v in prop._choices]
            return f.SelectField(**kwargs)

        else:
            converter = self.converters.get(prop_type_name, None)
            if converter is not None:
                return converter(model, prop, kwargs)
            else:
                return self.fallback_converter(model, prop, kwargs)


class ModelConverter(ModelConverterBase):
    """
    Converts properties from a ``ndb.Model`` class to form fields.

    Default conversions between properties and fields:

    +====================+===================+==============+==================+
    | Property subclass  | Field subclass    | datatype     | notes            |
    +====================+===================+==============+==================+
    | StringProperty     | TextField         | unicode      | TextArea         | repeated support
    |                    |                   |              | if multiline     |
    +--------------------+-------------------+--------------+------------------+
    | BooleanProperty    | BooleanField      | bool         |                  |
    +--------------------+-------------------+--------------+------------------+
    | IntegerProperty    | IntegerField      | int or long  |                  | repeated support
    +--------------------+-------------------+--------------+------------------+
    | FloatProperty      | TextField         | float        |                  |
    +--------------------+-------------------+--------------+------------------+
    | DateTimeProperty   | DateTimeField     | datetime     | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | DateProperty       | DateField         | date         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | TimeProperty       | DateTimeField     | time         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | TextProperty       | TextAreaField     | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | GeoPtProperty      | TextField         | db.GeoPt     |                  |
    +--------------------+-------------------+--------------+------------------+
    | KeyProperty        | KeyProperyField   | ndb.Key      |                  |
    +--------------------+-------------------+--------------+------------------+
    | BlobKeyProperty    | None              | ndb.BlobKey  | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | UserProperty       | None              | users.User   | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | StructuredProperty | None              | ndb.Model    | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | LocalStructuredPro | None              | ndb.Model    | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | JsonProperty       | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | PickleProperty     | None              | bytedata     | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | GenericProperty    | None              | generic      | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | ComputedProperty   | none              |              | always skipped   |
    +====================+===================+==============+==================+

    """
    # Don't automatically add a required validator for these properties
    NO_AUTO_REQUIRED = frozenset(['ListProperty', 'StringListProperty', 'BooleanProperty'])

    def convert_StringProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.StringProperty``."""
        if prop._repeated:
            return StringListPropertyField(**kwargs)
        kwargs['validators'].append(validators.length(max=500))
        return get_TextField(kwargs)

    def convert_BooleanProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.BooleanProperty``."""
        return f.BooleanField(**kwargs)

    def convert_IntegerProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.IntegerProperty``."""
        if prop._repeated:
            return IntegerListPropertyField(**kwargs)
        return get_IntegerField(kwargs)

    def convert_FloatProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.FloatProperty``."""
        return f.FloatField(**kwargs)

    def convert_DateTimeProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.DateTimeProperty``."""
        if prop._auto_now or prop._auto_now_add:
            return None

        return f.DateTimeField(format='%Y-%m-%d %H:%M:%S', **kwargs)

    def convert_DateProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.DateProperty``."""
        if prop._auto_now or prop._auto_now_add:
            return None

        return f.DateField(format='%Y-%m-%d', **kwargs)

    def convert_TimeProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.TimeProperty``."""
        if prop._auto_now or prop._auto_now_add:
            return None

        return f.DateTimeField(format='%H:%M:%S', **kwargs)

    def convert_RepeatedProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        return None

    def convert_UserProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.UserProperty``."""
        return None

    def convert_StructuredProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        return None

    def convert_LocalStructuredProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        return None

    def convert_JsonProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        return None

    def convert_PickleProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        return None

    def convert_GenericProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ListProperty``."""
        kwargs['validators'].append(validators.length(max=500))
        return get_TextField(kwargs)

    def convert_BlobKeyProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.BlobKeyProperty``."""
        return f.FileField(**kwargs)

    def convert_TextProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.TextProperty``."""
        return f.TextAreaField(**kwargs)

    def convert_ComputedProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.ComputedProperty``."""
        return None

    def convert_GeoPtProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.GeoPtProperty``."""
        return GeoPtPropertyField(**kwargs)

    def convert_KeyProperty(self, model, prop, kwargs):
        """Returns a form field for a ``ndb.KeyProperty``."""
        if 'reference_class' not in kwargs:
            try:
                reference_class = prop._kind
            except AttributeError:
                reference_class = prop._reference_class

            if isinstance(reference_class, string_types):
                # reference class is a string, try to retrieve the model object.
                mod = __import__(model.__module__, None, None, [reference_class], 0)
                reference_class = getattr(mod, reference_class)
            kwargs['reference_class'] = reference_class
        kwargs.setdefault('allow_blank', not prop._required)
        return KeyPropertyField(**kwargs)


def model_fields(model, only=None, exclude=None, field_args=None,
                 converter=None):
    """
    Extracts and returns a dictionary of form fields for a given
    ``db.Model`` class.

    :param model:
        The ``db.Model`` class to extract fields from.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to a keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    # Get the field names we want to include or exclude, starting with the
    # full list of model properties.
    props = model._properties
    field_names = list(x[0] for x in sorted(props.items(), key=lambda x: x[1]._creation_counter))

    if only:
        field_names = list(f for f in only if f in field_names)
    elif exclude:
        field_names = list(f for f in field_names if f not in exclude)

    # Create all fields.
    field_dict = {}
    for name in field_names:
        field = converter.convert(model, props[name], field_args.get(name))
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, only=None, exclude=None, field_args=None,
               converter=None):
    """
    Creates and returns a dynamic ``wtforms.Form`` class for a given
    ``ndb.Model`` class. The form class can be used as it is or serve as a base
    for extended form classes, which can then mix non-model related fields,
    subforms with other model forms, among other possibilities.

    :param model:
        The ``ndb.Model`` class to generate a form for.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    # Extract the fields from the model.
    field_dict = model_fields(model, only, exclude, field_args, converter)

    # Return a dynamically created form class, extending from base_class and
    # including the created fields as properties.
    return type(model._get_kind() + 'Form', (base_class,), field_dict)

########NEW FILE########
__FILENAME__ = fields
from wtforms.fields import HiddenField


class CSRFTokenField(HiddenField):
    current_token = None

    def _value(self):
        """
        We want to always return the current token on render, regardless of
        whether a good or bad token was passed.
        """
        return self.current_token

    def populate_obj(self, *args):
        """
        Don't populate objects with the CSRF token
        """
        pass

########NEW FILE########
__FILENAME__ = form
from __future__ import unicode_literals

from wtforms.form import Form
from wtforms.validators import ValidationError

from .fields import CSRFTokenField


class SecureForm(Form):
    """
    Form that enables CSRF processing via subclassing hooks.
    """
    csrf_token = CSRFTokenField()

    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None, **kwargs):
        """
        :param csrf_context:
            Optional extra data which is passed transparently to your
            CSRF implementation.
        """
        super(SecureForm, self).__init__(formdata, obj, prefix, **kwargs)
        self.csrf_token.current_token = self.generate_csrf_token(csrf_context)

    def generate_csrf_token(self, csrf_context):
        """
        Implementations must override this to provide a method with which one
        can get a CSRF token for this form.

        A CSRF token should be a string which can be generated
        deterministically so that on the form POST, the generated string is
        (usually) the same assuming the user is using the site normally.

        :param csrf_context:
            A transparent object which can be used as contextual info for
            generating the token.
        """
        raise NotImplementedError()

    def validate_csrf_token(self, field):
        """
        Override this method to provide custom CSRF validation logic.

        The default CSRF validation logic simply checks if the recently
        generated token equals the one we received as formdata.
        """
        if field.current_token != field.data:
            raise ValidationError(field.gettext('Invalid CSRF Token'))

    @property
    def data(self):
        d = super(SecureForm, self).data
        d.pop('csrf_token')
        return d

########NEW FILE########
__FILENAME__ = session
"""
A provided CSRF implementation which puts CSRF data in a session.

This can be used fairly comfortably with many `request.session` type
objects, including the Werkzeug/Flask session store, Django sessions, and
potentially other similar objects which use a dict-like API for storing
session keys.

The basic concept is a randomly generated value is stored in the user's
session, and an hmac-sha1 of it (along with an optional expiration time,
for extra security) is used as the value of the csrf_token. If this token
validates with the hmac of the random value + expiration time, and the
expiration time is not passed, the CSRF validation will pass.
"""
from __future__ import unicode_literals

import hmac
import os

from hashlib import sha1
from datetime import datetime, timedelta

from ...validators import ValidationError
from .form import SecureForm

__all__ = ('SessionSecureForm', )


class SessionSecureForm(SecureForm):
    TIME_FORMAT = '%Y%m%d%H%M%S'
    TIME_LIMIT = timedelta(minutes=30)
    SECRET_KEY = None

    def generate_csrf_token(self, csrf_context):
        if self.SECRET_KEY is None:
            raise Exception('must set SECRET_KEY in a subclass of this form for it to work')
        if csrf_context is None:
            raise TypeError('Must provide a session-like object as csrf context')

        session = getattr(csrf_context, 'session', csrf_context)

        if 'csrf' not in session:
            session['csrf'] = sha1(os.urandom(64)).hexdigest()

        self.csrf_token.csrf_key = session['csrf']
        if self.TIME_LIMIT:
            expires = (datetime.now() + self.TIME_LIMIT).strftime(self.TIME_FORMAT)
            csrf_build = '%s%s' % (session['csrf'], expires)
        else:
            expires = ''
            csrf_build = session['csrf']

        hmac_csrf = hmac.new(self.SECRET_KEY, csrf_build.encode('utf8'), digestmod=sha1)
        return '%s##%s' % (expires, hmac_csrf.hexdigest())

    def validate_csrf_token(self, field):
        if not field.data or '##' not in field.data:
            raise ValidationError(field.gettext('CSRF token missing'))

        expires, hmac_csrf = field.data.split('##')

        check_val = (field.csrf_key + expires).encode('utf8')

        hmac_compare = hmac.new(self.SECRET_KEY, check_val, digestmod=sha1)
        if hmac_compare.hexdigest() != hmac_csrf:
            raise ValidationError(field.gettext('CSRF failed'))

        if self.TIME_LIMIT:
            now_formatted = datetime.now().strftime(self.TIME_FORMAT)
            if now_formatted > expires:
                raise ValidationError(field.gettext('CSRF token expired'))

########NEW FILE########
__FILENAME__ = fields
"""
A DateTimeField and DateField that use the `dateutil` package for parsing.
"""
from __future__ import unicode_literals

from dateutil import parser

from wtforms.fields import Field
from wtforms.validators import ValidationError
from wtforms.widgets import TextInput


__all__ = (
    'DateTimeField', 'DateField',
)


# This is a fix to handle issues in dateutil which arose in version 2.2.
# A bug ticket is filed: https://bugs.launchpad.net/dateutil/+bug/1247643
try:
    parser.parse('foobar')
except TypeError:
    DATEUTIL_TYPEERROR_ISSUE = True
except ValueError:
    DATEUTIL_TYPEERROR_ISSUE = False
else:
    import warnings
    warnings.warn('In testing for a dateutil issue, we ran into a very strange error.', ImportWarning)


class DateTimeField(Field):
    """
    DateTimeField represented by a text input, accepts all input text formats
    that `dateutil.parser.parse` will.

    :param parse_kwargs:
        A dictionary of keyword args to pass to the dateutil parse() function.
        See dateutil docs for available keywords.
    :param display_format:
        A format string to pass to strftime() to format dates for display.
    """
    widget = TextInput()

    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d %H:%M', **kwargs):
        super(DateTimeField, self).__init__(label, validators, **kwargs)
        if parse_kwargs is None:
            parse_kwargs = {}
        self.parse_kwargs = parse_kwargs
        self.display_format = display_format

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.display_format) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            if not date_str:
                self.data = None
                raise ValidationError(self.gettext('Please input a date/time value'))

            parse_kwargs = self.parse_kwargs.copy()
            if 'default' not in parse_kwargs:
                try:
                    parse_kwargs['default'] = self.default()
                except TypeError:
                    parse_kwargs['default'] = self.default
            try:
                self.data = parser.parse(date_str, **parse_kwargs)
            except ValueError:
                self.data = None
                raise ValidationError(self.gettext('Invalid date/time input'))
            except TypeError:
                if not DATEUTIL_TYPEERROR_ISSUE:
                    raise

                # If we're using dateutil 2.2, then consider it a normal
                # ValidationError. Hopefully dateutil fixes this issue soon.
                self.data = None
                raise ValidationError(self.gettext('Invalid date/time input'))


class DateField(DateTimeField):
    """
    Same as the DateTimeField, but stores only the date portion.
    """
    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(label, validators, parse_kwargs=parse_kwargs, display_format=display_format, **kwargs)

    def process_formdata(self, valuelist):
        super(DateField, self).process_formdata(valuelist)
        if self.data is not None and hasattr(self.data, 'date'):
            self.data = self.data.date()

########NEW FILE########
__FILENAME__ = fields
"""
Useful form fields for use with the Django ORM.
"""
from __future__ import unicode_literals

import datetime
import operator

try:
    from django.conf import settings
    from django.utils import timezone
    has_timezone = True
except ImportError:
    has_timezone = False

from wtforms import fields, widgets
from wtforms.compat import string_types
from wtforms.validators import ValidationError

__all__ = (
    'ModelSelectField', 'QuerySetSelectField', 'DateTimeField'
)


class QuerySetSelectField(fields.SelectFieldBase):
    """
    Given a QuerySet either at initialization or inside a view, will display a
    select drop-down field of choices. The `data` property actually will
    store/keep an ORM model instance, not the ID. Submitting a choice which is
    not in the queryset will result in a validation error.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`.  The label for the blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, queryset=None, get_label=None, allow_blank=False, blank_text='', **kwargs):
        super(QuerySetSelectField, self).__init__(label, validators, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if queryset is not None:
            self.queryset = queryset.all()  # Make sure the queryset is fresh

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.queryset:
                if obj.pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.queryset:
            yield (obj.pk, self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = int(valuelist[0])

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.queryset:
                if self.data == obj:
                    break
            else:
                raise ValidationError(self.gettext('Not a valid choice'))


class ModelSelectField(QuerySetSelectField):
    """
    Like a QuerySetSelectField, except takes a model class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=None, validators=None, model=None, **kwargs):
        super(ModelSelectField, self).__init__(label, validators, queryset=model._default_manager.all(), **kwargs)


class DateTimeField(fields.DateTimeField):
    """
    Adds support for Django's timezone utilities.
    Requires Django >= 1.5
    """
    def __init__(self, *args, **kwargs):
        if not has_timezone:
            raise ImportError('DateTimeField requires Django >= 1.5')

        super(DateTimeField, self).__init__(*args, **kwargs)

    def process_formdata(self, valuelist):
        super(DateTimeField, self).process_formdata(valuelist)

        date = self.data

        if settings.USE_TZ and date is not None and timezone.is_naive(date):
            current_timezone = timezone.get_current_timezone()
            self.data = timezone.make_aware(date, current_timezone)

    def _value(self):
        date = self.data

        if settings.USE_TZ and isinstance(date, datetime.datetime) and timezone.is_aware(date):
            self.data = timezone.localtime(date)

        return super(DateTimeField, self)._value()

########NEW FILE########
__FILENAME__ = i18n
from django.utils.translation import ugettext, ungettext
from wtforms import form


class DjangoTranslations(object):
    """
    A translations object for WTForms that gets its messages from django's
    translations providers.
    """
    def gettext(self, string):
        return ugettext(string)

    def ngettext(self, singular, plural, n):
        return ungettext(singular, plural, n)


class Form(form.Form):
    """
    A Form derivative which uses the translations engine from django.
    """
    _django_translations = DjangoTranslations()

    def _get_translations(self):
        return self._django_translations

########NEW FILE########
__FILENAME__ = orm
"""
Tools for generating forms based on Django models.
"""
from wtforms import fields as f
from wtforms import Form
from wtforms import validators
from wtforms.compat import iteritems
from wtforms.ext.django.fields import ModelSelectField


__all__ = (
    'model_fields', 'model_form',
)


class ModelConverterBase(object):
    def __init__(self, converters):
        self.converters = converters

    def convert(self, model, field, field_args):
        kwargs = {
            'label': field.verbose_name,
            'description': field.help_text,
            'validators': [],
            'filters': [],
            'default': field.default,
        }
        if field_args:
            kwargs.update(field_args)

        if field.blank:
            kwargs['validators'].append(validators.Optional())
        if field.max_length is not None and field.max_length > 0:
            kwargs['validators'].append(validators.Length(max=field.max_length))

        ftype = type(field).__name__
        if field.choices:
            kwargs['choices'] = field.choices
            return f.SelectField(**kwargs)
        elif ftype in self.converters:
            return self.converters[ftype](model, field, kwargs)
        else:
            converter = getattr(self, 'conv_%s' % ftype, None)
            if converter is not None:
                return converter(model, field, kwargs)


class ModelConverter(ModelConverterBase):
    DEFAULT_SIMPLE_CONVERSIONS = {
        f.IntegerField: ['AutoField', 'IntegerField', 'SmallIntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField'],
        f.DecimalField: ['DecimalField', 'FloatField'],
        f.FileField: ['FileField', 'FilePathField', 'ImageField'],
        f.DateTimeField: ['DateTimeField'],
        f.DateField: ['DateField'],
        f.BooleanField: ['BooleanField'],
        f.TextField: ['CharField', 'PhoneNumberField', 'SlugField'],
        f.TextAreaField: ['TextField', 'XMLField'],
    }

    def __init__(self, extra_converters=None, simple_conversions=None):
        converters = {}
        if simple_conversions is None:
            simple_conversions = self.DEFAULT_SIMPLE_CONVERSIONS
        for field_type, django_fields in iteritems(simple_conversions):
            converter = self.make_simple_converter(field_type)
            for name in django_fields:
                converters[name] = converter

        if extra_converters:
            converters.update(extra_converters)
        super(ModelConverter, self).__init__(converters)

    def make_simple_converter(self, field_type):
        def _converter(model, field, kwargs):
            return field_type(**kwargs)
        return _converter

    def conv_ForeignKey(self, model, field, kwargs):
        return ModelSelectField(model=field.rel.to, **kwargs)

    def conv_TimeField(self, model, field, kwargs):
        def time_only(obj):
            try:
                return obj.time()
            except AttributeError:
                return obj
        kwargs['filters'].append(time_only)
        return f.DateTimeField(format='%H:%M:%S', **kwargs)

    def conv_EmailField(self, model, field, kwargs):
        kwargs['validators'].append(validators.email())
        return f.TextField(**kwargs)

    def conv_IPAddressField(self, model, field, kwargs):
        kwargs['validators'].append(validators.ip_address())
        return f.TextField(**kwargs)

    def conv_URLField(self, model, field, kwargs):
        kwargs['validators'].append(validators.url())
        return f.TextField(**kwargs)

    def conv_NullBooleanField(self, model, field, kwargs):
        from django.db.models.fields import NOT_PROVIDED

        def coerce_nullbool(value):
            d = {'None': None, None: None, 'True': True, 'False': False}
            if isinstance(value, NOT_PROVIDED):
                return None
            elif value in d:
                return d[value]
            else:
                return bool(int(value))

        choices = ((None, 'Unknown'), (True, 'Yes'), (False, 'No'))
        return f.SelectField(choices=choices, coerce=coerce_nullbool, **kwargs)


def model_fields(model, only=None, exclude=None, field_args=None, converter=None):
    """
    Generate a dictionary of fields for a given Django model.

    See `model_form` docstring for description of parameters.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    model_fields = ((f.attname, f) for f in model._meta.fields)
    if only:
        model_fields = (x for x in model_fields if x[0] in only)
    elif exclude:
        model_fields = (x for x in model_fields if x[0] not in exclude)

    field_dict = {}
    for name, model_field in model_fields:
        field = converter.convert(model, model_field, field_args.get(name))
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, only=None, exclude=None, field_args=None, converter=None):
    """
    Create a wtforms Form for a given Django model class::

        from wtforms.ext.django.orm import model_form
        from myproject.myapp.models import User
        UserForm = model_form(User)

    :param model:
        A Django ORM model class
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    field_dict = model_fields(model, only, exclude, field_args, converter)
    return type(model._meta.object_name + 'Form', (base_class, ), field_dict)

########NEW FILE########
__FILENAME__ = wtforms
"""
Template tags for easy WTForms access in Django templates.
"""
from __future__ import unicode_literals

import re

from django import template
from django.conf import settings
from django.template import Variable

from ....compat import iteritems

register = template.Library()


class FormFieldNode(template.Node):
    def __init__(self, field_var, html_attrs):
        self.field_var = field_var
        self.html_attrs = html_attrs

    def render(self, context):
        try:
            if '.' in self.field_var:
                base, field_name = self.field_var.rsplit('.', 1)
                field = getattr(Variable(base).resolve(context), field_name)
            else:
                field = context[self.field_var]
        except (template.VariableDoesNotExist, KeyError, AttributeError):
            return settings.TEMPLATE_STRING_IF_INVALID

        h_attrs = {}
        for k, v in iteritems(self.html_attrs):
            try:
                h_attrs[k] = v.resolve(context)
            except template.VariableDoesNotExist:
                h_attrs[k] = settings.TEMPLATE_STRING_IF_INVALID

        return field(**h_attrs)


@register.tag(name='form_field')
def do_form_field(parser, token):
    """
    Render a WTForms form field allowing optional HTML attributes.
    Invocation looks like this:
      {% form_field form.username class="big_text" onclick="alert('hello')" %}
    where form.username is the path to the field value we want.  Any number
    of key="value" arguments are supported. Unquoted values are resolved as
    template variables.
    """
    parts = token.contents.split(' ', 2)
    if len(parts) < 2:
        error_text = '%r tag must have the form field name as the first value, followed by optional key="value" attributes.'
        raise template.TemplateSyntaxError(error_text % parts[0])

    html_attrs = {}
    if len(parts) == 3:
        raw_args = list(args_split(parts[2]))
        if (len(raw_args) % 2) != 0:
            raise template.TemplateSyntaxError('%r tag received the incorrect number of key=value arguments.' % parts[0])
        for x in range(0, len(raw_args), 2):
            html_attrs[str(raw_args[x])] = Variable(raw_args[x + 1])

    return FormFieldNode(parts[1], html_attrs)


args_split_re = re.compile(r'''("(?:[^"\\]*(?:\\.[^"\\]*)*)"|'(?:[^'\\]*(?:\\.[^'\\]*)*)'|[^\s=]+)''')


def args_split(text):
    """ Split space-separated key=value arguments.  Keeps quoted strings intact. """
    for bit in args_split_re.finditer(text):
        bit = bit.group(0)
        if bit[0] == '"' and bit[-1] == '"':
            yield '"' + bit[1:-1].replace('\\"', '"').replace('\\\\', '\\') + '"'
        elif bit[0] == "'" and bit[-1] == "'":
            yield "'" + bit[1:-1].replace("\\'", "'").replace("\\\\", "\\") + "'"
        else:
            yield bit

########NEW FILE########
__FILENAME__ = form
import warnings
from wtforms import form
from wtforms.ext.i18n.utils import get_translations

translations_cache = {}


class Form(form.Form):
    """
    Base form for a simple localized WTForms form.

    **NOTE** this class is now un-necessary as the i18n features have
    been moved into the core of WTForms, and will be removed in WTForms 3.0.

    This will use the stdlib gettext library to retrieve an appropriate
    translations object for the language, by default using the locale
    information from the environment.

    If the LANGUAGES class variable is overridden and set to a sequence of
    strings, this will be a list of languages by priority to use instead, e.g::

        LANGUAGES = ['en_GB', 'en']

    One can also provide the languages by passing `LANGUAGES=` to the
    constructor of the form.

    Translations objects are cached to prevent having to get a new one for the
    same languages every instantiation.
    """
    LANGUAGES = None

    def __init__(self, *args, **kwargs):
        warnings.warn('i18n is now in core, wtforms.ext.i18n will be removed in WTForms 3.0', DeprecationWarning)
        if 'LANGUAGES' in kwargs:
            self.LANGUAGES = kwargs.pop('LANGUAGES')
        super(Form, self).__init__(*args, **kwargs)

    def _get_translations(self):
        languages = tuple(self.LANGUAGES) if self.LANGUAGES else (self.meta.locales or None)
        if languages not in translations_cache:
            translations_cache[languages] = get_translations(languages)
        return translations_cache[languages]

########NEW FILE########
__FILENAME__ = utils
"""
Module is just here for compatibility reasons, and will be removed in a future release.

Importing this will cause a DeprecationWarning.
"""
__all__ = ('messages_path', 'get_builtin_gnu_translations', 'get_translations', 'DefaultTranslations')

from wtforms.i18n import (messages_path, get_builtin_gnu_translations, get_translations, DefaultTranslations)


import warnings
warnings.warn('i18n utils have been merged into core, and this module will go away in WTForms 1.2', DeprecationWarning)

########NEW FILE########
__FILENAME__ = fields
"""
Useful form fields for use with SQLAlchemy ORM.
"""
from __future__ import unicode_literals

import operator

from wtforms import widgets
from wtforms.compat import text_type, string_types
from wtforms.fields import SelectFieldBase
from wtforms.validators import ValidationError

try:
    from sqlalchemy.orm.util import identity_key
    has_identity_key = True
except ImportError:
    has_identity_key = False


__all__ = (
    'QuerySelectField', 'QuerySelectMultipleField',
)


class QuerySelectField(SelectFieldBase):
    """
    Will display a select drop-down field to choose between ORM results in a
    sqlalchemy `Query`.  The `data` property actually will store/keep an ORM
    model instance, not the ID. Submitting a choice which is not in the query
    will result in a validation error.

    This field only works for queries on models whose primary key column(s)
    have a consistent string representation. This means it mostly only works
    for those composed of string, unicode, and integer types. For the most
    part, the primary keys will be auto-detected from the model, alternately
    pass a one-argument callable to `get_pk` which can return a unique
    comparable key.

    The `query` property on the field can be set from within a view to assign
    a query per-instance to the field. If the property is not set, the
    `query_factory` callable passed to the field constructor will be called to
    obtain a query.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`. The label for this blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, query_factory=None,
                 get_pk=None, get_label=None, allow_blank=False,
                 blank_text='', **kwargs):
        super(QuerySelectField, self).__init__(label, validators, **kwargs)
        self.query_factory = query_factory

        if get_pk is None:
            if not has_identity_key:
                raise Exception('The sqlalchemy identity_key function could not be imported.')
            self.get_pk = get_pk_from_identity
        else:
            self.get_pk = get_pk

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self.query = None
        self._object_list = None

    def _get_data(self):
        if self._formdata is not None:
            for pk, obj in self._get_object_list():
                if pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def _get_object_list(self):
        if self._object_list is None:
            query = self.query or self.query_factory()
            get_pk = self.get_pk
            self._object_list = list((text_type(get_pk(obj)), obj) for obj in query)
        return self._object_list

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if self.allow_blank and valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        data = self.data
        if data is not None:
            for pk, obj in self._get_object_list():
                if data == obj:
                    break
            else:
                raise ValidationError(self.gettext('Not a valid choice'))
        elif self._formdata or not self.allow_blank:
            raise ValidationError(self.gettext('Not a valid choice'))


class QuerySelectMultipleField(QuerySelectField):
    """
    Very similar to QuerySelectField with the difference that this will
    display a multiple select. The data property will hold a list with ORM
    model instances and will be an empty list when no value is selected.

    If any of the items in the data list or submitted form data cannot be
    found in the query, this will result in a validation error.
    """
    widget = widgets.Select(multiple=True)

    def __init__(self, label=None, validators=None, default=None, **kwargs):
        if default is None:
            default = []
        super(QuerySelectMultipleField, self).__init__(label, validators, default=default, **kwargs)
        if kwargs.get('allow_blank', False):
            import warnings
            warnings.warn('allow_blank=True does not do anything for QuerySelectMultipleField.')
        self._invalid_formdata = False

    def _get_data(self):
        formdata = self._formdata
        if formdata is not None:
            data = []
            for pk, obj in self._get_object_list():
                if not formdata:
                    break
                elif pk in formdata:
                    formdata.remove(pk)
                    data.append(obj)
            if formdata:
                self._invalid_formdata = True
            self._set_data(data)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), obj in self.data)

    def process_formdata(self, valuelist):
        self._formdata = set(valuelist)

    def pre_validate(self, form):
        if self._invalid_formdata:
            raise ValidationError(self.gettext('Not a valid choice'))
        elif self.data:
            obj_list = list(x[1] for x in self._get_object_list())
            for v in self.data:
                if v not in obj_list:
                    raise ValidationError(self.gettext('Not a valid choice'))


def get_pk_from_identity(obj):
    cls, key = identity_key(instance=obj)
    return ':'.join(text_type(x) for x in key)

########NEW FILE########
__FILENAME__ = orm
"""
Tools for generating forms based on SQLAlchemy models.
"""
from __future__ import unicode_literals

import inspect

from wtforms import fields as f
from wtforms import validators
from wtforms.form import Form
from .fields import QuerySelectField, QuerySelectMultipleField

__all__ = (
    'model_fields', 'model_form',
)


def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner


class ModelConversionError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class ModelConverterBase(object):
    def __init__(self, converters, use_mro=True):
        self.use_mro = use_mro

        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters

    def convert(self, model, mapper, prop, field_args, db_session=None):
        if not hasattr(prop, 'columns') and not hasattr(prop, 'direction'):
            return
        elif not hasattr(prop, 'direction') and len(prop.columns) != 1:
            raise TypeError(
                'Do not know how to convert multiple-column properties currently'
            )

        kwargs = {
            'validators': [],
            'filters': [],
            'default': None,
        }

        converter = None
        column = None
        types = None

        if not hasattr(prop, 'direction'):
            column = prop.columns[0]
            # Support sqlalchemy.schema.ColumnDefault, so users can benefit
            # from  setting defaults for fields, e.g.:
            #   field = Column(DateTimeField, default=datetime.utcnow)

            default = getattr(column, 'default', None)

            if default is not None:
                # Only actually change default if it has an attribute named
                # 'arg' that's callable.
                callable_default = getattr(default, 'arg', None)

                if callable_default is not None:
                    # ColumnDefault(val).arg can be also a plain value
                    default = callable_default(None) if callable(callable_default) else callable_default

            kwargs['default'] = default

            if column.nullable:
                kwargs['validators'].append(validators.Optional())
            else:
                kwargs['validators'].append(validators.Required())

            if self.use_mro:
                types = inspect.getmro(type(column.type))
            else:
                types = [type(column.type)]

            for col_type in types:
                type_string = '%s.%s' % (col_type.__module__, col_type.__name__)
                if type_string.startswith('sqlalchemy'):
                    type_string = type_string[11:]

                if type_string in self.converters:
                    converter = self.converters[type_string]
                    break
            else:
                for col_type in types:
                    if col_type.__name__ in self.converters:
                        converter = self.converters[col_type.__name__]
                        break
                else:
                    raise ModelConversionError('Could not find field converter for %s (%r).' % (prop.key, types[0]))
        else:
            # We have a property with a direction.
            if not db_session:
                raise ModelConversionError("Cannot convert field %s, need DB session." % prop.key)

            foreign_model = prop.mapper.class_

            nullable = True
            for pair in prop.local_remote_pairs:
                if not pair[0].nullable:
                    nullable = False

            kwargs.update({
                'allow_blank': nullable,
                'query_factory': lambda: db_session.query(foreign_model).all()
            })

            converter = self.converters[prop.direction.name]

        if field_args:
            kwargs.update(field_args)

        return converter(
            model=model,
            mapper=mapper,
            prop=prop,
            column=column,
            field_args=kwargs
        )


class ModelConverter(ModelConverterBase):
    def __init__(self, extra_converters=None, use_mro=True):
        super(ModelConverter, self).__init__(extra_converters, use_mro=use_mro)

    @classmethod
    def _string_common(cls, column, field_args, **extra):
        if column.type.length:
            field_args['validators'].append(validators.Length(max=column.type.length))

    @converts('String', 'Unicode')
    def conv_String(self, field_args, **extra):
        self._string_common(field_args=field_args, **extra)
        return f.TextField(**field_args)

    @converts('types.Text', 'UnicodeText', 'types.LargeBinary', 'types.Binary', 'sql.sqltypes.Text')
    def conv_Text(self, field_args, **extra):
        self._string_common(field_args=field_args, **extra)
        return f.TextAreaField(**field_args)

    @converts('Boolean')
    def conv_Boolean(self, field_args, **extra):
        return f.BooleanField(**field_args)

    @converts('Date')
    def conv_Date(self, field_args, **extra):
        return f.DateField(**field_args)

    @converts('DateTime')
    def conv_DateTime(self, field_args, **extra):
        return f.DateTimeField(**field_args)

    @converts('Enum')
    def conv_Enum(self, column, field_args, **extra):
        if 'choices' not in field_args:
            field_args['choices'] = [(e, e) for e in column.type.enums]
        return f.SelectField(**field_args)

    @converts('Integer', 'SmallInteger')
    def handle_integer_types(self, column, field_args, **extra):
        unsigned = getattr(column.type, 'unsigned', False)
        if unsigned:
            field_args['validators'].append(validators.NumberRange(min=0))
        return f.IntegerField(**field_args)

    @converts('Numeric', 'Float')
    def handle_decimal_types(self, column, field_args, **extra):
        places = getattr(column.type, 'scale', 2)
        if places is not None:
            field_args['places'] = places
        return f.DecimalField(**field_args)

    @converts('databases.mysql.MSYear', 'dialects.mysql.base.YEAR')
    def conv_MSYear(self, field_args, **extra):
        field_args['validators'].append(validators.NumberRange(min=1901, max=2155))
        return f.TextField(**field_args)

    @converts('databases.postgres.PGInet', 'dialects.postgresql.base.INET')
    def conv_PGInet(self, field_args, **extra):
        field_args.setdefault('label', 'IP Address')
        field_args['validators'].append(validators.IPAddress())
        return f.TextField(**field_args)

    @converts('dialects.postgresql.base.MACADDR')
    def conv_PGMacaddr(self, field_args, **extra):
        field_args.setdefault('label', 'MAC Address')
        field_args['validators'].append(validators.MacAddress())
        return f.TextField(**field_args)

    @converts('dialects.postgresql.base.UUID')
    def conv_PGUuid(self, field_args, **extra):
        field_args.setdefault('label', 'UUID')
        field_args['validators'].append(validators.UUID())
        return f.TextField(**field_args)

    @converts('MANYTOONE')
    def conv_ManyToOne(self, field_args, **extra):
        return QuerySelectField(**field_args)

    @converts('MANYTOMANY', 'ONETOMANY')
    def conv_ManyToMany(self, field_args, **extra):
        return QuerySelectMultipleField(**field_args)


def model_fields(model, db_session=None, only=None, exclude=None,
                 field_args=None, converter=None, exclude_pk=False,
                 exclude_fk=False):
    """
    Generate a dictionary of fields for a given SQLAlchemy model.

    See `model_form` docstring for description of parameters.
    """
    mapper = model._sa_class_manager.mapper
    converter = converter or ModelConverter()
    field_args = field_args or {}
    properties = []

    for prop in mapper.iterate_properties:
        if getattr(prop, 'columns', None):
            if exclude_fk and prop.columns[0].foreign_keys:
                continue
            elif exclude_pk and prop.columns[0].primary_key:
                continue

        properties.append((prop.key, prop))

    # ((p.key, p) for p in mapper.iterate_properties)
    if only:
        properties = (x for x in properties if x[0] in only)
    elif exclude:
        properties = (x for x in properties if x[0] not in exclude)

    field_dict = {}
    for name, prop in properties:
        field = converter.convert(
            model, mapper, prop,
            field_args.get(name), db_session
        )
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, db_session=None, base_class=Form, only=None,
               exclude=None, field_args=None, converter=None, exclude_pk=True,
               exclude_fk=True, type_name=None):
    """
    Create a wtforms Form for a given SQLAlchemy model class::

        from wtalchemy.orm import model_form
        from myapp.models import User
        UserForm = model_form(User)

    :param model:
        A SQLAlchemy mapped model class.
    :param db_session:
        An optional SQLAlchemy Session.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    :param exclude_pk:
        An optional boolean to force primary key exclusion.
    :param exclude_fk:
        An optional boolean to force foreign keys exclusion.
    :param type_name:
        An optional string to set returned type name.
    """
    if not hasattr(model, '_sa_class_manager'):
        raise TypeError('model must be a sqlalchemy mapped model')

    type_name = type_name or str(model.__name__ + 'Form')
    field_dict = model_fields(
        model, db_session, only, exclude, field_args, converter,
        exclude_pk=exclude_pk, exclude_fk=exclude_fk
    )
    return type(type_name, (base_class, ), field_dict)

########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

import datetime
import decimal
import itertools

from wtforms import widgets
from wtforms.compat import text_type, izip
from wtforms.i18n import DummyTranslations
from wtforms.validators import StopValidation
from wtforms.utils import unset_value


__all__ = (
    'BooleanField', 'DecimalField', 'DateField', 'DateTimeField', 'FieldList',
    'FloatField', 'FormField', 'IntegerField', 'RadioField', 'SelectField',
    'SelectMultipleField', 'StringField',
)


class Field(object):
    """
    Field base class
    """
    errors = tuple()
    process_errors = tuple()
    raw_data = None
    validators = tuple()
    widget = None
    _formfield = True
    _translations = DummyTranslations()
    do_not_call_in_templates = True  # Allow Django 1.4 traversal

    def __new__(cls, *args, **kwargs):
        if '_form' in kwargs and '_name' in kwargs:
            return super(Field, cls).__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(self, label=None, validators=None, filters=tuple(),
                 description='', id=None, default=None, widget=None,
                 _form=None, _name=None, _prefix='', _translations=None,
                 _meta=None):
        """
        Construct a new field.

        :param label:
            The label of the field.
        :param validators:
            A sequence of validators to call when `validate` is called.
        :param filters:
            A sequence of filters which are run on input data by `process`.
        :param description:
            A description for the field, typically used for help text.
        :param id:
            An id to use for the field. A reasonable default is set by the form,
            and you shouldn't need to set this manually.
        :param default:
            The default value to assign to the field, if no form or object
            input is provided. May be a callable.
        :param widget:
            If provided, overrides the widget used to render the field.
        :param _form:
            The form holding this field. It is passed by the form itself during
            construction. You should never pass this value yourself.
        :param _name:
            The name of this field, passed by the enclosing form during its
            construction. You should never pass this value yourself.
        :param _prefix:
            The prefix to prepend to the form name of this field, passed by
            the enclosing form during construction.
        :param _translations:
            A translations object providing message translations. Usually
            passed by the enclosing form during construction. See
            :doc:`I18n docs <i18n>` for information on message translations.
        :param _meta:
            If provided, this is the 'meta' instance from the form. You usually
            don't pass this yourself.

        If `_form` and `_name` isn't provided, an :class:`UnboundField` will be
        returned instead. Call its :func:`bind` method with a form instance and
        a name to construct the field.
        """
        if _translations is not None:
            self._translations = _translations

        if _meta is not None:
            self.meta = _meta
        elif _form is not None:
            self.meta = _form.meta
        else:
            raise TypeError("Must provide one of _form or _meta")

        self.default = default
        self.description = description
        self.filters = filters
        self.flags = Flags()
        self.name = _prefix + _name
        self.short_name = _name
        self.type = type(self).__name__
        self.validators = validators or list(self.validators)

        self.id = id or self.name
        self.label = Label(self.id, label if label is not None else self.gettext(_name.replace('_', ' ').title()))

        if widget is not None:
            self.widget = widget

        for v in self.validators:
            flags = getattr(v, 'field_flags', ())
            for f in flags:
                setattr(self.flags, f, True)

    def __unicode__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __str__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __html__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the :meth:`__call__` method.
        """
        return self()

    def __call__(self, **kwargs):
        """
        Render this field as HTML, using keyword args as additional attributes.

        This delegates rendering to
        :meth:`meta.render_field <wtforms.meta.DefaultMeta.render_field>`
        whose default behavior is to call the field's widget, passing any
        keyword arguments from this call along to the widget.

        In all of the WTForms HTML widgets, keyword arguments are turned to
        HTML attributes, though in theory a widget is free to do anything it
        wants with the supplied keyword arguments, and widgets don't have to
        even do anything related to HTML.
        """
        return self.meta.render_field(self, kwargs)

    def gettext(self, string):
        """
        Get a translation for the given message.

        This proxies for the internal translations object.

        :param string: A unicode string to be translated.
        :return: A unicode string which is the translated output.
        """
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        """
        Get a translation for a message which can be pluralized.

        :param str singular: The singular form of the message.
        :param str plural: The plural form of the message.
        :param int n: The number of elements this message is referring to
        """
        return self._translations.ngettext(singular, plural, n)

    def validate(self, form, extra_validators=tuple()):
        """
        Validates the field and returns True or False. `self.errors` will
        contain any errors raised during validation. This is usually only
        called by `Form.validate`.

        Subfields shouldn't override this, but rather override either
        `pre_validate`, `post_validate` or both, depending on needs.

        :param form: The form the field belongs to.
        :param extra_validators: A sequence of extra validators to run.
        """
        self.errors = list(self.process_errors)
        stop_validation = False

        # Call pre_validate
        try:
            self.pre_validate(form)
        except StopValidation as e:
            if e.args and e.args[0]:
                self.errors.append(e.args[0])
            stop_validation = True
        except ValueError as e:
            self.errors.append(e.args[0])

        # Run validators
        if not stop_validation:
            chain = itertools.chain(self.validators, extra_validators)
            stop_validation = self._run_validation_chain(form, chain)

        # Call post_validate
        try:
            self.post_validate(form, stop_validation)
        except ValueError as e:
            self.errors.append(e.args[0])

        return len(self.errors) == 0

    def _run_validation_chain(self, form, validators):
        """
        Run a validation chain, stopping if any validator raises StopValidation.

        :param form: The Form instance this field beongs to.
        :param validators: a sequence or iterable of validator callables.
        :return: True if validation was stopped, False otherwise.
        """
        for validator in validators:
            try:
                validator(form, self)
            except StopValidation as e:
                if e.args and e.args[0]:
                    self.errors.append(e.args[0])
                return True
            except ValueError as e:
                self.errors.append(e.args[0])

        return False

    def pre_validate(self, form):
        """
        Override if you need field-level validation. Runs before any other
        validators.

        :param form: The form the field belongs to.
        """
        pass

    def post_validate(self, form, validation_stopped):
        """
        Override if you need to run any field-level validation tasks after
        normal validation. This shouldn't be needed in most cases.

        :param form: The form the field belongs to.
        :param validation_stopped:
            `True` if any validator raised StopValidation.
        """
        pass

    def process(self, formdata, data=unset_value):
        """
        Process incoming data, calling process_data, process_formdata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_formdata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.
        """
        self.process_errors = []
        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        try:
            self.process_data(data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

        if formdata:
            try:
                if self.name in formdata:
                    self.raw_data = formdata.getlist(self.name)
                else:
                    self.raw_data = []
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

        try:
            for filter in self.filters:
                    self.data = filter(self.data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        self.data = value

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        if valuelist:
            self.data = valuelist[0]

    def populate_obj(self, obj, name):
        """
        Populates `obj.<name>` with the field's data.

        :note: This is a destructive operation. If `obj.<name>` already exists,
               it will be overridden. Use with caution.
        """
        setattr(obj, name, self.data)


class UnboundField(object):
    _formfield = True
    creation_counter = 0

    def __init__(self, field_class, *args, **kwargs):
        UnboundField.creation_counter += 1
        self.field_class = field_class
        self.args = args
        self.kwargs = kwargs
        self.creation_counter = UnboundField.creation_counter

    def bind(self, form, name, prefix='', translations=None, **kwargs):
        kw = dict(
            self.kwargs,
            _form=form,
            _prefix=prefix,
            _name=name,
            _translations=translations,
            **kwargs
        )
        return self.field_class(*self.args, **kw)

    def __repr__(self):
        return '<UnboundField(%s, %r, %r)>' % (self.field_class.__name__, self.args, self.kwargs)


class Flags(object):
    """
    Holds a set of boolean flags as attributes.

    Accessing a non-existing attribute returns False for its value.
    """
    def __getattr__(self, name):
        if name.startswith('_'):
            return super(Flags, self).__getattr__(name)
        return False

    def __contains__(self, name):
        return getattr(self, name)

    def __repr__(self):
        flags = (name for name in dir(self) if not name.startswith('_'))
        return '<wtforms.fields.Flags: {%s}>' % ', '.join(flags)


class Label(object):
    """
    An HTML form label.
    """
    def __init__(self, field_id, text):
        self.field_id = field_id
        self.text = text

    def __str__(self):
        return self()

    def __unicode__(self):
        return self()

    def __html__(self):
        return self()

    def __call__(self, text=None, **kwargs):
        if 'for_' in kwargs:
            kwargs['for'] = kwargs.pop('for_')
        else:
            kwargs.setdefault('for', self.field_id)

        attributes = widgets.html_params(**kwargs)
        return widgets.HTMLString('<label %s>%s</label>' % (attributes, text or self.text))

    def __repr__(self):
        return 'Label(%r, %r)' % (self.field_id, self.text)


class SelectFieldBase(Field):
    option_widget = widgets.Option()

    """
    Base class for fields which can be iterated to produce options.

    This isn't a field, but an abstract base class for fields which want to
    provide this functionality.
    """
    def __init__(self, label=None, validators=None, option_widget=None, **kwargs):
        super(SelectFieldBase, self).__init__(label, validators, **kwargs)

        if option_widget is not None:
            self.option_widget = option_widget

    def iter_choices(self):
        """
        Provides data for choice widget rendering. Must return a sequence or
        iterable of (value, label, selected) tuples.
        """
        raise NotImplementedError()

    def __iter__(self):
        opts = dict(widget=self.option_widget, _name=self.name, _form=None, _meta=self.meta)
        for i, (value, label, checked) in enumerate(self.iter_choices()):
            opt = self._Option(label=label, id='%s-%d' % (self.id, i), **opts)
            opt.process(None, value)
            opt.checked = checked
            yield opt

    class _Option(Field):
        checked = False

        def _value(self):
            return text_type(self.data)


class SelectField(SelectFieldBase):
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, coerce=text_type, choices=None, **kwargs):
        super(SelectField, self).__init__(label, validators, **kwargs)
        self.coerce = coerce
        self.choices = choices

    def iter_choices(self):
        for value, label in self.choices:
            yield (value, label, self.coerce(value) == self.data)

    def process_data(self, value):
        try:
            self.data = self.coerce(value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = self.coerce(valuelist[0])
            except ValueError:
                raise ValueError(self.gettext('Invalid Choice: could not coerce'))

    def pre_validate(self, form):
        for v, _ in self.choices:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


class SelectMultipleField(SelectField):
    """
    No different from a normal select field, except this one can take (and
    validate) multiple choices.  You'll need to specify the HTML `size`
    attribute to the select field when rendering.
    """
    widget = widgets.Select(multiple=True)

    def iter_choices(self):
        for value, label in self.choices:
            selected = self.data is not None and self.coerce(value) in self.data
            yield (value, label, selected)

    def process_data(self, value):
        try:
            self.data = list(self.coerce(v) for v in value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        try:
            self.data = list(self.coerce(x) for x in valuelist)
        except ValueError:
            raise ValueError(self.gettext('Invalid choice(s): one or more data inputs could not be coerced'))

    def pre_validate(self, form):
        if self.data:
            values = list(c[0] for c in self.choices)
            for d in self.data:
                if d not in values:
                    raise ValueError(self.gettext("'%(value)s' is not a valid choice for this field") % dict(value=d))


class RadioField(SelectField):
    """
    Like a SelectField, except displays a list of radio buttons.

    Iterating the field will produce subfields (each containing a label as
    well) in order to allow custom rendering of the individual radio fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class StringField(Field):
    """
    This field is the base for most of the more complicated fields, and
    represents an ``<input type="text">``.
    """
    widget = widgets.TextInput()

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]
        else:
            self.data = ''

    def _value(self):
        return text_type(self.data) if self.data is not None else ''


class LocaleAwareNumberField(Field):
    """
    Base class for implementing locale-aware number parsing.

    Locale-aware numbers require the 'babel' package to be present.
    """
    def __init__(self, label=None, validators=None, use_locale=False, number_format=None, **kwargs):
        super(LocaleAwareNumberField, self).__init__(label, validators, **kwargs)
        self.use_locale = use_locale
        if use_locale:
            self.number_format = number_format
            self.locale = kwargs['_form'].meta.locales[0]
            self._init_babel()

    def _init_babel(self):
        try:
            from babel import numbers
            self.babel_numbers = numbers
        except ImportError:
            raise ImportError('Using locale-aware decimals requires the babel library.')

    def _parse_decimal(self, value):
        return self.babel_numbers.parse_decimal(value, self.locale)

    def _format_decimal(self, value):
        return self.babel_numbers.format_decimal(value, self.number_format, self.locale)


class IntegerField(Field):
    """
    A text field, except all input is coerced to an integer.  Erroneous input
    is ignored and will not be accepted as a value.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(IntegerField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = int(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid integer value'))


class DecimalField(LocaleAwareNumberField):
    """
    A text field which displays and coerces data of the `decimal.Decimal` type.

    :param places:
        How many decimal places to quantize the value to for display on form.
        If None, does not quantize value.
    :param rounding:
        How to round the value during quantize, for example
        `decimal.ROUND_UP`. If unset, uses the rounding value from the
        current thread's context.
    :param use_locale:
        If True, use locale-based number formatting. Locale-based number
        formatting requires the 'babel' package.
    :param number_format:
        Optional number format for locale. If omitted, use the default decimal
        format for the locale.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, places=unset_value, rounding=None, **kwargs):
        super(DecimalField, self).__init__(label, validators, **kwargs)
        if self.use_locale and (places is not unset_value or rounding is not None):
            raise TypeError("When using locale-aware numbers, 'places' and 'rounding' are ignored.")

        if places is unset_value:
            places = 2
        self.places = places
        self.rounding = rounding

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            if self.use_locale:
                return text_type(self._format_decimal(self.data))
            elif self.places is not None:
                if hasattr(self.data, 'quantize'):
                    exp = decimal.Decimal('.1') ** self.places
                    if self.rounding is None:
                        quantized = self.data.quantize(exp)
                    else:
                        quantized = self.data.quantize(exp, rounding=self.rounding)
                    return text_type(quantized)
                else:
                    # If for some reason, data is a float or int, then format
                    # as we would for floats using string formatting.
                    format = '%%0.%df' % self.places
                    return format % self.data
            else:
                return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                if self.use_locale:
                    self.data = self._parse_decimal(valuelist[0])
                else:
                    self.data = decimal.Decimal(valuelist[0])
            except (decimal.InvalidOperation, ValueError):
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value'))


class FloatField(Field):
    """
    A text field, except all input is coerced to an float.  Erroneous input
    is ignored and will not be accepted as a value.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(FloatField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = float(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid float value'))


class BooleanField(Field):
    """
    Represents an ``<input type="checkbox">``.

    :param false_values:
        If provided, a sequence of strings each of which is an exact match
        string of what is considered a "false" value. Defaults to the tuple
        ``('false', '')``
    """
    widget = widgets.CheckboxInput()
    false_values = ('false', '')

    def __init__(self, label=None, validators=None, false_values=None, **kwargs):
        super(BooleanField, self).__init__(label, validators, **kwargs)
        if false_values is not None:
            self.false_values = false_values

    def process_data(self, value):
        self.data = bool(value)

    def process_formdata(self, valuelist):
        if not valuelist or valuelist[0] in self.false_values:
            self.data = False
        else:
            self.data = True

    def _value(self):
        if self.raw_data:
            return text_type(self.raw_data[0])
        else:
            return 'y'


class DateTimeField(Field):
    """
    A text field which stores a `datetime.datetime` matching a format.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, format='%Y-%m-%d %H:%M:%S', **kwargs):
        super(DateTimeField, self).__init__(label, validators, **kwargs)
        self.format = format

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.format) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.datetime.strptime(date_str, self.format)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))


class DateField(DateTimeField):
    """
    Same as DateTimeField, except stores a `datetime.date`.
    """
    def __init__(self, label=None, validators=None, format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))


class FormField(Field):
    """
    Encapsulate a form as a field in another form.

    :param form_class:
        A subclass of Form that will be encapsulated.
    :param separator:
        A string which will be suffixed to this field's name to create the
        prefix to enclosed fields. The default is fine for most uses.
    """
    widget = widgets.TableWidget()

    def __init__(self, form_class, label=None, validators=None, separator='-', **kwargs):
        super(FormField, self).__init__(label, validators, **kwargs)
        self.form_class = form_class
        self.separator = separator
        self._obj = None
        if self.filters:
            raise TypeError('FormField cannot take filters, as the encapsulated data is not mutable.')
        if validators:
            raise TypeError('FormField does not accept any validators. Instead, define them on the enclosed form.')

    def process(self, formdata, data=unset_value):
        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
            self._obj = data

        self.object_data = data

        prefix = self.name + self.separator
        if isinstance(data, dict):
            self.form = self.form_class(formdata=formdata, prefix=prefix, **data)
        else:
            self.form = self.form_class(formdata=formdata, obj=data, prefix=prefix)

    def validate(self, form, extra_validators=tuple()):
        if extra_validators:
            raise TypeError('FormField does not accept in-line validators, as it gets errors from the enclosed form.')
        return self.form.validate()

    def populate_obj(self, obj, name):
        candidate = getattr(obj, name, None)
        if candidate is None:
            if self._obj is None:
                raise TypeError('populate_obj: cannot find a value to populate from the provided obj or input data/defaults')
            candidate = self._obj
            setattr(obj, name, candidate)

        self.form.populate_obj(candidate)

    def __iter__(self):
        return iter(self.form)

    def __getitem__(self, name):
        return self.form[name]

    def __getattr__(self, name):
        return getattr(self.form, name)

    @property
    def data(self):
        return self.form.data

    @property
    def errors(self):
        return self.form.errors


class FieldList(Field):
    """
    Encapsulate an ordered list of multiple instances of the same field type,
    keeping data as a list.

    >>> authors = FieldList(StringField('Name', [validators.required()]))

    :param unbound_field:
        A partially-instantiated field definition, just like that would be
        defined on a form directly.
    :param min_entries:
        if provided, always have at least this many entries on the field,
        creating blank ones if the provided input does not specify a sufficient
        amount.
    :param max_entries:
        accept no more than this many entries as input, even if more exist in
        formdata.
    """
    widget = widgets.ListWidget()

    def __init__(self, unbound_field, label=None, validators=None, min_entries=0,
                 max_entries=None, default=tuple(), **kwargs):
        super(FieldList, self).__init__(label, validators, default=default, **kwargs)
        if self.filters:
            raise TypeError('FieldList does not accept any filters. Instead, define them on the enclosed field.')
        assert isinstance(unbound_field, UnboundField), 'Field must be unbound, not a field class'
        self.unbound_field = unbound_field
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.last_index = -1
        self._prefix = kwargs.get('_prefix', '')

    def process(self, formdata, data=unset_value):
        self.entries = []
        if data is unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        if formdata:
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[:self.max_entries]

            idata = iter(data)
            for index in indices:
                try:
                    obj_data = next(idata)
                except StopIteration:
                    obj_data = unset_value
                self._add_entry(formdata, obj_data, index=index)
        else:
            for obj_data in data:
                self._add_entry(formdata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)

    def _extract_indices(self, prefix, formdata):
        """
        Yield indices of any keys with given prefix.

        formdata must be an object which will produce keys when iterated.  For
        example, if field 'foo' contains keys 'foo-0-bar', 'foo-1-baz', then
        the numbers 0 and 1 will be yielded, but not neccesarily in order.
        """
        offset = len(prefix) + 1
        for k in formdata:
            if k.startswith(prefix):
                k = k[offset:].split('-', 1)[0]
                if k.isdigit():
                    yield int(k)

    def validate(self, form, extra_validators=tuple()):
        """
        Validate this FieldList.

        Note that FieldList validation differs from normal field validation in
        that FieldList validates all its enclosed fields first before running any
        of its own validators.
        """
        self.errors = []

        # Run validators on all entries within
        for subfield in self.entries:
            if not subfield.validate(form):
                self.errors.append(subfield.errors)

        chain = itertools.chain(self.validators, extra_validators)
        self._run_validation_chain(form, chain)

        return len(self.errors) == 0

    def populate_obj(self, obj, name):
        values = getattr(obj, name, None)
        try:
            ivalues = iter(values)
        except TypeError:
            ivalues = iter([])

        candidates = itertools.chain(ivalues, itertools.repeat(None))
        _fake = type(str('_fake'), (object, ), {})
        output = []
        for field, data in izip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, 'data')
            output.append(fake_obj.data)

        setattr(obj, name, output)

    def _add_entry(self, formdata=None, data=unset_value, index=None):
        assert not self.max_entries or len(self.entries) < self.max_entries, \
            'You cannot have more than max_entries entries in this FieldList'
        if index is None:
            index = self.last_index + 1
        self.last_index = index
        name = '%s-%d' % (self.short_name, index)
        id = '%s-%d' % (self.id, index)
        field = self.unbound_field.bind(form=None, name=name, prefix=self._prefix, id=id, _meta=self.meta)
        field.process(formdata, data)
        self.entries.append(field)
        return field

    def append_entry(self, data=unset_value):
        """
        Create a new entry with optional default data.

        Entries added in this way will *not* receive formdata however, and can
        only receive object data.
        """
        return self._add_entry(data=data)

    def pop_entry(self):
        """ Removes the last entry from the list and returns it. """
        entry = self.entries.pop()
        self.last_index -= 1
        return entry

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        return self.entries[index]

    @property
    def data(self):
        return [f.data for f in self.entries]

########NEW FILE########
__FILENAME__ = html5
"""
Fields to support various HTML5 input types.
"""
from ..widgets import html5 as widgets
from . import core

__all__ = (
    'DateField', 'DateTimeField', 'DateTimeLocalField', 'DecimalField',
    'DecimalRangeField', 'EmailField', 'IntegerField', 'IntegerRangeField',
    'SearchField', 'TelField', 'URLField',
)


class SearchField(core.StringField):
    """
    Represents an ``<input type="search">``.
    """
    widget = widgets.SearchInput()


class TelField(core.StringField):
    """
    Represents an ``<input type="tel">``.
    """
    widget = widgets.TelInput()


class URLField(core.StringField):
    """
    Represents an ``<input type="url">``.
    """
    widget = widgets.URLInput()


class EmailField(core.StringField):
    """
    Represents an ``<input type="email">``.
    """
    widget = widgets.EmailInput()


class DateTimeField(core.DateTimeField):
    """
    Represents an ``<input type="datetime">``.
    """
    widget = widgets.DateTimeInput()


class DateField(core.DateField):
    """
    Represents an ``<input type="date">``.
    """
    widget = widgets.DateInput()


class DateTimeLocalField(core.DateTimeField):
    """
    Represents an ``<input type="datetime-local">``.
    """
    widget = widgets.DateTimeLocalInput()


class IntegerField(core.IntegerField):
    """
    Represents an ``<input type="number">``.
    """
    widget = widgets.NumberInput(step='1')


class DecimalField(core.DecimalField):
    """
    Represents an ``<input type="number">``.
    """
    widget = widgets.NumberInput(step='any')


class IntegerRangeField(core.IntegerField):
    """
    Represents an ``<input type="range">``.
    """
    widget = widgets.RangeInput(step='1')


class DecimalRangeField(core.DecimalField):
    """
    Represents an ``<input type="range">``.
    """
    widget = widgets.RangeInput(step='any')

########NEW FILE########
__FILENAME__ = simple
import warnings

from .. import widgets
from .core import StringField, BooleanField


__all__ = (
    'BooleanField', 'TextAreaField', 'PasswordField', 'FileField',
    'HiddenField', 'SubmitField', 'TextField'
)


class TextField(StringField):
    """
    Legacy alias for StringField

    .. deprecated:: 2.0
    """
    def __init__(self, *args, **kw):
        super(TextField, self).__init__(*args, **kw)
        warnings.warn(
            'The TextField alias for StringField has been deprecated and will be removed in WTForms 3.0',
            DeprecationWarning
        )


class TextAreaField(StringField):
    """
    This field represents an HTML ``<textarea>`` and can be used to take
    multi-line input.
    """
    widget = widgets.TextArea()


class PasswordField(StringField):
    """
    A StringField, except renders an ``<input type="password">``.

    Also, whatever value is accepted by this field is not rendered back
    to the browser like normal fields.
    """
    widget = widgets.PasswordInput()


class FileField(StringField):
    """
    Can render a file-upload field.  Will take any passed filename value, if
    any is sent by the browser in the post params.  This field will NOT
    actually handle the file upload portion, as wtforms does not deal with
    individual frameworks' file handling capabilities.
    """
    widget = widgets.FileInput()


class HiddenField(StringField):
    """
    HiddenField is a convenience for a StringField with a HiddenInput widget.

    It will render as an ``<input type="hidden">`` but otherwise coerce to a string.
    """
    widget = widgets.HiddenInput()


class SubmitField(BooleanField):
    """
    Represents an ``<input type="submit">``.  This allows checking if a given
    submit button has been pressed.
    """
    widget = widgets.SubmitInput()

########NEW FILE########
__FILENAME__ = form
import itertools
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from wtforms.compat import with_metaclass, iteritems, itervalues
from wtforms.meta import DefaultMeta

__all__ = (
    'BaseForm',
    'Form',
)


class BaseForm(object):
    """
    Base Form Class.  Provides core behaviour like field construction,
    validation, and data and error proxying.
    """

    def __init__(self, fields, prefix='', meta=DefaultMeta()):
        """
        :param fields:
            A dict or sequence of 2-tuples of partially-constructed fields.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        :param meta:
            A meta instance which is used for configuration and customization
            of WTForms behaviors.
        """
        if prefix and prefix[-1] not in '-_;:/.':
            prefix += '-'

        self.meta = meta
        self._prefix = prefix
        self._errors = None
        self._fields = OrderedDict()

        if hasattr(fields, 'items'):
            fields = fields.items()

        translations = self._get_translations()
        extra_fields = []
        if meta.csrf:
            self._csrf = meta.build_csrf(self)
            extra_fields.extend(self._csrf.setup_form(self))

        for name, unbound_field in itertools.chain(fields, extra_fields):
            options = dict(name=name, prefix=prefix, translations=translations)
            field = meta.bind_field(self, unbound_field, options)
            self._fields[name] = field

    def __iter__(self):
        """Iterate form fields in creation order."""
        return iter(itervalues(self._fields))

    def __contains__(self, name):
        """ Returns `True` if the named field is a member of this form. """
        return (name in self._fields)

    def __getitem__(self, name):
        """ Dict-style access to this form's fields."""
        return self._fields[name]

    def __setitem__(self, name, value):
        """ Bind a field to this form. """
        self._fields[name] = value.bind(form=self, name=name, prefix=self._prefix)

    def __delitem__(self, name):
        """ Remove a field from this form. """
        del self._fields[name]

    def _get_translations(self):
        """
        .. deprecated:: 2.0
            `_get_translations` is being removed in WTForms 3.0, use
            `Meta.get_translations` instead.

        Override in subclasses to provide alternate translations factory.

        Must return an object that provides gettext() and ngettext() methods.
        """
        return self.meta.get_translations(self)

    def populate_obj(self, obj):
        """
        Populates the attributes of the passed `obj` with data from the form's
        fields.

        :note: This is a destructive operation; Any attribute with the same name
               as a field will be overridden. Use with caution.
        """
        for name, field in iteritems(self._fields):
            field.populate_obj(obj, name)

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        """
        Take form, object data, and keyword arg input and have the fields
        process them.

        :param formdata:
            Used to pass data coming from the enduser, usually `request.POST` or
            equivalent.
        :param obj:
            If `formdata` is empty or not provided, this object is checked for
            attributes matching form field names, which will be used for field
            values.
        :param data:
            If provided, must be a dictionary of data. This is only used if
            `formdata` is empty or not provided and `obj` does not contain
            an attribute named the same as the field.
        :param `**kwargs`:
            If `formdata` is empty or not provided and `obj` does not contain
            an attribute named the same as a field, form will assign the value
            of a matching keyword argument to the field, if one exists.
        """
        formdata = self.meta.wrap_formdata(self, formdata)

        if data is not None:
            # XXX we want to eventually process 'data' as a new entity.
            #     Temporarily, this can simply be merged with kwargs.
            kwargs = dict(data, **kwargs)

        for name, field, in iteritems(self._fields):
            if obj is not None and hasattr(obj, name):
                field.process(formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(formdata, kwargs[name])
            else:
                field.process(formdata)

    def validate(self, extra_validators=None):
        """
        Validates the form by calling `validate` on each field.

        :param extra_validators:
            If provided, is a dict mapping field names to a sequence of
            callables which will be passed as extra validators to the field's
            `validate` method.

        Returns `True` if no errors occur.
        """
        self._errors = None
        success = True
        for name, field in iteritems(self._fields):
            if extra_validators is not None and name in extra_validators:
                extra = extra_validators[name]
            else:
                extra = tuple()
            if not field.validate(self, extra):
                success = False
        return success

    @property
    def data(self):
        return dict((name, f.data) for name, f in iteritems(self._fields))

    @property
    def errors(self):
        if self._errors is None:
            self._errors = dict((name, f.errors) for name, f in iteritems(self._fields) if f.errors)
        return self._errors


class FormMeta(type):
    """
    The metaclass for `Form` and any subclasses of `Form`.

    `FormMeta`'s responsibility is to create the `_unbound_fields` list, which
    is a list of `UnboundField` instances sorted by their order of
    instantiation.  The list is created at the first instantiation of the form.
    If any fields are added/removed from the form, the list is cleared to be
    re-generated on the next instantiaton.

    Any properties which begin with an underscore or are not `UnboundField`
    instances are ignored by the metaclass.
    """
    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields = None
        cls._wtforms_meta = None

    def __call__(cls, *args, **kwargs):
        """
        Construct a new `Form` instance.

        Creates the `_unbound_fields` list and the internal `_wtforms_meta`
        subclass of the class Meta in order to allow a proper inheritance
        hierarchy.
        """
        if cls._unbound_fields is None:
            fields = []
            for name in dir(cls):
                if not name.startswith('_'):
                    unbound_field = getattr(cls, name)
                    if hasattr(unbound_field, '_formfield'):
                        fields.append((name, unbound_field))
            # We keep the name as the second element of the sort
            # to ensure a stable sort.
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields

        # Create a subclass of the 'class Meta' using all the ancestors.
        if cls._wtforms_meta is None:
            bases = []
            for mro_class in cls.__mro__:
                if 'Meta' in mro_class.__dict__:
                    bases.append(mro_class.Meta)
            cls._wtforms_meta = type('Meta', tuple(bases), {})
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value):
        """
        Add an attribute to the class, clearing `_unbound_fields` if needed.
        """
        if name == 'Meta':
            cls._wtforms_meta = None
        elif not name.startswith('_') and hasattr(value, '_formfield'):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        """
        Remove an attribute from the class, clearing `_unbound_fields` if
        needed.
        """
        if not name.startswith('_'):
            cls._unbound_fields = None
        type.__delattr__(cls, name)


class Form(with_metaclass(FormMeta, BaseForm)):
    """
    Declarative Form base class. Extends BaseForm's core behaviour allowing
    fields to be defined on Form subclasses as class attributes.

    In addition, form and instance input data are taken at construction time
    and passed to `process()`.
    """
    Meta = DefaultMeta

    def __init__(self, formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs):
        """
        :param formdata:
            Used to pass data coming from the enduser, usually `request.POST` or
            equivalent. formdata should be some sort of request-data wrapper which
            can get multiple parameters from the form input, and values are unicode
            strings, e.g. a Werkzeug/Django/WebOb MultiDict
        :param obj:
            If `formdata` is empty or not provided, this object is checked for
            attributes matching form field names, which will be used for field
            values.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        :param data:
            Accept a dictionary of data. This is only used if `formdata` and
            `obj` are not present.
        :param meta:
            If provided, this is a dictionary of values to override attributes
            on this form's meta instance.
        :param `**kwargs`:
            If `formdata` is empty or not provided and `obj` does not contain
            an attribute named the same as a field, form will assign the value
            of a matching keyword argument to the field, if one exists.
        """
        meta_obj = self._wtforms_meta()
        if meta is not None and isinstance(meta, dict):
            meta_obj.update_values(meta)
        super(Form, self).__init__(self._unbound_fields, meta=meta_obj, prefix=prefix)

        for name, field in iteritems(self._fields):
            # Set all the fields to attributes so that they obscure the class
            # attributes with the same names.
            setattr(self, name, field)
        self.process(formdata, obj, data=data, **kwargs)

    def __setitem__(self, name, value):
        raise TypeError('Fields may not be added to Form instances, only classes.')

    def __delitem__(self, name):
        del self._fields[name]
        setattr(self, name, None)

    def __delattr__(self, name):
        if name in self._fields:
            self.__delitem__(name)
        else:
            # This is done for idempotency, if we have a name which is a field,
            # we want to mask it by setting the value to None.
            unbound_field = getattr(self.__class__, name, None)
            if unbound_field is not None and hasattr(unbound_field, '_formfield'):
                setattr(self, name, None)
            else:
                super(Form, self).__delattr__(name)

    def validate(self):
        """
        Validates the form by calling `validate` on each field, passing any
        extra `Form.validate_<fieldname>` validators to the field validator.
        """
        extra = {}
        for name in self._fields:
            inline = getattr(self.__class__, 'validate_%s' % name, None)
            if inline is not None:
                extra[name] = [inline]

        return super(Form, self).validate(extra)

########NEW FILE########
__FILENAME__ = i18n
import os


def messages_path():
    """
    Determine the path to the 'messages' directory as best possible.
    """
    module_path = os.path.abspath(__file__)
    return os.path.join(os.path.dirname(module_path), 'locale')


def get_builtin_gnu_translations(languages=None):
    """
    Get a gettext.GNUTranslations object pointing at the
    included translation files.

    :param languages:
        A list of languages to try, in order. If omitted or None, then
        gettext will try to use locale information from the environment.
    """
    import gettext
    return gettext.translation('wtforms', messages_path(), languages)


def get_translations(languages=None, getter=get_builtin_gnu_translations):
    """
    Get a WTForms translation object which wraps a low-level translations object.

    :param languages:
        A sequence of languages to try, in order.
    :param getter:
        A single-argument callable which returns a low-level translations object.
    """
    translations = getter(languages)

    if hasattr(translations, 'ugettext'):
        return DefaultTranslations(translations)
    else:
        # Python 3 has no ugettext/ungettext, so just return the translations object.
        return translations


class DefaultTranslations(object):
    """
    A WTForms translations object to wrap translations objects which use
    ugettext/ungettext.
    """
    def __init__(self, translations):
        self.translations = translations

    def gettext(self, string):
        return self.translations.ugettext(string)

    def ngettext(self, singular, plural, n):
        return self.translations.ungettext(singular, plural, n)


class DummyTranslations(object):
    """
    A translations object which simply returns unmodified strings.

    This is typically used when translations are disabled or if no valid
    translations provider can be found.
    """
    def gettext(self, string):
        return string

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular

        return plural

########NEW FILE########
__FILENAME__ = meta
from wtforms.utils import WebobInputWrapper
from wtforms import i18n


class DefaultMeta(object):
    """
    This is the default Meta class which defines all the default values and
    therefore also the 'API' of the class Meta interface.
    """

    # -- Basic form primitives

    def bind_field(self, form, unbound_field, options):
        """
        bind_field allows potential customization of how fields are bound.

        The default implementation simply passes the options to
        :meth:`UnboundField.bind`.

        :param form: The form.
        :param unbound_field: The unbound field.
        :param options:
            A dictionary of options which are typically passed to the field.

        :return: A bound field
        """
        return unbound_field.bind(form=form, **options)

    def wrap_formdata(self, form, formdata):
        """
        wrap_formdata allows doing custom wrappers of WTForms formdata.

        The default implementation detects webob-style multidicts and wraps
        them, otherwise passes formdata back un-changed.

        :param form: The form.
        :param formdata: Form data.
        :return: A form-input wrapper compatible with WTForms.
        """
        if formdata is not None and not hasattr(formdata, 'getlist'):
            if hasattr(formdata, 'getall'):
                return WebobInputWrapper(formdata)
            else:
                raise TypeError("formdata should be a multidict-type wrapper that supports the 'getlist' method")
        return formdata

    def render_field(self, field, render_kw):
        """
        render_field allows customization of how widget rendering is done.

        The default implementation calls ``field.widget(field, **render_kw)``
        """
        return field.widget(field, **render_kw)

    # -- CSRF

    csrf = False
    csrf_field_name = 'csrf_token'
    csrf_secret = None
    csrf_context = None
    csrf_class = None

    def build_csrf(self, form):
        """
        Build a CSRF implementation. This is called once per form instance.

        The default implementation builds the class referenced to by
        :attr:`csrf_class` with zero arguments. If `csrf_class` is ``None``,
        will instead use the default implementation
        :class:`wtforms.csrf.session.SessionCSRF`.

        :param form: The form.
        :return: A CSRF implementation.
        """
        if self.csrf_class is not None:
            return self.csrf_class()

        from wtforms.csrf.session import SessionCSRF
        return SessionCSRF()

    # -- i18n

    locales = False
    cache_translations = True
    translations_cache = {}

    def get_translations(self, form):
        """
        Override in subclasses to provide alternate translations factory.
        See the i18n documentation for more.

        :param form: The form.
        :return: An object that provides gettext() and ngettext() methods.
        """
        locales = self.locales
        if locales is False:
            return None

        if self.cache_translations:
            # Make locales be a hashable value
            locales = tuple(locales) if locales else None

            translations = self.translations_cache.get(locales)
            if translations is None:
                translations = self.translations_cache[locales] = i18n.get_translations(locales)

            return translations

        return i18n.get_translations(locales)

    # -- General

    def update_values(self, values):
        """
        Given a dictionary of values, update values on this `Meta` instance.
        """
        for key, value in values.items():
            setattr(self, key, value)

########NEW FILE########
__FILENAME__ = utils


class UnsetValue(object):
    """
    An unset value.

    This is used in situations where a blank value like `None` is acceptable
    usually as the default value of a class variable or function parameter
    (iow, usually when `None` is a valid value.)
    """
    def __str__(self):
        return '<unset value>'

    def __repr__(self):
        return '<unset value>'

    def __bool__(self):
        return False

    def __nonzero__(self):
        return False

unset_value = UnsetValue()


class WebobInputWrapper(object):
    """
    Wrap a webob MultiDict for use as passing as `formdata` to Field.

    Since for consistency, we have decided in WTForms to support as input a
    small subset of the API provided in common between cgi.FieldStorage,
    Django's QueryDict, and Werkzeug's MultiDict, we need to wrap Webob, the
    only supported framework whose multidict does not fit this API, but is
    nevertheless used by a lot of frameworks.

    While we could write a full wrapper to support all the methods, this will
    undoubtedly result in bugs due to some subtle differences between the
    various wrappers. So we will keep it simple.
    """

    def __init__(self, multidict):
        self._wrapped = multidict

    def __iter__(self):
        return iter(self._wrapped)

    def __len__(self):
        return len(self._wrapped)

    def __contains__(self, name):
        return (name in self._wrapped)

    def getlist(self, name):
        return self._wrapped.getall(name)

########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals

import re
import warnings

from wtforms.compat import string_types, text_type

__all__ = (
    'DataRequired', 'data_required', 'Email', 'email', 'EqualTo', 'equal_to',
    'IPAddress', 'ip_address', 'InputRequired', 'input_required', 'Length',
    'length', 'NumberRange', 'number_range', 'Optional', 'optional',
    'Required', 'required', 'Regexp', 'regexp', 'URL', 'url', 'AnyOf',
    'any_of', 'NoneOf', 'none_of', 'MacAddress', 'mac_address', 'UUID'
)


class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    def __init__(self, message='', *args, **kwargs):
        ValueError.__init__(self, message, *args, **kwargs)


class StopValidation(Exception):
    """
    Causes the validation chain to stop.

    If StopValidation is raised, no more validators in the validation chain are
    called. If raised with a message, the message will be added to the errors
    list.
    """
    def __init__(self, message='', *args, **kwargs):
        Exception.__init__(self, message, *args, **kwargs)


class EqualTo(object):
    """
    Compares the values of two fields.

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """
    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)
        if field.data != other.data:
            d = {
                'other_label': hasattr(other, 'label') and other.label.text or self.fieldname,
                'other_name': self.fieldname
            }
            message = self.message
            if message is None:
                message = field.gettext('Field must be equal to %(other_name)s.')

            raise ValidationError(message % d)


class Length(object):
    """
    Validates the length of a string.

    :param min:
        The minimum required length of the string. If not provided, minimum
        length will not be checked.
    :param max:
        The maximum length of the string. If not provided, maximum length
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)d` and `%(max)d` if desired. Useful defaults
        are provided depending on the existence of min and max.
    """
    def __init__(self, min=-1, max=-1, message=None):
        assert min != -1 or max != -1, 'At least one of `min` or `max` must be specified.'
        assert max == -1 or min <= max, '`min` cannot be more than `max`.'
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        l = field.data and len(field.data) or 0
        if l < self.min or self.max != -1 and l > self.max:
            message = self.message
            if message is None:
                if self.max == -1:
                    message = field.ngettext('Field must be at least %(min)d character long.',
                                             'Field must be at least %(min)d characters long.', self.min)
                elif self.min == -1:
                    message = field.ngettext('Field cannot be longer than %(max)d character.',
                                             'Field cannot be longer than %(max)d characters.', self.max)
                else:
                    message = field.gettext('Field must be between %(min)d and %(max)d characters long.')

            raise ValidationError(message % dict(min=self.min, max=self.max, length=l))


class NumberRange(object):
    """
    Validates that a number is of a minimum and/or maximum value, inclusive.
    This will work with any comparable number type, such as floats and
    decimals, not just integers.

    :param min:
        The minimum required value of the number. If not provided, minimum
        value will not be checked.
    :param max:
        The maximum value of the number. If not provided, maximum value
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)s` and `%(max)s` if desired. Useful defaults
        are provided depending on the existence of min and max.
    """
    def __init__(self, min=None, max=None, message=None):
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        data = field.data
        if data is None or (self.min is not None and data < self.min) or \
                (self.max is not None and data > self.max):
            message = self.message
            if message is None:
                # we use %(min)s interpolation to support floats, None, and
                # Decimals without throwing a formatting exception.
                if self.max is None:
                    message = field.gettext('Number must be at least %(min)s.')
                elif self.min is None:
                    message = field.gettext('Number must be at most %(max)s.')
                else:
                    message = field.gettext('Number must be between %(min)s and %(max)s.')

            raise ValidationError(message % dict(min=self.min, max=self.max))


class Optional(object):
    """
    Allows empty input and stops the validation chain from continuing.

    If input is empty, also removes prior errors (such as processing errors)
    from the field.

    :param strip_whitespace:
        If True (the default) also stop the validation chain on input which
        consists of only whitespace.
    """
    field_flags = ('optional', )

    def __init__(self, strip_whitespace=True):
        if strip_whitespace:
            self.string_check = lambda s: s.strip()
        else:
            self.string_check = lambda s: s

    def __call__(self, form, field):
        if not field.raw_data or isinstance(field.raw_data[0], string_types) and not self.string_check(field.raw_data[0]):
            field.errors[:] = []
            raise StopValidation()


class DataRequired(object):
    """
    Checks the field's data is 'truthy' otherwise stops the validation chain.

    This validator checks that the ``data`` attribute on the field is a 'true'
    value (effectively, it does ``if field.data``.) Furthermore, if the data
    is a string type, a string containing only whitespace characters is
    considered false.

    If the data is empty, also removes prior errors (such as processing errors)
    from the field.

    **NOTE** this validator used to be called `Required` but the way it behaved
    (requiring coerced data, not input data) meant it functioned in a way
    which was not symmetric to the `Optional` validator and furthermore caused
    confusion with certain fields which coerced data to 'falsey' values like
    ``0``, ``Decimal(0)``, ``time(0)`` etc. Unless a very specific reason
    exists, we recommend using the :class:`InputRequired` instead.

    :param message:
        Error message to raise in case of a validation error.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not field.data or isinstance(field.data, string_types) and not field.data.strip():
            if self.message is None:
                message = field.gettext('This field is required.')
            else:
                message = self.message

            field.errors[:] = []
            raise StopValidation(message)


class Required(DataRequired):
    """
    Legacy alias for DataRequired.

    This is needed over simple aliasing for those who require that the
    class-name of required be 'Required.'

    """
    def __init__(self, *args, **kwargs):
        super(Required, self).__init__(*args, **kwargs)
        warnings.warn('Required is going away in WTForms 3.0, use DataRequired', DeprecationWarning)


class InputRequired(object):
    """
    Validates that input was provided for this field.

    Note there is a distinction between this and DataRequired in that
    InputRequired looks that form-input data was provided, and DataRequired
    looks at the post-coercion data.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not field.raw_data or not field.raw_data[0]:
            if self.message is None:
                message = field.gettext('This field is required.')
            else:
                message = self.message

            field.errors[:] = []
            raise StopValidation(message)


class Regexp(object):
    """
    Validates the field against a user provided regexp.

    :param regex:
        The regular expression string to use. Can also be a compiled regular
        expression pattern.
    :param flags:
        The regexp flags to use, for example re.IGNORECASE. Ignored if
        `regex` is not a string.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, regex, flags=0, message=None):
        if isinstance(regex, string_types):
            regex = re.compile(regex, flags)
        self.regex = regex
        self.message = message

    def __call__(self, form, field, message=None):
        if not self.regex.match(field.data or ''):
            if message is None:
                if self.message is None:
                    message = field.gettext('Invalid input.')
                else:
                    message = self.message

            raise ValidationError(message)


class Email(Regexp):
    """
    Validates an email address. Note that this uses a very primitive regular
    expression and should only be used in instances where you later verify by
    other means, such as email activation or lookups.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        super(Email, self).__init__(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE, message)

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext('Invalid email address.')

        super(Email, self).__call__(form, field, message)


class IPAddress(object):
    """
    Validates an IP address.

    :param ipv4:
        If True, accept IPv4 addresses as valid (default True)
    :param ipv6:
        If True, accept IPv6 addresses as valid (default False)
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, ipv4=True, ipv6=False, message=None):
        if not ipv4 and not ipv6:
            raise ValueError('IP Address Validator must have at least one of ipv4 or ipv6 enabled.')
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        if value:
            valid = (self.ipv4 and self.check_ipv4(value)) or (self.ipv6 and self.check_ipv6(value))

        if not valid:
            message = self.message
            if message is None:
                message = field.gettext('Invalid IP address.')
            raise ValidationError(message)

    def check_ipv4(self, value):
        parts = value.split('.')
        if len(parts) == 4 and all(x.isdigit() for x in parts):
            numbers = list(int(x) for x in parts)
            return all(num >= 0 and num < 256 for num in numbers)
        return False

    def check_ipv6(self, value):
        parts = value.split(':')
        if len(parts) > 8:
            return False

        num_blank = 0
        for part in parts:
            if not part:
                num_blank += 1
            else:
                try:
                    value = int(part, 16)
                except ValueError:
                    return False
                else:
                    if value < 0 or value >= 65536:
                        return False

        if num_blank < 2:
            return True
        elif num_blank == 2 and not parts[0] and not parts[1]:
            return True
        return False


class MacAddress(Regexp):
    """
    Validates a MAC address.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        pattern = r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
        super(MacAddress, self).__init__(pattern, message=message)

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext('Invalid Mac address.')

        super(MacAddress, self).__call__(form, field, message)


class URL(Regexp):
    """
    Simple regexp based url validation. Much like the email validator, you
    probably want to validate the url later by other means if the url must
    resolve.

    :param require_tld:
        If true, then the domain-name portion of the URL must contain a .tld
        suffix.  Set this to false if you want to allow domains like
        `localhost`.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, require_tld=True, message=None):
        tld_part = (require_tld and r'\.[a-z]{2,10}' or '')
        regex = r'^[a-z]+://([^/:]+%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % tld_part
        super(URL, self).__init__(regex, re.IGNORECASE, message)

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext('Invalid URL.')

        super(URL, self).__call__(form, field, message)


class UUID(Regexp):
    """
    Validates a UUID.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        pattern = r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$'
        super(UUID, self).__init__(pattern, message=message)

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext('Invalid UUID.')

        super(UUID, self).__call__(form, field, message)


class AnyOf(object):
    """
    Compares the incoming data to a sequence of valid inputs.

    :param values:
        A sequence of valid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """
    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = self.default_values_formatter
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        if field.data not in self.values:
            message = self.message
            if message is None:
                message = field.gettext('Invalid value, must be one of: %(values)s.')

            raise ValidationError(message % dict(values=self.values_formatter(self.values)))

    @staticmethod
    def default_values_formatter(values):
        return ', '.join(text_type(x) for x in values)


class NoneOf(object):
    """
    Compares the incoming data to a sequence of invalid inputs.

    :param values:
        A sequence of invalid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """
    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = lambda v: ', '.join(text_type(x) for x in v)
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        if field.data in self.values:
            message = self.message
            if message is None:
                message = field.gettext('Invalid value, can\'t be any of: %(values)s.')

            raise ValidationError(message % dict(values=self.values_formatter(self.values)))


email = Email
equal_to = EqualTo
ip_address = IPAddress
mac_address = MacAddress
length = Length
number_range = NumberRange
optional = Optional
required = Required
input_required = InputRequired
data_required = DataRequired
regexp = Regexp
url = URL
any_of = AnyOf
none_of = NoneOf

########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

try:
    from html import escape
except ImportError:
    from cgi import escape

from wtforms.compat import text_type, iteritems

__all__ = (
    'CheckboxInput', 'FileInput', 'HiddenInput', 'ListWidget', 'PasswordInput',
    'RadioInput', 'Select', 'SubmitInput', 'TableWidget', 'TextArea',
    'TextInput', 'Option'
)


def html_params(**kwargs):
    """
    Generate HTML attribute syntax from inputted keyword arguments.

    The output value is sorted by the passed keys, to provide consistent output
    each time this function is called with the same parameters. Because of the
    frequent use of the normally reserved keywords `class` and `for`, suffixing
    these with an underscore will allow them to be used.

    In addition, the values ``True`` and ``False`` are special:
      * ``attr=True`` generates the HTML compact output of a boolean attribute,
        e.g. ``checked=True`` will generate simply ``checked``
      * ``attr=`False`` will be ignored and generate no output.

    >>> html_params(name='text1', id='f', class_='text')
    'class="text" id="f" name="text1"'
    >>> html_params(checked=True, readonly=False, name="text1", abc="hello")
    'abc="hello" checked name="text1"'
    """
    params = []
    for k, v in sorted(iteritems(kwargs)):
        if k in ('class_', 'class__', 'for_'):
            k = k[:-1]
        elif k.startswith('data_'):
            k = k.replace('_', '-', 1)
        if v is True:
            params.append(k)
        elif v is False:
            pass
        else:
            params.append('%s="%s"' % (text_type(k), escape(text_type(v), quote=True)))
    return ' '.join(params)


class HTMLString(text_type):
    """
    This is an "HTML safe string" class that is returned by WTForms widgets.

    For the most part, HTMLString acts like a normal unicode string, except
    in that it has a `__html__` method. This method is invoked by a compatible
    auto-escaping HTML framework to get the HTML-safe version of a string.

    Usage::

        HTMLString('<input type="text" value="hello">')

    """
    def __html__(self):
        """
        Give an HTML-safe string.

        This method actually returns itself, because it's assumed that
        whatever you give to HTMLString is a string with any unsafe values
        already escaped. This lets auto-escaping template frameworks
        know that this string is safe for HTML rendering.
        """
        return self


class ListWidget(object):
    """
    Renders a list of fields as a `ul` or `ol` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """
    def __init__(self, html_tag='ul', prefix_label=True):
        assert html_tag in ('ol', 'ul')
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = ['<%s %s>' % (self.html_tag, html_params(**kwargs))]
        for subfield in field:
            if self.prefix_label:
                html.append('<li>%s %s</li>' % (subfield.label, subfield()))
            else:
                html.append('<li>%s %s</li>' % (subfield(), subfield.label))
        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class TableWidget(object):
    """
    Renders a list of fields as a set of table rows with th/td pairs.

    If `with_table_tag` is True, then an enclosing <table> is placed around the
    rows.

    Hidden fields will not be displayed with a row, instead the field will be
    pushed into a subsequent table row to ensure XHTML validity. Hidden fields
    at the end of the field list will appear outside the table.
    """
    def __init__(self, with_table_tag=True):
        self.with_table_tag = with_table_tag

    def __call__(self, field, **kwargs):
        html = []
        if self.with_table_tag:
            kwargs.setdefault('id', field.id)
            html.append('<table %s>' % html_params(**kwargs))
        hidden = ''
        for subfield in field:
            if subfield.type == 'HiddenField':
                hidden += text_type(subfield)
            else:
                html.append('<tr><th>%s</th><td>%s%s</td></tr>' % (text_type(subfield.label), hidden, text_type(subfield)))
                hidden = ''
        if self.with_table_tag:
            html.append('</table>')
        if hidden:
            html.append(hidden)
        return HTMLString(''.join(html))


class Input(object):
    """
    Render a basic ``<input>`` field.

    This is used as the basis for most of the other input fields.

    By default, the `_value()` method will be called upon the associated field
    to provide the ``value=`` HTML attribute.
    """
    html_params = staticmethod(html_params)

    def __init__(self, input_type=None):
        if input_type is not None:
            self.input_type = input_type

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.input_type)
        if 'value' not in kwargs:
            kwargs['value'] = field._value()
        return HTMLString('<input %s>' % self.html_params(name=field.name, **kwargs))


class TextInput(Input):
    """
    Render a single-line text input.
    """
    input_type = 'text'


class PasswordInput(Input):
    """
    Render a password input.

    For security purposes, this field will not reproduce the value on a form
    submit by default. To have the value filled in, set `hide_value` to
    `False`.
    """
    input_type = 'password'

    def __init__(self, hide_value=True):
        self.hide_value = hide_value

    def __call__(self, field, **kwargs):
        if self.hide_value:
            kwargs['value'] = ''
        return super(PasswordInput, self).__call__(field, **kwargs)


class HiddenInput(Input):
    """
    Render a hidden input.
    """
    input_type = 'hidden'


class CheckboxInput(Input):
    """
    Render a checkbox.

    The ``checked`` HTML attribute is set if the field's data is a non-false value.
    """
    input_type = 'checkbox'

    def __call__(self, field, **kwargs):
        if getattr(field, 'checked', field.data):
            kwargs['checked'] = True
        return super(CheckboxInput, self).__call__(field, **kwargs)


class RadioInput(Input):
    """
    Render a single radio button.

    This widget is most commonly used in conjunction with ListWidget or some
    other listing, as singular radio buttons are not very useful.
    """
    input_type = 'radio'

    def __call__(self, field, **kwargs):
        if field.checked:
            kwargs['checked'] = True
        return super(RadioInput, self).__call__(field, **kwargs)


class FileInput(object):
    """
    Renders a file input chooser field.
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        return HTMLString('<input %s>' % html_params(name=field.name, type='file', **kwargs))


class SubmitInput(Input):
    """
    Renders a submit button.

    The field's label is used as the text of the submit button instead of the
    data on the field.
    """
    input_type = 'submit'

    def __call__(self, field, **kwargs):
        kwargs.setdefault('value', field.label.text)
        return super(SubmitInput, self).__call__(field, **kwargs)


class TextArea(object):
    """
    Renders a multi-line text area.

    `rows` and `cols` ought to be passed as keyword args when rendering.
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        return HTMLString('<textarea %s>%s</textarea>' % (
            html_params(name=field.name, **kwargs),
            escape(text_type(field._value()), quote=False)
        ))


class Select(object):
    """
    Renders a select field.

    If `multiple` is True, then the `size` property should be specified on
    rendering to make the field useful.

    The field must provide an `iter_choices()` method which the widget will
    call on rendering; this method must yield tuples of
    `(value, label, selected)`.
    """
    def __init__(self, multiple=False):
        self.multiple = multiple

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        if self.multiple:
            kwargs['multiple'] = True
        html = ['<select %s>' % html_params(name=field.name, **kwargs)]
        for val, label, selected in field.iter_choices():
            html.append(self.render_option(val, label, selected))
        html.append('</select>')
        return HTMLString(''.join(html))

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        if value is True:
            # Handle the special case of a 'True' value.
            value = text_type(value)

        options = dict(kwargs, value=value)
        if selected:
            options['selected'] = True
        return HTMLString('<option %s>%s</option>' % (html_params(**options), escape(text_type(label), quote=False)))


class Option(object):
    """
    Renders the individual option from a select field.

    This is just a convenience for various custom rendering situations, and an
    option by itself does not constitute an entire field.
    """
    def __call__(self, field, **kwargs):
        return Select.render_option(field._value(), field.label.text, field.checked, **kwargs)

########NEW FILE########
__FILENAME__ = html5
"""
Widgets for various HTML5 input types.
"""

from .core import Input

__all__ = (
    'ColorInput', 'DateInput', 'DateTimeInput', 'DateTimeLocalInput',
    'EmailInput', 'MonthInput', 'NumberInput', 'RangeInput', 'SearchInput',
    'TelInput', 'TimeInput', 'URLInput', 'WeekInput',
)


class SearchInput(Input):
    """
    Renders an input with type "search".
    """
    input_type = 'search'


class TelInput(Input):
    """
    Renders an input with type "tel".
    """
    input_type = 'tel'


class URLInput(Input):
    """
    Renders an input with type "url".
    """
    input_type = 'url'


class EmailInput(Input):
    """
    Renders an input with type "email".
    """
    input_type = 'email'


class DateTimeInput(Input):
    """
    Renders an input with type "datetime".
    """
    input_type = 'datetime'


class DateInput(Input):
    """
    Renders an input with type "date".
    """
    input_type = 'date'


class MonthInput(Input):
    """
    Renders an input with type "month".
    """
    input_type = 'month'


class WeekInput(Input):
    """
    Renders an input with type "week".
    """
    input_type = 'week'


class TimeInput(Input):
    """
    Renders an input with type "time".
    """
    input_type = 'time'


class DateTimeLocalInput(Input):
    """
    Renders an input with type "datetime-local".
    """
    input_type = 'datetime-local'


class NumberInput(Input):
    """
    Renders an input with type "number".
    """
    input_type = 'number'

    def __init__(self, step=None):
        self.step = step

    def __call__(self, field, **kwargs):
        if self.step is not None:
            kwargs.setdefault('step', self.step)
        return super(NumberInput, self).__call__(field, **kwargs)


class RangeInput(Input):
    """
    Renders an input with type "range".
    """
    input_type = 'range'

    def __init__(self, step=None):
        self.step = step

    def __call__(self, field, **kwargs):
        if self.step is not None:
            kwargs.setdefault('step', self.step)
        return super(RangeInput, self).__call__(field, **kwargs)


class ColorInput(Input):
    """
    Renders an input with type "color".
    """
    input_type = 'color'

########NEW FILE########
