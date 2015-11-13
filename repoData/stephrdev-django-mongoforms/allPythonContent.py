__FILENAME__ = forms
# -*- coding: utf-8 -*-

from django import forms
from mongoforms import MongoForm
from models import BlogPost

class BlogPostForm(MongoForm):
    class Meta:
        document = BlogPost
        fields = ('author', 'title', 'content', 'published')
    content = forms.CharField(widget=forms.Textarea)
########NEW FILE########
__FILENAME__ = models
import datetime

from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse

from mongoengine import *

class BlogPost(Document):
    published = BooleanField(default=False)
    author = StringField(required=True)
    title = StringField(required=True)
    slug = StringField()
    content = StringField(required=True)
    
    datetime_added = DateTimeField(default=datetime.datetime.now)
    
    def save(self):
        if self.slug is None:
            slug = slugify(self.title)
            new_slug = slug
            c = 1
            while True:
                try:
                    BlogPost.objects.get(slug=new_slug)
                except BlogPost.DoesNotExist:
                    break
                else:
                    c += 1
                    new_slug = '%s-%s' % (slug, c)
            self.slug = new_slug
        return super(BlogPost, self).save()
    
    def get_absolute_url(self):
        #return u'%s/' % self.slug
        return reverse('apps.blog.views.show', kwargs={'slug': self.slug})
    
    @queryset_manager
    def published_posts(doc_cls, queryset):
        return queryset(published=True)

    meta = {
        'ordering': ['-datetime_added']
    }
########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to, direct_to_template

entry_pattern = patterns('apps.blog.views',
    (r'^$', 'show'),
    (r'^edit/$', 'edit'),
    (r'^delete/$', 'delete'),
)

urlpatterns = patterns('apps.blog.views',
    (r'^$', 'index'),
    (r'^new/$', 'new'),
    (r'^(?P<slug>[\w\-]+)/', include(entry_pattern)),
)
########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from models import BlogPost
from forms import BlogPostForm

def index(request, slug=None, template_name='blog/index.html'):
    posts = BlogPost.objects[:5]
    template_context = {'posts': posts}
    #print posts[0].get_absolute_url()
    return render_to_response(
        template_name,
        template_context,
        RequestContext(request)
    )

def show(request, slug, template_name='blog/show.html'):
    post = BlogPost.objects.get(slug=slug)
    template_context = {'post': post}
    
    return render_to_response(
        template_name,
        template_context,
        RequestContext(request)
    )

def new(request, template_name='blog/new_or_edit.html'):
    if request.method == 'POST':
        form = BlogPostForm(request.POST)
        if form.is_valid():
            form.save()
        return HttpResponseRedirect("/")
    else:
        form = BlogPostForm()
    
    template_context = {'form': form}
    
    return render_to_response(
        template_name,
        template_context,
        RequestContext(request)
    )

def delete(request, slug):
    post = BlogPost.objects(slug=slug)
    post.delete()
    return HttpResponseRedirect("/")

def edit(request, slug, template_name='blog/new_or_edit.html'):
    
    post = BlogPost.objects.get(slug=slug)
    if request.method == 'POST':
        form = BlogPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
        return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = BlogPostForm(instance=post)
    
    template_context = {'form': form}
    
    return render_to_response(
        template_name,
        template_context,
        RequestContext(request)
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
__FILENAME__ = settings
# -*- coding: utf-8 -*-

import platform
import sys
import os

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, '../../../'))
from mongoengine import connect

connect('mongoforms_test')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

sys.path.append(os.path.join(PROJECT_ROOT, '../../'))

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'site_media')
TEMPLATE_DIRS = [os.path.join(PROJECT_ROOT, 'templates')]
ADMIN_MEDIA_PREFIX = '/media/'
ROOT_URLCONF = 'blogprj.urls'
TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de-de'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

INSTALLED_APPS = (
    'apps.blog',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.request",
    "django.core.context_processors.auth",
    "django.core.context_processors.media",
    "django.core.context_processors.debug",
)

try:
    SECRET_KEY
except NameError:
    SECRET_FILE = os.path.join(PROJECT_ROOT, 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            from random import choice
            SECRET_KEY = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
            secret = file(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % SECRET_FILE)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^', include('apps.blog.urls')),
)
########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.utils.encoding import smart_unicode
from bson.errors import InvalidId
from bson.objectid import ObjectId


class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, queryset, *aargs, **kwaargs):
        forms.Field.__init__(self, *aargs, **kwaargs)
        self.queryset = queryset

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices

        self._choices = [(obj.id, smart_unicode(obj)) for obj in self.queryset]
        return self._choices

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def clean(self, value):
        try:
            oid = ObjectId(value)
            oid = super(ReferenceField, self).clean(oid)
            if 'id' in self.queryset._query_obj.query:
                obj = self.queryset.get()
            else:
                obj = self.queryset.get(id=oid)
        except (TypeError, InvalidId, self.queryset._document.DoesNotExist):
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value':value})
        return obj


class MongoFormFieldGenerator(object):
    """This class generates Django form-fields for mongoengine-fields."""

    def generate(self, field_name, field):
        """Tries to lookup a matching formfield generator (lowercase
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """

        if hasattr(self, 'generate_%s' % field.__class__.__name__.lower()):
            generator = getattr(
                self,
                'generate_%s' % field.__class__.__name__.lower())
            return generator(
                field_name,
                field,
                (field.verbose_name or field_name).capitalize())
        else:
            raise NotImplementedError('%s is not supported by MongoForm' % \
                field.__class__.__name__)

    def generate_stringfield(self, field_name, field, label):

        if field.regex:
            return forms.RegexField(
                label=label,
                regex=field.regex,
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
                initial=field.default)
        elif field.choices:
            choices = tuple(field.choices)
            if not isinstance(field.choices[0], (tuple, list)):
                choices = zip(choices, choices)
            return forms.ChoiceField(
                label=label,
                required=field.required,
                initial=field.default,
                choices=choices)
        elif field.max_length is None:
            return forms.CharField(
                label=label,
                required=field.required,
                initial=field.default,
                min_length=field.min_length,
                widget=forms.Textarea)
        else:
            return forms.CharField(
                label=label,
                required=field.required,
                min_length=field.min_length,
                max_length=field.max_length,
                initial=field.default)

    def generate_emailfield(self, field_name, field, label):
        return forms.EmailField(
            label=label,
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default)

    def generate_urlfield(self, field_name, field, label):
        return forms.URLField(
            label=label,
            required=field.required,
            min_length=field.min_length,
            max_length=field.max_length,
            initial=field.default)

    def generate_intfield(self, field_name, field, label):
        return forms.IntegerField(
            label=label,
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default)

    def generate_floatfield(self, field_name, field, label):
        return forms.FloatField(
            label=label,
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default)

    def generate_decimalfield(self, field_name, field, label):
        return forms.DecimalField(
            label=label,
            required=field.required,
            min_value=field.min_value,
            max_value=field.max_value,
            initial=field.default)

    def generate_booleanfield(self, field_name, field, label):
        return forms.BooleanField(
            label=label,
            required=field.required,
            initial=field.default)

    def generate_datetimefield(self, field_name, field, label):
        return forms.DateTimeField(
            label=label,
            required=field.required,
            initial=field.default)

    def generate_referencefield(self, field_name, field, label):
        return ReferenceField(
            field.document_type.objects,
            label=label)

########NEW FILE########
__FILENAME__ = forms
import types
from django import forms
from django.utils.datastructures import SortedDict
from mongoengine.base import BaseDocument
from fields import MongoFormFieldGenerator
from utils import mongoengine_validate_wrapper, iter_valid_fields
from mongoengine.fields import ReferenceField

__all__ = ('MongoForm',)

class MongoFormMetaClass(type):
    """Metaclass to create a new MongoForm."""

    def __new__(cls, name, bases, attrs):
        # get all valid existing Fields and sort them
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in \
            attrs.items() if isinstance(obj, forms.Field)]
        fields.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))

        # get all Fields from base classes
        for base in bases[::-1]:
            if hasattr(base, 'base_fields'):
                fields = base.base_fields.items() + fields

        # add the fields as "our" base fields
        attrs['base_fields'] = SortedDict(fields)
        
        # Meta class available?
        if 'Meta' in attrs and hasattr(attrs['Meta'], 'document') and \
           issubclass(attrs['Meta'].document, BaseDocument):
            doc_fields = SortedDict()

            formfield_generator = getattr(attrs['Meta'], 'formfield_generator', \
                MongoFormFieldGenerator)()

            # walk through the document fields
            for field_name, field in iter_valid_fields(attrs['Meta']):
                # add field and override clean method to respect mongoengine-validator
                doc_fields[field_name] = formfield_generator.generate(field_name, field)
                doc_fields[field_name].clean = mongoengine_validate_wrapper(
                    doc_fields[field_name].clean, field._validate)

            # write the new document fields to base_fields
            doc_fields.update(attrs['base_fields'])
            attrs['base_fields'] = doc_fields

        # maybe we need the Meta class later
        attrs['_meta'] = attrs.get('Meta', object())

        return super(MongoFormMetaClass, cls).__new__(cls, name, bases, attrs)

class MongoForm(forms.BaseForm):
    """Base MongoForm class. Used to create new MongoForms"""
    __metaclass__ = MongoFormMetaClass

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
        initial=None, error_class=forms.util.ErrorList, label_suffix=':',
        empty_permitted=False, instance=None):
        """ initialize the form"""

        assert isinstance(instance, (types.NoneType, BaseDocument)), \
            'instance must be a mongoengine document, not %s' % \
                type(instance).__name__

        assert hasattr(self, 'Meta'), 'Meta class is needed to use MongoForm'
        # new instance or updating an existing one?
        if instance is None:
            if self._meta.document is None:
                raise ValueError('MongoForm has no document class specified.')
            self.instance = self._meta.document()
            object_data = {}
            self.instance._adding = True
        else:
            self.instance = instance
            self.instance._adding = False
            object_data = {}

            # walk through the document fields
            for field_name, field in iter_valid_fields(self._meta):
                # add field data if needed
                field_data = getattr(instance, field_name)
                if isinstance(self._meta.document._fields[field_name], ReferenceField):
                    # field data could be None for not populated refs
                    field_data = field_data and str(field_data.id)
                object_data[field_name] = field_data

        # additional initial data available?
        if initial is not None:
            object_data.update(initial)

        self._validate_unique = False
        super(MongoForm, self).__init__(data, files, auto_id, prefix,
            object_data, error_class, label_suffix, empty_permitted)

    def save(self, commit=True):
        """save the instance or create a new one.."""

        # walk through the document fields
        for field_name, field in iter_valid_fields(self._meta):
            setattr(self.instance, field_name, self.cleaned_data.get(field_name))

        if commit:
            self.instance.save()

        return self.instance

########NEW FILE########
__FILENAME__ = utils
from django import forms
from mongoengine.base import ValidationError


def mongoengine_validate_wrapper(old_clean, new_clean):
    """
    A wrapper function to validate formdata against mongoengine-field
    validator and raise a proper django.forms ValidationError if there
    are any problems.
    """

    def inner_validate(value):
        value = old_clean(value)
        try:
            new_clean(value)
            return value
        except ValidationError, e:
            raise forms.ValidationError(e)
    return inner_validate


def iter_valid_fields(meta):
    """walk through the available valid fields.."""

    # fetch field configuration and always add the id_field as exclude
    meta_fields = getattr(meta, 'fields', ())
    meta_exclude = getattr(meta, 'exclude', ())
    meta_exclude += (meta.document._meta.get('id_field'),)

    # walk through meta_fields or through the document fields to keep
    # meta_fields order in the form
    if meta_fields:
        for field_name in meta_fields:
            field = meta.document._fields.get(field_name)
            if field:
                yield (field_name, field)
    else:
        for field_name, field in meta.document._fields.iteritems():
            # skip excluded fields
            if field_name not in meta_exclude:
                yield (field_name, field)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testprj project.
from django.conf.global_settings import *
from mongoengine import connect


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DB = connect('test')

TEST_RUNNER = 'testprj.tests.MongoengineDjangoTestSuiteRunner'

# hack for DATABASES setting
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}

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

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = 'fu3h7p7%#3#b6%m!e&equh6zuitgu5h9%nb@^=2#os5@#^8*gx'

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

ROOT_URLCONF = 'urls'

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
    'testapp',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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

########NEW FILE########
__FILENAME__ = decorators
from django.shortcuts import render_to_response


def render_test(func):
    
    def wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)        
        return (isinstance(result, dict) and
            render_to_response('test_template.html', result) or result)
    
    return wrapper

########NEW FILE########
__FILENAME__ = documents
from mongoengine import *


class Test001Parent(Document):
    name = StringField(required=True)
    
    def __unicode__(self):
        return u'%s' % self.name


class Test001Child(Document):
    parent = ReferenceField(Test001Parent, required=True)
    name = StringField(required=True)
    
    def __unicode__(self):
        return u'%s' % self.name


class Test002StringField(Document):
    string_field_1 = StringField(choices=(
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Extra Extra Large')))
    string_field_2 = StringField(choices=('S', 'M', 'L', 'XL', 'XXL'))
    string_field_3 = StringField(regex=r'^test.*$')

########NEW FILE########
__FILENAME__ = forms
from django.forms import CharField, PasswordInput
from mongoengine.django.auth import User

from mongoforms import MongoForm

from documents import Test001Child, Test002StringField


class Test001ChildForm(MongoForm):
    class Meta:
        document = Test001Child
        fields = ('parent', 'name')


class Test002StringFieldForm(MongoForm):
    class Meta:
        document = Test002StringField
        fields = ('string_field_1', 'string_field_2')


class Test003FormFieldOrder(MongoForm):
    class Meta:
        document = User
        fields = ('username', 'email', 'password')
    password = CharField(widget=PasswordInput, label="Your password")
    repeat_password = CharField(widget=PasswordInput, label="Repeat password")


class Test004StringFieldForm(MongoForm):
    class Meta:
        document = Test002StringField
        fields = ('string_field_3',)

########NEW FILE########
__FILENAME__ = models
from documents import *

########NEW FILE########
__FILENAME__ = render
from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *

from mongoforms.fields import MongoFormFieldGenerator

from testprj.tests import MongoengineTestCase


class _FieldRenderTestCase(MongoengineTestCase):
    # mongoengine field instance to test
    field_class = None
    # widget rendering result (most common value)
    rendered_widget = '<input name="test_field" type="text" />'
    # hook for not implemented fields
    is_not_implemented = False

    def setUp(self):
        self.generator = MongoFormFieldGenerator()

    def get_field(self):

        class TestDocument(Document):
            test_field = self.field_class()

        return TestDocument._fields['test_field']

    def get_form_field(self):
        return self.generator.generate('test_field', self.get_field())

    def runTest(self):

        if self.is_not_implemented:
            self.assertRaises(NotImplementedError, self.get_form_field)
        else:
            self.assertMultiLineEqual(
                self.rendered_widget,
                self.get_form_field().widget.render('test_field', None))


class Test001StringFieldRender(_FieldRenderTestCase):
    field_class = StringField
    rendered_widget = \
        '<textarea cols="40" name="test_field" rows="10">\r\n</textarea>'


class Test002IntFieldRender(_FieldRenderTestCase):
    field_class = IntField


class Test003FloatFieldRender(_FieldRenderTestCase):
    field_class = FloatField


class Test004BooleanFieldRender(_FieldRenderTestCase):
    field_class = BooleanField
    rendered_widget = \
        '<input name="test_field" type="checkbox" />'


class Test005DateTimeFieldRender(_FieldRenderTestCase):
    field_class = DateTimeField


class Test006EmbeddedDocumentFieldRender(_FieldRenderTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestEmbeddedDocument(EmbeddedDocument):
            pass

        class TestDocument(Document):
            test_field = EmbeddedDocumentField(TestEmbeddedDocument)

        return TestDocument._fields['test_field']


class Test007ListFieldRender(_FieldRenderTestCase):
    field_class = ListField
    is_not_implemented = True


class Test008DictFieldRender(_FieldRenderTestCase):
    field_class = DictField
    is_not_implemented = True


class Test009ObjectIdFieldRender(_FieldRenderTestCase):
    field_class = ObjectIdField
    is_not_implemented = True


class Test010ReferenceFieldRender(_FieldRenderTestCase):
    rendered_widget = \
        '<select name="test_field">\n</select>'

    def get_field(self):

        class TestDocument(Document):
            test_field = ReferenceField('self')

        return TestDocument._fields['test_field']


class Test011MapFieldRender(_FieldRenderTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestDocument(Document):
            test_field = MapField(StringField())

        return TestDocument._fields['test_field']


class Test012DecimalFieldRender(_FieldRenderTestCase):
    field_class = DecimalField


class Test013ComplexDateTimeFieldRender(_FieldRenderTestCase):
    field_class = ComplexDateTimeField
    is_not_implemented = True


class Test014URLFieldRender(_FieldRenderTestCase):
    field_class = URLField


class Test015GenericReferenceFieldRender(_FieldRenderTestCase):
    field_class = GenericReferenceField
    is_not_implemented = True


class Test016FileFieldRender(_FieldRenderTestCase):
    field_class = FileField
    is_not_implemented = True


class Test017BinaryFieldRender(_FieldRenderTestCase):
    field_class = BinaryField
    is_not_implemented = True


class Test018SortedListFieldRender(_FieldRenderTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestDocument(Document):
            test_field = SortedListField(StringField)

        return TestDocument._fields['test_field']


class Test019EmailFieldRender(_FieldRenderTestCase):
    field_class = EmailField


class Test020GeoPointFieldRender(_FieldRenderTestCase):
    field_class = GeoPointField
    is_not_implemented = True


class Test021ImageFieldRender(_FieldRenderTestCase):
    field_class = ImageField
    is_not_implemented = True


class Test022SequenceFieldRender(_FieldRenderTestCase):
    field_class = SequenceField
    is_not_implemented = True


class Test023UUIDFieldRender(_FieldRenderTestCase):
    field_class = UUIDField
    is_not_implemented = True


class Test024GenericEmbeddedDocumentFieldRender(_FieldRenderTestCase):
    field_class = GenericEmbeddedDocumentField
    is_not_implemented = True

########NEW FILE########
__FILENAME__ = validate
from decimal import Decimal

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *

from mongoforms.fields import MongoFormFieldGenerator

from testprj.tests import MongoengineTestCase


class _FieldValidateTestCase(MongoengineTestCase):

    # mongoengine field instance to test
    field_class = None
    # list of correct sample field values before and after clean
    correct_samples = ()
    # list of incorrect sample field values before clean
    incorrect_samples = ()
    # hook for not implemented fields
    is_not_implemented = False

    def setUp(self):
        self.generator = MongoFormFieldGenerator()

    def get_field(self):

        class TestDocument(Document):
            test_field = self.field_class()

        return TestDocument._fields['test_field']

    def get_form_field(self):
        return self.generator.generate('test_field', self.get_field())

    def runTest(self):

        # skip test as we have already tested this in render tests
        if self.is_not_implemented:
            return

        # test for correct samples
        for dirty_value, clean_value in self.correct_samples:
            self.assertEqual(
                clean_value,
                self.get_form_field().validate(dirty_value))

        # test for incorrect samples
        for value in self.incorrect_samples:
            self.assertRaises(
                ValidationError,
                lambda: self.get_form_field().validate(value))


class Test001StringFieldValidate(_FieldValidateTestCase):
    field_class = StringField
    correct_samples = [('test value', None)]


class Test002IntFieldValidate(_FieldValidateTestCase):
    field_class = IntField
    correct_samples = [('42', None)]


class Test003FloatFieldValidate(_FieldValidateTestCase):
    field_class = FloatField
    correct_samples = [('3.14', None)]


class Test004BooleanFieldValidate(_FieldValidateTestCase):
    field_class = BooleanField
    correct_samples = [('1', None), ('0', None)]


class Test005DateTimeFieldValidate(_FieldValidateTestCase):
    field_class = DateTimeField
    correct_samples = [('1970-01-02 03:04:05.678901', None)]


class Test006EmbeddedDocumentFieldValidate(_FieldValidateTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestEmbeddedDocument(EmbeddedDocument):
            pass

        class TestDocument(Document):
            test_field = EmbeddedDocumentField(TestEmbeddedDocument)

        return TestDocument._fields['test_field']


class Test007ListFieldValidate(_FieldValidateTestCase):
    field_class = ListField
    is_not_implemented = True


class Test008DictFieldValidate(_FieldValidateTestCase):
    field_class = DictField
    is_not_implemented = True


class Test009ObjectIdFieldValidate(_FieldValidateTestCase):
    field_class = ObjectIdField
    is_not_implemented = True


class Test010ReferenceFieldValidate(_FieldValidateTestCase):
    correct_samples = []

    def get_field(self):

        class TestDocument(Document):
            test_field = ReferenceField('self')

        return TestDocument._fields['test_field']


class Test011MapFieldValidate(_FieldValidateTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestDocument(Document):
            test_field = MapField(StringField())

        return TestDocument._fields['test_field']


class Test012DecimalFieldValidate(_FieldValidateTestCase):
    field_class = DecimalField
    correct_samples = [(Decimal('3.14'), Decimal('3.14'))]


class Test013ComplexDateTimeFieldValidate(_FieldValidateTestCase):
    field_class = ComplexDateTimeField
    is_not_implemented = True


class Test014URLFieldValidate(_FieldValidateTestCase):
    field_class = URLField
    correct_samples = [('http://www.example.com/', None)]


class Test015GenericReferenceFieldValidate(_FieldValidateTestCase):
    field_class = GenericReferenceField
    is_not_implemented = True


class Test016FileFieldValidate(_FieldValidateTestCase):
    field_class = FileField
    is_not_implemented = True


class Test017BinaryFieldValidate(_FieldValidateTestCase):
    field_class = BinaryField
    is_not_implemented = True


class Test018SortedListFieldValidate(_FieldValidateTestCase):
    is_not_implemented = True

    def get_field(self):

        class TestDocument(Document):
            test_field = SortedListField(StringField)

        return TestDocument._fields['test_field']


class Test019EmailFieldValidate(_FieldValidateTestCase):
    field_class = EmailField
    correct_samples = [('user@example.com', None)]


class Test020GeoPointFieldValidate(_FieldValidateTestCase):
    field_class = GeoPointField
    is_not_implemented = True


class Test021ImageFieldValidate(_FieldValidateTestCase):
    field_class = ImageField
    is_not_implemented = True


class Test022SequenceFieldValidate(_FieldValidateTestCase):
    field_class = SequenceField
    is_not_implemented = True


class Test023UUIDFieldValidate(_FieldValidateTestCase):
    field_class = UUIDField
    is_not_implemented = True


class Test024GenericEmbeddedDocumentFieldValidate(_FieldValidateTestCase):
    field_class = GenericEmbeddedDocumentField
    is_not_implemented = True

########NEW FILE########
__FILENAME__ = regression
from django.test.client import Client

from ..documents import Test001Parent
from ..forms import (Test002StringFieldForm, Test003FormFieldOrder,
    Test004StringFieldForm)

from testprj.tests import MongoengineTestCase


class MongoformsRegressionTests(MongoengineTestCase):

    def test001_possible_changes_loose_in_ReferenceField_clean_method(self):
        # drop any parent present
        Test001Parent.objects.delete()

        # prepare two test parents
        parent1 = Test001Parent(name='parent1')
        parent1.save()
        parent2 = Test001Parent(name='parent2')
        parent2.save()

        # prepare test client
        c = Client()

        # post form with first parent and empty name
        response = c.post('/test001/', {'parent': parent1.pk})

        # assert first parent is selected
        self.assertEqual(response.context['form'].data['parent'],
            unicode(parent1.pk), 'first parent must be selected')

        # post form with second parent and empty name
        response = c.post('/test001/', {'parent': parent2.pk})

        # assert second parent is selected
        self.assertEqual(response.context['form'].data['parent'],
            unicode(parent2.pk), 'second parent must be selected')

    def test002_issue_13_StringField_problem(self):
        form = Test002StringFieldForm(
            {'string_field_1': 'M', 'string_field_2': 'S'})
        self.assertTrue(form.is_valid())
        self.assertEqual('M', form.cleaned_data['string_field_1'])
        self.assertEqual('S', form.cleaned_data['string_field_2'])

    def test003_issue_19_form_field_order(self):
        form = Test003FormFieldOrder()
        self.assertListEqual(
            ['username', 'email', 'password', 'repeat_password'],
            form.fields.keys())

    def test004_issue_23_StringField_regex(self):
        form = Test004StringFieldForm({'string_field_3': 'testbar',})
        self.assertTrue(form.is_valid())
        self.assertEqual('testbar', form.cleaned_data['string_field_3'])

    def test004_issue_23_StringField_regex_fail(self):
        form = Test004StringFieldForm({'string_field_3': 'foobar',})
        self.assertFalse(form.is_valid())

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('testapp.views',
    url(r'^test001/$', 'test001', {}, 'test001'),
)

########NEW FILE########
__FILENAME__ = views
from decorators import render_test

from forms import Test001ChildForm


@render_test
def test001(request):

    if request.method == 'POST':
        form = Test001ChildForm(request.POST)

        if form.is_valid():
            form.save()

    else:
        form = Test001ChildForm()

    return {'form': form}

########NEW FILE########
__FILENAME__ = tests
from django.test.simple import DjangoTestSuiteRunner
from django.test.testcases import TestCase


class MongoengineDjangoTestSuiteRunner(DjangoTestSuiteRunner):

    def setup_databases(self, **kwargs):
        return None

    def teardown_databases(self, old_config, **kwargs):
        pass


class MongoengineTestCase(TestCase):
    """ completely dummy test case class """

    def setUp(self):
        TestCase.setUp(self)

    def _fixture_setup(self):
        pass

    def _fixture_teardown(self):
        pass


mongoforms_test_runner = MongoengineDjangoTestSuiteRunner(
    verbosity=1,
    interactive=True,
    failfast=True)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^', include('testapp.urls')),
)

########NEW FILE########
