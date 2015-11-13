__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.insert(0, 'buildout:accept-buildout-test-releases=true')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
        if sys.version_info[:2] == (2, 4):
            setup_args['version'] = '0.6.32'
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if not find_links and options.accept_buildout_test_releases:
    find_links = 'http://downloads.buildout.org/'
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if distv >= pkg_resources.parse_version('2dev'):
                continue
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version

if version:
    requirement += '=='+version
else:
    requirement += '<2dev'

cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout

# If there isn't already a command in the args, add bootstrap
if not [a for a in args if '=' not in a]:
    args.append('bootstrap')


# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = settings
"""Settings for the demo of emencia.django.newsletter"""
import os

gettext = lambda s: s

DEBUG = True

DATABASES = {'default':
             {'ENGINE': 'django.db.backends.sqlite3',
              'NAME': os.path.join(os.path.dirname(__file__), 'demo.db')}
             }

STATIC_URL = '/static/'

MEDIA_URL = 'http://localhost:8000/'

SECRET_KEY = 'jkjf7878fsdok-|767sjdvjsm_qcskhvs$:?shf67dd66%&sfj'

USE_I18N = True
USE_L10N = True

SITE_ID = 1

LANGUAGE_CODE = 'en'

LANGUAGES = (('en', gettext('English')),
             ('fr', gettext('French')),
             ('de', gettext('German')),
             ('es', gettext('Spanish')),
             ('es_DO', gettext('Spanish (Dominican Republic)')),
             ('it', gettext('Italian')),
             ('pt', gettext('Portuguese')),
             ('pt_BR', gettext('Portuguese (Brazilian)')),
             ('nl', gettext('Dutch')),
             ('cs', gettext('Czech')),
             ('fo', gettext('Faroese')),
             ('ja', gettext('Japanese')),
             ('sk_SK', gettext('Slovak (Slovakia)')),
             ('sl', gettext('Slovenian')),
             ('zh_CN', gettext('Chinese (China)')),)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    )

ROOT_URLCONF = 'demo.urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
    )

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    )

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'tagging',
    'emencia.django.newsletter',
    )

########NEW FILE########
__FILENAME__ = urls
"""Urls for the demo of emencia.django.newsletter"""
from django.contrib import admin
from django.conf.urls.defaults import url
from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import handler404
from django.conf.urls.defaults import handler500

admin.autodiscover()

urlpatterns = patterns('',
                       (r'^$', 'django.views.generic.simple.redirect_to',
                        {'url': '/admin/'}),
                       url(r'^newsletters/', include('emencia.django.newsletter.urls')),
                       url(r'^i18n/', include('django.conf.urls.i18n')),
                       url(r'^admin/', include(admin.site.urls)),
                       )

########NEW FILE########
__FILENAME__ = contact
"""ModelAdmin for Contact"""
import StringIO
from django.conf import settings
from datetime import datetime

from django.contrib import admin
from django.dispatch import Signal
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.contrib.admin.views.main import ChangeList
from django.db import DatabaseError

from emencia.django.newsletter.models import MailingList
from emencia.django.newsletter.settings import USE_WORKGROUPS
from emencia.django.newsletter.utils.importation import import_dispatcher
from emencia.django.newsletter.utils.workgroups import request_workgroups
from emencia.django.newsletter.utils.workgroups import request_workgroups_contacts_pk
from emencia.django.newsletter.utils.vcard import vcard_contacts_export_response
from emencia.django.newsletter.utils.excel import ExcelResponse


contacts_imported = Signal(providing_args=['source', 'type'])


class ContactAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('email', 'first_name', 'last_name', 'tags', 'tester', 'subscriber',
                    'valid', 'total_subscriptions', 'creation_date', 'related_object_admin')
    list_filter = ('subscriber', 'valid', 'tester', 'creation_date', 'modification_date')
    search_fields = ('email', 'first_name', 'last_name', 'tags')
    fieldsets = ((None, {'fields': ('email', 'first_name', 'last_name')}),
                 (None, {'fields': ('tags',)}),
                 (_('Status'), {'fields': ('subscriber', 'valid', 'tester')}),
                 (_('Advanced'), {'fields': ('object_id', 'content_type'),
                                  'classes': ('collapse',)}),
                 )
    actions = ['create_mailinglist', 'export_vcard', 'export_excel']
    actions_on_top = False
    actions_on_bottom = True

    def queryset(self, request):
        queryset = super(ContactAdmin, self).queryset(request)
        if not request.user.is_superuser and USE_WORKGROUPS:
            contacts_pk = request_workgroups_contacts_pk(request)
            queryset = queryset.filter(pk__in=contacts_pk)
        return queryset

    def save_model(self, request, contact, form, change):
        workgroups = []
        if not contact.pk and not request.user.is_superuser \
               and USE_WORKGROUPS:
            workgroups = request_workgroups(request)
        contact.save()
        for workgroup in workgroups:
            workgroup.contacts.add(contact)

    def related_object_admin(self, contact):
        """Display link to related object's admin"""
        if contact.content_type and contact.object_id:
            admin_url = reverse('admin:%s_%s_change' % (contact.content_type.app_label,
                                                        contact.content_type.model),
                                args=(contact.object_id,))
            return '%s: <a href="%s">%s</a>' % (contact.content_type.model.capitalize(),
                                                admin_url,
                                                contact.content_object.__unicode__())
        return _('No relative object')
    related_object_admin.allow_tags = True
    related_object_admin.short_description = _('Related object')

    def total_subscriptions(self, contact):
        """Display user subscriptions to unsubscriptions"""
        subscriptions = contact.subscriptions().count()
        unsubscriptions = contact.unsubscriptions().count()
        return '%s / %s' % (subscriptions - unsubscriptions, subscriptions)
    total_subscriptions.short_description = _('Total subscriptions')

    def export_vcard(self, request, queryset, export_name=''):
        """Export selected contact in VCard"""
        return vcard_contacts_export_response(queryset)
    export_vcard.short_description = _('Export contacts as VCard')

    def export_excel(self, request, queryset, export_name=''):
        """Export selected contact in Excel"""
        if not export_name:
            export_name = 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y')
        return ExcelResponse(queryset, export_name)
    export_excel.short_description = _('Export contacts in Excel')

    def create_mailinglist(self, request, queryset):
        """Create a mailing list from selected contact"""
        when = str(datetime.now()).split('.')[0]
        new_mailing = MailingList(name=_('New mailinglist at %s') % when,
                                  description=_('New mailing list created in admin at %s') % when)
        new_mailing.save()

        if 'lite' in settings.DATABASES['default']['ENGINE']:
            self.message_user(request, _('SQLite3 or a SpatialLite database type detected, ' \
                                         'please note you will be limited to 999 contacts ' \
                                         'per mailing list.'))
        try:
            new_mailing.subscribers = queryset.all()
        except DatabaseError:
            new_mailing.subscribers = queryset.none()

        if not request.user.is_superuser and USE_WORKGROUPS:
            for workgroup in request_workgroups(request):
                workgroup.mailinglists.add(new_mailing)

        self.message_user(request, _('%s succesfully created.') % new_mailing)
        return HttpResponseRedirect(reverse('admin:newsletter_mailinglist_change',
                                            args=[new_mailing.pk]))
    create_mailinglist.short_description = _('Create a mailinglist')

    def importation(self, request):
        """Import contacts from a VCard"""
        opts = self.model._meta

        if request.POST:
            source = request.FILES.get('source') or \
                     StringIO.StringIO(request.POST.get('source', ''))
            if not request.user.is_superuser and USE_WORKGROUPS:
                workgroups = request_workgroups(request)
            else:
                workgroups = []
            inserted = import_dispatcher(source, request.POST['type'],
                                         workgroups)
            if inserted:
                contacts_imported.send(sender=self, source=source,
                                       type=request.POST['type'])

            self.message_user(request, _('%s contacts succesfully imported.') % inserted)

        context = {'title': _('Contact importation'),
                   'opts': opts,
                   'root_path': self.admin_site.root_path,
                   'app_label': opts.app_label}

        return render_to_response('newsletter/contact_import.html',
                                  context, RequestContext(request))

    def filtered_request_queryset(self, request):
        """Return queryset filtered by the admin list view"""
        cl = ChangeList(request, self.model, self.list_display,
                        self.list_display_links, self.list_filter,
                        self.date_hierarchy, self.search_fields,
                        self.list_select_related, self.list_per_page,
                        self.list_editable, self)
        return cl.get_query_set()

    def creation_mailinglist(self, request):
        """Create a mailing list form the filtered contacts"""
        return self.create_mailinglist(request, self.filtered_request_queryset(request))

    def exportation_vcard(self, request):
        """Export filtered contacts in VCard"""
        return self.export_vcard(request, self.filtered_request_queryset(request),
                                 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y'))

    def exportation_excel(self, request):
        """Export filtered contacts in Excel"""
        return self.export_excel(request, self.filtered_request_queryset(request),
                                 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y'))

    def get_urls(self):
        urls = super(ContactAdmin, self).get_urls()
        my_urls = patterns('',
                           url(r'^import/$',
                               self.admin_site.admin_view(self.importation),
                               name='newsletter_contact_import'),
                           url(r'^create_mailinglist/$',
                               self.admin_site.admin_view(self.creation_mailinglist),
                               name='newsletter_contact_create_mailinglist'),
                           url(r'^export/vcard/$',
                               self.admin_site.admin_view(self.exportation_vcard),
                               name='newsletter_contact_export_vcard'),
                           url(r'^export/excel/$',
                               self.admin_site.admin_view(self.exportation_excel),
                               name='newsletter_contact_export_excel'),)
        return my_urls + urls

########NEW FILE########
__FILENAME__ = mailinglist
"""ModelAdmin for MailingList"""
from datetime import datetime

from django.contrib import admin
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns
from django.utils.encoding import smart_str
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect

from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import MailingList
from emencia.django.newsletter.settings import USE_WORKGROUPS
from emencia.django.newsletter.utils.workgroups import request_workgroups
from emencia.django.newsletter.utils.workgroups import request_workgroups_contacts_pk
from emencia.django.newsletter.utils.workgroups import request_workgroups_mailinglists_pk
from emencia.django.newsletter.utils.vcard import vcard_contacts_export_response
from emencia.django.newsletter.utils.excel import ExcelResponse


class MailingListAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('creation_date', 'name', 'description',
                    'subscribers_count', 'unsubscribers_count',
                    'exportation_links')
    list_editable = ('name', 'description')
    list_filter = ('creation_date', 'modification_date')
    search_fields = ('name', 'description',)
    filter_horizontal = ['subscribers', 'unsubscribers']
    fieldsets = ((None, {'fields': ('name', 'description',)}),
                 (None, {'fields': ('subscribers',)}),
                 (None, {'fields': ('unsubscribers',)}),
                 )
    actions = ['merge_mailinglist']
    actions_on_top = False
    actions_on_bottom = True

    def queryset(self, request):
        queryset = super(MailingListAdmin, self).queryset(request)
        if not request.user.is_superuser and USE_WORKGROUPS:
            mailinglists_pk = request_workgroups_mailinglists_pk(request)
            queryset = queryset.filter(pk__in=mailinglists_pk)
        return queryset

    def save_model(self, request, mailinglist, form, change):
        workgroups = []
        if not mailinglist.pk and not request.user.is_superuser \
               and USE_WORKGROUPS:
            workgroups = request_workgroups(request)
        mailinglist.save()
        for workgroup in workgroups:
            workgroup.mailinglists.add(mailinglist)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if 'subscribers' in db_field.name and not request.user.is_superuser \
               and USE_WORKGROUPS:
            contacts_pk = request_workgroups_contacts_pk(request)
            kwargs['queryset'] = Contact.objects.filter(pk__in=contacts_pk)
        return super(MailingListAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def merge_mailinglist(self, request, queryset):
        """Merge multiple mailing list"""
        if queryset.count() == 1:
            self.message_user(request, _('Please select a least 2 mailing list.'))
            return None

        subscribers = {}
        unsubscribers = {}
        for ml in queryset:
            for contact in ml.subscribers.all():
                subscribers[contact] = ''
            for contact in ml.unsubscribers.all():
                unsubscribers[contact] = ''

        when = str(datetime.now()).split('.')[0]
        new_mailing = MailingList(name=_('Merging list at %s') % when,
                                  description=_('Mailing list created by merging at %s') % when)
        new_mailing.save()
        new_mailing.subscribers = subscribers.keys()
        new_mailing.unsubscribers = unsubscribers.keys()

        if not request.user.is_superuser and USE_WORKGROUPS:
            for workgroup in request_workgroups(request):
                workgroup.mailinglists.add(new_mailing)

        self.message_user(request, _('%s succesfully created by merging.') % new_mailing)
        return HttpResponseRedirect(reverse('admin:newsletter_mailinglist_change',
                                            args=[new_mailing.pk]))
    merge_mailinglist.short_description = _('Merge selected mailinglists')

    def exportation_links(self, mailinglist):
        """Display links for exportation"""
        return u'<a href="%s">%s</a> / <a href="%s">%s</a>' % (
            reverse('admin:newsletter_mailinglist_export_excel',
                    args=[mailinglist.pk]), _('Excel'),
            reverse('admin:newsletter_mailinglist_export_vcard',
                    args=[mailinglist.pk]), _('VCard'))
    exportation_links.allow_tags = True
    exportation_links.short_description = _('Export')

    def exportion_vcard(self, request, mailinglist_id):
        """Export subscribers in the mailing in VCard"""
        mailinglist = get_object_or_404(MailingList, pk=mailinglist_id)
        name = 'contacts_%s' % smart_str(mailinglist.name)
        return vcard_contacts_export_response(mailinglist.subscribers.all(), name)

    def exportion_excel(self, request, mailinglist_id):
        """Export subscribers in the mailing in Excel"""
        mailinglist = get_object_or_404(MailingList, pk=mailinglist_id)
        name = 'contacts_%s' % smart_str(mailinglist.name)
        return ExcelResponse(mailinglist.subscribers.all(), name)

    def get_urls(self):
        urls = super(MailingListAdmin, self).get_urls()
        my_urls = patterns('',
                           url(r'^export/vcard/(?P<mailinglist_id>\d+)/$',
                               self.admin_site.admin_view(self.exportion_vcard),
                               name='newsletter_mailinglist_export_vcard'),
                           url(r'^export/excel/(?P<mailinglist_id>\d+)/$',
                               self.admin_site.admin_view(self.exportion_excel),
                               name='newsletter_mailinglist_export_excel'))
        return my_urls + urls

########NEW FILE########
__FILENAME__ = newsletter
"""ModelAdmin for Newsletter"""
from HTMLParser import HTMLParseError

from django import forms
from django.db.models import Q
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import Attachment
from emencia.django.newsletter.models import MailingList
from emencia.django.newsletter.mailer import Mailer
from emencia.django.newsletter.settings import USE_TINYMCE
from emencia.django.newsletter.settings import USE_WORKGROUPS
try:
    CAN_USE_PREMAILER = True
    from emencia.django.newsletter.utils.premailer import Premailer
    from emencia.django.newsletter.utils.premailer import PremailerError
except ImportError:
    CAN_USE_PREMAILER = False
from emencia.django.newsletter.utils.workgroups import request_workgroups
from emencia.django.newsletter.utils.workgroups import request_workgroups_contacts_pk
from emencia.django.newsletter.utils.workgroups import request_workgroups_newsletters_pk
from emencia.django.newsletter.utils.workgroups import request_workgroups_mailinglists_pk


class AttachmentAdminInline(admin.TabularInline):
    model = Attachment
    extra = 1
    fieldsets = ((None, {'fields': (('title', 'file_attachment'))}),)


class BaseNewsletterAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('title', 'mailing_list', 'server', 'status',
                    'sending_date', 'creation_date', 'modification_date',
                    'historic_link', 'statistics_link')
    list_filter = ('status', 'sending_date', 'creation_date', 'modification_date')
    search_fields = ('title', 'content', 'header_sender', 'header_reply')
    filter_horizontal = ['test_contacts']
    fieldsets = ((None, {'fields': ('title', 'content',)}),
                 (_('Receivers'), {'fields': ('mailing_list', 'test_contacts',)}),
                 (_('Sending'), {'fields': ('sending_date', 'status',)}),
                 (_('Miscellaneous'), {'fields': ('server', 'header_sender',
                                                  'header_reply', 'slug'),
                                       'classes': ('collapse',)}),
                 )
    prepopulated_fields = {'slug': ('title',)}
    inlines = (AttachmentAdminInline,)
    actions = ['send_mail_test', 'make_ready_to_send', 'make_cancel_sending']
    actions_on_top = False
    actions_on_bottom = True

    def get_actions(self, request):
        actions = super(BaseNewsletterAdmin, self).get_actions(request)
        if not request.user.has_perm('newsletter.can_change_status'):
            del actions['make_ready_to_send']
            del actions['make_cancel_sending']
        return actions

    def queryset(self, request):
        queryset = super(BaseNewsletterAdmin, self).queryset(request)
        if not request.user.is_superuser and USE_WORKGROUPS:
            newsletters_pk = request_workgroups_newsletters_pk(request)
            queryset = queryset.filter(pk__in=newsletters_pk)
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'mailing_list' and \
               not request.user.is_superuser and USE_WORKGROUPS:
            mailinglists_pk = request_workgroups_mailinglists_pk(request)
            kwargs['queryset'] = MailingList.objects.filter(pk__in=mailinglists_pk)
            return db_field.formfield(**kwargs)
        return super(BaseNewsletterAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'status' and \
               not request.user.has_perm('newsletter.can_change_status'):
            kwargs['choices'] = ((Newsletter.DRAFT, _('Default')),)
            return db_field.formfield(**kwargs)
        return super(BaseNewsletterAdmin, self).formfield_for_choice_field(
            db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'test_contacts':
            queryset = Contact.objects.filter(tester=True)
            if not request.user.is_superuser and USE_WORKGROUPS:
                contacts_pk = request_workgroups_contacts_pk(request)
                queryset = queryset.filter(pk__in=contacts_pk)
            kwargs['queryset'] = queryset
        return super(BaseNewsletterAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def save_model(self, request, newsletter, form, change):
        workgroups = []
        if not newsletter.pk and not request.user.is_superuser \
               and USE_WORKGROUPS:
            workgroups = request_workgroups(request)

        if newsletter.content.startswith('http://'):
            if CAN_USE_PREMAILER:
                try:
                    premailer = Premailer(newsletter.content.strip())
                    newsletter.content = premailer.transform()
                except PremailerError:
                    self.message_user(request, _('Unable to download HTML, due to errors within.'))
            else:
                self.message_user(request, _('Please install lxml for parsing an URL.'))
        if not request.user.has_perm('newsletter.can_change_status'):
            newsletter.status = form.initial.get('status', Newsletter.DRAFT)

        newsletter.save()

        for workgroup in workgroups:
            workgroup.newsletters.add(newsletter)

    def historic_link(self, newsletter):
        """Display link for historic"""
        if newsletter.contactmailingstatus_set.count():
            return u'<a href="%s">%s</a>' % (newsletter.get_historic_url(), _('View historic'))
        return _('Not available')
    historic_link.allow_tags = True
    historic_link.short_description = _('Historic')

    def statistics_link(self, newsletter):
        """Display link for statistics"""
        if newsletter.status == Newsletter.SENDING or \
           newsletter.status == Newsletter.SENT:
            return u'<a href="%s">%s</a>' % (newsletter.get_statistics_url(), _('View statistics'))
        return _('Not available')
    statistics_link.allow_tags = True
    statistics_link.short_description = _('Statistics')

    def send_mail_test(self, request, queryset):
        """Send newsletter in test"""
        for newsletter in queryset:
            if newsletter.test_contacts.count():
                mailer = Mailer(newsletter, test=True)
                try:
                    mailer.run()
                except HTMLParseError:
                    self.message_user(request, _('Unable send newsletter, due to errors within HTML.'))
                    continue
                self.message_user(request, _('%s succesfully sent.') % newsletter)
            else:
                self.message_user(request, _('No test contacts assigned for %s.') % newsletter)
    send_mail_test.short_description = _('Send test email')

    def make_ready_to_send(self, request, queryset):
        """Make newsletter ready to send"""
        queryset = queryset.filter(status=Newsletter.DRAFT)
        for newsletter in queryset:
            newsletter.status = Newsletter.WAITING
            newsletter.save()
        self.message_user(request, _('%s newletters are ready to send') % queryset.count())
    make_ready_to_send.short_description = _('Make ready to send')

    def make_cancel_sending(self, request, queryset):
        """Cancel the sending of newsletters"""
        queryset = queryset.filter(Q(status=Newsletter.WAITING) |
                                   Q(status=Newsletter.SENDING))
        for newsletter in queryset:
            newsletter.status = Newsletter.CANCELED
            newsletter.save()
        self.message_user(request, _('%s newletters are cancelled') % queryset.count())
    make_cancel_sending.short_description = _('Cancel the sending')


if USE_TINYMCE:
    from tinymce.widgets import TinyMCE

    class NewsletterTinyMCEForm(forms.ModelForm):
        content = forms.CharField(
            widget=TinyMCE(attrs={'cols': 150, 'rows': 80}))

        class Meta:
            model = Newsletter

    class NewsletterAdmin(BaseNewsletterAdmin):
        form = NewsletterTinyMCEForm
else:
    class NewsletterAdmin(BaseNewsletterAdmin):
        pass

########NEW FILE########
__FILENAME__ = smtpserver
"""ModelAdmin for SMTPServer"""
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from emencia.django.newsletter.models import SMTPServer


class SMTPServerAdminForm(forms.ModelForm):
    """Form ofr SMTPServer with custom validation"""

    def clean_headers(self):
        """Check if the headers are well formated"""
        for line in self.cleaned_data['headers'].splitlines():
            elems = line.split(':')
            if len(elems) < 2:
                raise ValidationError(_('Invalid syntax, do not forget the ":".'))
            if len(elems) > 2:
                raise ValidationError(_('Invalid syntax, several assignments by line.'))

        return self.cleaned_data['headers']

    class Meta:
        model = SMTPServer


class SMTPServerAdmin(admin.ModelAdmin):
    form = SMTPServerAdminForm
    list_display = ('name', 'host', 'port', 'user', 'tls', 'mails_hour',)
    list_filter = ('tls',)
    search_fields = ('name', 'host', 'user')
    fieldsets = ((None, {'fields': ('name', )}),
                 (_('Configuration'), {'fields': ('host', 'port',
                                                  'user', 'password', 'tls')}),
                 (_('Miscellaneous'), {'fields': ('mails_hour', 'headers'),
                                       'classes': ('collapse', )}),
                 )
    actions = ['check_connections']
    actions_on_top = False
    actions_on_bottom = True

    def check_connections(self, request, queryset):
        """Check the SMTP connection"""
        message = '%s connection %s'
        for server in queryset:
            try:
                smtp = server.connect()
                if smtp:
                    status = 'OK'
                    smtp.quit()
                else:
                    status = 'KO'
            except:
                status = 'KO'
            self.message_user(request, message % (server.__unicode__(), status))
    check_connections.short_description = _('Check connection')

########NEW FILE########
__FILENAME__ = workgroup
"""ModelAdmin for WorkGroup"""
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


class WorkGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'contacts_length',
                    'mailinglists_length', 'newsletters_length')
    fieldsets = ((None, {'fields': ('name', 'group')}),
                 (None, {'fields': ('contacts', 'mailinglists', 'newsletters')}),
                 )
    filter_horizontal = ['contacts', 'mailinglists', 'newsletters']
    actions_on_top = False
    actions_on_bottom = True

    def contacts_length(self, workgroup):
        return workgroup.contacts.count()
    contacts_length.short_description = _('Contacts length')

    def mailinglists_length(self, workgroup):
        return workgroup.mailinglists.count()
    mailinglists_length.short_description = _('Mailing List length')

    def newsletters_length(self, workgroup):
        return workgroup.newsletters.count()
    newsletters_length.short_description = _('Newsletter length')

########NEW FILE########
__FILENAME__ = cms_plugins
"""Plugins for CMS"""
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from emencia.django.newsletter.cmsplugin_newsletter import settings
from emencia.django.newsletter.cmsplugin_newsletter.models import SubscriptionFormPlugin
from emencia.django.newsletter.forms import MailingListSubscriptionForm


class CMSSubscriptionFormPlugin(CMSPluginBase):
    module = _('newsletter')
    model = SubscriptionFormPlugin
    name = _('Subscription Form')
    render_template = 'newsletter/cms/subscription_form.html'
    text_enabled = False
    admin_preview = False

    def render(self, context, instance, placeholder):
        request = context['request']
        if request.method == "POST" and (settings.FORM_NAME in request.POST.keys()):
            form = MailingListSubscriptionForm(data=request.POST)
            if form.is_valid():
                form.save(instance.mailing_list)
                form.saved = True
        else:
            form = MailingListSubscriptionForm()
        context.update({
            'object': instance,
            'form': form,
            'form_name': settings.FORM_NAME,
            'placeholder': placeholder,
        })
        return context


plugin_pool.register_plugin(CMSSubscriptionFormPlugin)

########NEW FILE########
__FILENAME__ = models
"""Models of Emencia CMS Plugins"""
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin

from emencia.django.newsletter.models import MailingList


class SubscriptionFormPlugin(CMSPlugin):
    """CMS Plugin for susbcribing to a mailing list"""
    title = models.CharField(_('title'), max_length=100, blank=True)
    show_description = models.BooleanField(_('show description'), default=True,
                                           help_text=_('Show the mailing list\'s description.'))
    mailing_list = models.ForeignKey(MailingList, verbose_name=_('mailing list'),
                                     help_text=_('Mailing List to subscribe to.'))

    def __unicode__(self):
        return self.mailing_list.name

########NEW FILE########
__FILENAME__ = settings
"""Settings for emencia.django.newsletter.cmsplugin_newsletter"""
from django.conf import settings

FORM_NAME = getattr(settings, 'SUBSCRIPTION_FORM_NAME', 'cms_subscription_form_plugin')

########NEW FILE########
__FILENAME__ = forms

"""Forms for emencia.django.newsletter"""
from django import forms
from django.utils.translation import ugettext_lazy as _

from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import MailingList


class MailingListSubscriptionForm(forms.ModelForm):
    """Form for subscribing to a mailing list"""
    # Notes : This form will not check the uniquess of
    # the 'email' field, by defining it explictly and setting
    # it the Meta.exclude list, for allowing registration
    # to a mailing list even if the contact already exists.
    # Then the contact is always added to the subscribers field
    # of the mailing list because it will be cleaned with no
    # double.

    email = forms.EmailField(label=_('Email'), max_length=75)

    def save(self, mailing_list):
        data = self.cleaned_data
        contact, created = Contact.objects.get_or_create(
            email=data['email'],
            defaults={'first_name': data['first_name'],
                      'last_name': data['last_name']})

        mailing_list.subscribers.add(contact)
        mailing_list.unsubscribers.remove(contact)

    class Meta:
        model = Contact
        fields = ('first_name', 'last_name')
        exclude = ('email',)


class AllMailingListSubscriptionForm(MailingListSubscriptionForm):
    """Form for subscribing to all mailing list"""

    mailing_lists = forms.ModelMultipleChoiceField(
        queryset=MailingList.objects.all(),
        initial=[obj.id for obj in MailingList.objects.all()],
        label=_('Mailing lists'),
        widget=forms.CheckboxSelectMultiple())

    def save(self, mailing_list):
        data = self.cleaned_data
        contact, created = Contact.objects.get_or_create(
            email=data['email'],
            defaults={'first_name': data['first_name'],
                      'last_name': data['last_name']})

        for mailing_list in data['mailing_lists']:
            mailing_list.subscribers.add(contact)
            mailing_list.unsubscribers.remove(contact)

########NEW FILE########
__FILENAME__ = mailer
"""Mailer for emencia.django.newsletter"""
import re
import sys
import time
import threading
import mimetypes
from random import sample
from StringIO import StringIO
from datetime import datetime
from datetime import timedelta
from smtplib import SMTPRecipientsRefused

try:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.Encoders import encode_base64
    from email.mime.MIMEAudio import MIMEAudio
    from email.mime.MIMEBase import MIMEBase
    from email.mime.MIMEImage import MIMEImage
except ImportError:  # Python 2.4 compatibility
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
    from email.Encoders import encode_base64
    from email.MIMEAudio import MIMEAudio
    from email.MIMEBase import MIMEBase
    from email.MIMEImage import MIMEImage
from email import message_from_file
from html2text import html2text as html2text_orig
from django.contrib.sites.models import Site
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.utils.encoding import smart_unicode

from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import ContactMailingStatus
from emencia.django.newsletter.utils.tokens import tokenize
from emencia.django.newsletter.utils.newsletter import track_links
from emencia.django.newsletter.utils.newsletter import body_insertion
from emencia.django.newsletter.settings import TRACKING_LINKS
from emencia.django.newsletter.settings import TRACKING_IMAGE
from emencia.django.newsletter.settings import TRACKING_IMAGE_FORMAT
from emencia.django.newsletter.settings import UNIQUE_KEY_LENGTH
from emencia.django.newsletter.settings import UNIQUE_KEY_CHAR_SET
from emencia.django.newsletter.settings import INCLUDE_UNSUBSCRIPTION
from emencia.django.newsletter.settings import SLEEP_BETWEEN_SENDING
from emencia.django.newsletter.settings import \
     RESTART_CONNECTION_BETWEEN_SENDING


if not hasattr(timedelta, 'total_seconds'):
    def total_seconds(td):
        return ((td.microseconds +
                 (td.seconds + td.days * 24 * 3600) * 1000000) /
                1000000.0)
else:
    total_seconds = lambda td: td.total_seconds()


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


class NewsLetterSender(object):

    def __init__(self, newsletter, test=False, verbose=0):
        self.test = test
        self.verbose = verbose
        self.newsletter = newsletter
        self.newsletter_template = Template(self.newsletter.content)
        self.title_template = Template(self.newsletter.title)

    def build_message(self, contact):
        """
        Build the email as a multipart message containing
        a multipart alternative for text (plain, HTML) plus
        all the attached files.
        """
        content_html = self.build_email_content(contact)
        content_text = html2text(content_html)

        message = MIMEMultipart()

        message['Subject'] = self.build_title_content(contact)
        message['From'] = smart_str(self.newsletter.header_sender)
        message['Reply-to'] = smart_str(self.newsletter.header_reply)
        message['To'] = contact.mail_format()

        message_alt = MIMEMultipart('alternative')
        message_alt.attach(MIMEText(smart_str(content_text), 'plain', 'UTF-8'))
        message_alt.attach(MIMEText(smart_str(content_html), 'html', 'UTF-8'))
        message.attach(message_alt)

        for attachment in self.attachments:
            message.attach(attachment)

        for header, value in self.newsletter.server.custom_headers.items():
            message[header] = value

        return message

    def build_attachments(self):
        """Build email's attachment messages"""
        attachments = []

        for attachment in self.newsletter.attachment_set.all():
            ctype, encoding = mimetypes.guess_type(attachment.file_attachment.path)

            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'

            maintype, subtype = ctype.split('/', 1)

            fd = open(attachment.file_attachment.path, 'rb')
            if maintype == 'text':
                message_attachment = MIMEText(fd.read(), _subtype=subtype)
            elif maintype == 'message':
                message_attachment = message_from_file(fd)
            elif maintype == 'image':
                message_attachment = MIMEImage(fd.read(), _subtype=subtype)
            elif maintype == 'audio':
                message_attachment = MIMEAudio(fd.read(), _subtype=subtype)
            else:
                message_attachment = MIMEBase(maintype, subtype)
                message_attachment.set_payload(fd.read())
                encode_base64(message_attachment)
            fd.close()
            message_attachment.add_header('Content-Disposition', 'attachment',
                                          filename=attachment.title)
            attachments.append(message_attachment)

        return attachments

    def build_title_content(self, contact):
        """Generate the email title for a contact"""
        context = Context({'contact': contact,
                           'UNIQUE_KEY': ''.join(sample(UNIQUE_KEY_CHAR_SET,
                                                        UNIQUE_KEY_LENGTH))})
        title = self.title_template.render(context)
        return title

    def build_email_content(self, contact):
        """Generate the mail for a contact"""
        uidb36, token = tokenize(contact)
        context = Context({'contact': contact,
                           'domain': Site.objects.get_current().domain,
                           'newsletter': self.newsletter,
                           'tracking_image_format': TRACKING_IMAGE_FORMAT,
                           'uidb36': uidb36, 'token': token})
        content = self.newsletter_template.render(context)
        if TRACKING_LINKS:
            content = track_links(content, context)
        link_site = render_to_string('newsletter/newsletter_link_site.html', context)
        content = body_insertion(content, link_site)

        if INCLUDE_UNSUBSCRIPTION:
            unsubscription = render_to_string('newsletter/newsletter_link_unsubscribe.html', context)
            content = body_insertion(content, unsubscription, end=True)
        if TRACKING_IMAGE:
            image_tracking = render_to_string('newsletter/newsletter_image_tracking.html', context)
            content = body_insertion(content, image_tracking, end=True)
        return smart_unicode(content)

    def update_newsletter_status(self):
        """Update the status of the newsletter"""
        if self.test:
            return

        if self.newsletter.status == Newsletter.WAITING:
            self.newsletter.status = Newsletter.SENDING
        if self.newsletter.status == Newsletter.SENDING and \
               self.newsletter.mails_sent() >= \
               self.newsletter.mailing_list.expedition_set().count():
            self.newsletter.status = Newsletter.SENT
        self.newsletter.save()

    @property
    def can_send(self):
        """Check if the newsletter can be sent"""
        if self.test:
            return True

        if self.newsletter.sending_date <= datetime.now() and \
               (self.newsletter.status == Newsletter.WAITING or \
                self.newsletter.status == Newsletter.SENDING):
            return True

        return False

    @property
    def expedition_list(self):
        """Build the expedition list"""
        if self.test:
            return self.newsletter.test_contacts.all()

        already_sent = ContactMailingStatus.objects.filter(status=ContactMailingStatus.SENT,
                                                           newsletter=self.newsletter).values_list('contact__id', flat=True)
        expedition_list = self.newsletter.mailing_list.expedition_set().exclude(id__in=already_sent)
        return expedition_list

    def update_contact_status(self, contact, exception):
        if exception is None:
            status = (self.test
                      and ContactMailingStatus.SENT_TEST
                      or ContactMailingStatus.SENT)
        elif isinstance(exception, (UnicodeError, SMTPRecipientsRefused)):
            status = ContactMailingStatus.INVALID
            contact.valid = False
            contact.save()
        else:
            # signal error
            print >>sys.stderr, 'smtp connection raises %s' % exception
            status = ContactMailingStatus.ERROR

        ContactMailingStatus.objects.create(
            newsletter=self.newsletter, contact=contact, status=status)


class Mailer(NewsLetterSender):
    """Mailer for generating and sending newsletters
    In test mode the mailer always send mails but do not log it"""
    smtp = None

    def run(self):
        """Send the mails"""
        if not self.can_send:
            return

        if not self.smtp:
            self.smtp_connect()

        self.attachments = self.build_attachments()

        expedition_list = self.expedition_list

        number_of_recipients = len(expedition_list)
        if self.verbose:
            print '%i emails will be sent' % number_of_recipients

        i = 1
        for contact in expedition_list:
            if self.verbose:
                print '- Processing %s/%s (%s)' % (
                    i, number_of_recipients, contact.pk)

            try:
                message = self.build_message(contact)
                self.smtp.sendmail(smart_str(self.newsletter.header_sender),
                                   contact.email,
                                   message.as_string())
            except Exception, e:
                exception = e
            else:
                exception = None

            self.update_contact_status(contact, exception)

            if SLEEP_BETWEEN_SENDING:
                time.sleep(SLEEP_BETWEEN_SENDING)
            if RESTART_CONNECTION_BETWEEN_SENDING:
                self.smtp.quit()
                self.smtp_connect()

            i += 1

        self.smtp.quit()
        self.update_newsletter_status()

    def smtp_connect(self):
        """Make a connection to the SMTP"""
        self.smtp = self.newsletter.server.connect()

    @property
    def expedition_list(self):
        """Build the expedition list"""
        credits = self.newsletter.server.credits()
        if credits <= 0:
            return []
        return super(Mailer, self).expedition_list[:credits]

    @property
    def can_send(self):
        """Check if the newsletter can be sent"""
        if self.newsletter.server.credits() <= 0:
            return False
        return super(Mailer, self).can_send


class SMTPMailer(object):
    """for generating and sending newsletters

    SMTPMailer takes the problem on a different basis than Mailer, it use
    a SMTP server and make a roundrobin over all newsletters to be sent
    dispatching it's send command to smtp server regularly over time to
    reach the limit.

    It is more robust in term of predictability.

    In test mode the mailer always send mails but do not log it"""

    smtp = None

    def __init__(self, server, test=False, verbose=0):
        self.start = datetime.now()
        self.server = server
        self.test = test
        self.verbose = verbose
        self.stop_event = threading.Event()

    def run(self):
        """send mails
        """
        sending = dict()
        candidates = self.get_candidates()
        roundrobin = []

        if not self.smtp:
            self.smtp_connect()

        delay = self.server.delay()

        i = 1
        sleep_time = 0
        while (not self.stop_event.wait(sleep_time) and
               not self.stop_event.is_set()):
            if not roundrobin:
                # refresh the list
                for expedition in candidates:
                    if expedition.id not in sending and expedition.can_send:
                        sending[expedition.id] = expedition()

                roundrobin = list(sending.keys())

            if roundrobin:
                nl_id = roundrobin.pop()
                nl = sending[nl_id]

                try:
                    self.smtp.sendmail(*nl.next())
                except StopIteration:
                    del sending[nl_id]
                except Exception, e:
                    nl.throw(e)
                else:
                    nl.next()

                sleep_time = (delay * i -
                              total_seconds(datetime.now() - self.start))
                if SLEEP_BETWEEN_SENDING:
                    sleep_time = max(time.sleep(SLEEP_BETWEEN_SENDING), sleep_time)
                if RESTART_CONNECTION_BETWEEN_SENDING:
                    self.smtp.quit()
                    self.smtp_connect()
                i += 1
            else:
                # no work, sleep a bit and some reset
                sleep_time = 600
                i = 1
                self.start = datetime.now()

            if sleep_time < 0:
                sleep_time = 0

        self.smtp.quit()

    def get_candidates(self):
        """get candidates NL"""
        return [NewsLetterExpedition(nl, self)
                for nl in Newsletter.objects.filter(server=self.server)]

    def smtp_connect(self):
        """Make a connection to the SMTP"""
        self.smtp = self.server.connect()


class NewsLetterExpedition(NewsLetterSender):
    """coroutine that will give messages to be sent with mailer

    between to message it alternate with None so that
    the mailer give it a chance to save status to db
    """

    def __init__(self, newsletter, mailer):
        super(NewsLetterExpedition, self).__init__(
                        newsletter, test=mailer.test, verbose=mailer.verbose)
        self.mailer = mailer
        self.id = newsletter.id

    def __call__(self):
        """iterator on messages to be sent
        """
        newsletter = self.newsletter

        title = 'smtp-%s (%s), nl-%s (%s)' % (
                        self.mailer.server.id, self.mailer.server.name[:10],
                        newsletter.id, newsletter.title[:10])
        # ajust len
        title = '%-30s' % title

        self.attachments = self.build_attachments()

        expedition_list = self.expedition_list

        number_of_recipients = len(expedition_list)
        if self.verbose:
            print '%s %s: %i emails will be sent' % (
                    datetime.now().strftime('%Y-%m-%d'),
                    title, number_of_recipients)

        try:
            i = 1
            for contact in expedition_list:
                if self.verbose:
                    print '%s %s: processing %s/%s (%s)' % (
                        datetime.now().strftime('%H:%M:%S'),
                        title, i, number_of_recipients, contact.pk)
                try:
                    message = self.build_message(contact)
                    yield (smart_str(self.newsletter.header_sender),
                                       contact.email,
                                       message.as_string())
                except Exception, e:
                    exception = e
                else:
                    exception = None

                self.update_contact_status(contact, exception)
                i += 1
                # this one permits us to save to database imediately
                # and acknoledge eventual exceptions
                yield None
        finally:
            self.update_newsletter_status()

########NEW FILE########
__FILENAME__ = send_newsletter
"""Command for sending the newsletter"""
from django.conf import settings
from django.utils.translation import activate
from django.core.management.base import NoArgsCommand

from emencia.django.newsletter.mailer import Mailer
from emencia.django.newsletter.models import Newsletter


class Command(NoArgsCommand):
    """Send the newsletter in queue"""
    help = 'Send the newsletter in queue'

    def handle_noargs(self, **options):
        verbose = int(options['verbosity'])

        if verbose:
            print 'Starting sending newsletters...'

        activate(settings.LANGUAGE_CODE)

        for newsletter in Newsletter.objects.exclude(
            status=Newsletter.DRAFT).exclude(status=Newsletter.SENT):
            mailer = Mailer(newsletter, verbose=verbose)
            if mailer.can_send:
                if verbose:
                    print 'Start emailing %s' % newsletter.title
                mailer.run()

        if verbose:
            print 'End session sending'

########NEW FILE########
__FILENAME__ = send_newsletter_continuous
"""Command for sending the newsletter"""
from threading import Thread
import signal
import sys

from django.conf import settings
from django.utils.translation import activate
from django.core import signals
from django.core.management.base import NoArgsCommand

from emencia.django.newsletter.mailer import SMTPMailer
from emencia.django.newsletter.models import SMTPServer


class Command(NoArgsCommand):
    """Send the newsletter in queue"""
    help = 'Send the newsletter in queue'

    def handle_noargs(self, **options):
        verbose = int(options['verbosity'])

        if verbose:
            print 'Starting sending newsletters...'

        activate(settings.LANGUAGE_CODE)

        senders = SMTPServer.objects.all()
        workers = []

        for sender in senders:
            worker = SMTPMailer(sender, verbose=verbose)
            thread = Thread(target=worker.run, name=sender.name)
            workers.append((worker, thread))

        handler = term_handler(workers)
        for s in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(s, handler)

        # first close current connection
        signals.request_finished.send(sender=self.__class__)

        for worker, thread in workers:
            thread.start()

        signal.pause()  # wait for sigterm

        for worker, thread in workers:
            if thread.is_alive():
                thread.join()

        sys.exit(0)


def term_handler(workers):

    def handler(signum, frame):
        for worker, thread in workers:
            worker.stop_event.set()

    return handler

########NEW FILE########
__FILENAME__ = managers
"""Managers for emencia.django.newsletter"""
from django.db import models


class ContactManager(models.Manager):
    """Manager for the contacts"""

    def subscribers(self):
        """Return all subscribers"""
        return self.get_query_set().filter(subscriber=True)

    def unsubscribers(self):
        """Return all unsubscribers"""
        return self.get_query_set().filter(subscriber=False)

    def valids(self):
        """Return only valid contacts"""
        return self.get_query_set().filter(valid=True)

    def valid_subscribers(self):
        """Return only valid subscribers"""
        return self.subscribers().filter(valid=True)

########NEW FILE########
__FILENAME__ = 0001_initial
from south.db import db
from django.db import models
from emencia.django.newsletter.models import *


class Migration:

    def forwards(self, orm):

        # Adding model 'MailingList'
        db.create_table('newsletter_mailinglist', (
            ('id', orm['newsletter.MailingList:id']),
            ('name', orm['newsletter.MailingList:name']),
            ('description', orm['newsletter.MailingList:description']),
            ('creation_date', orm['newsletter.MailingList:creation_date']),
            ('modification_date', orm['newsletter.MailingList:modification_date']),
        ))
        db.send_create_signal('newsletter', ['MailingList'])

        # Adding model 'ContactMailingStatus'
        db.create_table('newsletter_contactmailingstatus', (
            ('id', orm['newsletter.ContactMailingStatus:id']),
            ('newsletter', orm['newsletter.ContactMailingStatus:newsletter']),
            ('contact', orm['newsletter.ContactMailingStatus:contact']),
            ('status', orm['newsletter.ContactMailingStatus:status']),
            ('link', orm['newsletter.ContactMailingStatus:link']),
            ('creation_date', orm['newsletter.ContactMailingStatus:creation_date']),
        ))
        db.send_create_signal('newsletter', ['ContactMailingStatus'])

        # Adding model 'WorkGroup'
        db.create_table('newsletter_workgroup', (
            ('id', orm['newsletter.WorkGroup:id']),
            ('name', orm['newsletter.WorkGroup:name']),
            ('group', orm['newsletter.WorkGroup:group']),
        ))
        db.send_create_signal('newsletter', ['WorkGroup'])

        # Adding model 'Link'
        db.create_table('newsletter_link', (
            ('id', orm['newsletter.Link:id']),
            ('title', orm['newsletter.Link:title']),
            ('url', orm['newsletter.Link:url']),
            ('creation_date', orm['newsletter.Link:creation_date']),
        ))
        db.send_create_signal('newsletter', ['Link'])

        # Adding model 'Newsletter'
        db.create_table('newsletter_newsletter', (
            ('id', orm['newsletter.Newsletter:id']),
            ('title', orm['newsletter.Newsletter:title']),
            ('content', orm['newsletter.Newsletter:content']),
            ('mailing_list', orm['newsletter.Newsletter:mailing_list']),
            ('server', orm['newsletter.Newsletter:server']),
            ('header_sender', orm['newsletter.Newsletter:header_sender']),
            ('header_reply', orm['newsletter.Newsletter:header_reply']),
            ('status', orm['newsletter.Newsletter:status']),
            ('sending_date', orm['newsletter.Newsletter:sending_date']),
            ('slug', orm['newsletter.Newsletter:slug']),
            ('creation_date', orm['newsletter.Newsletter:creation_date']),
            ('modification_date', orm['newsletter.Newsletter:modification_date']),
        ))
        db.send_create_signal('newsletter', ['Newsletter'])

        # Adding model 'SMTPServer'
        db.create_table('newsletter_smtpserver', (
            ('id', orm['newsletter.SMTPServer:id']),
            ('name', orm['newsletter.SMTPServer:name']),
            ('host', orm['newsletter.SMTPServer:host']),
            ('user', orm['newsletter.SMTPServer:user']),
            ('password', orm['newsletter.SMTPServer:password']),
            ('port', orm['newsletter.SMTPServer:port']),
            ('tls', orm['newsletter.SMTPServer:tls']),
            ('headers', orm['newsletter.SMTPServer:headers']),
            ('mails_hour', orm['newsletter.SMTPServer:mails_hour']),
        ))
        db.send_create_signal('newsletter', ['SMTPServer'])

        # Adding model 'Contact'
        db.create_table('newsletter_contact', (
            ('id', orm['newsletter.Contact:id']),
            ('email', orm['newsletter.Contact:email']),
            ('first_name', orm['newsletter.Contact:first_name']),
            ('last_name', orm['newsletter.Contact:last_name']),
            ('subscriber', orm['newsletter.Contact:subscriber']),
            ('valid', orm['newsletter.Contact:valid']),
            ('tester', orm['newsletter.Contact:tester']),
            ('tags', orm['newsletter.Contact:tags']),
            ('content_type', orm['newsletter.Contact:content_type']),
            ('object_id', orm['newsletter.Contact:object_id']),
            ('creation_date', orm['newsletter.Contact:creation_date']),
            ('modification_date', orm['newsletter.Contact:modification_date']),
        ))
        db.send_create_signal('newsletter', ['Contact'])

        # Adding ManyToManyField 'WorkGroup.mailinglists'
        db.create_table('newsletter_workgroup_mailinglists', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('workgroup', models.ForeignKey(orm.WorkGroup, null=False)),
            ('mailinglist', models.ForeignKey(orm.MailingList, null=False))
        ))

        # Adding ManyToManyField 'MailingList.subscribers'
        db.create_table('newsletter_mailinglist_subscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('mailinglist', models.ForeignKey(orm.MailingList, null=False)),
            ('contact', models.ForeignKey(orm.Contact, null=False))
        ))

        # Adding ManyToManyField 'WorkGroup.contacts'
        db.create_table('newsletter_workgroup_contacts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('workgroup', models.ForeignKey(orm.WorkGroup, null=False)),
            ('contact', models.ForeignKey(orm.Contact, null=False))
        ))

        # Adding ManyToManyField 'WorkGroup.newsletters'
        db.create_table('newsletter_workgroup_newsletters', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('workgroup', models.ForeignKey(orm.WorkGroup, null=False)),
            ('newsletter', models.ForeignKey(orm.Newsletter, null=False))
        ))

        # Adding ManyToManyField 'MailingList.unsubscribers'
        db.create_table('newsletter_mailinglist_unsubscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('mailinglist', models.ForeignKey(orm.MailingList, null=False)),
            ('contact', models.ForeignKey(orm.Contact, null=False))
        ))

        # Adding ManyToManyField 'Newsletter.test_contacts'
        db.create_table('newsletter_newsletter_test_contacts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('newsletter', models.ForeignKey(orm.Newsletter, null=False)),
            ('contact', models.ForeignKey(orm.Contact, null=False))
        ))

    def backwards(self, orm):

        # Deleting model 'MailingList'
        db.delete_table('newsletter_mailinglist')

        # Deleting model 'ContactMailingStatus'
        db.delete_table('newsletter_contactmailingstatus')

        # Deleting model 'WorkGroup'
        db.delete_table('newsletter_workgroup')

        # Deleting model 'Link'
        db.delete_table('newsletter_link')

        # Deleting model 'Newsletter'
        db.delete_table('newsletter_newsletter')

        # Deleting model 'SMTPServer'
        db.delete_table('newsletter_smtpserver')

        # Deleting model 'Contact'
        db.delete_table('newsletter_contact')

        # Dropping ManyToManyField 'WorkGroup.mailinglists'
        db.delete_table('newsletter_workgroup_mailinglists')

        # Dropping ManyToManyField 'MailingList.subscribers'
        db.delete_table('newsletter_mailinglist_subscribers')

        # Dropping ManyToManyField 'WorkGroup.contacts'
        db.delete_table('newsletter_workgroup_contacts')

        # Dropping ManyToManyField 'WorkGroup.newsletters'
        db.delete_table('newsletter_workgroup_newsletters')

        # Dropping ManyToManyField 'MailingList.unsubscribers'
        db.delete_table('newsletter_mailinglist_unsubscribers')

        # Dropping ManyToManyField 'Newsletter.test_contacts'
        db.delete_table('newsletter_newsletter_test_contacts')

    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsletter.contact': {
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'tester': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'newsletter.contactmailingstatus': {
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Contact']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Link']", 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Newsletter']"}),
            'status': ('django.db.models.fields.IntegerField', [], {})
        },
        'newsletter.link': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.mailinglist': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.Contact']"}),
            'unsubscribers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'})
        },
        'newsletter.newsletter': {
            'content': ('django.db.models.fields.TextField', [], {'default': "u'<body>\\n<!-- Edit your newsletter here -->\\n</body>'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'header_reply': ('django.db.models.fields.CharField', [], {'default': "'Emencia Newsletter<noreply@emencia.com>'", 'max_length': '255'}),
            'header_sender': ('django.db.models.fields.CharField', [], {'default': "'Emencia Newsletter<noreply@emencia.com>'", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailing_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.MailingList']"}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sending_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['newsletter.SMTPServer']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'test_contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.smtpserver': {
            'headers': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mails_hour': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '25'}),
            'tls': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'})
        },
        'newsletter.workgroup': {
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailinglists': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.MailingList']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'newsletters': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['newsletter.Newsletter']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['newsletter']

########NEW FILE########
__FILENAME__ = 0002_auto__add_attachment
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Attachment'
        db.create_table('newsletter_attachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('newsletter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['newsletter.Newsletter'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('file_attachment', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('newsletter', ['Attachment'])

    def backwards(self, orm):
        # Deleting model 'Attachment'
        db.delete_table('newsletter_attachment')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsletter.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Newsletter']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.contact': {
            'Meta': {'object_name': 'Contact'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'tester': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'newsletter.contactmailingstatus': {
            'Meta': {'object_name': 'ContactMailingStatus'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Contact']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Link']", 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Newsletter']"}),
            'status': ('django.db.models.fields.IntegerField', [], {})
        },
        'newsletter.link': {
            'Meta': {'object_name': 'Link'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.mailinglist': {
            'Meta': {'object_name': 'MailingList'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'mailinglist_subscriber'", 'symmetrical': 'False', 'to': "orm['newsletter.Contact']"}),
            'unsubscribers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mailinglist_unsubscriber'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['newsletter.Contact']"})
        },
        'newsletter.newsletter': {
            'Meta': {'object_name': 'Newsletter'},
            'content': ('django.db.models.fields.TextField', [], {'default': "u'<body>\\n<!-- Edit your newsletter here -->\\n</body>'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'header_reply': ('django.db.models.fields.CharField', [], {'default': "'Giorgio Barbarotta Newsletter<noreply@giorgiobarbarotta.it>'", 'max_length': '255'}),
            'header_sender': ('django.db.models.fields.CharField', [], {'default': "'Giorgio Barbarotta Newsletter<noreply@giorgiobarbarotta.it>'", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailing_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.MailingList']"}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sending_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['newsletter.SMTPServer']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'test_contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.smtpserver': {
            'Meta': {'object_name': 'SMTPServer'},
            'headers': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mails_hour': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '25'}),
            'tls': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'})
        },
        'newsletter.workgroup': {
            'Meta': {'object_name': 'WorkGroup'},
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailinglists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.MailingList']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'newsletters': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Newsletter']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['newsletter']

########NEW FILE########
__FILENAME__ = 0003_auto__add_unique_newsletter_slug
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'Newsletter', fields ['slug']
        db.create_unique('newsletter_newsletter', ['slug'])

    def backwards(self, orm):
        # Removing unique constraint on 'Newsletter', fields ['slug']
        db.delete_unique('newsletter_newsletter', ['slug'])

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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'newsletter.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Newsletter']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.contact': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'Contact'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscriber': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tags': ('tagging.fields.TagField', [], {'default': "''"}),
            'tester': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'newsletter.contactmailingstatus': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'ContactMailingStatus'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Contact']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Link']", 'null': 'True', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.Newsletter']"}),
            'status': ('django.db.models.fields.IntegerField', [], {})
        },
        'newsletter.link': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'Link'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.mailinglist': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'MailingList'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'mailinglist_subscriber'", 'symmetrical': 'False', 'to': "orm['newsletter.Contact']"}),
            'unsubscribers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mailinglist_unsubscriber'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['newsletter.Contact']"})
        },
        'newsletter.newsletter': {
            'Meta': {'ordering': "('creation_date',)", 'object_name': 'Newsletter'},
            'content': ('django.db.models.fields.TextField', [], {'default': "u'<body>\\n<!-- Edit your newsletter here -->\\n</body>'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'header_reply': ('django.db.models.fields.CharField', [], {'default': "'Emencia Newsletter<noreply@emencia.com>'", 'max_length': '255'}),
            'header_sender': ('django.db.models.fields.CharField', [], {'default': "'Emencia Newsletter<noreply@emencia.com>'", 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailing_list': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['newsletter.MailingList']"}),
            'modification_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sending_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': "orm['newsletter.SMTPServer']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'test_contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'newsletter.smtpserver': {
            'Meta': {'object_name': 'SMTPServer'},
            'headers': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mails_hour': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '25'}),
            'tls': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'})
        },
        'newsletter.workgroup': {
            'Meta': {'object_name': 'WorkGroup'},
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Contact']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailinglists': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.MailingList']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'newsletters': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['newsletter.Newsletter']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['newsletter']

########NEW FILE########
__FILENAME__ = models
"""Models for emencia.django.newsletter"""
from smtplib import SMTP
from smtplib import SMTPHeloError
from datetime import datetime
from datetime import timedelta

from django.db import models
from django.utils.encoding import smart_str
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from django.utils.encoding import force_unicode

from tagging.fields import TagField
from emencia.django.newsletter.managers import ContactManager
from emencia.django.newsletter.settings import BASE_PATH
from emencia.django.newsletter.settings import MAILER_HARD_LIMIT
from emencia.django.newsletter.settings import DEFAULT_HEADER_REPLY
from emencia.django.newsletter.settings import DEFAULT_HEADER_SENDER
from emencia.django.newsletter.utils.vcard import vcard_contact_export

# Patch for Python < 2.6
try:
    getattr(SMTP, 'ehlo_or_helo_if_needed')
except AttributeError:
    def ehlo_or_helo_if_needed(self):
        if self.helo_resp is None and self.ehlo_resp is None:
            if not (200 <= self.ehlo()[0] <= 299):
                (code, resp) = self.helo()
                if not (200 <= code <= 299):
                    raise SMTPHeloError(code, resp)
    SMTP.ehlo_or_helo_if_needed = ehlo_or_helo_if_needed


class SMTPServer(models.Model):
    """Configuration of a SMTP server"""
    name = models.CharField(_('name'), max_length=255)
    host = models.CharField(_('server host'), max_length=255)
    user = models.CharField(_('server user'), max_length=128, blank=True,
                            help_text=_('Leave it empty if the host is public.'))
    password = models.CharField(_('server password'), max_length=128, blank=True,
                                help_text=_('Leave it empty if the host is public.'))
    port = models.IntegerField(_('server port'), default=25)
    tls = models.BooleanField(_('server use TLS'))

    headers = models.TextField(_('custom headers'), blank=True,
                               help_text=_('key1: value1 key2: value2, splitted by return line.\n'\
                                           'Useful for passing some tracking headers if your provider allows it.'))
    mails_hour = models.IntegerField(_('mails per hour'), default=0)

    def connect(self):
        """Connect the SMTP Server"""
        smtp = SMTP(smart_str(self.host), int(self.port))
        smtp.ehlo_or_helo_if_needed()
        if self.tls:
            smtp.starttls()
            smtp.ehlo_or_helo_if_needed()

        if self.user or self.password:
            smtp.login(smart_str(self.user), smart_str(self.password))
        return smtp

    def delay(self):
        """compute the delay (in seconds) between mails to ensure mails
        per hour limit is not reached

        :rtype: float
        """
        if not self.mails_hour:
            return 0.0
        else:
            return 3600.0 / self.mails_hour

    def credits(self):
        """Return how many mails the server can send"""
        if not self.mails_hour:
            return MAILER_HARD_LIMIT

        last_hour = datetime.now() - timedelta(hours=1)
        sent_last_hour = ContactMailingStatus.objects.filter(
            models.Q(status=ContactMailingStatus.SENT) |
            models.Q(status=ContactMailingStatus.SENT_TEST),
            newsletter__server=self,
            creation_date__gte=last_hour).count()
        return self.mails_hour - sent_last_hour

    @property
    def custom_headers(self):
        if self.headers:
            headers = {}
            for header in self.headers.splitlines():
                if header:
                    key, value = header.split(':')
                    headers[key.strip()] = value.strip()
            return headers
        return {}

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.host)

    class Meta:
        verbose_name = _('SMTP server')
        verbose_name_plural = _('SMTP servers')


class Contact(models.Model):
    """Contact for emailing"""
    email = models.EmailField(_('email'), unique=True)
    first_name = models.CharField(_('first name'), max_length=50, blank=True)
    last_name = models.CharField(_('last name'), max_length=50, blank=True)

    subscriber = models.BooleanField(_('subscriber'), default=True)
    valid = models.BooleanField(_('valid email'), default=True)
    tester = models.BooleanField(_('contact tester'), default=False)
    tags = TagField(_('tags'))

    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(_('modification date'), auto_now=True)

    objects = ContactManager()

    def subscriptions(self):
        """Return the user subscriptions"""
        return MailingList.objects.filter(subscribers=self)

    def unsubscriptions(self):
        """Return the user unsubscriptions"""
        return MailingList.objects.filter(unsubscribers=self)

    def vcard_format(self):
        return vcard_contact_export(self)

    def mail_format(self):
        if self.first_name and self.last_name:
            return '%s %s <%s>' % (self.last_name, self.first_name, self.email)
        return self.email
    mail_format.short_description = _('mail format')

    def get_absolute_url(self):
        if self.content_type and self.object_id:
            return self.content_object.get_absolute_url()
        return reverse('admin:newsletter_contact_change', args=(self.pk,))

    def __unicode__(self):
        if self.first_name and self.last_name:
            contact_name = '%s %s' % (self.last_name, self.first_name)
        else:
            contact_name = self.email
        if self.tags:
            return '%s | %s' % (contact_name, self.tags)
        return contact_name

    class Meta:
        ordering = ('creation_date',)
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')


class MailingList(models.Model):
    """Mailing list"""
    name = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'), blank=True)

    subscribers = models.ManyToManyField(Contact, verbose_name=_('subscribers'),
                                         related_name='mailinglist_subscriber')
    unsubscribers = models.ManyToManyField(Contact, verbose_name=_('unsubscribers'),
                                           related_name='mailinglist_unsubscriber',
                                           null=True, blank=True)

    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(_('modification date'), auto_now=True)

    def subscribers_count(self):
        return self.subscribers.all().count()
    subscribers_count.short_description = _('subscribers')

    def unsubscribers_count(self):
        return self.unsubscribers.all().count()
    unsubscribers_count.short_description = _('unsubscribers')

    def expedition_set(self):
        unsubscribers_id = self.unsubscribers.values_list('id', flat=True)
        return self.subscribers.valid_subscribers().exclude(
            id__in=unsubscribers_id)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('-creation_date',)
        verbose_name = _('mailing list')
        verbose_name_plural = _('mailing lists')


class Newsletter(models.Model):
    """Newsletter to be sended to contacts"""
    DRAFT = 0
    WAITING = 1
    SENDING = 2
    SENT = 4
    CANCELED = 5

    STATUS_CHOICES = ((DRAFT, _('draft')),
                      (WAITING, _('waiting sending')),
                      (SENDING, _('sending')),
                      (SENT, _('sent')),
                      (CANCELED, _('canceled')),
                      )

    title = models.CharField(_('title'), max_length=255,
                             help_text=_('You can use the "{{ UNIQUE_KEY }}" variable ' \
                                         'for unique identifier within the newsletter\'s title.'))
    content = models.TextField(_('content'), help_text=_('Or paste an URL.'),
                               default=_('<body>\n<!-- Edit your newsletter here -->\n</body>'))

    mailing_list = models.ForeignKey(MailingList, verbose_name=_('mailing list'))
    test_contacts = models.ManyToManyField(Contact, verbose_name=_('test contacts'),
                                           blank=True, null=True)

    server = models.ForeignKey(SMTPServer, verbose_name=_('smtp server'),
                               default=1)
    header_sender = models.CharField(_('sender'), max_length=255,
                                     default=DEFAULT_HEADER_SENDER)
    header_reply = models.CharField(_('reply to'), max_length=255,
                                    default=DEFAULT_HEADER_REPLY)

    status = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=DRAFT)
    sending_date = models.DateTimeField(_('sending date'), default=datetime.now)

    slug = models.SlugField(help_text=_('Used for displaying the newsletter on the site.'),
                            unique=True)
    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(_('modification date'), auto_now=True)

    def mails_sent(self):
        return self.contactmailingstatus_set.filter(status=ContactMailingStatus.SENT).count()

    @models.permalink
    def get_absolute_url(self):
        return ('newsletter_newsletter_preview', (self.slug,))

    @models.permalink
    def get_historic_url(self):
        return ('newsletter_newsletter_historic', (self.slug,))

    @models.permalink
    def get_statistics_url(self):
        return ('newsletter_newsletter_statistics', (self.slug,))

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('-creation_date',)
        verbose_name = _('newsletter')
        verbose_name_plural = _('newsletters')
        permissions = (('can_change_status', 'Can change status'),)


class Link(models.Model):
    """Link sended in a newsletter"""
    title = models.CharField(_('title'), max_length=255)
    url = models.CharField(_('url'), max_length=255)

    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)

    def get_absolute_url(self):
        return self.url

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('-creation_date',)
        verbose_name = _('link')
        verbose_name_plural = _('links')


class Attachment(models.Model):
    """Attachment file in a newsletter"""

    def get_newsletter_storage_path(self, filename):
        filename = force_unicode(filename)
        return '/'.join([BASE_PATH, self.newsletter.slug, filename])

    newsletter = models.ForeignKey(Newsletter, verbose_name=_('newsletter'))
    title = models.CharField(_('title'), max_length=255)
    file_attachment = models.FileField(_('file to attach'), max_length=255,
                                       upload_to=get_newsletter_storage_path)

    class Meta:
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return self.file_attachment.url


class ContactMailingStatus(models.Model):
    """Status of the reception"""
    SENT_TEST = -1
    SENT = 0
    ERROR = 1
    INVALID = 2
    OPENED = 4
    OPENED_ON_SITE = 5
    LINK_OPENED = 6
    UNSUBSCRIPTION = 7

    STATUS_CHOICES = ((SENT_TEST, _('sent in test')),
                      (SENT, _('sent')),
                      (ERROR, _('error')),
                      (INVALID, _('invalid email')),
                      (OPENED, _('opened')),
                      (OPENED_ON_SITE, _('opened on site')),
                      (LINK_OPENED, _('link opened')),
                      (UNSUBSCRIPTION, _('unsubscription')),
                      )

    newsletter = models.ForeignKey(Newsletter, verbose_name=_('newsletter'))
    contact = models.ForeignKey(Contact, verbose_name=_('contact'))
    status = models.IntegerField(_('status'), choices=STATUS_CHOICES)
    link = models.ForeignKey(Link, verbose_name=_('link'),
                             blank=True, null=True)

    creation_date = models.DateTimeField(_('creation date'), auto_now_add=True)

    def __unicode__(self):
        return '%s : %s : %s' % (self.newsletter.__unicode__(),
                                 self.contact.__unicode__(),
                                 self.get_status_display())

    class Meta:
        ordering = ('-creation_date',)
        verbose_name = _('contact mailing status')
        verbose_name_plural = _('contact mailing statuses')


class WorkGroup(models.Model):
    """Work Group for privatization of the ressources"""
    name = models.CharField(_('name'), max_length=255)
    group = models.ForeignKey(Group, verbose_name=_('permissions group'))

    contacts = models.ManyToManyField(Contact, verbose_name=_('contacts'),
                                      blank=True, null=True)
    mailinglists = models.ManyToManyField(MailingList, verbose_name=_('mailing lists'),
                                          blank=True, null=True)
    newsletters = models.ManyToManyField(Newsletter, verbose_name=_('newsletters'),
                                         blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('workgroup')
        verbose_name_plural = _('workgroups')

########NEW FILE########
__FILENAME__ = settings
"""Settings for emencia.django.newsletter"""
import string
from django.conf import settings

BASE64_IMAGES = {
    'gif': 'AJEAAAAAAP///////wAAACH5BAEHAAIALAAAAAABAAEAAAICVAEAOw==',
    'png': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAABBJREFUeNpi+P//PwNAgAEACPwC/tuiTRYAAAAASUVORK5CYII=',
    'jpg': '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAYEBAQFBAYFBQYJBgUGCQsIBgYICwwKCgsKCgwQDAwMDAwMEAwODxAPDgwTExQUExMcGxsbHCAgICAgICAgICD/2wBDAQcHBw0MDRgQEBgaFREVGiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICD/wAARCAABAAEDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AVIP/2Q=='
    }

USE_WORKGROUPS = getattr(settings, 'NEWSLETTER_USE_WORKGROUPS', False)
USE_UTM_TAGS = getattr(settings, 'NEWSLETTER_USE_UTM_TAGS', True)
USE_TINYMCE = getattr(settings, 'NEWSLETTER_USE_TINYMCE',
                      'tinymce' in settings.INSTALLED_APPS)

USE_PRETTIFY = getattr(settings, 'NEWSLETTER_USE_PRETTIFY', True)

MAILER_HARD_LIMIT = getattr(settings, 'NEWSLETTER_MAILER_HARD_LIMIT', 10000)

INCLUDE_UNSUBSCRIPTION = getattr(settings, 'NEWSLETTER_INCLUDE_UNSUBSCRIPTION', True)

UNIQUE_KEY_LENGTH = getattr(settings, 'NEWSLETTER_UNIQUE_KEY_LENGTH', 8)
UNIQUE_KEY_CHAR_SET = getattr(settings, 'NEWSLETTER_UNIQUE_KEY_CHAR_SET', string.ascii_uppercase + string.digits)

DEFAULT_HEADER_SENDER = getattr(settings, 'NEWSLETTER_DEFAULT_HEADER_SENDER',
                                'Emencia Newsletter<noreply@emencia.com>')
DEFAULT_HEADER_REPLY = getattr(settings, 'NEWSLETTER_DEFAULT_HEADER_REPLY',
                               DEFAULT_HEADER_SENDER)

TRACKING_LINKS = getattr(settings, 'NEWSLETTER_TRACKING_LINKS', True)
TRACKING_IMAGE_FORMAT = getattr(settings, 'NEWSLETTER_TRACKING_IMAGE_FORMAT', 'jpg')
TRACKING_IMAGE = getattr(settings, 'NEWSLETTER_TRACKING_IMAGE',
                         BASE64_IMAGES[TRACKING_IMAGE_FORMAT])

SLEEP_BETWEEN_SENDING = getattr(
    settings, 'NEWSLETTER_SLEEP_BETWEEN_SENDING', 0)
RESTART_CONNECTION_BETWEEN_SENDING = getattr(
    settings, 'NEWSLETTER_RESTART_CONNECTION_BETWEEN_SENDING', False)

BASE_PATH = getattr(settings, 'NEWSLETTER_BASE_PATH', 'uploads/newsletter')

########NEW FILE########
__FILENAME__ = tests
"""Unit tests for emencia.django.newsletter"""
from datetime import datetime
from datetime import timedelta
from tempfile import NamedTemporaryFile

from django.test import TestCase
from django.http import Http404
from django.db import IntegrityError
from django.core.files import File

from emencia.django.newsletter.mailer import Mailer
from emencia.django.newsletter.models import Link
from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import MailingList
from emencia.django.newsletter.models import SMTPServer
from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import Attachment
from emencia.django.newsletter.models import ContactMailingStatus
from emencia.django.newsletter.utils.tokens import tokenize
from emencia.django.newsletter.utils.tokens import untokenize
from emencia.django.newsletter.utils.statistics import get_newsletter_opening_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_on_site_opening_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_unsubscription_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_clicked_link_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_top_links
from emencia.django.newsletter.utils.statistics import get_newsletter_statistics


class FakeSMTP(object):
    mails_sent = 0

    def sendmail(self, *ka, **kw):
        self.mails_sent += 1
        return {}

    def quit(*ka, **kw):
        pass


class SMTPServerTestCase(TestCase):
    """Tests for the SMTPServer model"""

    def setUp(self):
        self.server = SMTPServer.objects.create(name='Test SMTP',
                                                host='smtp.domain.com')
        self.server_2 = SMTPServer.objects.create(name='Test SMTP 2',
                                                  host='smtp.domain2.com')
        self.contact = Contact.objects.create(email='test@domain.com')
        self.mailinglist = MailingList.objects.create(name='Test MailingList')
        self.mailinglist.subscribers.add(self.contact)
        self.newsletter = Newsletter.objects.create(title='Test Newsletter',
                                                    content='Test Newsletter Content',
                                                    mailing_list=self.mailinglist,
                                                    server=self.server, slug='test-nl')

        self.newsletter_2 = Newsletter.objects.create(title='Test Newsletter 2',
                                                      content='Test Newsletter 2 Content',
                                                      mailing_list=self.mailinglist,
                                                      server=self.server, slug='test-nl-2')
        self.newsletter_3 = Newsletter.objects.create(title='Test Newsletter 2',
                                                      content='Test Newsletter 2 Content',
                                                      mailing_list=self.mailinglist,
                                                      server=self.server_2, slug='test-nl-3')

    def test_credits(self):
        # Testing unlimited account
        self.assertEquals(self.server.credits(), 10000)
        # Testing default limit
        self.server.mails_hour = 42
        self.assertEquals(self.server.credits(), 42)

        # Testing credits status, with multiple server case
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT)
        self.assertEquals(self.server.credits(), 41)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT_TEST)
        self.assertEquals(self.server.credits(), 40)
        # Testing with a fake status
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contact,
                                            status=ContactMailingStatus.ERROR)
        self.assertEquals(self.server.credits(), 40)
        # Testing with a second newsletter sharing the server
        ContactMailingStatus.objects.create(newsletter=self.newsletter_2,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT)
        self.assertEquals(self.server.credits(), 39)
        # Testing with a third newsletter with another server
        ContactMailingStatus.objects.create(newsletter=self.newsletter_3,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT)
        self.assertEquals(self.server.credits(), 39)

    def test_custom_headers(self):
        self.assertEquals(self.server.custom_headers, {})
        self.server.headers = 'key_1: val_1\r\nkey_2   :   val_2'
        self.assertEquals(len(self.server.custom_headers), 2)


class ContactTestCase(TestCase):
    """Tests for the Contact model"""

    def setUp(self):
        self.mailinglist_1 = MailingList.objects.create(name='Test MailingList')
        self.mailinglist_2 = MailingList.objects.create(name='Test MailingList 2')

    def test_unique(self):
        Contact(email='test@domain.com').save()
        self.assertRaises(IntegrityError, Contact(email='test@domain.com').save)

    def test_mail_format(self):
        contact = Contact(email='test@domain.com')
        self.assertEquals(contact.mail_format(), 'test@domain.com')
        contact = Contact(email='test@domain.com', first_name='Toto')
        self.assertEquals(contact.mail_format(), 'test@domain.com')
        contact = Contact(email='test@domain.com', first_name='Toto', last_name='Titi')
        self.assertEquals(contact.mail_format(), 'Titi Toto <test@domain.com>')

    def test_vcard_format(self):
        contact = Contact(email='test@domain.com', first_name='Toto', last_name='Titi')
        self.assertEquals(contact.vcard_format(), 'BEGIN:VCARD\r\nVERSION:3.0\r\n'\
                          'EMAIL;TYPE=INTERNET:test@domain.com\r\nFN:Toto Titi\r\n'\
                          'N:Titi;Toto;;;\r\nEND:VCARD\r\n')

    def test_subscriptions(self):
        contact = Contact.objects.create(email='test@domain.com')
        self.assertEquals(len(contact.subscriptions()), 0)

        self.mailinglist_1.subscribers.add(contact)
        self.assertEquals(len(contact.subscriptions()), 1)
        self.mailinglist_2.subscribers.add(contact)
        self.assertEquals(len(contact.subscriptions()), 2)

    def test_unsubscriptions(self):
        contact = Contact.objects.create(email='test@domain.com')
        self.assertEquals(len(contact.unsubscriptions()), 0)

        self.mailinglist_1.unsubscribers.add(contact)
        self.assertEquals(len(contact.unsubscriptions()), 1)
        self.mailinglist_2.unsubscribers.add(contact)
        self.assertEquals(len(contact.unsubscriptions()), 2)


class MailingListTestCase(TestCase):
    """Tests for the MailingList model"""

    def setUp(self):
        self.contact_1 = Contact.objects.create(email='test1@domain.com')
        self.contact_2 = Contact.objects.create(email='test2@domain.com', valid=False)
        self.contact_3 = Contact.objects.create(email='test3@domain.com', subscriber=False)
        self.contact_4 = Contact.objects.create(email='test4@domain.com')

    def test_subscribers_count(self):
        mailinglist = MailingList(name='Test MailingList')
        mailinglist.save()
        self.assertEquals(mailinglist.subscribers_count(), 0)
        mailinglist.subscribers.add(self.contact_1, self.contact_2, self.contact_3)
        self.assertEquals(mailinglist.subscribers_count(), 3)

    def test_unsubscribers_count(self):
        mailinglist = MailingList.objects.create(name='Test MailingList')
        self.assertEquals(mailinglist.unsubscribers_count(), 0)
        mailinglist.unsubscribers.add(self.contact_1, self.contact_2, self.contact_3)
        self.assertEquals(mailinglist.unsubscribers_count(), 3)

    def test_expedition_set(self):
        mailinglist = MailingList.objects.create(name='Test MailingList')
        self.assertEquals(len(mailinglist.expedition_set()), 0)
        mailinglist.subscribers.add(self.contact_1, self.contact_2, self.contact_3)
        self.assertEquals(len(mailinglist.expedition_set()), 1)
        mailinglist.subscribers.add(self.contact_4)
        self.assertEquals(len(mailinglist.expedition_set()), 2)
        mailinglist.unsubscribers.add(self.contact_4)
        self.assertEquals(len(mailinglist.expedition_set()), 1)


class NewsletterTestCase(TestCase):
    """Tests for the Newsletter model"""

    def setUp(self):
        self.server = SMTPServer.objects.create(name='Test SMTP',
                                                host='smtp.domain.com')
        self.contact = Contact.objects.create(email='test@domain.com')
        self.mailinglist = MailingList.objects.create(name='Test MailingList')
        self.newsletter = Newsletter.objects.create(title='Test Newsletter',
                                                    content='Test Newsletter Content',
                                                    mailing_list=self.mailinglist,
                                                    server=self.server)

    def test_mails_sent(self):
        self.assertEquals(self.newsletter.mails_sent(), 0)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contact,
                                            status=ContactMailingStatus.SENT_TEST)
        self.assertEquals(self.newsletter.mails_sent(), 1)


class TokenizationTestCase(TestCase):
    """Tests for the tokenization process"""

    def setUp(self):
        self.contact = Contact.objects.create(email='test@domain.com')

    def test_tokenize_untokenize(self):
        uidb36, token = tokenize(self.contact)
        self.assertEquals(untokenize(uidb36, token), self.contact)
        self.assertRaises(Http404, untokenize, 'toto', token)
        self.assertRaises(Http404, untokenize, uidb36, 'toto')


class MailerTestCase(TestCase):
    """Tests for the Mailer object"""

    def setUp(self):
        self.server = SMTPServer.objects.create(name='Test SMTP',
                                                host='smtp.domain.com',
                                                mails_hour=100)
        self.contacts = [Contact.objects.create(email='test1@domain.com'),
                         Contact.objects.create(email='test2@domain.com'),
                         Contact.objects.create(email='test3@domain.com'),
                         Contact.objects.create(email='test4@domain.com')]
        self.mailinglist = MailingList.objects.create(name='Test MailingList')
        self.mailinglist.subscribers.add(*self.contacts)
        self.newsletter = Newsletter.objects.create(title='Test Newsletter',
                                                    content='Test Newsletter Content',
                                                    slug='test-newsletter',
                                                    mailing_list=self.mailinglist,
                                                    server=self.server,
                                                    status=Newsletter.WAITING)
        self.newsletter.test_contacts.add(*self.contacts[:2])
        self.attachment = Attachment.objects.create(newsletter=self.newsletter,
                                                    title='Test attachment',
                                                    file_attachment=File(NamedTemporaryFile()))

    def test_expedition_list(self):
        mailer = Mailer(self.newsletter, test=True)
        self.assertEquals(len(mailer.expedition_list), 2)
        self.server.mails_hour = 1
        self.assertEquals(len(mailer.expedition_list), 1)

        self.server.mails_hour = 100
        mailer = Mailer(self.newsletter)
        self.assertEquals(len(mailer.expedition_list), 4)
        self.server.mails_hour = 3
        self.assertEquals(len(mailer.expedition_list), 3)

        self.server.mails_hour = 100
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.SENT)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.SENT)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.SENT)
        self.assertEquals(len(mailer.expedition_list), 2)
        self.assertFalse(self.contacts[0] in mailer.expedition_list)

    def test_can_send(self):
        mailer = Mailer(self.newsletter)
        self.assertTrue(mailer.can_send)

        # Checks credits
        self.server.mails_hour = 1
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.SENT)
        mailer = Mailer(self.newsletter)
        self.assertFalse(mailer.can_send)
        self.server.mails_hour = 10
        mailer = Mailer(self.newsletter)
        self.assertTrue(mailer.can_send)

        # Checks statut
        self.newsletter.status = Newsletter.DRAFT
        mailer = Mailer(self.newsletter)
        self.assertFalse(mailer.can_send)
        mailer = Mailer(self.newsletter, test=True)
        self.assertTrue(mailer.can_send)

        # Checks expedition time
        self.newsletter.status = Newsletter.WAITING
        self.newsletter.sending_date = datetime.now() + timedelta(hours=1)
        mailer = Mailer(self.newsletter)
        self.assertFalse(mailer.can_send)
        self.newsletter.sending_date = datetime.now()
        mailer = Mailer(self.newsletter)
        self.assertTrue(mailer.can_send)

    def test_run(self):
        mailer = Mailer(self.newsletter)
        mailer.smtp = FakeSMTP()
        mailer.run()
        self.assertEquals(mailer.smtp.mails_sent, 4)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.SENT, newsletter=self.newsletter).count(), 4)

        mailer = Mailer(self.newsletter, test=True)
        mailer.smtp = FakeSMTP()

        mailer.run()
        self.assertEquals(mailer.smtp.mails_sent, 2)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.SENT_TEST, newsletter=self.newsletter).count(), 2)

        mailer.smtp = None

    def test_update_newsletter_status(self):
        mailer = Mailer(self.newsletter, test=True)
        self.assertEquals(self.newsletter.status, Newsletter.WAITING)
        mailer.update_newsletter_status()
        self.assertEquals(self.newsletter.status, Newsletter.WAITING)

        mailer = Mailer(self.newsletter)
        self.assertEquals(self.newsletter.status, Newsletter.WAITING)
        mailer.update_newsletter_status()
        self.assertEquals(self.newsletter.status, Newsletter.SENDING)

        for contact in self.contacts:
            ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                                contact=contact,
                                                status=ContactMailingStatus.SENT)
        mailer.update_newsletter_status()
        self.assertEquals(self.newsletter.status, Newsletter.SENT)

    def test_update_newsletter_status_advanced(self):
        self.server.mails_hour = 2
        self.server.save()

        mailer = Mailer(self.newsletter)
        mailer.smtp = FakeSMTP()
        mailer.run()

        self.assertEquals(mailer.smtp.mails_sent, 2)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.SENT, newsletter=self.newsletter).count(), 2)
        self.assertEquals(self.newsletter.status, Newsletter.SENDING)

        self.server.mails_hour = 0
        self.server.save()

        mailer = Mailer(self.newsletter)
        mailer.smtp = FakeSMTP()
        mailer.run()

        self.assertEquals(mailer.smtp.mails_sent, 2)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.SENT, newsletter=self.newsletter).count(), 4)
        self.assertEquals(self.newsletter.status, Newsletter.SENT)

    def test_recipients_refused(self):
        server = SMTPServer.objects.create(name='Local SMTP',
                                           host='localhost')
        contact = Contact.objects.create(email='thisisaninvalidemail')
        self.newsletter.test_contacts.clear()
        self.newsletter.test_contacts.add(contact)
        self.newsletter.server = server
        self.newsletter.save()

        self.assertEquals(contact.valid, True)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.INVALID, newsletter=self.newsletter).count(), 0)

        mailer = Mailer(self.newsletter, test=True)
        mailer.run()

        self.assertEquals(Contact.objects.get(email='thisisaninvalidemail').valid, False)
        self.assertEquals(ContactMailingStatus.objects.filter(
            status=ContactMailingStatus.INVALID, newsletter=self.newsletter).count(), 1)


class StatisticsTestCase(TestCase):
    """Tests for the statistics functions"""

    def setUp(self):
        self.server = SMTPServer.objects.create(name='Test SMTP',
                                                host='smtp.domain.com')
        self.contacts = [Contact.objects.create(email='test1@domain.com'),
                         Contact.objects.create(email='test2@domain.com'),
                         Contact.objects.create(email='test3@domain.com'),
                         Contact.objects.create(email='test4@domain.com')]
        self.mailinglist = MailingList.objects.create(name='Test MailingList')
        self.mailinglist.subscribers.add(*self.contacts)
        self.newsletter = Newsletter.objects.create(title='Test Newsletter',
                                                    content='Test Newsletter Content',
                                                    mailing_list=self.mailinglist,
                                                    server=self.server,
                                                    status=Newsletter.SENT)
        self.links = [Link.objects.create(title='link 1', url='htt://link.1'),
                      Link.objects.create(title='link 2', url='htt://link.2')]

        for contact in self.contacts:
            ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                                contact=contact,
                                                status=ContactMailingStatus.SENT)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.SENT_TEST)

        self.recipients = len(self.contacts)
        self.status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

    def test_get_newsletter_opening_statistics(self):
        stats = get_newsletter_opening_statistics(self.status, self.recipients)
        self.assertEquals(stats['total_openings'], 0)
        self.assertEquals(stats['unique_openings'], 0)
        self.assertEquals(stats['double_openings'], 0)
        self.assertEquals(stats['unique_openings_percent'], 0)
        self.assertEquals(stats['unknow_openings'], 0)
        self.assertEquals(stats['unknow_openings_percent'], 0)
        self.assertEquals(stats['opening_average'], 0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            status=ContactMailingStatus.LINK_OPENED)
        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_opening_statistics(status, self.recipients)
        self.assertEquals(stats['total_openings'], 4)
        self.assertEquals(stats['unique_openings'], 3)
        self.assertEquals(stats['double_openings'], 1)
        self.assertEquals(stats['unique_openings_percent'], 75.0)
        self.assertEquals(stats['unknow_openings'], 1)
        self.assertEquals(stats['unknow_openings_percent'], 25.0)
        self.assertEquals(stats['opening_average'], 1.3333333333333333)
        self.assertEquals(stats['opening_deducted'], 0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[3],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[3],
                                            status=ContactMailingStatus.LINK_OPENED)
        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_opening_statistics(status, self.recipients)
        self.assertEquals(stats['total_openings'], 5)
        self.assertEquals(stats['unique_openings'], 4)
        self.assertEquals(stats['double_openings'], 1)
        self.assertEquals(stats['unique_openings_percent'], 100.0)
        self.assertEquals(stats['unknow_openings'], 0)
        self.assertEquals(stats['unknow_openings_percent'], 0.0)
        self.assertEquals(stats['opening_average'], 1.25)
        self.assertEquals(stats['opening_deducted'], 1)

    def test_get_newsletter_on_site_opening_statistics(self):
        stats = get_newsletter_on_site_opening_statistics(self.status)
        self.assertEquals(stats['total_on_site_openings'], 0)
        self.assertEquals(stats['unique_on_site_openings'], 0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_on_site_opening_statistics(status)
        self.assertEquals(stats['total_on_site_openings'], 4)
        self.assertEquals(stats['unique_on_site_openings'], 3)

    def test_get_newsletter_clicked_link_statistics(self):
        stats = get_newsletter_clicked_link_statistics(self.status, self.recipients, 0)
        self.assertEquals(stats['total_clicked_links'], 0)
        self.assertEquals(stats['total_clicked_links_percent'], 0)
        self.assertEquals(stats['double_clicked_links'], 0)
        self.assertEquals(stats['double_clicked_links_percent'], 0.0)
        self.assertEquals(stats['unique_clicked_links'], 0)
        self.assertEquals(stats['unique_clicked_links_percent'], 0)
        self.assertEquals(stats['clicked_links_by_openings'], 0.0)
        self.assertEquals(stats['clicked_links_average'], 0.0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[1],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[1],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_clicked_link_statistics(status, self.recipients, 3)
        self.assertEquals(stats['total_clicked_links'], 5)
        self.assertEquals(stats['total_clicked_links_percent'], 125.0)
        self.assertEquals(stats['double_clicked_links'], 2)
        self.assertEquals(stats['double_clicked_links_percent'], 50.0)
        self.assertEquals(stats['unique_clicked_links'], 3)
        self.assertEquals(stats['unique_clicked_links_percent'], 75.0)
        self.assertEquals(stats['clicked_links_by_openings'], 166.66666666666669)
        self.assertEquals(stats['clicked_links_average'], 1.6666666666666667)

    def test_get_newsletter_unsubscription_statistics(self):
        stats = get_newsletter_unsubscription_statistics(self.status, self.recipients)
        self.assertEquals(stats['total_unsubscriptions'], 0)
        self.assertEquals(stats['total_unsubscriptions_percent'], 0.0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)

        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_unsubscription_statistics(status, self.recipients)
        self.assertEquals(stats['total_unsubscriptions'], 2)
        self.assertEquals(stats['total_unsubscriptions_percent'], 50.0)

    def test_get_newsletter_unsubscription_statistics_fix_doublon(self):
        stats = get_newsletter_unsubscription_statistics(self.status, self.recipients)
        self.assertEquals(stats['total_unsubscriptions'], 0)
        self.assertEquals(stats['total_unsubscriptions_percent'], 0.0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)

        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_unsubscription_statistics(status, self.recipients)
        self.assertEquals(stats['total_unsubscriptions'], 2)
        self.assertEquals(stats['total_unsubscriptions_percent'], 50.0)

    def test_get_newsletter_top_links(self):
        stats = get_newsletter_top_links(self.status)
        self.assertEquals(stats['top_links'], [])

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[1],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        status = ContactMailingStatus.objects.filter(newsletter=self.newsletter)

        stats = get_newsletter_top_links(status)
        self.assertEquals(len(stats['top_links']), 2)
        self.assertEquals(stats['top_links'][0]['link'], self.links[0])
        self.assertEquals(stats['top_links'][0]['total_clicks'], 4)
        self.assertEquals(stats['top_links'][0]['unique_clicks'], 3)
        self.assertEquals(stats['top_links'][1]['link'], self.links[1])
        self.assertEquals(stats['top_links'][1]['total_clicks'], 1)
        self.assertEquals(stats['top_links'][1]['unique_clicks'], 1)

    def test_get_newsletter_statistics(self):
        stats = get_newsletter_statistics(self.newsletter)

        self.assertEquals(stats['clicked_links_average'], 0.0)
        self.assertEquals(stats['clicked_links_by_openings'], 0.0)
        self.assertEquals(stats['double_clicked_links'], 0)
        self.assertEquals(stats['double_clicked_links_percent'], 00.0)
        self.assertEquals(stats['double_openings'], 0)
        self.assertEquals(stats['mails_sent'], 4)
        self.assertEquals(stats['mails_to_send'], 4)
        self.assertEquals(stats['opening_average'], 0)
        self.assertEquals(stats['remaining_mails'], 0)
        self.assertEquals(stats['tests_sent'], 1)
        self.assertEquals(stats['top_links'], [])
        self.assertEquals(stats['total_clicked_links'], 0)
        self.assertEquals(stats['total_clicked_links_percent'], 0.0)
        self.assertEquals(stats['total_on_site_openings'], 0)
        self.assertEquals(stats['total_openings'], 0)
        self.assertEquals(stats['total_unsubscriptions'], 0)
        self.assertEquals(stats['total_unsubscriptions_percent'], 0.0)
        self.assertEquals(stats['unique_clicked_links'], 0)
        self.assertEquals(stats['unique_clicked_links_percent'], 0.0)
        self.assertEquals(stats['unique_on_site_openings'], 0)
        self.assertEquals(stats['unique_openings'], 0)
        self.assertEquals(stats['unique_openings_percent'], 0)
        self.assertEquals(stats['unknow_openings'], 0)
        self.assertEquals(stats['unknow_openings_percent'], 0.0)

        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            status=ContactMailingStatus.OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            status=ContactMailingStatus.OPENED_ON_SITE)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[1],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            link=self.links[1],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[1],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[2],
                                            link=self.links[0],
                                            status=ContactMailingStatus.LINK_OPENED)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.UNSUBSCRIPTION)

        stats = get_newsletter_statistics(self.newsletter)

        self.assertEquals(stats['clicked_links_average'], 1.6666666666666667)
        self.assertEquals(stats['clicked_links_by_openings'], 100.0)
        self.assertEquals(stats['double_clicked_links'], 2)
        self.assertEquals(stats['double_clicked_links_percent'], 50.0)
        self.assertEquals(stats['double_openings'], 2)
        self.assertEquals(stats['mails_sent'], 4)
        self.assertEquals(stats['mails_to_send'], 4)
        self.assertEquals(stats['opening_average'], 1.6666666666666667)
        self.assertEquals(stats['remaining_mails'], 0)
        self.assertEquals(stats['tests_sent'], 1)
        self.assertEquals(stats['total_clicked_links'], 5)
        self.assertEquals(stats['total_clicked_links_percent'], 125.0)
        self.assertEquals(stats['total_on_site_openings'], 2)
        self.assertEquals(stats['total_openings'], 5)
        self.assertEquals(stats['total_unsubscriptions'], 1)
        self.assertEquals(stats['total_unsubscriptions_percent'], 25.0)
        self.assertEquals(stats['unique_clicked_links'], 3)
        self.assertEquals(stats['unique_clicked_links_percent'], 75.0)
        self.assertEquals(stats['unique_on_site_openings'], 2)
        self.assertEquals(stats['unique_openings'], 3)
        self.assertEquals(stats['unique_openings_percent'], 75)
        self.assertEquals(stats['unknow_openings'], 1)
        self.assertEquals(stats['unknow_openings_percent'], 25.0)

    def test_get_newsletter_statistics_division_by_zero(self):
        """Try to have a ZeroDivisionError by unsubscribing all contacts,
        and creating a ContactMailingStatus for more code coverage.
        Bug : http://github.com/Fantomas42/emencia-django-newsletter/issues#issue/9"""
        get_newsletter_statistics(self.newsletter)

        self.mailinglist.unsubscribers.add(*self.contacts)
        ContactMailingStatus.objects.create(newsletter=self.newsletter,
                                            contact=self.contacts[0],
                                            status=ContactMailingStatus.OPENED)
        get_newsletter_statistics(self.newsletter)

########NEW FILE########
__FILENAME__ = testsettings
"""Settings for testing emencia.django.newsletter"""

SITE_ID = 1

USE_I18N = False

ROOT_URLCONF = 'emencia.django.newsletter.urls'

DATABASES = {'default': {'NAME': 'newsletter_tests.db',
                         'ENGINE': 'django.db.backends.sqlite3'}}

INSTALLED_APPS = ['django.contrib.contenttypes',
                  'django.contrib.sites',
                  'django.contrib.auth',
                  'tagging',
                  'emencia.django.newsletter']

########NEW FILE########
__FILENAME__ = mailing_list
"""Urls for the emencia.django.newsletter Mailing List"""
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns

from emencia.django.newsletter.forms import MailingListSubscriptionForm
from emencia.django.newsletter.forms import AllMailingListSubscriptionForm

urlpatterns = patterns('emencia.django.newsletter.views.mailing_list',
                       url(r'^unsubscribe/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           'view_mailinglist_unsubscribe',
                           name='newsletter_mailinglist_unsubscribe'),
                       url(r'^subscribe/(?P<mailing_list_id>\d+)/',
                           'view_mailinglist_subscribe',
                           {'form_class': MailingListSubscriptionForm},
                           name='newsletter_mailinglist_subscribe'),
                       url(r'^subscribe/',
                           'view_mailinglist_subscribe',
                           {'form_class': AllMailingListSubscriptionForm},
                           name='newsletter_mailinglist_subscribe_all'),
                       )

########NEW FILE########
__FILENAME__ = newsletter
"""Urls for the emencia.django.newsletter Newsletter"""
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns

urlpatterns = patterns('emencia.django.newsletter.views.newsletter',
                       url(r'^preview/(?P<slug>[-\w]+)/$',
                           'view_newsletter_preview',
                           name='newsletter_newsletter_preview'),
                       url(r'^(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           'view_newsletter_contact',
                           name='newsletter_newsletter_contact'),
                       )

########NEW FILE########
__FILENAME__ = statistics
"""Urls for the emencia.django.newsletter statistics"""
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns

urlpatterns = patterns('emencia.django.newsletter.views.statistics',
                       url(r'^(?P<slug>[-\w]+)/$',
                           'view_newsletter_statistics',
                           name='newsletter_newsletter_statistics'),
                       url(r'^report/(?P<slug>[-\w]+)/$',
                           'view_newsletter_report',
                           name='newsletter_newsletter_report'),
                       url(r'^charts/(?P<slug>[-\w]+)/$',
                           'view_newsletter_charts',
                           name='newsletter_newsletter_charts'),
                       url(r'^density/(?P<slug>[-\w]+)/$',
                           'view_newsletter_density',
                           name='newsletter_newsletter_density'),
                       )

########NEW FILE########
__FILENAME__ = tracking
"""Urls for the emencia.django.newsletter Tracking"""
from django.conf.urls.defaults import url
from django.conf.urls.defaults import patterns

urlpatterns = patterns('emencia.django.newsletter.views.tracking',
                       url(r'^newsletter/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)\.(?P<format>png|gif|jpg)$',
                           'view_newsletter_tracking',
                           name='newsletter_newsletter_tracking'),
                       url(r'^link/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/(?P<link_id>\d+)/$',
                           'view_newsletter_tracking_link',
                           name='newsletter_newsletter_tracking_link'),
                       url(r'^historic/(?P<slug>[-\w]+)/$',
                           'view_newsletter_historic',
                           name='newsletter_newsletter_historic'),
                       )

########NEW FILE########
__FILENAME__ = excel
"""ExcelResponse for emencia.django.newsletter"""
# Based on http://www.djangosnippets.org/snippets/1151/
import datetime

from django.http import HttpResponse
from django.db.models.query import QuerySet
from django.db.models.query import ValuesQuerySet


class ExcelResponse(HttpResponse):
    """ExcelResponse feeded by queryset"""

    def __init__(self, data, output_name='excel_data', headers=None,
                 force_csv=False, encoding='utf8'):
        valid_data = False
        if isinstance(data, ValuesQuerySet):
            data = list(data)
        elif isinstance(data, QuerySet):
            data = list(data.values())
        if hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                if headers is None:
                    headers = data[0].keys()
                data = [[row[col] for col in headers] for row in data]
                data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
        assert valid_data is True, "ExcelResponse requires a sequence of sequences"

        import StringIO
        output = StringIO.StringIO()
        # Excel has a limit on number of rows; if we have more than that, make a csv
        use_xls = False
        if len(data) <= 65536 and force_csv is not True:
            try:
                import xlwt
            except ImportError:
                pass
            else:
                use_xls = True
        if use_xls:
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')
            styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                      'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                      'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                      'default': xlwt.Style.default_style}
            for rowx, row in enumerate(data):
                for colx, value in enumerate(row):
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    else:
                        cell_style = styles['default']
                    sheet.write(rowx, colx, value, style=cell_style)
            book.save(output)
            mimetype = 'application/vnd.ms-excel'
            file_ext = 'xls'
        else:
            for row in data:
                out_row = []
                for value in row:
                    if not isinstance(value, basestring):
                        value = unicode(value)
                    value = value.encode(encoding)
                    out_row.append(value.replace('"', '""'))
                output.write('"%s"\n' %
                             '","'.join(out_row))
            mimetype = 'text/csv'
            file_ext = 'csv'
        output.seek(0)
        super(ExcelResponse, self).__init__(content=output.getvalue(),
                                            mimetype=mimetype)
        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), file_ext)

########NEW FILE########
__FILENAME__ = importation
"""Utils for importation of contacts"""
import csv
from datetime import datetime

import xlrd
import vobject

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from tagging.models import Tag

from emencia.django.newsletter.models import Contact
from emencia.django.newsletter.models import MailingList


COLUMNS = ['email', 'first_name', 'last_name', 'tags']
csv.register_dialect('edn', delimiter=';')


def create_contact(contact_dict, workgroups=[]):
    """Create a contact and validate the mail"""
    contact_dict['email'] = contact_dict['email'].strip()
    try:
        validate_email(contact_dict['email'])
        contact_dict['valid'] = True
    except ValidationError:
        contact_dict['valid'] = False

    contact, created = Contact.objects.get_or_create(
        email=contact_dict['email'],
        defaults=contact_dict)

    if not created:
        new_tags = contact_dict.get('tags')
        if new_tags:
            Tag.objects.update_tags(contact, '%s, %s' % (contact.tags, new_tags))

    for workgroup in workgroups:
        workgroup.contacts.add(contact)

    return contact, created


def create_contacts(contact_dicts, importer_name, workgroups=[]):
    """Create all the contacts to import and
    associated them in a mailing list"""
    inserted = 0
    when = str(datetime.now()).split('.')[0]
    mailing_list = MailingList(
        name=_('Mailing list created by importation at %s') % when,
        description=_('Contacts imported by %s.') % importer_name)
    mailing_list.save()

    for workgroup in workgroups:
        workgroup.mailinglists.add(mailing_list)

    for contact_dict in contact_dicts:
        contact, created = create_contact(contact_dict, workgroups)
        mailing_list.subscribers.add(contact)
        inserted += int(created)

    return inserted


def vcard_contacts_import(stream, workgroups=[]):
    """Import contacts from a VCard file"""
    contacts = []
    vcards = vobject.readComponents(stream)

    for vcard in vcards:
        contact = {'email': vcard.email.value,
                   'first_name': vcard.n.value.given,
                   'last_name': vcard.n.value.family}
        contacts.append(contact)

    return create_contacts(contacts, 'vcard', workgroups)


def text_contacts_import(stream, workgroups=[]):
    """Import contact from a plaintext file, like CSV"""
    contacts = []
    contact_reader = csv.reader(stream, dialect='edn')

    for contact_row in contact_reader:
        contact = {}
        for i in range(len(contact_row)):
            contact[COLUMNS[i]] = contact_row[i]
        contacts.append(contact)

    return create_contacts(contacts, 'text', workgroups)


def excel_contacts_import(stream, workgroups=[]):
    """Import contacts from an Excel file"""
    contacts = []
    wb = xlrd.open_workbook(file_contents=stream.read())
    sh = wb.sheet_by_index(0)

    for row in range(sh.nrows):
        contact = {}
        for i in range(len(COLUMNS)):
            try:
                value = sh.cell(row, i).value
                contact[COLUMNS[i]] = value
            except IndexError:
                break
        contacts.append(contact)

    return create_contacts(contacts, 'excel', workgroups)


def import_dispatcher(source, type_, workgroups):
    """Select importer and import contacts"""
    if type_ == 'vcard':
        return vcard_contacts_import(source, workgroups)
    elif type_ == 'text':
        return text_contacts_import(source, workgroups)
    elif type_ == 'excel':
        return excel_contacts_import(source, workgroups)
    return 0

########NEW FILE########
__FILENAME__ = newsletter
"""Utils for newsletter"""
from BeautifulSoup import BeautifulSoup
from django.core.urlresolvers import reverse

from emencia.django.newsletter.models import Link
from emencia.django.newsletter.settings import USE_PRETTIFY


def body_insertion(content, insertion, end=False):
    """Insert an HTML content into the body HTML node"""
    if not content.startswith('<body'):
        content = '<body>%s</body>' % content
    soup = BeautifulSoup(content)

    if end:
        soup.body.append(insertion)
    else:
        soup.body.insert(0, insertion)

    if USE_PRETTIFY:
        return soup.prettify()
    else:
        return soup.renderContents()


def track_links(content, context):
    """Convert all links in the template for the user
    to track his navigation"""
    if not context.get('uidb36'):
        return content

    soup = BeautifulSoup(content)
    for link_markup in soup('a'):
        if link_markup.get('href') and \
               'no-track' not in link_markup.get('rel', ''):
            link_href = link_markup['href']
            link_title = link_markup.get('title', link_href)
            link, created = Link.objects.get_or_create(url=link_href,
                                                       defaults={'title': link_title})
            link_markup['href'] = 'http://%s%s' % (context['domain'], reverse('newsletter_newsletter_tracking_link',
                                                                              args=[context['newsletter'].slug,
                                                                                    context['uidb36'], context['token'],
                                                                                    link.pk]))
    if USE_PRETTIFY:
        return soup.prettify()
    else:
        return soup.renderContents()

########NEW FILE########
__FILENAME__ = ofc
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Author: Eugene Kin Chee Yip
# Date:   16 January 2010
# Modified by: Fantomas42

import copy

from django.utils.simplejson import dumps


class Chart(dict):
    replaceKeyDictionary = {
        'on_show': 'on-show', 'on_click': 'on-click',
        'start_angle': 'start-angle', 'javascript_function': 'javascript-function',
        'threeD': '3d', 'tick_height': 'tick-height',
        'grid_colour': 'grid-colour', 'tick_length': 'tick-length',
        'spoke_labels': 'spoke-labels', 'barb_length': 'barb-length',
        'dot_style': 'dot-style', 'dot_size': 'dot-size',
        'halo_size': 'halo-size', 'line_style': 'line-style',
        'outline_colour': 'outline-colour', 'fill_alpha': 'fill-alpha',
        'gradient_fill': 'gradient-fill', 'negative_colour': 'negative-colour'}

    def __init__(self, *ka, **kw):
        for key, value in kw.items():
            self.__dict__[key] = value

    def __getattribute__(self, key):
        try:
            return dict.__getattribute__(self, key)
        except AttributeError:
            self.__dict__[key] = Chart()
            return dict.__getattribute__(self, key)

    def __copy__(self):
        attributes = dict()
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                attributes[self.replaceKey(key)] = [copy.copy(item) for item in value]
            else:
                attributes[self.replaceKey(key)] = copy.copy(value)
        return attributes

    def replaceKey(self, key):
        if (key in self.replaceKeyDictionary):
            return self.replaceKeyDictionary[key]
        else:
            return key

    def render(self):
        attributes = copy.copy(self)
        return dumps(attributes)

########NEW FILE########
__FILENAME__ = premailer
"""Premailer for emencia.django.newsletter
Used for converting a page with CSS inline and links corrected.
Based on http://www.peterbe.com/plog/premailer.py"""
import re
from urllib2 import urlopen
from lxml.html import parse
from lxml.html import tostring


_css_comments = re.compile(r'/\*.*?\*/', re.MULTILINE | re.DOTALL)
_regex = re.compile('((.*?){(.*?)})', re.DOTALL | re.M)
_semicolon_regex = re.compile(';(\s+)')
_colon_regex = re.compile(':(\s+)')


def _merge_styles(old, new, class_=''):
    """
    if ::
      old = 'font-size:1px; color: red'
    and ::
      new = 'font-size:2px; font-weight: bold'
    then ::
      return 'color: red; font-size:2px; font-weight: bold'

    In other words, the new style bits replace the old ones.

    The @class_ parameter can be something like ':hover' and if that
    is there, you split up the style with '{...} :hover{...}'
    Note: old could be something like '{...} ::first-letter{...}'
    """
    news = {}
    for k, v in [x.strip().split(':', 1) for x in new.split(';') if x.strip()]:
        news[k.strip()] = v.strip()

    groups = {}
    grouping_regex = re.compile('([:\-\w]*){([^}]+)}')
    grouped_split = grouping_regex.findall(old)
    if grouped_split:
        for old_class, old_content in grouped_split:
            olds = {}
            for k, v in [x.strip().split(':', 1)
                         for x in old_content.split(';') if x.strip()]:
                olds[k.strip()] = v.strip()
            groups[old_class] = olds
    else:
        olds = {}
        for k, v in [x.strip().split(':', 1)
                     for x in old.split(';') if x.strip()]:
            olds[k.strip()] = v.strip()
        groups[''] = olds

    # Perform the merge
    merged = news
    for k, v in groups.get(class_, {}).items():
        if k not in merged:
            merged[k] = v
    groups[class_] = merged

    if len(groups) == 1:
        return '; '.join(['%s:%s' % (k, v)
                          for (k, v) in groups.values()[0].items()])
    else:
        all = []
        for class_, mergeable in sorted(groups.items(),
                                        lambda x, y: cmp(x[0].count(':'), y[0].count(':'))):
            all.append('%s{%s}' % (class_,
                                   '; '.join(['%s:%s' % (k, v)
                                              for (k, v)
                                              in mergeable.items()])))
        return ' '.join([x for x in all if x != '{}'])


class PremailerError(Exception):
    pass


class Premailer(object):
    """Premailer for converting a webpage
    to be e-mail ready"""

    def __init__(self, url, include_star_selectors=False):
        self.url = url
        try:
            self.page = parse(self.url).getroot()
        except:
            raise PremailerError('Could not parse the html')

        self.include_star_selectors = include_star_selectors

    def transform(self):
        """Do some transformations to self.page
        for being e-mail compliant"""
        self.page.make_links_absolute(self.url)

        self.inline_rules(self.get_page_rules())
        self.clean_page()
        # Do it a second time for correcting
        # ressources added by inlining.
        # Will not work as expected if medias
        # are located in other domain.
        self.page.make_links_absolute(self.url)

        return tostring(self.page.body)

    def get_page_rules(self):
        """Retrieve CSS rules in the <style> markups
        and in the external CSS files"""
        rules = []
        for style in self.page.cssselect('style'):
            css_body = tostring(style)
            css_body = css_body.split('>')[1].split('</')[0]
            these_rules, these_leftover = self._parse_style_rules(css_body)
            rules.extend(these_rules)

        for external_css in self.page.cssselect('link'):
            attr = external_css.attrib
            if attr.get('rel', '').lower() == 'stylesheet' and \
                   attr.get('href'):
                media = attr.get('media', 'screen')
                for media_allowed in ('all', 'screen', 'projection'):
                    if media_allowed in media:
                        css = urlopen(attr['href']).read()
                        rules.extend(self._parse_style_rules(css)[0])
                        break

        return rules

    def inline_rules(self, rules):
        """Apply in the page inline the CSS rules"""
        for selector, style in rules:
            class_ = ''
            if ':' in selector:
                selector, class_ = re.split(':', selector, 1)
                class_ = ':%s' % class_

            for item in self.page.cssselect(selector):
                old_style = item.attrib.get('style', '')
                new_style = _merge_styles(old_style, style, class_)
                item.attrib['style'] = new_style
                self._style_to_basic_html_attributes(item, new_style)

    def clean_page(self):
        """Clean the page of useless parts"""
        for elem in self.page.xpath('//@class'):
            parent = elem.getparent()
            del parent.attrib['class']
        for elem in self.page.cssselect('style'):
            elem.getparent().remove(elem)
        for elem in self.page.cssselect('script'):
            elem.getparent().remove(elem)

    def _parse_style_rules(self, css_body):
        leftover = []
        rules = []
        css_body = _css_comments.sub('', css_body)
        for each in _regex.findall(css_body.strip()):
            __, selectors, bulk = each
            bulk = _semicolon_regex.sub(';', bulk.strip())
            bulk = _colon_regex.sub(':', bulk.strip())
            if bulk.endswith(';'):
                bulk = bulk[:-1]
            for selector in [x.strip()
                             for x in selectors.split(',') if x.strip()]:
                if ':' in selector:
                    # A pseudoclass
                    leftover.append((selector, bulk))
                    continue
                elif selector == '*' and not self.include_star_selectors:
                    continue

                rules.append((selector, bulk))

        return rules, leftover

    def _style_to_basic_html_attributes(self, element, style_content):
        """Given an element and styles like
        'background-color:red; font-family:Arial' turn some of that into HTML
        attributes. like 'bgcolor', etc.
        Note, the style_content can contain pseudoclasses like:
        '{color:red; border:1px solid green} :visited{border:1px solid green}'
        """
        if style_content.count('}') and \
          style_content.count('{') == style_content.count('{'):
            style_content = style_content.split('}')[0][1:]

        attributes = {}
        for key, value in [x.split(':') for x in style_content.split(';')
                           if len(x.split(':')) == 2]:
            key = key.strip()

            if key == 'text-align':
                attributes['align'] = value.strip()
            elif key == 'background-color':
                attributes['bgcolor'] = value.strip()
            elif key == 'width':
                value = value.strip()
                if value.endswith('px'):
                    value = value[:-2]
                attributes['width'] = value

        for key, value in attributes.items():
            if key in element.attrib:
                # Already set, don't dare to overwrite
                continue
            element.attrib[key] = value

########NEW FILE########
__FILENAME__ = statistics
"""Statistics for emencia.django.newsletter"""
from django.db.models import Q

from emencia.django.newsletter.models import ContactMailingStatus as Status


def smart_division(a, b):
    """Not a really smart division, but avoid
    to have ZeroDivisionError"""
    try:
        return float(a) / float(b)
    except ZeroDivisionError:
        return 0.0


def get_newsletter_opening_statistics(status, recipients):
    """Return opening statistics of a newsletter based on status"""
    openings = status.filter(Q(status=Status.OPENED) | Q(status=Status.OPENED_ON_SITE))

    openings_by_links_opened = len(set(status.filter(status=Status.LINK_OPENED).exclude(
        contact__in=openings.values_list('contact', flat=True)).values_list('contact', flat=True)))

    total_openings = openings.count() + openings_by_links_opened
    if total_openings:
        unique_openings = len(set(openings.values_list('contact', flat=True))) + openings_by_links_opened
        unique_openings_percent = smart_division(unique_openings, recipients) * 100
        unknow_openings = recipients - unique_openings
        unknow_openings_percent = smart_division(unknow_openings, recipients) * 100
        opening_average = smart_division(total_openings, unique_openings)
    else:
        unique_openings = unique_openings_percent = unknow_openings = \
                          unknow_openings_percent = opening_average = 0

    return {'total_openings': total_openings,
            'double_openings': total_openings - unique_openings,
            'unique_openings': unique_openings,
            'unique_openings_percent': unique_openings_percent,
            'unknow_openings': unknow_openings,
            'unknow_openings_percent': unknow_openings_percent,
            'opening_average': opening_average,
            'opening_deducted': openings_by_links_opened}


def get_newsletter_on_site_opening_statistics(status):
    """Return on site opening statistics of a newsletter based on status"""
    on_site_openings = status.filter(status=Status.OPENED_ON_SITE)
    total_on_site_openings = on_site_openings.count()
    unique_on_site_openings = len(set(on_site_openings.values_list('contact', flat=True)))

    return {'total_on_site_openings': total_on_site_openings,
            'unique_on_site_openings': unique_on_site_openings}


def get_newsletter_clicked_link_statistics(status, recipients, openings):
    """Return clicked link statistics of a newsletter based on status"""
    clicked_links = status.filter(status=Status.LINK_OPENED)

    total_clicked_links = clicked_links.count()
    total_clicked_links_percent = smart_division(total_clicked_links, recipients) * 100

    unique_clicked_links = len(set(clicked_links.values_list('contact', flat=True)))
    unique_clicked_links_percent = smart_division(unique_clicked_links, recipients) * 100

    double_clicked_links = total_clicked_links - unique_clicked_links
    double_clicked_links_percent = smart_division(double_clicked_links, recipients) * 100

    clicked_links_by_openings = openings and smart_division(total_clicked_links, openings) * 100 or 0.0

    clicked_links_average = total_clicked_links and smart_division(total_clicked_links, unique_clicked_links) or 0.0

    return {'total_clicked_links': total_clicked_links,
            'total_clicked_links_percent': total_clicked_links_percent,
            'double_clicked_links': double_clicked_links,
            'double_clicked_links_percent': double_clicked_links_percent,
            'unique_clicked_links': unique_clicked_links,
            'unique_clicked_links_percent': unique_clicked_links_percent,
            'clicked_links_by_openings': clicked_links_by_openings,
            'clicked_links_average': clicked_links_average}


def get_newsletter_unsubscription_statistics(status, recipients):
    unsubscriptions = status.filter(status=Status.UNSUBSCRIPTION)

    #Patch: multiple unsubsriptions logs could exist before a typo bug was corrected, a 'set' is needed
    total_unsubscriptions = len(set(unsubscriptions.values_list('contact', flat=True)))
    total_unsubscriptions_percent = smart_division(total_unsubscriptions, recipients) * 100

    return {'total_unsubscriptions': total_unsubscriptions,
            'total_unsubscriptions_percent': total_unsubscriptions_percent}


def get_newsletter_top_links(status):
    """Return the most clicked links"""
    links = {}
    clicked_links = status.filter(status=Status.LINK_OPENED)

    for cl in clicked_links:
        links.setdefault(cl.link, 0)
        links[cl.link] += 1

    top_links = []
    for link, score in sorted(links.iteritems(), key=lambda (k, v): (v, k), reverse=True):
        unique_clicks = len(set(clicked_links.filter(link=link).values_list('contact', flat=True)))
        top_links.append({'link': link,
                          'total_clicks': score,
                          'unique_clicks': unique_clicks})

    return {'top_links': top_links}


def get_newsletter_statistics(newsletter):
    """Return the statistics of a newsletter"""
    recipients = newsletter.mailing_list.expedition_set().count()
    all_status = Status.objects.filter(newsletter=newsletter)
    post_sending_status = all_status.filter(creation_date__gte=newsletter.sending_date)
    mails_sent = post_sending_status.filter(status=Status.SENT).count()

    statistics = {'tests_sent': all_status.filter(status=Status.SENT_TEST).count(),
                  'mails_sent': mails_sent,
                  'mails_to_send': recipients,
                  'remaining_mails': recipients - mails_sent}

    statistics.update(get_newsletter_opening_statistics(post_sending_status, recipients))
    statistics.update(get_newsletter_on_site_opening_statistics(post_sending_status))
    statistics.update(get_newsletter_unsubscription_statistics(post_sending_status, recipients))
    statistics.update(get_newsletter_clicked_link_statistics(post_sending_status, recipients,
                                                             statistics['total_openings']))
    statistics.update(get_newsletter_top_links(post_sending_status))

    return statistics

########NEW FILE########
__FILENAME__ = tokens
"""Tokens system for emencia.django.newsletter"""
from django.conf import settings
from django.http import Http404
from django.utils.http import int_to_base36, base36_to_int

from emencia.django.newsletter.models import Contact


class ContactTokenGenerator(object):
    """ContactTokengenerator for the newsletter
    based on the PasswordResetTokenGenerator bundled
    in django.contrib.auth"""

    def make_token(self, contact):
        """Method for generating the token"""
        from django.utils.hashcompat import sha_constructor

        token = sha_constructor(settings.SECRET_KEY + unicode(contact.id) +
                                contact.email).hexdigest()[::2]
        return token

    def check_token(self, contact, token):
        """Check if the token is correct for this user"""
        return token == self.make_token(contact)


def tokenize(contact):
    """Return the uid in base 36 of a contact, and a token"""
    token_generator = ContactTokenGenerator()
    return int_to_base36(contact.id), token_generator.make_token(contact)


def untokenize(uidb36, token):
    """Retrieve a contact by uidb36 and token"""
    try:
        contact_id = base36_to_int(uidb36)
        contact = Contact.objects.get(pk=contact_id)
    except:
        raise Http404

    token_generator = ContactTokenGenerator()
    if token_generator.check_token(contact, token):
        return contact
    raise Http404

########NEW FILE########
__FILENAME__ = vcard
"""VCard system for exporting Contact models"""
from datetime import datetime

import vobject

from django.http import HttpResponse


def vcard_contact_export(contact):
    """Export in VCard 3.0 a Contact model instance"""
    if hasattr(contact.content_object, 'vcard_export'):
        return contact.content_object.vcard_export()

    vcard = vobject.vCard()
    vcard.add('n')
    vcard.n.value = vobject.vcard.Name(family=contact.last_name, given=contact.first_name)
    vcard.add('fn')
    vcard.fn.value = '%s %s' % (contact.first_name, contact.last_name)
    vcard.add('email')
    vcard.email.value = contact.email
    vcard.email.type_param = 'INTERNET'
    return vcard.serialize()


def vcard_contacts_export(contacts):
    """Export multiples contacts in VCard"""
    export = ''
    for contact in contacts:
        export += '%s\r\n' % vcard_contact_export(contact)
    return export


def vcard_contacts_export_response(contacts, filename=''):
    """Return VCard contacts attached in a HttpResponse"""
    if not filename:
        filename = 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y')
    filename = filename.replace(' ', '_')

    response = HttpResponse(vcard_contacts_export(contacts),
                            mimetype='text/x-vcard')
    response['Content-Disposition'] = 'attachment; filename=%s.vcf' % filename
    return response

########NEW FILE########
__FILENAME__ = workgroups
"""Utils for workgroups"""
from emencia.django.newsletter.models import WorkGroup


def request_workgroups(request):
    return WorkGroup.objects.filter(group__in=request.user.groups.all())


def request_workgroups_contacts_pk(request):
    contacts = []
    for workgroup in request_workgroups(request):
        contacts.extend([c.pk for c in workgroup.contacts.all()])
    return set(contacts)


def request_workgroups_mailinglists_pk(request):
    mailinglists = []
    for workgroup in request_workgroups(request):
        mailinglists.extend([ml.pk for ml in workgroup.mailinglists.all()])
    return set(mailinglists)


def request_workgroups_newsletters_pk(request):
    newsletters = []
    for workgroup in request_workgroups(request):
        newsletters.extend([n.pk for n in workgroup.newsletters.all()])
    return set(newsletters)

########NEW FILE########
__FILENAME__ = mailing_list
"""Views for emencia.django.newsletter Mailing List"""
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response

from emencia.django.newsletter.utils.tokens import untokenize
from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import MailingList
from emencia.django.newsletter.models import ContactMailingStatus


def view_mailinglist_unsubscribe(request, slug, uidb36, token):
    """Unsubscribe a contact to a mailing list"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)

    already_unsubscribed = contact in newsletter.mailing_list.unsubscribers.all()

    if request.POST.get('email') and not already_unsubscribed:
        newsletter.mailing_list.unsubscribers.add(contact)
        newsletter.mailing_list.save()
        already_unsubscribed = True
        ContactMailingStatus.objects.create(newsletter=newsletter, contact=contact,
                                            status=ContactMailingStatus.UNSUBSCRIPTION)

    return render_to_response('newsletter/mailing_list_unsubscribe.html',
                              {'email': contact.email,
                               'already_unsubscribed': already_unsubscribed},
                              context_instance=RequestContext(request))


def view_mailinglist_subscribe(request, form_class, mailing_list_id=None):
    """
    A simple view that shows a form for subscription
    for a mailing list(s).
    """
    subscribed = False
    mailing_list = None
    if mailing_list_id:
        mailing_list = get_object_or_404(MailingList, id=mailing_list_id)

    if request.POST and not subscribed:
        form = form_class(request.POST)
        if form.is_valid():
            form.save(mailing_list)
            subscribed = True
    else:
        form = form_class()

    return render_to_response('newsletter/mailing_list_subscribe.html',
                              {'subscribed': subscribed,
                               'mailing_list': mailing_list,
                               'form': form},
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = newsletter
"""Views for emencia.django.newsletter Newsletter"""
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response

from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string as render_file

from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import ContactMailingStatus
from emencia.django.newsletter.utils import render_string
from emencia.django.newsletter.utils.newsletter import body_insertion
from emencia.django.newsletter.utils.newsletter import track_links
from emencia.django.newsletter.utils.tokens import untokenize
from emencia.django.newsletter.settings import TRACKING_LINKS


def render_newsletter(request, slug, context):
    """Return a newsletter in HTML format"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    context.update({'newsletter': newsletter,
                    'domain': Site.objects.get_current().domain})

    content = render_string(newsletter.content, context)
    title = render_string(newsletter.title, context)
    if TRACKING_LINKS:
        content = track_links(content, context)
    unsubscription = render_file('newsletter/newsletter_link_unsubscribe.html', context)
    content = body_insertion(content, unsubscription, end=True)

    return render_to_response('newsletter/newsletter_detail.html',
                              {'content': content,
                               'title': title,
                               'object': newsletter},
                              context_instance=RequestContext(request))


@login_required
def view_newsletter_preview(request, slug):
    """View of the newsletter preview"""
    context = {'contact': request.user}
    return render_newsletter(request, slug, context)


def view_newsletter_contact(request, slug, uidb36, token):
    """Visualization of a newsletter by an user"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.OPENED_ON_SITE)
    context = {'contact': contact,
               'uidb36': uidb36, 'token': token}

    return render_newsletter(request, slug, context)

########NEW FILE########
__FILENAME__ = statistics
"""Views for emencia.django.newsletter statistics"""
import csv
from datetime import timedelta

from django.db.models import Q
from django.http import HttpResponse
from django.template import RequestContext
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template.defaultfilters import date

from emencia.django.newsletter.utils.ofc import Chart
from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.models import ContactMailingStatus
from emencia.django.newsletter.utils.statistics import get_newsletter_top_links
from emencia.django.newsletter.utils.statistics import get_newsletter_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_opening_statistics
from emencia.django.newsletter.utils.statistics import get_newsletter_clicked_link_statistics

BG_COLOR = '#ffffff'
GRID_COLOR = '#eeeeee'
AXIS_COLOR = '#666666'
BAR_COLOR_1 = '#5b80b2'
BAR_COLOR_2 = '#ff3333'
BAR_COLOR_3 = '#9459b4'
BAR_COLOR_4 = '#5eca71'


def get_statistics_period(newsletter):
    status = ContactMailingStatus.objects.filter(Q(status=ContactMailingStatus.OPENED) |
                                                 Q(status=ContactMailingStatus.OPENED_ON_SITE) |
                                                 Q(status=ContactMailingStatus.LINK_OPENED),
                                                 newsletter=newsletter)
    if not status:
        return []
    start_date = newsletter.sending_date.date()
    end_date = status.latest('creation_date').creation_date.date()

    period = []
    for i in range((end_date - start_date).days + 1):
        period.append(start_date + timedelta(days=i))
    return period


@login_required
def view_newsletter_statistics(request, slug):
    """Display the statistics of a newsletters"""
    opts = Newsletter._meta
    newsletter = get_object_or_404(Newsletter, slug=slug)

    context = {'title': _('Statistics of %s') % newsletter.__unicode__(),
               'object': newsletter,
               'opts': opts,
               'object_id': newsletter.pk,
               'app_label': opts.app_label,
               'stats': get_newsletter_statistics(newsletter),
               'period': get_statistics_period(newsletter)}

    return render_to_response('newsletter/newsletter_statistics.html',
                              context, context_instance=RequestContext(request))


@login_required
def view_newsletter_report(request, slug):
    newsletter = get_object_or_404(Newsletter, slug=slug)
    status = ContactMailingStatus.objects.filter(newsletter=newsletter,
                                                 creation_date__gte=newsletter.sending_date)
    links = set([s.link for s in status.exclude(link=None)])

    def header_line(links):
        link_cols = [smart_str(link.title) for link in links]
        return [smart_str(_('first name')), smart_str(_('last name')),
                smart_str(_('email')), smart_str(_('openings'))] + link_cols

    def contact_line(contact, links):
        contact_status = status.filter(contact=contact)

        link_cols = [contact_status.filter(status=ContactMailingStatus.LINK_OPENED,
                                           link=link).count() for link in links]
        openings = contact_status.filter(Q(status=ContactMailingStatus.OPENED) |
                                         Q(status=ContactMailingStatus.OPENED_ON_SITE)).count()
        return [smart_str(contact.first_name), smart_str(contact.last_name),
                smart_str(contact.email), openings] + link_cols

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report-%s.csv' % newsletter.slug

    writer = csv.writer(response)
    writer.writerow(header_line(links))
    for contact in newsletter.mailing_list.expedition_set():
        writer.writerow(contact_line(contact, links))

    return response


@login_required
def view_newsletter_density(request, slug):
    newsletter = get_object_or_404(Newsletter, slug=slug)
    status = ContactMailingStatus.objects.filter(newsletter=newsletter,
                                                 creation_date__gte=newsletter.sending_date)
    context = {'object': newsletter,
               'top_links': get_newsletter_top_links(status)['top_links']}

    return render_to_response('newsletter/newsletter_density.html',
                              context, context_instance=RequestContext(request))


@login_required
def view_newsletter_charts(request, slug):
    newsletter = get_object_or_404(Newsletter, slug=slug)

    start = int(request.POST.get('start', 0))
    end = int(request.POST.get('end', 6))

    recipients = newsletter.mailing_list.expedition_set().count()

    sending_date = newsletter.sending_date.date()
    labels, clicks_by_day, openings_by_day = [], [], []

    for i in range(start, end + 1):
        day = sending_date + timedelta(days=i)
        day_status = ContactMailingStatus.objects.filter(newsletter=newsletter,
                                                         creation_date__day=day.day,
                                                         creation_date__month=day.month,
                                                         creation_date__year=day.year)

        opening_stats = get_newsletter_opening_statistics(day_status, recipients)
        click_stats = get_newsletter_clicked_link_statistics(day_status, recipients, 0)
        # Labels
        labels.append(date(day, 'D d M y').capitalize())
        # Values
        openings_by_day.append(opening_stats['total_openings'])
        clicks_by_day.append(click_stats['total_clicked_links'])

    b1 = Chart(type='bar_3d', colour=BAR_COLOR_1,
               text=_('Total openings'), tip=_('#val# openings'),
               on_show={'type': 'grow-up'}, values=openings_by_day)

    b2 = Chart(type='bar_3d', colour=BAR_COLOR_2,
               text=_('Total clicked links'), tip=_('#val# clicks'),
               on_show={'type': 'grow-up'}, values=clicks_by_day)

    chart = Chart(bg_colour=BG_COLOR)
    chart.title.text = _('Consultation histogram')
    chart.title.style = '{font-size: 16px; color: #666666; text-align: center; font-weight: bold;}'

    chart.y_axis = {'colour': AXIS_COLOR, 'grid-colour': GRID_COLOR,
                    'min': 0, 'max': max(openings_by_day + clicks_by_day) + 2,
                    'steps': max(openings_by_day) / 5}
    chart.x_axis = {'colour': AXIS_COLOR, 'grid-colour': GRID_COLOR,
                    '3d': 5, 'labels': {'labels': labels, 'rotate': 60}}
    chart.elements = [b1, b2]

    return HttpResponse(chart.render())

########NEW FILE########
__FILENAME__ = tracking
"""Views for emencia.django.newsletter Tracking"""
import base64
from urllib import urlencode
from urlparse import urlparse
from urlparse import urlunparse
# For Python < 2.6
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

from emencia.django.newsletter.models import Link
from emencia.django.newsletter.models import Newsletter
from emencia.django.newsletter.utils.tokens import untokenize
from emencia.django.newsletter.models import ContactMailingStatus
from emencia.django.newsletter.settings import USE_UTM_TAGS
from emencia.django.newsletter.settings import TRACKING_IMAGE


def view_newsletter_tracking(request, slug, uidb36, token, format):
    """Track the opening of the newsletter by requesting a blank img"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.OPENED)
    return HttpResponse(base64.b64decode(TRACKING_IMAGE),
                        mimetype='image/%s' % format)


def view_newsletter_tracking_link(request, slug, uidb36, token, link_id):
    """Track the opening of a link on the website"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    link = get_object_or_404(Link, pk=link_id)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.LINK_OPENED,
                                        link=link)
    if not USE_UTM_TAGS:
        return HttpResponseRedirect(link.url)

    url_parts = urlparse(link.url)
    query_dict = parse_qs(url_parts.query)
    query_dict.update({'utm_source': 'newsletter_%s' % newsletter.pk,
                       'utm_medium': 'mail',
                       'utm_campaign': smart_str(newsletter.title)})
    url = urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path,
                      url_parts.params, urlencode(query_dict), url_parts.fragment))
    return HttpResponseRedirect(url)


@login_required
def view_newsletter_historic(request, slug):
    """Display the historic of a newsletter"""
    opts = Newsletter._meta
    newsletter = get_object_or_404(Newsletter, slug=slug)

    context = {'title': _('Historic of %s') % newsletter.__unicode__(),
               'original': newsletter,
               'opts': opts,
               'object_id': newsletter.pk,
               'app_label': opts.app_label}
    return render_to_response('newsletter/newsletter_historic.html',
                              context, context_instance=RequestContext(request))

########NEW FILE########
