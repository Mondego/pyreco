__FILENAME__ = errors
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The `errors` module contains all exceptions used by Booby."""


class BoobyError(Exception):
    """Base class for all Booby exceptions."""

    pass


class FieldError(BoobyError):
    """This exception is used as an equivalent to :class:`AttributeError`
    for :mod:`fields`.

    """

    pass


class ValidationError(BoobyError):
    """This exception should be raised when a `value` doesn't validate.
    See :mod:`validators`.

    """

    pass

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The `fields` module contains a list of `Field` classes
for model's definition.

The example below shows the most common fields and builtin validations::

    class Token(Model):
        key = String()
        secret = String()

    class User(Model):
        login = String(required=True)
        name = String()
        role = String(choices=['admin', 'moderator', 'user'])
        email = Email(required=True)
        token = Embedded(Token, required=True)
        is_active = Boolean(default=False)
"""

import collections

from booby import validators as builtin_validators, _utils


class Field(object):
    """This is the base class for all :mod:`booby.fields`. This class
    can also be used as field in any :class:`models.Model` declaration.

    :param default: This field `default`'s value.

        If passed a callable object then uses its return value as the
        field's default. This is particularly useful when working with
        `mutable objects <http://effbot.org/zone/default-values.htm>`_.

        If `default` is a callable it can optionaly receive the owner
        `model` instance as its first positional argument.

    :param required: If `True` this field value should not be `None`.
    :param choices: A `list` of values where this field value should be in.
    :param \*validators: A list of field :mod:`validators` as positional arguments.

    """

    def __init__(self, *validators, **kwargs):
        self.options = kwargs

        self.default = kwargs.get('default')

        # Setup field validators
        self.validators = []

        if kwargs.get('required'):
            self.validators.append(builtin_validators.Required())

        choices = kwargs.get('choices')

        if choices:
            self.validators.append(builtin_validators.In(choices))

        self.validators.extend(validators)

    def __repr__(self):
        options = dict(self.options)
        options['validators'] = self.validators

        cls = type(self)

        return '<{}.{}({})>'.format(cls.__module__, cls.__name__,
                                    _utils.repr_options(options))

    def __get__(self, instance, owner):
        if instance is not None:
            try:
                return instance._data[self]
            except KeyError:
                return instance._data.setdefault(self, self._default(instance))

        return self

    def __set__(self, instance, value):
        instance._data[self] = value

    def _default(self, model):
        if callable(self.default):
            return self.__call_default(model)

        return self.default

    def __call_default(self, *args):
        try:
            return self.default()
        except TypeError as error:
            try:
                return self.default(*args)
            except TypeError:
                raise error

    def validate(self, value):
        for validator in self.validators:
            validator(value)


class String(Field):
    """:class:`Field` subclass with builtin `string` validation."""

    def __init__(self, *args, **kwargs):
        super(String, self).__init__(builtin_validators.String(), *args, **kwargs)


class Integer(Field):
    """:class:`Field` subclass with builtin `integer` validation."""

    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__(builtin_validators.Integer(), *args, **kwargs)


class Float(Field):
    """:class:`Field` subclass with builtin `float` validation."""

    def __init__(self, *args, **kwargs):
        super(Float, self).__init__(builtin_validators.Float(), *args, **kwargs)


class Boolean(Field):
    """:class:`Field` subclass with builtin `bool` validation."""

    def __init__(self, *args, **kwargs):
        super(Boolean, self).__init__(builtin_validators.Boolean(), *args, **kwargs)


class Embedded(Field):
    """:class:`Field` subclass with builtin embedded :class:`models.Model`
    validation.

    """

    def __init__(self, model, *args, **kwargs):
        super(Embedded, self).__init__(builtin_validators.Model(model), *args, **kwargs)

        self.model = model

    def __set__(self, instance, value):
        if isinstance(value, collections.MutableMapping):
            value = self.model(**value)

        super(Embedded, self).__set__(instance, value)


class Email(Field):
    """:class:`Field` subclass with builtin `email` validation."""

    def __init__(self, *args, **kwargs):
        super(Email, self).__init__(builtin_validators.Email(), *args, **kwargs)

########NEW FILE########
__FILENAME__ = inspection
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The :mod:`inspection` module provides users and 3rd-party library
developers a public api to access :mod:`booby` objects and classes internal
data, such as defined fields, and some low-level type validations.

This module is based on the Python :py:mod:`inspect` module.

"""

from booby import models


def get_fields(model):
    """Returns a `dict` mapping the given `model` field names to their
    `fields.Field` objects.

    :param model: The `models.Model` subclass or instance you want to
                  get their fields.

    :raises: :py:exc:`TypeError` if the given `model` is not a model.

    """

    if not is_model(model):
        raise TypeError(
            '{} is not a {} subclass or instance'.format(model, models.Model))

    return dict(model._fields)


def is_model(obj):
    """Returns `True` if the given object is a `models.Model` instance
    or subclass. If not then returns `False`.

    """

    try:
        return (isinstance(obj, models.Model) or
                issubclass(obj, models.Model))

    except TypeError:
        return False

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The `models` module contains the `booby` highest level abstraction:
the `Model`.

To define a model you should subclass the :class:`Model` class and
add a list of :mod:`fields` as attributes. And then you could instantiate
your `Model` and work with these objects.

Something like this::

    class Repo(Model):
         name = fields.String()
         owner = fields.Embedded(User)

    booby = Repo(
        name='Booby',
        owner={
            'login': 'jaimegildesagredo',
            'name': 'Jaime Gil de Sagredo'
        })

    print booby.to_json()
    '{"owner": {"login": "jaimegildesagredo", "name": "Jaime Gil de Sagredo"}, "name": "Booby"}'
"""

import json
import collections

from booby import fields, errors, _utils


class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs['_fields'] = {}

        for base in bases:
            for k, v in base.__dict__.items():
                if isinstance(v, fields.Field):
                    attrs['_fields'][k] = v

        for k, v in attrs.items():
            if isinstance(v, fields.Field):
                attrs['_fields'][k] = v

        return super(ModelMeta, cls).__new__(cls, name, bases, attrs)

    def __repr__(cls):
        return '<{}.{}({})>'.format(cls.__module__, cls.__name__,
                                    _utils.repr_options(cls._fields))


class Model(object):
    """The `Model` class. All Booby models should subclass this.

    By default the `Model's` :func:`__init__` takes a list of keyword arguments
    to initialize the `fields` values. If any of these keys is not a `field`
    then raises :class:`errors.FieldError`. Of course you can overwrite the
    `Model's` :func:`__init__` to get a custom behavior.

    You can get or set Model `fields` values in two different ways: through
    object attributes or dict-like items::

        >>> booby.name is booby['name']
        True
        >>> booby['name'] = 'booby'
        >>> booby['foo'] = 'bar'
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        errors.FieldError: foo

    :param \*\*kwargs: Keyword arguments with the fields values to initialize the model.

    """

    __metaclass__ = ModelMeta

    def __new__(cls, *args, **kwargs):
        model = super(Model, cls).__new__(cls)
        model._data = {}

        return model

    def __init__(self, **kwargs):
        self._update(kwargs)

    def __repr__(self):
        cls = type(self)

        return '<{}.{}({})>'.format(cls.__module__, cls.__name__,
                                    _utils.repr_options(dict(self)))

    def __iter__(self):
        for name in self._fields:
            value = getattr(self, name)

            if isinstance(value, Model):
                value = dict(value)
            elif isinstance(value, collections.MutableSequence):
                value = self._encode_sequence(value)

            yield name, value

    def _encode_sequence(self, sequence):
        result = []

        for value in sequence:
            if isinstance(value, Model):
                value = dict(value)

            result.append(value)

        return result

    def __getitem__(self, k):
        if k not in self._fields:
            raise errors.FieldError(k)

        return getattr(self, k)

    def __setitem__(self, k, v):
        if k not in self._fields:
            raise errors.FieldError(k)

        setattr(self, k, v)

    def update(self, *args, **kwargs):
        """This method updates the `model` fields values with the given `dict`.
        The model can be updated passing a dict object or keyword arguments,
        like the Python's builtin :py:func:`dict.update`.

        """

        self._update(dict(*args, **kwargs))

    def _update(self, values):
        for k, v in values.items():
            self[k] = v

    @property
    def is_valid(self):
        """This property will be `True` if there are not validation
        errors in this `model` fields. If there are any error then
        will be `False`.

        This property wraps the :func:`Model.validate` method to be
        used in a boolean context.

        """

        try:
            self.validate()
        except errors.ValidationError:
            return False
        else:
            return True

    def validate(self):
        """This method validates the entire `model`. That is, validates
        all the :mod:`fields` within this model.

        If some `field` validation fails, then this method raises the same
        exception that the :func:`field.validate` method had raised.

        """

        for name, field in self._fields.items():
            field.validate(getattr(self, name))

    @property
    def validation_errors(self):
        """Generator of field name and validation error string pairs
        for each validation error on this `model` fields.

        """

        for name, field in self._fields.items():
            try:
                field.validate(getattr(self, name))
            except errors.ValidationError as err:
                yield name, str(err)

    def to_json(self, *args, **kwargs):
        """This method returns the `model` as a `json string`. It receives
        the same arguments as the builtin :py:func:`json.dump` function.

        To build a json representation of this `model` this method iterates
        over the object to build a `dict` and then serializes it as json.

        """

        return json.dumps(dict(self), *args, **kwargs)

########NEW FILE########
__FILENAME__ = validators
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The `validators` module contains a set of :mod:`fields` validators.

A validator is any callable `object` which receives a `value` as the
target for the validation. If the validation fails then should raise an
:class:`errors.ValidationError` exception with an error message.

`Validators` are passed to :class:`fields.Field` and subclasses as possitional
arguments.

"""

import re
import functools
import collections

from booby import errors


def nullable(method):
    """This is a helper validation decorator for validators that allow
    their `values` to be :keyword:`None`.

    The :class:`String` validator is a good example::

        class String(object):
            def validate(self, value):
                if value is not None:
                    pass # Do the validation here ...

    Now the same but using the `@nullable` decorator::

        @nullable
        def validate(self, value):
            pass # Do the validation here ...

    """

    @functools.wraps(method)
    def wrapper(self, value):
        if value is not None:
            method(self, value)

    return wrapper


class Validator(object):
    def __call__(self, value):
        self.validate(value)

    def validate(self, value):
        raise NotImplementedError()


class Required(Validator):
    """This validator forces fields to have a value other than :keyword:`None`."""

    def validate(self, value):
        if value is None:
            raise errors.ValidationError('is required')


class In(Validator):
    """This validator forces fields to have their value in the given list.

    :param choices: A `list` of possible values.

    """

    def __init__(self, choices):
        self.choices = choices

    def validate(self, value):
        if value not in self.choices:
            raise errors.ValidationError('should be in {}'.format(self.choices))


class String(Validator):
    """This validator forces fields values to be an instance of `basestring`."""

    @nullable
    def validate(self, value):
        if not isinstance(value, basestring):
            raise errors.ValidationError('should be a string')


class Integer(Validator):
    """This validator forces fields values to be an instance of `int`."""

    @nullable
    def validate(self, value):
        if not isinstance(value, int):
            raise errors.ValidationError('should be an integer')


class Float(Validator):
    """This validator forces fields values to be an instance of `float`."""

    @nullable
    def validate(self, value):
        if not isinstance(value, float):
            raise errors.ValidationError('should be a float')


class Boolean(Validator):
    """This validator forces fields values to be an instance of `bool`."""

    @nullable
    def validate(self, value):
        if not isinstance(value, bool):
            raise errors.ValidationError('should be a boolean')


class Model(Validator):
    """This validator forces fields values to be an instance of the given
    :class:`models.Model` subclass and also performs a validation in the
    entire `model` object.

    :param model: A subclass of :class:`models.Model`

    """

    def __init__(self, model):
        self.model = model

    @nullable
    def validate(self, value):
        if not isinstance(value, self.model):
            raise errors.ValidationError(
                "should be an instance of '{}'".format(self.model.__name__))

        value.validate()


class Email(String):
    """This validator forces fields values to be strings and match a
    valid email address.

    """

    def __init__(self):
        super(Email, self).__init__()

        self.pattern = re.compile('^[^@]+\@[^@]+$')

    @nullable
    def validate(self, value):
        super(Email, self).validate(value)

        if self.pattern.match(value) is None:
            raise errors.ValidationError('should be a valid email')


class List(Validator):
    """This validator forces field values to be a :keyword:`list`.
    Also a list of inner :mod:`validators` could be specified to validate
    each list element. For example, to validate a list of
    :class:`models.Model` you could do::

        books = fields.Field(validators.List(validators.Model(YourBookModel)))

    :param \*validators: A list of inner validators as possitional arguments.

    """

    def __init__(self, *validators):
        self.validators = validators

    def validate(self, value):
        if not isinstance(value, collections.MutableSequence):
            raise errors.ValidationError('should be a list')

        for i in value:
            for validator in self.validators:
                validator(i)

########NEW FILE########
__FILENAME__ = _utils
# -*- coding: utf-8 -*-
#
# Copyright 2014 Jaime Gil de Sagredo Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def repr_options(options):
    return ', '.join('{}={!r}'.format(k, v) for k, v in options.items())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Booby documentation build configuration file, created by
# sphinx-quickstart on Fri Dec 28 14:02:27 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

import booby

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.dirname(booby.__file__))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Booby'
copyright = u'2014, Jaime Gil de Sagredo'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5.2'

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
htmlhelp_basename = 'Boobydoc'


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
  ('index', 'Booby.tex', u'Booby Documentation',
   u'Jaime Gil de Sagredo', 'manual'),
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
    ('index', 'booby', u'Booby Documentation',
     [u'Jaime Gil de Sagredo'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Booby', u'Booby Documentation',
   u'Jaime Gil de Sagredo', 'Booby', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# -- Options for Intersphinx plugin --------------------------------------------
intersphinx_mapping = {'python': ('http://docs.python.org/3.3', None)}

########NEW FILE########
__FILENAME__ = test_model_declaration
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from nose.tools import assert_raises_regexp

from booby import Model, fields, errors


class TestModelValidation(object):
    def test_when_login_is_none_then_raises_validation_error(self):
        user = User()

        with assert_raises_regexp(errors.ValidationError, 'required'):
            user.validate()

    def test_when_karma_is_not_an_integer_then_raises_validation_error(self):
        user = User(login='root', karma='max')

        with assert_raises_regexp(errors.ValidationError, 'should be an integer'):
            user.validate()

    def test_when_token_key_is_not_a_string_then_raises_validation_error(self):
        user = User(login='root', token=Token(key=1))

        with assert_raises_regexp(errors.ValidationError, 'should be a string'):
            user.validate()

    def test_when_email_is_an_invalid_email_then_raises_validation_error(self):
        user = User(login='root', email='@localhost')

        with assert_raises_regexp(errors.ValidationError, 'should be a valid email'):
            user.validate()


class Token(Model):
    key = fields.String()
    secret = fields.String()


class User(Model):
    login = fields.String(required=True)
    email = fields.Email()
    name = fields.String()
    karma = fields.Integer()
    token = fields.Embedded(Token)

########NEW FILE########
__FILENAME__ = test_fields
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import collections

from expects import expect
from ._helpers import Spy, stub_validator

from booby import fields, errors, models


class TestFieldInit(object):
    def test_when_kwargs_then_field_options_is_a_dict_with_these_args(self):
        kwargs = dict(required=True, primary=True, foo='bar')

        field = fields.Field(**kwargs)

        expect(field.options).to.equal(kwargs)

    def test_when_no_kwargs_then_field_options_is_an_empty_dict(self):
        field = fields.Field()

        expect(field.options).to.equal({})


class TestFieldDefault(object):
    def test_when_access_obj_field_and_value_is_not_assigned_yet_then_is_default(self):
        user = User()

        expect(user.name).to.equal('nobody')

    def test_when_default_is_callable_then_use_its_returned_value_as_field_default(self):
        default = 'anonymous'
        User.name.default = lambda: default

        user = User()

        expect(user.name).to.be(default)

    def test_when_callable_receives_argument_then_pass_owner_instance(self):
        User.name.default = lambda model: model == user

        user = User()

        expect(user.name).to.be.true

    def test_when_callable_raises_type_error_then_should_not_be_catched(self):
        def callback():
            raise TypeError('foo')

        User.name.default = callback

        expect(lambda: User().name).to.raise_error(TypeError, 'foo')

    def test_when_default_is_callable_then_should_be_called_once_per_onwer_instance(self):
        default_callable = Spy()

        User.name.default = default_callable

        user = User()
        user.name
        user.name

        expect(default_callable.times_called).to.equal(1)

    def test_when_default_is_callable_then_should_be_called_on_each_owner_instance(self):
        default_callable = Spy()
        User.name.default = default_callable

        User().name
        User().name

        expect(default_callable.times_called).to.equal(2)


class TestFieldValues(object):
    def test_when_access_obj_field_and_value_is_already_assigned_then_is_value(self):
        user = User()
        user.name = 'Jack'

        expect(user.name).to.equal('Jack')

    def test_when_access_class_field_then_is_field_object(self):
        expect(User.name).to.be.a(fields.Field)


class TestEmbeddedFieldDescriptor(object):
    def test_when_set_field_value_with_dict_then_value_is_embedded_object_with_dict_values(self):
        self.group.admin = {'name': 'foo', 'email': 'foo@example.com'}

        expect(self.group.admin).to.be.an(User)
        expect(self.group.admin).to.have.properties(
            name='foo', email='foo@example.com')

    def test_when_set_field_value_with_dict_with_invalid_field_then_raises_field_error(self):
        def callback():
            self.group.admin = {'name': 'foo', 'foo': 'bar'}

        expect(callback).to.raise_error(errors.FieldError, 'foo')

    def test_when_set_field_value_with_mutable_mapping_then_value_is_model_instance_with_dict_values(self):
        self.group.admin = MyDict(name='foo', email='foo@example.com')

        expect(self.group.admin).to.be.an(User)
        expect(self.group.admin).to.have.properties(
            name='foo', email='foo@example.com')

    def test_when_set_field_value_with_not_dict_object_then_value_is_given_object(self):
        user = User(name='foo', email='foo@example.com')
        self.group.admin = user

        expect(self.group.admin).to.be(user)

    def test_when_set_field_with_not_model_instance_then_value_is_given_object(self):
        user = object()
        self.group.admin = user

        expect(self.group.admin).to.be(user)

    def setup(self):
        self.group = Group()


class User(models.Model):
    name = fields.String(default='nobody')
    email = fields.String()


class Group(models.Model):
    name = fields.String()
    admin = fields.Embedded(User)


class TestValidateField(object):
    def test_when_validate_without_validation_errors_then_does_not_raise(self):
        field = fields.Field(stub_validator, stub_validator)

        field.validate('foo')

    def test_when_first_validator_raises_validation_error_then_raises_exception(self):
        def validator1(value):
            if value == 'foo':
                raise errors.ValidationError()

        field = fields.Field(validator1, stub_validator)

        expect(lambda: field.validate('foo')).to.raise_error(
            errors.ValidationError)

    def test_when_second_validator_raises_validation_error_then_raises_exception(self):
        def validator2(value):
            if value == 'foo':
                raise errors.ValidationError()

        field = fields.Field(stub_validator, validator2)

        expect(lambda: field.validate('foo')).to.raise_error(
            errors.ValidationError)


class TestFieldBuiltinValidations(object):
    def test_when_required_is_true_then_value_shouldnt_be_none(self):
        field = fields.Field(required=True)

        expect(lambda: field.validate(None)).to.raise_error(
            errors.ValidationError, 'required')

    def test_when_required_is_false_then_value_can_be_none(self):
        field = fields.Field(required=False)

        field.validate(None)

    def test_when_not_required_then_value_can_be_none(self):
        field = fields.Field()

        field.validate(None)

    def test_when_choices_then_value_should_be_in_choices(self):
        field = fields.Field(choices=['foo', 'bar'])

        expect(lambda: field.validate('baz')).to.raise_error(
            errors.ValidationError, ' in ')

    def test_when_not_choices_then_value_can_be_whatever_value(self):
        field = fields.Field()

        field.validate('foo')


class TestEmbeddedFieldBuildtinValidators(object):
    def test_when_value_is_not_instance_of_model_then_raises_validation_error(self):
        expect(lambda: self.field.validate(object())).to.raise_error(
            errors.ValidationError, 'instance of')

    def test_when_embedded_model_field_has_invalid_value_then_raises_validation_error(self):
        expect(lambda: self.field.validate(User(name=1))).to.raise_error(
            errors.ValidationError, 'string')

    def test_when_embedded_model_validates_then_does_not_raise(self):
        self.field.validate(User())

    def setup(self):
        self.field = fields.Embedded(User)


class MyDict(collections.MutableMapping):
    def __init__(self, **kwargs):
        self._store = kwargs

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        pass

    def __delitem__(self, key):
        pass

    def __len__(self):
        pass

    def __iter__(self):
        return iter(self._store)

########NEW FILE########
__FILENAME__ = test_inspection
# -*- coding: utf-8 -*-

from expects import expect

from booby import models, fields
from booby.inspection import get_fields, is_model


class TestGetFields(object):
    def test_should_return_model_instance_fields_dict(self):
        result = get_fields(User())

        expect(result).to.have.keys(name=User.name, email=User.email)

    def test_should_return_model_class_fields_dict(self):
        result = get_fields(User)

        expect(result).to.have.keys(name=User.name, email=User.email)

    def test_should_return_a_copy_of_internal_fields_dict(self):
        result = get_fields(User)

        expect(result).not_to.be(get_fields(User))

    def test_non_model_object_should_raise_type_error(self):
        expect(lambda: get_fields(object)).to.raise_error(TypeError)


class TestIsModel(object):
    def test_should_return_true_if_object_is_a_model_instance(self):
        expect(is_model(User())).to.be.true

    def test_should_return_true_if_object_is_a_model_subclass(self):
        expect(is_model(User)).to.be.true

    def test_should_return_false_if_object_isnt_a_model_subclass(self):
        expect(is_model(object)).to.be.false

    def test_should_return_false_if_object_isnt_a_model_instance(self):
        expect(is_model(object())).to.be.false


class User(models.Model):
    name = fields.String()
    email = fields.String()

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json

from expects import expect
from ._helpers import MyList

from booby import errors, fields, models


class TestDefaultModelInit(object):
    def test_when_pass_kwargs_then_set_fields_values(self):
        user = User(name='foo', email='foo@example.com')

        expect(user.name).to.equal('foo')
        expect(user.email).to.equal('foo@example.com')

    def test_when_pass_kwargs_without_required_field_then_required_field_is_none(self):
        user = UserWithRequiredName(email='foo@example.com')

        expect(user.name).to.equal(None)

    def test_when_pass_invalid_field_in_kwargs_then_raises_field_error(self):
        expect(lambda: User(foo='bar')).to.raise_error(
            errors.FieldError, 'foo')


class TestOverridenModelInit(object):
    def test_when_pass_args_then_set_fields_values(self):
        class UserWithOverridenInit(User):
            def __init__(self, name, email):
                self.name = name
                self.email = email

        user = UserWithOverridenInit('foo', 'foo@example.com')

        expect(user.name).to.equal('foo')
        expect(user.email).to.equal('foo@example.com')


class TestModelData(object):
    def test_when_set_field_value_then_another_model_shouldnt_have_the_same_value(self):
        user = User(name='foo')
        another = User(name='bar')

        expect(user.name).not_to.equal(another.name)


class TestValidateModel(object):
    def test_when_validate_and_validation_errors_then_raises_first_validation_error(self):
        user = UserWithRequiredName(email='foo@example.com')

        expect(lambda: user.validate()).to.raise_error(
            errors.ValidationError, 'required')

    def test_when_validate_without_errors_then_does_not_raise(self):
        user = UserWithRequiredName(name='Jack')

        user.validate()

    def test_when_is_valid_and_validation_errors_then_is_false(self):
        user = UserWithRequiredName(email='foo@example.com')

        expect(user.is_valid).to.be.false

    def test_when_is_valid_and_not_validation_errors_then_is_true(self):
        user = UserWithRequiredName(name='Jack')

        expect(user.is_valid).to.be.true

    def test_when_validation_errors_and_errors_then_has_pairs_of_name_and_errors(self):
        user = UserWithRequiredFields(id=1, role='root')

        errors = dict(user.validation_errors)

        expect(errors['id']).to.have('be a string')
        expect(errors['role']).to.have('be in')
        expect(errors['name']).to.have('required')

    def test_when_validation_errors_and_no_errors_then_returns_none(self):
        user = UserWithRequiredName(name='jack')

        errors = user.validation_errors

        expect(errors).to.be.empty


class TestInheritedModel(object):
    def test_when_pass_kwargs_then_set_fields_values(self):
        user = UserWithPage(name='foo', email='foo@example.com', page='example.com')

        expect(user.name).to.equal('foo')
        expect(user.email).to.equal('foo@example.com')
        expect(user.page).to.equal('example.com')

    def test_when_pass_invalid_field_in_kwargs_then_raises_field_error(self):
        expect(lambda: UserWithPage(foo='bar')).to.raise_error(
            errors.FieldError, 'foo')

    def test_when_override_superclass_field_then_validates_subclass_field(self):
        class UserWithoutRequiredName(UserWithRequiredName):
            name = fields.String()

        user = UserWithoutRequiredName()
        user.validate()


class TestInheritedMixin(object):
    def test_when_pass_kwargs_then_set_fields_values(self):
        user = UserWithEmail(name='foo', email='foo@example.com')

        expect(user).to.have.properties(name='foo', email='foo@example.com')

    def test_when_pass_invalid_field_in_kwargs_then_raises_field_error(self):
        expect(lambda: UserWithEmail(foo='bar')).to.raise_error(
            errors.FieldError, 'foo')

    def test_when_override_mixin_field_then_validates_subclass_field(self):
        class User(UserMixin, models.Model):
            name = fields.String(required=True)

        user = User()

        expect(lambda: user.validate()).to.raise_error(
            errors.ValidationError, 'required')


class TestDictModel(object):
    def test_when_get_field_then_returns_value(self):
        expect(self.user['name']).to.equal('foo')

    def test_when_get_invalid_field_then_raises_field_error(self):
        expect(lambda: self.user['foo']).to.raise_error(
            errors.FieldError, 'foo')

    def test_when_set_field_then_update_field_value(self):
        self.user['name'] = 'bar'

        expect(self.user).to.have.property('name', 'bar')

    def test_when_set_invalid_field_then_raises_field_error(self):
        def callback():
            self.user['foo'] = 'bar'

        expect(callback).to.raise_error(errors.FieldError, 'foo')

    def test_when_update_with_dict_then_update_fields_values(self):
        self.user.update({'name': 'foobar', 'email': 'foo@bar.com'})

        expect(self.user).to.have.properties(name='foobar', email='foo@bar.com')

    def test_when_update_kw_arguments_then_update_fields_values(self):
        self.user.update(name='foobar', email='foo@bar.com')

        expect(self.user).to.have.properties(name='foobar', email='foo@bar.com')

    def test_when_update_invalid_field_then_raises_field_error(self):
        expect(lambda: self.user.update(foo='bar')).to.raise_error(
            errors.FieldError, 'foo')

    def setup(self):
        self.user = User(name='foo', email='roo@example.com')


class TestModelToDict(object):
    def test_when_model_has_single_fields_then_returns_dict_with_fields_values(self):
        user = dict(User(name='foo', email='roo@example.com'))

        expect(user).to.have.keys(name='foo', email='roo@example.com')

    def test_when_model_has_embedded_model_field_then_returns_dict_with_inner_dict(self):
        class UserWithToken(User):
            token = fields.Field()

        user = dict(UserWithToken(name='foo', email='roo@example.com',
                                  token=self.token1))

        expect(user).to.have.keys(name='foo', email='roo@example.com',
                                  token=dict(self.token1))

    def test_when_model_has_list_of_models_then_returns_list_of_dicts(self):
        user = dict(UserWithList(tokens=[self.token1, self.token2]))

        expect(user['tokens']).to.have(dict(self.token1), dict(self.token2))

    def test_when_model_has_list_of_models_and_values_then_returns_list_of_dicts_and_values(self):
        user = dict(UserWithList(tokens=[self.token1, 'foo', self.token2]))

        expect(user['tokens']).to.have(dict(self.token1), 'foo',
                                       dict(self.token2))

    def test_when_model_has_mutable_sequence_of_models_then_returns_list_of_dicts(self):
        user = dict(UserWithList(tokens=MyList(self.token1, self.token2)))

        expect(user['tokens']).to.have(dict(self.token1), dict(self.token2))

    def setup(self):
        self.token1 = Token(key='foo', secret='bar')
        self.token2 = Token(key='fuu', secret='baz')


class TestModelToJSON(object):
    def test_when_model_has_single_fields_then_returns_json_with_fields_values(self):
        result = self.user.to_json()

        expect(result).to.equal(json.dumps(dict(self.user)))

    def test_when_pass_extra_arguments_then_call_json_dump_function_with_these_args(self):
        result = self.user.to_json(indent=2)

        expect(result).to.equal(json.dumps(dict(self.user), indent=2))

    def setup(self):
        self.user = User(name='Jack', email='jack@example.com')


class User(models.Model):
    name = fields.String()
    email = fields.String()


class UserWithRequiredName(User):
    name = fields.String(required=True)


class UserWithRequiredFields(UserWithRequiredName):
    id = fields.String()
    role = fields.String(choices=['admin', 'user'])


class UserWithPage(User):
    page = fields.String()


class UserMixin(object):
    name = fields.String()


class UserWithEmail(UserMixin, models.Model):
    email = fields.String()


class UserWithList(User):
    tokens = fields.Field()


class Token(models.Model):
    key = fields.String()
    secret = fields.String()

########NEW FILE########
__FILENAME__ = mixins
# -*- coding: utf-8 -*-

from expects import expect

from booby import errors


class String(object):
    def test_should_pass_if_value_is_none(self):
        self.validator(None)

    def test_should_fail_if_value_is_not_a_string(self):
        expect(lambda: self.validator(1)).to.raise_error(
            errors.ValidationError, 'should be a string')

########NEW FILE########
__FILENAME__ = test_email
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from expects import expect
from . import mixins

from booby import validators, errors


class TestEmail(mixins.String):
    def test_should_pass_if_value_is_valid_email(self):
        self.validator('foo2bar@example.com')

    def test_should_pass_if_value_contains_plus_sign(self):
        self.validator('foo+bar@example.com')

    def test_should_pass_if_value_contains_minus_sign(self):
        self.validator('foo-bar@example.com')

    def test_should_pass_if_domain_is_tld(self):
        self.validator('foo@example')

    def test_should_fail_if_nothing_before_at_sign(self):
        expect(lambda: self.validator('@example')).to.raise_error(
            errors.ValidationError, 'should be a valid email')

    def test_should_fail_if_value_doesnt_have_at_sign(self):
        expect(lambda: self.validator('foo%example.com')).to.raise_error(
            errors.ValidationError, 'should be a valid email')

    def test_should_fail_if_empty_string(self):
        expect(lambda: self.validator('')).to.raise_error(
            errors.ValidationError, 'should be a valid email')

    def setup(self):
        self.validator = validators.Email()

########NEW FILE########
__FILENAME__ = test_list
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from expects import expect
from .._helpers import MyList, stub_validator

from booby import validators, errors


class TestList(object):
    def test_should_pass_if_value_is_a_list(self):
        self.validator(['foo', 'bar'])

    def test_should_pass_if_value_is_a_mutable_sequence(self):
        self.validator(MyList('foo', 'bar'))

    def test_should_fail_if_value_is_not_a_list(self):
        expect(lambda: self.validator(object())).to.raise_error(
            errors.ValidationError, 'should be a list')

    def test_should_fail_if_value_is_none(self):
        expect(lambda: self.validator(None)).to.raise_error(
            errors.ValidationError, 'should be a list')

    def test_should_fail_if_inner_validator_fails(self):
        def inner_validator(value):
            if value == 'bar':
                raise errors.ValidationError('invalid')

        self.validator = validators.List(stub_validator, inner_validator)

        expect(lambda: self.validator(['foo', 'bar'])).to.raise_error(
            errors.ValidationError, 'invalid')

    def setup(self):
        self.validator = validators.List()

########NEW FILE########
__FILENAME__ = test_validators
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from expects import expect
from . import mixins
from .._helpers import stub_validator

from booby import validators, fields, models, errors


class TestRequired(object):
    def test_when_value_is_none_then_raises_validation_error(self):
        expect(lambda: self.validator(None)).to.raise_error(
            errors.ValidationError, 'is required')

    def test_when_value_is_not_none_then_does_not_raise(self):
        self.validator('foo')

    def setup(self):
        self.validator = validators.Required()


class TestIn(object):
    def test_when_value_is_not_in_choices_then_raises_validation_error(self):
        expect(lambda: self.validator('baz')).to.raise_error(
            errors.ValidationError, "should be in \[u?'foo', u?'bar'\]")

    def test_when_value_is_in_choices_then_does_not_raise(self):
        self.validator('bar')

    def setup(self):
        self.validator = validators.In(['foo', 'bar'])


class TestString(mixins.String):
    def test_when_value_is_a_string_then_does_not_raise(self):
        self.validator('foo')

    def test_when_value_is_unicode_then_does_not_raise(self):
        self.validator('foo')

    def setup(self):
        self.validator = validators.String()


class TestInteger(object):
    def test_when_value_is_not_an_integer_then_raises_validation_error(self):
        expect(lambda: self.validator('foo')).to.raise_error(
            errors.ValidationError, 'should be an integer')

    def test_when_value_is_an_integer_then_does_not_raise(self):
        self.validator(1)

    def test_when_value_is_none_then_does_not_raise(self):
        self.validator(None)

    def setup(self):
        self.validator = validators.Integer()


class TestFloat(object):
    def test_when_value_is_not_a_float_then_raises_validation_error(self):
        expect(lambda: self.validator('foo')).to.raise_error(
            errors.ValidationError, 'should be a float')

    def test_when_value_is_a_float_then_does_not_raise(self):
        self.validator(1.0)

    def test_when_value_is_none_then_does_not_raise(self):
        self.validator(None)

    def setup(self):
        self.validator = validators.Float()


class TestBoolean(object):
    def test_when_value_is_not_a_boolean_then_raises_validation_error(self):
        expect(lambda: self.validator('foo')).to.raise_error(
            errors.ValidationError, 'should be a boolean')

    def test_when_value_is_a_boolean_then_does_not_raises(self):
        self.validator(False)

    def test_when_value_is_none_then_does_not_raise(self):
        self.validator(None)

    def setup(self):
        self.validator = validators.Boolean()


class TestModel(object):
    def test_when_value_is_not_instance_of_model_then_raises_validation_error(self):
        expect(lambda: self.validator(object())).to.raise_error(
            errors.ValidationError, "should be an instance of 'User'")

    def test_when_model_validate_raises_validation_error_then_raises_validation_error(self):
        class InvalidUser(User):
            def validate(self):
                raise errors.ValidationError()

        expect(lambda: self.validator(InvalidUser())).to.raise_error(
            errors.ValidationError)

    def test_when_model_validate_does_not_raise_then_does_not_raise(self):
        self.validator(User())

    def test_when_value_is_none_then_does_not_raise(self):
        self.validator(None)

    def setup(self):
        self.validator = validators.Model(User)


class User(models.Model):
    name = fields.String()

########NEW FILE########
__FILENAME__ = _helpers
# -*- coding: utf-8 -*-

import collections


def stub_validator(value):
    pass


class Spy(object):
    def __init__(self):
        self.times_called = 0

    def __call__(self):
        self.times_called += 1


class MyList(collections.MutableSequence):
    def __init__(self, *args):
        self._store = list(args)

    def __getitem__(self, index):
        return self._store[index]

    def __setitem__(self, index, value):
        pass

    def __delitem__(self, index):
        pass

    def __len__(self):
        pass

    def insert(self, index, value):
        pass

########NEW FILE########
