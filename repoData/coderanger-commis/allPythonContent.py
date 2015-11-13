__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from commis.clients.models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('name', 'admin')

    def save(self, commit=True):
        ret = super(ClientForm, self).save(commit)
        if not self.instance.key:
            self.instance.generate_key()
        return ret

class ClientEditForm(ClientForm):
    rekey = forms.BooleanField(
        label=_('Regenerate private key'),
        required=False,
        help_text=_('Generate a new key for this client. This will invalidate the current key.')
    )

    def save(self, commit=True):
        if self.cleaned_data['rekey']:
            self.instance.generate_key()
        return super(ClientEditForm, self).save(commit)

########NEW FILE########
__FILENAME__ = models
import chef
from chef.rsa import Key
from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from commis import conf
from commis.db import update

class ClientManager(models.Manager):
    def create(self, *args, **kwargs):
        client = super(ClientManager, self).create(*args, **kwargs)
        client.generate_key()
        return client

    def from_dict(self, data, *args, **kwargs):
        chef_client = chef.Client.from_search(data)
        client, created = self.get_or_create(name=chef_client.name)
        client.generate_key()
        client.save()
        client.private_key = client._key_cache.private_export()
        return client

class Client(models.Model):
    name = models.CharField(_('Name'), unique=True, max_length=1024)
    key_pem = models.TextField(_('Public Key'))
    admin = models.BooleanField(_('Admin'))

    objects = ClientManager()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('commis_webui_clients_show', args=(self,))

    @property
    def key(self):
        if not self.key_pem:
            return None
        if not getattr(self, '_key_cache', None):
            self._key_cache = Key(self.key_pem)
        return self._key_cache

    @property
    def validator(self):
        return self.name == conf.COMMIS_VALIDATOR_NAME

    def generate_key(self):
        key = Key.generate(2048)
        update(self, key_pem=key.public_export())
        self._key_cache = key
        return key

    def to_dict(self):
        client = chef.Client(self.name, skip_load=True)
        client.admin = self.admin
        client.public_key = self.key_pem
        return client.to_dict()

    def to_search(self):
        return self.to_dict()

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import site

from commis.clients.models import Client
from commis.search.indexes import CommisSearchIndex

class ClientIndex(CommisSearchIndex):
    pass

site.register(Client, ClientIndex)

########NEW FILE########
__FILENAME__ = tests
import datetime

from django.test import TestCase
import chef
from chef.auth import sign_request
from chef.rsa import Key, SSLError

from commis.clients.models import Client
from commis.test import ChefTestCase, TestChefAPI

class ClientTestCase(TestCase):
    def test_create(self):
        c = Client.objects.create(name='test_1')
        self.assertTrue(c.key)
        self.assertTrue(c.key.public_export())
        self.assertTrue(c.key.private_export())

        c2 = Client.objects.get(name='test_1')
        self.assertTrue(c2.key)
        self.assertTrue(c2.key.public_export())
        self.assertRaises(SSLError, c2.key.private_export)


class APITestCase(ChefTestCase):
    def sign_request(self, path, **kwargs):
        d = dict(key=self.api.key, http_method='GET',
            path=self.api.parsed_url.path+path.split('?', 1)[0], body=None,
            host=self.api.parsed_url.netloc, timestamp=datetime.datetime.utcnow(),
            user_id=self.api.client)
        d.update(kwargs)
        auth_headers = sign_request(**d)
        headers = {}
        for key, value in auth_headers.iteritems():
            headers['HTTP_'+key.upper().replace('-', '_')] = value
        return headers

    def test_good(self):
        path = '/clients'
        headers = self.sign_request(path)
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 200)

    def test_bad_timestamp(self):
        path = '/clients'
        headers = self.sign_request(path, timestamp=datetime.datetime(2000, 1, 1))
        response = self.client.get('/api'+path, **headers)
        self.assertContains(response, 'clock', status_code=401)

    def test_no_timestamp(self):
        path = '/clients'
        headers = self.sign_request(path)
        del headers['HTTP_X_OPS_TIMESTAMP']
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 401)

    def test_no_sig(self):
        path = '/clients'
        headers = self.sign_request(path)
        for key in headers.keys():
            if key.startswith('HTTP_X_OPS_AUTHORIZATION'):
                del headers[key]
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 401)

    def test_no_sig2(self):
        path = '/clients'
        headers = self.sign_request(path, key=Key.generate(2048))
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 401)

    def test_bad_method(self):
        path = '/clients'
        headers = self.sign_request(path, http_method='POST')
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 401)

    def test_no_userid(self):
        path = '/clients'
        headers = self.sign_request(path)
        del headers['HTTP_X_OPS_USERID']
        response = self.client.get('/api'+path, **headers)
        self.assertEqual(response.status_code, 401)


class ClientAPITestCase(ChefTestCase):
    def test_list(self):
        clients = chef.Client.list()
        self.assertTrue('unittest' in clients)

    def test_list_fail(self):
        api = TestChefAPI(self.client, Key.generate(2048), self._client.name)
        self.assertRaises(chef.ChefError, chef.Client.list, api=api)

    def test_get(self):
        client = chef.Client('unittest')
        self.assertTrue(client.admin)
        self.assertEqual(client.public_key, self.api.key.public_export())

########NEW FILE########
__FILENAME__ = views
from django.template.response import TemplateResponse

from commis import conf
from commis.clients.forms import ClientForm, ClientEditForm
from commis.clients.models import Client
from commis.exceptions import ChefAPIError
from commis.generic_views import CommisAPIView, api, CommisView

class ClientAPIView(CommisAPIView):
    model = Client

    @api('POST')
    def create(self, request):
        if not (request.client.admin or request.client.name == conf.COMMIS_VALIDATOR_NAME):
            raise ChefAPIError(403, 'You are not allowed to take this action')
        return super(ClientAPIView, self).create(request)

    def create_data(self, request, obj):
        data = super(ClientAPIView, self).create_data(request, obj)
        # Initial creation (via ClientManager.from_dict, which should end up
        # being called by our parent classes) attaches a temporary .private_key
        # attribute which we can send back to the Chef client.
        data['private_key'] = obj.private_key
        return data


class ClientView(CommisView):
    model = Client
    form = ClientForm
    edit_form = ClientEditForm

    def change_redirect(self, request, action, obj):
        if not obj.key.public:
            # Rekey occured
            opts = self.model._meta
            return TemplateResponse(request, 'commis/%s/show.html'%self.get_app_label(), {
                'opts': opts,
                'obj': obj,
                'action': 'show',
                'block_nav': self.block_nav(request, obj),
            })
        return super(ClientView, self).change_redirect(request, action, obj)

########NEW FILE########
__FILENAME__ = conf
import os

from django.conf import settings

COMMIS_TIME_SKEW = getattr(settings, 'COMMIS_TIME_SKEW', 15*60)

COMMIS_VALIDATOR_NAME = getattr(settings, 'COMMIS_VALIDATOR_NAME', 'chef-validator')

COMMIS_FILE_ROOT = getattr(settings, 'COMMIS_FILE_ROOT', os.path.join(settings.MEDIA_ROOT, 'sandbox'))

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _, ungettext_lazy

from commis.exceptions import ChefAPIError
from commis.sandboxes.models import SandboxFile

class CookbookManager(models.Manager):
    def from_dict(self, data):
        cookbook, created = self.get_or_create(name=data['cookbook_name'], version=data['version'])
        if 'metadata' in data:
            cookbook.maintainer = data['metadata'].get('maintainer', '')
            cookbook.maintainer_email = data['metadata'].get('maintainer_email', '')
            cookbook.description = data['metadata'].get('description', '')
            cookbook.long_description = data['metadata'].get('long_description', '')
            cookbook.license = data['metadata'].get('license', '')
        dependencies = data.get('metadata', {}).get('dependencies', {})
        for dep in cookbook.dependencies.all():
            if dep.name not in dependencies:
                # Dependency removed
                dep.delete()
        # I don't know what the value here is exactly. It is likely the dependency version in some form
        for name, _unknown in dependencies.iteritems():
            cookbook.dependencies.get_or_create(name=name)
        recipes = data.get('metadata', {}).get('recipes', {})
        for recipe in cookbook.recipes.all():
            if recipe.name not in recipes:
                recipe.delete()
        for name, description in recipes.iteritems():
            try:
                recipe = cookbook.recipes.get(name=name)
                recipe.description = description
                recipe.save()
            except CookbookRecipe.DoesNotExist:
                cookbook.recipes.create(name=name, description=description)
        for type, label in CookbookFile.TYPES:
            for file_info in data.get(type, []):
                try:
                    cookbook_file = cookbook.files.get(type=type, file__checksum=file_info['checksum'])
                except CookbookFile.DoesNotExist:
                    try:
                        file = SandboxFile.objects.get(checksum=file_info['checksum'])
                    except SandboxFile.DoesNotExist:
                        raise ChefAPIError(500, 'Checksum %s does not match any uploaded file', file_info['checksum'])
                    if not file.uploaded:
                        raise ChefAPIError(500, 'Checksum %s does not match any uploaded file', file_info['checksum'])
                    cookbook_file = cookbook.files.create(type=type, file=file)
                cookbook_file.name = file_info['name']
                cookbook_file.path = file_info['path']
                cookbook_file.specificity = file_info['specificity']
                cookbook_file.save()
        cookbook.save()
        return cookbook


class Cookbook(models.Model):
    class Meta:
        verbose_name = _('cookbook')
        verbose_name_plural = _('cookbooks')
    name = models.CharField(max_length=1024)
    version = models.CharField(max_length=1024)
    maintainer = models.CharField(max_length=1024, blank=True)
    maintainer_email = models.CharField(max_length=1024, blank=True)
    description = models.CharField(max_length=1024, blank=True)
    long_description = models.TextField(blank=True)
    license = models.CharField(max_length=1024, blank=True)

    objects = CookbookManager()

    def __unicode__(self):
        return self.name

    def to_dict(self, request=None):
        data = {}
        data['name'] = self.name + '-' + self.version
        data['cookbook_name'] = self.name
        data['version'] = self.version
        data['json_class'] = 'Chef::CookbookVersion'
        data['chef_type'] = 'cookbook_version'
        metadata = data['metadata'] = {}
        metadata['name'] = self.name
        metadata['version'] = self.version
        metadata['maintainer'] = self.maintainer
        metadata['maintainer_email'] = self.maintainer_email
        metadata['description'] = self.description
        metadata['long_description'] = self.long_description
        metadata['license'] = self.license
        dependencies = metadata['dependencies'] = {}
        for dep in self.dependencies.all():
            dependencies[dep.name] = []
        recipes = metadata['recipes'] = {}
        for recipe in self.recipes.all():
            recipes[recipe.name] = recipe.description
        # Not storing this info for now, fill in later with real code
        metadata['attributes'] = {}
        metadata['suggestions'] = {}
        metadata['platforms'] = {}
        metadata['recommendations'] = {}
        metadata['conflicting'] = {}
        metadata['groupings'] = {}
        metadata['replacing'] = {}
        metadata['providing'] = {}
        for type, label in CookbookFile.TYPES:
            data[type] = []
        for file in self.files.all():
            data[file.type].append(file.to_dict(request))
        return data

    def parts(self):
        for type, label in CookbookFile.TYPES:
            qs = self.files.filter(type=type).order_by('name')
            if qs:
                yield type, label(len(qs)), qs


class CookbookFile(models.Model):
    class Meta:
        verbose_name = _('cookbook file')
        verbose_name_plural = _('cookbook files')
    TYPES = (
        ('definitions', lambda n: ungettext_lazy('Definition', 'Definitions', n)),
        ('attributes', lambda n: ungettext_lazy('Attribute', 'Attributes', n)),
        ('files', lambda n: ungettext_lazy('File', 'Files', n)),
        ('libraries', lambda n: ungettext_lazy('Library', 'Libraries', n)),
        ('templates', lambda n: ungettext_lazy('Template', 'Templates', n)),
        ('providers', lambda n: ungettext_lazy('Provider', 'Providers', n)),
        ('resources', lambda n: ungettext_lazy('Resource', 'Resources', n)),
        ('recipes', lambda n: ungettext_lazy('Recipe', 'Recipes', n)),
        ('root_files', lambda n: ungettext_lazy('Root File', 'Root Files', n)),
    )
    cookbook = models.ForeignKey(Cookbook, related_name='files')
    type = models.CharField(max_length=32, choices=[(k, v(1)) for k, v in TYPES])
    name = models.CharField(max_length=1024)
    file = models.ForeignKey(SandboxFile, related_name='cookbook_files')
    path = models.CharField(max_length=1024)
    specificity = models.CharField(max_length=1024)

    def to_dict(self, request=None):
        data = {
            'name': self.name,
            'checksum': self.file.checksum,
            'path': self.path,
            'specificity': self.specificity,
        }
        if request:
            data['url'] = request.build_absolute_uri(reverse('commis_api_cookbooks_file', args=[self.cookbook.name, self.cookbook.version, self.file.checksum]))
        return data


class CookbookDependency(models.Model):
    class Meta:
        verbose_name = _('cookbook dependency')
        verbose_name_plural = _('cookbook dependencies')
    cookbook = models.ForeignKey(Cookbook, related_name='dependencies')
    name = models.CharField(max_length=1024)


class CookbookRecipe(models.Model):
    class Meta:
        verbose_name = _('cookbook recipe')
        verbose_name_plural = _('cookbook recipes')
    cookbook = models.ForeignKey(Cookbook, related_name='recipes')
    name = models.CharField(max_length=1024)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
from commis.test import ChefTestCase

class CookbookAPITestCase(ChefTestCase):
    fixtures = ['cookbook_apt']
    maxDiff = 100000
    
    def test_list(self):
        data = self.api['/cookbooks']
        self.assertEqual(data, {'apt': 'http://testserver/api/cookbooks/apt'})

    def test_get(self):
        data = self.api['/cookbooks/apt']
        self.assertEqual(data, {'apt': ['1.0.0']})

    def test_get_version(self):
        data = self.api['/cookbooks/apt/1.0.0']
        reference = {
            'name': 'apt-1.0.0',
            'cookbook_name': 'apt',
            'version': '1.0.0',
            'json_class': 'Chef::CookbookVersion',
            'chef_type': 'cookbook_version',
            'metadata': {
                'name': 'apt',
                'version': '1.0.0',
                'maintainer': 'Opscode, Inc.',
                'maintainer_email': 'cookbooks@opscode.com',
                'license': 'Apache 2.0',
                'description': 'Configures apt and apt services and an LWRP for managing apt repositories',
                'long_description': 'Description\n===========\n\nConfigures various APT components on Debian-like systems.  Also includes a LWRP.\n\n',
                'dependencies': {
                    'ruby': [],
                },
                'recipes': {
                    'apt': 'Runs apt-get update during compile phase and sets up preseed directories',
                    'apt::cacher': 'Set up an APT cache',
                    'apt::proxy': 'Set up an APT proxy',
                 },
                'attributes': {},
                'suggestions': {},
                'platforms': {},
                'recommendations': {},
                'conflicting': {},
                'groupings': {},
                'replacing': {},
                'providing': {},
            },
            'attributes': [],
            'definitions': [],
            'files': [
                {
                    'checksum': '046661f9e728b783ea90738769219d71',
                    'name': 'apt-cacher',
                    'specificity': 'default',
                    'path': 'files/default/apt-cacher',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/046661f9e728b783ea90738769219d71',
                },
                {
                    'checksum': '3e4afb4ca7cb38b707b803cbb2a316a7',
                    'name': 'apt-cacher.conf',
                    'specificity': 'default',
                    'path': 'files/default/apt-cacher.conf',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/3e4afb4ca7cb38b707b803cbb2a316a7',
                },
                {
                    'checksum': 'a67a0204d4c54848aad67a8e9de5cad1',
                    'name': 'apt-proxy-v2.conf',
                    'specificity': 'default',
                    'path': 'files/default/apt-proxy-v2.conf',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/a67a0204d4c54848aad67a8e9de5cad1',
                },
            ],
            'libraries': [],
            'providers': [],
            'recipes': [
                {
                    'checksum': '5479013c6f17fb6e1930ea31e8fb1df5',
                    'name': 'cacher.rb',
                    'specificity': 'default',
                    'path': 'recipes/cacher.rb',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/5479013c6f17fb6e1930ea31e8fb1df5',
                },
                {
                    'checksum': '112a8c22a020417dcc1c1fd06a4312ef',
                    'name': 'default.rb',
                    'specificity': 'default',
                    'path': 'recipes/default.rb',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/112a8c22a020417dcc1c1fd06a4312ef',
                },
                {
                    'checksum': '434450082c67c354884c4b8b5db23ffb',
                    'name': 'proxy.rb',
                    'specificity': 'default',
                    'path': 'recipes/proxy.rb',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/434450082c67c354884c4b8b5db23ffb',
                },
            ],
            'resources': [
                {
                    'checksum': '33653076212a8b7737838198bbea2d72',
                    'name': 'repository.rb',
                    'specificity': 'default',
                    'path': 'resources/repository.rb',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/33653076212a8b7737838198bbea2d72',
                },
            ],
            'root_files': [
                {
                    'checksum': '3e7cc22c3f9a1a9e8708d5c2a3cd2d64',
                    'name': 'metadata.json',
                    'specificity': 'default',
                    'path': 'metadata.json',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/3e7cc22c3f9a1a9e8708d5c2a3cd2d64',
                },
                {
                    'checksum': '4d80cafd968bb603d9f1a6a9422663e4',
                    'name': 'metadata.rb',
                    'specificity': 'default',
                    'path': 'metadata.rb',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/4d80cafd968bb603d9f1a6a9422663e4',
                },
                {
                    'checksum': 'c7faa6cd1213a6afff1e59ee447b9fd0',
                    'name': 'README.md',
                    'specificity': 'default',
                    'path': 'README.md',
                    'url': 'http://testserver/api/cookbooks/apt/1.0.0/files/c7faa6cd1213a6afff1e59ee447b9fd0',
                },
            ],
            'templates': [],
        }
        self.assertEqual(data, reference)

########NEW FILE########
__FILENAME__ = views
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from pkg_resources import parse_version

from commis.exceptions import ChefAPIError
from commis.generic_views import CommisAPIView, api, CommisViewBase
from commis.cookbooks.models import Cookbook, CookbookFile

class CookbookAPIView(CommisAPIView):
    model = Cookbook

    @api('GET')
    def list(self, request):
        data = {}
        # Expected format for Chef 0.10:
        # {
        #   'cookbook_name': {
        #       'versions': [
        #           {'version': <version_number>, 'url': <url>},
        #           ...
        #       ]
        #   },
        #   ...
        # }
        for obj in self.model.objects.all():
            url = self.reverse(request, 'get', obj)
            data[obj.name] = {'versions': [{'version': obj.version, 'url': url}]}
        return data

    @api('GET')
    def get(self, request, name):
        versions = Cookbook.objects.filter(name=name).values_list('version', flat=True)
        if not versions:
            raise ChefAPIError(404, 'Cookbook %s not found', name)
        return {name: versions}

    @api('GET')
    def version(self, request, name, version):
        try:
            cookbook = Cookbook.objects.get(name=name, version=version)
        except Cookbook.DoesNotExist:
            raise ChefAPIError(404, 'Cookbook %s@%s not found', name, version)
        return cookbook.to_dict(request)

    @api('PUT', admin=True)
    def update(self, request, name, version):
        cookbook = Cookbook.objects.from_dict(request.json)
        return cookbook.to_dict(request)

    @api('DELETE', admin=True)
    def delete(self, request, name, version):
        qs = Cookbook.objects.filter(name=name, version=version)
        if not qs.exists():
            raise ChefAPIError(404, 'Cookbook %s@%s not found', name, version)
        qs.delete()
        return {}

    @api('GET', '{name}/{version}/files/{checksum}')
    def file(self, request, name, version, checksum):
        qs = CookbookFile.objects.select_related('file').filter(cookbook__name=name, cookbook__version=version, file__checksum=checksum, file__uploaded=True)
        if not qs:
            raise ChefAPIError(404, 'File not found')
        cookbook_file = qs[0]
        response = HttpResponse(cookbook_file.file.content, content_type=cookbook_file.file.content_type)
        return response


class CookbookView(CommisViewBase):
    model = Cookbook

    def has_permission(self, request, action, obj=None):
        if action != 'list' and action != 'show':
            return False
        return super(CookbookView, self).has_permission(request, action, obj)

    def reverse(self, request, action, *args):
        if action == 'show':
            obj = args[0]
            args = obj.name, obj.version
        return super(CookbookView, self).reverse(request, action, *args)

    def list(self, request, name=None):
        opts = self.model._meta
        self.assert_permission(request, 'list')
        qs = self.model.objects.all()
        if name:
            qs = qs.filter(name=name)
        cookbooks = {}
        for obj in qs:
            cookbooks.setdefault(obj.name, []).append((obj, self.block_nav(request, obj)))
        for name, cookbook_list in cookbooks.iteritems():
            cookbook_list.sort(key=lambda x: parse_version(x[0].version), reverse=True)
        cookbooks = sorted(cookbooks.iteritems())
        return TemplateResponse(request, 'commis/%s/list.html'%self.get_app_label(), {
            'opts': opts,
            'object_list': cookbooks,
            'action': 'list',
            'block_nav': self.block_nav(request),
        })

    def show(self, request, name, version):
        opts = self.model._meta
        obj = get_object_or_404(self.model, name=name, version=version)
        self.assert_permission(request, 'show', obj)
        return TemplateResponse(request, 'commis/%s/show.html'%self.get_app_label(), {
            'opts': opts,
            'obj': obj,
            'action': 'show',
            'block_nav': self.block_nav(request, obj),
        })

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^$',
                self.list,
                name='commis_webui_%s_list' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/$',
                self.list,
                name='commis_webui_%s_list_single' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/(?P<version>[^/]+)/$',
                self.show,
                name='commis_webui_%s_show' % self.get_app_label()),
        )
        return urlpatterns

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import ValidationError

from commis.data_bags.models import DataBag, DataBagItem
from commis.utils import json

class DataBagForm(forms.ModelForm):
    class Meta:
        model = DataBag
        fields = ('name',) 


class DataBagItemForm(forms.ModelForm):
    class Meta:
        model = DataBagItem
        fields = ('name', 'data') 

    def __init__(self, bag, *args, **kwargs):
        super(DataBagItemForm, self).__init__(*args, **kwargs)
        self.__bag = bag

    def save(self, *args, **kwargs):
        self.instance.bag = self.__bag
        return super(DataBagItemForm, self).save(*args, **kwargs)

    def clean_data(self):
        try:
            json.loads(self.cleaned_data['data'])
        except ValueError, e:
            raise ValidationError(str(e))
        return self.cleaned_data['data']

########NEW FILE########
__FILENAME__ = models
import chef
from django.db import models

from commis.utils import json

class DataBagManager(models.Manager):
    def from_dict(self, data):
        return self.get_or_create(name=data['name'])[0]


class DataBag(models.Model):
    name = models.CharField(max_length=1024, unique=True)

    objects = DataBagManager()

    def __unicode__(self):
        return self.name

    def to_dict(self):
        chef_bag = chef.DataBag(self.name, skip_load=True)
        return chef_bag


class DataBagItem(models.Model):
    bag = models.ForeignKey(DataBag, related_name='items')
    name = models.CharField(max_length=1024)
    data = models.TextField()

    def __unicode__(self):
        return self.name

    @property
    def object(self):
        if self.data:
            return json.loads(self.data)
        return {}

    def to_search(self):
        data = self.object
        data['chef_type'] = 'data_bag_item'
        data['data_bag'] = self.bag.name
        return data

    def to_dict(self):
        return {
            'name': 'data_bag_item_%s_%s'%(self.bag.name, self.name),
            'data_bag': self.bag.name,
            'json_class': 'Chef::DataBagItem',
            'chef_type': 'data_bag_item',
            'raw_data': json.loads(self.data),
        }
########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes, site

from commis.data_bags.models import DataBagItem
from commis.search.indexes import CommisSearchIndex

class DataBagItemIndex(CommisSearchIndex):
    data_bag = indexes.CharField(model_attr='bag__name')

site.register(DataBagItem, DataBagItemIndex)

########NEW FILE########
__FILENAME__ = tests
import chef

from commis.test import ChefTestCase
from commis.data_bags.models import DataBag, DataBagItem
from commis.utils import json

class DataBagAPITestCase(ChefTestCase):
    def test_list(self):
        DataBag.objects.create(name='mybag')
        self.assertIn('mybag', chef.DataBag.list())

    def test_create(self):
        chef.DataBag.create('mybag')
        DataBag.objects.get(name='mybag')

    def test_get(self):
        bag = DataBag.objects.create(name='mybag')
        bag.items.create(name='item1', data='{"id":"item1"}')
        bag.items.create(name='item2', data='{"id":"item2"}')
        self.assertEqual(len(chef.DataBag('mybag')), 2)
        self.assertIn('item1', chef.DataBag('mybag'))
        self.assertIn('item2', chef.DataBag('mybag'))

    def test_delete(self):
        DataBag.objects.create(name='mybag')
        chef.DataBag('mybag').delete()
        with self.assertRaises(DataBag.DoesNotExist):
            DataBag.objects.get(name='mybag')


class DataBagItemAPITestCase(ChefTestCase):
    def test_create(self):
        DataBag.objects.create(name='mybag')
        chef.DataBagItem.create('mybag', 'item1', attr=1)
        chef.DataBagItem.create('mybag', 'item2', attr=2)
        bag = DataBag.objects.get(name='mybag')
        self.assertEqual(bag.items.count(), 2)
        item = bag.items.get(name='item1')
        self.assertEqual(json.loads(item.data), {'id': 'item1', 'attr': 1})
        item = bag.items.get(name='item2')
        self.assertEqual(json.loads(item.data), {'id': 'item2', 'attr': 2})

    def test_get(self):
        bag = DataBag.objects.create(name='mybag')
        data = {'id': 'myitem', 'attr': 1, 'nested': {'nested_attr': 'foo'}}
        bag.items.create(name='myitem', data=json.dumps(data))
        chef_item = chef.DataBagItem('mybag', 'myitem')
        self.assertEqual(data, chef_item)

    def test_update(self):
        bag = DataBag.objects.create(name='mybag')
        data = {'id': 'myitem', 'attr': 1, 'nested': {'nested_attr': 'foo'}}
        bag.items.create(name='myitem', data=json.dumps(data))
        chef_item = chef.DataBagItem('mybag', 'myitem')
        chef_item['attr'] = 2
        chef_item['nested']['nested_attr'] = 'bar'
        chef_item.save()
        data2 = {'id': 'myitem', 'attr': 2, 'nested': {'nested_attr': 'bar'}}
        item = DataBagItem.objects.get(bag__name='mybag', name='myitem')
        self.assertEqual(json.loads(item.data), data2)

    def test_delete(self):
        bag = DataBag.objects.create(name='mybag')
        bag.items.create(name='myitem', data='{"id":"myitem"}')
        chef.DataBagItem('mybag', 'myitem').delete()
        with self.assertRaises(DataBagItem.DoesNotExist):
            DataBagItem.objects.get(bag__name='mybag', name='myitem')

########NEW FILE########
__FILENAME__ = views
import functools

from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.translation import ugettext as _

from commis.exceptions import ChefAPIError
from commis.generic_views import CommisAPIView, api, CommisView
from commis.data_bags.forms import DataBagForm, DataBagItemForm
from commis.data_bags.models import DataBag, DataBagItem
from commis.db import update

class DataBagAPIView(CommisAPIView):
    model = DataBag
    item_model = DataBagItem

    def get_item_or_404(self, bag_name, name):
        bag = self.get_or_404(bag_name)
        try:
            return bag.items.get(name=name)
        except self.item_model.DoesNotExist:
            raise ChefAPIError(404, '%s %s::%s not found', self.item_model._meta.verbose_name.capitalize(), bag_name, name)

    def get_data(self, request, bag):
        data = {}
        for item in bag.items.all():
            data[item.name] = self.reverse(request, 'item_get', bag, item)
        return data

    @api('POST', admin=True)
    def item_create(self, request, name):
        json = request.json.get('raw_data', {})
        if not json or 'id' not in json:
            raise ChefAPIError(500, 'No item ID specified')
        bag = self.get_or_404(name)
        if bag.items.filter(name=json['id']).exists():
            raise ChefAPIError(409, 'Data bag item %s::%s already exists', name, json['id'])
        bag.items.create(name=json['id'], data=request.raw_post_data)
        return request.json

    @api('GET')
    def item_get(self, request, bag_name, name):
        item = self.get_item_or_404(bag_name, name)
        return HttpResponse(item.data, status=200, content_type='application/json')

    @api('PUT', admin=True)
    def item_update(self, request, bag_name, name):
        if not request.json:
            raise ChefAPIError(500, 'No data sent')
        if request.json.get('id') != name:
            raise ChefAPIError(500, 'Name mismatch in data bag item')
        item = self.get_item_or_404(bag_name, name)
        update(item, data=request.raw_post_data)
        return HttpResponse(item.data, status=200, content_type='application/json')

    @api('DELETE', admin=True)
    def item_delete(self, request, bag_name, name):
        item = self.get_item_or_404(bag_name, name)
        item.delete()
        return HttpResponse(item.data, status=200, content_type='application/json')


class DataBagView(CommisView):
    model = DataBag
    item_model = DataBagItem
    form = DataBagForm
    item_form = DataBagItemForm

    def show_response(self, request, obj):
        response = super(DataBagView, self).list_response(request, obj.items.all())
        response.context_data['obj'] = obj
        response.context_data['action'] = 'show'
        response.context_data['block_nav'] = self.block_nav(request, obj)
        return response

    def create_item(self, request, name):
        opts = self.item_model._meta
        bag = self.get_object(request, name)
        self.assert_permission(request, 'create_item', bag)
        form_class = functools.partial(self.item_form, bag)
        if request.method == 'POST':
            form = form_class(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _('Created %(verbose_name)s %(object)s')%{'verbose_name':opts.verbose_name, 'object':form.cleaned_data[self.search_key]})
                return self.change_redirect(request, 'create_item', form.instance)
        else:
            form = form_class()
        response = self.create_response(request, form)
        response.context_data['action'] = 'create_item'
        response.context_data['block_nav'] = self.block_nav(request, bag)
        return response

    def show_item(self, request, name, item_name):
        bag = self.get_object(request, name)
        try:
            item = bag.items.get(name=item_name)
        except self.item_model.DoesNotExist:
            raise Http404
        response = super(DataBagView, self).show_response(request, item)
        response.context_data['action'] = 'show_item'
        return response

    def reverse(self, request, action, *args):
        if args and isinstance(args[0], self.item_model):
            action += '_item'
            args = args[0].bag.name, args[0].name
        return super(DataBagView, self).reverse(request, action, *args)

    def block_nav(self, request, obj=None):
        data = super(DataBagView, self).block_nav(request, obj)
        if obj is not None:
            if isinstance(obj, self.model):
                bag = obj
                item = None
            elif isinstance(obj, self.item_model):
                bag = obj.bag
                item = obj
            if self.has_permission(request, 'create_item', bag):
                data.insert(data.keyOrder.index('create')+1, 'create_item', {'label': _('Create Item'), 'link': self.reverse(request, 'create_item', bag)})
            del data['create']
            if item is not None:
                if self.has_permission(request, 'show', bag):
                    data['list']['link'] = self.reverse(request, 'show', bag)
                else:
                    del data['list']
                
                #data['show']['label'] = _('Show Bag')
                #data['show']['link'] = self.reverse(request, 'show', bag)
                data.insert(data.keyOrder.index('show')+1, 'show_item', {'label': _('Show Item'), 'link': self.reverse(request, 'show', item)})
        return data

    def change_redirect(self, request, action, obj):
        if action.endswith('_item'):
            if self.has_permission(request, 'show_item', obj):
                return HttpResponseRedirect(reverse('commis_webui_%s_show_item'%self.get_app_label(), args=(obj.bag, obj)))
            elif self.has_permission(request, 'show', obj.bag):
                return HttpResponseRedirect(reverse('commis_webui_%s_show'%self.get_app_label(), args=(obj.bag,)))
            else:
                return HttpResponseRedirect(reverse('commis_webui_%s_list'%self.get_app_label()))
        return super(DataBagView, self).change_redirect(request, action, obj)

    # XXX: With a better permissions system this shouldn't be needed at all. <NPK 2011-05-07>
    def has_permission(self, request, action, obj=None):
        if action.endswith('_item'):
            action = {
                'create_item': 'edit',
                'show_item': 'show',
                'edit_item': 'edit',
                'delete_item': 'delete',
            }[action]
        return super(DataBagView, self).has_permission(request, action, obj)

    def get_urls(self):
        return super(DataBagView, self).get_urls() + patterns('',
            url(r'^(?P<name>[^/]+)/new/$',
                self.create_item,
                name='commis_webui_%s_create_item' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/(?P<item_name>[^/]+)/delete/$',
                self.show_item,
                name='commis_webui_%s_delete_item' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/(?P<item_name>[^/]+)/edit/$',
                self.show_item,
                name='commis_webui_%s_edit_item' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/(?P<item_name>[^/]+)/$',
                self.show_item,
                name='commis_webui_%s_show_item' % self.get_app_label()),
        )
########NEW FILE########
__FILENAME__ = update
import operator

from django.db.models import signals
from django.db.models.expressions import F, ExpressionNode

EXPRESSION_NODE_CALLBACKS = {
    ExpressionNode.ADD: operator.add,
    ExpressionNode.SUB: operator.sub,
    ExpressionNode.MUL: operator.mul,
    ExpressionNode.DIV: operator.div,
    ExpressionNode.MOD: operator.mod,
    ExpressionNode.AND: operator.and_,
    ExpressionNode.OR: operator.or_,
    }

class CannotResolve(Exception):
    pass

def _resolve(instance, node):
    if isinstance(node, F):
        return getattr(instance, node.name)
    elif isinstance(node, ExpressionNode):
        return _resolve(instance, node)
    return node

def resolve_expression_node(instance, node):
    op = EXPRESSION_NODE_CALLBACKS.get(node.connector, None)
    if not op:
        raise CannotResolve
    runner = _resolve(instance, node.children[0])
    for n in node.children[1:]:
        runner = op(runner, _resolve(instance, n))
    return runner

def update(instance, **kwargs):
    "Atomically update instance, setting field/value pairs from kwargs"
    # fields that use auto_now=True should be updated corrected, too!
    for field in instance._meta.fields:
        if hasattr(field, 'auto_now') and field.auto_now and field.name not in kwargs:
            kwargs[field.name] = field.pre_save(instance, False)

    signals.pre_save.send(sender=instance.__class__, instance=instance, raw=False, using=None)
    rows_affected = instance.__class__._default_manager.filter(pk=instance.pk).update(**kwargs)
    signals.post_save.send(sender=instance.__class__, instance=instance, created=False, raw=False, using=None)

    # apply the updated args to the instance to mimic the change
    # note that these might slightly differ from the true database values
    # as the DB could have been updated by another thread. callers should
    # retrieve a new copy of the object if up-to-date values are required
    for k,v in kwargs.iteritems():
        if isinstance(v, ExpressionNode):
            v = resolve_expression_node(instance, v)
        setattr(instance, k, v)

    # If you use an ORM cache, make sure to invalidate the instance!
    #cache.set(djangocache.get_cache_key(instance=instance), None, 5)
    return rows_affected

########NEW FILE########
__FILENAME__ = views
from commis.generic_views import CommisAPIViewBase, api
from commis.cookbooks.models import Cookbook


class EnvironmentAPIView(CommisAPIViewBase):
    app_label = 'environments'

    @api('POST', url=r'(?P<name>[^/]+)')
    def create(self, request, name):
        # We actually don't use `name` here as it should always be _default
        # when not using Chef's environments feature.
        data = {}
        for obj in Cookbook.objects.all():
            data[obj.name] = obj.to_dict(request)
        return data

########NEW FILE########
__FILENAME__ = exceptions
class ChefAPIError(Exception):
    def __init__(self, code, msg, *args):
        self.code = code
        self.msg = msg%args


class InsuffcientPermissions(Exception):
    """Token error for permissions failure."""

    def __init__(self, model, action):
        self.model = model
        self.action = action

########NEW FILE########
__FILENAME__ = api
from functools import wraps

from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from commis.utils.chef_api import execute_request
from commis.exceptions import ChefAPIError
from commis.generic_views.base import CommisGenericViewBase
from commis.utils import json, routes


def api(method, url=None, admin=False, validator=None):
    def dec(fn):
        # Return modified function wrapping fn and possibly doing work before
        # it runs.
        @wraps(fn)
        def inner(*args, **kwargs):
            if validator is not None:
                validator(*args, **kwargs)
            return fn(*args, **kwargs)

        # Decorate returned function with API metadata
        if url is not None:
            realurl = routes.route_from_string(url)
        else:
            realurl = routes.route_from_function(fn)
        inner._commis_api = {
            'name': fn.__name__,
            'url': realurl,
            'method': method,
            'admin': admin,
        }
        return inner
    return dec


class _DispatchView(object):
    def __init__(self, view_map):
        self.view_map = view_map

    def __call__(self, instance):
        return _BoundDispatchView(self, instance)


class _BoundDispatchView(object):
    def __init__(self, dispatch_view, instance):
        self.dispatch_view = dispatch_view
        self.instance = instance
        if 'GET' in self.dispatch_view.view_map:
            name = self.dispatch_view.view_map['GET'].__name__
        else:
            name = self.dispatch_view.view_map.values()[0].__name__
        self.name = 'commis_api_%s_%s'%(instance.get_app_label(), name)

    def __call__(self, request, *args, **kwargs):
        view = self.dispatch_view.view_map.get(request.method)
        def wrapper_view(request, *args, **kwargs):
            if view._commis_api['admin'] and not request.client.admin:
                raise ChefAPIError(403, 'You are not allowed to take this action')
            return view(self.instance, request, *args, **kwargs)
        return execute_request(wrapper_view, request, *args, **kwargs)


class CommisAPIViewMeta(type):
    def __init__(self, name, bases, d):
        super(CommisAPIViewMeta, self).__init__(name, bases, d)
        self.views = {}
        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_commis_api'):
                #view = method_decorator(chef_api(admin=obj._commis_api['admin']))(obj)
                #view._commis_api = obj._commis_api
                self.views.setdefault(obj._commis_api['url'], {})[obj._commis_api['method']] = getattr(self, name)

        self.dispatch_views = {}
        for url_pattern, view_map in self.views.iteritems():
            self.dispatch_views[url_pattern] = _DispatchView(view_map)


class CommisAPIViewBase(CommisGenericViewBase):
    __metaclass__ = CommisAPIViewMeta

    def reverse(self, request, tag, *args):
        return request.build_absolute_uri(reverse('commis_api_%s_%s'%(self.get_app_label(), tag), args=args))

    def get_or_404(self, name, model=None):
        if model is None:
            model = self.model
        try:
            return model.objects.get(name=name)
        except model.DoesNotExist:
            raise ChefAPIError(404, '%s %s not found', model._meta.verbose_name.capitalize(), name)

    def get_urls(self):
        urlpatterns = patterns('')
        dispatch_views = self.dispatch_views.items()
        dispatch_views.sort(key=lambda x: len(x[0]), reverse=True)
        for url_pattern, dispatch_view in dispatch_views:
            bound_view = dispatch_view(self)
            urlpatterns.append(url(url_pattern, csrf_exempt(bound_view), name=bound_view.name))
        return urlpatterns


class CommisAPIView(CommisAPIViewBase):
    @api('GET')
    def list(self, request):
        data = {}
        # This could be sped up by using .values_list('name', flat=true)
        for obj in self.model.objects.all():
            data[obj.name] = self.reverse(request, 'get', obj)
        return data

    @api('POST', admin=True)
    def create(self, request):
        if self.model.objects.filter(name=request.json['name']).exists():
            raise ChefAPIError(409, '%s %s already exists', self.model._meta.verbose_name, request.json['name'])
        obj = self.model.objects.from_dict(request.json)
        data = self.create_data(request, obj)
        return HttpResponse(json.dumps(data), status=201, content_type='application/json')

    def create_data(self, request, obj):
        return {'uri': self.reverse(request, 'get', obj)}

    @api('GET')
    def get(self, request, name):
        obj = self.get_or_404(name)
        return self.get_data(request, obj)

    def get_data(self, request, obj):
        return obj

    @api('PUT', admin=True)
    def update(self, request, name):
        if request.json['name'] != name:
            raise ChefAPIError(500, 'Name mismatch')
        if not self.model.objects.filter(name=name).exists():
            raise ChefAPIError(404, '%s %s not found', self.model._meta.verbose_name, name)
        obj = self.model.objects.from_dict(request.json)
        return self.update_data(request, obj)

    def update_data(self, request, obj):
        return obj

    @api('DELETE', admin=True)
    def delete(self, request, name):
        obj = self.get_or_404(name)
        obj.delete()
        return self.delete_data(request, obj)

    def delete_data(self, request, obj):
        return obj

########NEW FILE########
__FILENAME__ = base
from django.utils.decorators import classonlymethod

class CommisGenericViewBase(object):
    model = None
    app_label = None
    model_name = None

    def get_app_label(self):
        return self.app_label or self.model._meta.app_label

    def get_model_name(self):
        return self.model_name or self.model._meta.object_name

    def get_urls(self):
        raise NotImplementedError

    @property
    def urls(self):
        return self.get_urls()

    @classonlymethod
    def as_view(cls):
        self = cls()
        return self.urls

########NEW FILE########
__FILENAME__ = webui
from django.conf.urls.defaults import patterns, url
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext as _

from commis.exceptions import InsuffcientPermissions
from commis.generic_views.base import CommisGenericViewBase
from commis.utils.deleted_objects import get_deleted_objects

class CommisViewBase(CommisGenericViewBase):
    form = None
    create_form = None
    edit_form = None
    search_key = 'name'

    def get_create_form(self, request):
        if self.create_form is not None:
            return self.create_form
        return self.form

    def get_edit_form(self, request):
        if self.edit_form is not None:
            return self.edit_form
        return self.form

    def get_object(self, request, name):
        return get_object_or_404(self.model, **{self.search_key: name})

    def has_permission(self, request, action, obj=None):
        if action == 'list' or action == 'show':
            # I don't, yet, have an actual Django permission for list or show
            return request.user.is_authenticated()
        # Django spells these actions differently
        django_action = {
            'create': 'add',
            'edit': 'change',
            'delete': 'delete',
        }[action]
        permission = '%s.%s_%s'%(self.get_app_label(), django_action, self.get_model_name().lower())
        return request.user.has_perm(permission)

    def assert_permission(self, request, action, obj=None):
        if not self.has_permission(request, action, obj):
            raise InsuffcientPermissions(self.model, action)

    def reverse(self, request, action, *args):
        return reverse('commis_webui_%s_%s'%(self.get_app_label(), action), args=args)

    def block_nav(self, request, obj=None):
        data = SortedDict()
        data.name = self.model and self.model.__name__.lower() or self.get_app_label()
        data['list'] = {'label': _('List'), 'link': self.reverse(request, 'list')}
        if self.has_permission(request, 'create'):
            data['create'] = {'label': _('Create'), 'link': self.reverse(request, 'create')}
        if obj is not None:
            if self.has_permission(request, 'show', obj):
                data['show'] = {'label': _('Show'), 'link': self.reverse(request, 'show', obj)}
            if self.has_permission(request, 'edit', obj):
                data['edit'] = {'label': _('Edit'), 'link': self.reverse(request, 'edit', obj)}
            if self.has_permission(request, 'delete', obj):
                data['delete'] = {'label': _('Delete'), 'link': self.reverse(request, 'delete', obj)}
        return data


class CommisView(CommisViewBase):
    def list(self, request):
        self.assert_permission(request, 'list')
        return self.list_response(request, self.model.objects.all())

    def list_response(self, request, qs):
        opts = self.model._meta
        return TemplateResponse(request, ('commis/%s/list.html'%self.get_app_label(), 'commis/generic/list.html'), {
            'opts': opts,
            'object_list': [(obj, self.block_nav(request, obj)) for obj in qs],
            'action': 'list',
            'block_nav': self.block_nav(request),
        })

    def create(self, request):
        opts = self.model._meta
        self.assert_permission(request, 'create')
        form_class = self.get_create_form(request)
        if request.method == 'POST':
            form = form_class(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _('Created %(verbose_name)s %(object)s')%{'verbose_name':opts.verbose_name, 'object':form.cleaned_data[self.search_key]})
                return self.change_redirect(request, 'create', form.instance)
        else:
            form = form_class()
        return self.create_response(request, form)

    def create_response(self, request, form):
        opts = self.model._meta
        return TemplateResponse(request, ('commis/%s/edit.html'%self.get_app_label(), 'commis/generic/edit.html'), {
            'opts': opts,
            'obj': self.model(),
            'form': form,
            'action': 'create',
            'block_nav': self.block_nav(request),
        })

    def show(self, request, name):
        obj = self.get_object(request, name)
        self.assert_permission(request, 'show', obj)
        return self.show_response(request, obj)

    def show_response(self, request, obj):
        opts = self.model._meta
        return TemplateResponse(request, 'commis/%s/show.html'%self.get_app_label(), {
            'opts': opts,
            'obj': obj,
            'action': 'show',
            'block_nav': self.block_nav(request, obj),
        })

    def edit(self, request, name):
        opts = self.model._meta
        obj = self.get_object(request, name)
        self.assert_permission(request, 'edit', obj)
        form_class = self.get_edit_form(request)
        if request.method == 'POST':
            form = form_class(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                messages.success(request, _('Edited %(verbose_name)s %(object)s')%{'verbose_name':opts.verbose_name, 'object':form.cleaned_data[self.search_key]})
                return self.change_redirect(request, 'edit', obj)
        else:
            form = form_class(instance=obj)
        return self.edit_response(request, obj, form)

    def edit_response(self, request, obj, form):
        opts = self.model._meta
        return TemplateResponse(request, ('commis/%s/edit.html'%self.get_app_label(), 'commis/generic/edit.html'), {
            'opts': opts,
            'obj': obj,
            'form': form,
            'action': 'edit',
            'block_nav': self.block_nav(request, obj),
        })

    def delete(self, request, name):
        opts = self.model._meta
        obj = self.get_object(request, name)
        self.assert_permission(request, 'delete', obj)
        deleted_objects, perms_needed, protected = get_deleted_objects(obj, request)
        if request.POST: # The user has already confirmed the deletion.
            if perms_needed:
                raise PermissionDenied
            obj.delete()
            messages.success(request, _(u'Deleted %s %s')%(opts.verbose_name, obj))
            return self.change_redirect(request, 'delete', obj)
        return TemplateResponse(request, ('commis/%s/delete.html'%self.get_app_label(), 'commis/generic/delete.html'), {
            'opts': opts,
            'obj': obj,
            'action': 'delete',
            'block_nav': self.block_nav(request, obj),
            'deleted_objects': deleted_objects,
            'perms_lacking': perms_needed,
            'protected': protected,
        })

    def change_redirect(self, request, action, obj):
        if action != 'delete' and self.has_permission(request, 'show', obj):
            name, args = 'show', (obj,)
        else:
            name, args = 'list', ()
        url = reverse('commis_webui_%s_%s' % (self.get_app_label(), name), args=args)
        return HttpResponseRedirect(url)

    def get_urls(self):
        return patterns('',
            url(r'^$',
                self.list,
                name='commis_webui_%s_list' % self.get_app_label()),
            url(r'^new/$',
                self.create,
                name='commis_webui_%s_create' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/delete/$',
                self.delete,
                name='commis_webui_%s_delete' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/edit/$',
                self.edit,
                name='commis_webui_%s_edit' % self.get_app_label()),
            url(r'^(?P<name>[^/]+)/$',
                self.show,
                name='commis_webui_%s_show' % self.get_app_label()),
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
__FILENAME__ = commis_client
import os
import sys
from optparse import make_option

from django.core.management.base import BaseCommand

from commis import conf

class Command(BaseCommand):
    help = 'Generate a Chef API client'

    option_list = BaseCommand.option_list + (
        make_option('-o', '--output',
            help='Path to write key.'),
        make_option('--validator', action='store_true', default=False,
            help='Generate a validator key'),
        make_option('-a', '--admin', action='store_true', default=False,
            help='Generate an admin client'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--force', action='store_true', default=False,
            help='Continue despite the possibility of data loss.'),
        )

    def ask(self, msg, options):    
        interactive = options.get('interactive')
        force = options.get('force')

        if force:
            return True
        if interactive:
            confirm = None
            while not confirm or confirm[0] not in 'yn':
                try:
                    confirm = raw_input(msg+" [yN]").lower()
                except KeyboardInterrupt:
                    confirm = 'n'
                if not confirm:
                    confirm = 'n'
            return confirm[0] == 'y'
        else:
            return False

    def handle(self, *args, **options):
        from commis.clients.models import Client
        output = options.get('output')
        if options.get('validator'):
            if args:
                sys.stderr.write('Error: --validator is mutually exclusive with name argument\n')
                return 1
            if options.get('admin'):
                sys.stderr.write('Error: --validator is mutually exclusive with --admin\n')
                return 1
            name = conf.COMMIS_VALIDATOR_NAME
            default_output = 'validation.pem'
        elif args:
            name = args[0]
            default_output = name + '.pem'
        else:
            sys.stderr.write('Error: No name specified\n')
            return 1

        if not output:
            output = default_output

        qs = Client.objects.filter(name=name)
        if qs.exists():
            if self.ask('A client named %s already exists. Would you like to create a new key?'%name, options):
                qs.delete()
            else:
                return
        if output != '-' and os.path.exists(output):
            if not self.ask('A file %s already exists. Would you like to overwrite it?'%output, options):
                return

        client = Client.objects.create(name=name, admin=bool(options.get('admin')))
        if output == '-':
            outf = self.stdout
        else:
            outf = open(output, 'wb')
        outf.write(client.key.private_export())

########NEW FILE########
__FILENAME__ = middleware
import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.http import urlquote

from commis.exceptions import InsuffcientPermissions
from commis.utils import json

logger = logging.getLogger(__name__)

class LogOutputMiddleware(object):
    def process_response(self, request, response):
        # We're primarily interested in debuggin API output.
        # Non-API URLs are typically hit by a user who will see the debug info
        # in the browser. API can't do that!
        if request.path.startswith("/api"):
            content = response.content
            # JSON responses (caveat: this is probably all of them...) should
            # get pretty-printed
            if response['content-type'] == 'application/json':
                obj = json.loads(content)
                # And responses containing a top level traceback key should
                # also pretty-print that value.
                traceback = obj and obj.pop('traceback', None)
                if traceback is not None:
                    logger.debug(traceback)
                content = json.dumps(obj, indent=4)
            logger.debug(content)
        return response

    def process_exception(self, request, exception):
        logger.info(exception)


class PermissionsMiddleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, InsuffcientPermissions):
            if request.user.is_authenticated():
                # Logged in, send back a nice page
                    return TemplateResponse(request, 'commis/403.html', {})
            else:
                # Not logged in, redirect
                return HttpResponseRedirect(request.build_absolute_uri(reverse('django.contrib.auth.views.login') + '?next=' + urlquote(request.get_full_path())))

########NEW FILE########
__FILENAME__ = models
# This space left intentionally blank

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from commis.cookbooks.models import CookbookRecipe
from commis.nodes.models import Node
from commis.roles.models import Role

class NodeRunList(forms.SelectMultiple):
    def __init__(self, attrs=None, environment=None):
        super(NodeRunList, self).__init__(attrs)
        self.environment = environment

    def render(self, name, value, attrs=None):
        return render_to_string('commis/nodes/_run_list.html', {
            'value': value,
            'available_roles': Role.objects.all(),
            'available_recipes': CookbookRecipe.objects.all(),
        })


class MultipleChoiceAnyField(forms.MultipleChoiceField):
    """A MultipleChoiceField with no validation."""

    def valid_value(self, *args, **kwargs):
        return True


class NodeForm(forms.ModelForm):
    run_list = MultipleChoiceAnyField(required=False)

    class Meta:
        model = Node
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.initial['run_list'] = [str(entry) for entry in self.instance.run_list.all()]
        self.fields['run_list'].widget = NodeRunList()

    def clean_run_list(self):
        run_list = self.cleaned_data['run_list']
        ret = []
        for entry in run_list:
            if '[' not in entry:
                raise ValidationError('Unparseable run list entry "%s"' % entry)
            entry_type, entry_name = entry.rstrip(']').split('[', 1)
            entry_class = {'role': Role, 'recipe': CookbookRecipe}.get(entry_type)
            if entry_class is None:
                raise ValidationError('Unknown run list entry type "%s"' % entry_type)
            if not entry_class.objects.filter(name=entry_name).exists():
                raise ValidationError('Unknown %s "%s"' % (entry_class._meta.verbose_name, entry_name))
            ret.append({'type': entry_type, 'name': entry_name})
        return ret

    def save(self, *args, **kwargs):
        node = super(NodeForm, self).save(*args, **kwargs)
        node.run_list.all().delete()
        for entry in self.cleaned_data['run_list']:
            node.run_list.create(**entry)
        return node

########NEW FILE########
__FILENAME__ = models
import chef
from django.core.urlresolvers import reverse
from django.db import models

from commis.roles.models import Role
from commis.utils import json
from commis.utils.dict import deep_merge

class NodeManager(models.Manager):
    def from_dict(self, data):
        chef_node = chef.Node.from_search(data)
        node, created = self.get_or_create(name=chef_node.name)
        node.automatic_data = json.dumps(chef_node.automatic)
        node.override_data = json.dumps(chef_node.override)
        node.normal_data = json.dumps(chef_node.normal)
        node.default_data = json.dumps(chef_node.default)
        node.save()
        node.run_list.all().delete()
        for entry in chef_node.run_list:
            if '[' not in entry:
                continue # Can't parse this
            type, name = entry.split('[', 1)
            name = name.rstrip(']')
            node.run_list.create(type=type, name=name)
        return node


class Node(models.Model):
    name = models.CharField(max_length=1024, unique=True)
    automatic_data = models.TextField()
    override_data = models.TextField()
    normal_data = models.TextField()
    default_data = models.TextField()

    objects = NodeManager()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('commis_webui_nodes_show', args=(self,))

    @property
    def automatic(self):
        if not self.automatic_data:
            return {}
        return json.loads(self.automatic_data)

    @property
    def override(self):
        if not self.override_data:
            return {}
        return json.loads(self.override_data)

    @property
    def normal(self):
        if not self.normal_data:
            return {}
        return json.loads(self.normal_data)

    @property
    def default(self):
        if not self.default_data:
            return {}
        return json.loads(self.default_data)

    def to_dict(self):
        chef_node = chef.Node(self.name, skip_load=True)
        chef_node.automatic = self.automatic
        chef_node.override = self.override
        chef_node.normal = self.normal
        chef_node.default = self.default
        chef_node.run_list = [unicode(entry) for entry in self.run_list.all()]
        return chef_node

    def to_search(self):
        data = deep_merge(self.automatic, self.override, self.normal, self.default)
        data['name'] = self.name
        data['chef_type'] = 'node'
        run_list = list(self.run_list.all().order_by('id'))
        data['recipe'] = [entry.name for entry in run_list if entry.type == 'recipe']
        data['role'] = [entry.name for entry in run_list if entry.type == 'role']
        data['run_list'] = [entry.name for entry in run_list]
        return data

    def expand_run_list(self):
        recipes = []
        for entry in self.run_list.all().order_by('id'):
            if entry.type == 'role':
                try:
                    role = Role.objects.get(name=entry.name)
                except Role.DoesNotExist:
                    continue
                for recipe in role.expand_run_list():
                    if recipe not in recipes:
                        recipes.append(recipe)
            elif entry.type == 'recipe':
                if entry.name not in recipes:
                    recipes.append(entry.name)
        return recipes


class NodeRunListEntry(models.Model):
    node = models.ForeignKey(Node, related_name='run_list')
    name = models.CharField(max_length=1024)
    type = models.CharField(max_length=1024, choices=[('recipe', 'Recipe'), ('role', 'Role')])

    def __unicode__(self):
        return u'%s[%s]'%(self.type, self.name)

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import site

from commis.nodes.models import Node
from commis.search.indexes import CommisSearchIndex

class NodeIndex(CommisSearchIndex):
    pass

site.register(Node, NodeIndex)

########NEW FILE########
__FILENAME__ = tests
import chef

from commis.test import ChefTestCase
from commis.nodes.models import Node

class NodeAPITestCase(ChefTestCase):
    fixtures = ['cookbook_apt']

    def test_list(self):
        Node.objects.create(name='mynode')
        self.assertIn('mynode', chef.Node.list())

    def test_create(self):
        chef.Node.create(name='mynode', run_list=['recipe[apt]'])
        node = Node.objects.get(name='mynode')
        self.assertEqual(node.run_list.count(), 1)
        self.assertEqual(node.run_list.all()[0].type, 'recipe')
        self.assertEqual(node.run_list.all()[0].name, 'apt')

    def test_get(self):
        node = Node.objects.create(name='mynode', normal_data='{"test_attr": "foo"}')
        node.run_list.create(type='recipe', name='apt')
        chef_node = chef.Node('mynode')
        self.assertEqual(chef_node['test_attr'], 'foo')
        self.assertEqual(chef_node.run_list, ['recipe[apt]'])

    def test_update(self):
        node = Node.objects.create(name='mynode', normal_data='{"test_attr": "foo"}')
        node.run_list.create(type='recipe', name='apt')
        chef_node = chef.Node('mynode')
        chef_node['test_attr'] = 'bar'
        chef_node.run_list = ['role[web_server]']
        chef_node.save()
        node = Node.objects.get(name='mynode')
        self.assertEqual(node.normal, {u'test_attr': u'bar'})
        self.assertEqual(node.run_list.count(), 1)
        self.assertEqual(node.run_list.all()[0].type, 'role')
        self.assertEqual(node.run_list.all()[0].name, 'web_server')

    def test_delete(self):
        Node.objects.create(name='mynode')
        chef.Node('mynode').delete()
        with self.assertRaises(Node.DoesNotExist):
            Node.objects.get(name='mynode')

    def test_cookbooks(self):
        node = Node.objects.create(name='mynode')
        node.run_list.create(type='recipe', name='apt')
        data = chef.Node('mynode').cookbooks()
        self.assertIn('apt', data)

    def test_cookbooks2(self):
        node = Node.objects.create(name='mynode')
        node.run_list.create(type='recipe', name='apache2')
        data = chef.Node('mynode').cookbooks()
        self.assertNotIn('apt', data)

########NEW FILE########
__FILENAME__ = views
from commis.cookbooks.models import Cookbook
from commis.exceptions import ChefAPIError
from commis.generic_views import CommisAPIView, api, CommisView
from commis.nodes.forms import NodeForm
from commis.nodes.models import Node


def authorize_client(self, request, name=None):
    # Normalize name -- in create hooks it comes from the form, not the URI
    # path
    node_name = name or request.json['name']
    if not request.client.admin and not request.client.name == node_name:
        raise ChefAPIError(401, 'You are not allowed to take this action')


class NodeAPIView(CommisAPIView):
    model = Node

    @api('POST', validator=authorize_client)
    def create(self, request):
        return super(NodeAPIView, self).create(request)

    @api('PUT', validator=authorize_client)
    def update(self, request, name):
        return super(NodeAPIView, self).update(request, name)

    @api('DELETE', validator=authorize_client)
    def node_delete(self, request, name):
        return super(NodeAPIView, self).delete(request, name)

    @api('GET', '{name}/cookbooks', validator=authorize_client)
    def node_cookbooks(self, request, name):
        try:
            node = Node.objects.get(name=name)
        except Node.DoesNotExist:
            raise ChefAPIError(404, 'Node %s not found', request.json['name'])
        candidates = set([recipe.split('::', 1)[0] for recipe in node.expand_run_list()])
        cookbooks = {}
        while candidates:
            candidate = candidates.pop()
            if candidate in cookbooks:
                continue # Already checked
            qs = Cookbook.objects.filter(name=candidate).order_by('version')
            if not qs:
                continue # Error?
            candidate_cookbook = qs[0]
            for dep in candidate_cookbook.dependencies.all():
                candidates.add(dep.name)
            cookbooks[candidate] = candidate_cookbook.to_dict(request)
        return cookbooks


class NodeView(CommisView):
    model = Node
    form = NodeForm

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from commis.cookbooks.models import CookbookRecipe
from commis.roles.models import Role

class RoleRunList(forms.SelectMultiple):
    def __init__(self, attrs=None, environment=None):
        super(RoleRunList, self).__init__(attrs)
        self.environment = environment

    def render(self, name, value, attrs=None):
        return render_to_string('commis/roles/_run_list.html', {
            'value': value,
            'available_roles': Role.objects.all(),
            'available_recipes': CookbookRecipe.objects.all(),
        })


class MultipleChoiceAnyField(forms.MultipleChoiceField):
    """A MultipleChoiceField with no validation."""

    def valid_value(self, *args, **kwargs):
        return True


class RoleForm(forms.ModelForm):
    run_list = MultipleChoiceAnyField(required=False)

    class Meta:
        model = Role
        fields = ('name', 'description')

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.initial['run_list'] = [str(entry) for entry in self.instance.run_list.all()]
        self.fields['run_list'].widget = RoleRunList()

    def clean_run_list(self):
        run_list = self.cleaned_data['run_list']
        ret = []
        for entry in run_list:
            if '[' not in entry:
                raise ValidationError('Unparseable run list entry "%s"' % entry)
            entry_type, entry_name = entry.rstrip(']').split('[', 1)
            entry_class = {'role': Role, 'recipe': CookbookRecipe}.get(entry_type)
            if entry_class is None:
                raise ValidationError('Unknown run list entry type "%s"' % entry_type)
            if not entry_class.objects.filter(name=entry_name).exists():
                raise ValidationError('Unknown %s "%s"' % (entry_class._meta.verbose_name, entry_name))
            ret.append({'type': entry_type, 'name': entry_name})
        return ret

    def save(self, *args, **kwargs):
        node = super(RoleForm, self).save(*args, **kwargs)
        node.run_list.all().delete()
        for entry in self.cleaned_data['run_list']:
            node.run_list.create(**entry)
        return node

########NEW FILE########
__FILENAME__ = models
import chef
from django.core.urlresolvers import reverse
from django.db import models

from commis.utils import json

class RoleManager(models.Manager):
    def from_dict(self, data):
        chef_role = chef.Role.from_search(data)
        role, created = self.get_or_create(name=chef_role.name)
        role.description = chef_role.description
        role.override_data = json.dumps(chef_role.override_attributes)
        role.default_data = json.dumps(chef_role.default_attributes)
        role.save()
        role.run_list.all().delete()
        for entry in chef_role.run_list:
            if '[' not in entry:
                continue # Can't parse this
            type, name = entry.split('[', 1)
            name = name.rstrip(']')
            role.run_list.create(type=type, name=name)
        return role


class Role(models.Model):
    name = models.CharField(max_length=1024, unique=True)
    description = models.TextField()
    override_data = models.TextField()
    default_data = models.TextField()

    objects = RoleManager()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('commis_webui_roles_show', args=(self,))

    @property
    def override(self):
        if not self.override_data:
            return {}
        return json.loads(self.override_data)

    @property
    def default(self):
        if not self.default_data:
            return {}
        return json.loads(self.default_data)

    def to_dict(self):
        chef_role = chef.Role(self.name, skip_load=True)
        chef_role.description = self.description
        chef_role.run_list = [unicode(entry) for entry in self.run_list.all()]
        chef_role.default_attributes = self.default
        chef_role.override_attributes = self.override
        return chef_role

    def to_search(self):
        return self.to_dict()

    def expand_run_list(self):
        recipes = []
        for entry in self.run_list.all().order_by('id'):
            if entry.type == 'role':
                try:
                    role = Role.objects.get(name=entry.name)
                except Role.DoesNotExist:
                    continue
                for recipe in role.expand_run_list():
                    if recipe not in recipes:
                        recipes.append(recipe)
            elif entry.type == 'recipe':
                if entry.name not in recipes:
                    recipes.append(entry.name)
        return recipes


class RoleRunListEntry(models.Model):
    role = models.ForeignKey(Role, related_name='run_list')
    name = models.CharField(max_length=1024)
    type = models.CharField(max_length=1024, choices=[('recipe', 'Recipe'), ('role', 'Role')])

    def __unicode__(self):
        return u'%s[%s]'%(self.type, self.name)

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import site

from commis.roles.models import Role
from commis.search.indexes import CommisSearchIndex

class RoleIndex(CommisSearchIndex):
    pass

site.register(Role, RoleIndex)

########NEW FILE########
__FILENAME__ = tests
import chef

from commis.test import ChefTestCase
from commis.roles.models import Role

class RoleAPITestCase(ChefTestCase):
    def test_list(self):
        Role.objects.create(name='myrole')
        self.assertIn('myrole', chef.Role.list())

    def test_create(self):
        chef.Role.create(name='myrole', run_list=['recipe[apt]'])
        role = Role.objects.get(name='myrole')
        self.assertEqual(role.run_list.count(), 1)
        self.assertEqual(role.run_list.all()[0].type, 'recipe')
        self.assertEqual(role.run_list.all()[0].name, 'apt')

    def test_get(self):
        role = Role.objects.create(name='myrole', default_data='{"test_attr": "foo"}', override_data='{"test_attr": "bar"}')
        role.run_list.create(type='recipe', name='apt')
        chef_role = chef.Role('myrole')
        self.assertEqual(chef_role.default_attributes['test_attr'], 'foo')
        self.assertEqual(chef_role.override_attributes['test_attr'], 'bar')
        self.assertEqual(chef_role.run_list, ['recipe[apt]'])

    def test_update(self):
        role = Role.objects.create(name='myrole', default_data='{"test_attr": "foo"}')
        role.run_list.create(type='recipe', name='apt')
        chef_role = chef.Role('myrole')
        chef_role.default_attributes['test_attr'] = 'bar'
        chef_role.run_list = ['role[web_server]']
        chef_role.save()
        role = Role.objects.get(name='myrole')
        self.assertEqual(role.default, {u'test_attr': u'bar'})
        self.assertEqual(role.run_list.count(), 1)
        self.assertEqual(role.run_list.all()[0].type, 'role')
        self.assertEqual(role.run_list.all()[0].name, 'web_server')

    def test_delete(self):
        Role.objects.create(name='myrole')
        chef.Role('myrole').delete()
        with self.assertRaises(Role.DoesNotExist):
            Role.objects.get(name='myrole')

########NEW FILE########
__FILENAME__ = views
from commis.generic_views import CommisAPIView, CommisView
from commis.roles.forms import RoleForm
from commis.roles.models import Role

class RoleAPIView(CommisAPIView):
    model = Role

class RoleView(CommisView):
    model = Role
    form = RoleForm

########NEW FILE########
__FILENAME__ = exceptions
class SandboxConflict(Exception):
    """An upload conflict in a file sandbox."""

########NEW FILE########
__FILENAME__ = models
import os

from django.db import models
from django_extensions.db.fields import UUIDField, CreationDateTimeField

from commis import conf
from commis.clients.models import Client
from commis.sandboxes.exceptions import SandboxConflict

class Sandbox(models.Model):
    uuid = UUIDField()
    created = CreationDateTimeField()

    def commit(self):
        completed = []
        for sandbox_file in self.files.all():
            try:
                sandbox_file.commit(self)
            except Exception:
                # Undo and bail
                self.uncommit(completed)
                raise
        self.delete()

    def uncommit(self, completed):
        for sandbox_file in completed:
            try:
                sandbox_file.uncommit(self)
            except Exception:
                pass


class SandboxFile(models.Model):
    sandboxes = models.ManyToManyField(Sandbox, related_name='files')
    checksum = models.CharField(max_length=1024, unique=True)
    uploaded = models.BooleanField()
    content_type = models.CharField(max_length=32)
    created_by = models.ForeignKey(Client, related_name='+')

    @property
    def path(self):
        return os.path.join(conf.COMMIS_FILE_ROOT, self.checksum[0], self.checksum[1], self.checksum)

    @property
    def content(self):
        if not self.uploaded:
            raise ValueError('File not uploaded')
        return open(self.path, 'rb').read()

    def pending_path(self, sandbox):
        return os.path.join(conf.COMMIS_FILE_ROOT, 'pending', sandbox.uuid, self.checksum[0], self.checksum[1], self.checksum)

    def write(self, sandbox, data):
        path = self.pending_path(sandbox)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        open(path, 'wb').write(data)

    def commit(self, sandbox):
        path = self.path
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if os.path.exists(path):
            raise SandboxConflict
        rows = SandboxFile.objects.filter(id=self.id, uploaded=False).update(uploaded=True)
        if not rows:
            raise SandboxConflict
        self.uploaded = True
        self.sandboxes.remove(sandbox)
        os.rename(self.pending_path(sandbox), path)

    def uncommit(self, sandbox):
        path = self.pending_path(sandbox)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if os.path.exists(path):
            os.unlink(path)
        rows = SandboxFile.objects.filter(id=self.id, uploaded=True).update(uploaded=False)
        if not rows:
            raise SandboxConflict
        self.uploaded = False
        self.sandboxes.add(sandbox)
        try:
            os.rename(self.path, path)
        except Exception:
            os.unlink(self.path)

########NEW FILE########
__FILENAME__ = tests
import os

from commis import conf
from commis.test import ChefTestCase
from commis.sandboxes.models import SandboxFile

class SandboxAPITestCase(ChefTestCase):
    def test_create(self):
        checksums = [
            '385ea5490c86570c7de71070bce9384a',
            'f6f73175e979bd90af6184ec277f760c',
            '2e03dd7e5b2e6c8eab1cf41ac61396d5',
        ]
        input = {'checksums': dict((csum, None) for csum in checksums)}
        resp = self.api.api_request('POST', '/sandboxes', data=input)
        self.assertIn('uri', resp)
        self.assertIn('sandbox_id', resp)
        self.assertTrue(resp['sandbox_id'])
        self.assertIn('checksums', resp)
        for csum in checksums:
            self.assertIn(csum, resp['checksums'])
            self.assertIn('needs_upload', resp['checksums'][csum])
            self.assertTrue(resp['checksums'][csum]['needs_upload'])
            self.assertIn('url', resp['checksums'][csum])
            self.assertTrue(resp['checksums'][csum]['url'])

    def test_upload(self):
        checksums = [
            'ab56b4d92b40713acc5af89985d4b786', # 'abcde'
            '0fbd31a7d4febcc8ea2f84414ab95684', # 'abc\0de'
            '9fb548d26b69c60aae1cbdfe25348377', # 'abc\nde'
        ]
        input = {'checksums': dict((csum, None) for csum in checksums)}
        resp = self.api.api_request('POST', '/sandboxes', data=input)
        self.api.request('PUT', '/sandboxes/%s/ab56b4d92b40713acc5af89985d4b786'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abcde')
        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, 'pending', resp['sandbox_id'], 'a', 'b', 'ab56b4d92b40713acc5af89985d4b786')).read(), 'abcde')
        self.api.request('PUT', '/sandboxes/%s/0fbd31a7d4febcc8ea2f84414ab95684'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abc\0de')
        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, 'pending', resp['sandbox_id'], '0', 'f', '0fbd31a7d4febcc8ea2f84414ab95684')).read(), 'abc\0de')
        self.api.request('PUT', '/sandboxes/%s/9fb548d26b69c60aae1cbdfe25348377'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abc\nde')
        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, 'pending', resp['sandbox_id'], '9', 'f', '9fb548d26b69c60aae1cbdfe25348377')).read(), 'abc\nde')

        self.assertFalse(SandboxFile.objects.get(checksum='ab56b4d92b40713acc5af89985d4b786').uploaded)
        self.assertFalse(SandboxFile.objects.get(checksum='0fbd31a7d4febcc8ea2f84414ab95684').uploaded)
        self.assertFalse(SandboxFile.objects.get(checksum='9fb548d26b69c60aae1cbdfe25348377').uploaded)

    def test_commit(self):
        checksums = [
            'ab56b4d92b40713acc5af89985d4b786', # 'abcde'
            '0fbd31a7d4febcc8ea2f84414ab95684', # 'abc\0de'
            '9fb548d26b69c60aae1cbdfe25348377', # 'abc\nde'
        ]
        input = {'checksums': dict((csum, None) for csum in checksums)}
        resp = self.api.api_request('POST', '/sandboxes', data=input)
        self.api.request('PUT', '/sandboxes/%s/ab56b4d92b40713acc5af89985d4b786'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abcde')
        self.api.request('PUT', '/sandboxes/%s/0fbd31a7d4febcc8ea2f84414ab95684'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abc\0de')
        self.api.request('PUT', '/sandboxes/%s/9fb548d26b69c60aae1cbdfe25348377'%resp['sandbox_id'], headers={'Content-Type': 'text/plain'}, data='abc\nde')
        self.api.api_request('PUT', '/sandboxes/%s'%resp['sandbox_id'], data={'is_completed': True})

        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, 'a', 'b', 'ab56b4d92b40713acc5af89985d4b786')).read(), 'abcde')
        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, '0', 'f', '0fbd31a7d4febcc8ea2f84414ab95684')).read(), 'abc\0de')
        self.assertEqual(open(os.path.join(conf.COMMIS_FILE_ROOT, '9', 'f', '9fb548d26b69c60aae1cbdfe25348377')).read(), 'abc\nde')

        self.assertTrue(SandboxFile.objects.get(checksum='ab56b4d92b40713acc5af89985d4b786').uploaded)
        self.assertTrue(SandboxFile.objects.get(checksum='0fbd31a7d4febcc8ea2f84414ab95684').uploaded)
        self.assertTrue(SandboxFile.objects.get(checksum='9fb548d26b69c60aae1cbdfe25348377').uploaded)

########NEW FILE########
__FILENAME__ = views
import hashlib

from commis.generic_views import CommisAPIViewBase, api
from commis.exceptions import ChefAPIError
from commis.sandboxes.models import Sandbox, SandboxFile
from commis.db import update

class SandboxAPIView(CommisAPIViewBase):
    model = Sandbox

    @api('POST', admin=True)
    def create(self, request):
        checksums = request.json['checksums'].keys()
        sandbox = Sandbox.objects.create()
        data = {'uri': self.reverse(request, 'update', sandbox.uuid),
                'sandbox_id': sandbox.uuid, 'checksums': {}}
        for csum in sorted(checksums):
            csum_data = data['checksums'][csum] = {}
            qs = SandboxFile.objects.filter(checksum=csum)
            if qs and qs[0].uploaded:
                csum_data['needs_upload'] = False
            else:
                if qs:
                    sandbox_file = qs[0]
                else:
                    sandbox_file = SandboxFile.objects.create(checksum=csum, created_by=request.client)
                sandbox_file.sandboxes.add(sandbox)
                csum_data['needs_upload'] = True
                csum_data['url'] = self.reverse(request, 'upload', sandbox.uuid, csum)
        return data


    @api('PUT', admin=True)
    def update(self, request, sandbox_id):
        try:
            sandbox = Sandbox.objects.get(uuid=sandbox_id)
        except Sandbox.DoesNotExist:
            raise ChefAPIError(404, 'Sandbox not found')
        if request.json['is_completed']:
            sandbox.commit()
        return {}


    @api('PUT', admin=True)
    def upload(self, request, sandbox_id, checksum):
        try:
            sandbox = Sandbox.objects.get(uuid=sandbox_id)
        except Sandbox.DoesNotExist:
            raise ChefAPIError(404, 'Sandbox not found')
        try:
            sandbox_file = SandboxFile.objects.get(checksum=checksum)
        except SandboxFile.DoesNotExist:
            raise ChefAPIError(404, 'Invalid upload target')
        if sandbox_file.uploaded:
            raise ChefAPIError(500, 'Duplicate upload')
        if sandbox_file.created_by_id != request.client.id:
            raise ChefAPIError(403, 'Upload client mismatch')
        if hashlib.md5(request.raw_post_data).hexdigest() != checksum:
            raise ChefAPIError(500, 'Checksum mismatch')
        update(sandbox_file, content_type=request.META['CONTENT_TYPE'])
        sandbox_file.write(sandbox, request.raw_post_data)
        return {'uri': self.reverse(request, 'upload', sandbox.uuid, checksum)}

########NEW FILE########
__FILENAME__ = commis_solr_backend
from haystack.backends import solr_backend

class SearchBackend(solr_backend.SearchBackend):
    def setup(self):
        super(SearchBackend, self).setup()

    def build_schema(self, fields):
        content_field_name, schema_fields = super(SearchBackend, self).build_schema(fields)
        for field in schema_fields:
            if field['type'] == 'text':
                field['type'] = 'text_ws'
        return content_field_name, schema_fields


class SearchQuery(solr_backend.SearchQuery):
    def __init__(self, site=None, backend=None):
        super(SearchQuery, self).__init__(backend=backend)

        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)

########NEW FILE########
__FILENAME__ = commis_whoosh_backend
from haystack.backends import whoosh_backend
from whoosh.analysis import SimpleAnalyzer
from whoosh.fields import TEXT
from whoosh.qparser.common import rcompile
from whoosh.qparser.default import QueryParser
from whoosh.qparser.plugins import (BoostPlugin, OperatorsPlugin, FieldsPlugin,
    GroupPlugin, PhrasePlugin, RangePlugin, SingleQuotesPlugin, WildcardPlugin)

class CommisWildcardPlugin(WildcardPlugin):
    def tokens(self, parser):
        return ((CommisWildcardPlugin.Wild, 1), )

    class Wild(WildcardPlugin.Wild):
        # Any number of chars, followed by at least one question mark or
        # star, followed by any number of chars
        # \u055E = Armenian question mark
        # \u061F = Arabic question mark
        # \u1367 = Ethiopic question mark
        expr = rcompile(u"[^\\s()'\"]*[*?\u055E\u061F\u1367][^\\s()'\"]*")

plugins = (BoostPlugin, OperatorsPlugin, FieldsPlugin, GroupPlugin,
                PhrasePlugin, RangePlugin, SingleQuotesPlugin, CommisWildcardPlugin)

class SearchBackend(whoosh_backend.SearchBackend):
    def setup(self):
        super(SearchBackend, self).setup()
        self.parser = QueryParser(self.content_field_name, schema=self.schema, plugins=plugins)

    def build_schema(self, fields):
        content_field_name, schema = super(SearchBackend, self).build_schema(fields)
        for field in schema:
            if isinstance(field, TEXT):
                field.format.analyzer = SimpleAnalyzer(r'[\r\n]+', True)
        return content_field_name, schema


class SearchQuery(whoosh_backend.SearchQuery):
    def __init__(self, site=None, backend=None):
        super(SearchQuery, self).__init__(backend=backend)

        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)

########NEW FILE########
__FILENAME__ = exceptions
class InvalidSearchQuery(Exception):
    """An invalid expression in a search query."""

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from commis.data_bags.models import DataBag
from commis.search.query_transformer import transform_query, execute_query, DEFAULT_INDEXES
from commis.utils.dict import flatten_dict

class SearchForm(forms.Form):
    index = forms.ChoiceField(choices=(), required=False)
    q = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        size = kwargs.pop('size', 0)
        super(SearchForm, self).__init__(*args, **kwargs)
        indexes = {}
        for name, model in DEFAULT_INDEXES.iteritems():
            indexes[name] = model._meta.verbose_name.capitalize()
        for name in DataBag.objects.values_list('name', flat=True):
            if name not in indexes:
                indexes[name] = name.capitalize()
        self.fields['index'].choices = sorted(indexes.iteritems())
        # If the query is too big to see, scale up to field (capped at 150)
        if 'q' in self.data and len(self.data['q']) > size - 10:
            size = min(len(self.data['q']) + 20, 150)
        if size:
            self.fields['q'].widget.attrs['size'] = size
        self._sqs = None

    def clean_q(self):
        if self.cleaned_data['q']:
            # No query isn't error, but just pass through
            try:
                self.cleaned_data['q'], self.cleaned_data['q_fields'] = transform_query(self.cleaned_data['q'])
            except Exception:
                raise forms.ValidationError(_('Invalid query'))
        return self.cleaned_data['q']

    def clean_index(self):
        if not self.cleaned_data['index']:
            return 'node'
        return self.cleaned_data['index']

    def is_searchable(self):
        return self.is_valid() and self.cleaned_data['q']

    def _run_search(self):
        if self._sqs is None and self.is_searchable():
            self._sqs = execute_query(self.cleaned_data['index'], self.cleaned_data['q'])

    @property
    def results(self):
        self._run_search()
        return self._sqs

    @property
    def table_header(self):
        return self.cleaned_data['q_fields']

    @property
    def table(self):
        header = self.table_header
        for row in self.results:
            table_row = {
                'obj': row.object,
                'url': row.object.get_absolute_url(),
                'data': [],
            }
            data = flatten_dict(row.object.to_search())
            for name in header:
                values = [unicode(v) for v in data.get(name, ())]
                table_row['data'].append(' '.join(values))
            yield table_row

########NEW FILE########
__FILENAME__ = indexes
# From https://github.com/mixcloud/django-celery-haystack-SearchIndex/blob/master/queued_indexer.py
from django.db.models import signals
from django.db.models.loading import get_model
from haystack import indexes
from haystack import site

from commis.search.tasks import SearchIndexUpdateTask
from commis.utils.dict import flatten_dict

def remove_instance_from_index(instance):
    model_class = get_model(instance._meta.app_label, instance._meta.module_name)
    search_index = site.get_index(model_class)
    search_index.remove_object(instance)


class QueuedSearchIndex(indexes.SearchIndex):
    """
    A ``SearchIndex`` subclass that enqueues updates for later processing.

    Deletes are handled instantly since a reference, not the instance, is put on the queue. It would not be hard
    to update this to handle deletes as well (with a delete task).
    """
    # We override the built-in _setup_* methods to connect the enqueuing operation.
    def _setup_save(self, model):
        signals.post_save.connect(self.enqueue_save, sender=model)

    def _setup_delete(self, model):
        signals.post_delete.connect(self.enqueue_delete, sender=model)

    def _teardown_save(self, model):
        signals.post_save.disconnect(self.enqueue_save, sender=model)

    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)

    def enqueue_save(self, instance, **kwargs):
        SearchIndexUpdateTask.apply_async(args=[instance._meta.app_label, instance._meta.module_name, instance._get_pk_val()])

    def enqueue_delete(self, instance, **kwargs):
        remove_instance_from_index(instance)


class CommisSearchIndex(QueuedSearchIndex):
    text = indexes.CharField(document=True)
    id_order = indexes.CharField()

    def prepare_text(self, obj):
        buf = []
        for key, values in flatten_dict(obj.to_search()).iteritems():
            for value in values:
                buf.append('%s__=__%s'%(key, value))
        return '\n'.join(buf)

    def prepare_id_order(self, obj):
        return '%016d'%obj.id

########NEW FILE########
__FILENAME__ = models


########NEW FILE########
__FILENAME__ = query_parser
#
# lucene_grammar.py
#
# Copyright 2011, Paul McGuire
#
# implementation of Lucene grammar, as decribed
# at http://svn.apache.org/viewvc/lucene/dev/trunk/lucene/docs/queryparsersyntax.html
#

from pyparsing import (Literal, CaselessKeyword, Forward, Regex, QuotedString, Suppress,
    Optional, Group, FollowedBy, operatorPrecedence, opAssoc, ParseException, ParserElement)
ParserElement.enablePackrat()

COLON,LBRACK,RBRACK,LBRACE,RBRACE,TILDE,CARAT = map(Literal,":[]{}~^")
LPAR,RPAR = map(Suppress,"()")
and_ = CaselessKeyword("AND")
or_ = CaselessKeyword("OR")
not_ = CaselessKeyword("NOT")
to_ = CaselessKeyword("TO")
keyword = and_ | or_ | not_

expression = Forward()

valid_word = Regex(r'([a-zA-Z0-9*_+.-]|\\[!(){}\[\]^"~*?\\:])+').setName("word")
valid_word.setParseAction(
    lambda t : t[0].replace('\\\\',chr(127)).replace('\\','').replace(chr(127),'\\')
    )

string = QuotedString('"')

required_modifier = Literal("+")("required")
prohibit_modifier = Literal("-")("prohibit")
integer = Regex(r"\d+").setParseAction(lambda t:int(t[0]))
proximity_modifier = Group(TILDE + integer("proximity"))
number = Regex(r'\d+(\.\d+)?').setParseAction(lambda t:float(t[0]))
fuzzy_modifier = (Group(TILDE + number) | TILDE)("fuzzy")

term = Forward()
field_name = valid_word.copy().setName("fieldname")
incl_range_search = Group(LBRACK + term("lower") + to_ + term("upper") + RBRACK)
excl_range_search = Group(LBRACE + term("lower") + to_ + term("upper") + RBRACE)
range_search = incl_range_search("incl_range") | excl_range_search("excl_range")
boost = (CARAT + number("boost"))

string_expr = Group(string + proximity_modifier) | string
word_expr = Group(valid_word + fuzzy_modifier) | valid_word
term << (Optional(field_name("field") + COLON) + 
         (word_expr("value") | string_expr("value") | range_search | Group(LPAR + expression + RPAR)) +
         Optional(boost))
term.setParseAction(lambda t:[t] if 'field' in t or 'boost' in t else None)

expression << operatorPrecedence(term,
    [
    (required_modifier | prohibit_modifier, 1, opAssoc.RIGHT),
    ((not_ | '!').setParseAction(lambda:"NOT")("not"), 1, opAssoc.RIGHT),
    ((and_ | '&&').setParseAction(lambda:"AND")("and"), 2, opAssoc.LEFT),
    (Optional(or_ | '||').setParseAction(lambda:"OR")("or"), 2, opAssoc.LEFT),
    ])

########NEW FILE########
__FILENAME__ = query_transformer
from haystack.query import SearchQuerySet, SQ

from commis.clients.models import Client
from commis.data_bags.models import DataBagItem
from commis.nodes.models import Node
from commis.roles.models import Role
from commis.search.exceptions import InvalidSearchQuery
from commis.search.query_parser import expression

DEFAULT_INDEXES = {
    'client': Client,
    'node': Node,
    'role': Role,
}

def transform_query(query_text):
    if query_text == '*:*':
         return query_text, []
    if ':' not in query_text:
        # Use simple query mode
        query_text = ' AND '.join('%s:*'%field for field in query_text.split())
    query = expression.parseString(query_text, parseAll=True)
    fields = []
    transformed_query = _transform(query[0], fields)
    return transformed_query, fields


def execute_query(index, query_text):
    qs = SearchQuerySet().order_by('id_order')
    model = DEFAULT_INDEXES.get(index)
    if model is None:
        qs = qs.models(DataBagItem).narrow('data_bag:%s'%index)
    else:
        qs = qs.models(model)
    if query_text == '*:*':
        # Shortcut for all models, this could even skip haystack entirely.
        return qs
    return qs.filter(query_text)


def _transform(query, fields):
    if 'field' in query and query['field'] not in fields and '*' not in query['field']:
        fields.append(query['field'])
    if 'value' in query:
        return SQ(content='%s__=__%s'%(query['field'], query['value']))
    if 'incl_range' in query:
        lower = query['incl_range']['lower']
        upper = query['incl_range']['upper']
        if lower == '*' and upper == '*':
            # Shortcut for [* TO *]
            return SQ(content='%s__=__*'%(query['field']))
        return SQ(text__range=['%s__=__%s'%(query['field'], lower), 
                                  '%s__=__%s'%(query['field'], upper)])
    elif 'excl_range' in query:
        lower = query['excl_range']['lower']
        upper = query['excl_range']['upper']
        return ~SQ(text__range=['%s__=__%s'%(query['field'], lower), 
                                   '%s__=__%s'%(query['field'], upper)])
    if 'and' in query:
        return _transform(query[0], fields) & _transform(query[2], fields)
    if 'or' in query:
        return _transform(query[0], fields) | _transform(query[2], fields)
    if 'not' in query:
        return ~ _transform(query[1], fields)
    if len(query) == 1:
        return _transform(query[0], fields)
    raise InvalidSearchQuery

########NEW FILE########
__FILENAME__ = tasks
# From https://github.com/mixcloud/django-celery-haystack-SearchIndex/blob/master/tasks.py
from celery.task import Task, PeriodicTask
from celery.task.schedules import crontab
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.loading import get_model
from haystack import site
from haystack.management.commands import update_index

class SearchIndexUpdateTask(Task):
    routing_key = 'search.index.update'
    default_retry_delay = 5 * 60
    max_retries = 1

    def run(self, app_name, model_name, pk, **kwargs):
        logger = self.get_logger(**kwargs)
        try:
            model_class = get_model(app_name, model_name)
            instance = model_class.objects.get(pk=pk)
            search_index = site.get_index(model_class)
            search_index.update_object(instance)
        except ObjectDoesNotExist, exc:
            logger.warn(exc)
        except Exception, exc:
            logger.error(exc)
            self.retry([app_name, model_name, pk], kwargs, exc=exc)


class SearchIndexUpdateTask(PeriodicTask):
    routing_key = 'periodic.search.update_index'
    run_every = crontab(hour=4, minute=0)

    def run(self, **kwargs):
        logger = self.get_logger(**kwargs)
        logger.info("Starting update index")
        # Run the update_index management command
        update_index.Command().handle()
        logger.info("Finishing update index")

########NEW FILE########
__FILENAME__ = tests
import chef
from django.utils import unittest

from commis.test import ChefTestCase
from commis.data_bags.models import DataBag
from commis.utils import json

class SearchAPITestCase(ChefTestCase):
    @unittest.skip('Still working on Haystack test setup')
    def test_bag(self):
        bag = DataBag.objects.create(name='mybag')
        data = {'id': 'item1', 'attr': 1, 'nested': {'nested_attr': 'foo'}}
        bag.items.create(name='item1', data=json.dumps(data))
        data = {'id': 'item2', 'attr': 1, 'nested': {'nested_attr': 'bar'}}
        bag.items.create(name='item2', data=json.dumps(data))
        data = {'id': 'item3', 'attr2': 1}
        bag.items.create(name='item3', data=json.dumps(data))
        chef_query = chef.Search('mybag', 'attr:1')
        self.assertEqual(len(chef_query), 2)
        self.assertIn('item1', chef_query)
        self.assertIn('item2', chef_query)

########NEW FILE########
__FILENAME__ = views
import csv
import itertools
from StringIO import StringIO

from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import django.utils.simplejson as json

from commis.data_bags.models import DataBag
from commis.generic_views import CommisAPIViewBase, api, CommisViewBase
from commis.exceptions import ChefAPIError
from commis.search.forms import SearchForm
from commis.search.query_transformer import DEFAULT_INDEXES

class SearchAPIView(CommisAPIViewBase):
    app_label = 'search'

    @api('GET')
    def list(self, request):
        data = {}
        for name in itertools.chain(DEFAULT_INDEXES.iterkeys(), DataBag.objects.values_list('name', flat=True)):
            data[name] = self.reverse(request, 'get', name)
        return data

    @api('GET')
    def get(self, request, name):
        args = {'index': name, 'q': request.GET.get('q', '*:*')}
        form = SearchForm(args)
        if not form.is_searchable():
            if form['index'].errors:
                raise ChefAPIError(404, 'Index %s not found', name)
            raise ChefAPIError(500, 'Invalid search')
        rows = int(request.GET.get('rows', 20))
        start = int(request.GET.get('start', 0))
        rows = [result.object for result in form.results[start:start+rows]]
        return {
            'total': form.results.count(),
            'start': start,
            'rows': rows,
        }


class SearchView(CommisViewBase):
    app_label = 'search'

    def csv_format(self, request, form):
        outf = StringIO()
        writer = csv.writer(outf)
        writer.writerow([_('name')] + form.table_header)
        for row in form.table:
            writer.writerow([unicode(row['obj'])] + row['data'])
        return HttpResponse(outf.getvalue(), mimetype='text/plain')

    def json_format(self, request, form):
        json_data = []
        for row in form.table:
            json_row = {_('name'): unicode(row['obj'])}
            for field, value in itertools.izip(form.table_header, row['data']):
                json_row[field] = value
            json_data.append(json_row)
        return HttpResponse(json.dumps(json_data), mimetype='application/json')

    def search(self, request):
        form = SearchForm(request.GET, size=70)
        format = request.GET.get('format')
        if format and form.is_searchable():
            format_cb = {
                'csv': self.csv_format,
                'json': self.json_format,
            }.get(format)
            if format_cb:
                return format_cb(request, form)
        return TemplateResponse(request, 'commis/search/search.html', {
            'form': form,
        })

    def get_urls(self):
        return patterns('',
            url(r'^$',
                self.search,
                name='commis_webui_%s' % self.get_app_label()),
        )

########NEW FILE########
__FILENAME__ = search_sites
import haystack
haystack.autodiscover()

########NEW FILE########
__FILENAME__ = settings
# Django settings for commis project.
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_ROOT, 'commis.db'),                      # Or path to database file if using sqlite3.
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
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'c18gpwy2fno=dbwv0o1=@&mdl#oi$z5@g^5%**^p7!7a#i_ehq'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'commis.middleware.PermissionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'commis.middleware.LogOutputMiddleware',
)

ROOT_URLCONF = 'commis.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'commis.middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'djcelery',
    'haystack',
    'commis',
    'commis.clients',
    'commis.sandboxes',
    'commis.cookbooks',
    'commis.roles',
    'commis.data_bags',
    'commis.search',
    'commis.nodes',
    'commis.users',
    'commis.status',
]

# Enable PyZen optionally
try:
    import pyzen
    INSTALLED_APPS.append('pyzen')
except ImportError:
    pass

TEST_RUNNER = 'commis.test.runner.CommisTestSuiteRunner'
TEST_EXTRA = ['commis.utils']

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {message_constants.INFO: 'notice', message_constants.SUCCESS: 'notice'}

import djcelery
djcelery.setup_loader()
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

from commis.search import backends
backends.setup_backends()
HAYSTACK_SITECONF = 'commis.search_sites'
HAYSTACK_SEARCH_ENGINE = 'commis_whoosh'
HAYSTACK_WHOOSH_PATH = os.path.join(PROJECT_ROOT, '.search_index')
HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr'

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = commis_status
from __future__ import absolute_import
import datetime

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext as _, ungettext

register = template.Library()

@register.filter
@stringfilter
def commis_status_short_uptime(uptime):
    return ' '.join(uptime.split()[0:2])


@register.inclusion_tag('commis/status/_last_checkin.html')
def commis_status_last_checkin(ohai_time):
    delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(ohai_time)

    # Compute the CSS class for the cell
    if delta >= datetime.timedelta(days=1):
        status_class = 'error'
    elif delta >= datetime.timedelta(hours=1):
        status_class = 'warning'
    else:
        status_class = ''
    
    hours = delta.seconds // 3600
    hours_text = ungettext('%(hours)s hour', '%(hours)s hours', hours) % {'hours': hours}
    minutes = delta.seconds // 60
    minutes_text = ungettext('%(minutes)s minute', '%(minutes)s minutes', minutes) % {'minutes': minutes}

    # Short form of the delta
    if delta.days > 2:
        delta_short = _('> %(days)s days ago') % {'days': delta.days}
    elif hours:
        delta_short = _('> %(hours_text)s ago') % {'hours_text': hours_text}
    elif minutes < 1:
        delta_short = _('< 1 minute ago')
    else:
        delta_short = _('%(minutes_text)s ago') % {'minutes_text': minutes_text}

    # Long form of the delta
    if hours:
        delta_long = _('%(hours_text)s, %(minutes_text)s ago') % {'hours_text': hours_text, 'minutes_text': minutes_text}
    else:
        delta_long = _('%(minutes_text)s ago') % {'minutes_text': minutes_text}
    return {
        'ohai_time': ohai_time,
        'status_class': status_class,
        'delta_short': delta_short,
        'delta_long': delta_long,
    }

########NEW FILE########
__FILENAME__ = views
from django.conf.urls.defaults import patterns, url
from django.template.response import TemplateResponse

from commis.generic_views import CommisViewBase
from commis.nodes.models import Node

class StatusView(CommisViewBase):
    app_label = 'status'

    def status(self, request):
        return TemplateResponse(request, 'commis/status/status.html', {
            'nodes': Node.objects.all(),
        })

    def get_urls(self):
        return patterns('',
            url(r'^$',
                self.status,
                name='commis_webui_%s' % self.get_app_label()),
        )

########NEW FILE########
__FILENAME__ = commis
from __future__ import absolute_import
import collections

from django import template
from django.core.urlresolvers import reverse
from django.utils.encoding import force_unicode

from commis.search.forms import SearchForm
from commis.utils.deleted_objects import get_deleted_objects

register = template.Library()

@register.simple_tag(takes_context=True)
def commis_nav_item(context, name, view_name):
    request = context['request']
    url = reverse(view_name)
    active = request.path_info.startswith(url)
    return '<li%s><a href="%s">%s</a></li>'%(' class="active"' if active else '', url, name)


@register.inclusion_tag('commis/delete_confirmation.html', takes_context=True)
def commis_delete_confirmation(context, obj):
    request = context['request']
    opts = obj._meta
    deleted_objects, perms_needed, protected = get_deleted_objects(obj, request)
    return {
        'object': obj,
        'object_name': force_unicode(opts.verbose_name),
        'deleted_objects': deleted_objects,
        'perms_lacking': perms_needed,
        'protected': protected,
        'opts': opts,
    }


@register.inclusion_tag('commis/_json.html')
def commis_json(name, obj):
    return {
        'name': name,
        'obj': obj,
        'count': 0,
    }


@register.inclusion_tag('commis/_json_tree.html', takes_context=True)
def commis_json_tree(context, key, value, parent=0):
    root_context = context.get('root_context', context)
    root_dict = root_context.dicts[0]
    root_dict['count'] += 1
    return {
        'root_context': root_context,
        'name': context['name'],
        'count': root_dict['count'],
        'key': key,
        'value': value,
        'cur_count': root_dict['count'],
        'parent': parent,
        'is_dict': isinstance(value, collections.Mapping),
        'is_list': isinstance(value, collections.Sequence) and not isinstance(value, basestring),
    }


@register.simple_tag()
def commis_run_list_class(entry):
    if entry.startswith('recipe['):
        return 'ui-state-default'
    elif entry.startswith('role['):
        return 'ui-state-highlight'
    raise ValueError('Unknown entry %s'%entry)


@register.simple_tag()
def commis_run_list_name(entry):
    return entry.split('[', 1)[1].rstrip(']')


@register.inclusion_tag('commis/_header_search.html', takes_context=True)
def commis_header_search(context):
    return {'form': SearchForm(size=20)}

########NEW FILE########
__FILENAME__ = cases
import shutil
import StringIO
import tempfile
import urllib2
import urlparse

from django.test import TestCase
import chef

from commis import conf
from commis.clients.models import Client


class TestChefAPI(chef.ChefAPI):
    fake_url = 'http://localhost/api'

    def __init__(self, testclient, *args, **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.fake_url
        else:
            args = (self.fake_url,) + args
        super(TestChefAPI, self).__init__(*args, **kwargs)
        self.testclient = testclient

    def _request(self, method, url, data, headers):
        parsed_url = urlparse.urlparse(url)
        args = {'path': parsed_url.path}
        if parsed_url.query:
            args['path'] += '?' + parsed_url.query
        if data:
            args['data'] = data
        for key, value in headers.iteritems():
            args['HTTP_'+key.upper().replace('-', '_')] = value
        if 'HTTP_CONTENT_TYPE' in args:
            args['content_type'] = args['HTTP_CONTENT_TYPE']
        resp = getattr(self.testclient, method.lower())(**args)
        if not (200 <= resp.status_code < 300):
            raise urllib2.HTTPError(url, resp.status_code, '', resp, StringIO.StringIO(resp.content))
        return resp.content


class ChefTestCase(TestCase):
    def setUp(self):
        super(ChefTestCase, self).setUp()
        self.old_file_root = conf.COMMIS_FILE_ROOT
        conf.COMMIS_FILE_ROOT = tempfile.mkdtemp()

        self._client = Client.objects.create(name='unittest', admin=True)
        self.api = TestChefAPI(self.client, self._client.key, self._client.name)
        self.api.__enter__()

    def tearDown(self):
        self.api.__exit__(None, None, None)

        shutil.rmtree(conf.COMMIS_FILE_ROOT)
        conf.COMMIS_FILE_ROOT = self.old_file_root
        super(ChefTestCase, self).tearDown()

########NEW FILE########
__FILENAME__ = runner
from fnmatch import fnmatch

from django.conf import settings
from django.db.models import get_app, get_apps
from django.test.simple import build_suite, build_test, reorder_suite, DjangoTestSuiteRunner, TEST_MODULE
from django.test.testcases import TestCase
from django.utils import unittest
from django.utils.importlib import import_module

from commis.utils.modules import guess_app

class CommisTestSuiteRunner(DjangoTestSuiteRunner):
    def setup_test_environment(self, **kwargs):
        settings.HAYSTACK_SEARCH_ENGINE = 'commis_whoosh'
        settings.HAYSTACK_WHOOSH_STORAGE = 'ram'
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
        super(CommisTestSuiteRunner, self).setup_test_environment(**kwargs)

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = unittest.TestSuite()

        if test_labels:
            for label in test_labels:
                if '.' in label:
                    suite.addTest(build_test(label))
                else:
                    app = get_app(label)
                    suite.addTest(build_suite(app))
        else:
            for app in get_apps():
                app_name = guess_app(app)
                for pattern in getattr(settings, 'TEST_WHITELIST', ('%s.*'%__name__.split('.')[0],)):
                    if fnmatch(app_name, pattern):
                        suite.addTest(build_suite(app))
                        break

            for name in getattr(settings, 'TEST_EXTRA', ()):
                mod = import_module(name + '.' + TEST_MODULE)
                extra_suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
                suite.addTest(extra_suite)


        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)

        return reorder_suite(suite, (TestCase,))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url, include
from django.views.generic import TemplateView

from commis.clients.views import ClientAPIView, ClientView
from commis.cookbooks.views import CookbookAPIView, CookbookView
from commis.data_bags.views import DataBagAPIView, DataBagView
from commis.nodes.views import NodeAPIView, NodeView
from commis.roles.views import RoleAPIView, RoleView
from commis.sandboxes.views import SandboxAPIView
from commis.search.views import SearchAPIView, SearchView
from commis.status.views import StatusView
from commis.users.views import UserView
from commis.environments.views import EnvironmentAPIView


urlpatterns = patterns('',
    url(r'^api/clients', include(ClientAPIView.as_view())),
    url(r'^api//?cookbooks', include(CookbookAPIView.as_view())),
    url(r'^api/data', include(DataBagAPIView.as_view())),
    url(r'^api/nodes', include(NodeAPIView.as_view())),
    url(r'^api/roles', include(RoleAPIView.as_view())),
    url(r'^api/sandboxes', include(SandboxAPIView.as_view())),
    url(r'^api/search', include(SearchAPIView.as_view())),
    url(r'^api/environments', include(EnvironmentAPIView.as_view())),

    url(r'^clients/', include(ClientView.as_view())),
    url(r'^cookbooks/', include(CookbookView.as_view())),
    url(r'^databags/', include(DataBagView.as_view())),
    url(r'^nodes/', include(NodeView.as_view())),
    url(r'^roles/', include(RoleView.as_view())),
    url(r'^search/', include(SearchView.as_view())),
    url(r'^status/', include(StatusView.as_view())),
    url(r'^users/', include(UserView.as_view())),
    url(r'^$', TemplateView.as_view(template_name='commis/index.html'), name='commis_webui'),
)

########NEW FILE########
__FILENAME__ = models
# This space left intentionally blank

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from commis.generic_views import CommisView

class UserView(CommisView):
    model = User
    create_form = UserCreationForm
    edit_form = UserChangeForm
    app_label = 'users'
    search_key = 'username'

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
            url(r'^login/$', 'django.contrib.auth.views.login', kwargs={'template_name': 'commis/users/login.html'}),
            url(r'^logout/$', 'django.contrib.auth.views.logout'),
        ) + super(UserView, self).get_urls()

########NEW FILE########
__FILENAME__ = chef_api
import base64
import datetime
import itertools
import traceback

from chef.auth import sha1_base64, canonical_request
from chef.rsa import SSLError
from django.http import HttpResponse

from commis import conf
from commis.exceptions import ChefAPIError
from commis.clients.models import Client
from commis.utils import json

def decode_timestamp(request):
    timestamp = request.META.get('HTTP_X_OPS_TIMESTAMP')
    if not timestamp:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')
    return datetime.datetime.strptime(timestamp.strip(), '%Y-%m-%dT%H:%M:%SZ')


def hash_body(request):
    return sha1_base64(request.raw_post_data)


def decode_client(request):
    user_id = request.META.get('HTTP_X_OPS_USERID')
    if not user_id:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')
    qs = Client.objects.filter(name=user_id.strip())
    if not qs:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')
    return qs[0]


def decode_signature(request):
    request_signature = []
    for i in itertools.count(1):
        hdr = request.META.get('HTTP_X_OPS_AUTHORIZATION_%s'%i)
        if not hdr:
            break
        request_signature.append(hdr.strip())
    return base64.b64decode(''.join(request_signature))


def verify_timestamp(request, timestamp):
    delta = datetime.datetime.utcnow() - timestamp
    if abs(delta.total_seconds()) > conf.COMMIS_TIME_SKEW:
        raise ChefAPIError(401, 'Failed to authenticate. Please synchronize the clock on your client')


def verify_signature(request, timestamp, client, hashed_body):
    candidate_block = canonical_request(request.method, request.path, hashed_body, timestamp, client.name)
    request_signature = decode_signature(request)
    if not request_signature:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')
    try:
        decrypted_block = client.key.public_decrypt(request_signature)
    except SSLError:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')
    if candidate_block != decrypted_block:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')


def verify_body_hash(request, hashed_body):
    candidate_hash = request.META.get('HTTP_X_OPS_CONTENT_HASH', '').strip()
    if candidate_hash != hashed_body:
        raise ChefAPIError(401, 'Failed to authenticate. Ensure that your client key is valid')


def decode_json(request):
    request.json = None
    if request.META.get('CONTENT_TYPE') == 'application/json' and request.raw_post_data:
        try:
            request.json = json.loads(request.raw_post_data)
        except ValueError:
            pass


def create_error(msg, code):
    return HttpResponse(json.dumps({'error': msg, 'traceback': traceback.format_exc()}), status=code, content_type='application/json')


def verify_request(request):
    hashed_body = hash_body(request)
    timestamp = decode_timestamp(request)
    client = decode_client(request)
    verify_timestamp(request, timestamp)
    verify_signature(request, timestamp, client, hashed_body)
    verify_body_hash(request, hashed_body)
    return client


def execute_request(view, request, *args, **kwargs):
    if view is None:
        return create_error('No method found', 404)
    try:
        client = verify_request(request)
        decode_json(request)
        request.client = client
        data = view(request, *args, **kwargs)
        if not isinstance(data, HttpResponse):
            data = HttpResponse(json.dumps(data), content_type='application/json')
        return data
    except ChefAPIError, e:
        return create_error(e.msg, e.code)
    except Exception, e:
        return create_error(str(e), 500)

########NEW FILE########
__FILENAME__ = deleted_objects
from django.contrib.admin import util
from django.db import router

class FakeAdminSite(object):
    def __init__(self):
        self._registry = ()
fake_admin_site = FakeAdminSite()


def get_deleted_objects(obj, request):
    opts = obj._meta
    using = router.db_for_write(obj)
    return util.get_deleted_objects([obj], opts, request.user, fake_admin_site, using)

########NEW FILE########
__FILENAME__ = dict
import collections

def deep_merge(*args):
    dest = {}
    stack = [(dest, d) for d in args]
    while stack:
        current_dest, current_src = stack.pop()
        for key, value in current_src.iteritems():
            if key not in current_dest:
                current_dest[key] = value
            else:
                if isinstance(value, collections.Mapping) and isinstance(current_dest[key], collections.Mapping):
                    stack.append((current_dest[key], value))
                else:
                    current_dest[key] = value
    return dest


def flatten_dict(data):
    return _flatten_each({}, data, ())


def _flatten_each(dest, data, key_path):
    if isinstance(data, collections.Mapping):
        for key, value in data.iteritems():
            _flatten_each(dest, value, key_path+(key,))
    elif isinstance(data, collections.Sequence) and not isinstance(data, basestring):
        for value in data:
            _flatten_each(dest, value, key_path)
    else:
        dest.setdefault('_'.join(key_path), []).append(data)
        if len(key_path) > 1:
            dest.setdefault(key_path[-1], []).append(data)
    return dest

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import

from functools import partial
import types

try: #pragma: no cover
    import json
except ImportError: #pragma: no cover
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import QuerySet
from django.contrib.auth.models import User

def maybe_call(x):
    if callable(x):
        return x()
    return x

def user_to_dict(user):
    return {}

class JSONEncoder(DjangoJSONEncoder):
    """Custom encoder to allow arbitrary model classes."""

    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return maybe_call(obj.to_dict)
        elif hasattr(obj, 'to_list'):
            return maybe_call(obj.to_list)
        elif isinstance(obj, User):
            return user_to_dict(obj)
        elif isinstance(obj, QuerySet):
            return list(obj)
        elif isinstance(obj, types.GeneratorType):
            return list(obj)
        return super(JSONEncoder, self).default(obj)

load = json.load
loads = json.loads
dump = partial(json.dump, cls=JSONEncoder)
dumps = partial(json.dumps, cls=JSONEncoder)

########NEW FILE########
__FILENAME__ = modules
import types

from django.conf import settings

def guess_app(obj):
    if isinstance(obj, types.ModuleType):
        name = obj.__name__
    elif isinstance(obj, basestring):
        name = obj
    else:
        name = obj.__module__
    possibles = []
    for app in settings.INSTALLED_APPS:
        if name.startswith(app):
            possibles.append(app)
    return max(possibles, key=len)

def guess_app_label(obj):
    app = guess_app(obj)
    if app is not None:
        return app.rsplit('.', 1)[-1]

########NEW FILE########
__FILENAME__ = routes
import inspect
import re

ROUTE_PART = re.compile(r'\{(?P<name>\w+)\}')

def route_from_string(s):
    converted = ROUTE_PART.sub(r'(?P<\1>[^/]+)', s)
    if converted:
        converted = '^/' + converted
    return converted

def route_from_function(fn):
    argspec = inspect.getargspec(fn)
    route = '/'.join('{%s}'%arg for arg in argspec.args if arg != 'self' and arg != 'request')
    return route_from_string(route)

########NEW FILE########
__FILENAME__ = tests
from django.utils import unittest

from commis.utils.dict import deep_merge, flatten_dict
from commis.utils.routes import route_from_string, route_from_function

class DictTestCase(unittest.TestCase):
    def test_deep_merge(self):
        a = {
            'a': 1,
            'b': 2,
            'c': {
                'd': 3,
                'e': 4,
            }
        }
        b = {
            'a': 10,
            'd': 3,
            'c': {
                'd': 10,
                'f': 4,
            }
        }
        data = deep_merge(a, b)
        self.assertEqual(data, {
            'a': 1,
            'b': 2,
            'd': 3,
            'c': {
                'd': 3,
                'e': 4,
                'f': 4,
            }
        })

    def test_flatten_dict(self):
        data = {
            'a': 1,
            'b': 2,
            'c': {
                'b': 3,
                'd': 4,
            }
        }
        self.assertEqual(flatten_dict(data), {
            'a': [1],
            'b': [3, 2],
            'd': [4],
            'c_b': [3],
            'c_d': [4],
        })


class RoutesTestCase(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(route_from_string(''), '')
        self.assertEqual(route_from_string('{foo}'), '^/(?P<foo>[^/]+)')
        self.assertEqual(route_from_string('{foo}/{bar}'), '^/(?P<foo>[^/]+)/(?P<bar>[^/]+)')

    def test_from_function(self):
        self.assertEqual(route_from_function(lambda: None), '')
        self.assertEqual(route_from_function(lambda self: None), '')
        self.assertEqual(route_from_function(lambda self, request: None), '')
        self.assertEqual(route_from_function(lambda foo: None), '^/(?P<foo>[^/]+)')
        self.assertEqual(route_from_function(lambda request, foo: None), '^/(?P<foo>[^/]+)')
        self.assertEqual(route_from_function(lambda self, request, foo: None), '^/(?P<foo>[^/]+)')
        self.assertEqual(route_from_function(lambda foo, bar: None), '^/(?P<foo>[^/]+)/(?P<bar>[^/]+)')
        self.assertEqual(route_from_function(lambda request, foo, bar: None), '^/(?P<foo>[^/]+)/(?P<bar>[^/]+)')
        self.assertEqual(route_from_function(lambda self, request, foo, bar: None), '^/(?P<foo>[^/]+)/(?P<bar>[^/]+)')

########NEW FILE########
