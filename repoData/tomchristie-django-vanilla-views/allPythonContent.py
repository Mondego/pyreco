__FILENAME__ = models
# coding=utf-8
from django.db import models

class Note(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=100)
    complete = models.BooleanField(default=False)

    @property
    def checkbox_character(self):
        return '☑' if self.complete else '☐'

    class Meta:
        ordering = ('-created',)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse_lazy
from example.notes.models import Note
from vanilla import CreateView, DeleteView, ListView, UpdateView


class ListNotes(ListView):
    model = Note


class CreateNote(CreateView):
    model = Note
    success_url = reverse_lazy('list_notes')


class EditNote(UpdateView):
    model = Note
    success_url = reverse_lazy('list_notes')


class DeleteNote(DeleteView):
    model = Note
    success_url = reverse_lazy('list_notes')

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'sqlite3.db',                   # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

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
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'statics',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'qv!8w33y)!_!w&&5ve)l)k01mzivs*+i8ms32r7x$0z2qmawbt'

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

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'templates',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'example.notes'
)

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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from example.notes.models import Note
from example.notes.views import ListNotes, CreateNote, EditNote, DeleteNote

urlpatterns = patterns('',
    url(r'^$', ListNotes.as_view(), name='list_notes'),
    url(r'^create/$', CreateNote.as_view(), name='create_note'),
    url(r'^edit/(?P<pk>\d+)/$', EditNote.as_view(), name='edit_note'),
    url(r'^delete/(?P<pk>\d+)/$', DeleteNote.as_view(), name='delete_note'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = mkdocs
#!/usr/bin/env python

import markdown
import os
import re
import shutil
import sys

root_dir = os.path.abspath(os.path.dirname(__file__))
docs_dir = os.path.join(root_dir, 'docs')
html_dir = os.path.join(root_dir, 'html')

local = not '--deploy' in sys.argv
preview = '-p' in sys.argv

if local:
    base_url = 'file://%s/' % os.path.normpath(os.path.join(os.getcwd(), html_dir))
    suffix = '.html'
    index = 'index.html'
else:
    base_url = 'http://django-vanilla-views.org'
    suffix = ''
    index = ''


main_header = '<li class="main"><a href="#{{ anchor }}">{{ title }}</a></li>'
sub_header = '<li><a href="#{{ anchor }}">{{ title }}</a></li>'
code_label = r'<a class="github" href="https://github.com/tomchristie/django-vanilla-views/tree/master/vanilla/\1"><span class="label label-info">\1</span></a>'

page = open(os.path.join(docs_dir, 'template.html'), 'r').read()

# Copy static files
# for static in ['css', 'js', 'img']:
#     source = os.path.join(docs_dir, 'static', static)
#     target = os.path.join(html_dir, static)
#     if os.path.exists(target):
#         shutil.rmtree(target)
#     shutil.copytree(source, target)


# Hacky, but what the hell, it'll do the job
path_list = [
    'index.md',
    'api/base-views.md',
    'api/model-views.md',
    'migration/base-views.md',
    'migration/model-views.md',
    'topics/frequently-asked-questions.md',
    'topics/django-braces-compatibility.md',
    'topics/django-extra-views-compatibility.md',
    'topics/release-notes.md',
]

prev_url_map = {}
next_url_map = {}
for idx in range(len(path_list)):
    path = path_list[idx]
    rel = '../' * path.count('/')

    if idx > 0:
        prev_url_map[path] = rel + path_list[idx - 1][:-3] + suffix

    if idx < len(path_list) - 1:
        next_url_map[path] = rel + path_list[idx + 1][:-3] + suffix


for (dirpath, dirnames, filenames) in os.walk(docs_dir):
    relative_dir = dirpath.replace(docs_dir, '').lstrip(os.path.sep)
    build_dir = os.path.join(html_dir, relative_dir)

    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    for filename in filenames:
        path = os.path.join(dirpath, filename)
        relative_path = os.path.join(relative_dir, filename)

        if not filename.endswith('.md'):
            if relative_dir:
                output_path = os.path.join(build_dir, filename)
                shutil.copy(path, output_path)
            continue

        output_path = os.path.join(build_dir, filename[:-3] + '.html')

        toc = ''
        text = open(path, 'r').read().decode('utf-8')
        main_title = None
        description = 'Django, CBV, GCBV, Generic class based views'
        for line in text.splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                template = main_header
                description = description + ', ' + title
            elif line.startswith('## '):
                title = line[3:].strip()
                template = sub_header
            else:
                continue

            if not main_title:
                main_title = title
            anchor = title.lower().replace(' ', '-').replace(':-', '-').replace("'", '').replace('?', '').replace('.', '')
            template = template.replace('{{ title }}', title)
            template = template.replace('{{ anchor }}', anchor)
            toc += template + '\n'

        if filename == 'index.md':
            main_title = 'Django Vanilla Views - Beautifully simple class based views'
        else:
            main_title = 'Django Vanilla Views - ' + main_title

        prev_url = prev_url_map.get(relative_path)
        next_url = next_url_map.get(relative_path)

        content = markdown.markdown(text, ['headerid'])

        output = page.replace('{{ content }}', content).replace('{{ toc }}', toc).replace('{{ base_url }}', base_url).replace('{{ suffix }}', suffix).replace('{{ index }}', index)
        output = output.replace('{{ title }}', main_title)
        output = output.replace('{{ description }}', description)
        output = output.replace('{{ page_id }}', filename[:-3])

        if prev_url:
            output = output.replace('{{ prev_url }}', prev_url)
            output = output.replace('{{ prev_url_disabled }}', '')
        else:
            output = output.replace('{{ prev_url }}', '#')
            output = output.replace('{{ prev_url_disabled }}', 'disabled')

        if next_url:
            output = output.replace('{{ next_url }}', next_url)
            output = output.replace('{{ next_url_disabled }}', '')
        else:
            output = output.replace('{{ next_url }}', '#')
            output = output.replace('{{ next_url_disabled }}', 'disabled')

        output = re.sub(r'a href="([^"]*)\.md"', r'a href="\1%s"' % suffix, output)
        output = re.sub(r'<pre><code>:::bash', r'<pre class="prettyprint lang-bsh">', output)
        output = re.sub(r'<pre>', r'<pre class="prettyprint lang-py">', output)
        output = re.sub(r'<a class="github" href="([^"]*)"></a>', code_label, output)
        open(output_path, 'w').write(output.encode('utf-8'))

if preview:
    import subprocess

    url = 'html/index.html'

    try:
        subprocess.Popen(["open", url])  # Mac
    except OSError:
        subprocess.Popen(["xdg-open", url])  # Linux
    except:
        os.startfile(url)  # Windows

########NEW FILE########
__FILENAME__ = testsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'vanilla',
)


SECRET_KEY = 'abcde12345'

########NEW FILE########
__FILENAME__ = models
# Just so that 'manage.py test' doesn't complain.

########NEW FILE########
__FILENAME__ = model_views
#coding: utf-8
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator, InvalidPage
from django.forms import models as model_forms
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.views.generic import View
import warnings


class GenericModelView(View):
    """
    Base class for all model generic views.
    """
    model = None
    fields = None

    # Object lookup parameters. These are used in the URL kwargs, and when
    # performing the model instance lookup.
    # Note that if unset then `lookup_url_kwarg` defaults to using the same
    # value as `lookup_field`.
    lookup_field = 'pk'
    lookup_url_kwarg = None

    # All the following are optional, and fall back to default values
    # based on the 'model' shortcut.
    # Each of these has a corresponding `.get_<attribute>()` method.
    queryset = None
    form_class = None
    template_name = None
    context_object_name = None

    # Pagination parameters.
    # Set `paginate_by` to an integer value to turn pagination on.
    paginate_by = None
    page_kwarg = 'page'

    # Suffix that should be appended to automatically generated template names.
    template_name_suffix = None


    # Queryset and object lookup

    def get_object(self):
        """
        Returns the object the view is displaying.
        """
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        try:
            lookup = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        except KeyError:
            msg = "Lookup field '%s' was not provided in view kwargs to '%s'"
            raise ImproperlyConfigured(msg % (lookup_url_kwarg, self.__class__.__name__))

        return get_object_or_404(queryset, **lookup)

    def get_queryset(self):
        """
        Returns the base queryset for the view.

        Either used as a list of objects to display, or as the queryset
        from which to perform the individual object lookup.
        """
        if self.queryset is not None:
            return self.queryset._clone()

        if self.model is not None:
            return self.model._default_manager.all()

        msg = "'%s' must either define 'queryset' or 'model', or override 'get_queryset()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    # Form instantiation

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        if self.form_class is not None:
            return self.form_class

        if self.model is not None:
            if self.fields is None:
                msg = "'Using GenericModelView (base class of '%s) without setting" \
                    "either 'form_class' or the 'fields' attribute is pending deprecation."
                warnings.warn(msg % self.__class__.__name__,
                              PendingDeprecationWarning)
            return model_forms.modelform_factory(self.model, fields=self.fields)

        msg = "'%s' must either define 'form_class' or both 'model' and " \
            "'fields', or override 'get_form_class()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_form(self, data=None, files=None, **kwargs):
        """
        Returns a form instance.
        """
        cls = self.get_form_class()
        return cls(data=data, files=files, **kwargs)

    # Pagination

    def get_paginate_by(self):
        """
        Returns the size of pages to use with pagination.
        """
        return self.paginate_by

    def get_paginator(self, queryset, page_size):
        """
        Returns a paginator instance.
        """
        return Paginator(queryset, page_size)

    def paginate_queryset(self, queryset, page_size):
        """
        Paginates a queryset, and returns a page object.
        """
        paginator = self.get_paginator(queryset, page_size)
        page_kwarg = self.kwargs.get(self.page_kwarg)
        page_query_param = self.request.GET.get(self.page_kwarg)
        page_number = page_kwarg or page_query_param or 1
        try:
            page_number = int(page_number)
        except ValueError:
            if page_number == 'last':
                page_number = paginator.num_pages
            else:
                msg = "Page is not 'last', nor can it be converted to an int."
                raise Http404(_(msg))

        try:
            return paginator.page(page_number)
        except InvalidPage as exc:
            msg = 'Invalid page (%s): %s'
            raise Http404(_(msg % (page_number, str(exc))))

    # Response rendering

    def get_context_object_name(self, is_list=False):
        """
        Returns a descriptive name to use in the context in addition to the
        default 'object'/'object_list'.
        """
        if self.context_object_name is not None:
            return self.context_object_name

        elif self.model is not None:
            fmt = '%s_list' if is_list else '%s'
            return fmt % self.model._meta.object_name.lower()

        return None

    def get_context_data(self, **kwargs):
        """
        Returns a dictionary to use as the context of the response.

        Takes a set of keyword arguments to use as the base context,
        and adds the following keys:

        * 'view'
        * Optionally, 'object' or 'object_list'
        * Optionally, '{context_object_name}' or '{context_object_name}_list'
        """
        kwargs['view'] = self

        if getattr(self, 'object', None) is not None:
            kwargs['object'] = self.object
            context_object_name = self.get_context_object_name()
            if context_object_name:
                kwargs[context_object_name] = self.object

        if getattr(self, 'object_list', None) is not None:
            kwargs['object_list'] = self.object_list
            context_object_name = self.get_context_object_name(is_list=True)
            if context_object_name:
                kwargs[context_object_name] = self.object_list

        return kwargs

    def get_template_names(self):
        """
        Returns a list of template names to use when rendering the response.

        If `.template_name` is not specified, then defaults to the following
        pattern: "{app_label}/{model_name}{template_name_suffix}.html"
        """
        if self.template_name is not None:
            return [self.template_name]

        if self.model is not None and self.template_name_suffix is not None:
            return ["%s/%s%s.html" % (
                self.model._meta.app_label,
                self.model._meta.object_name.lower(),
                self.template_name_suffix
            )]

        msg = "'%s' must either define 'template_name' or 'model' and " \
            "'template_name_suffix', or override 'get_template_names()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def render_to_response(self, context):
        """
        Given a context dictionary, returns an HTTP response.
        """
        return TemplateResponse(
            request=self.request,
            template=self.get_template_names(),
            context=context
        )


## The concrete model views

class ListView(GenericModelView):
    template_name_suffix = '_list'
    allow_empty = True

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        paginate_by = self.get_paginate_by()

        if not self.allow_empty and not queryset.exists():
            raise Http404

        if paginate_by is None:
            # Unpaginated response
            self.object_list = queryset
            context = self.get_context_data(
                page_obj=None,
                is_paginated=False,
                paginator=None,
            )
        else:
            # Paginated response
            page = self.paginate_queryset(queryset, paginate_by)
            self.object_list = page.object_list
            context = self.get_context_data(
                page_obj=page,
                is_paginated=page.has_other_pages(),
                paginator=page.paginator,
            )

        return self.render_to_response(context)


class DetailView(GenericModelView):
    template_name_suffix = '_detail'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return self.render_to_response(context)


class CreateView(GenericModelView):
    success_url = None
    template_name_suffix = '_form'

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_success_url(self):
        try:
            return self.success_url or self.object.get_absolute_url()
        except AttributeError:
            msg = "No URL to redirect to. '%s' must provide 'success_url' " \
                "or define a 'get_absolute_url()' method on the Model."
            raise ImproperlyConfigured(msg % self.__class__.__name__)


class UpdateView(GenericModelView):
    success_url = None
    template_name_suffix = '_form'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form(instance=self.object)
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form(data=request.POST, files=request.FILES, instance=self.object)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_success_url(self):
        try:
            return self.success_url or self.object.get_absolute_url()
        except AttributeError:
            msg = "No URL to redirect to. '%s' must provide 'success_url' " \
                "or define a 'get_absolute_url()' method on the Model."
            raise ImproperlyConfigured(msg % self.__class__.__name__)


class DeleteView(GenericModelView):
    success_url = None
    template_name_suffix = '_confirm_delete'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.success_url is None:
            msg = "No URL to redirect to. '%s' must define 'success_url'"
            raise ImproperlyConfigured(msg % self.__class__.__name__)
        return self.success_url

########NEW FILE########
__FILENAME__ = tests
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Page, Paginator
from django.db import models
from django.forms import fields, BaseForm, Form, ModelForm
from django.http import Http404
from django.test import RequestFactory, TestCase
from vanilla import *
import types
import warnings


class Example(models.Model):
    text = models.CharField(max_length=10)

    class Meta:
        ordering = ('id',)


class ExampleForm(Form):
    text = fields.CharField(max_length=10)


class InstanceOf(object):
    """
    We use this sentinal object together with our 'assertContext' helper method.

    Used to ensure that a particular context value is an object of the given
    type, without requiring a specific fixed value.  Useful for form context,
    and other complex instances.
    """
    def __init__(self, expected_type):
        self.expected_type = expected_type


def create_instance(text=None, quantity=1):
    for idx in range(quantity):
        text = text or ('example %d' % idx)
        Example.objects.create(text=text)


class BaseTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        super(BaseTestCase, self).setUp()

    def assertFormError(self, response, form, field, errors, msg_prefix=''):
        # Hack to get around the fact that we're using request factory,
        # instead of the full test client.
        response.context = response.context_data
        return super(BaseTestCase, self).assertFormError(response, form, field, errors, msg_prefix)

    def assertContext(self, response, expected):
        # Ensure the keys all match.
        # Note that this style ensures we get nice descriptive failures.
        for key in expected.keys():
            self.assertTrue(key in response.context_data,
                "context missing key '%s'" % key)
        for key in response.context_data.keys():
            self.assertTrue(key in expected,
                "context contains unexpected key '%s'" % key)

        # Ensure all the values match.
        for key, val in response.context_data.items():
            expected_val = expected[key]
            if isinstance(val, (models.query.QuerySet)):
                val = list(val)
            if isinstance(expected_val, models.query.QuerySet):
                expected_val = list(expected_val)

            if isinstance(expected_val, InstanceOf):
                self.assertTrue(isinstance(val, expected_val.expected_type),
                    "context['%s'] contained type '%s', but expected type '%s'"
                    % (key, type(val), expected_val.expected_type))
            else:
                self.assertEqual(val, expected_val,
                    "context['%s'] contained '%s', but expected '%s'" %
                    (key, val, expected_val))

    def get(self, view, *args, **kwargs):
        request = self.factory.get('/')
        return view(request, *args, **kwargs)

    def post(self, view, *args, **kwargs):
        data = kwargs.pop('data', {})
        request = self.factory.post('/', data=data)
        return view(request, *args, **kwargs)


class TestDetail(BaseTestCase):
    def test_detail(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(model=Example)
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_detail.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })

    def test_detail_not_found(self):
        create_instance(quantity=3)
        view = DetailView.as_view(model=Example)
        self.assertRaises(Http404, self.get, view, pk=999)

    def test_detail_misconfigured_urlconf(self):
        # If we don't provide 'pk' in the URL conf,
        # we should expect an ImproperlyConfigured exception.
        create_instance(quantity=3)
        view = DetailView.as_view(model=Example)
        self.assertRaises(ImproperlyConfigured, self.get, view, slug=999)

    def test_detail_misconfigured_template_name(self):
        # If don't provide 'model' or 'template_name',
        # we should expect an ImproperlyConfigured exception.
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(queryset=Example.objects.all())
        self.assertRaises(ImproperlyConfigured, self.get, view, pk=pk)

    def test_detail_misconfigured_queryset(self):
        # If don't provide 'model' or 'queryset',
        # we should expect an ImproperlyConfigured exception.
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(template_name='example.html')
        self.assertRaises(ImproperlyConfigured, self.get, view, pk=pk)

    def test_detail_missing_context_object_name(self):
        # If don't provide 'model' or 'context_object_name',
        # then the context will only contain the 'object' key.
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(queryset=Example.objects.all(), template_name='example.html')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['example.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })


class TestList(BaseTestCase):
    def test_list(self):
        create_instance(quantity=3)
        view = ListView.as_view(model=Example)
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': Example.objects.all(),
            'example_list': Example.objects.all(),
            'view': InstanceOf(View),
            'page_obj': None,
            'paginator': None,
            'is_paginated': False
        })

    def test_empty_list(self):
        view = ListView.as_view(model=Example)
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': [],
            'example_list': [],
            'view': InstanceOf(View),
            'page_obj': None,
            'paginator': None,
            'is_paginated': False
        })

    def test_empty_list_not_found(self):
        view = ListView.as_view(model=Example, allow_empty=False)
        self.assertRaises(Http404, self.get, view, pk=999)

    def test_paginated_list(self):
        create_instance(quantity=30)
        view = ListView.as_view(model=Example, paginate_by=10)
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': Example.objects.all()[:10],
            'example_list': Example.objects.all()[:10],
            'view': InstanceOf(View),
            'page_obj': InstanceOf(Page),
            'paginator': InstanceOf(Paginator),
            'is_paginated': True
        })

    def test_paginated_list_valid_page_specified(self):
        create_instance(quantity=30)
        view = ListView.as_view(model=Example, paginate_by=10)
        response = self.get(view, page=2)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': Example.objects.all()[10:20],
            'example_list': Example.objects.all()[10:20],
            'view': InstanceOf(View),
            'page_obj': InstanceOf(Page),
            'paginator': InstanceOf(Paginator),
            'is_paginated': True
        })

    def test_paginated_list_last_page_specified(self):
        create_instance(quantity=30)
        view = ListView.as_view(model=Example, paginate_by=10)
        response = self.get(view, page='last')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': Example.objects.all()[20:],
            'example_list': Example.objects.all()[20:],
            'view': InstanceOf(View),
            'page_obj': InstanceOf(Page),
            'paginator': InstanceOf(Paginator),
            'is_paginated': True
        })

    def test_paginated_list_invalid_page_specified(self):
        create_instance(quantity=30)
        view = ListView.as_view(model=Example, paginate_by=10)
        self.assertRaises(Http404, self.get, view, page=999)

    def test_paginated_list_non_integer_page_specified(self):
        create_instance(quantity=30)
        view = ListView.as_view(model=Example, paginate_by=10)
        self.assertRaises(Http404, self.get, view, page='null')


class TestCreate(BaseTestCase):
    def test_create(self):
        view = CreateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.post(view, data={'text': 'example'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], '/success/')
        self.assertEqual(Example.objects.count(), 1)
        self.assertEqual(Example.objects.get().text, 'example')

    def test_create_failed(self):
        view = CreateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.post(view, data={'text': 'example' * 100})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_form.html'])
        self.assertFormError(response, 'form', 'text', ['Ensure this value has at most 10 characters (it has 700).'])
        self.assertContext(response, {
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })
        self.assertFalse(Example.objects.exists())

    def test_create_preview(self):
        view = CreateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_form.html'])
        self.assertContext(response, {
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })
        self.assertFalse(Example.objects.exists())

    def test_create_no_success_url(self):
        view = CreateView.as_view(model=Example, fields=('text',))
        self.assertRaises(ImproperlyConfigured, self.post, view, data={'text': 'example'})

    def test_create_misconfigured_form_class(self):
        # If don't provide 'model' or 'form_class',
        # we should expect an ImproperlyConfigured exception.
        view = CreateView.as_view(
            queryset=Example.objects.all(),
            template_name='example.html',
            success_url='/success/'
        )
        self.assertRaises(ImproperlyConfigured, self.post, view, data={'text': 'example'})

    def test_create_create_no_fields(self):
        # If we don't provide `.fields` then expect a `PendingDeprecation` warning.
        view = CreateView.as_view(model=Example, success_url='/success/')
        with warnings.catch_warnings(record=True) as warned:
            warnings.simplefilter("always")
            self.post(view, data={'text': 'example'})
            self.assertTrue(bool(warned))

class TestUpdate(BaseTestCase):
    def test_update(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = UpdateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.post(view, pk=pk, data={'text': 'example'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], '/success/')
        self.assertEqual(Example.objects.count(), 3)
        self.assertEqual(Example.objects.get(pk=pk).text, 'example')

    def test_update_failed(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        original_text = Example.objects.all()[0].text
        view = UpdateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.post(view, pk=pk, data={'text': 'example' * 100})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_form.html'])
        self.assertFormError(response, 'form', 'text', ['Ensure this value has at most 10 characters (it has 700).'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })
        self.assertEqual(Example.objects.count(), 3)
        self.assertEqual(Example.objects.get(pk=pk).text, original_text)

    def test_update_preview(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = UpdateView.as_view(model=Example, fields=('text',), success_url='/success/')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_form.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })
        self.assertEqual(Example.objects.count(), 3)

    def test_update_no_success_url(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = UpdateView.as_view(model=Example, fields=('text',))
        self.assertRaises(ImproperlyConfigured, self.post, view, pk=pk, data={'text': 'example'})

    def test_update_no_fields(self):
        # If we don't provide `.fields` then expect a `PendingDeprecation` warning.
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = UpdateView.as_view(model=Example, success_url='/success/')
        with warnings.catch_warnings(record=True) as warned:
            warnings.simplefilter("always")
            self.post(view, pk=pk, data={'text': 'example'})
            self.assertTrue(bool(warned))

class TestDelete(BaseTestCase):
    def test_delete(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DeleteView.as_view(model=Example, success_url='/success/')
        response = self.post(view, pk=pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], '/success/')
        self.assertEqual(Example.objects.count(), 2)
        self.assertFalse(Example.objects.filter(pk=pk).exists())

    def test_delete_not_found(self):
        create_instance(quantity=3)
        view = DeleteView.as_view(model=Example, success_url='/success/')
        self.assertRaises(Http404, self.get, view, pk=999)

    def test_delete_preview(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DeleteView.as_view(model=Example, success_url='/success/')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_confirm_delete.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })
        self.assertEqual(Example.objects.count(), 3)

    def test_delete_no_success_url(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DeleteView.as_view(model=Example)
        self.assertRaises(ImproperlyConfigured, self.post, view, pk=pk)


class TestAttributeOverrides(BaseTestCase):
    def test_template_name_override(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(model=Example, template_name='example.html')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['example.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })

    def test_template_name_suffix_override(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(model=Example, template_name_suffix='_suffix')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_suffix.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'example': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })

    def test_context_object_name_override(self):
        create_instance(quantity=3)
        pk = Example.objects.all()[0].pk
        view = DetailView.as_view(model=Example, context_object_name='current')
        response = self.get(view, pk=pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_detail.html'])
        self.assertContext(response, {
            'object': Example.objects.get(pk=pk),
            'current': Example.objects.get(pk=pk),
            'view': InstanceOf(View)
        })

    def test_form_class_override(self):
        class CustomForm(ModelForm):
            class Meta:
                model = Example
        view = CreateView.as_view(model=Example, success_url='/success/', form_class=CustomForm)
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_form.html'])
        self.assertContext(response, {
            'form': InstanceOf(CustomForm),
            'view': InstanceOf(View)
        })
        self.assertFalse(Example.objects.exists())

    def test_queryset_override(self):
        create_instance(text='abc', quantity=3)
        create_instance(text='def', quantity=3)
        view = ListView.as_view(model=Example, queryset=Example.objects.filter(text='abc'))
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['vanilla/example_list.html'])
        self.assertContext(response, {
            'object_list': Example.objects.filter(text='abc'),
            'example_list': Example.objects.filter(text='abc'),
            'view': InstanceOf(View),
            'page_obj': None,
            'paginator': None,
            'is_paginated': False
        })


class TestTemplateView(BaseTestCase):
    def test_template_view(self):
        view = TemplateView.as_view(template_name='example.html')
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['example.html'])
        self.assertContext(response, {
            'view': InstanceOf(View)
        })

    def test_misconfigured_template_view(self):
        # A template view with no `template_name` is improperly configured.
        view = TemplateView.as_view()
        self.assertRaises(ImproperlyConfigured, self.get, view)


class TestFormView(BaseTestCase):
    def test_form_success(self):
        view = FormView.as_view(
            form_class=ExampleForm,
            success_url='/success/',
            template_name='example.html'
        )
        response = self.post(view, data={'text': 'example'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], '/success/')

    def test_form_failure(self):
        view = FormView.as_view(
            form_class=ExampleForm,
            success_url='/success/',
            template_name='example.html'
        )
        response = self.post(view, data={'text': 'example' * 100})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['example.html'])
        self.assertFormError(response, 'form', 'text', ['Ensure this value has at most 10 characters (it has 700).'])
        self.assertContext(response, {
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })

    def test_form_preview(self):
        view = FormView.as_view(
            form_class=ExampleForm,
            success_url='/success/',
            template_name='example.html'
        )
        response = self.get(view)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ['example.html'])
        self.assertContext(response, {
            'form': InstanceOf(BaseForm),
            'view': InstanceOf(View)
        })

    def test_misconfigured_form_view_no_form_class(self):
        # A template view with no `form_class` is improperly configured.
        view = FormView.as_view(
            success_url='/success/',
            template_name='example.html'
        )
        self.assertRaises(ImproperlyConfigured, self.get, view)

    def test_misconfigured_form_view_no_success_url(self):
        # A template view with no `success_url` is improperly configured.
        view = FormView.as_view(
            form_class=ExampleForm,
            template_name='example.html'
        )
        self.assertRaises(ImproperlyConfigured, self.post, view, data={'text': 'example'})

########NEW FILE########
__FILENAME__ = views
#coding: utf-8
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.generic import View, RedirectView


class GenericView(View):
    """
    A generic base class for building template and/or form views.
    """
    form_class = None
    template_name = None

    # Form instantiation

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        if self.form_class is not None:
            return self.form_class

        msg = "'%s' must either define 'form_class' or override 'get_form_class()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_form(self, data=None, files=None, **kwargs):
        """
        Given `data` and `files` QueryDicts, and optionally other named
        arguments, and returns a form.
        """
        cls = self.get_form_class()
        return cls(data=data, files=files, **kwargs)

    # Response rendering

    def get_template_names(self):
        """
        Returns a set of template names that may be used when rendering
        the response.
        """
        if self.template_name is not None:
            return [self.template_name]

        msg = "'%s' must either define 'template_name' or override 'get_template_names()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_context_data(self, **kwargs):
        """
        Takes a set of keyword arguments to use as the base context, and
        returns a context dictionary to use for the view, additionally adding
        in 'view'.
        """
        kwargs['view'] = self
        return kwargs

    def render_to_response(self, context):
        """
        Given a context dictionary, returns an HTTP response.
        """
        return TemplateResponse(
            request=self.request,
            template=self.get_template_names(),
            context=context
        )


class TemplateView(GenericView):
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return self.render_to_response(context)


class FormView(GenericView):
    success_url = None

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_success_url(self):
        if self.success_url is None:
            msg = "'%s' must define 'success_url' or override 'form_valid()'"
            raise ImproperlyConfigured(msg % self.__class__.__name__)
        return self.success_url    

########NEW FILE########
