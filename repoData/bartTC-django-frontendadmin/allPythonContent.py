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
import sys, os

# Quick hack to put frontendadmin from the parent directory into pythonpath
# If this is not working correctly, uncomment these lines and put
# frontendadmin manually into pythonpath.
sys.path.append(
    os.path.abspath(
        os.path.normpath('%s/../' % os.path.dirname(__file__))
    )
)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'myproject.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'site_media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/site_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '^6qlxq*maky)*u!fl+!_97m^zcywod0c)tujsm5+fngj1+y55x'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.flatpages',

    # Put frontendadmin before your applications, so that they can overwrite
    # the frontendadmin templates.
    'frontendadmin',
    'example_project.weblog',
)

# Define custom forms to handle any model
FRONTEND_FORMS = {
    # ``app_label.model_name`` : ``form_class``,
    'weblog.entry': 'weblog.forms.EntryForm',
}

# Define which fields to exclude on a particular model
FRONTEND_EXCLUDES = {
    # ``app_label.model_name`` : ``tuple``,
    'weblog.entry': ('public',),
}

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

from example_project.weblog.models import Entry

admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$',
        'django.views.generic.list_detail.object_list', {
            'queryset': Entry.objects.filter(public=True).order_by('-published'),
            'template_name': 'weblog_overview.html',
        }, name='weblog_index'
    ),

    url(r'^entry-(?P<object_id>[\d]+)/$',
        'django.views.generic.list_detail.object_detail', {
            'queryset': Entry.objects.filter(public=True).order_by('-published'),
            'template_name': 'weblog_details.html',
        }, name='weblog_details'
    ),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^admin/', include(admin.site.urls)),

    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)

'''
This example shows, howto set fields for a specific app_label and/or model_name.
Yes, this is ugly. I try to change this behaviour in future. So expect backwards
incompatible changes.
'''
urlpatterns += patterns('',
    (
        # Override frontendadmin url for specific app_label, mode_name
        r'^frontendadmin/change/(?P<app_label>flatpages)/(?P<model_name>flatpage)/(?P<instance_id>[\d]+)/$',

        # Point it to the view (either add, change or delete)
        'frontendadmin.views.change',

        # Provide extra arguments
        {
            # Fields to include
            'form_fields': ('title', 'content'),

            # And/Or fields to exclude
            #'form_exclude': ('title', 'content'),
        }
    ),
)


'''
This is the default frontendadmin inclusion and a fallback for all frontendadmin
links not overwritten above.
'''
urlpatterns += patterns('',
    (r'^frontendadmin/', include('frontendadmin.urls')),
)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from models import Entry
from django.contrib.admin import widgets                                       


class EntryForm(forms.ModelForm):
    published = forms.CharField(widget=widgets.AdminSplitDateTime())
    
    def clean_published(self):
        """
        Join the split admin format into a single DateTime stamp
        turn "[u'2008-10-04', u'05:28:08']" into 2008-10-04 05:28:08
        """
        return filter(lambda c: not c in "u[],\'", self.cleaned_data['published'])
    
    class Meta:
        model = Entry

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db.models import permalink
from django.db import models

class Entry(models.Model):
    title = models.CharField(max_length=50)
    content = models.TextField()
    published = models.DateTimeField(default=datetime.datetime.now)
    public = models.BooleanField(default=True)
        
    class Meta:
        verbose_name = u'Weblog Entry'
        verbose_name_plural = u'Weblog Entries'

    def __unicode__(self):
        return self.title

    @permalink
    def get_absolute_url(self):
        return ('weblog_details', (str(self.pk),))


########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

class FrontendAdminModelForm(forms.ModelForm):
    pass

class DeleteRequestForm(forms.Form):
    do_delete = forms.BooleanField(
        label=_(u'Yes, delete this object'),
        required=True,
    )
########NEW FILE########
__FILENAME__ = frontendadmin_tags
from django import template
from django.db.models import Model
from django.db.models.query import QuerySet
from django.core.urlresolvers import reverse
from frontendadmin.views import check_permission
 
register = template.Library()
 
@register.inclusion_tag('frontendadmin/link_add.html', takes_context=True)
def frontendadmin_add(context, queryset_object, label=None):
 
    # Check if `queryset_object` is a queryset
    if not isinstance(queryset_object, QuerySet):
        raise template.TemplateSyntaxError, "'%s' argument must be a queryset" % queryset_object
 
    app_label = queryset_object.model._meta.app_label
    model_name = queryset_object.model._meta.module_name
 
    template_context = {
        'add_link': reverse('frontendadmin_add', kwargs={
            'app_label': app_label,
            'model_name': model_name,
        }),
        'next_link': context['request'].META['PATH_INFO'],
        'label': label,
    }
 
    # Check for permission
    if check_permission(request=context['request'], mode_name='add',
                                                    app_label=app_label,
                                                    model_name=model_name):
        template_context['has_permission'] = True
    else:
        template_context['has_permission'] = False
    context.update(template_context)
    return context
 
@register.inclusion_tag('frontendadmin/link_edit.html', takes_context=True)
def frontendadmin_change(context, model_object, label=None):
 
    # Check if `model_object` is a model-instance
    if not isinstance(model_object, Model):
        raise template.TemplateSyntaxError, "'%s' argument must be a model-instance" % model_object
 
    app_label = model_object._meta.app_label
    model_name = model_object._meta.module_name
 
    template_context = {
        'edit_link': reverse('frontendadmin_change', kwargs={
            'app_label': app_label,
            'model_name': model_name,
            'instance_id': model_object.pk,
        }),
        'next_link': context['request'].META['PATH_INFO'],
        'label': label,
    }
 
    # Check for permission
    if check_permission(request=context['request'], mode_name='change',
                                                    app_label=app_label,
                                                    model_name=model_name):
        template_context['has_permission'] = True
    else:
        template_context['has_permission'] = False
    context.update(template_context)
    return context
 
@register.inclusion_tag('frontendadmin/link_delete.html', takes_context=True)
def frontendadmin_delete(context, model_object, label=None):
 
    # Check if `model_object` is a model-instance
    if not isinstance(model_object, Model):
        raise template.TemplateSyntaxError, "'%s' argument must be a model-instance" % model_object
 
    app_label = model_object._meta.app_label
    model_name = model_object._meta.module_name
 
    template_context = {
        'delete_link': reverse('frontendadmin_delete', kwargs={
            'app_label': app_label,
            'model_name': model_name,
            'instance_id': model_object.pk,
        }),
        'next_link': context['request'].META['PATH_INFO'],
        'label': label,
    }
 
    # Check for permission
    if check_permission(request=context['request'], mode_name='delete',
                                                    app_label=app_label,
                                                    model_name=model_name):
        template_context['has_permission'] = True
    else:
        template_context['has_permission'] = False
    context.update(template_context)
    return context
 
@register.inclusion_tag('frontendadmin/common.css')
def frontendadmin_common_css():
    return {}
 
@register.inclusion_tag('frontendadmin/common.js')
def frontendadmin_common_js():
    return {}
    

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from frontendadmin.views import add, change, delete, success, success_delete
from django.views.decorators.cache import never_cache

urlpatterns = patterns('',
    url(r'^add/(?P<app_label>[\w]+)/(?P<model_name>[\w]+)/$',
        never_cache(add),
        name='frontendadmin_add'
    ),

    url(r'^change/(?P<app_label>[\w]+)/(?P<model_name>[\w]+)/(?P<instance_id>[\d]+)/$',
        never_cache(change),
        name='frontendadmin_change'
    ),

    url(r'^delete/(?P<app_label>[\w]+)/(?P<model_name>[\w]+)/(?P<instance_id>[\d]+)/$',
        never_cache(delete),
        name='frontendadmin_delete'
    ),

    url(r'^success/$',
        success,
        name='frontendadmin_success'
    ),

    url(r'^success_delete/$',
        success_delete,
        name='frontendadmin_success_delete'
    ),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.contrib.admin import site
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.utils.importlib import import_module
from django.conf import settings
from django.forms import CharField
from django.contrib import messages

from forms import DeleteRequestForm, FrontendAdminModelForm


EXCLUDES = getattr(settings, 'FRONTEND_EXCLUDES', {})
FIELDS = getattr(settings, 'FRONTEND_FIELDS', {})
FORMS = getattr(settings, 'FRONTEND_FORMS', {})

def import_function(s):
    """
    Import a function given the string formatted as
    `module_name.function_name`  (eg `django.utils.text.capfirst`)
    """
    a = s.split('.')
    j = lambda x: '.'.join(x)
    return getattr(import_module(j(a[:-1])), a[-1])

def check_permission(request, mode_name, app_label, model_name):
    '''
    Check for proper permissions. mode_name may be either add, change or delete.
    '''
    p = '%s.%s_%s' % (app_label, mode_name, model_name)
    return request.user.is_active and request.user.has_perm(p)

def _get_instance(request, mode_name, app_label, model_name, instance_id=None,
                                            form=None,
                                            form_fields=None,
                                            form_exclude=None):
    '''
    Returns the model and an instance_form for the given arguments. If an primary
    key (instance_id) is given, it will return also the instance.

    If the user has no permission to add, change or delete the object, a
    HttpResponse is returned.
    '''
    # Check for permission to add/change/delete this object
    if not check_permission(request, mode_name, app_label, model_name):
        return HttpResponseForbidden('You have no permission to do this!')

    try:
        model = get_model(app_label, model_name)
    # Model does not exist
    except AttributeError:
        return HttpResponseForbidden('This model does not exist!')
    label = '%s.%s' % (app_label, model_name)
    # get form for model
    if label in FORMS and not form:
        form = import_function(FORMS[label])
    elif model in site._registry and not form:
        form = site._registry[model].form
    elif form is None:
        form = FrontendAdminModelForm
    
    if label in EXCLUDES:
        form_exclude = EXCLUDES[label]
    if label in FIELDS:
        form_fields = FIELDS[label]

    instance_form = modelform_factory(model, form=form,
                                      fields=form_fields, exclude=form_exclude)
    # if instance_id is set, grab this model object
    if instance_id:
        instance = model.objects.get(pk=instance_id)
        return model, instance_form, instance
    return model, instance_form


def _handle_cancel(request, instance=None):
    '''
    Handles clicks on the 'Cancel' button in forms. Returns a redirect to the
    last page, the user came from. If not given, to the detail-view of
    the object. Last fallback is a redirect to the common success page.
    '''
    if request.POST.get('_cancel', False):
        if request.GET.get('next', False):
            return HttpResponseRedirect(request.GET.get('next'))
        if instance and hasattr(instance, 'get_absolute_url'):
            return HttpResponseRedirect(instance.get_absolute_url())
        return HttpResponseRedirect(reverse('frontendadmin_success'))
    return None

def _handle_response(request, instance=None):
    '''
    Handles redirects for completet form actions. Returns a redirect to the
    last page, the user came from. If not given, to the detail-view of
    the object. Last fallback is a redirect to the common success page.
    '''
    if 'next' in request.REQUEST:
        return HttpResponseRedirect(request.REQUEST['next'])
    if instance and hasattr(instance, 'get_absolute_url'):
        return HttpResponseRedirect(instance.get_absolute_url())
    return HttpResponseRedirect(reverse('frontendadmin_success'))

def _find_template(template_name, app_label=None, model_name=None):
    """
    Finds a template_name for the given, optional ``app_label`` . ``model_name``
    """
    if app_label is None and model_name is None:
        return 'frontendadmin/%s' % template_name
    
    try:
        name = 'frontendadmin/%s_%s_%s' % (app_label, model_name, template_name)
        get_template(name)
        return name
    except TemplateDoesNotExist:
        return 'frontendadmin/%s' % template_name

def _get_template(request, app_label=None, model_name=None):
    '''
    Returns wether the ajax or the normal (full blown) template.
    '''
    return _find_template(request.is_ajax() and 'form_ajax.html' or 'form.html',
        app_label, model_name)
    
@never_cache
@login_required
def add(request, app_label, model_name, mode_name='add',
                            form_fields=None,
                            form_exclude=None):

    # Get model, instance_form and instance for arguments
    instance_return = _get_instance(request, mode_name, app_label, model_name,
                                                                   form_fields=form_fields,
                                                                   form_exclude=form_exclude)
    if isinstance(instance_return, HttpResponseForbidden):
        return instance_return
    model, instance_form = instance_return

    # Handle cancel request
    cancel = _handle_cancel(request)
    if cancel:
        return cancel
    if request.method == 'POST':
        form = instance_form(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()
            # Give the user a nice message
            msg=_(u'Your %(model_name)s was added successfully') % \
                                {'model_name': model._meta.verbose_name}           
            try:
                request.user.message_set.create(message=msg)
            except AttributeError:
                messages.success(request, msg)
            # Return to last page
            if request.is_ajax():
                return success(request)
            return _handle_response(request, instance)
    else:
        form = instance_form()
    template_context = {
        'action': 'add',
        'action_url': request.get_full_path(),
        'model_title': model._meta.verbose_name,
        'form': form
    }
    return render_to_response(
        _get_template(request, app_label, model_name),
        template_context,
        RequestContext(request)
    )

@never_cache
@login_required
def change(request, app_label, model_name, instance_id, mode_name='change',
                                           form_fields=None,
                                           form_exclude=None):

    # Get model, instance_form and instance for arguments
    instance_return = _get_instance(request, mode_name, app_label, model_name,
                                                           instance_id,
                                                           form_fields=form_fields,
                                                           form_exclude=form_exclude)
    if isinstance(instance_return, HttpResponseForbidden):
        return instance_return
    model, instance_form, instance = instance_return

    # Handle cancel request
    cancel = _handle_cancel(request)
    if cancel:
        return cancel

    if request.method == 'POST':
        form = instance_form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            instance = form.save()
            msg=_(u'Your %(model_name)s was changed successfully') % \
                                {'model_name': model._meta.verbose_name}           
            # Give the user a nice message
            try:
                request.user.message_set.create(message=msg)
            except AttributeError:
                messages.success(request, msg)
                
            # Return to success page
            if request.is_ajax():
                return success(request)
            return _handle_response(request, instance)
    else:
        form = instance_form(instance=instance)

    template_context = {
        'action': 'change',
        'action_url': request.get_full_path(),
        'model_title': model._meta.verbose_name,
        'form': form,
    }

    return render_to_response(
        _get_template(request, app_label, model_name),
        template_context,
        RequestContext(request)
    )


@never_cache
@login_required
def delete(request, app_label, model_name, instance_id,
                               delete_form=DeleteRequestForm):

    # Get model, instance_form and instance for arguments
    instance_return = _get_instance(request, 'delete', app_label, model_name, instance_id)
    if isinstance(instance_return, HttpResponseForbidden):
        return instance_return
    model, instance_form, instance = instance_return

    # Handle cancel request
    cancel = _handle_cancel(request)
    if cancel:
        return cancel

    if request.method == 'POST':
        form = delete_form(request.POST)
        if form.is_valid():
            instance.delete()
            # Give the user a nice message
            
            msg=_(u'Your %(model_name)s was deleted.') % \
                    {'model_name': model._meta.verbose_name}
            try:
                request.user.message_set.create(message=msg)
            except AttributeError:
                messages.success(request, msg)    
                
            # Return to last page
            if request.is_ajax():
                return success_delete(request)
            return _handle_response(request, instance)

    else:
        form = delete_form()

    template_context = {
        'action': 'delete',
        'action_url': request.get_full_path(),
        'model_title': model._meta.verbose_name,
        'form': form,
    }

    return render_to_response(
        _get_template(request, None, None),
        template_context,
        RequestContext(request)
    )

def success(request, template_name='success.html', template_ajax='success_ajax.html'):
    '''
    First, a view would redirect to the last page the user came from. If
    this is not available (because somebody fiddled in the url), we redirect
    to this common success page.

    Normally a user should never see this page.
    '''
    template = _find_template(request.is_ajax() and template_ajax or template_name)
    return render_to_response(template, {}, RequestContext(request))


def success_delete(request, template_name='success_delete.html', template_ajax='success_delete_ajax.html'):
    '''
    Normally a view would redirect to the last page. After delete from a object
    in a detail-view, there is no "last page" so we redirect to a unique, shiny
    success-page.
    '''
    template = _find_template(request.is_ajax() and template_ajax or template_name)
    return render_to_response(template, {}, RequestContext(request))


########NEW FILE########
