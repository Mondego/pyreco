__FILENAME__ = future
from django.contrib.formtools.wizard.views import SessionWizardView as BaseSessionWizardView


class SessionWizardView(BaseSessionWizardView):
    def get_form_class(self):
        step = self.get_step_index()
        form = self.form_list[str(step)]

        if not hasattr(form, 'management_form'):
            # If isn't a FormSet
            return form

        formset = form
        form = formset.form

        return form

    def get_context_data(self, *args, **kwargs):
        context = super(SessionWizardView, self).get_context_data(*args, **kwargs)

        form_meta = self.get_form_class()._meta
        model_meta = form_meta.model._meta

        context['model_verbose_name'] = model_meta.verbose_name
        context['model_verbose_name_plural'] = model_meta.verbose_name_plural

        context['success_url'] = self.get_success_url()

        return context

    def get_success_url(self):
        form_meta = self.get_form_class()._meta
        model_meta = form_meta.model._meta

        app_label = model_meta.app_label
        name = model_meta.object_name.lower()

        return reverse('%s:%s_list' % (app_label, name))

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from .views import (ListView,
                    CreateView,
                    UpdateView,
                    DeleteView)


def bootstrap_patterns(*forms, **kwargs):
    patterns_ = patterns('')
    for form in forms:
        patterns_ += bootstrap_pattern(form, **kwargs)
    return patterns_


def bootstrap_pattern(form, **kwargs):
    model = form._meta.model
    name = model._meta.object_name.lower()

    urls = []

    if 'list_view' not in kwargs or kwargs.get('list_view') is not None:
        view = kwargs.get('list_view', ListView).as_view(model=model)
        url_ = kwargs.get('list_view_url', r'^%s/$' % name)
        urls.append(bootstrap_list(url_, view=view, name='%s_list' % name))

    if 'create_view' not in kwargs or kwargs.get('create_view') is not None:
        view = kwargs.get('create_view', CreateView).as_view(form_class=form)
        url_ = kwargs.get('create_view_url', r'^%s/add/$' % name)
        urls.append(bootstrap_create(url_, view=view, name='%s_form' % name))

    if 'update_view' not in kwargs or kwargs.get('update_view') is not None:
        view = kwargs.get('update_view', UpdateView).as_view(form_class=form)
        url_ = kwargs.get('update_view_url', r'^%s/(?P<pk>\d+)/$' % name)
        urls.append(bootstrap_update(url_, view=view, name='%s_form' % name))

    if 'delete_view' not in kwargs or kwargs.get('delete_view') is not None:
        view = kwargs.get('delete_view', DeleteView).as_view(model=model)
        url_ = kwargs.get('delete_view_url', r'^%s/(?P<pk>\d+)/delete/$' % name)
        urls.append(bootstrap_delete(url_, view=view, name='%s_delete' % name))

    return patterns('', *urls)


def bootstrap_list(url_, name, view=None, model=None):
    if view is None:
        view = ListView.as_view(model=model)
    return url(url_, view, name=name)


def bootstrap_create(url_, name, view=None, form=None):
    if view is None:
        view = CreateView.as_view(form_class=form)
    return url(url_, view, name=name)


def bootstrap_update(url_, name, view=None, form=None):
    if view is None:
        view = UpdateView.as_view(form_class=form)
    return url(url_, view, name=name)


def bootstrap_delete(url_, name, view=None, model=None):
    if view is None:
        view = DeleteView.as_view(model=model)
    return url(url_, view, name=name)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse

from django.contrib import messages

from django.views.generic import ListView as BaseListView

from django.views.generic.edit import (FormView as BaseFormView,
                                       CreateView as BaseCreateView,
                                       UpdateView as BaseUpdateView,
                                       DeleteView as BaseDeleteView)

from django import VERSION

if float('%d.%d1' % VERSION[:2]) >= 1.4:
    """
    Only available for Django >= 1.4

    """
    from .future import SessionWizardView


class ListView(BaseListView):
    def get_template_names(self):
        templates = super(ListView, self).get_template_names()
        templates.append('bootstrap/list.html')
        return templates

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)

        model_meta = self.model._meta

        context['model_verbose_name'] = model_meta.verbose_name
        context['model_verbose_name_plural'] = model_meta.verbose_name_plural

        context['add_object_url'] = self._get_create_url()

        return context

    def _get_create_url(self):
        model_meta = self.model._meta
        app_label = model_meta.app_label
        name = model_meta.object_name.lower()

        return reverse('%s:%s_form' % (app_label, name))


class FormView(BaseFormView):
    def get_context_data(self, **kwargs):
        context = super(FormView, self).get_context_data(**kwargs)

        form_meta = self.get_form_class()._meta
        model_meta = form_meta.model._meta

        context['model_verbose_name'] = model_meta.verbose_name
        context['model_verbose_name_plural'] = model_meta.verbose_name_plural

        context['success_url'] = self.get_success_url()

        return context

    def get_success_url(self):
        form_meta = self.get_form_class()._meta
        model_meta = form_meta.model._meta

        app_label = model_meta.app_label
        name = model_meta.object_name.lower()

        return reverse('%s:%s_list' % (app_label, name))

    def _get_model_verbose_name(self):
        model_meta = self.form_class._meta.model._meta

        return (model_meta.verbose_name,
                model_meta.verbose_name_plural)


class CreateView(FormView, BaseCreateView):
    def get_template_names(self):
        templates = super(CreateView, self).get_template_names()
        templates.append('bootstrap/create.html')
        return templates

    def form_valid(self, form):
        verbose_name = self._get_model_verbose_name()[0]
        messages.success(self.request, '%s "%s" added' % (verbose_name, form.instance))
        return super(CreateView, self).form_valid(form)


class UpdateView(FormView, BaseUpdateView):
    def get_template_names(self):
        templates = super(UpdateView, self).get_template_names()
        templates.append('bootstrap/update.html')
        return templates

    def form_valid(self, form):
        verbose_name = self._get_model_verbose_name()[0]
        messages.success(self.request, '%s "%s" updated' % (verbose_name, form.instance))
        return super(UpdateView, self).form_valid(form)

    def get_queryset(self):
        form = self.get_form_class()
        model = form._meta.model
        return model.objects.filter(pk=self.kwargs.get('pk', None))

    def get_object(self):
        return self.get_queryset().get()

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['delete_url'] = self._get_delete_url()
        return context

    def _get_delete_url(self):
        form_meta = self.get_form_class()._meta
        model_meta = form_meta.model._meta

        app_label = model_meta.app_label
        name = model_meta.object_name.lower()

        pk = self.kwargs.get('pk', None)

        return reverse('%s:%s_delete' % (app_label, name), args=(pk,))


class DeleteView(BaseDeleteView):
    def get_template_names(self):
        templates = super(DeleteView, self).get_template_names()
        templates.append('bootstrap/delete.html')
        return templates

    def delete(self, *args, **kwargs):
        instance = self.get_object()
        verbose_name = self._get_model_verbose_name()[0]
        messages.success(self.request, '%s "%s" deleted' % (verbose_name, instance))
        return super(DeleteView, self).delete(*args, **kwargs)

    def _get_model_verbose_name(self):
        model_meta = self.model._meta

        return (model_meta.verbose_name,
                model_meta.verbose_name_plural)

    def get_context_data(self, **kwargs):
        context = super(DeleteView, self).get_context_data(**kwargs)

        model_meta = self.model._meta

        context['model_verbose_name'] = model_meta.verbose_name
        context['model_verbose_name_plural'] = model_meta.verbose_name_plural

        context['success_url'] = self.get_success_url()

        return context

    def get_success_url(self):
        model_meta = self.model._meta

        app_label = model_meta.app_label
        name = model_meta.object_name.lower()

        return reverse('%s:%s_list' % (app_label, name))

########NEW FILE########
__FILENAME__ = forms
from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.core.urlresolvers import reverse


class Contact(models.Model):
    name = models.CharField(max_length=255,
                            verbose_name='Name')
    email = models.EmailField(blank=True,
                              null=True)
    phone = models.CharField(max_length=255,
                             blank=True,
                             null=True)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('contact_list:contact_form', args=(self.pk,))

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from bootstrap.urls import bootstrap_patterns

from contact_list.forms import ContactForm


urlpatterns = bootstrap_patterns(ContactForm)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

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
# Django settings for test_app project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
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
SECRET_KEY = '(o41d^lvnulotlu$d+mf_%@!nhaqc0$^$_4&&y486-tut(zl*#'

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

ROOT_URLCONF = 'test_app.urls'

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
    'bootstrap',
    'contact_list',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
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
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_app.views.home', name='home'),
    # url(r'^test_app/', include('test_app.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url('^', include('contact_list.urls', namespace='contact_list')),
)

########NEW FILE########
