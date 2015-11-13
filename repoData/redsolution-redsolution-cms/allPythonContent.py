__FILENAME__ = admin
from django import template
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms.formsets import all_valid
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from redsolutioncms.models import CMSSettings, CMSPackage, CMSEntryPoint, \
    CMSCreatedModel, ProcessTask

try:
    admin.site.register(CMSSettings)
except admin.sites.AlreadyRegistered:
    pass

class CMSEntryPointInline(admin.TabularInline):
    model = CMSEntryPoint

class CMSPackageForm(admin.ModelAdmin):
    model = CMSPackage
    inlines = [CMSEntryPointInline]

try:
    admin.site.register(CMSPackage, CMSPackageForm)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(CMSCreatedModel)
except admin.sites.AlreadyRegistered:
    pass

HORIZONTAL, VERTICAL = 1, 2
# returns the <ul> class for a given radio_admin field
get_ul_class = lambda x: 'radiolist%s' % ((x == HORIZONTAL) and ' inline' or '')


class CMSBaseAdmin(admin.ModelAdmin):

    def __init__(self):
        self.opts = self.model._meta
        self.admin_site = None
        self.inline_instances = []
        for inline_class in self.inlines:
            inline_instance = inline_class(self.model, self.admin_site)
            self.inline_instances.append(inline_instance)
        if 'action_checkbox' not in self.list_display and self.actions is not None:
            self.list_display = ['action_checkbox'] + list(self.list_display)
        if not self.list_display_links:
            for name in self.list_display:
                if name != 'action_checkbox':
                    self.list_display_links = [name]
                    break
        super(CMSBaseAdmin, self).__init__(self.model, self.admin_site)

    # Redefine urls for views
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = patterns('',
            url(r'^(.+)/$', self.change_view, name='%s_%s_change' % info),
        )
        return urlpatterns

    def change_view(self, request, **kwargs):
        "The 'change' admin view for this model"
        model = self.model
        opts = model._meta

        try:
            obj = self.model.objects.get_settings()
        except model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to be able
            # to determine whether a given object exists.
            obj = None

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(kwargs.get('object_id', ''))})

        if request.method == 'POST' and request.POST.has_key("_saveasnew"):
            return self.add_view(request, form_url='../add/')

        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet in self.get_formsets(request, new_object):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix)
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)

                self.construct_change_message(request, form, formsets)
                return self.response_change(request, new_object)

        else:
            form = ModelForm(instance=obj)
            prefixes = {}
            for FormSet in self.get_formsets(request, obj):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix)
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, self.get_fieldsets(request, obj), self.prepopulated_fields)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset, fieldsets)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'original': obj,
            'is_popup': request.REQUEST.has_key('_popup'),
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        return self.render_change_form(request, context, change=True, obj=obj)
    change_view = transaction.commit_on_success(change_view)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        opts = self.model._meta
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
        })
        context_instance = template.RequestContext(request)
        return render_to_response(self.change_form_template or [
            "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "admin/%s/change_form.html" % app_label,
            "admin/change_form.html"
        ], context, context_instance=context_instance)

    def response_change(self, request, obj):
        ''' No messages, no continues'''
        return HttpResponseRedirect(reverse('custom'))

class ProcessTaskAdmin(admin.ModelAdmin):
    list_display = ('task', 'pid')
    pass

admin.site.register(ProcessTask, ProcessTaskAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from redsolutioncms.models import CMSSettings, CMSEntryPoint, Category

class FrontpageForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(FrontpageForm, self).__init__(*args, **kwargs)
        self.fields['frontpage'] = forms.ChoiceField(
            label=_('Choose frontpage handler'),
            choices=self.get_fronpage_handlers(),
        )

    def get_fronpage_handlers(self):
        installed_packages = CMSSettings.objects.get_settings().packages.installed()
        handlers = []
        for package in installed_packages:
            for entry_point in package.entry_points.frontpage_handlers():
                handlers.append((entry_point.module, package.verbose_name),)
        return handlers

    def save(self):
        '''Write frontpage setting to global CMS settings'''
        entry_point = CMSEntryPoint.objects.get(module=self.cleaned_data['frontpage'])
        cms_settings = CMSSettings.objects.get_settings()
        cms_settings.frontpage_handler = entry_point
        cms_settings.save()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['id']

    def __init__(self, *args, **kwds):
        super(CategoryForm, self).__init__(*args, **kwds)
        category = self.instance
        if category.name == 'templates':
            self.fields['template'] = forms.ChoiceField(
                label=_('Template'),
                widget=forms.RadioSelect,
                choices=[(package.id, package.screenshot) for package in category.packages.all()],
                required=False,
            )
        else:
            for package in category.packages.all():
                self.fields['package_%s' % package.id] = forms.BooleanField(
                    label=_(package.verbose_name), required=False, help_text=_(package.description))

    def clean(self):
        if self.instance.name == 'templates':
            template_id = self.cleaned_data.get('template', '')
            if not self.instance.packages.filter(id__in=template_id).count():
                raise forms.ValidationError(_('You must select only one package from this category'))
        else:
            packages = self.cleaned_data.keys()
            packages.remove('id')
            package_ids = [p.replace('package_', '') for p in packages
                if self.cleaned_data[p]]
            if self.instance.required:
                if not self.instance.packages.filter(id__in=package_ids).count():
                    raise forms.ValidationError(_('You must select at least one package from this category'))
        return self.cleaned_data

    def save(self, *args, **kwds):
        if self.instance.name == 'templates':
            package_ids = [self.cleaned_data.get('template', ''), ]
        else:
            packages = self.cleaned_data.keys()
            packages.remove('id')
            package_ids = [p.replace('package_', '') for p in packages
                if self.cleaned_data[p]]
        # select:
        self.instance.packages.filter(id__in=package_ids).update(selected=True)
        # unselect others:
        self.instance.packages.exclude(id__in=package_ids).update(selected=False)
        super(CategoryForm, self).save(*args, **kwds)


class UserCreationForm(forms.Form):
    username = forms.RegexField(label=_("Username"), max_length=30, regex=r'^\w+$',
        help_text=_("Required. 30 characters or fewer. Alphanumeric characters only (letters, digits and underscores)."),
        error_message=_("This value must contain only letters, numbers and underscores."), initial='admin')
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput)
    email = forms.EmailField(label=_("E-mail"), max_length=75, initial='admin@example.com')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

########NEW FILE########
__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser(
    'This is a custom version of the zc.buildout %prog script.  It is '
    'intended to meet a temporary need if you encounter problems with '
    'the zc.buildout 1.5 release.')
parser.add_option("-v", "--version", dest="version", default='1.4.4',
                          help='Use a specific zc.buildout version.  *This '
                          'bootstrap script defaults to '
                          '1.4.4, unlike usual buildpout bootstrap scripts.*')
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

env = dict(os.environ,
           PYTHONPATH=
           ws.find(pkg_resources.Requirement.parse(requirement)).location
           )

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(tmpeggs)]

if 'bootstrap-testing-find-links' in os.environ:
    cmd.extend(['-f', os.environ['bootstrap-testing-find-links']])

cmd.append('zc.buildout' + VERSION)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else: # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
assert exitcode == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)
########NEW FILE########
__FILENAME__ = extrapath_additional


########NEW FILE########
__FILENAME__ = settings_additional
#
########NEW FILE########
__FILENAME__ = urls_additional
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = importpath
from django.core.exceptions import ImproperlyConfigured

def importpath(path, error_text=None):
    """
    Import value by specified ``path``.
    Value can represent module, class, object, attribute or method.
    If ``error_text`` is not None and import will
    raise ImproperlyConfigured with user friendly text.
    """
    result = None
    attrs = []
    parts = path.split('.')
    exception = None
    while parts:
        try:
            result = __import__('.'.join(parts), {}, {}, [''])
        except ImportError, e:
            if exception is None:
                exception = e
            attrs = parts[-1:] + attrs
            parts = parts[:-1]
        else:
            break
    for attr in attrs:
        try:
            result = getattr(result, attr)
        except (AttributeError, ValueError), error:
            if error_text is not None:
                raise ImproperlyConfigured('Error: %s can import "%s"' % (error_text, path))
            else:
                if exception is None:
                    raise ImportError(path)
                raise exception
    return result

########NEW FILE########
__FILENAME__ = loader
#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import shutil
import sys
import subprocess
from os import remove, listdir
from os.path import join, dirname, exists, abspath
from optparse import OptionParser


# Home dir defined here!
if os.sys.platform == 'win32':
    home_dir = join(os.getenv('USERPROFILE'), '.redsolutioncms')
else:
    home_dir = join(os.getenv('HOME'), '.redsolutioncms')
project_dir = os.getcwd()
project_dir = project_dir.decode(sys.getfilesystemencoding())
home_dir = home_dir.decode(sys.getfilesystemencoding())

def install_in_home():
    '''Copy nessesary files to home folder''' 
    # check target dir doesn't exists
    import redsolutioncms
    if exists(home_dir):
        # Delete downloaded libraries
        if exists(join(home_dir, 'eggs')):
            shutil.rmtree(join(home_dir, 'eggs'))
        # Delete all files copied from home
        for filename in listdir(join(dirname(redsolutioncms.__file__), 'home')):
            path = join(home_dir, filename)
            if exists(path):
                remove(path)
        if exists(join(home_dir, 'cms.sqlite')):
            remove(join(home_dir, 'cms.sqlite'))
        # delete *.pyc files
        for filename in listdir(home_dir):
            if '.pyc' in filename:
                remove(join(home_dir, filename))
    else:
        os.mkdir(home_dir)

    for filename in listdir(join(dirname(redsolutioncms.__file__), 'home')):
        src = join(dirname(redsolutioncms.__file__), 'home', filename)
        shutil.copy(src, home_dir)

def run_cmd(cmd, cmd_dict=None):
    # I splitted this function in two for API usage in CMS task system
    cmd = process_cmd_string(cmd, cmd_dict)
    run_in_home(cmd)

def process_cmd_string(cmd, cmd_dict=None):
    if cmd_dict is None:
        cmd_dict = {}
    default_dict = {
        'python': sys.executable,
        'buildout_cfg': join(home_dir, 'buildout.cfg'),
        'bootstrap': join(home_dir, 'bootstrap.py'),
        'buildout': join(home_dir, 'bin', 'buildout'),
        'django': join(home_dir, 'bin', 'django'),
    }
    cmd_dict.update(default_dict)
    return cmd % cmd_dict

def run_in_home(cmd):
    # run python boostrap.py from home installation dir 
    cwd = os.getcwd()
#    os.chdir(home_dir)
    subprocess.call(cmd, shell=(os.sys.platform != 'win32'))
#    os.chdir(cwd)


def main():
    parser = OptionParser()
    parser.add_option('-c', '--continue', action='store_true', dest='continue_install',
        help="Continue installation, doesn't delete old files", default=False)
    parser.add_option('-t', '--test', action='store_true', dest='test',
        help="Test variables", default=False)
    
    (options, args) = parser.parse_args()
    # TODO: Find installed CMS automatically and ask user, does he want to delete old files
    
    if options.test:
        print 'Test mode'
        print 'home_dir=%s' % home_dir
        print 'project_dir=%s' % project_dir
        print process_cmd_string('python: %(python)s')
        print process_cmd_string('buildout_cfg: %(buildout_cfg)s')
        print process_cmd_string('bootstrap: %(bootstrap)s')
        print process_cmd_string('bulidout: %(buildout)s')
        print process_cmd_string('django: %(django)s')
        sys.exit(0)
    
    if not options.continue_install:
        print '1. Copying files to home dir'
        install_in_home()
        print '2. Bootstraping'
        run_cmd('"%(python)s" "%(bootstrap)s" -c "%(buildout_cfg)s"')
        print '3. Building'
        run_cmd('"%(buildout)s" -c "%(buildout_cfg)s"')
    print '4. Syncdb'
    run_cmd('"%(django)s" syncdb --noinput')
    print '5. Run wrapper'
    run_cmd('"%(django)s" wrap_runserver')

if __name__ == '__main__':
    # set path automatically
    cms_path = dirname(dirname(abspath(__file__)))
    sys.path[0:0] = [cms_path, ]
    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = cms_path
    else:
        os.environ['PYTHONPATH'] = os.path.pathsep + cms_path
    main()

########NEW FILE########
__FILENAME__ = make
import os

from redsolutioncms.models import CMSSettings
from django.conf import settings
from random import choice
from redsolutioncms.utils import prepare_fixtures
from redsolutioncms.loader import project_dir, home_dir


def copy_downloads():
    '''
    Copies downloads folder from CMS installation to project dir 
    '''
    cms_settings = CMSSettings.objects.get_settings()
    cms_settings.copy_dir(
        os.path.join(project_dir, 'downloads'),
        os.path.join(home_dir, 'downloads'),
    )

def copy_eggs():
    '''
    Copies all installed eggs info project dir
    '''
    cms_settings = CMSSettings.objects.get_settings()
    for package in cms_settings.packages.installed():
        egg_folder = package.path.rsplit(os.path.sep, 1)[1]
        cms_settings.copy_dir(
            os.path.join(project_dir, 'eggs', egg_folder),
            package.path
        )


class AlreadyMadeException(Exception):
    """
    Exception raise if function in Make class was called twice.
    """

class BaseMake(object):
    """
    Base class for all Make classes.
    You MUST call super method before any action in overridden functions.
    Functions can raise ``AlreadyMadeException`` if function was already called. 
    """
    # In customizing apps view user has selected frontpage handler.
    # this variable can be set to True in that view

    def __init__(self):
        """
        Create make object.
        """
        self.flush()

    def flush(self):
        """
        Flush all flags as if project was not made yet. 
        """
        self.premade = False
        self.made = False
        self.postmade = False

    def premake(self):
        """
        Called immediately before make() for all packages.
        """
        if self.premade:
            raise AlreadyMadeException
        self.premade = True

    def make(self):
        """
        Called to make() settings for this package.
        """
        if self.made:
            raise AlreadyMadeException
        self.made = True

    def postmake(self):
        """
        Called after all make() for all packages.
        """
        if self.postmade:
            raise AlreadyMadeException
        self.postmade = True

class Make(BaseMake):
    def premake(self):
        super(Make, self).premake()
        cms_settings = CMSSettings.objects.get_settings()
        cms_settings.render_to(os.path.join('..', 'templates', 'base_template.html'), 'redsolutioncms/project/templates/base_template.html', {}, 'w')

    def make(self):
        super(Make, self).make()
        cms_settings = CMSSettings.objects.get_settings()
        cms_settings.render_to(['..', 'buildout.cfg'], 'redsolutioncms/project/buildout.cfg',
            {'index': getattr(settings, 'CUSTOM_PACKAGE_INDEX', None)}, 'w')
        cms_settings.render_to('development.py', 'redsolutioncms/project/development.pyt', {}, 'w')
        cms_settings.render_to('production.py', 'redsolutioncms/project/production.pyt', {}, 'w')
        cms_settings.render_to('settings.py', 'redsolutioncms/project/settings.pyt', {
            'secret': ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
        }, 'w')
        cms_settings.render_to('urls.py', 'redsolutioncms/project/urls.pyt', {}, 'w')
        cms_settings.render_to('manage.py', 'redsolutioncms/project/manage.pyt', {}, 'w')
        cms_settings.render_to(os.path.join('..', 'templates', '404.html'), 'redsolutioncms/project/templates/404.html', {}, 'w')
        cms_settings.render_to(os.path.join('..', 'templates', '500.html'), 'redsolutioncms/project/templates/500.html', {}, 'w')

        cms_settings.render_to(os.path.join('..', 'fixtures', 'initial_data.json'),
            'redsolutioncms/project/fixtures/initial_data.json', {}, 'w')
#===============================================================================
# Static templates
#===============================================================================
        redsolutioncms_templates_dir = os.path.join(os.path.dirname(__file__),
            'templates', 'redsolutioncms', 'project')

        cms_settings.copy_file(
            os.path.join(cms_settings.project_dir, 'develop.cfg',),
            os.path.join(redsolutioncms_templates_dir, 'develop.cfg'),
        )
        cms_settings.copy_file(
            os.path.join(cms_settings.project_dir, 'bootstrap.py',),
            os.path.join(redsolutioncms_templates_dir, 'bootstrap.pyt'),
        )
        cms_settings.copy_file(
            os.path.join(cms_settings.project_dir, '.gitignore',),
            os.path.join(redsolutioncms_templates_dir, 'gitignore'),
        )
        cms_settings.copy_file(
            os.path.join(cms_settings.project_dir, cms_settings.project_name, '__init__.py',),
            os.path.join(redsolutioncms_templates_dir, '__init__.pyt'),
        )
        cms_settings.copy_dir(
            os.path.join(cms_settings.project_dir, 'media'),
            os.path.join(redsolutioncms_templates_dir, 'media'),
            merge=True
        )
        cms_settings.copy_dir(
            os.path.join(cms_settings.project_dir, 'templates/admin/'),
            os.path.join(redsolutioncms_templates_dir, 'templates/admin'),
            merge=True
        )
        copy_downloads()
        copy_eggs()

    def postmake(self):
        super(Make, self).postmake()
        cms_settings = CMSSettings.objects.get_settings()
        cms_settings.render_to(os.path.join('..', 'templates', 'base.html'), 'redsolutioncms/project/templates/base.html', {}, 'w')
        cms_settings.render_to('urls.py', 'redsolutioncms/project/sitemaps.pyt')

        # process initial data
        initial_data_filename = os.path.join(project_dir, 'fixtures', 'initial_data.json')
        if os.path.exists(initial_data_filename):
            content = open(initial_data_filename).read()
        fixture_data = prepare_fixtures(content)
        cms_settings.render_to(['..', 'fixtures', 'initial_data.json'],
            'redsolutioncms/project/raw_content.txt', {'content': fixture_data}, 'w')

make = Make()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([
])
sys.path[0:0] = [
    os.path.abspath(current_dir),
    os.path.abspath(os.path.join(current_dir, '..', 'parts', 'django')),
    os.path.abspath(os.path.join(current_dir, '..', 'eggs', 'zc.buildout-1.5.1-py2.6.egg')),
    os.path.abspath(os.path.join(current_dir, '..', 'eggs', 'zc.buildout-1.5.1-py2.5.egg')),
    os.path.abspath(os.path.join(current_dir, '..', 'eggs', 'setuptools-0.6c12dev_r84273-py2.6.egg')),
    os.path.abspath(os.path.join(current_dir, '..', 'eggs', 'setuptools-0.6c12dev_r84273-py2.5.egg')),
]

from manage_additional import *

from django.core.management import execute_manager
try:
    import settings_additional as settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = change_settings
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from redsolutioncms.loader import home_dir
from redsolutioncms.models import CMSSettings, ProcessTask
import os
import signal
import sys
import time

CONFIG_FILES = ['extrapath', 'settings', 'urls', ]

class Command(BaseCommand):

    def handle(self, *args, **options):
        cms_settings = CMSSettings.objects.get_settings()
        for file_name in CONFIG_FILES:
            data = render_to_string('redsolutioncms/%s.pyt' % (file_name), {
                'cms_settings': cms_settings,
            })
            open(os.path.join(home_dir,
                '%s_additional.py' % (file_name)), 'w').write(data)

########NEW FILE########
__FILENAME__ = install_packages
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from redsolutioncms.models import CMSSettings, CMSCreatedModel, \
    CMSEntryPoint
import os
from redsolutioncms.packages import install
from redsolutioncms.importpath import importpath
from redsolutioncms.loader import home_dir

def uninstall_packages():
    '''
    Removes all records in all tables, from all modules.
    Set installed to False in all records in CMSPackages
    '''
    cms_settings = CMSSettings.objects.get_settings()
    if not cms_settings.packages.filter(selected=False, installed=True).count() and \
        not cms_settings.packages.filter(selected=True, installed=False).count():
        return
    for model in CMSCreatedModel.objects.all():
        try:
            importpath(model.name).objects.all().delete()
        except:
            pass
    for package in cms_settings.packages.installed():
        package.installed = False
        package.save()

def load_packages():
    """
    Downloads packages to eggs and imports them to sys.path
    TODO: Raise download error if download failed
    """
    cms_settings = CMSSettings.objects.get_settings()
    # delete all old entry points, because we reset all settings at step 2
    CMSEntryPoint.objects.all().delete()
    selected_packages = cms_settings.packages.filter(selected=True)
    # prepare modules...
    modules_to_download = [{'name': package.package, 'version': package.version, }
        for package in selected_packages]
    workset = install(modules_to_download, os.path.join(home_dir, 'eggs'))
    # Now fetch entry points and import modules
    for package in selected_packages:
        distr = workset.by_key[package.package]
        distr.activate()

        package.path = distr.location
        entry_points = distr.get_entry_info(None, 'redsolutioncms')

        installed = True
        if entry_points:
            for _, entry_point in entry_points.iteritems():
                try:
                    importpath(entry_point.module_name)
                except ImportError:
                    installed = False
                    break
                # Interactive setup feature
                try:
                    importpath(entry_point.module_name + '.urls')
                except ImportError:
                    has_urls = False
                else:
                    has_urls = True
                # Frontpage handler feature
                try:
                    importpath(entry_point.module_name + '.frontpage_handler')
                except ImportError:
                    frontpage_handler = False
                else:
                    frontpage_handler = True

                CMSEntryPoint.objects.create(
                    package=package,
                    module=entry_point.module_name,
                    has_urls=has_urls,
                    frontpage_handler=frontpage_handler)

        package.installed = installed
        package.save()

class Command(BaseCommand):

    def handle(self, *args, **options):
#        import time
#        time.sleep(10)
        uninstall_packages()
        load_packages()

########NEW FILE########
__FILENAME__ = kill_runserver
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from redsolutioncms.models import ProcessTask
import time
import os, signal, sys

class Command(BaseCommand):

    def handle(self, *args, **options):
        runserver_tasks = ProcessTask.objects.filter(process_finished=False,
            task__contains=' runserver', executed=True)
        for task in runserver_tasks:
            if task.pid:
                if os.sys.platform == 'win32':
                        import ctypes
                        CTRL_BREAK_EVENT = 1
                        GenerateConsoleCtrlEvent = ctypes.windll.kernel32.GenerateConsoleCtrlEvent
                        GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, task.pid)
                else:
                    try:
                        os.kill(task.pid, signal.SIG_DFL)
                    except OSError:
                        pass
                    else:
                        sys.stdout.flush()
                        os.killpg(os.getpgid(task.pid), signal.SIGINT)
                task.process_finished = True
                task.save()

########NEW FILE########
__FILENAME__ = open_browser
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from optparse import make_option
import webbrowser, time


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-u', '--url', action='store', type='string',
            dest='url', default='http://127.0.0.1:8000'),
        make_option('-d', '--delay', action='store', type='int',
            dest='delay', default=3),
    )
    help = 'Opens browser with a given delay'

    def handle(self, *args, **options):
        time.sleep(options['delay'])
        webbrowser.open_new(options['url'])

########NEW FILE########
__FILENAME__ = wrap_runserver
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from redsolutioncms.models import ProcessTask
import subprocess
import time
import os, signal
from redsolutioncms.loader import home_dir, process_cmd_string

class Command(BaseCommand):

    def handle(self, *args, **options):
        ProcessTask.objects.create(task=process_cmd_string('"%(django)s" runserver --noreload'))
        ProcessTask.objects.create(task=process_cmd_string('"%(django)s" open_browser'))
        self.wrapper()

    def wrapper(self):
        try:
            while True:
#                check executing tasks
                executing_tasks = ProcessTask.objects.filter(
                    executed=True,
                    process_finished=False)
                for task in executing_tasks:
#                    check process finished
                    if os.sys.platform == 'win32':
                        pass
                    else:
                        try:
                            os.kill(task.pid, signal.SIG_DFL)
                        except OSError:
                            task.process_finished = True
                            task.save()
                tasks = ProcessTask.objects.filter(executed=False)
                time.sleep(1)
                lock_tasks = tasks.filter(lock=True)
                if lock_tasks:
                    first_lock_task = lock_tasks[0]
                    tasks = tasks.filter(id__lt=first_lock_task.id)
                if tasks:
                    task = tasks[0]
                    print task.task, 'executing...'
                    if os.sys.platform == 'win32':
                        CREATE_NEW_PROCESS_GROUP = 512
                        p = subprocess.Popen(task.task,
                            creationflags=CREATE_NEW_PROCESS_GROUP)
                    else:
                        p = subprocess.Popen(task.task, close_fds=True,
                            shell=True, preexec_fn=os.setsid,)
                    task.pid = p.pid
                    if task.wait:
                        p.wait()
                        task.process_finished = True
                    task.executed = True
                    task.save()
        except KeyboardInterrupt:
            executing_tasks = ProcessTask.objects.filter(process_finished=False)
            for task in executing_tasks:
                if task.pid:
                    if os.sys.platform == 'win32':
                        import ctypes
                        CTRL_BREAK_EVENT = 1
                        GenerateConsoleCtrlEvent = ctypes.windll.kernel32.GenerateConsoleCtrlEvent
                        GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, task.pid)
                    else:
                        try:
                            os.kill(task.pid, signal.SIG_DFL)
                        except OSError:
                            pass
                        else:
                            os.killpg(os.getpgid(task.pid), signal.SIGINT)
#                            if not kill
                            try:
                                os.kill(task.pid, signal.SIG_DFL)
                            except OSError:
                                pass
                            else:
                                os.killpg(os.getpgid(task.pid), signal.SIGKILL)
                        task.process_finished = True
                        task.save()
            not_executed_tasks = ProcessTask.objects.filter(
                executed=False)
            not_executed_tasks.update(executed=True, process_finished=True)
            raise KeyboardInterrupt


########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath, join, dirname, isdir, isfile, exists
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_syncdb
from redsolutioncms.loader import home_dir, project_dir

# utility
def merge_dirs(src, dst):
    '''Recursive merge directories'''
    for root, dirs, files in os.walk(src):
        rel_path = root.replace(src, '')
        rel_path = rel_path.lstrip(os.path.sep)
        for file in files:
            shutil.copy(
                join(root, file),
                join(dst, rel_path)
            )
        for dir in dirs:
            if not exists(join(dst, rel_path, dir)):
                os.mkdir(join(dst, rel_path, dir))

class BaseSettingsManager(models.Manager):
    def get_settings(self):
        if self.get_query_set().count():
            return self.get_query_set()[0]
        else:
            return self.get_query_set().create()

class BaseSettings(models.Model):
    class Meta:
        abstract = True
    objects = BaseSettingsManager()

class CMSSettings(BaseSettings):
    DATABASE_ENGINES = [
        ('postgresql_psycopg2', 'postgresql_psycopg2',),
        ('postgresql', 'postgresql',),
        ('mysql', 'mysql',),
        ('sqlite3', 'sqlite3',),
    ]

    project_name = models.CharField(verbose_name=_('Project name'),
        max_length=50, default='myproject', help_text=_('Invent a project name'))
    domain = models.CharField(verbose_name=_('Desired domain'),
        max_length=50, default='myproject.com', help_text=_('Enter your site domain for configuration'))
    default_from_email = models.EmailField(verbose_name=_('Default from e-mail'),
        default='webmaster@example.com',
        help_text=_('Value for "DEFAULT_FROM_EMAIL" and "SERVER_EMAIL"'))
    database_engine = models.CharField(verbose_name=_('Database engine'),
        max_length=50, choices=DATABASE_ENGINES, default='sqlite3')
    database_name = models.CharField(verbose_name=_('Database name'),
        max_length=50, default='myproject.sqlite', help_text=_('In case of sqlite3, database filename'))
    database_user = models.CharField(verbose_name=_('Database user'),
        max_length=50, blank=True, default='', help_text=_('Not used with sqlite3'))
    database_password = models.CharField(verbose_name=_('Database password'),
        max_length=50, blank=True, default='', help_text=_('Not used with sqlite3'))
    database_host = models.CharField(verbose_name=_('Database host'),
        max_length=50, blank=True, default='', help_text=_('Not used with sqlite3'))
    database_port = models.IntegerField(verbose_name=_('Database port'),
        blank=True, null=True, help_text=_('Not used with sqlite3'))
    # hidden fields
    initialized = models.BooleanField(verbose_name=_('CMS was initialized'), default=False)
    base_template = models.CharField(verbose_name=_('Base template'), max_length=50, blank=True, default='')
    frontpage_handler = models.ForeignKey('CMSEntryPoint', related_name='settings', null=True)

    def render_to(self, file_name, template_name, dictionary=None, mode='a+'):
        """
        ``file_name`` is relative path to destination file.
            It can be list or tuple to be os.path.joined
            To make settings.py use: 'settings.py'
            To make template use: ['..', 'templates', 'base.html']
            To make media use: ['..', 'media', 'css', 'style.css']
        
        ``template_name`` is name of template to be rendered.
        
        ``dictionary`` is context dictionary.
            ``cms_settings`` variable always will be add to context.
        
         ``mode`` is mode in witch destination file will be opened.
             Use 'w' to override old content.
        """
        if isinstance(file_name, (tuple, list)):
            file_name = join(*file_name)
        file_name = join(project_dir, self.project_name, file_name)
        try:
            os.makedirs(dirname(file_name))
        except OSError:
            pass
        if dictionary is None:
            dictionary = {}
        dictionary['cms_settings'] = self
        value = render_to_string(template_name, dictionary)
        value = value.encode('utf-8')
        open(file_name, mode).write(value)

    def copy_to(self, dst, src, merge=True, mode='wb'):
        """
        Deprecated. Use ``copy_dir`` or ``copy_file`` instead.
        Copies directory or file with mergig directories capability.
        If ``src`` is regular file, copy it in ``dst`` file or ``dst`` dir.
        If ``src`` is directory, ``dst`` must be directory or must not exist.
        If ``dst`` dir exists, merge or replace it with ``src`` content, 
        depending on ``merge`` argument
        
        Example:
        cms_settings.copy_to(os.path.join(project_media, 'img'), path_to_images)
        """
        import warnings
        warnings.warn('Deprecated. Use ``copy_dir`` or ``copy_file`` instead.')

        # first, check ``src``
        if isfile(src):
            self.copy_file(dst, src, mode)
        if isdir(src):
            self.copy_dir(dst, src, merge)
    
    def copy_file(self, dst, src, mode='wb'):
        '''
        Copy or append file content.
        Mode 'w' is for file rewriting, 'a' for appending to the end of file
        '''
        # silently try to make parent dir
        try:
            os.makedirs(dirname(dst))
        except OSError:
            pass
        if not exists(dst):
            shutil.copy(src, dst)
        else:
            dst_file = open(dst, mode)
            src_file = open(src, 'r')
            dst_file.write(src_file.read())
            dst_file.close()
            src_file.close()
        
    def copy_dir(self, dst, src, merge=True):
        '''
        Copy whole dir recursively.
        When merge=True, target directory will not be deleted,
        othwerwise, it will.
        '''
        if exists(dst):
            if isdir(dst):
                if not merge:
                    shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    merge_dirs(src, dst)
            else:
                raise IOError('Error: ``dst`` is not dir')
        else:
            shutil.copytree(src, dst)

    def package_was_installed(self, package_name):
        return package_name in self.installed_packages

    @property
    def installed_packages(self):
        return self.packages.installed().values_list('package', flat=True)

    @property
    def project_dir(self):
        import warnings
        warnings.warn('Project dir is deprecated attribute. Use redsolutioncms.loader.project_dir instead')
        return project_dir

    @property
    def temp_dir(self):
        import warnings
        warnings.warn('Project dir is deprecated attribute. Use redsolutioncms.loader.home_dir instead')
        return home_dir

class PackageManager(models.Manager):

    def installed(self):
        return self.get_query_set().filter(installed=True)

    def modules(self):
        return self.get_query_set().exclude(category__name='templates')

    def templates(self):
        return self.get_query_set().filter(category__name='templates')

class CMSPackage(models.Model):
    class Meta:
        unique_together = (
            ('settings', 'package',),
        )
    settings = models.ForeignKey(CMSSettings, related_name='packages')

    selected = models.BooleanField(verbose_name=_('Selected'), default=False)
    package = models.CharField(verbose_name=_('Package'), max_length=255)
    version = models.CharField(verbose_name=_('Package version'), max_length=50)
    verbose_name = models.CharField(verbose_name=_('Verbose name'), max_length=255)
    description = models.TextField(verbose_name=_('Description'))
    path = models.CharField(verbose_name=_('Installed to path'), max_length=255, blank=True, null=True)
    installed = models.BooleanField(verbose_name=_('Was successfully installed'), default=False)
    category = models.ForeignKey('Category', null=True, related_name='packages')

    screenshot = models.URLField(verbose_name=_('Screenshot preview URL'), null=True)

    objects = PackageManager()

    def __unicode__(self):
        return self.package

class CategoryManager(models.Manager):

    def templates(self):
        return self.get_query_set().filter(name='templates')

    def required(self):
        return self.get_query_set().filter(required=True)


class Category(models.Model):
    '''Category for package'''

    class Meta:
        ordering = ['-required', 'id']

    settings = models.ForeignKey(CMSSettings, related_name='categories')
    name = models.CharField(verbose_name=_('Category name'), max_length=255)
    parent = models.ForeignKey('self', null=True)
    required = models.BooleanField(verbose_name=_('Mandatory category'), default=False)

    def __unicode__(self):
        return self.name

    def verbose_name(self):
        '''
        Hardcoded categories names 
        '''
        verbose_names = {
            'frontpage': _('Frontpage handlers'),
            'content': _('Content plugins'),
            'utilities': _('Utilities'),
            'templates': _('Templates for site'),
            'other': _('Other applications'),
        }
        return verbose_names.get(self.name, self.name)

class EntryPointManager(models.Manager):
    def has_urls(self):
        return self.get_query_set().filter(has_urls=True)

    def frontpage_handlers(self):
        return self.get_query_set().filter(frontpage_handler=True)

class CMSEntryPoint(models.Model):
    package = models.ForeignKey(CMSPackage, related_name='entry_points')
    module = models.CharField(verbose_name=_('Module name'), max_length=255)
    has_urls = models.BooleanField(verbose_name=_('Has urls'))
    frontpage_handler = models.BooleanField(verbose_name=_('Can handle frontpage'))

    objects = EntryPointManager()

    def __unicode__(self):
        return 'Entry point %s' % self.module

class CMSCreatedModel(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=100, unique=True)

    def __unicode__(self):
        return self.name

class ProcessTask(models.Model):
    task = models.CharField(verbose_name=_('task'), max_length=255)
    pid = models.IntegerField(verbose_name=_('process pid'), blank=True, null=True)
    lock = models.BooleanField(verbose_name=_('task inactive'), default=False)
    executed = models.BooleanField(verbose_name=_('task executed'), default=False)
    process_finished = models.BooleanField(verbose_name=_('process finished'), default=False)
    wait = models.BooleanField(verbose_name=_('wait finish'), default=False)

    def __unicode__(self):
        return self.task

def add_created_model(created_models, **kwargs):
    cms_settings = CMSSettings.objects.get_settings()
    if cms_settings.initialized:
        for model in created_models:
            CMSCreatedModel.objects.get_or_create(name='%s.%s' % (model.__module__, model.__name__))

post_syncdb.connect(add_created_model)

########NEW FILE########
__FILENAME__ = packages
# -*- coding: utf-8 -*-
from xmlrpc_urllib2_transport import ProxyTransport
from django.utils.translation import ugettext as _
from django.conf import settings
from zc.buildout import easy_install
import xmlrpclib
import os
from redsolutioncms.models import CMSSettings, Category
import urllib2
import re
from pkg_resources import parse_version

PYPI_INDEX = 'http://pypi.python.org/simple'


def search_pypi_xmlrpc(query):
    client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi', transport=ProxyTransport())
    return client.search({'name': query})

def get_package_info(package_name, package_index_url=PYPI_INDEX):
    proxy_handler = urllib2.ProxyHandler()
    opener = urllib2.build_opener(proxy_handler)
    link_pattern = re.compile('.*<a.*href=[\'"](?P<href>.*?)[\'"].*>(?P<text>[\W\w]*)</a>.*')

    package = {}
    package['name'] = package_name
    package['summary'] = _('No description')
    # Go and find out package versions and screenshots
    url = package_index_url + '/%s/' % package_name
    versions = set()
    for hyperlink in opener.open(url).readlines():
        # Example:
        # <a href="/media/dists/redsolutioncms.django-seo-0.2.0.tar.gz#md5=3bb1437373cc1ce46a216674db75ffa6">
        # redsolutioncms.django-seo-0.2.0.tar.gz</a><br />
        match = re.match(link_pattern, hyperlink)
        if match:
            href, text = match.groups()
            version_match = re.match(
                '.*%s-(?P<version>[\d\.\w]+)(?P<extension>\.tar\.gz|\.zip|\.py\d\.\d\.egg)' % package['name'], href)
            if version_match:
                versions.add(version_match.groupdict()['version'])
            screenshot_match = re.match('(?P<filepath>.+)(?P<extension>\.png|\.jpg|\.gif)', href)
            if screenshot_match:
                # If image hosts on PYPI (relative link)
                if 'http://' not in href:
                    index_root = package_index_url.replace('/simple', '')
                    href = index_root + href
                package['screenshot'] = href
            classifier_match = re.match('http\:\/\/www\.redsolutioncms\.org\/classifiers\/([\w\/]+)', href)
            if classifier_match:
                # Fetch classifiers from links
                package['category'] = classifier_match.groups()

    if versions:
        package['version'] = versions.pop()
        # Do not append packages without versions
        return package

def add_package(packages, package):
    if package['name'] in packages:
        old_package = packages[package['name']]
        new_version = parse_version(package['version'])
        old_version = parse_version(old_package['version'])
        if new_version > old_version:
            packages[package['name']] = package
    else:
        packages.update({package['name']: package})

def search_index(query):
    packages = {}
    if getattr(settings, 'CUSTOM_PACKAGE_INDEX', None):
        # Work with custom /simple/ index
        # http proxy issue
        proxy_handler = urllib2.ProxyHandler()
        opener = urllib2.build_opener(proxy_handler)
        query_pattern = re.compile(
            '.*<a.*href=[\'"](?P<href>.*?)[\'"].*>(?P<text>[\w\.\-]*%s[\w\.\-]*)</a>.*'
             % query)

        for line in opener.open(settings.CUSTOM_PACKAGE_INDEX).readlines():
            # Example:
            # <a href="/simple/redsolutioncms.django-model-url/">redsolutioncms.django-model-url</a><br />
            match = re.match(query_pattern, line)
            if match:
                href, text = match.groups()
                package_info = get_package_info(text, settings.CUSTOM_PACKAGE_INDEX)
                if package_info:
                    add_package(packages, package_info)
    else:
        # Standard way: working with PYPI
        for package in search_pypi_xmlrpc(query):
            package_info = get_package_info(package['name'], PYPI_INDEX)
            if package_info:
                if package_info.get('screenshot'):
                    package['screenshot'] = package_info['screenshot']
                if package_info.get('category'):
                    package['categories'] = package_info['category']
            add_package(packages, package)

    try:
        packages.pop('redsolutioncms')
    except KeyError:
        pass
    return packages

def install(modules, path='parts'):
    '''
    Install module in given path
    Module should be dictionary object, returned by xmlrpc server pypi:
    Example:
        {'_pypi_ordering': 16,
         'name': 'django-tools',
         'summary': 'miscellaneous tools for django',
         'version': '0.10.0.git-ce3ec2d',
    }
    Returns WorkingSet object, 
    see
        http://peak.telecommunity.com/DevCenter/PkgResources#workingset-objects
    terminology:
         http://mail.python.org/pipermail/distutils-sig/2005-June/004652.html
    '''

    path = os.path.abspath(path)
    if not os.path.exists(path):
        os.makedirs(path)

    # TODO: If traceback risen here, installation of the all package list fails
    return easy_install.install(['%s==%s' % (module_['name'], module_['version'])
        for module_ in modules], path,
        index=getattr(settings, 'CUSTOM_PACKAGE_INDEX', None),
        use_dependency_links=False)

def load_package_list():
    """
    Creates objects in CMSPackages model for all modules at PYPI
    """
    cms_settings = CMSSettings.objects.get_settings()
    all_packages = search_index('redsolutioncms')

    # Flush old apps?
    cms_settings.packages.all().delete()
    cms_settings.categories.all().delete()
    # fill database again
    # create required catagories
    Category.objects.create(name='frontpage', required=True, settings=cms_settings)
    Category.objects.create(name='templates', required=True, settings=cms_settings)

    for package in all_packages.itervalues():
        cms_package = cms_settings.packages.create(
            selected=False,
            package=package['name'],
            version=package['version'],
            verbose_name=package['name'].replace('django-', '').replace('redsolutioncms.', ''),
            description=package['summary'],
            screenshot=package.get('screenshot'),
        )
        # fill cms_settings foreign key
        cms_settings.packages.add(cms_package)
        if package.get('categories'):
            for category in package['categories']:
                category_obj, created = Category.objects.get_or_create(
                    name=category, settings=cms_settings)
                category_obj.packages.add(cms_package)
        else:
            other_category, created = Category.objects.get_or_create(
                name='other', settings=cms_settings)
            other_category.packages.add(cms_package)

def test():
    print 'Searching module mptt'
    modules = search_index('mptt')
    if modules:
        print 'found %s modules' % len(modules)
    workset = install([modules[0]])
    mptt_distr = workset.by_key['django-mptt']
    print 'Trying to import mptt'
    mptt_distr.activate()
    from mptt.exceptions import InvalidMove
    print 'Successfull!'

if __name__ == '__main__':
    # run with no parameters for basic test case.
    test()

########NEW FILE########
__FILENAME__ = settings
# Django settings for redsolutioncms project.

import os
from redsolutioncms.loader import home_dir


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Redsolution', 'src@redsolution.ru'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(home_dir, 'cms.sqlite')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '*r6w%0l1g0i%hf@%evw(-%v5_(mydn^_)$c5@f^^$mp6#r85)m'

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
)

ROOT_URLCONF = 'redsolutioncms.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'redsolutioncms',
]

# set CUSTOM_PACKAGE_INDEX to None, if you want to work with default PYPI
# or set to /simple interface of custom package index to 
# work with custom index, like this:
#CUSTOM_PACKAGE_INDEX = 'http://localhost:8008/simple'


# import extra path for new plugins
try:
    from extrapath_additional import *
except ImportError:
    print 'Can not import extrapath_additional!'

try:
    from settings_additional import *
except ImportError:
    print 'Can not import settings_additional!'


########NEW FILE########
__FILENAME__ = redsolutioncms_tags
from django import template
from django.template import TOKEN_VAR, TOKEN_BLOCK, TOKEN_COMMENT, TOKEN_TEXT, \
    BLOCK_TAG_START, VARIABLE_TAG_START, VARIABLE_TAG_END, BLOCK_TAG_END

register = template.Library()

class RawNode(template.Node):
    def __init__(self, data):
        self.data = data

    def render(self, context):
        return self.data

@register.tag
def raw(parser, token):
    """
    Render as just text everything between ``{% raw %}`` and ``{% endraw %}``.
    """
    ENDRAW = 'endraw'
    data = u''
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == TOKEN_BLOCK and token.contents == ENDRAW:
            return RawNode(data)
        if token.token_type == TOKEN_VAR:
            data += '%s %s %s' % (VARIABLE_TAG_START, token.contents, VARIABLE_TAG_END)
        elif token.token_type == TOKEN_BLOCK:
            data += '%s %s %s' % (BLOCK_TAG_START, token.contents, BLOCK_TAG_END)
        elif token.token_type == TOKEN_COMMENT:
            pass # django.template don`t save comments
        elif token.token_type == TOKEN_TEXT:
            data += token.contents
    parser.unclosed_block_tag([ENDRAW])

@register.simple_tag
def start_block():
    return u'{%'

@register.simple_tag
def end_block():
    return u'%}'

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, include, url, handler404, handler500
from django.conf import settings

handler404
handler500

urlpatterns = patterns('')

if settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()

    urlpatterns += patterns('',
        (r'^admin/', include(admin.site.urls)),
    )
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )

urlpatterns += patterns(
    '',
    url(r'^$', 'redsolutioncms.views.index', name='index'),
    url(r'^apps$', 'redsolutioncms.views.apps', name='apps'),
    url(r'^load$', 'redsolutioncms.views.load', name='load'),
    url(r'^restart$', 'redsolutioncms.views.restart', name='restart'),
    url(r'^started/$', 'redsolutioncms.views.started', name='started'),
    url(r'^custom$', 'redsolutioncms.views.custom', name='custom'),
    url(r'^build$', 'redsolutioncms.views.build', name='build'),
    url(r'^done$', 'redsolutioncms.views.done', name='done'),
    url(r'^cancel_lock/$', 'redsolutioncms.views.cancel_lock', name='cancel_lock'),
    url(r'^create_superuser/$', 'redsolutioncms.views.create_superuser', name='create_superuser'),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog',
        {'packages': ('django.conf',)}, name='admin_jsi18n'),
)

try:
    from urls_additional import *
except ImportError:
    print 'Can not import urls_additional!'

########NEW FILE########
__FILENAME__ = utils
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson

def render_to(template_path):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            output = func(request, *args, **kwargs)
            if output is None:
                output = {}
            if not isinstance(output, dict):
                return output
            return render_to_response(template_path, output,
                context_instance=RequestContext(request))
        return wrapper
    return decorator

def prepare_fixtures(content):
    '''
    Modles' fixtures appended to file initial_data.json. Django loaddata script
    exepcts that json data contains only one list of dicts. But appended content
    looks like many lists. This function process each list, pull dict objects from
    it and join them together again in one list.
    For example:
        [{'a': 'test'}]
        [{'b': 'bar'}]
    becomes:
        [{'a': 'test'}, {'b': 'bar'}]
    '''
    fixtures = []
    for line in content.splitlines():
        json = simplejson.loads(line)
        if type(json) is list:
            for object in json:
                fixtures.append(object)
    return simplejson.dumps(fixtures)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory, modelformset_factory
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from redsolutioncms.forms import UserCreationForm, FrontpageForm, CategoryForm
from redsolutioncms.importpath import importpath
from redsolutioncms.loader import home_dir, process_cmd_string, project_dir
from redsolutioncms.make import AlreadyMadeException
from redsolutioncms.models import CMSSettings, ProcessTask, Category
from redsolutioncms.packages import load_package_list
import os, subprocess, datetime

CONFIG_FILES = ['manage', 'settings', 'urls', ]


def index(request):
    """
    Shows greetings form, base settings form: project name, database settings, etc.
    """
    cms_settings = CMSSettings.objects.get_settings()
    cms_settings.initialized = True
    cms_settings.save()
    SettingsForm = modelform_factory(CMSSettings, exclude=['initialized',
        'frontpage_handler', 'base_template'])
    if request.method == 'POST':
        form = SettingsForm(data=request.POST, files=request.FILES, instance=cms_settings)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('apps'))
    else:
        form = SettingsForm(instance=cms_settings)
    return render_to_response('redsolutioncms/index.html', {
        'form': form,
    }, context_instance=RequestContext(request))


def apps(request):
    """
    Second step. Shows available packages listing.
    """
    FormsetClass = modelformset_factory(Category, CategoryForm)

    if request.method == 'POST':
        formset = FormsetClass(request.POST)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(reverse('load'))
    else:
        from urllib2 import HTTPError, URLError
        try:
            load_package_list()
        except (HTTPError, URLError):
            return render_to_response('redsolutioncms/error.html', {
                'error': _('Htttp problem with index server'),
            })
        formset = FormsetClass()
    return render_to_response('redsolutioncms/apps.html', {
        'formset': formset,
    }, context_instance=RequestContext(request))


def load(request):
    """
    Show wait circle loader, fetch packages from index site.
    Template has AJAX checker, so user will be redirected to next step automatically.
    Saves installation information for packages.
    Makes settings.py, urls.py, manage.py with installed setup-packages.
    Syncdb for setup-packages.
    """
    task = ProcessTask.objects.create(
        task=process_cmd_string('"%(django)s" kill_runserver'),
        lock=True, wait=True)
    ProcessTask.objects.create(task=process_cmd_string('"%(django)s" install_packages'), wait=True)
    ProcessTask.objects.create(task=process_cmd_string('"%(django)s" change_settings'), wait=True)
    ProcessTask.objects.create(task=process_cmd_string('"%(django)s" syncdb --noinput'), wait=True)
    ProcessTask.objects.create(task=process_cmd_string('"%(django)s" runserver --noreload'))
    return render_to_response('redsolutioncms/wait.html', {
        'task_id':task.id,
        'redirect_to': reverse('custom'),
        'start_task_id':task.id,
        'title': _('Downloading packages'),
    }, context_instance=RequestContext(request))

def custom(request):
    """
    User can go to detail settings for packages or can ask to make project.
    Make files for new project.
    """
    cms_settings = CMSSettings.objects.get_settings()
    if request.method == 'POST':
        entry_points = ['redsolutioncms']
        cms_settings.base_template = 'base_template.html'
        cms_settings.save()
        # handle frontpage
        frontpage_form = FrontpageForm(request.POST)
        if frontpage_form.is_valid():
            frontpage_form.save()
            for package in cms_settings.packages.installed():
                for entry_point in package.entry_points.all():
                    entry_points.append(entry_point.module)
            make_objects = []
            for entry_point in entry_points:
                try:
                    make_object = importpath('.'.join([entry_point, 'make', 'make']))
                except ImportError, error:
                    print 'Entry point %s has no make object.' % entry_point
                    continue
                else:
                    make_objects.append(make_object)

            for make_object in make_objects:
                make_object.flush()
            for make_object in make_objects:
                try:
                    make_object.premake()
                except AlreadyMadeException:
                    pass
            for make_object in make_objects:
                try:
                    make_object.make()
                except AlreadyMadeException:
                    pass
            for make_object in make_objects:
                try:
                    make_object.postmake()
                except AlreadyMadeException:
                    pass
            return HttpResponseRedirect(reverse('build'))
    else:
        frontpage_form = FrontpageForm()
    return render_to_response('redsolutioncms/custom.html', {
        'cms_settings': cms_settings,
        'frontpage_form': frontpage_form,
    }, context_instance=RequestContext(request))

def build(request):
    cms_settings = CMSSettings.objects.get_settings()
    task = ProcessTask.objects.create(
        task=process_cmd_string('"%(django)s" kill_runserver'),
        lock=True, wait=True)

    project_params = {
        'project_bootstrap': os.path.join(project_dir, 'bootstrap.py'),
        'project_buildout_cfg': os.path.join(project_dir, 'develop.cfg'),
        'project_buildout': os.path.join(project_dir, 'bin', 'buildout'),
        'project_django': os.path.join(project_dir, 'bin', 'django'),
    }


    ProcessTask.objects.create(
        task=process_cmd_string('"%(python)s" "%(project_bootstrap)s" -c "%(project_buildout_cfg)s"', project_params),
        wait=True)
    ProcessTask.objects.create(
        task=process_cmd_string('"%(project_buildout)s" -c "%(project_buildout_cfg)s"', project_params),
        wait=True)
    ProcessTask.objects.create(
        task=process_cmd_string('"%(project_django)s" syncdb --noinput', project_params),
        wait=True)
    ProcessTask.objects.create(
        task=process_cmd_string('"%(project_django)s" runserver 8001 --noreload',
        project_params))
    ProcessTask.objects.create(
        task=process_cmd_string('"%(django)s" runserver --noreload'))

    return render_to_response('redsolutioncms/wait.html', {
        'task_id': task.id,
        'redirect_to': reverse('create_superuser'),
        'start_task_id':task.id,
        'title': _('Building your site'),
    }, context_instance=RequestContext(request))

def create_superuser(request):
    cms_settings = CMSSettings.objects.get_settings()
    if request.method == 'POST':
        form = UserCreationForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            password = form.cleaned_data['password1']
            user = User.objects.model(username='generate_password')
            user.set_password(password)
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            context = {
                'username': form.cleaned_data['username'],
                'password': user.password,
                'email': form.cleaned_data['email'],
                'current_datetime': current_datetime,
                }
            data = render_to_string(
                'redsolutioncms/project/fixtures/create_superuser.json', context)
            open(os.path.join(project_dir,
                'create_superuser.json'), 'w').write(data)
            django_name = os.path.join(project_dir, 'bin', 'django')
            subprocess.Popen([django_name, 'loaddata',
                os.path.join(project_dir, 'create_superuser.json')]).wait()
            os.remove(os.path.join(project_dir, 'create_superuser.json'))
            return HttpResponseRedirect(reverse('done'))
    else:
        form = UserCreationForm()
    return render_to_response('redsolutioncms/build.html', {
        'cms_settings': cms_settings,
        'bootstrap': os.path.join(project_dir, 'bootstrap.py'),
        'buildout': os.path.join(project_dir, 'bin', 'buildout'),
        'django': os.path.join(project_dir, 'bin', 'django'),
        'form': form,
    }, context_instance=RequestContext(request))

def done(request):
    cms_settings = CMSSettings.objects.get_settings()
    return render_to_response('redsolutioncms/done.html', {
        'cms_settings': cms_settings,
        'project_dir': project_dir,
        'django': os.path.join(project_dir, 'bin', 'django'),
    }, context_instance=RequestContext(request))

def restart(request):
    """
    Ajax view. Restarts runserver
    """
    task = ProcessTask.objects.create(task=process_cmd_string('"%(django)s" kill_runserver'),
        lock=True, wait=True)
    ProcessTask.objects.create(task=process_cmd_string('"%(django)s" runserver --noreload'))
    task.lock = False
    task.save()
    return HttpResponse()

def started(request):
    """
    User can`t see it. It will be called by javascript.
    Used to check, whether server is available after restart.
    """
    if request.method == "POST":
        task_id = request.POST.get('task_id')
        task = get_object_or_404(ProcessTask, id=task_id)
        if task.process_finished:
            return HttpResponse()
    return HttpResponseNotFound()

def cancel_lock(request):
    if request.method == "POST":
        task_id = request.POST.get('task_id')
        task = get_object_or_404(ProcessTask, id=task_id)
        task.lock = False
        task.save()
    return HttpResponse()

########NEW FILE########
__FILENAME__ = xmlrpc_urllib2_transport
#!/bin/env python
"""urllib2-based transport class for xmlrpclib.py (with test code).

Written from scratch but inspired by xmlrpc_urllib_transport.py file from http://starship.python.net/crew/jjkunce/ by jjk.

A. Ellerton 2006-07-06

Testing with Python 2.4 on Windows and Linux, with/without a corporate proxy in place.

****************************
*** USE AT YOUR OWN RISK ***
****************************
"""

import xmlrpclib

class ProxyTransport(xmlrpclib.Transport):
    """Provides an XMl-RPC transport routing via a http proxy.
    
    This is done by using urllib2, which in turn uses the environment
    varable http_proxy and whatever else it is built to use (e.g. the
    windows    registry).
    
    NOTE: the environment variable http_proxy should be set correctly.
    See checkProxySetting() below.
    
    Written from scratch but inspired by xmlrpc_urllib_transport.py
    file from http://starship.python.net/crew/jjkunce/ by jjk.
    
    A. Ellerton 2006-07-06
    """
#    redefine parse_response and _parse_response(taken from python 2.6)
#    to work with python 2.7

    def parse_response(self, file):
        # compatibility interface
        return self._parse_response(file, None)

    def _parse_response(self, file, sock):
        # read response from input file/socket, and parse it

        p, u = self.getparser()

        while 1:
            if sock:
                response = sock.recv(1024)
            else:
                response = file.read(1024)
            if not response:
                break
            if self.verbose:
                print "body:", repr(response)
            p.feed(response)

        file.close()
        p.close()

        return u.close()

    def request(self, host, handler, request_body, verbose):
        import urllib2
        self.verbose = verbose
        url = 'http://' + host + handler
        if self.verbose: "ProxyTransport URL: [%s]" % url

        request = urllib2.Request(url)
        request.add_data(request_body)
        # Note: 'Host' and 'Content-Length' are added automatically
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Content-Type", "text/xml") # Important

        proxy_handler = urllib2.ProxyHandler()
        opener = urllib2.build_opener(proxy_handler)
        f = opener.open(request)
        return(self.parse_response(f))


def checkProxySetting():
    """If the variable 'http_proxy' is set, it will most likely be in one
    of these forms (not real host/ports):
    
          proxyhost:8080
          http://proxyhost:8080
    
    urlllib2 seems to require it to have 'http;//" at the start.
    This routine does that, and returns the transport for xmlrpc.
    """
    import os, re
    try:
        http_proxy = os.environ['http_proxy']
    except KeyError:
        return

    # ensure the proxy has the 'http://' at the start
    #

    match = re.search('(http://)?([\w/-/.]+):([\w/-/.]+)(\@)?([\w/-/.]+)?:?([\w/-/.]+)?', http_proxy)
    if not match:
        raise Exception("Proxy format not recognised: [%s]" % http_proxy)
    else:
        groups = match.groups()
        if not groups[3]:
            # proxy without authorization
            os.environ['http_proxy'] = "http://%s:%s" % (groups[1], groups(2))
        else:
            os.environ['http_proxy'] = "http://%s:%s@%s:%s" % (groups[1], groups[2], groups[4], groups[5])

    return


def test():
    import sys, os

    def nextArg():
        try: return sys.argv.pop(1)
        except: return None

    checkProxySetting()

    url = nextArg() or "http://betty.userland.com"
    api = nextArg() or "examples.getStateName(32)" # "examples.getStateList([1,2])"
    try:
        server = xmlrpclib.Server(url, transport=ProxyTransport())
        print "Url: %s" % url

        try: print "Proxy: %s" % os.environ['http_proxy']
        except KeyError: print "Proxy: (Apparently none)"

        print "API: %s" % api
        r = eval("server.%s" % api)
        print "Result: ", r

    except xmlrpclib.ProtocolError, e:
        print "Connection error: %s" % e
    except xmlrpclib.Fault, e:
        print "Error: %s" % e

if __name__ == '__main__':
    # run with no parameters for basic test case.
    test()

########NEW FILE########
