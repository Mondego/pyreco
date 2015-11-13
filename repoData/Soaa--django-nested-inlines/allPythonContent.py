__FILENAME__ = admin
from django.contrib import admin
from nested_inlines.admin import NestedModelAdmin, NestedTabularInline, NestedStackedInline

from models import A, B, C

class CInline(NestedTabularInline):
    model = C

class BInline(NestedStackedInline):
    model = B
    inlines = [CInline,]
    
class AAdmin(NestedModelAdmin):
    inlines = [BInline,]

admin.site.register(A, AAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models

class A(models.Model):
    name = models.CharField("name", max_length=255)

class B(models.Model):
    a = models.ForeignKey(A)
    name = models.CharField("name", max_length=255)
    
class C(models.Model):
    b = models.ForeignKey(B)
    name = models.CharField("name", max_length=255)
########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for example project.
import os, manage
gettext = lambda s: s
PROJECT_PATH = os.path.abspath(os.path.dirname(manage.__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_PATH, 'example.db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en//ref/settings/#allowed-hosts
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
SECRET_KEY = 'q2r=q_6z+h8$wvqu1g=1a+%l!6lqpiv3i-!js^y66-89be#3h^'

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
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'nested_inlines',
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'example',
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

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example.views.home', name='home'),
    # url(r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
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
__FILENAME__ = admin
from django.contrib.admin.options import (ModelAdmin, InlineModelAdmin,
    csrf_protect_m, models, transaction, all_valid,
    PermissionDenied, unquote, escape, Http404, reverse)
# Fix to make Django 1.5 compatible, maintain backwards compatibility
try:
    from django.contrib.admin.options import force_unicode
except ImportError:
    from django.utils.encoding import force_unicode

from django.contrib.admin.helpers import InlineAdminFormSet, AdminForm
from django.utils.translation import ugettext as _

from forms import BaseNestedModelForm, BaseNestedInlineFormSet
from helpers import AdminErrorList

class NestedModelAdmin(ModelAdmin):
    class Media:
        css = {'all': ('admin/css/nested.css',)}
        js = ('admin/js/nested.js',)
        
    def get_form(self, request, obj=None, **kwargs):
        return super(NestedModelAdmin, self).get_form(
            request, obj, form=BaseNestedModelForm, **kwargs)
        
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not (inline.has_add_permission(request) or
                        inline.has_change_permission(request, obj) or
                        inline.has_delete_permission(request, obj)):
                    continue
                if not inline.has_add_permission(request):
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances
    
    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        formset.save()
        
        #iterate through the nested formsets and save them
        #skip formsets, where the parent is marked for deletion
        deleted_forms = formset.deleted_forms
        for form in formset.forms:
            if hasattr(form, 'nested_formsets') and form not in deleted_forms:
                for nested_formset in form.nested_formsets:
                    self.save_formset(request, form, nested_formset, change)
                    
    def add_nested_inline_formsets(self, request, inline, formset, depth=0):
        if depth > 5:
            raise Exception("Maximum nesting depth reached (5)")
        for form in formset.forms:
            nested_formsets = []
            for nested_inline in inline.get_inline_instances(request):
                InlineFormSet = nested_inline.get_formset(request, form.instance)
                prefix = "%s-%s" % (form.prefix, InlineFormSet.get_default_prefix())
                
                #because of form nesting with extra=0 it might happen, that the post data doesn't include values for the formset.
                #This would lead to a Exception, because the ManagementForm construction fails. So we check if there is data available, and otherwise create an empty form
                keys = request.POST.keys()
                has_params = any(s.startswith(prefix) for s in keys)
                if request.method == 'POST' and has_params:
                    nested_formset = InlineFormSet(request.POST, request.FILES,
                                                   instance=form.instance,
                                                   prefix=prefix, queryset=nested_inline.queryset(request))
                else:
                    nested_formset = InlineFormSet(instance=form.instance,
                                                   prefix=prefix, queryset=nested_inline.queryset(request))
                nested_formsets.append(nested_formset)
                if nested_inline.inlines:
                    self.add_nested_inline_formsets(request, nested_inline, nested_formset, depth=depth+1)
            form.nested_formsets = nested_formsets
            
    def wrap_nested_inline_formsets(self, request, inline, formset):
        """wraps each formset in a helpers.InlineAdminFormset.
        @TODO someone with more inside knowledge should write done why this is done
        """
        media = None
        def get_media(extra_media):
            if media:
                return media + extra_media
            else:
                return extra_media
                        
        for form in formset.forms:
            wrapped_nested_formsets = []
            for nested_inline, nested_formset in zip(inline.get_inline_instances(request), form.nested_formsets):
                if form.instance.pk:
                    instance = form.instance
                else:
                    instance = None
                fieldsets = list(nested_inline.get_fieldsets(request))
                readonly = list(nested_inline.get_readonly_fields(request))
                prepopulated = dict(nested_inline.get_prepopulated_fields(request))
                wrapped_nested_formset = InlineAdminFormSet(nested_inline, nested_formset,
                    fieldsets, prepopulated, readonly, model_admin=self)
                wrapped_nested_formsets.append(wrapped_nested_formset)
                media = get_media(wrapped_nested_formset.media)
                if nested_inline.inlines:
                    media = get_media(self.wrap_nested_inline_formsets(request, nested_inline, nested_formset))
            form.nested_formsets = wrapped_nested_formsets
        return media
    
    def all_valid_with_nesting(self, formsets):
        """Recursively validate all nested formsets
        """
        if not all_valid(formsets):
            return False
        for formset in formsets:
            if not formset.is_bound:
                pass
            for form in formset:
                if hasattr(form, 'nested_formsets'):
                    if not self.all_valid_with_nesting(form.nested_formsets):
                        return False
        return True
    
    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied

        ModelForm = self.get_form(request)
        formsets = []
        inline_instances = self.get_inline_instances(request, None)
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.model()
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new="_saveasnew" in request.POST,
                                  prefix=prefix, queryset=inline.queryset(request))
                formsets.append(formset)
                if inline.inlines:
                    self.add_nested_inline_formsets(request, inline, formset)
            if self.all_valid_with_nesting(formsets) and form_validated:
                self.save_model(request, new_object, form, False)
                self.save_related(request, form, formsets, False)
                self.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)
                if inline.inlines:
                    self.add_nested_inline_formsets(request, inline, formset)

        adminForm = AdminForm(form, list(self.get_fieldsets(request)),
            self.get_prepopulated_fields(request),
            self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            prepopulated = dict(inline.get_prepopulated_fields(request))
            inline_admin_formset = InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
            if inline.inlines:
                media = media + self.wrap_nested_inline_formsets(request, inline, formset)

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'show_delete': False,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=True)

    @csrf_protect_m
    @transaction.commit_on_success
    def change_view(self, request, object_id, form_url='', extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        if request.method == 'POST' and "_saveasnew" in request.POST:
            return self.add_view(request, form_url=reverse('admin:%s_%s_add' %
                                    (opts.app_label, opts.module_name),
                                    current_app=self.admin_site.name))

        ModelForm = self.get_form(request, obj)
        formsets = []
        inline_instances = self.get_inline_instances(request, obj)
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, new_object), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)
                if inline.inlines:
                    self.add_nested_inline_formsets(request, inline, formset)

            if self.all_valid_with_nesting(formsets) and form_validated:
                self.save_model(request, new_object, form, True)
                self.save_related(request, form, formsets, True)
                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                return self.response_change(request, new_object)

        else:
            form = ModelForm(instance=obj)
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, obj), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)
                if inline.inlines:
                    self.add_nested_inline_formsets(request, inline, formset)

        adminForm = AdminForm(form, self.get_fieldsets(request, obj),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            prepopulated = dict(inline.get_prepopulated_fields(request, obj))
            inline_admin_formset = InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media
            if inline.inlines:
                media = media + self.wrap_nested_inline_formsets(request, inline, formset)

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj, form_url=form_url)

class NestedInlineModelAdmin(InlineModelAdmin):
    inlines = []
    formset = BaseNestedInlineFormSet

    def get_form(self, request, obj=None, **kwargs):
        return super(NestedModelAdmin, self).get_form(
            request, obj, form=BaseNestedModelForm, **kwargs)
    
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not (inline.has_add_permission(request) or
                        inline.has_change_permission(request, obj) or
                        inline.has_delete_permission(request, obj)):
                    continue
                if not inline.has_add_permission(request):
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances
    
    def get_formsets(self, request, obj=None):
        for inline in self.get_inline_instances(request):
            yield inline.get_formset(request, obj)

class NestedStackedInline(NestedInlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'
    
class NestedTabularInline(NestedInlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'

########NEW FILE########
__FILENAME__ = forms
from django.forms.forms import BaseForm, ErrorDict
from django.forms.models import ModelForm, BaseInlineFormSet

class NestedFormMixin(object):
    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors and
        self.cleaned_data.
        """
        self._errors = ErrorDict()
        if not self.is_bound: # Stop further processing.
            return
        self.cleaned_data = {}
        # If the form is permitted to be empty, and none of the form data has
        # changed from the initial data, short circuit any validation.
        if self.empty_permitted and not self.has_changed() and not self.dependency_has_changed():
            return
        self._clean_fields()
        self._clean_form()
        self._post_clean()
    
    def dependency_has_changed(self):
        """
        Returns true, if any dependent form has changed.
        This is needed to force validation, even if this form wasn't changed but a dependent form
        """
        return False

class BaseNestedForm(NestedFormMixin, BaseForm):
    pass

class NestedFormSetMixin(object):
    def dependency_has_changed(self):
        for form in self.forms:
            if form.has_changed() or form.dependency_has_changed():
                return True
        return False

class BaseNestedInlineFormSet(NestedFormSetMixin, BaseInlineFormSet):
    pass

class NestedModelFormMixin(NestedFormMixin):
    def dependency_has_changed(self):
        #check for the nested_formsets attribute, added by the admin app.
        #TODO this should be generalized
        if hasattr(self, 'nested_formsets'):
            for f in self.nested_formsets:
                return f.dependency_has_changed()
            
class BaseNestedModelForm(NestedModelFormMixin, ModelForm):
    pass
########NEW FILE########
__FILENAME__ = helpers
from django.contrib.admin.helpers import AdminErrorList, InlineAdminFormSet
from django.utils import six

class AdminErrorList(AdminErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        if form.is_bound:
            self.extend(form.errors.values())
            for inline_formset in inline_formsets:
                self._add_formset_recursive(inline_formset)
                    
    def _add_formset_recursive(self, formset):
        #check if it is a wrapped formset
        if isinstance(formset, InlineAdminFormSet):
            formset = formset.formset
            
        self.extend(formset.non_form_errors())
        for errors_in_inline_form in formset.errors:
            self.extend(list(six.itervalues(errors_in_inline_form)))
        
        #support for nested formsets
        for form in formset:
            if hasattr(form, 'nested_formsets'):
                for fs in form.nested_formsets:
                    self._add_formset_recursive(fs)
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
