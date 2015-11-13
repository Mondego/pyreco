__FILENAME__ = admin
from django.contrib import admin

from localshop.apps.packages.models import Classifier, Package, Release, ReleaseFile


class ReleaseFileInline(admin.TabularInline):
    model = ReleaseFile


class PackageAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'created', 'modified', 'is_local']
    list_filter = ['is_local']
    search_fields = ['name']


class ReleaseAdmin(admin.ModelAdmin):
    inlines = [ReleaseFileInline]
    list_display = ['__unicode__', 'package', 'created', 'modified']
    list_filter = ['package']
    search_fields = ['version', 'package__name']
    ordering = ['-created', 'version']


class ReleaseFileAdmin(admin.ModelAdmin):
    list_filter = ['user', 'release__package']
    list_display = ['__unicode__', 'created', 'modified', 'md5_digest', 'url']


admin.site.register(Classifier)
admin.site.register(Package, PackageAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(ReleaseFile, ReleaseFileAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from localshop.apps.packages.models import Package


def sidebar(request):
    if not request.user.is_authenticated():
        return {'sidebar': {}}
    sidebar_local = (Package.objects
        .filter(is_local=True)
        .order_by('name')
        .all())

    return {
        'sidebar': {
            'local': sidebar_local
        }
    }

########NEW FILE########
__FILENAME__ = forms
from django import forms

from localshop.apps.packages import models


class PypiReleaseDataForm(forms.ModelForm):
    class Meta:
        model = models.Release
        exclude = ['classifiers', 'package', 'user', 'metadata_version']


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = models.Release
        exclude = ['classifiers', 'package', 'user']


class ReleaseFileForm(forms.ModelForm):
    class Meta:
        model = models.ReleaseFile
        exclude = ['size', 'release', 'filename', 'user']

    def __init__(self, *args, **kwargs):
        super(ReleaseFileForm, self).__init__(*args, **kwargs)
        self.fields['pyversion'] = self.fields.pop('python_version')
        self.fields['pyversion'].required = False

    def save(self, commit=True):
        obj = super(ReleaseFileForm, self).save(False)
        obj.python_version = self.cleaned_data['pyversion'] or 'source'
        if commit:
            obj.save()
        return obj

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Classifier'
        db.create_table('packages_classifier', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('packages', ['Classifier'])

        # Adding model 'Package'
        db.create_table('packages_package', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now, db_index=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=200, db_index=True)),
            ('is_local', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('update_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('packages', ['Package'])

        # Adding M2M table for field owners on 'Package'
        db.create_table('packages_package_owners', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('package', models.ForeignKey(orm['packages.package'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('packages_package_owners', ['package_id', 'user_id'])

        # Adding model 'Release'
        db.create_table('packages_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('author_email', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('download_url', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('home_page', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('license', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('metadata_version', self.gf('django.db.models.fields.CharField')(default=1.0, max_length=64)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(related_name='releases', to=orm['packages.Package'])),
            ('summary', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=512)),
        ))
        db.send_create_signal('packages', ['Release'])

        # Adding M2M table for field classifiers on 'Release'
        db.create_table('packages_release_classifiers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('release', models.ForeignKey(orm['packages.release'], null=False)),
            ('classifier', models.ForeignKey(orm['packages.classifier'], null=False))
        ))
        db.create_unique('packages_release_classifiers', ['release_id', 'classifier_id'])

        # Adding model 'ReleaseFile'
        db.create_table('packages_releasefile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='files', to=orm['packages.Release'])),
            ('size', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('filetype', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('distribution', self.gf('django.db.models.fields.files.FileField')(max_length=512)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('md5_digest', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('python_version', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=1024, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
        ))
        db.send_create_signal('packages', ['ReleaseFile'])

        # Adding unique constraint on 'ReleaseFile', fields ['release', 'filetype', 'python_version', 'filename']
        db.create_unique('packages_releasefile', ['release_id', 'filetype', 'python_version', 'filename'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'ReleaseFile', fields ['release', 'filetype', 'python_version', 'filename']
        db.delete_unique('packages_releasefile', ['release_id', 'filetype', 'python_version', 'filename'])

        # Deleting model 'Classifier'
        db.delete_table('packages_classifier')

        # Deleting model 'Package'
        db.delete_table('packages_package')

        # Removing M2M table for field owners on 'Package'
        db.delete_table('packages_package_owners')

        # Deleting model 'Release'
        db.delete_table('packages_release')

        # Removing M2M table for field classifiers on 'Release'
        db.delete_table('packages_release_classifiers')

        # Deleting model 'ReleaseFile'
        db.delete_table('packages_releasefile')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'packages.classifier': {
            'Meta': {'object_name': 'Classifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_local': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'update_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'packages.release': {
            'Meta': {'object_name': 'Release'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'author_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Classifier']", 'symmetrical': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'home_page': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'metadata_version': ('django.db.models.fields.CharField', [], {'default': '1.0', 'max_length': '64'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'filetype', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'distribution': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'filetype': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'md5_digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = models
import docutils.core
import logging
import os
from docutils.utils import SystemMessage
from shutil import copyfileobj
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete
from django.core.files import File
from django.core.files.storage import get_storage_class
from django.core.urlresolvers import reverse
from django.utils.functional import LazyObject
from django.utils.html import escape
from model_utils import Choices
from model_utils.fields import AutoCreatedField, AutoLastModifiedField

from localshop.apps.packages.signals import release_file_notfound
from localshop.apps.packages.utils import delete_files


logger = logging.getLogger(__name__)


class Classifier(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return self.name


class Package(models.Model):
    created = AutoCreatedField(db_index=True)

    modified = AutoLastModifiedField()

    name = models.SlugField(max_length=200, unique=True)

    #: Indicate if this package is local (a private package)
    is_local = models.BooleanField(default=False)

    #: Timestamp when we last retrieved the metadata
    update_timestamp = models.DateTimeField(null=True)

    owners = models.ManyToManyField(User)

    class Meta:
        ordering = ['name']
        permissions = (
            ("view_package", "Can view package"),
        )

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('packages:detail', None, {'name': self.name})

    def get_all_releases(self):
        result = {}
        for release in self.releases.all():
            files = dict((r.filename, r) for r in release.files.all())
            result[release.version] = (release, files)
        return result

    @property
    def last_release(self):
        return self.releases.order_by('-created')[0]


class Release(models.Model):

    created = AutoCreatedField()

    modified = AutoLastModifiedField()

    author = models.CharField(max_length=128, blank=True)

    author_email = models.CharField(max_length=255, blank=True)

    classifiers = models.ManyToManyField(Classifier)

    description = models.TextField(blank=True)

    download_url = models.CharField(max_length=200, blank=True, null=True)

    home_page = models.CharField(max_length=200, blank=True, null=True)

    license = models.TextField(blank=True)

    metadata_version = models.CharField(max_length=64, default=1.0)

    package = models.ForeignKey(Package, related_name="releases")

    summary = models.TextField(blank=True)

    user = models.ForeignKey(User, null=True)

    version = models.CharField(max_length=512)

    class Meta:
        ordering = ['-version']

    def __unicode__(self):
        return self.version

    @property
    def description_html(self):
        try:
            parts = docutils.core.publish_parts(
                self.description, writer_name='html4css1')
            return parts['fragment']
        except SystemMessage:
            desc = escape(self.description)
            return '<pre>%s</pre>' % desc


def release_file_upload_to(instance, filename):
    package = instance.release.package
    assert package.name and instance.python_version
    return os.path.join(
        instance.python_version,
        package.name[0],
        package.name,
        filename)


class DistributionStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(
            settings.LOCALSHOP_DISTRIBUTION_STORAGE)()


class ReleaseFile(models.Model):

    TYPES = Choices(
        ('sdist', 'Source'),
        ('bdist_egg', 'Egg'),
        ('bdist_msi', 'MSI'),
        ('bdist_dmg', 'DMG'),
        ('bdist_rpm', 'RPM'),
        ('bdist_dumb', 'bdist_dumb'),
        ('bdist_wininst', 'bdist_wininst'),
        ('bdist_wheel', 'bdist_wheel'),
    )

    created = AutoCreatedField()

    modified = AutoLastModifiedField()

    release = models.ForeignKey(Release, related_name="files")

    size = models.IntegerField(null=True)

    filetype = models.CharField(max_length=25, choices=TYPES)

    distribution = models.FileField(upload_to=release_file_upload_to,
        storage=DistributionStorage(), max_length=512)

    filename = models.CharField(max_length=200, blank=True, null=True)

    md5_digest = models.CharField(max_length=512)

    python_version = models.CharField(max_length=25)

    url = models.CharField(max_length=1024, blank=True)

    user = models.ForeignKey(User, null=True)

    class Meta:
        unique_together = ('release', 'filetype', 'python_version', 'filename')

    def __unicode__(self):
        return self.filename

    def get_absolute_url(self):
        url = reverse('packages:download', kwargs={
            'name': self.release.package.name,
            'pk': self.pk, 'filename': self.filename
        })
        return '%s#md5=%s' % (url, self.md5_digest)

    def save_filecontent(self, filename, fh):
        tmp_file = NamedTemporaryFile()
        copyfileobj(fh, tmp_file)
        self.distribution.save(filename, File(tmp_file))


if settings.LOCALSHOP_DELETE_FILES:
    post_delete.connect(
        delete_files, sender=ReleaseFile,
        dispatch_uid="localshop.apps.packages.utils.delete_files")


def download_missing_release_file(sender, release_file, **kwargs):
    """Start a celery task to download the release file from pypi.

    If `settings.LOCALSHOP_ISOLATED` is True then download the file in-process.

    """
    from .tasks import download_file
    if not settings.LOCALSHOP_ISOLATED:
        download_file.delay(pk=release_file.pk)
    else:
        download_file(pk=release_file.pk)

release_file_notfound.connect(download_missing_release_file,
    dispatch_uid='localshop_download_release_file')

########NEW FILE########
__FILENAME__ = pypi
# -*- coding: utf-8 -*-

import sys
import logging
import re
import xmlrpclib
import httplib
import requests
from copy import copy

from django.conf import settings

from localshop.utils import now
from localshop.apps.packages import forms
from localshop.apps.packages import models


logger = logging.getLogger(__name__)


class RequestTransport(xmlrpclib.Transport, object):

    def __init__(self, use_datetime=0, proxies=None):
        super(RequestTransport, self).__init__(use_datetime)
        self.session = requests.Session()
        self.configure_requests(proxies=proxies)

    def configure_requests(self, proxies=None):
        self.session.headers.update({
            'Content-Type': 'text/xml',
            'User-Agent': self.user_agent,
            'Accept-Encoding': 'identity',
        })
        self.session.proxies = copy(proxies)

    def set_proxy(self, proxies):
        self.session.proxies = copy(proxies)

    def request(self, host, handler, request_body, verbose=0):
        r = self.session.post('https://%s%s' % (host, handler), data=request_body)
        if r.status_code == 200:
            self.verbose = verbose
            from StringIO import StringIO
            s = StringIO(r.content)
            return self.parse_response(s)


def get_search_names(name):
    """Return a list of values to search on when we are looking for a package
    with the given name.

    This is required to search on both pyramid_debugtoolbar and
    pyramid-debugtoolbar.

    """
    parts = re.split('[-_]', name)
    if len(parts) == 1:
        return parts

    result = set()
    for i in range(len(parts) - 1, 0, -1):
        for s1 in '-_':
            prefix = s1.join(parts[:i])
            for s2 in '-_':
                suffix = s2.join(parts[i:])
                for s3 in '-_':
                    result.add(s3.join([prefix, suffix]))
    return list(result)


def get_package_data(name, package=None):
    """Retrieve metadata information for the given package name"""
    if not package:
        package = models.Package(name=name)
        releases = {}
    else:
        releases = package.get_all_releases()

    if settings.LOCALSHOP_HTTP_PROXY:
        proxy = RequestTransport()
        proxy.set_proxy(settings.LOCALSHOP_HTTP_PROXY)

        client = xmlrpclib.ServerProxy(
            settings.LOCALSHOP_PYPI_URL,transport=proxy)
    else:
        client = xmlrpclib.ServerProxy(settings.LOCALSHOP_PYPI_URL)

    versions = client.package_releases(package.name, True)

    # package_releases() method is case-sensitive, if nothing found
    # then we search for it
    # XXX: Ask pypi to make it case-insensitive?
    names = get_search_names(name)
    if not versions:
        for item in client.search({'name': names}):
            if item['name'].lower() in [n.lower() for n in names]:
                package.name = name = item['name']
                break
        else:
            logger.info("No packages found matching %r", name)
            return

        # Retry retrieving the versions with the new/correct name
        versions = client.package_releases(package.name, True)

    # If the matched package differs from the name we tried to retrieve then
    # retry to fetch the package from the database.
    if package.name != name:
        try:
            package = models.Package.objects.get(name=package.name)
        except models.Package.objects.DoesNotExist:
            pass

    # Save the package if it is new
    if not package.pk:
        package.save()

    for version in versions:
        release, files = releases.get(version, (None, {}))
        if not release:
            release = models.Release(package=package, version=version)
            release.save()

        data = client.release_data(package.name, release.version)

        release_form = forms.PypiReleaseDataForm(data, instance=release)
        if release_form.is_valid():
            release_form.save()

        release_files = client.package_urls(package.name, release.version)
        for info in release_files:
            release_file = files.get(info['filename'])
            if not release_file:
                release_file = models.ReleaseFile(
                    release=release, filename=info['filename'])

            release_file.python_version = info['python_version']
            release_file.filetype = info['packagetype']
            release_file.url = info['url']
            release_file.size = info['size']
            release_file.md5_digest = info['md5_digest']
            release_file.save()

    package.update_timestamp = now()
    package.save()
    return package

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

release_file_notfound = Signal(providing_args=["release_file"])

########NEW FILE########
__FILENAME__ = tasks
import mimetypes
import logging
import os

import requests
from celery.task import task
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile

from localshop.apps.packages import models
from localshop.apps.packages.pypi import get_package_data
from localshop.apps.packages.utils import md5_hash_file


@task
def download_file(pk):
    release_file = models.ReleaseFile.objects.get(pk=pk)
    logging.info("Downloading %s", release_file.url)

    proxies = None
    if settings.LOCALSHOP_HTTP_PROXY:
        proxies = settings.LOCALSHOP_HTTP_PROXY
    response = requests.get(release_file.url, stream=True, proxies=proxies)

    # Write the file to the django file field
    filename = os.path.basename(release_file.url)

    # Setting the size manually since Django can't figure it our from
    # the raw HTTPResponse
    if 'content-length' in response.headers:
        size = int(response.headers['content-length'])
    else:
        size = len(response.content)

    # Setting the content type by first looking at the response header
    # and falling back to guessing it from the filename
    default_content_type = 'application/octet-stream'
    content_type = response.headers.get('content-type')
    if content_type is None or content_type == default_content_type:
        content_type = mimetypes.guess_type(filename)[0] or default_content_type

    # Using Django's temporary file upload system to not risk memory
    # overflows
    with TemporaryUploadedFile(name=filename, size=size, charset='utf-8',
                               content_type=content_type) as temp_file:
        temp_file.write(response.content)
        temp_file.seek(0)

        # Validate the md5 hash of the downloaded file
        md5_hash = md5_hash_file(temp_file)
        if md5_hash != release_file.md5_digest:
            logging.error("MD5 hash mismatch: %s (expected: %s)" % (
                md5_hash, release_file.md5_digest))
            return

        release_file.distribution.save(filename, temp_file)
        release_file.save()
    logging.info("Complete")


@task
def update_packages():
    logging.info('Updated packages')
    for package in models.Package.objects.filter(is_local=False):
        logging.info('Updating package %s', package.name)
        get_package_data(package.name, package)
    logging.info('Complete')

########NEW FILE########
__FILENAME__ = factories
import factory

from localshop.apps.packages import models


class PackageFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Package

    name = 'test-package'


class ReleaseFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Release

    author = 'John Doe'
    author_email = 'j.doe@example.org'
    description = 'A test release'
    download_url = 'http://www.example.org/download'
    home_page = 'http://www.example.org'
    license = 'BSD'
    metadata_version = '1.0'
    package = factory.SubFactory(PackageFactory)
    summary = 'Summary of the test package'
    version = '1.0.0'


class ReleaseFileFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.ReleaseFile

    release = factory.SubFactory(ReleaseFactory)
    size = 1120
    filetype = 'sdist'
    filename = factory.LazyAttribute(lambda a: 'test-%s-%s.zip' % (
        a.release.version, a.filetype))
    md5_digest = '62ecd3ee980023db87945470aa2b347b'
    python_version = '2.7'
    url = factory.LazyAttribute(lambda a: (
        'http://www.example.org/download/%s' % a.filename))

########NEW FILE########
__FILENAME__ = test_models
import os.path
from cStringIO import StringIO

from django.test import TestCase

from storages.backends.overwrite import OverwriteStorage

from localshop.apps.packages import models
from localshop.apps.packages import utils
from localshop.apps.packages.tests import factories
from localshop.utils import TemporaryMediaRootMixin


class TestReleaseFile(TemporaryMediaRootMixin, TestCase):
    def setUp(self):
        super(TestReleaseFile, self).setUp()

        field = [field for field in models.ReleaseFile._meta.fields
                    if field.name == 'distribution'][0]
        field.storage = OverwriteStorage()

    def test_save_contents(self):
        release_file = factories.ReleaseFileFactory()

        dummy_fh = StringIO("release-file-contents")
        release_file.save_filecontent('dummy.txt', dummy_fh)

        self.assertEqual(
            release_file.distribution.name, '2.7/t/test-package/dummy.txt')
        self.assertTrue(os.path.exists(release_file.distribution.path))

    def test_delete_file(self):
        release_file = factories.ReleaseFileFactory()

        dummy_fh = StringIO("release-file-contents")
        release_file.save_filecontent('dummy.txt', dummy_fh)

        self.assertTrue(os.path.exists(release_file.distribution.path))

        utils.delete_files(models.ReleaseFile, instance=release_file)
        self.assertFalse(os.path.exists(release_file.distribution.path))

    def test_delete_file_twice_referenced(self):
        release_file = factories.ReleaseFileFactory()

        dummy_fh = StringIO("release-file-contents")
        release_file.save_filecontent('dummy.txt', dummy_fh)

        release_file = factories.ReleaseFileFactory(
            release=release_file.release, filetype='bdist_egg')
        release_file.save_filecontent('dummy.txt', dummy_fh)

        self.assertTrue(os.path.exists(release_file.distribution.path))

        utils.delete_files(models.ReleaseFile, instance=release_file)

        # File should still exist
        self.assertTrue(os.path.exists(release_file.distribution.path))

########NEW FILE########
__FILENAME__ = test_pypi
import datetime
import mock
from django.test import TestCase

from localshop.apps.packages import models


class TestPypi(TestCase):
    def test_get_package_data_new(self):
        from localshop.apps.packages.pypi import get_package_data

        with mock.patch('xmlrpclib.ServerProxy') as mock_obj:
            mock_obj.return_value = client = mock.Mock()
            client.package_releases.return_value = ['0.1', '0.2']

            def package_urls_side_effect(name, version):
                return [{
                    'comment_text': '',
                    'downloads': 1,
                    'filename': 'localshop-%s.tar.gz' % version,
                    'has_sig': True,
                    'md5_digest': '7ddf32e17a6ac5ce04a8ecbf782ca509',
                    'packagetype': 'sdist',
                    'python_version': 'source',
                    'size': 23232,
                    'upload_time': datetime.datetime(2012, 2, 2, 11, 32, 00),
                    'url': 'http://pypi.python.org/packages/source/r/'
                        'localshop/localshop-%s.tar.gz' % version
                }]
            client.package_urls.side_effect = package_urls_side_effect

            def release_data_side_effect(name, version):
                return  {
                    'maintainer': None,
                    'requires_python': None,
                    'maintainer_email': None,
                    'cheesecake_code_kwalitee_id': None,
                    'keywords': None,
                    'package_url': 'http://pypi.python.org/pypi/localshop',
                    'author': 'Michael van Tellingen',
                    'author_email': 'michaelvantellingen@gmail.com',
                    'download_url': 'UNKNOWN',
                    'platform': 'UNKNOWN',
                    'version': version,
                    'cheesecake_documentation_id': None,
                    '_pypi_hidden': False,
                    'description': "the-description",
                    'release_url': 'http://pypi.python.org/pypi/localshop/%s'
                        % version,
                    '_pypi_ordering': 12,
                    'classifiers': [],
                    'name': 'localshop',
                    'bugtrack_url': None,
                    'license': 'BSD',
                    'summary': 'Short summary',
                    'home_page': 'http://github.com/mvantellingen/localshop',
                    'stable_version': None,
                    'cheesecake_installability_id': None
                }
            client.release_data.side_effect = release_data_side_effect

            package = get_package_data('localshop')

        package = models.Package.objects.get(pk=package.pk)

        self.assertEqual(package.releases.count(), 2)
        self.assertTrue(package.releases.get(version='0.1'))
        self.assertTrue(package.releases.get(version='0.2'))

        self.assertEqual(package.releases.get(version='0.1').files.count(), 1)
        self.assertEqual(package.releases.get(version='0.2').files.count(), 1)

        info = package.releases.get(version='0.1').files.all()[0]
        self.assertEqual(info.filename, 'localshop-0.1.tar.gz')
        self.assertEqual(info.filetype, 'sdist')
        self.assertEqual(info.python_version, 'source')
        self.assertEqual(info.md5_digest, '7ddf32e17a6ac5ce04a8ecbf782ca509')
        self.assertEqual(info.size, 23232)
        self.assertEqual(info.url, 'http://pypi.python.org/packages/source/r/'
            'localshop/localshop-0.1.tar.gz')

    def test_get_package_data_wrong_case(self):
        from localshop.apps.packages.pypi import get_package_data

        with mock.patch('xmlrpclib.ServerProxy') as mock_obj:
            mock_obj.return_value = client = mock.Mock()

            def se_package_releases(name, show_hidden=False):
                """side_effect for package_releases"""
                if name == 'localshop':
                    return ['0.1']
                return []
            client.package_releases.side_effect = se_package_releases

            client.search.return_value = [
                {'name': 'localshop'}
            ]

            client.release_data.return_value = {
                'maintainer': None,
                'requires_python': None,
                'maintainer_email': None,
                'cheesecake_code_kwalitee_id': None,
                'keywords': None,
                'package_url': 'http://pypi.python.org/pypi/localshop',
                'author': 'Michael van Tellingen',
                'author_email': 'michaelvantellingen@gmail.com',
                'download_url': 'UNKNOWN',
                'platform': 'UNKNOWN',
                'version': '0.1',
                'cheesecake_documentation_id': None,
                '_pypi_hidden': False,
                'description': "the-description",
                'release_url': 'http://pypi.python.org/pypi/localshop/0.1',
                '_pypi_ordering': 12,
                'classifiers': [],
                'name': 'django-cofingo',
                'bugtrack_url': None,
                'license': 'BSD',
                'summary': 'Short summary',
                'home_page': 'http://github.com/mvantellingen/localshop',
                'stable_version': None,
                'cheesecake_installability_id': None
            }

            client.package_urls.return_value = [{
                    'comment_text': '',
                    'downloads': 1,
                    'filename': 'localshop-0.1.tar.gz',
                    'has_sig': True,
                    'md5_digest': '7ddf32e17a6ac5ce04a8ecbf782ca509',
                    'packagetype': 'sdist',
                    'python_version': 'source',
                    'size': 23232,
                    'upload_time': datetime.datetime(2012, 2, 2, 11, 32, 00),
                    'url': 'http://pypi.python.org/packages/source/r/'
                        'localshop/localshop-0.1.tar.gz'
                }]

            package = get_package_data('Localshop')

            client.search.called_with({'name': 'Localshop'})

        package = models.Package.objects.get(pk=package.pk)
        self.assertEqual(package.releases.count(), 1)

########NEW FILE########
__FILENAME__ = test_tasks
import mock
from django.test import TestCase

from localshop.apps.packages import tasks
from localshop.apps.packages import models


class TestTasks(TestCase):
    def test_download_file(self):
        package = models.Package.objects.create(name='localshop')
        release = models.Release.objects.create(package=package, version='0.1')
        release_file = models.ReleaseFile.objects.create(
            release=release,
            md5_digest='098f6bcd4621d373cade4e832627b4f6',
            python_version='source',
            url=(
                'http://pypi.python.org/packages/source/l/localshop/'
                'localshop-0.1.tar.gz'
            )
        )

        with mock.patch('requests.get') as mock_obj:
            mock_obj.return_value = mock.Mock()
            mock_obj.return_value.content = 'test'
            mock_obj.return_value.headers = {
                'content-length': 1024
            }
            tasks.download_file(release_file.pk)

        release_file = models.ReleaseFile.objects.get(pk=release_file.pk)
        self.assertEqual(release_file.distribution.read(), 'test')

        self.assertEqual(
            release_file.distribution.name,
            'source/l/localshop/localshop-0.1.tar.gz')

    def test_download_file_incorrect_md5_sum(self):
        package = models.Package.objects.create(name='localshop')
        release = models.Release.objects.create(package=package, version='0.1')
        release_file = models.ReleaseFile.objects.create(
            release=release,
            md5_digest='098f6bcd4621d373cade4e832627b4f6',
            python_version='source',
            url=(
                'http://pypi.python.org/packages/source/l/localshop/'
                'localshop-0.1.tar.gz'
            )
        )

        with mock.patch('requests.get') as mock_obj:
            mock_obj.return_value = mock.Mock()
            mock_obj.return_value.content = 'tes.'
            mock_obj.return_value.headers = {
                'content-length': 1024
            }
            tasks.download_file(release_file.pk)

        release_file = models.ReleaseFile.objects.get(pk=release_file.pk)
        self.assertFalse(release_file.distribution)

########NEW FILE########
__FILENAME__ = test_utils
from mock import Mock

from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from localshop.apps.packages.utils import parse_distutils_request


class TestParseDistutilsRequest(TestCase):
    def test_register_post(self):
        data = (
            '\n----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="license"\n\n'
            'BSD\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="name"\n\nlocalshop\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="metadata_version"\n\n'
            '1.0\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="author"\n\n'
            'Michael van Tellingen\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="home_page"\n\n'
            'http://github.com/mvantellingen/localshop\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name=":action"\n\n'
            'submit\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="download_url"\n\n'
            'UNKNOWN\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="summary"\n\n'
            'A private pypi server including auto-mirroring of pypi.\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="author_email"\n\n'
            'michaelvantellingen@gmail.com\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="version"\n\n'
            '0.1\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="platform"\n\n'
            'UNKNOWN\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Development Status :: 2 - Pre-Alpha\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Framework :: Django\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Intended Audience :: Developers\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Intended Audience :: System Administrators\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Operating System :: OS Independent\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="classifiers"\n\n'
            'Topic :: Software Development\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254\n'
            'Content-Disposition: form-data; name="description"\n\n'
            'UNKNOWN\n'
            '----------------GHSKFJDLGDS7543FJKLFHRE75642756743254--\n'
        )
        request = Mock()
        request.raw_post_data = data
        request.FILES = MultiValueDict()
        parse_distutils_request(request)

        expected_post = MultiValueDict({
            'name': ['localshop'],
            'license': ['BSD'],
            'author': ['Michael van Tellingen'],
            'home_page': ['http://github.com/mvantellingen/localshop'],
            ':action': ['submit'],
            'download_url': [None],
            'summary': [
                'A private pypi server including auto-mirroring of pypi.'],
            'author_email': ['michaelvantellingen@gmail.com'],
            'metadata_version': ['1.0'],
            'version': ['0.1'],
            'platform': [None],
            'classifiers': [
                'Development Status :: 2 - Pre-Alpha',
                'Framework :: Django',
                'Intended Audience :: Developers',
                'Intended Audience :: System Administrators',
                'Operating System :: OS Independent',
                'Topic :: Software Development'
            ],
            'description': [None]
        })
        expected_files = MultiValueDict()

        self.assertEqual(request.POST, expected_post)
        self.assertEqual(request.FILES, expected_files)

########NEW FILE########
__FILENAME__ = test_views
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from localshop.apps.packages import models
from localshop.apps.packages import views


class TestDistutilsViews(TestCase):

    def test_register_new(self):
        post = MultiValueDict({
            'name': ['localshop'],
            'license': ['BSD'],
            'author': ['Michael van Tellingen'],
            'home_page': ['http://github.com/mvantellingen/localshop'],
            ':action': ['submit'],
            'download_url': [None],
            'summary': [
                'A private pypi server including auto-mirroring of pypi.'],
            'author_email': ['michaelvantellingen@gmail.com'],
            'metadata_version': ['1.0'],
            'version': ['0.1'],
            'platform': [None],
            'classifiers': [
                'Development Status :: 2 - Pre-Alpha',
                'Framework :: Django',
                'Intended Audience :: Developers',
                'Intended Audience :: System Administrators',
                'Operating System :: OS Independent',
                'Topic :: Software Development'
            ],
            'description': [None]
        })
        files = MultiValueDict()

        user = User.objects.create_user('john', 'john@example.org', 'secret')
        response = views.handle_register_or_upload(post, files, user)
        self.assertEqual(response.status_code, 200, response.content)

        package = models.Package.objects.get(name='localshop')
        self.assertEqual(package.releases.count(), 1)

    def test_upload_new(self):
        post = MultiValueDict({
            'name': ['localshop'],
            'license': ['BSD'],
            'author': ['Michael van Tellingen'],
            'home_page': ['http://github.com/mvantellingen/localshop'],
            ':action': ['submit'],
            'download_url': [None],
            'summary': [
                'A private pypi server including auto-mirroring of pypi.'],
            'author_email': ['michaelvantellingen@gmail.com'],
            'metadata_version': ['1.0'],
            'version': ['0.1'],
            'platform': [None],
            'classifiers': [
                'Development Status :: 2 - Pre-Alpha',
                'Framework :: Django',
                'Intended Audience :: Developers',
                'Intended Audience :: System Administrators',
                'Operating System :: OS Independent',
                'Topic :: Software Development'
            ],
            'description': [None],

            # Extra fields for upload
            'pyversion': [''],
            'filetype': ['sdist'],
            'md5_digest': ['dc8f0311bb830ee96b8627f8335f2cb1'],
        })
        files = MultiValueDict({
            'distribution': [
                SimpleUploadedFile(
                    'localshop-0.1.tar.gz', 'binary-test-data-here')
            ]
        })

        user = User.objects.create_user('john', 'john@example.org', 'secret')
        response = views.handle_register_or_upload(post, files, user)
        self.assertEqual(response.status_code, 200, response.content)

        package = models.Package.objects.get(name='localshop')
        self.assertEqual(package.releases.count(), 1)
        self.assertTrue(package.is_local)

        release = package.releases.all()[0]
        self.assertEqual(release.files.count(), 1)

        release_file = release.files.all()[0]
        self.assertEqual(release_file.python_version, 'source')
        self.assertEqual(release_file.filetype, 'sdist')
        self.assertEqual(release_file.md5_digest,
            'dc8f0311bb830ee96b8627f8335f2cb1')
        self.assertEqual(release_file.filename, 'localshop-0.1.tar.gz')
        self.assertEqual(release_file.distribution.read(),
            'binary-test-data-here')

########NEW FILE########
__FILENAME__ = test_xmlrpc
from django.test import TestCase

from localshop.apps.packages import xmlrpc


class TestXMLRPC(TestCase):
    def test_search(self):
        rv = xmlrpc.search({'name': 'foo', 'summary': 'bar'}, 'or')
        self.assertEqual([], rv)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from localshop.apps.packages import views


urlpatterns = patterns('',
    url(r'^$', views.Index.as_view(), name='index'),

    url(r'^(?P<name>[-\._\w]+)/$', views.Detail.as_view(), name='detail'),

    url(r'^(?P<name>[-\._\w]+)/refresh',
        views.refresh, name='refresh'),
    url(r'^(?P<name>[-\._\w]+)/download/(?P<pk>\d+)/(?P<filename>.*)$',
        views.download_file, name='download'),
)

########NEW FILE########
__FILENAME__ = urls_simple
from django.conf.urls import patterns, url

urlpatterns = patterns('localshop.apps.packages.views',
    url(r'^$', 'simple_index', name='simple_index'),
    url(r'^(?P<slug>[-\._\w]+)/?(?P<version>.*?)/?$', 'simple_detail',
        name='simple_detail')
)

########NEW FILE########
__FILENAME__ = utils
import inspect
import hashlib
import logging
import os

from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import FieldDoesNotExist
from django.db.models.fields.files import FileField
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

logger = logging.getLogger(__name__)


def parse_distutils_request(request):
    """Parse the `request.raw_post_data` and update the request POST and FILES
    attributes .

    """

    try:
        sep = request.raw_post_data.splitlines()[1]
    except:
        raise ValueError('Invalid post data')

    request.POST = QueryDict('', mutable=True)
    try:
        request._files = MultiValueDict()
    except Exception:
        pass

    for part in filter(lambda e: e.strip(), request.raw_post_data.split(sep)):
        try:
            header, content = part.lstrip().split('\n', 1)
        except Exception:
            continue

        if content.startswith('\n'):
            content = content[1:]

        if content.endswith('\n'):
            content = content[:-1]

        headers = parse_header(header)

        if "name" not in headers:
            continue

        if "filename" in headers and headers['name'] == 'content':
            dist = TemporaryUploadedFile(name=headers["filename"],
                                         size=len(content),
                                         content_type="application/gzip",
                                         charset='utf-8')
            dist.write(content)
            dist.seek(0)
            request.FILES.appendlist('distribution', dist)
        else:
            # Distutils sends UNKNOWN for empty fields (e.g platform)
            # [russell.sim@gmail.com]
            if content == 'UNKNOWN':
                content = None
            request.POST.appendlist(headers["name"], content)


def parse_header(header):
    headers = {}
    for kvpair in filter(lambda p: p,
                         map(lambda p: p.strip(),
                             header.split(';'))):
        try:
            key, value = kvpair.split("=", 1)
        except ValueError:
            continue
        headers[key.strip()] = value.strip('"')

    return headers


def delete_files(sender, **kwargs):
    """Signal callback for deleting old files when database item is deleted"""
    for fieldname in sender._meta.get_all_field_names():
        try:
            field = sender._meta.get_field(fieldname)
        except FieldDoesNotExist:
            continue

        if isinstance(field, FileField):
            instance = kwargs['instance']
            fieldfile = getattr(instance, fieldname)

            if not hasattr(fieldfile, 'path'):
                return

            if not os.path.exists(fieldfile.path):
                return

            # Check if there are other instances which reference this fle
            is_referenced = (
                instance.__class__._default_manager
                .filter(**{'%s__exact' % fieldname: fieldfile})
                .exclude(pk=instance._get_pk_val())
                .exists())
            if is_referenced:
                return

            try:
                field.storage.delete(fieldfile.path)
            except Exception:
                logger.exception(
                    'Error when trying to delete file %s of package %s:' % (
                        instance.pk, fieldfile.path))


def md5_hash_file(fh):
    """Return the md5 hash of the given file-object"""
    md5 = hashlib.md5()
    while True:
        data = fh.read(8192)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()

########NEW FILE########
__FILENAME__ = views
import logging
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from localshop.apps.packages import forms
from localshop.apps.packages import models
from localshop.apps.packages.pypi import get_package_data
from localshop.apps.packages.pypi import get_search_names
from localshop.apps.packages.signals import release_file_notfound
from localshop.apps.packages.utils import parse_distutils_request
from localshop.apps.permissions.utils import credentials_required
from localshop.apps.permissions.utils import split_auth, authenticate_user
from localshop.http import HttpResponseUnauthorized
from localshop.views import LoginRequiredMixin, PermissionRequiredMixin

logger = logging.getLogger(__name__)


class SimpleIndex(ListView):
    """Index view with all available packages used by /simple url

    This page is used by pip/easy_install to find packages.

    """
    queryset = models.Package.objects.values('name')
    context_object_name = 'packages'
    http_method_names = ['get', 'post']
    template_name = 'packages/simple_package_list.html'

    @method_decorator(csrf_exempt)
    @method_decorator(credentials_required)
    def dispatch(self, request, *args, **kwargs):
        return super(SimpleIndex, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        parse_distutils_request(request)

        # XXX: Auth is currently a bit of a hack
        method, identity = split_auth(request)
        if not method:
            return HttpResponseUnauthorized(content='Missing auth header')

        user = authenticate_user(request)
        if not user:
            return HttpResponse('Invalid username/password', status=401)

        actions = {
            'submit': handle_register_or_upload,
            'file_upload': handle_register_or_upload,
        }

        handler = actions.get(request.POST.get(':action'))
        if not handler:
            raise Http404('Unknown action')
        return handler(request.POST, request.FILES, user)

simple_index = SimpleIndex.as_view()


class SimpleDetail(DetailView):
    """List all available files for a specific package.

    This page is used by pip/easy_install to find the files.

    """
    model = models.Package
    context_object_name = 'package'
    template_name = 'packages/simple_package_detail.html'

    @method_decorator(credentials_required)
    def dispatch(self, request, *args, **kwargs):
        return super(SimpleDetail, self).dispatch(request, *args, **kwargs)

    def get(self, request, slug, version=None):
        condition = Q()
        for name in get_search_names(slug):
            condition |= Q(name__iexact=name)

        try:
            package = models.Package.objects.get(condition)
        except ObjectDoesNotExist:
            package = get_package_data(slug)

        if package is None:
            raise Http404

        # Redirect if slug is not an exact match
        if slug != package.name:
            url = reverse('packages-simple:simple_detail', kwargs={
                'slug': package.name, 'version': version
            })
            return redirect(url)

        releases = package.releases
        if version and not package.is_local:
            releases = releases.filter(version=version)

            # Perhaps this version is new, refresh data
            if releases.count() == 0:
                get_package_data(slug, package)

        self.object = package
        context = self.get_context_data(
            object=self.object,
            releases=list(releases.all()))
        return self.render_to_response(context)

simple_detail = SimpleDetail.as_view()


class Index(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Package
    context_object_name = 'packages'
    permission_required = 'packages.view_package'


class Detail(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Package
    context_object_name = 'package'
    slug_url_kwarg = 'name'
    slug_field = 'name'
    permission_required = 'packages.view_package'

    def get_object(self, queryset=None):
        # Could be dropped when we use django 1.4
        self.kwargs['slug'] = self.kwargs.get(self.slug_url_kwarg, None)
        return super(Detail, self).get_object(queryset)

    def get_context_data(self, *args, **kwargs):
        context = super(Detail, self).get_context_data(*args, **kwargs)
        context['release'] = self.object.last_release
        context['pypi_url'] = settings.LOCALSHOP_PYPI_URL
        return context


@permission_required('packages.change_package')
@login_required
def refresh(request, name):
    try:
        package = models.Package.objects.get(name__iexact=name)
    except ObjectDoesNotExist:
        package = None
    package = get_package_data(name, package)
    return redirect(package)


@credentials_required
def download_file(request, name, pk, filename):
    """
    If the requested file is not already cached locally from a previous
    download it will be fetched from PyPi for local storage and the client will
    be redirected to PyPi, unless the LOCALSHOP_ISOLATED variable is set to
    True, in wich case the file will be served to the client after it is
    downloaded.
    """

    release_file = models.ReleaseFile.objects.get(pk=pk)
    if not release_file.distribution:
        logger.info("Queueing %s for mirroring", release_file.url)
        release_file_notfound.send(sender=release_file.__class__,
                                   release_file=release_file)
        if not settings.LOCALSHOP_ISOLATED:
            logger.debug("Redirecting user to pypi")
            return redirect(release_file.url)
        else:
            release_file = models.ReleaseFile.objects.get(pk=pk)

    # TODO: Use sendfile if enabled
    response = HttpResponse(
        FileWrapper(release_file.distribution.file),
        content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=%s' % (
        release_file.filename)
    size = release_file.distribution.file.size
    if size:
        response["Content-Length"] = size
    return response


def handle_register_or_upload(post_data, files, user):
    """Process a `register` or `upload` comment issued via distutils.

    This method is called with the authenticated user.

    """
    name = post_data.get('name')
    version = post_data.get('version')
    if not name or not version:
        logger.info("Missing name or version for package")
        return HttpResponseBadRequest('No name or version given')

    try:
        package = models.Package.objects.get(name=name)

        # Error out when we try to override a mirror'ed package for now
        # not sure what the best thing is
        if not package.is_local:
            return HttpResponseBadRequest(
                '%s is a pypi package!' % package.name)

        # Ensure that the user is one of the owners
        if not package.owners.filter(pk=user.pk).exists():
            if not user.is_superuser:
                return HttpResponseForbidden('No permission for this package')

            # User is a superuser, add him to the owners
            package.owners.add(user)

        try:
            release = package.releases.get(version=version)
        except ObjectDoesNotExist:
            release = None
    except ObjectDoesNotExist:
        package = None
        release = None

    # Validate the data
    form = forms.ReleaseForm(post_data, instance=release)
    if not form.is_valid():
        return HttpResponseBadRequest('ERRORS %s' % form.errors)

    if not package:
        package = models.Package.objects.create(name=name, is_local=True)
        package.owners.add(user)
        package.save()

    release = form.save(commit=False)
    release.package = package
    release.user = user
    release.save()

    # If this is an upload action then process the uploaded file
    if files:
        filename = files['distribution']._name
        try:
            release_file = release.files.get(filename=filename)
        except ObjectDoesNotExist:
            release_file = models.ReleaseFile(
                release=release, filename=filename, user=user)

        form_file = forms.ReleaseFileForm(
            post_data, files, instance=release_file)
        if not form_file.is_valid():
            return HttpResponseBadRequest('ERRORS %s' % form_file.errors)
        release_file = form_file.save(commit=False)
        release_file.user = user
        release_file.save()

    return HttpResponse()

########NEW FILE########
__FILENAME__ = xmlrpc
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher

from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from localshop.apps.packages import models
from localshop.apps.permissions.utils import credentials_required

dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)


@csrf_exempt
@credentials_required
def handle_request(request):
    response = HttpResponse(mimetype='application/xml')
    response.write(dispatcher._marshaled_dispatch(request.raw_post_data))
    return response


def search(query, operator):
    """Implement xmlrpc search command.

    This only searches through the mirrored and private packages

    """
    field_map = {
        'name': 'name__icontains',
        'summary': 'releases__summary__icontains',
    }

    query_filter = None
    for field, values in query.iteritems():
        for value in values:
            if field not in field_map:
                continue

            field_filter = Q(**{field_map[field]: value})
            if not query_filter:
                query_filter = field_filter
                continue

            if operator == 'and':
                query_filter &= field_filter
            else:
                query_filter |= field_filter

    result = []
    packages = models.Package.objects.filter(query_filter).all()[:20]
    for package in packages:
        release = package.releases.all()[0]
        result.append({
            'name': package.name,
            'summary': release.summary,
            'version': release.version,
            '_pypi_ordering': 0,
        })
    return result

dispatcher.register_function(search, 'search')

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from localshop.apps.permissions import models


class CidrAdmin(admin.ModelAdmin):
    list_display = ['cidr', 'label']


class CredentialAdmin(admin.ModelAdmin):
    list_display = ['creator', 'access_key', 'created', 'comment']

admin.site.register(models.CIDR, CidrAdmin)
admin.site.register(models.Credential, CredentialAdmin)

########NEW FILE########
__FILENAME__ = backend
from django.contrib.auth.backends import ModelBackend

from .models import Credential


class CredentialBackend(ModelBackend):
    def authenticate(self, access_key=None, secret_key=None):
        try:
            credential = Credential.objects.active().get(access_key=access_key,
                                                         secret_key=secret_key)
        except (Credential.DoesNotExist,
                Credential.MultipleObjectsReturned):
            pass
        else:
            if credential.creator.is_active:
                return credential.creator
        return None

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'CIDR'
        db.create_table('permissions_cidr', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cidr', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('permissions', ['CIDR'])


    def backwards(self, orm):
        
        # Deleting model 'CIDR'
        db.delete_table('permissions_cidr')


    models = {
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['permissions']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_cidr_label__add_unique_cidr_cidr
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CIDR.label'
        db.add_column('permissions_cidr', 'label',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding unique constraint on 'CIDR', fields ['cidr']
        db.create_unique('permissions_cidr', ['cidr'])


    def backwards(self, orm):
        # Removing unique constraint on 'CIDR', fields ['cidr']
        db.delete_unique('permissions_cidr', ['cidr'])

        # Deleting field 'CIDR.label'
        db.delete_column('permissions_cidr', 'label')


    models = {
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = 0003_auto__add_credential
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Credential'
        db.create_table('permissions_credential', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('access_key', self.gf('uuidfield.fields.UUIDField')(max_length=32)),
            ('secret_key', self.gf('uuidfield.fields.UUIDField')(max_length=32)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('deactivated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('permissions', ['Credential'])


    def backwards(self, orm):
        # Deleting model 'Credential'
        db.delete_table('permissions_credential')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'permissions.credential': {
            'Meta': {'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'max_length': '32'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = 0004_auto__add_unique_credential_access_key__add_unique_credential_secret_k
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Credential', fields ['access_key']
        db.create_index('permissions_credential', ['access_key'])

        # Adding unique constraint on 'Credential', fields ['access_key']
        db.create_unique('permissions_credential', ['access_key'])

        # Adding index on 'Credential', fields ['secret_key']
        db.create_index('permissions_credential', ['secret_key'])

        # Adding unique constraint on 'Credential', fields ['secret_key']
        db.create_unique('permissions_credential', ['secret_key'])


    def backwards(self, orm):
        # Removing unique constraint on 'Credential', fields ['secret_key']
        db.delete_unique('permissions_credential', ['secret_key'])

        # Removing index on 'Credential', fields ['secret_key']
        db.delete_index('permissions_credential', ['secret_key'])

        # Removing unique constraint on 'Credential', fields ['access_key']
        db.delete_unique('permissions_credential', ['access_key'])

        # Removing index on 'Credential', fields ['access_key']
        db.delete_index('permissions_credential', ['access_key'])


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'permissions.credential': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = 0005_auto__add_authprofile
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AuthProfile'
        db.create_table('permissions_authprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mugshot', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='registered', max_length=15)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='auth_profile', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('permissions', ['AuthProfile'])


    def backwards(self, orm):
        # Deleting model 'AuthProfile'
        db.delete_table('permissions_authprofile')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.authprofile': {
            'Meta': {'object_name': 'AuthProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'auth_profile'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'permissions.credential': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = 0006_userena
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for user in orm['auth.User'].objects.all():
            try:
                user.auth_profile
            except orm.AuthProfile.DoesNotExist:
                orm.AuthProfile.objects.create(user=user, privacy='closed')

    def backwards(self, orm):
        "Write your backwards methods here."

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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.authprofile': {
            'Meta': {'object_name': 'AuthProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'auth_profile'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'permissions.credential': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_cidr_require_credentials
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CIDR.require_credentials'
        db.add_column('permissions_cidr', 'require_credentials',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CIDR.require_credentials'
        db.delete_column('permissions_cidr', 'require_credentials')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.authprofile': {
            'Meta': {'object_name': 'AuthProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'auth_profile'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'require_credentials': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'permissions.credential': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_credential_comment
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Credential.comment'
        db.add_column('permissions_credential', 'comment',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Credential.comment'
        db.delete_column('permissions_credential', 'comment')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'permissions.authprofile': {
            'Meta': {'object_name': 'AuthProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'auth_profile'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'permissions.cidr': {
            'Meta': {'object_name': 'CIDR'},
            'cidr': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'require_credentials': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'permissions.credential': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Credential'},
            'access_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'}),
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deactivated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret_key': ('uuidfield.fields.UUIDField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        }
    }

    complete_apps = ['permissions']
########NEW FILE########
__FILENAME__ = models
import netaddr

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from userena.models import UserenaBaseProfile
from uuidfield import UUIDField

from localshop.utils import now


class AuthProfile(UserenaBaseProfile):
    user = models.OneToOneField(
        User, unique=True, verbose_name=_('user'), related_name='auth_profile')


class CIDRManager(models.Manager):
    def has_access(self, ip_addr, with_credentials=True):
        cidrs = self.filter(
            require_credentials=with_credentials
        ).values_list('cidr', flat=True)
        return bool(netaddr.all_matching_cidrs(ip_addr, cidrs))


class CIDR(models.Model):
    cidr = models.CharField('CIDR', max_length=128, unique=True,
        help_text='IP addresses and/or subnet')
    label = models.CharField('label', max_length=128, blank=True, null=True,
        help_text='Human-readable name (optional)')
    require_credentials = models.BooleanField(default=True)

    objects = CIDRManager()

    def __unicode__(self):
        return self.cidr

    class Meta:
        permissions = (
            ("view_cidr", "Can view CIDR"),
        )


class CredentialManager(models.Manager):

    def active(self):
        return self.filter(deactivated__isnull=True)


class Credential(models.Model):
    access_key = UUIDField(verbose_name='Access key', help_text='The access key', auto=True, db_index=True)
    secret_key = UUIDField(verbose_name='Secret key', help_text='The secret key', auto=True, db_index=True)
    creator = models.ForeignKey(User)
    created = models.DateTimeField(default=now)
    deactivated = models.DateTimeField(blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True, default='',
        help_text="A comment about this credential, e.g. where it's being used")

    objects = CredentialManager()

    def __unicode__(self):
        return self.access_key.hex

    class Meta:
        ordering = ['-created']
        permissions = (
            ("view_credential", "Can view credential"),
        )

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase

from localshop.apps.permissions import models


class CidrTest(TestCase):
    def test_has_access(self):
        self.assertFalse(models.CIDR.objects.has_access('192.168.1.1'))

    def test_simple(self):
        models.CIDR.objects.create(cidr='192.168.1.1')
        self.assertTrue(models.CIDR.objects.has_access('192.168.1.1'))

    def test_cidr(self):
        models.CIDR.objects.create(cidr='192.168.1.0/24')
        self.assertTrue(models.CIDR.objects.has_access('192.168.1.1'))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from localshop.apps.permissions import views


urlpatterns = patterns('',
    url(r'^cidr/$', views.CidrListView.as_view(), name='cidr_index'),
    url(r'^cidr/create$', views.CidrCreateView.as_view(), name='cidr_create'),
    url(r'^cidr/(?P<pk>\d+)/edit', views.CidrUpdateView.as_view(),
        name='cidr_edit'),
    url(r'^cidr/(?P<pk>\d+)/delete', views.CidrDeleteView.as_view(),
        name='cidr_delete'),
    url(r'^credentials/$', views.CredentialListView.as_view(),
        name='credential_index'),
    url(r'^credentials/create$', views.create_credential,
        name='credential_create'),
    url(r'^credentials/(?P<access_key>[a-f0-9]+)/activate', views.activate_credential,
        name='credential_activate'),
    url(r'^credentials/(?P<access_key>[a-f0-9]+)/deactivate', views.deactivate_credential,
        name='credential_deactivate'),
    url(r'^credentials/(?P<access_key>[a-f0-9]+)/secret', views.secret_key,
        name='credential_secret'),
    url(r'^credentials/(?P<access_key>[a-f0-9]+)/edit', views.CredentialUpdateView.as_view(),
        name='credential_edit'),
    url(r'^credentials/(?P<access_key>[a-f0-9]+)/delete', views.CredentialDeleteView.as_view(),
        name='credential_delete'),
)

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

from django.contrib.auth import login, authenticate
from django.utils.decorators import available_attrs
from django.http import HttpResponseForbidden

from localshop.apps.permissions.models import CIDR
from localshop.http import HttpResponseUnauthorized


def decode_credentials(auth):
    auth = auth.strip().decode('base64')
    return auth.split(':', 1)


def split_auth(request):
    auth = request.META.get('HTTP_AUTHORIZATION')
    if auth:
        method, identity = auth.split(' ', 1)
    else:
        method, identity = None, None
    return method, identity


def authenticate_user(request):
    method, identity = split_auth(request)
    if method is not None and method.lower() == 'basic':
        key, secret = decode_credentials(identity)
        user = authenticate(access_key=key, secret_key=secret)
        if not user:
            user = authenticate(username=key, password=secret)
        return user


def credentials_required(view_func):
    """
    This decorator should be used with views that need simple authentication
    against Django's authentication framework.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def decorator(request, *args, **kwargs):
        ip_addr = request.META['REMOTE_ADDR']

        if CIDR.objects.has_access(ip_addr, with_credentials=False):
            return view_func(request, *args, **kwargs)

        if not CIDR.objects.has_access(ip_addr, with_credentials=True):
            return HttpResponseForbidden('No permission')

        # Just return the original view because already logged in
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)

        user = authenticate_user(request)
        if user is not None:
            login(request, user)
            return view_func(request, *args, **kwargs)

        return HttpResponseUnauthorized(content='Authorization Required')
    return decorator

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.sites.models import Site
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.forms import ModelForm
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, CreateView
from django.views.generic import UpdateView, DeleteView

from localshop.views import LoginRequiredMixin, PermissionRequiredMixin
from localshop.utils import now
from localshop.apps.permissions import models


class CidrListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.CIDR
    object_context_name = 'cidrs'
    permission_required = 'permissions.view_cidr'


class CidrCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.CIDR
    permission_required = 'permissions.add_cidr'

    def get_success_url(self):
        return reverse('permissions:cidr_index')


class CidrUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = models.CIDR
    permission_required = 'permissions.change_cidr'

    def get_success_url(self):
        return reverse('permissions:cidr_index')


class CidrDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.CIDR
    permission_required = 'permissions.delete_cidr'

    def get_success_url(self):
        return reverse('permissions:cidr_index')


class CredentialListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    object_context_name = 'credentials'
    permission_required = 'permissions.view_credential'

    def get_queryset(self):
        return models.Credential.objects.filter(creator=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(CredentialListView, self).get_context_data(**kwargs)
        context['current_url'] = Site.objects.get_current()
        return context


class CredentialUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):

    class CredentialModelForm(ModelForm):
        class Meta:
            model = models.Credential
            fields = ('comment',)

    model = models.Credential
    form_class = CredentialModelForm
    slug_field = 'access_key'
    slug_url_kwarg = 'access_key'
    permission_required = 'permissions.change_credential'

    def get_object(self, queryset=None):
        obj = super(CredentialUpdateView, self).get_object(queryset)
        if not obj.creator == self.request.user:
            raise Http404
        return obj

    def get_success_url(self):
        return reverse('permissions:credential_index')


class CredentialDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Credential
    slug_field = 'access_key'
    slug_url_kwarg = 'access_key'
    permission_required = 'permissions.delete_credential'

    def get_object(self, queryset=None):
        obj = super(CredentialDeleteView, self).get_object(queryset)
        if not obj.creator == self.request.user:
            raise Http404
        return obj

    def get_success_url(self):
        return reverse('permissions:credential_index')


@permission_required('permissions.add_credential')
@login_required
def create_credential(request):
    models.Credential.objects.create(creator=request.user)
    return redirect('permissions:credential_index')


@permission_required('permissions.add_credential')
@login_required
def secret_key(request, access_key):
    if not request.is_ajax():
        raise SuspiciousOperation
    credential = get_object_or_404(models.Credential,
                                   creator=request.user,
                                   access_key=access_key)
    return HttpResponse(credential.secret_key)


@permission_required('permissions.change_credential')
@login_required
def activate_credential(request, access_key):
    credential = get_object_or_404(models.Credential,
                                   creator=request.user,
                                   access_key=access_key)
    credential.deactivated = None
    credential.save()
    return redirect('permissions:credential_index')


@permission_required('permissions.change_credential')
@login_required
def deactivate_credential(request, access_key):
    credential = get_object_or_404(models.Credential,
                                   creator=request.user,
                                   access_key=access_key)
    credential.deactivated = now()
    credential.save()
    return redirect('permissions:credential_index')

########NEW FILE########
__FILENAME__ = http
from django.conf import settings
from django.http import HttpResponse

BASIC_AUTH_REALM = getattr(settings, 'BASIC_AUTH_REALM', 'pypi')


class HttpResponseUnauthorized(HttpResponse):
    status_code = 401

    def __init__(self, basic_auth_realm=None, *args, **kwargs):
        super(HttpResponseUnauthorized, self).__init__(*args, **kwargs)
        if basic_auth_realm is None:
            basic_auth_realm = BASIC_AUTH_REALM
        self['WWW-Authenticate'] = 'Basic realm="%s"' % basic_auth_realm

########NEW FILE########
__FILENAME__ = init
import os
import uuid

from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            "--no-superuser",
            default=False,
            action="store_true",
            dest="nosuperuser",
            help="Doesn't create a superuser and therefore requires no interaction. Useful for deploying using automated tools. You'll need to provide some initial fixtures to actually get access",
        ),
    )

    def handle(self, *args, **kwargs):

        self.nosuperuser = kwargs.get("nosuperuser")

        try:
            default_path = os.environ['LOCALSHOP_HOME']
        except KeyError:
            default_path = os.path.expanduser('~/.localshop')

        if not os.path.exists(default_path):
            os.mkdir(default_path)

        config_path = os.path.join(default_path, 'localshop.conf.py')
        if not os.path.exists(config_path):
            default_params = {
                'SECRET_KEY': uuid.uuid4()
            }

            with open(config_path, 'w') as fh:
                fh.write("""
SECRET_KEY = '%(SECRET_KEY)s'

                """ % default_params)

        call_command('syncdb', database='default', interactive=False)
        call_command('migrate', database='default', interactive=False)
        if not self.nosuperuser:
            call_command('createsuperuser', database='default', interactive=True)

########NEW FILE########
__FILENAME__ = upgrade
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        call_command('syncdb', database='default', interactive=False)

        if 'south' in settings.INSTALLED_APPS:
            call_command('migrate', database='default', interactive=False,
                delete_ghosts=True)

########NEW FILE########
__FILENAME__ = runner
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localshop.settings')
    os.environ.setdefault('DJANGO_CONFIGURATION', 'Localshop')

    from configurations.management import execute_from_command_line

    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = settings
import os
import imp
from celery.schedules import crontab

import djcelery
djcelery.setup_loader()

from configurations import Settings
from configurations.utils import uppercase_attributes

try:
    DEFAULT_PATH = os.environ['LOCALSHOP_HOME']
except KeyError:
    DEFAULT_PATH = os.path.expanduser('~/.localshop')


def FileSettings(path):
    path = os.path.expanduser(path)
    mod = imp.new_module('localshop.local')
    mod.__file__ = path

    class Holder(object):
        pass

    try:
        with open(path, 'r') as fh:
            exec(fh.read(), mod.__dict__)
    except IOError as e:
        print("Notice: Unable to load configuration file %s (%s), "
              "using default settings\n\n" % (path, e.strerror))
        return Holder

    for name, value in uppercase_attributes(mod).items():
        setattr(Holder, name, value)

    return Holder


class Base(Settings):
    # Django settings for localshop project.
    PROJECT_ROOT = os.path.join(os.path.dirname(__file__), os.pardir)

    DEBUG = False
    TEMPLATE_DEBUG = DEBUG

    ADMINS = (
        # ('Your Name', 'your_email@example.com'),
    )

    MANAGERS = ADMINS

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(DEFAULT_PATH, 'localshop.db'),
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }

    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # On Unix systems, a value of None will cause Django to use the same
    # timezone as the operating system.
    # If running in a Windows environment this must be set to the same as your
    # system time zone.
    TIME_ZONE = 'Europe/Amsterdam'

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
    # MEDIA_ROOT = 'files'

    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    # STATIC_ROOT = 'assets'

    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"
    STATIC_URL = '/assets/'

    # Additional locations of static files
    STATICFILES_DIRS = [
        os.path.join(PROJECT_ROOT, 'static')
    ]

    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    )

    # Make this unique, and don't share it with anybody.
    SECRET_KEY = 'CHANGE-ME'

    # List of callables that know how to import templates from various sources.
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        #'django.template.loaders.eggs.Loader',
    )

    TEMPLATE_CONTEXT_PROCESSORS = [
        'django.contrib.auth.context_processors.auth',
        'django.core.context_processors.debug',
        'django.core.context_processors.i18n',
        'django.core.context_processors.media',
        'django.core.context_processors.static',
        'django.contrib.messages.context_processors.messages',

        'localshop.apps.packages.context_processors.sidebar',
    ]

    MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    )

    ROOT_URLCONF = 'localshop.urls'

    # Python dotted path to the WSGI application used by Django's runserver.
    WSGI_APPLICATION = 'localshop.wsgi.application'

    TEMPLATE_DIRS = (
        os.path.join(PROJECT_ROOT, 'localshop', 'templates'),
    )

    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--logging-clear-handlers', '--cover-package=localshop']

    BROKER_URL = "django://"

    CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
    CELERYD_FORCE_EXECV = False
    CELERYBEAT_SCHEDULE = {
        # Executes every day at 1:00 AM
        'every-day-1am': {
            'task': 'localshop.apps.packages.tasks.update_packages',
            'schedule': crontab(hour=1, minute=0),
        },
    }

    INSTALLED_APPS = [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.admin',

        'kombu.transport.django',
        'djcelery',
        'south',
        'gunicorn',
        'userena',
        'guardian',

        'localshop',
        'localshop.apps.packages',
        'localshop.apps.permissions',
    ]

    import pkg_resources
    try:
        pkg_resources.get_distribution('django_nose')
        INSTALLED_APPS.append('django_nose')
    except pkg_resources.DistributionNotFound:
        pass

    # Auth settings
    AUTHENTICATION_BACKENDS = (
        'userena.backends.UserenaAuthenticationBackend',
        'guardian.backends.ObjectPermissionBackend',
        'localshop.apps.permissions.backend.CredentialBackend',
        'django.contrib.auth.backends.ModelBackend',
    )

    AUTH_PROFILE_MODULE = 'permissions.AuthProfile'
    LOGIN_URL = '/accounts/signin/'
    LOGIN_REDIRECT_URL = '/accounts/%(username)s/'
    LOGOUT_URL = '/accounts/signout'
    USERENA_MUGSHOT_GRAVATAR = True
    USERENA_MUGSHOT_SIZE = 20
    ANONYMOUS_USER_ID = -1

    # A sample logging configuration. The only tangible logging
    # performed by this configuration is to send an email to
    # the site admins on every HTTP 500 error when DEBUG=False.
    # See http://docs.djangoproject.com/en/dev/topics/logging for
    # more details on how to customize your logging configuration.
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'root': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler'
            },
        },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
        },
    }

    ALLOWED_HOSTS = ['*']

    LOCALSHOP_DELETE_FILES = False

    LOCALSHOP_DISTRIBUTION_STORAGE = 'storages.backends.overwrite.OverwriteStorage'

    LOCALSHOP_PYPI_URL = 'https://pypi.python.org/pypi'

    LOCALSHOP_HTTP_PROXY = None

    LOCALSHOP_ISOLATED = False


class TestConfig(Base):
    SECRET_KEY = "TEST-KEY"


class Localshop(FileSettings(os.path.join(DEFAULT_PATH, 'localshop.conf.py')), Base):
    pass

########NEW FILE########
__FILENAME__ = forms
from django import template

register = template.Library()


@register.filter
def form_widget(field):
    return field.field.widget.__class__.__name__

########NEW FILE########
__FILENAME__ = urls
import re
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from localshop.apps.packages.xmlrpc import handle_request

admin.autodiscover()

static_prefix = re.escape(settings.STATIC_URL.lstrip('/'))


urlpatterns = patterns('',
    url(r'^$', 'localshop.views.index', name='index'),

    # Default path for xmlrpc calls
    url(r'^RPC2$', handle_request),

    url(r'^packages/',
        include('localshop.apps.packages.urls', namespace='packages')),

    url(r'^simple/', include('localshop.apps.packages.urls_simple',
        namespace='packages-simple')),

    # We add a separate route for simple without the trailing slash so that
    # POST requests to /simple/ and /simple both work
    url(r'^simple$', 'localshop.apps.packages.views.simple_index'),

    url(r'^permissions/',
        include('localshop.apps.permissions.urls', namespace='permissions')),

    url(r'^accounts/signup/', RedirectView.as_view(url="/")),

    url(r'^accounts/', include('userena.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^%s(?P<path>.*)$' % static_prefix,
        'django.contrib.staticfiles.views.serve', {'insecure': True}),
)

########NEW FILE########
__FILENAME__ = utils
import os
import shutil
import tempfile

from django.conf import settings
from django.test.utils import override_settings

try:
    from django.utils.timezone import now
except ImportError:
    from datetime import datetime
    now = datetime.now


class TemporaryMediaRootMixin(object):

    def setUp(self):
        super(TemporaryMediaRootMixin, self).setUp()

        # Create path to temp dir and recreate it
        temp_media_root = os.path.join(
            tempfile.gettempdir(), 'project-testrun')
        if os.path.exists(temp_media_root):
            shutil.rmtree(temp_media_root)
        os.mkdir(temp_media_root)

        self.override = override_settings(
            MEDIA_ROOT=temp_media_root,
        )
        self.override.enable()

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT)
        self.override.disable()

        super(TemporaryMediaRootMixin, self).tearDown()

########NEW FILE########
__FILENAME__ = views

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from localshop.apps.packages.models import Release, ReleaseFile
from localshop.apps.packages import xmlrpc


@csrf_exempt
def index(request):
    if request.method == 'POST':
        return xmlrpc.handle_request(request)
    return frontpage(request)


@login_required
def frontpage(request):
    recent_local = (Release.objects
        .filter(package__is_local=True)
        .order_by('-created')
        .all()[:5])

    recent_mirror = (ReleaseFile.objects
        .filter(release__package__is_local=False)
        .exclude(distribution='')
        .order_by('-modified')
        .all()[:10])

    return TemplateResponse(request, 'frontpage.html', {
        'recent_local': recent_local,
        'recent_mirror': recent_mirror,
    })


class LoginRequiredMixin(object):
    """
    View mixin that applies the login_required decorator
    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class PermissionRequiredMixin(object):
    """
    View mixin which uses the permission_required decorator.
    """
    permission_required = None  # the permission, e.g. 'auth.add_user'
    raise_exception = True  # raises a 403 exception by default
    login_url = settings.LOGIN_URL  # the url to redirect to

    def dispatch(self, request, *args, **kwargs):
        if (self.permission_required is None or
                '.' not in self.permission_required):
            raise ImproperlyConfigured("PermissionRequiredMixin must have a "
                                       "permission_required attribute.")
        decorator = permission_required(self.permission_required,
                                        self.login_url, self.raise_exception)
        decorated_dispatch = decorator(super(PermissionRequiredMixin, self).dispatch)
        return decorated_dispatch(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for localshop project.

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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localshop.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Localshop')

from configurations.wsgi import get_wsgi_application

application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from localshop.runner import main

if __name__ == "__main__":
    main()

########NEW FILE########
